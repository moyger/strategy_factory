"""
Live Trading: Nick Radge Momentum with BSS (Breakout Strength Score) on IBKR

IMPROVED VERSION: Uses BSS instead of ROC for +51% better returns

This script implements the winning BSS qualifier for live trading on Interactive Brokers:
1. Quarterly rebalancing (Jan 1, Apr 1, Jul 1, Oct 1)
2. 3-tier regime filter (STRONG_BULL, WEAK_BULL, BEAR)
3. BSS ranking: (Price - MA100) / (2 × ATR)
4. GLD allocation during BEAR markets
5. Regime recovery (immediate re-entry on BEAR → BULL)

BACKTEST PERFORMANCE (2020-2024):
- BSS: +217.14% (NEW - This script)
- ROC: +166.10% (OLD - +51% worse)
- Max DD: -21.52% vs -30.39% (8.87% better)
- Win Rate: 71.6% vs 65.2% (6.4% better)

IMPORTANT: Test on IBKR paper account first!

Requirements:
- pip install ib_insync yfinance pandas numpy
- IBKR TWS or IB Gateway running (port 7496 for paper, 7497 for live)
- API connections enabled in TWS settings
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ib_insync import IB, Stock, MarketOrder, util
import time
import logging

# Import BSS qualifier
from strategy_factory.performance_qualifiers import BreakoutStrengthScore


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
    """Configuration for live trading with BSS"""

    # IBKR Connection
    IBKR_HOST = '127.0.0.1'
    IBKR_PORT = 7496  # 7496 = Paper trading, 7497 = Live trading
    IBKR_CLIENT_ID = 1

    # Strategy Parameters (BSS Configuration)
    PORTFOLIO_SIZE = 7
    NUM_STOCKS = 100  # Top 100 S&P 500

    # BSS Parameters (Breakout Strength Score)
    POI_PERIOD = 100  # Point of Initiation (MA100)
    ATR_PERIOD = 14   # ATR lookback
    ATR_MULTIPLIER = 2.0  # Threshold for strong breakout (BSS > 2.0)
    MA_FILTER_PERIOD = 100  # Stock must be above MA100

    # Regime Filter Parameters
    REGIME_MA_LONG = 200  # SPY 200-day MA
    REGIME_MA_SHORT = 50  # SPY 50-day MA

    # Regime-based Position Sizing (3-tier)
    STRONG_BULL_POSITIONS = 7    # SPY > 200MA & 50MA
    WEAK_BULL_POSITIONS = 3      # SPY > 200MA only
    BEAR_MARKET_POSITIONS = 0    # SPY < 200MA → 100% GLD

    # Bear Market Protection
    BEAR_MARKET_ASSET = 'GLD'  # Gold ETF
    BEAR_ALLOCATION = 1.0  # 100% allocation

    # Data Source
    USE_IBKR_DATA = False  # False = Yahoo Finance (recommended)

    # Rebalance Schedule
    REBALANCE_MONTHS = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
    REBALANCE_DAY = 1
    REBALANCE_HOUR = 10  # 10 AM ET

    # Safety Controls
    MAX_POSITION_SIZE_PCT = 0.20  # Max 20% per position
    MIN_POSITION_VALUE = 100  # Don't trade < $100
    MAX_SLIPPAGE_PCT = 0.01  # Cancel if price moves > 1%
    DRY_RUN = True  # ALWAYS start with dry run!

    # Logging
    LOG_FILE = 'output/live_bss_trading.log'
    TRADE_LOG_FILE = 'output/live_bss_trades.csv'


# =============================================================================
# LOGGING SETUP
# =============================================================================

Path('output').mkdir(exist_ok=True)

LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

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
# IBKR CONNECTION (Same as before)
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
            return False

    def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")

    def get_account_value(self):
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
        try:
            positions = self.ib.positions()
            return {canonical_symbol(pos.contract.symbol): int(pos.position) for pos in positions}
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}

    def get_current_price(self, ticker):
        try:
            data_symbol = symbol_for_data(ticker)
            df = yf.download(data_symbol, period='1d', progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                return df['Close'].iloc[-1]
            return None
        except Exception as e:
            logger.warning(f"Error getting price for {ticker}: {e}")
            return None

    def place_order(self, ticker, shares):
        if shares == 0:
            return True

        if self.config.DRY_RUN:
            action = 'BUY' if shares > 0 else 'SELL'
            logger.info(f"🧪 DRY RUN: Would {action} {abs(shares)} shares of {ticker}")
            return True

        try:
            contract = Stock(symbol_for_ib(ticker), 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            action = 'BUY' if shares > 0 else 'SELL'
            order = MarketOrder(action, abs(shares))

            trade = self.ib.placeOrder(contract, order)
            logger.info(f"📊 Placed {action} order: {abs(shares)} shares of {ticker}")

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
# BSS CALCULATION (Breakout Strength Score)
# =============================================================================

def calculate_atr(prices, period=14):
    """Calculate ATR for a price series"""
    high = prices.rolling(window=2).max()
    low = prices.rolling(window=2).min()
    prev_close = prices.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr


def calculate_bss_metrics(ticker, poi_period=100, atr_period=14, k=2.0, ma_period=100):
    """
    Calculate BSS (Breakout Strength Score) metrics for a stock

    BSS = (Price - POI) / (k × ATR)
    Where POI = Point of Initiation (MA100)

    Args:
        ticker: Stock ticker
        poi_period: POI lookback (default: 100)
        atr_period: ATR lookback (default: 14)
        k: ATR multiplier (default: 2.0)
        ma_period: MA filter period (default: 100)

    Returns:
        dict with 'BSS', 'Above_MA', 'Close', or None if error
    """
    try:
        # Download data
        data_symbol = symbol_for_data(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=poi_period * 3)
        df = yf.download(data_symbol, start=start_date, end=end_date, progress=False, auto_adjust=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df is None or df.empty or len(df) < poi_period:
            logger.warning(f"Insufficient data for {ticker}: {len(df) if df is not None else 0} bars")
            return None

        # Calculate POI (Point of Initiation = MA100)
        df['POI'] = df['Close'].rolling(window=poi_period).mean()

        # Calculate ATR
        df['ATR'] = calculate_atr(df['Close'], period=atr_period)

        # Calculate BSS (Breakout Strength Score)
        df['BSS'] = (df['Close'] - df['POI']) / (k * df['ATR'])

        # MA filter (above MA100)
        df['MA'] = df['Close'].rolling(window=ma_period).mean()
        df['Above_MA'] = df['Close'] > df['MA']

        # Get latest values
        latest = df.iloc[-1]

        if pd.isna(latest['BSS']) or pd.isna(latest['Close']) or pd.isna(latest['MA']):
            logger.warning(f"Incomplete BSS data for {ticker} - skipping")
            return None

        return {
            'BSS': latest['BSS'],
            'Above_MA': latest['Above_MA'],
            'Close': latest['Close'],
            'ATR': latest['ATR'],
            'POI': latest['POI']
        }

    except Exception as e:
        logger.error(f"Error calculating BSS for {ticker}: {e}")
        return None


# =============================================================================
# REGIME CALCULATION
# =============================================================================

def get_spy_regime():
    """
    Calculate SPY regime using 3-tier classification

    Returns:
        'STRONG_BULL', 'WEAK_BULL', or 'BEAR'
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=300)

        spy = yf.download('SPY', start=start_date, end=end_date, progress=False, auto_adjust=True)

        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)

        spy['MA50'] = spy['Close'].rolling(window=50).mean()
        spy['MA200'] = spy['Close'].rolling(window=200).mean()
        latest = spy.iloc[-1]

        # Three-tier regime (matches backtest)
        if latest['Close'] > latest['MA200'] and latest['Close'] > latest['MA50']:
            regime = 'STRONG_BULL'
        elif latest['Close'] > latest['MA200']:
            regime = 'WEAK_BULL'
        else:
            regime = 'BEAR'

        logger.info(f"📊 SPY Regime: {regime} (Price: ${latest['Close']:.2f}, MA50: ${latest['MA50']:.2f}, MA200: ${latest['MA200']:.2f})")

        return regime

    except Exception as e:
        logger.error(f"Error calculating SPY regime: {e}")
        return 'STRONG_BULL'  # Default


def get_sp500_tickers(num_stocks=100):
    """Get top S&P 500 stocks"""
    tickers = [
        # Tech (30)
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'ADBE', 'CRM',
        'ORCL', 'CSCO', 'ACN', 'AMD', 'INTC', 'IBM', 'QCOM', 'TXN', 'INTU', 'NOW',
        'AMAT', 'MU', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'NXPI', 'FTNT', 'PANW',
        # Finance (20)
        'BRK.B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'AXP', 'BLK',
        'C', 'SCHW', 'CB', 'SPGI', 'CME', 'PGR', 'MMC', 'AON', 'ICE', 'MCO',
        # Healthcare (20)
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
        'BSX', 'SYK', 'GILD', 'MDT', 'CI', 'REGN', 'VRTX', 'ZTS', 'CVS', 'HUM',
        # Consumer (20)
        'AMZN', 'HD', 'NKE', 'MCD', 'SBUX', 'TGT', 'LOW', 'DIS', 'BKNG', 'TJX',
        'ORLY', 'CMG', 'MAR', 'ROST', 'AZO', 'WMT', 'COST', 'PG', 'KO', 'PEP',
        # Energy & Industrials (10)
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'CAT', 'UNP', 'HON', 'UPS', 'BA',
    ]
    return tickers[:num_stocks]


# =============================================================================
# RANKING STOCKS BY BSS
# =============================================================================

def rank_stocks_by_bss(tickers, portfolio_size=7):
    """
    Rank stocks by BSS (Breakout Strength Score) and return top N

    Args:
        tickers: List of stock tickers
        portfolio_size: Number of top stocks to return

    Returns:
        List of dicts with 'Ticker', 'BSS', 'Close'
    """
    logger.info(f"📊 Calculating BSS for {len(tickers)} stocks...")

    # Get SPY BSS for relative strength filter
    spy_metrics = calculate_bss_metrics('SPY')
    spy_bss = spy_metrics['BSS'] if spy_metrics else 0

    rankings = []
    for ticker in tickers:
        metrics = calculate_bss_metrics(ticker)

        if metrics is None:
            continue

        # Filters (same as backtest)
        if not metrics['Above_MA']:
            continue

        if metrics['BSS'] <= spy_bss:  # Relative strength filter
            continue

        rankings.append({
            'Ticker': ticker,
            'BSS': metrics['BSS'],
            'Close': metrics['Close'],
            'ATR': metrics['ATR'],
            'POI': metrics['POI']
        })

    # Sort by BSS descending
    rankings.sort(key=lambda x: x['BSS'], reverse=True)

    # Return top N
    top_stocks = rankings[:portfolio_size]

    logger.info(f"✅ Top {len(top_stocks)} BSS stocks:")
    for i, stock in enumerate(top_stocks, 1):
        logger.info(f"   {i}. {stock['Ticker']} - BSS: {stock['BSS']:.2f} (Price: ${stock['Close']:.2f}, POI: ${stock['POI']:.2f})")

    return top_stocks


# =============================================================================
# REBALANCING LOGIC
# =============================================================================

def should_rebalance_today():
    """Check if today is a rebalance day"""
    now = datetime.now()
    if now.month in LiveTradingConfig.REBALANCE_MONTHS and now.day == LiveTradingConfig.REBALANCE_DAY:
        if now.hour >= LiveTradingConfig.REBALANCE_HOUR:
            return True
    return False


def execute_rebalance(ibkr_conn):
    """Execute quarterly portfolio rebalance using BSS"""
    logger.info("=" * 80)
    logger.info("🔄 STARTING QUARTERLY REBALANCE (BSS STRATEGY)")
    logger.info("=" * 80)

    # 1. Check regime
    regime = get_spy_regime()

    if regime == 'STRONG_BULL':
        portfolio_size = LiveTradingConfig.STRONG_BULL_POSITIONS
    elif regime == 'WEAK_BULL':
        portfolio_size = LiveTradingConfig.WEAK_BULL_POSITIONS
    else:  # BEAR
        portfolio_size = LiveTradingConfig.BEAR_MARKET_POSITIONS

    logger.info(f"📊 Regime: {regime} → Target positions: {portfolio_size}")

    # 2. Handle BEAR market (switch to GLD)
    if portfolio_size == 0:
        logger.info(f"🐻 BEAR MARKET - Switching to 100% {LiveTradingConfig.BEAR_MARKET_ASSET}")

        current_positions = ibkr_conn.get_positions()

        # Exit all stock positions
        for ticker, shares in current_positions.items():
            if ticker != LiveTradingConfig.BEAR_MARKET_ASSET and shares > 0:
                logger.info(f"   Exiting {ticker}: {shares} shares")
                ibkr_conn.place_order(ticker, -shares)

        # Calculate GLD position
        account_value = ibkr_conn.get_account_value()
        gld_price = ibkr_conn.get_current_price(LiveTradingConfig.BEAR_MARKET_ASSET)

        if gld_price and gld_price > 0:
            target_gld_shares = int((account_value * LiveTradingConfig.BEAR_ALLOCATION) / gld_price)
            current_gld_shares = current_positions.get(LiveTradingConfig.BEAR_MARKET_ASSET, 0)
            gld_delta = target_gld_shares - current_gld_shares

            if gld_delta != 0:
                logger.info(f"   {LiveTradingConfig.BEAR_MARKET_ASSET}: Target {target_gld_shares} shares (currently {current_gld_shares})")
                ibkr_conn.place_order(LiveTradingConfig.BEAR_MARKET_ASSET, gld_delta)

        logger.info("✅ Rebalance complete - 100% GLD protection")
        return

    # 3. Get target positions (top N by BSS)
    tickers = get_sp500_tickers(LiveTradingConfig.NUM_STOCKS)
    top_stocks = rank_stocks_by_bss(tickers, portfolio_size)

    if not top_stocks:
        logger.warning("⚠️  No stocks qualified - staying in cash")
        return

    # 4. Get current positions
    current_positions = ibkr_conn.get_positions()
    account_value = ibkr_conn.get_account_value()
    logger.info(f"💰 Account Value: ${account_value:,.2f}")

    # 5. Calculate target shares (equal weight)
    priceable_stocks = []
    for stock in top_stocks:
        ticker = stock['Ticker']
        price = ibkr_conn.get_current_price(ticker)

        if price is None or price <= 0:
            logger.warning(f"⚠️  Skipping {ticker} - no price data")
            continue

        priceable_stocks.append({
            'ticker': ticker,
            'price': price,
            'bss': stock['BSS']
        })

    if not priceable_stocks:
        logger.warning("⚠️  No stocks have valid pricing")
        return

    allocation_per_stock = account_value / len(priceable_stocks)
    logger.info(f"📊 Allocation per stock: ${allocation_per_stock:,.2f} ({len(priceable_stocks)} stocks)")

    target_positions = {}
    for stock_info in priceable_stocks:
        ticker = stock_info['ticker']
        price = stock_info['price']
        shares = int(allocation_per_stock / price)

        if shares <= 0 or shares * price < LiveTradingConfig.MIN_POSITION_VALUE:
            logger.warning(f"⚠️  Skipping {ticker} - position too small")
            continue

        target_positions[ticker] = shares

    # 6. Execute trades
    logger.info("\n📋 TRADE PLAN:")
    logger.info("-" * 80)

    # Exit positions not in target (including GLD if we're back in stocks)
    for ticker in list(current_positions.keys()):
        if ticker not in target_positions:
            shares = current_positions[ticker]
            if shares > 0:
                logger.info(f"   EXIT: {ticker} ({shares} shares)")
                ibkr_conn.place_order(ticker, -shares)

    # Refresh positions
    current_positions = ibkr_conn.get_positions()

    # Adjust positions
    for ticker, target_shares in target_positions.items():
        current_shares = current_positions.get(ticker, 0)
        delta = target_shares - current_shares

        if delta > 0:
            logger.info(f"   BUY: {ticker} ({delta} shares)")
            ibkr_conn.place_order(ticker, delta)
        elif delta < 0:
            logger.info(f"   SELL: {ticker} ({abs(delta)} shares)")
            ibkr_conn.place_order(ticker, delta)
        else:
            logger.info(f"   HOLD: {ticker} ({current_shares} shares)")

    # Final positions
    final_positions = ibkr_conn.get_positions()
    live_positions = {t: s for t, s in final_positions.items() if s > 0}

    logger.info("\n🏁 FINAL POSITIONS:")
    for ticker in sorted(live_positions):
        logger.info(f"   {ticker}: {live_positions[ticker]} shares")

    logger.info(f"\nTotal holdings: {len(live_positions)} (target {LiveTradingConfig.PORTFOLIO_SIZE})")
    logger.info("\n✅ Rebalance complete!")
    logger.info("=" * 80)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main(force_rebalance=False):
    """Main entry point for BSS live trading system"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 NICK RADGE MOMENTUM (BSS) - LIVE TRADING")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'DRY RUN 🧪' if LiveTradingConfig.DRY_RUN else 'LIVE TRADING 💰'}")
    logger.info(f"Strategy: BSS (Breakout Strength Score)")
    logger.info(f"Expected: +217% over 5 years (vs +166% for ROC)")

    # Connect to IBKR
    ibkr = IBKRConnection(LiveTradingConfig)

    if not ibkr.connect():
        logger.error("❌ Cannot proceed without IBKR connection")
        return

    try:
        if force_rebalance or should_rebalance_today():
            if force_rebalance:
                logger.info("🧪 FORCED REBALANCE - Testing BSS quarterly rebalance logic")
            else:
                logger.info("📅 Today is a rebalance day!")
            execute_rebalance(ibkr)
        else:
            # Daily monitoring (regime changes)
            logger.info("📊 Daily monitoring - checking regime")
            current_regime = get_spy_regime()

            current_positions = ibkr_conn.get_positions()
            num_positions = len([s for s in current_positions.values() if s > 0])

            # Determine previous regime
            if num_positions >= LiveTradingConfig.STRONG_BULL_POSITIONS:
                previous_regime = 'STRONG_BULL'
            elif num_positions >= LiveTradingConfig.WEAK_BULL_POSITIONS:
                previous_regime = 'WEAK_BULL'
            else:
                previous_regime = 'BEAR'

            logger.info(f"   Previous regime: {previous_regime} ({num_positions} positions)")
            logger.info(f"   Current regime: {current_regime}")

            # Regime recovery: BEAR → BULL
            if previous_regime == 'BEAR' and current_regime in ['WEAK_BULL', 'STRONG_BULL']:
                logger.info("🚀 REGIME RECOVERY: BEAR → BULL - Re-entering immediately!")
                execute_rebalance(ibkr)
            # Regime deterioration: BULL → BEAR
            elif previous_regime in ['STRONG_BULL', 'WEAK_BULL'] and current_regime == 'BEAR':
                logger.info("🐻 REGIME CHANGE: BULL → BEAR - Switching to GLD!")
                execute_rebalance(ibkr)
            # Regime shift within BULL
            elif (previous_regime == 'STRONG_BULL' and current_regime == 'WEAK_BULL') or \
                 (previous_regime == 'WEAK_BULL' and current_regime == 'STRONG_BULL'):
                logger.info(f"⚠️  Regime shift: {previous_regime} → {current_regime}")
                execute_rebalance(ibkr)
            else:
                logger.info("✅ Daily check complete - no action needed")

    except Exception as e:
        logger.error(f"❌ Error during execution: {e}", exc_info=True)

    finally:
        ibkr.disconnect()
        logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    import sys

    force_rebalance = '--force-rebalance' in sys.argv or '--test' in sys.argv

    if force_rebalance:
        logger.info("⚠️  FORCE REBALANCE MODE - Testing BSS strategy")

    main(force_rebalance=force_rebalance)
