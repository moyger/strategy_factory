"""
Live Trading System for Nick Radge Momentum Strategy on Interactive Brokers

This script automates the momentum strategy with IBKR. It should run daily to:
1. Check for regime changes (SPY vs 200-day MA)
2. Execute quarterly rebalances (Jan 1, Apr 1, Jul 1, Oct 1)
3. Handle regime recovery (immediate re-entry on BEAR → BULL)

IMPORTANT: Test on IBKR paper account first!

Requirements:
- ib_insync library: pip install ib_insync
- IBKR TWS or IB Gateway running and logged in
- API connections enabled in TWS settings
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from ib_insync import IB, Stock, MarketOrder, util
import time
import logging
from pathlib import Path


def canonical_symbol(symbol: str) -> str:
    """Return the internal canonical form (e.g., 'BRK.B')."""
    return symbol.replace(' ', '.').upper()


def symbol_for_ib(symbol: str) -> str:
    """Convert canonical symbol to IBKR contract format (e.g., 'BRK B')."""
    return symbol.replace('.', ' ').upper()


def symbol_for_data(symbol: str) -> str:
    """Convert canonical symbol to Yahoo Finance format (e.g., 'BRK-B')."""
    return symbol.replace('.', '-').upper()

# =============================================================================
# CONFIGURATION
# =============================================================================

class LiveTradingConfig:
    """Configuration for live trading"""

    # IBKR Connection
    IBKR_HOST = '127.0.0.1'  # localhost
    IBKR_PORT = 7496  # TWS paper trading port (7496 for live)
    IBKR_CLIENT_ID = 1

    # Strategy Parameters (MUST match backtest)
    PORTFOLIO_SIZE = 7
    NUM_STOCKS = 100  # Top 100 S&P 500 (expanded coverage)
    ROC_PERIOD = 100
    MA_PERIOD = 100

    # Regime-based position sizing (3-tier system from backtest)
    STRONG_BULL_POSITIONS = 7    # SPY > 200 MA
    WEAK_BULL_POSITIONS = 3      # SPY between 50 MA and 200 MA
    BEAR_MARKET_POSITIONS = 0    # SPY < 50 MA (100% cash)

    # Data Source
    USE_IBKR_DATA = False  # False = Yahoo Finance (recommended), True = IBKR API

    # Rebalance Schedule
    REBALANCE_MONTHS = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
    REBALANCE_DAY = 1  # 1st of month
    REBALANCE_HOUR = 10  # 10 AM ET (after market open)

    # Safety Controls
    MAX_POSITION_SIZE_PCT = 0.20  # Max 20% per position
    MIN_POSITION_VALUE = 100  # Don't trade positions < $100
    MAX_SLIPPAGE_PCT = 0.01  # Cancel if price moves > 1%
    DRY_RUN = False  # Set False for live trading

    # Logging
    LOG_FILE = 'output/live_trading.log'
    TRADE_LOG_FILE = 'output/live_trades.csv'


# =============================================================================
# LOGGING SETUP
# =============================================================================

Path('output').mkdir(exist_ok=True)

# Logging Configuration
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Windows-compatible logging (no emoji issues)
import sys
if sys.platform == 'win32':
    # Use UTF-8 encoding on Windows
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LiveTradingConfig.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# IBKR CONNECTION
# =============================================================================

class IBKRConnection:
    """Manages IBKR connection and operations"""

    def __init__(self, config):
        self.config = config
        self.ib = IB()
        self.connected = False

    def connect(self):
        """Connect to IBKR TWS/Gateway"""
        try:
            self.ib.connect(
                self.config.IBKR_HOST,
                self.config.IBKR_PORT,
                clientId=self.config.IBKR_CLIENT_ID
            )
            self.connected = True
            logger.info(f"✅ Connected to IBKR on port {self.config.IBKR_PORT}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to IBKR: {e}")
            logger.error("Make sure TWS or IB Gateway is running and API is enabled")
            return False

    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")

    def get_account_value(self):
        """Get total account value"""
        try:
            account_values = self.ib.accountValues()
            for item in account_values:
                if item.tag == 'NetLiquidation' and item.currency == 'USD':
                    return float(item.value)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting account value: {e}")
            return 0.0

    def get_positions(self):
        """Get current positions as dict {ticker: shares}"""
        try:
            positions = self.ib.positions()
            return {canonical_symbol(pos.contract.symbol): int(pos.position) for pos in positions}
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}

    def get_current_price(self, ticker):
        """Get current market price for ticker (uses Yahoo Finance)"""
        try:
            # Use Yahoo Finance for pricing (IBKR requires paid market data subscription)
            data_symbol = symbol_for_data(ticker)
            df = yf.download(data_symbol, period='1d', progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                return df['Close'].iloc[-1]
            else:
                logger.warning(f"No price data for {ticker}")
                return None
        except Exception as e:
            logger.warning(f"Error getting price for {ticker}: {e}")
            return None

    def get_historical_data(self, ticker, duration='200 D', bar_size='1 day'):
        """
        Get historical data from IBKR (alternative to Yahoo Finance)

        Args:
            ticker: Stock ticker
            duration: How far back (e.g., '200 D', '6 M', '1 Y')
            bar_size: Bar size (e.g., '1 day', '1 hour')

        Returns:
            DataFrame with OHLCV data
        """
        try:
            contract = Stock(symbol_for_ib(ticker), 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            # Request historical data
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,  # Regular trading hours only
                formatDate=1
            )

            # Convert to DataFrame
            df = util.df(bars)

            if df.empty:
                logger.warning(f"No historical data for {ticker}")
                return None

            # Rename columns to match Yahoo Finance format
            df = df.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })

            df.set_index('Date', inplace=True)

            logger.debug(f"Downloaded {len(df)} bars for {ticker} from IBKR")
            return df

        except Exception as e:
            logger.error(f"Error getting IBKR historical data for {ticker}: {e}")
            return None

    def place_order(self, ticker, shares, order_type='MKT'):
        """
        Place order via IBKR

        Args:
            ticker: Stock ticker
            shares: Number of shares (positive = buy, negative = sell)
            order_type: 'MKT' or 'LMT'
        """
        if shares == 0:
            logger.debug(f"Skipping order for {ticker} - zero share delta")
            return True

        if self.config.DRY_RUN:
            action = 'BUY' if shares > 0 else 'SELL'
            logger.info(f"🧪 DRY RUN: Would place {action} order for {abs(shares)} shares of {ticker}")
            return True

        try:
            contract = Stock(symbol_for_ib(ticker), 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            action = 'BUY' if shares > 0 else 'SELL'
            order = MarketOrder(action, abs(shares))

            trade = self.ib.placeOrder(contract, order)
            logger.info(f"📊 Placed {action} order: {abs(shares)} shares of {ticker}")

            # Wait for fill
            timeout = 30
            start = time.time()
            while not trade.isDone() and (time.time() - start) < timeout:
                self.ib.sleep(1)

            if trade.isDone():
                logger.info(f"✅ Order filled: {ticker}")
                return True
            else:
                logger.warning(f"⚠️  Order timeout: {ticker}")
                return False

        except Exception as e:
            logger.error(f"❌ Error placing order for {ticker}: {e}")
            return False


# =============================================================================
# MOMENTUM CALCULATION (Same as backtest)
# =============================================================================

def get_sp500_tickers(num_stocks=100):
    """Get top S&P 500 stocks by market cap and liquidity"""
    tickers = [
        # Technology (30 stocks)
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'ADBE', 'CRM',
        'ORCL', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU', 'NOW',
        'AMAT', 'MU', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'NXPI', 'FTNT', 'PANW',

        # Financials (20 stocks)
        'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'AXP', 'BLK',
        'C', 'SCHW', 'CB', 'SPGI', 'CME', 'PGR', 'MMC', 'AON', 'ICE', 'MCO',

        # Healthcare (20 stocks)
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
        'BSX', 'SYK', 'GILD', 'MDT', 'CI', 'REGN', 'VRTX', 'ZTS', 'CVS', 'HUM',

        # Consumer Discretionary (15 stocks)
        'AMZN', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'LOW', 'DIS', 'BKNG', 'TJX',
        'ORLY', 'CMG', 'MAR', 'ROST', 'AZO',

        # Consumer Staples (5 stocks)
        'WMT', 'COST', 'PG', 'KO', 'PEP',

        # Energy (5 stocks)
        'XOM', 'CVX', 'COP', 'SLB', 'EOG',

        # Industrials (5 stocks)
        'CAT', 'UNP', 'HON', 'UPS', 'BA',
    ]
    return tickers[:num_stocks]


def calculate_momentum(ticker, roc_period=100, ma_period=100, ibkr_conn=None):
    """
    Calculate momentum metrics for a stock

    Args:
        ticker: Stock ticker
        roc_period: ROC lookback period
        ma_period: MA lookback period
        ibkr_conn: IBKRConnection object (optional, for IBKR data source)

    Returns:
        dict with 'ROC', 'Above_MA', 'Close', or None if error
    """
    try:
        # Choose data source
        if LiveTradingConfig.USE_IBKR_DATA and ibkr_conn is not None:
            # Use IBKR historical data
            logger.debug(f"Fetching {ticker} data from IBKR...")
            df = ibkr_conn.get_historical_data(ticker, duration='200 D', bar_size='1 day')
        else:
            # Use Yahoo Finance (default)
            data_symbol = symbol_for_data(ticker)
            logger.debug(f"Fetching {ticker} data from Yahoo Finance as {data_symbol}...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=roc_period * 3)  # Extra buffer
            df = yf.download(data_symbol, start=start_date, end=end_date, progress=False, auto_adjust=True)

        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df is None or df.empty or len(df) < roc_period:
            logger.warning(f"Insufficient data for {ticker}: {len(df) if df is not None else 0} bars")
            return None

        # Calculate ROC
        df['ROC'] = ((df['Close'] / df['Close'].shift(roc_period)) - 1) * 100

        # Calculate MA
        df['MA'] = df['Close'].rolling(window=ma_period).mean()
        df['Above_MA'] = df['Close'] > df['MA']

        # Get latest values
        latest = df.iloc[-1]

        if pd.isna(latest['ROC']) or pd.isna(latest['Close']) or pd.isna(latest['MA']):
            logger.warning(f"Incomplete momentum data for {ticker} - skipping")
            return None

        return {
            'ROC': latest['ROC'],
            'Above_MA': latest['Above_MA'],
            'Close': latest['Close']
        }
    except Exception as e:
        logger.error(f"Error calculating momentum for {ticker}: {e}")
        return None


def get_spy_regime():
    """
    Check SPY regime using 3-tier classification (matches backtest logic)

    Returns:
        'STRONG_BULL', 'WEAK_BULL', or 'BEAR'
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)

        spy = yf.download('SPY', start=start_date, end=end_date, progress=False, auto_adjust=True)

        # Handle MultiIndex columns from yfinance
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        spy['MA50'] = spy['Close'].rolling(window=50).mean()
        spy['MA200'] = spy['Close'].rolling(window=200).mean()
        latest = spy.iloc[-1]

        # Three-tier regime classification (same as backtest)
        if latest['Close'] > latest['MA200']:
            regime = 'STRONG_BULL'
        elif latest['Close'] > latest['MA50']:
            regime = 'WEAK_BULL'
        else:
            regime = 'BEAR'

        logger.info(f"📊 SPY Regime: {regime} (Price: ${latest['Close']:.2f}, MA50: ${latest['MA50']:.2f}, MA200: ${latest['MA200']:.2f})")

        return regime
    except Exception as e:
        logger.error(f"Error calculating SPY regime: {e}")
        return 'STRONG_BULL'  # Default to STRONG_BULL on error (safer)


def rank_stocks_by_momentum(tickers, portfolio_size=7, ibkr_conn=None):
    """
    Rank stocks by momentum and return top N

    Args:
        tickers: List of stock tickers
        portfolio_size: Number of top stocks to return
        ibkr_conn: IBKRConnection object (optional, for IBKR data)

    Returns:
        List of dicts with 'Ticker', 'ROC', 'Close'
    """
    logger.info(f"📊 Calculating momentum for {len(tickers)} stocks...")

    # Get SPY ROC for relative strength filter
    spy_metrics = calculate_momentum('SPY', ibkr_conn=ibkr_conn)
    spy_roc = spy_metrics['ROC'] if spy_metrics else 0

    rankings = []
    for ticker in tickers:
        metrics = calculate_momentum(ticker, ibkr_conn=ibkr_conn)

        if metrics is None:
            continue

        # Filters (same as backtest)
        if not metrics['Above_MA']:
            continue

        if metrics['ROC'] <= spy_roc:  # Relative strength filter
            continue

        rankings.append({
            'Ticker': ticker,
            'ROC': metrics['ROC'],
            'Close': metrics['Close']
        })

    # Sort by ROC descending
    rankings.sort(key=lambda x: x['ROC'], reverse=True)

    # Return top N
    top_stocks = rankings[:portfolio_size]

    logger.info(f"✅ Top {len(top_stocks)} momentum stocks:")
    for i, stock in enumerate(top_stocks, 1):
        logger.info(f"   {i}. {stock['Ticker']} - ROC: {stock['ROC']:.2f}%")

    return top_stocks


# =============================================================================
# REBALANCING LOGIC
# =============================================================================

def should_rebalance_today():
    """Check if today is a rebalance day"""
    now = datetime.now()

    # Check if it's a rebalance month and day
    if now.month in LiveTradingConfig.REBALANCE_MONTHS and now.day == LiveTradingConfig.REBALANCE_DAY:
        # Check if it's the right time of day
        if now.hour >= LiveTradingConfig.REBALANCE_HOUR:
            return True

    return False


def execute_rebalance(ibkr_conn):
    """
    Execute quarterly portfolio rebalance

    Steps:
    1. Get current positions from IBKR
    2. Calculate target positions
    3. Generate exit trades (positions not in top 7)
    4. Generate entry trades (new positions)
    5. Execute trades
    """
    logger.info("=" * 80)
    logger.info("🔄 STARTING QUARTERLY REBALANCE")
    logger.info("=" * 80)

    # 1. Check regime and determine portfolio size
    regime = get_spy_regime()

    # Determine portfolio size based on regime (same as backtest)
    if regime == 'STRONG_BULL':
        portfolio_size = LiveTradingConfig.STRONG_BULL_POSITIONS  # 7
    elif regime == 'WEAK_BULL':
        portfolio_size = LiveTradingConfig.WEAK_BULL_POSITIONS    # 3
    else:  # BEAR
        portfolio_size = LiveTradingConfig.BEAR_MARKET_POSITIONS  # 0

    logger.info(f"📊 Regime: {regime} → Target positions: {portfolio_size}")

    # If bear market (portfolio_size = 0), exit all positions and hold cash
    if portfolio_size == 0:
        logger.info("🐻 BEAR MARKET - Exiting all positions to cash")
        current_positions = ibkr_conn.get_positions()

        for ticker, shares in current_positions.items():
            if shares > 0:
                logger.info(f"   Exiting {ticker}: {shares} shares")
                ibkr_conn.place_order(ticker, -shares)

        logger.info("✅ Rebalance complete - 100% cash")
        return

    # 2. Get target positions (top N momentum stocks based on regime)
    tickers = get_sp500_tickers(LiveTradingConfig.NUM_STOCKS)
    top_stocks = rank_stocks_by_momentum(tickers, portfolio_size, ibkr_conn=ibkr_conn)

    if not top_stocks:
        logger.warning("⚠️  No stocks qualified - staying in cash")
        return

    # 3. Get current positions
    current_positions = ibkr_conn.get_positions()
    current_tickers = set(current_positions.keys())

    # 4. Get account value for position sizing
    account_value = ibkr_conn.get_account_value()
    logger.info(f"💰 Account Value: ${account_value:,.2f}")

    # 5. Calculate target shares for each position (equal weight)
    # First pass: collect priceable stocks
    priceable_stocks = []
    skipped_for_pricing = []

    for stock in top_stocks:
        ticker = stock['Ticker']
        price = ibkr_conn.get_current_price(ticker)

        if price is None or price <= 0:
            logger.warning(f"⚠️  Skipping {ticker} - no price data")
            skipped_for_pricing.append(ticker)
            continue

        priceable_stocks.append({
            'ticker': ticker,
            'price': price,
            'roc': stock['ROC']
        })

    if not priceable_stocks:
        logger.warning("⚠️  No stocks have valid pricing - staying in cash")
        return

    # Second pass: allocate capital equally among priceable stocks only
    allocation_per_stock = account_value / len(priceable_stocks)
    logger.info(f"📊 Allocation per stock: ${allocation_per_stock:,.2f} ({len(priceable_stocks)} priceable stocks)")

    target_positions = {}
    for stock_info in priceable_stocks:
        ticker = stock_info['ticker']
        price = stock_info['price']
        shares = int(allocation_per_stock / price)

        if shares <= 0 or shares * price < LiveTradingConfig.MIN_POSITION_VALUE:
            logger.warning(f"⚠️  Skipping {ticker} - position too small (${shares * price:.2f})")
            skipped_for_pricing.append(ticker)
            continue

        target_positions[ticker] = shares

    if not target_positions:
        logger.warning("⚠️  No positions passed sizing filters - staying in cash")
        return

    if len(target_positions) < LiveTradingConfig.PORTFOLIO_SIZE:
        logger.warning(
            f"⚠️  Only {len(target_positions)} stocks sized successfully (target {LiveTradingConfig.PORTFOLIO_SIZE})"
        )

    if skipped_for_pricing:
        logger.info(
            "ℹ️  Skipped for price/size: %s",
            ', '.join(sorted(set(skipped_for_pricing)))
        )

    # 6. Generate trades
    logger.info("\n📋 TRADE PLAN:")
    logger.info("-" * 80)

    # Exit positions not in target
    exit_failures = []
    for ticker in sorted(current_tickers):
        if ticker not in target_positions:
            shares = current_positions[ticker]
            if shares <= 0:
                continue
            logger.info(f"   EXIT: {ticker} ({shares} shares)")
            if not ibkr_conn.place_order(ticker, -shares):
                exit_failures.append(ticker)

    if exit_failures:
        logger.error(
            "❌ Failed to exit positions %s. Aborting rebalance before new entries.",
            ', '.join(exit_failures)
        )
        return

    # Refresh positions after exits
    current_positions = ibkr_conn.get_positions()

    # Reduce oversized target holdings before buying new ones
    sell_failures = []
    for ticker, target_shares in target_positions.items():
        current_shares = current_positions.get(ticker, 0)
        delta = target_shares - current_shares
        if delta < 0:
            logger.info(f"   SELL: {ticker} ({abs(delta)} shares)")
            if not ibkr_conn.place_order(ticker, delta):
                sell_failures.append(ticker)

    if sell_failures:
        logger.error(
            "❌ Failed to reduce positions %s. Aborting buys to avoid over-allocation.",
            ', '.join(sell_failures)
        )
        return

    # Refresh positions after trims before entering new buys
    current_positions = ibkr_conn.get_positions()

    buy_failures = []
    for ticker, target_shares in target_positions.items():
        current_shares = current_positions.get(ticker, 0)
        delta = target_shares - current_shares

        if delta > 0:
            logger.info(f"   BUY: {ticker} ({delta} shares)")
            if not ibkr_conn.place_order(ticker, delta):
                buy_failures.append(ticker)
        elif delta == 0:
            logger.info(f"   HOLD: {ticker} (already at {current_shares} shares)")

    if buy_failures:
        logger.warning(
            "⚠️  Could not establish full positions in %s. Review IBKR trade logs.",
            ', '.join(buy_failures)
        )

    final_positions = ibkr_conn.get_positions()
    live_positions = {t: s for t, s in final_positions.items() if s > 0}

    logger.info("\n🏁 FINAL POSITIONS:")
    for ticker in sorted(live_positions):
        logger.info(f"   {ticker}: {live_positions[ticker]} shares")
    logger.info(
        f"Total holdings: {len(live_positions)} (target {LiveTradingConfig.PORTFOLIO_SIZE})"
    )
    if len(live_positions) > LiveTradingConfig.PORTFOLIO_SIZE:
        logger.warning("⚠️  Portfolio still holds more names than target – investigate manually")

    logger.info("\n✅ Rebalance complete!")
    logger.info("=" * 80)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main(force_rebalance=False):
    """Main entry point for live trading system

    Args:
        force_rebalance: If True, force a rebalance regardless of date (for testing)
    """
    logger.info("\n" + "=" * 80)
    logger.info("🚀 NICK RADGE MOMENTUM STRATEGY - LIVE TRADING")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'DRY RUN 🧪' if LiveTradingConfig.DRY_RUN else 'LIVE TRADING 💰'}")

    # Connect to IBKR
    ibkr = IBKRConnection(LiveTradingConfig)

    if not ibkr.connect():
        logger.error("❌ Cannot proceed without IBKR connection")
        return

    try:
        # Check if today is a rebalance day (or forced)
        if force_rebalance or should_rebalance_today():
            if force_rebalance:
                logger.info("🧪 FORCED REBALANCE - Testing quarterly rebalance logic")
            else:
                logger.info("📅 Today is a rebalance day!")
            execute_rebalance(ibkr)
        else:
            # Daily monitoring (regime changes)
            logger.info("📊 Daily monitoring - checking regime")
            current_regime = get_spy_regime()

            # Check current positions to infer previous regime
            current_positions = ibkr.get_positions()
            num_positions = len([shares for shares in current_positions.values() if shares > 0])

            # Determine previous regime from position count
            if num_positions >= LiveTradingConfig.STRONG_BULL_POSITIONS:
                previous_regime = 'STRONG_BULL'
            elif num_positions >= LiveTradingConfig.WEAK_BULL_POSITIONS:
                previous_regime = 'WEAK_BULL'
            else:
                previous_regime = 'BEAR'

            logger.info(f"   Previous regime (inferred): {previous_regime} ({num_positions} positions)")
            logger.info(f"   Current regime: {current_regime}")

            # Regime recovery: BEAR → BULL transition (re-enter immediately)
            if previous_regime == 'BEAR' and current_regime in ['WEAK_BULL', 'STRONG_BULL']:
                logger.info("🚀 REGIME RECOVERY: BEAR → BULL - Re-entering positions immediately!")
                logger.info("   (Not waiting for next quarterly rebalance)")
                execute_rebalance(ibkr)
            # Regime deterioration: BULL → BEAR transition (exit to cash)
            elif previous_regime in ['STRONG_BULL', 'WEAK_BULL'] and current_regime == 'BEAR':
                logger.info("🐻 REGIME CHANGE: BULL → BEAR - Exiting all positions to cash!")
                execute_rebalance(ibkr)
            # Regime shift within BULL regimes (STRONG ↔ WEAK)
            elif (previous_regime == 'STRONG_BULL' and current_regime == 'WEAK_BULL') or \
                 (previous_regime == 'WEAK_BULL' and current_regime == 'STRONG_BULL'):
                logger.info(f"⚠️  Regime shift: {previous_regime} → {current_regime}")
                logger.info(f"   Adjusting positions from {num_positions} → {LiveTradingConfig.STRONG_BULL_POSITIONS if current_regime == 'STRONG_BULL' else LiveTradingConfig.WEAK_BULL_POSITIONS}")
                execute_rebalance(ibkr)
            else:
                logger.info("✅ Daily check complete - no regime change, no action needed")

    except Exception as e:
        logger.error(f"❌ Error during execution: {e}", exc_info=True)

    finally:
        ibkr.disconnect()
        logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    import sys

    # Check for --force-rebalance flag
    force_rebalance = '--force-rebalance' in sys.argv or '--test' in sys.argv

    if force_rebalance:
        logger.info("⚠️  FORCE REBALANCE MODE - Simulating quarterly rebalance for testing")

    main(force_rebalance=force_rebalance)
