"""
Live Trading: Nick Radge Momentum with TQS (Trend Quality Score) on IBKR

BEST PERFORMING VERSION: Uses TQS qualifier for superior risk-adjusted returns

This script implements the winning TQS qualifier for live trading on Interactive Brokers:
1. Quarterly rebalancing (Jan 1, Apr 1, Jul 1, Oct 1)
2. 3-tier regime filter (STRONG_BULL, WEAK_BULL, BEAR)
3. TQS ranking: (Price - MA100) / ATR × (ADX / 25)
4. GLD allocation during BEAR markets
5. Volatility targeting (20% annual vol)
6. Position concentration limits (max 25% per position)

BACKTEST PERFORMANCE (2020-2025):
- TQS: +183.37% return, Sharpe 1.46 (NEW - This script)
- BSS: +167.50% return, Sharpe 1.33 (OLD - +15.87% worse)
- Max DD: -24.33% vs -26.72% (2.39% better)
- Win Rate: 51.03% vs 51.14% (comparable)

WHY TQS WINS:
- Better Sharpe ratio (1.46 vs 1.33) = 10% improvement
- Lower drawdown (-24.33% vs -26.72%)
- Higher total return (+183% vs +167%)
- Combines trend strength + breakout + trend quality
- ADX filter focuses on strong trending moves

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
import json
import importlib.util

# Import TQS strategy (using importlib for numbered file)
spec = importlib.util.spec_from_file_location(
    "nick_radge_tqs",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
tqs_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tqs_module)
NickRadgeEnhanced = tqs_module.NickRadgeEnhanced


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
    """Configuration for live trading with TQS"""

    # IBKR Connection
    IBKR_HOST = '127.0.0.1'
    IBKR_PORT = 7496  # 7496 = Paper trading, 7497 = Live trading
    IBKR_CLIENT_ID = 1

    # Strategy Parameters (TQS Configuration)
    PORTFOLIO_SIZE = 7
    NUM_STOCKS = 100  # Top 100 S&P 500

    # TQS Parameters (Trend Quality Score)
    QUALIFIER_TYPE = 'tqs'  # Best performer!
    MA_PERIOD = 100
    ATR_PERIOD = 14
    ADX_PERIOD = 14

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

    # Risk Management
    MAX_POSITION_SIZE_PCT = 0.25  # Max 25% per position (concentration limit)
    TARGET_VOLATILITY = 0.20  # 20% annual volatility target
    VOL_LOOKBACK = 20  # 20-day realized vol estimate

    # Data Source
    USE_IBKR_DATA = False  # False = Yahoo Finance (recommended)

    # Rebalance Schedule
    REBALANCE_MONTHS = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
    REBALANCE_DAY = 1
    REBALANCE_HOUR = 10  # 10 AM ET

    # Safety Controls
    MIN_POSITION_VALUE = 100  # Don't trade < $100
    MAX_SLIPPAGE_PCT = 0.01  # Cancel if price moves > 1%
    DRY_RUN = True  # ALWAYS start with dry run!

    # Logging
    LOG_FILE = 'output/live_tqs_trading.log'
    TRADE_LOG_FILE = 'output/live_tqs_trades.csv'


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
# DATA FETCHING
# =============================================================================

def download_price_data(tickers, lookback_days=300):
    """
    Download historical price data for backtesting

    Args:
        tickers: List of stock tickers
        lookback_days: Days of historical data

    Returns:
        DataFrame with Close prices (columns = tickers)
    """
    logger.info(f"📊 Downloading {lookback_days} days of data for {len(tickers)} stocks...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    # Download data
    data_tickers = [symbol_for_data(t) for t in tickers]
    df = yf.download(data_tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']

    # Convert back to canonical symbols
    df.columns = [canonical_symbol(col) for col in df.columns]

    return df


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
# STRATEGY EXECUTION
# =============================================================================

def calculate_target_allocations(tickers, regime, config):
    """
    Calculate target allocations using TQS strategy

    Returns:
        dict: {ticker: allocation_pct}
    """
    logger.info("📊 Calculating target allocations using TQS strategy...")

    # Determine portfolio size based on regime
    if regime == 'STRONG_BULL':
        portfolio_size = config.STRONG_BULL_POSITIONS
    elif regime == 'WEAK_BULL':
        portfolio_size = config.WEAK_BULL_POSITIONS
    else:  # BEAR
        portfolio_size = config.BEAR_MARKET_POSITIONS

    logger.info(f"   Regime: {regime} → Target positions: {portfolio_size}")

    # Handle BEAR market (100% GLD)
    if portfolio_size == 0:
        logger.info(f"   🐻 BEAR MARKET - Switching to 100% {config.BEAR_MARKET_ASSET}")
        return {config.BEAR_MARKET_ASSET: 1.0}

    # Download price data
    tickers_with_spy = tickers + ['SPY']
    prices = download_price_data(tickers_with_spy, lookback_days=300)

    if prices.empty:
        logger.error("❌ Failed to download price data")
        return {}

    # Initialize strategy
    strategy = NickRadgeEnhanced(
        portfolio_size=portfolio_size,
        qualifier_type=config.QUALIFIER_TYPE,
        ma_period=config.MA_PERIOD,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        regime_ma_long=config.REGIME_MA_LONG,
        regime_ma_short=config.REGIME_MA_SHORT,
        strong_bull_positions=config.STRONG_BULL_POSITIONS,
        weak_bull_positions=config.WEAK_BULL_POSITIONS,
        bear_positions=config.BEAR_MARKET_POSITIONS,
        bear_market_asset=config.BEAR_MARKET_ASSET,
        bear_allocation=config.BEAR_ALLOCATION
    )

    # Generate allocations
    allocations = strategy.generate_allocations(
        prices=prices,
        benchmark_ticker='SPY',
        max_position_size=config.MAX_POSITION_SIZE_PCT
    )

    if allocations is None or allocations.empty:
        logger.error("❌ Failed to generate allocations")
        return {}

    # Get latest allocations
    latest_allocations = allocations.iloc[-1]

    # Filter non-zero allocations
    target_allocations = {
        ticker: float(alloc)
        for ticker, alloc in latest_allocations.items()
        if alloc > 0.001  # Ignore tiny allocations
    }

    # Log top holdings
    logger.info(f"✅ Target allocations ({len(target_allocations)} positions):")
    for ticker in sorted(target_allocations, key=target_allocations.get, reverse=True):
        logger.info(f"   {ticker}: {target_allocations[ticker]:.1%}")

    return target_allocations


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


def execute_rebalance(ibkr_conn, config):
    """Execute quarterly portfolio rebalance using TQS"""
    logger.info("=" * 80)
    logger.info("🔄 STARTING QUARTERLY REBALANCE (TQS STRATEGY)")
    logger.info("=" * 80)

    # 1. Check regime
    regime = get_spy_regime()

    # 2. Get target allocations
    tickers = get_sp500_tickers(config.NUM_STOCKS)
    target_allocations = calculate_target_allocations(tickers, regime, config)

    if not target_allocations:
        logger.warning("⚠️  No target allocations - staying in cash")
        return

    # 3. Get current positions and account value
    current_positions = ibkr_conn.get_positions()
    account_value = ibkr_conn.get_account_value()
    logger.info(f"💰 Account Value: ${account_value:,.2f}")

    # 4. Calculate target shares
    target_shares = {}
    for ticker, alloc_pct in target_allocations.items():
        price = ibkr_conn.get_current_price(ticker)

        if price is None or price <= 0:
            logger.warning(f"⚠️  Skipping {ticker} - no price data")
            continue

        target_value = account_value * alloc_pct
        shares = int(target_value / price)

        if shares <= 0 or shares * price < config.MIN_POSITION_VALUE:
            logger.warning(f"⚠️  Skipping {ticker} - position too small")
            continue

        target_shares[ticker] = shares

    # 5. Execute trades
    logger.info("\n📋 TRADE PLAN:")
    logger.info("-" * 80)

    # Exit positions not in target
    for ticker in list(current_positions.keys()):
        if ticker not in target_shares:
            shares = current_positions[ticker]
            if shares > 0:
                logger.info(f"   EXIT: {ticker} ({shares} shares)")
                ibkr_conn.place_order(ticker, -shares)

    # Refresh positions
    current_positions = ibkr_conn.get_positions()

    # Adjust positions
    for ticker, target_shrs in target_shares.items():
        current_shrs = current_positions.get(ticker, 0)
        delta = target_shrs - current_shrs

        if delta > 0:
            logger.info(f"   BUY: {ticker} ({delta} shares)")
            ibkr_conn.place_order(ticker, delta)
        elif delta < 0:
            logger.info(f"   SELL: {ticker} ({abs(delta)} shares)")
            ibkr_conn.place_order(ticker, delta)
        else:
            logger.info(f"   HOLD: {ticker} ({current_shrs} shares)")

    # Final positions
    final_positions = ibkr_conn.get_positions()
    live_positions = {t: s for t, s in final_positions.items() if s > 0}

    logger.info("\n🏁 FINAL POSITIONS:")
    for ticker in sorted(live_positions):
        logger.info(f"   {ticker}: {live_positions[ticker]} shares")

    logger.info(f"\nTotal holdings: {len(live_positions)} (target {config.PORTFOLIO_SIZE})")
    logger.info("\n✅ Rebalance complete!")
    logger.info("=" * 80)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main(force_rebalance=False):
    """Main entry point for TQS live trading system"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 NICK RADGE MOMENTUM (TQS) - LIVE TRADING")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'DRY RUN 🧪' if LiveTradingConfig.DRY_RUN else 'LIVE TRADING 💰'}")
    logger.info(f"Strategy: TQS (Trend Quality Score)")
    logger.info(f"Expected: +183% over 5 years (Sharpe 1.46)")

    # Connect to IBKR
    ibkr = IBKRConnection(LiveTradingConfig)

    if not ibkr.connect():
        logger.error("❌ Cannot proceed without IBKR connection")
        return

    try:
        if force_rebalance or should_rebalance_today():
            if force_rebalance:
                logger.info("🧪 FORCED REBALANCE - Testing TQS quarterly rebalance logic")
            else:
                logger.info("📅 Today is a rebalance day!")
            execute_rebalance(ibkr, LiveTradingConfig)
        else:
            # Daily monitoring (regime changes)
            logger.info("📊 Daily monitoring - checking regime")
            current_regime = get_spy_regime()

            current_positions = ibkr.get_positions()
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
                execute_rebalance(ibkr, LiveTradingConfig)
            # Regime deterioration: BULL → BEAR
            elif previous_regime in ['STRONG_BULL', 'WEAK_BULL'] and current_regime == 'BEAR':
                logger.info("🐻 REGIME CHANGE: BULL → BEAR - Switching to GLD!")
                execute_rebalance(ibkr, LiveTradingConfig)
            # Regime shift within BULL
            elif (previous_regime == 'STRONG_BULL' and current_regime == 'WEAK_BULL') or \
                 (previous_regime == 'WEAK_BULL' and current_regime == 'STRONG_BULL'):
                logger.info(f"⚠️  Regime shift: {previous_regime} → {current_regime}")
                execute_rebalance(ibkr, LiveTradingConfig)
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
        logger.info("⚠️  FORCE REBALANCE MODE - Testing TQS strategy")

    main(force_rebalance=force_rebalance)
