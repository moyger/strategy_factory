"""
================================================================================
NICK RADGE MOMENTUM STRATEGY - PYTHON IMPLEMENTATION
================================================================================

Based on Nick Radge's "Unholy Grails" momentum trading system.

Strategy Overview:
------------------
1. Universe: S&P 500 stocks
2. Ranking: 100-day Rate of Change (ROC)
3. Portfolio: Hold top 20 momentum stocks
4. Rebalance: Weekly (every Monday)
5. Position Sizing: ATR-based risk parity (0.5% risk per position)
6. Exit: Drop out of top 20, OR 3x ATR trailing stop, OR below 100-day MA

Author: Built with Claude Code
Date: 2025-10-02
================================================================================
"""

# =============================================================================
# SECTION 1: IMPORTS
# =============================================================================
print("=" * 80)
print("NICK RADGE MOMENTUM STRATEGY BACKTEST")
print("=" * 80)
print("\n📦 Loading libraries...")

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
pd.set_option('display.float_format', '{:.2f}'.format)
plt.style.use('seaborn-v0_8-darkgrid')

print("✅ All libraries loaded successfully!\n")


# =============================================================================
# SECTION 2: CONFIGURATION PARAMETERS
# =============================================================================
print("⚙️  Setting up strategy parameters...\n")

class StrategyConfig:
    """
    Configuration parameters for the momentum strategy.

    Adjust these to test different variations of the strategy.
    """

    # Universe Selection
    NUM_TEST_STOCKS = 50  # Start with 50 stocks for speed (set to 500 for full S&P)

    # Momentum Parameters
    ROC_PERIOD = 100  # Rate of Change lookback period (days)
    MA_PERIOD = 100   # Moving Average trend filter (days)
    ATR_PERIOD = 20   # ATR volatility calculation period (days)

    # Portfolio Construction
    PORTFOLIO_SIZE = 7  # Number of positions to hold simultaneously (OPTIMIZED: was 10, higher conviction)
    REBALANCE_FREQ = 'QS'  # Rebalance frequency ('QS' = Quarter Start - OPTIMIZED: was 'MS', reduces costs)
    USE_MOMENTUM_WEIGHTING = True  # Weight positions by momentum strength (OPTIMIZED)
    USE_RELATIVE_STRENGTH_FILTER = True  # Only buy stocks outperforming SPY (OPTIMIZED)

    # Risk Management
    RISK_PER_POSITION = 0.01  # 1.0% risk per position (1.0% * 10 positions = 10% total portfolio risk)
    ATR_STOP_MULTIPLIER = 3.0  # Stop loss = 3x ATR below entry
    USE_TRAILING_STOP = False  # Disable trailing stop (hurts momentum strategy)
    TRAILING_STOP_PCT = 0.15   # 15% trailing stop from peak price
    INITIAL_CAPITAL = 5000  # Starting capital ($5k)

    # Market Regime Filter - Three Tier System
    USE_REGIME_FILTER = True  # Enable/disable regime-based risk adjustment
    REGIME_INDICATOR = 'SPY'  # Use SPY as market benchmark
    REGIME_MA_PERIOD_LONG = 200   # 200-day MA for long-term regime
    REGIME_MA_PERIOD_SHORT = 50   # 50-day MA for short-term regime

    # Three-tier regime-based position adjustments
    STRONG_BULL_POSITIONS = 7    # SPY > 200 MA (strong uptrend) - OPTIMIZED: was 10
    WEAK_BULL_POSITIONS = 3      # SPY between 50 MA and 200 MA (caution) - OPTIMIZED: was 5
    BEAR_MARKET_POSITIONS = 0    # SPY < 50 MA (bear market - 100% cash)

    # Transaction Costs (Realistic Modeling)
    ENABLE_TRANSACTION_COSTS = True  # Enable/disable cost modeling

    # Commission Structure
    COMMISSION_TYPE = 'per_share'  # 'per_share', 'per_trade', or 'percent'
    COMMISSION_PER_SHARE = 0.005   # $0.005 per share (Interactive Brokers-like)
    COMMISSION_MIN = 1.00          # Minimum $1 per trade
    COMMISSION_MAX = 0.005         # Max 0.5% of trade value (for percent mode)

    # Slippage (Market Impact)
    SLIPPAGE_BPS = 5               # 5 basis points = 0.05% slippage per trade
    # Note: Large cap stocks typically 2-5 bps, mid cap 5-10 bps, small cap 10-20 bps

    # Backtest Period
    START_DATE = datetime.now() - timedelta(days=365*5)  # 5 years of data
    END_DATE = datetime.now()

    # Output
    SAVE_RESULTS = True
    OUTPUT_DIR = 'output/momentum/'

config = StrategyConfig()

print(f"📊 Portfolio Size: {config.PORTFOLIO_SIZE} positions")
print(f"📅 Backtest Period: {config.START_DATE.date()} to {config.END_DATE.date()}")
print(f"💰 Initial Capital: ${config.INITIAL_CAPITAL:,.0f}")
print(f"🎯 Risk per Position: {config.RISK_PER_POSITION*100:.2f}%")
print()


# =============================================================================
# SECTION 3: DATA ACQUISITION
# =============================================================================
print("=" * 80)
print("SECTION 3: DOWNLOADING STOCK DATA")
print("=" * 80)

def get_sp500_tickers(num_stocks=None):
    """
    Fetch current S&P 500 tickers (using hardcoded list for reliability).

    Args:
        num_stocks: Number of stocks to return (None = all)

    Returns:
        List of ticker symbols
    """
    print("\n📥 Loading S&P 500 component list...")

    # Top S&P 500 stocks (mega-caps + diversified sectors)
    tickers = [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
        'CRM', 'AMD', 'INTC', 'CSCO', 'QCOM', 'INTU', 'NOW', 'AMAT', 'MU', 'PLTR',
        # Finance
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW', 'AXP', 'SPGI',
        # Healthcare
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
        # Consumer
        'WMT', 'HD', 'MCD', 'NKE', 'COST', 'SBUX', 'TGT', 'LOW', 'DIS', 'CMCSA',
    ]

    if num_stocks and num_stocks < len(tickers):
        tickers = tickers[:num_stocks]

    print(f"✅ Loaded {len(tickers)} S&P 500 tickers")
    return tickers


def download_market_regime_data(ticker, start_date, end_date, ma_period_long, ma_period_short):
    """
    Download market regime indicator (e.g., SPY) and calculate three-tier trend.

    Args:
        ticker: Market index ticker (e.g., 'SPY')
        start_date: Start date
        end_date: End date
        ma_period_long: Long-term MA period (e.g., 200 days)
        ma_period_short: Short-term MA period (e.g., 50 days)

    Returns:
        DataFrame with Close, MA200, MA50, and Regime columns
    """
    print(f"\n📊 Downloading market regime indicator ({ticker})...")

    # Add extra lookback for MA calculation (use longer period)
    lookback_start = start_date - timedelta(days=ma_period_long * 2)

    df = yf.download(ticker, start=lookback_start, end=end_date, progress=False)

    if df.empty:
        print(f"⚠️  Warning: Could not download {ticker}. Regime filter disabled.")
        return None

    # Flatten multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Calculate both MAs
    close_series = df['Close']
    df['MA200'] = close_series.rolling(window=ma_period_long).mean()
    df['MA50'] = close_series.rolling(window=ma_period_short).mean()

    # Three-tier regime classification
    def classify_regime(row):
        if pd.isna(row['MA200']) or pd.isna(row['MA50']):
            return None

        if row['Close'] > row['MA200']:
            return 'STRONG_BULL'  # Above 200 MA = strong bull
        elif row['Close'] > row['MA50']:
            return 'WEAK_BULL'    # Between 50 MA and 200 MA = weak bull
        else:
            return 'BEAR'         # Below 50 MA = bear

    df['Regime'] = df.apply(classify_regime, axis=1)

    # Drop NaN values
    df = df.dropna()

    # Filter to requested date range
    df = df[df.index >= start_date]

    print(f"✅ Market regime data loaded ({len(df)} days)")
    return df


def download_stock_data(tickers, start_date, end_date):
    """
    Download historical price data for multiple tickers.

    Args:
        tickers: List of ticker symbols
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        Dictionary of DataFrames (one per ticker)
    """
    print(f"\n📊 Downloading {len(tickers)} stocks from {start_date.date()} to {end_date.date()}...")
    print("⏳ This may take 2-3 minutes...\n")

    # Download all tickers at once
    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,  # Adjust for splits and dividends
        progress=True
    )

    # Reorganize data by ticker (yfinance returns multi-index DataFrame)
    stock_data = {}

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                # Single ticker case
                df = data.copy()
            else:
                # Multiple tickers case
                df = pd.DataFrame({
                    'Open': data['Open'][ticker],
                    'High': data['High'][ticker],
                    'Low': data['Low'][ticker],
                    'Close': data['Close'][ticker],
                    'Volume': data['Volume'][ticker]
                })

            # Drop rows with NaN (missing data)
            df = df.dropna()

            # Only keep stocks with sufficient data
            if len(df) >= config.ROC_PERIOD + 50:  # Need at least 150 days
                stock_data[ticker] = df
        except Exception as e:
            print(f"⚠️  Skipping {ticker}: {str(e)}")

    print(f"\n✅ Successfully downloaded {len(stock_data)} stocks with sufficient data")
    return stock_data


def get_stock_to_sector_mapping():
    """
    Map stocks to their corresponding sectors (based on top 50 S&P 500 stocks).

    Returns:
        Dictionary mapping ticker symbol to sector ETF (XLE, XLF, etc.)
    """
    stock_sectors = {
        # Technology (XLK)
        'AAPL': 'XLK', 'MSFT': 'XLK', 'NVDA': 'XLK', 'GOOGL': 'XLK', 'META': 'XLK',
        'TSLA': 'XLK', 'AVGO': 'XLK', 'ADBE': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK',
        'CSCO': 'XLK', 'ACN': 'XLK', 'AMD': 'XLK', 'INTC': 'XLK', 'IBM': 'XLK',
        'QCOM': 'XLK', 'TXN': 'XLK', 'INTU': 'XLK',

        # Financials (XLF)
        'BRK.B': 'XLF', 'JPM': 'XLF', 'V': 'XLF', 'MA': 'XLF', 'BAC': 'XLF',
        'WFC': 'XLF', 'MS': 'XLF', 'GS': 'XLF', 'AXP': 'XLF', 'BLK': 'XLF',

        # Healthcare (XLV)
        'UNH': 'XLV', 'JNJ': 'XLV', 'LLY': 'XLV', 'ABBV': 'XLV', 'MRK': 'XLV',
        'TMO': 'XLV', 'ABT': 'XLV', 'PFE': 'XLV', 'DHR': 'XLV', 'AMGN': 'XLV',

        # Consumer Discretionary (XLY)
        'AMZN': 'XLY', 'HD': 'XLY', 'NKE': 'XLY', 'MCD': 'XLY', 'SBUX': 'XLY',
        'TGT': 'XLY', 'LOW': 'XLY', 'DIS': 'XLY',

        # Consumer Staples (XLP)
        'WMT': 'XLP', 'COST': 'XLP', 'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP',

        # Communication Services (mapped to XLY as proxy)
        'GOOG': 'XLY', 'NFLX': 'XLY', 'CMCSA': 'XLY',

        # Industrials (XLI)
        'BA': 'XLI', 'CAT': 'XLI', 'GE': 'XLI', 'UPS': 'XLI',

        # Energy (XLE)
        'XOM': 'XLE', 'CVX': 'XLE',

        # Utilities (XLU) - if any in top 50
        # Materials (XLB) - if any in top 50
    }

    return stock_sectors


def download_sector_etf_data(start_date, end_date):
    """
    Download sector ETF data for sector weakness analysis.

    Args:
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        Dictionary of DataFrames (one per sector ETF)
    """
    print(f"\n📊 Downloading sector ETF data...")

    sector_etfs = {
        'XLE': 'Energy',
        'XLF': 'Financials',
        'XLI': 'Industrials',
        'XLK': 'Technology',
        'XLV': 'Healthcare',
        'XLY': 'Consumer Discretionary',
        'XLP': 'Consumer Staples',
        'XLU': 'Utilities',
        'XLB': 'Materials'
    }

    tickers = list(sector_etfs.keys())

    # Download all sector ETFs at once
    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False
    )

    # Reorganize data by ticker
    sector_data = {}

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = pd.DataFrame({
                    'Open': data['Open'][ticker],
                    'High': data['High'][ticker],
                    'Low': data['Low'][ticker],
                    'Close': data['Close'][ticker],
                    'Volume': data['Volume'][ticker]
                })

            df = df.dropna()

            if len(df) >= 100:  # Need at least 100 days for ROC
                sector_data[ticker] = df
                print(f"  ✅ {ticker} ({sector_etfs[ticker]}): {len(df)} days")
        except Exception as e:
            print(f"  ⚠️  Skipping {ticker}: {str(e)}")

    print(f"\n✅ Successfully downloaded {len(sector_data)}/9 sector ETFs")
    return sector_data


# Download the data
tickers = get_sp500_tickers(num_stocks=config.NUM_TEST_STOCKS)
stock_data = download_stock_data(tickers, config.START_DATE, config.END_DATE)

# Download sector ETF data for weakness analysis
sector_data = download_sector_etf_data(config.START_DATE, config.END_DATE)

# Download market regime indicator if enabled
regime_data = None
if config.USE_REGIME_FILTER:
    regime_data = download_market_regime_data(
        config.REGIME_INDICATOR,
        config.START_DATE,
        config.END_DATE,
        config.REGIME_MA_PERIOD_LONG,
        config.REGIME_MA_PERIOD_SHORT
    )

    if regime_data is not None:
        # Show regime summary
        regime_counts = regime_data['Regime'].value_counts()
        total_days = len(regime_data)
        print(f"\n📊 Market Regime Summary:")
        for regime, count in regime_counts.items():
            pct = (count / total_days) * 100
            print(f"   {regime} Market: {count} days ({pct:.1f}%)")

# Download benchmark data (SPY) for comparison
print("\n📊 Downloading benchmark (SPY) for comparison...")
benchmark_data = yf.download('SPY', start=config.START_DATE, end=config.END_DATE, progress=False)
if isinstance(benchmark_data.columns, pd.MultiIndex):
    benchmark_data.columns = benchmark_data.columns.get_level_values(0)
benchmark_data = benchmark_data.dropna()
# Calculate ROC for SPY (for relative strength comparison)
benchmark_data['ROC'] = ((benchmark_data['Close'] - benchmark_data['Close'].shift(config.ROC_PERIOD)) /
                         benchmark_data['Close'].shift(config.ROC_PERIOD)) * 100
benchmark_data = benchmark_data.dropna()
print(f"✅ Benchmark data loaded ({len(benchmark_data)} days)")

# Download SQQQ data for bear market hedging
print("\n📊 Downloading SQQQ (3X inverse QQQ) for bear market hedge...")
sqqq_data = yf.download('SQQQ', start=config.START_DATE, end=config.END_DATE, progress=False)
if isinstance(sqqq_data.columns, pd.MultiIndex):
    sqqq_data.columns = sqqq_data.columns.get_level_values(0)
sqqq_data = sqqq_data.dropna()
print(f"✅ SQQQ data loaded ({len(sqqq_data)} days)")


# =============================================================================
# SECTION 4: TECHNICAL INDICATORS
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 4: CALCULATING MOMENTUM INDICATORS")
print("=" * 80)

def calculate_indicators(df, roc_period=100, ma_period=100, atr_period=20):
    """
    Calculate momentum, trend, and volatility indicators.

    Indicators:
    -----------
    1. ROC (Rate of Change): Momentum measure
       Formula: ((Close_today - Close_N_days_ago) / Close_N_days_ago) * 100

    2. SMA (Simple Moving Average): Trend filter
       Formula: Average of last N closing prices

    3. ATR (Average True Range): Volatility measure
       Formula: Average of True Range over N days
       True Range = Max of (High-Low, |High-PrevClose|, |Low-PrevClose|)

    Args:
        df: DataFrame with OHLC data
        roc_period: ROC lookback period
        ma_period: SMA period
        atr_period: ATR period

    Returns:
        DataFrame with added indicator columns
    """
    data = df.copy()

    # 1. Rate of Change (Momentum)
    data['ROC'] = ((data['Close'] - data['Close'].shift(roc_period)) /
                   data['Close'].shift(roc_period)) * 100

    # 2. Simple Moving Average (Trend Filter)
    data['SMA'] = data['Close'].rolling(window=ma_period).mean()

    # 3. Average True Range (Volatility)
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift())
    low_close = abs(data['Low'] - data['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['ATR'] = true_range.rolling(window=atr_period).mean()

    # 4. Trend Filter (Boolean)
    data['Above_MA'] = data['Close'] > data['SMA']

    # Drop NaN rows
    data = data.dropna()

    return data


# Calculate indicators for all stocks
print("\n📈 Calculating ROC, SMA, and ATR for all stocks...")

for ticker in stock_data.keys():
    stock_data[ticker] = calculate_indicators(
        stock_data[ticker],
        roc_period=config.ROC_PERIOD,
        ma_period=config.MA_PERIOD,
        atr_period=config.ATR_PERIOD
    )

print(f"✅ Indicators calculated for {len(stock_data)} stocks")

# Show sample indicators for first stock
sample_ticker = list(stock_data.keys())[0]
print(f"\n📊 Sample indicators for {sample_ticker}:")
print(stock_data[sample_ticker][['Close', 'ROC', 'SMA', 'ATR', 'Above_MA']].tail(10))


# =============================================================================
# SECTION 5: MOMENTUM RANKING & PORTFOLIO CONSTRUCTION
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 5: RANKING STOCKS BY MOMENTUM")
print("=" * 80)

def rank_stocks_by_momentum(stock_data, date, portfolio_size=20, benchmark_data=None, use_relative_strength=False):
    """
    Rank all stocks by ROC and select top N.

    Rules:
    ------
    1. Only consider stocks above 100-day MA (trend filter)
    2. Optional: Only consider stocks outperforming SPY (relative strength filter)
    3. Rank by ROC (highest to lowest)
    4. Select top N stocks

    Args:
        stock_data: Dictionary of stock DataFrames
        date: Date to rank stocks
        portfolio_size: Number of top stocks to select
        benchmark_data: SPY DataFrame for relative strength comparison
        use_relative_strength: If True, only select stocks outperforming SPY

    Returns:
        List of (ticker, ROC, ATR) tuples for top momentum stocks
    """
    rankings = []

    # Get SPY ROC for comparison
    spy_roc = None
    if use_relative_strength and benchmark_data is not None and date in benchmark_data.index:
        spy_roc = benchmark_data.loc[date, 'ROC']

    for ticker, df in stock_data.items():
        # Check if date exists in data
        if date not in df.index:
            continue

        row = df.loc[date]

        # Only consider stocks above MA (trend filter)
        if not row['Above_MA']:
            continue

        # Relative strength filter: only stocks outperforming SPY
        if use_relative_strength and spy_roc is not None:
            if row['ROC'] <= spy_roc:
                continue

        # Store ticker, ROC, and ATR
        rankings.append({
            'Ticker': ticker,
            'ROC': row['ROC'],
            'ATR': row['ATR'],
            'Close': row['Close']
        })

    # Convert to DataFrame and sort by ROC
    rankings_df = pd.DataFrame(rankings)

    if len(rankings_df) == 0:
        return []

    rankings_df = rankings_df.sort_values('ROC', ascending=False)

    # Select top N
    top_stocks = rankings_df.head(portfolio_size)

    return top_stocks.to_dict('records')


def calculate_sector_weakness(sector_data, date, roc_period=100):
    """
    Calculate weakness (negative ROC) for each sector ETF.

    Args:
        sector_data: Dictionary of sector ETF DataFrames
        date: Date to calculate sector weakness
        roc_period: ROC calculation period (default 100 days)

    Returns:
        DataFrame with sector ETF tickers and their ROC, sorted by weakness (lowest ROC first)
    """
    sector_rankings = []

    for sector_etf, df in sector_data.items():
        if date not in df.index:
            continue

        # Calculate ROC if not already calculated
        if 'ROC' not in df.columns:
            df['ROC'] = ((df['Close'] / df['Close'].shift(roc_period)) - 1) * 100

        row = df.loc[date]

        if pd.notna(row['ROC']):
            sector_rankings.append({
                'Sector': sector_etf,
                'ROC': row['ROC']
            })

    if not sector_rankings:
        return pd.DataFrame()

    # Convert to DataFrame and sort by ROC (ascending = weakest first)
    sector_df = pd.DataFrame(sector_rankings)
    sector_df = sector_df.sort_values('ROC', ascending=True)

    return sector_df


def find_weakest_stocks_in_sectors(stock_data, stock_to_sector, weak_sectors, date, portfolio_size=7):
    """
    Find weakest stocks (lowest ROC) within the weakest sectors.

    Args:
        stock_data: Dictionary of stock DataFrames
        stock_to_sector: Dictionary mapping stock ticker to sector ETF
        weak_sectors: List of weak sector ETF tickers (e.g., ['XLE', 'XLF'])
        date: Date to find weak stocks
        portfolio_size: Number of stocks to short

    Returns:
        List of (ticker, ROC, ATR) tuples for weakest stocks
    """
    weak_stocks = []

    for ticker, df in stock_data.items():
        # Check if date exists
        if date not in df.index:
            continue

        # Get stock's sector
        stock_sector = stock_to_sector.get(ticker)

        # Only consider stocks in weak sectors
        if stock_sector not in weak_sectors:
            continue

        row = df.loc[date]

        # Only short stocks BELOW their MA (downtrend confirmation)
        if row.get('Above_MA', False):
            continue

        # Store ticker, ROC, ATR
        weak_stocks.append({
            'Ticker': ticker,
            'ROC': row['ROC'],
            'ATR': row['ATR'],
            'Close': row['Close'],
            'Sector': stock_sector
        })

    if not weak_stocks:
        return []

    # Convert to DataFrame and sort by ROC (ascending = weakest first)
    weak_df = pd.DataFrame(weak_stocks)
    weak_df = weak_df.sort_values('ROC', ascending=True)

    # Select bottom N stocks
    bottom_stocks = weak_df.head(portfolio_size)

    return bottom_stocks.to_dict('records')


# Test ranking on latest date
latest_date = stock_data[list(stock_data.keys())[0]].index[-1]
print(f"\n📅 Testing momentum ranking for {latest_date.date()}...")

top_momentum = rank_stocks_by_momentum(stock_data, latest_date, config.PORTFOLIO_SIZE)

print(f"\n🏆 Top {config.PORTFOLIO_SIZE} Momentum Stocks:")
print("-" * 80)
for i, stock in enumerate(top_momentum[:10], 1):
    print(f"{i:2d}. {stock['Ticker']:6s} | ROC: {stock['ROC']:6.2f}% | "
          f"Price: ${stock['Close']:7.2f} | ATR: ${stock['ATR']:5.2f}")

if len(top_momentum) > 10:
    print(f"... and {len(top_momentum) - 10} more")


# =============================================================================
# SECTION 6: POSITION SIZING (ATR-BASED)
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 6: CALCULATING POSITION SIZES")
print("=" * 80)

def calculate_position_size(portfolio_value, atr, risk_per_position=0.005, atr_multiplier=3.0):
    """
    Calculate position size using ATR-based risk parity.

    Formula:
    --------
    Position Size = (Portfolio Value × Risk%) / (ATR × ATR Multiplier)

    Logic:
    ------
    - We want to risk 0.5% of portfolio per position
    - Stop loss is 3× ATR below entry
    - So: Dollar Risk = Position Size × (3 × ATR)
    - Rearranging: Position Size = (Portfolio × 0.5%) / (3 × ATR)

    This ensures volatile stocks get smaller position sizes,
    and less volatile stocks get larger position sizes.
    All positions risk the same dollar amount!

    Args:
        portfolio_value: Current portfolio value
        atr: Stock's current ATR value
        risk_per_position: Risk as fraction of portfolio (0.005 = 0.5%)
        atr_multiplier: Stop loss distance in ATR units

    Returns:
        Number of shares to buy
    """
    # Dollar amount we're willing to risk on this position
    risk_dollars = portfolio_value * risk_per_position

    # Stop loss distance in dollars per share
    stop_distance = atr * atr_multiplier

    # Position size (shares)
    shares = int(risk_dollars / stop_distance)

    return max(shares, 0)  # Can't buy negative shares


# Example calculation
example_portfolio = config.INITIAL_CAPITAL
example_atr = 2.50

example_shares = calculate_position_size(
    example_portfolio,
    example_atr,
    config.RISK_PER_POSITION,
    config.ATR_STOP_MULTIPLIER
)

print(f"\n💡 Example Position Sizing:")
print(f"   Portfolio Value: ${example_portfolio:,.0f}")
print(f"   Stock ATR: ${example_atr:.2f}")
print(f"   Risk per Position: {config.RISK_PER_POSITION*100:.2f}%")
print(f"   Stop Distance: {config.ATR_STOP_MULTIPLIER}× ATR = ${example_atr * config.ATR_STOP_MULTIPLIER:.2f}")
print(f"   → Position Size: {example_shares:,} shares")
print(f"   → Dollar Risk: ${example_portfolio * config.RISK_PER_POSITION:,.2f}")


# =============================================================================
# SECTION 7: BACKTESTING ENGINE
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 7: RUNNING BACKTEST")
print("=" * 80)

class MomentumBacktester:
    """
    Backtest engine for Nick Radge momentum strategy.

    Process:
    --------
    1. On rebalance day (every Monday):
       - Rank all stocks by ROC
       - Select top 20 momentum stocks
       - Exit positions not in top 20
       - Enter new positions that entered top 20

    2. Every day:
       - Check trailing stops (3× ATR below highest price since entry)
       - Exit if stop hit or price drops below 100-day MA
    """

    def __init__(self, stock_data, config, regime_data=None, benchmark_data=None):
        self.stock_data = stock_data
        self.config = config
        self.regime_data = regime_data  # Market regime indicator
        self.benchmark_data = benchmark_data  # SPY data for relative strength

        # Portfolio state
        self.cash = config.INITIAL_CAPITAL
        self.positions = {}  # {ticker: {'shares': N, 'entry_price': P, 'highest_price': P}}
        self.portfolio_value = config.INITIAL_CAPITAL

        # Performance tracking
        self.equity_curve = []
        self.trades = []
        self.regime_changes = []  # Track regime transitions

        # Regime tracking for SQQQ confirmation
        self.consecutive_bear_days = 0  # Track consecutive BEAR days

        # Transaction cost tracking
        self.total_commissions = 0
        self.total_slippage = 0
        self.total_transaction_costs = 0

    def get_rebalance_dates(self):
        """Get list of rebalance dates, shifting to next business day if needed."""
        # Use first stock's date index as reference
        first_ticker = list(self.stock_data.keys())[0]
        available_dates = self.stock_data[first_ticker].index

        # Generate target rebalance dates
        target_dates = pd.date_range(
            start=available_dates[0],
            end=available_dates[-1],
            freq=self.config.REBALANCE_FREQ
        )

        # Shift to next available business day if target date is weekend/holiday
        rebalance_dates = []
        for target_date in target_dates:
            if target_date in available_dates:
                # Target date is a trading day - use it
                rebalance_dates.append(target_date)
            else:
                # Target date is weekend/holiday - find next business day
                next_dates = available_dates[available_dates > target_date]
                if len(next_dates) > 0:
                    next_business_day = next_dates[0]
                    # Avoid duplicates (e.g., if Feb 1 and Mar 1 both shift to same Monday)
                    if next_business_day not in rebalance_dates:
                        rebalance_dates.append(next_business_day)

        return rebalance_dates

    def run(self):
        """Execute the backtest."""
        print(f"\n🚀 Starting backtest...")
        print(f"   Strategy: Nick Radge Momentum")
        print(f"   Capital: ${self.config.INITIAL_CAPITAL:,.0f}")
        print(f"   Period: {self.config.START_DATE.date()} to {self.config.END_DATE.date()}")
        if self.config.USE_TRAILING_STOP:
            print(f"   Trailing Stop: {self.config.TRAILING_STOP_PCT*100:.0f}% from peak")
        print(f"\n⏳ Running simulation...\n")

        rebalance_dates = self.get_rebalance_dates()
        total_rebalances = len(rebalance_dates)

        # Get all trading dates for daily trailing stop checks
        first_ticker = list(self.stock_data.keys())[0]
        all_dates = self.stock_data[first_ticker].index

        rebalance_idx = 0
        last_regime = None

        for i, date in enumerate(all_dates):
            # Check current market regime
            current_regime = None
            if self.config.USE_REGIME_FILTER and self.regime_data is not None and date in self.regime_data.index:
                current_regime = self.regime_data.loc[date, 'Regime']

            # Track consecutive BEAR days for SQQQ confirmation
            if current_regime == 'BEAR':
                self.consecutive_bear_days += 1
            else:
                self.consecutive_bear_days = 0

            # Check if today is a rebalance date
            is_rebalance_date = rebalance_idx < len(rebalance_dates) and date == rebalance_dates[rebalance_idx]

            # Check if regime just changed from BEAR to BULL (opportunity to re-enter early)
            # Only check this if we're currently in cash (len(positions) == 0)
            regime_recovery = (last_regime == 'BEAR' and current_regime in ['WEAK_BULL', 'STRONG_BULL']
                              and len(self.positions) == 0)

            if is_rebalance_date or regime_recovery:
                # Progress indicator
                if is_rebalance_date:
                    if rebalance_idx % 10 == 0 or rebalance_idx == total_rebalances - 1:
                        print(f"   Progress: {rebalance_idx+1}/{total_rebalances} rebalance periods "
                              f"({(rebalance_idx+1)/total_rebalances*100:.1f}%) - Portfolio: ${self.portfolio_value:,.0f}")
                    rebalance_idx += 1
                elif regime_recovery:
                    print(f"   🔄 Regime recovery on {date.date()} - Re-entering positions early")

                # Rebalance portfolio
                self.rebalance(date)
            else:
                # Between rebalances: check trailing stops
                if self.config.USE_TRAILING_STOP and len(self.positions) > 0:
                    self.check_trailing_stops(date)

            # Update portfolio value daily (important for accurate equity tracking)
            self.update_portfolio_value(date)

            last_regime = current_regime

            # Track equity (daily)
            self.equity_curve.append({
                'Date': date,
                'Portfolio_Value': self.portfolio_value,
                'Cash': self.cash,
                'Positions': len(self.positions)
            })

        print(f"\n✅ Backtest complete!")
        print(f"   Total rebalance periods: {total_rebalances}")
        print(f"   Total trades: {len(self.trades)}")
        print(f"   Final portfolio value: ${self.portfolio_value:,.0f}")

        return self.get_results()

    def rebalance(self, date):
        """Rebalance portfolio on given date with regime-based position sizing."""
        # Determine market regime and adjust portfolio size
        portfolio_size = self.config.PORTFOLIO_SIZE

        if self.config.USE_REGIME_FILTER and self.regime_data is not None:
            if date in self.regime_data.index:
                regime = self.regime_data.loc[date, 'Regime']

                # Three-tier regime adjustment
                if regime == 'STRONG_BULL':
                    portfolio_size = self.config.STRONG_BULL_POSITIONS  # 10 positions
                elif regime == 'WEAK_BULL':
                    portfolio_size = self.config.WEAK_BULL_POSITIONS    # 5 positions
                else:  # BEAR
                    portfolio_size = self.config.BEAR_MARKET_POSITIONS  # 0 positions

                # Track regime changes
                if len(self.regime_changes) == 0 or self.regime_changes[-1]['regime'] != regime:
                    self.regime_changes.append({
                        'date': date,
                        'regime': regime,
                        'portfolio_size': portfolio_size
                    })

        # If bear market and portfolio size is 0, exit all positions and hold cash
        if portfolio_size == 0:
            current_tickers = list(self.positions.keys())
            for ticker in current_tickers:
                self.exit_position(ticker, date, reason="Bear Market - Exit to Cash")
            self.update_portfolio_value(date)
            return

        # Rank stocks by momentum
        top_stocks = rank_stocks_by_momentum(
            self.stock_data,
            date,
            portfolio_size,  # Use regime-adjusted size
            benchmark_data=self.benchmark_data,
            use_relative_strength=self.config.USE_RELATIVE_STRENGTH_FILTER
        )

        if not top_stocks:
            return

        # Exit ALL current positions
        current_tickers = list(self.positions.keys())
        for ticker in current_tickers:
            self.exit_position(ticker, date, reason="Rebalance")

        # Calculate allocation for each position
        # Use current portfolio value (cash + positions)
        self.update_portfolio_value(date)

        if self.config.USE_MOMENTUM_WEIGHTING:
            # Momentum-weighted allocation
            # Allocate more capital to stocks with stronger momentum
            total_roc = sum([stock['ROC'] for stock in top_stocks if stock['ROC'] > 0])

            if total_roc > 0:
                for stock in top_stocks:
                    ticker = stock['Ticker']
                    # Weight by momentum (normalized)
                    weight = max(stock['ROC'], 0) / total_roc
                    allocation = self.portfolio_value * weight
                    self.enter_position_equal_weight(
                        ticker, date, stock['Close'], allocation
                    )
            else:
                # Fall back to equal weight if all ROC are negative
                allocation_per_stock = self.portfolio_value / len(top_stocks)
                for stock in top_stocks:
                    ticker = stock['Ticker']
                    self.enter_position_equal_weight(
                        ticker, date, stock['Close'], allocation_per_stock
                    )
        else:
            # Equal weight allocation
            allocation_per_stock = self.portfolio_value / len(top_stocks)
            for stock in top_stocks:
                ticker = stock['Ticker']
                self.enter_position_equal_weight(
                    ticker, date, stock['Close'], allocation_per_stock
                )

        # Update portfolio value after rebalancing
        self.update_portfolio_value(date)

    def calculate_commission(self, shares, price):
        """Calculate commission cost for a trade."""
        if not self.config.ENABLE_TRANSACTION_COSTS:
            return 0

        trade_value = shares * price

        if self.config.COMMISSION_TYPE == 'per_share':
            commission = shares * self.config.COMMISSION_PER_SHARE
            # Apply min/max
            commission = max(commission, self.config.COMMISSION_MIN)
            commission = min(commission, trade_value * self.config.COMMISSION_MAX)
        elif self.config.COMMISSION_TYPE == 'per_trade':
            commission = self.config.COMMISSION_MIN
        elif self.config.COMMISSION_TYPE == 'percent':
            commission = trade_value * self.config.COMMISSION_MAX
        else:
            commission = 0

        return commission

    def calculate_slippage(self, shares, price, is_buy):
        """
        Calculate slippage cost (market impact).

        Args:
            shares: Number of shares
            price: Execution price
            is_buy: True for buy orders, False for sell orders

        Returns:
            Slippage cost in dollars
        """
        if not self.config.ENABLE_TRANSACTION_COSTS:
            return 0

        # Slippage in basis points (1 bp = 0.01%)
        slippage_rate = self.config.SLIPPAGE_BPS / 10000

        # Calculate slippage cost
        trade_value = shares * price
        slippage = trade_value * slippage_rate

        return slippage

    def enter_position_equal_weight(self, ticker, date, price, allocation):
        """
        Enter a new position with equal weight allocation.

        This ensures we always hold exactly 20 positions with equal capital.
        """
        # Calculate shares based on equal allocation
        shares = int(allocation / price)

        if shares == 0:
            return

        cost = shares * price

        # Check if we have enough cash (should always be true with equal weight)
        if cost > self.cash:
            shares = int(self.cash / price)
            cost = shares * price

        if shares == 0:
            return

        # Calculate transaction costs
        commission = self.calculate_commission(shares, price)
        slippage = self.calculate_slippage(shares, price, is_buy=True)
        total_costs = commission + slippage

        # Apply costs to cash
        self.cash -= (cost + total_costs)

        # Track costs
        self.total_commissions += commission
        self.total_slippage += slippage
        self.total_transaction_costs += total_costs

        # Execute trade
        self.positions[ticker] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': date,
            'highest_price': price
        }

        # Record trade
        self.trades.append({
            'Date': date,
            'Ticker': ticker,
            'Action': 'BUY',
            'Shares': shares,
            'Price': price,
            'Value': cost,
            'Commission': commission,
            'Slippage': slippage,
            'Total_Costs': total_costs
        })

    def enter_short_position(self, ticker, date, price, allocation, atr):
        """
        Enter a short position (sell borrowed shares).

        Short positions have negative shares and use stop-loss for risk management.

        Args:
            ticker: Stock ticker
            date: Entry date
            price: Current price
            allocation: Dollar amount to allocate
            atr: ATR for stop-loss calculation
        """
        # Calculate shares based on allocation (will be stored as negative)
        shares = int(allocation / price)

        if shares == 0:
            return

        # Short positions: we SELL shares we don't own (receive cash)
        proceeds = shares * price

        # Calculate transaction costs (shorts pay commission and slippage)
        commission = self.calculate_commission(shares, price)
        slippage = self.calculate_slippage(shares, price, is_buy=False)
        total_costs = commission + slippage

        # Receive proceeds (minus costs)
        self.cash += (proceeds - total_costs)

        # Track costs
        self.total_commissions += commission
        self.total_slippage += slippage
        self.total_transaction_costs += total_costs

        # Calculate stop-loss (15% above entry for shorts)
        stop_loss_price = price * 1.15  # Exit if price rises 15% (loss)

        # Execute short trade (negative shares = short)
        self.positions[ticker] = {
            'shares': -shares,  # NEGATIVE shares indicate short position
            'entry_price': price,
            'entry_date': date,
            'highest_price': price,  # Not used for shorts, but keep for compatibility
            'stop_loss': stop_loss_price,  # 15% stop-loss for shorts
            'sector_count': {}  # Will track sector concentration
        }

        # Record trade
        self.trades.append({
            'Date': date,
            'Ticker': ticker,
            'Action': 'SHORT',
            'Shares': -shares,  # Negative to indicate short
            'Price': price,
            'Value': proceeds,
            'Commission': commission,
            'Slippage': slippage,
            'Total_Costs': total_costs
        })

    def enter_position(self, ticker, date, price, atr):
        """Enter a new position (legacy method - keeping for compatibility)."""
        # Calculate position size
        shares = calculate_position_size(
            self.portfolio_value,
            atr,
            self.config.RISK_PER_POSITION,
            self.config.ATR_STOP_MULTIPLIER
        )

        if shares == 0:
            return

        cost = shares * price

        # Check if we have enough cash
        if cost > self.cash:
            shares = int(self.cash / price)
            cost = shares * price

        if shares == 0:
            return

        # Execute trade
        self.cash -= cost
        self.positions[ticker] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': date,
            'highest_price': price,
            'atr': atr
        }

        # Record trade
        self.trades.append({
            'Date': date,
            'Ticker': ticker,
            'Action': 'BUY',
            'Shares': shares,
            'Price': price,
            'Value': cost
        })

    def exit_position(self, ticker, date, reason="Rebalance"):
        """Exit an existing position (long or short)."""
        if ticker not in self.positions:
            return

        position = self.positions[ticker]
        shares = position['shares']
        is_short = shares < 0  # Negative shares = short position

        # Get current price
        if date not in self.stock_data[ticker].index:
            return
        current_price = self.stock_data[ticker].loc[date, 'Close']

        # Calculate transaction costs (use absolute value of shares)
        commission = self.calculate_commission(abs(shares), current_price)
        slippage = self.calculate_slippage(abs(shares), current_price, is_buy=is_short)  # Covering short = buying
        total_costs = commission + slippage

        # Track costs
        self.total_commissions += commission
        self.total_slippage += slippage
        self.total_transaction_costs += total_costs

        if is_short:
            # SHORT POSITION: We need to BUY shares to cover (pay cash)
            cost_to_cover = abs(shares) * current_price
            self.cash -= (cost_to_cover + total_costs)

            # P&L = proceeds from short - cost to cover
            proceeds_from_short = abs(shares) * position['entry_price']
            pnl = proceeds_from_short - cost_to_cover - total_costs
            pnl_pct = (pnl / proceeds_from_short) * 100

            action = 'COVER'
            gross_value = -cost_to_cover  # Negative because we're paying
            net_proceeds = -(cost_to_cover + total_costs)
        else:
            # LONG POSITION: Standard sell
            gross_proceeds = shares * current_price
            net_proceeds = gross_proceeds - total_costs
            self.cash += net_proceeds

            # Calculate P&L
            cost = shares * position['entry_price']
            pnl = net_proceeds - cost
            pnl_pct = (pnl / cost) * 100

            action = 'SELL'
            gross_value = gross_proceeds

        # Record trade
        self.trades.append({
            'Date': date,
            'Ticker': ticker,
            'Action': action,
            'Shares': shares,  # Keep sign (negative for shorts)
            'Price': current_price,
            'Value': gross_value,
            'Commission': commission,
            'Slippage': slippage,
            'Total_Costs': total_costs,
            'Net_Proceeds': net_proceeds,
            'P&L': pnl,
            'P&L%': pnl_pct,
            'Exit_Reason': reason
        })

        # Remove position
        del self.positions[ticker]

    def check_trailing_stops(self, date):
        """Check and execute trailing stops for all positions."""
        tickers_to_exit = []

        for ticker, position in self.positions.items():
            if date not in self.stock_data[ticker].index:
                continue

            current_price = self.stock_data[ticker].loc[date, 'Close']

            # Update highest price if current price is higher
            if current_price > position['highest_price']:
                position['highest_price'] = current_price

            # Check if trailing stop is hit
            stop_price = position['highest_price'] * (1 - self.config.TRAILING_STOP_PCT)
            if current_price < stop_price:
                tickers_to_exit.append(ticker)

        # Exit positions that hit trailing stops
        for ticker in tickers_to_exit:
            self.exit_position(ticker, date, reason=f"Trailing Stop ({self.config.TRAILING_STOP_PCT*100:.0f}%)")

    def check_short_stop_losses(self, date):
        """Check and execute stop-losses for short positions (15% above entry)."""
        tickers_to_cover = []

        for ticker, position in self.positions.items():
            # Only check short positions (negative shares)
            if position['shares'] >= 0:
                continue

            if date not in self.stock_data[ticker].index:
                continue

            current_price = self.stock_data[ticker].loc[date, 'Close']

            # Check if stop-loss is hit (price went UP 15% for shorts = loss)
            if 'stop_loss' in position and current_price > position['stop_loss']:
                tickers_to_cover.append(ticker)

        # Exit (cover) short positions that hit stop-loss
        for ticker in tickers_to_cover:
            self.exit_position(ticker, date, reason="Short Stop-Loss (15%)")

    def update_portfolio_value(self, date):
        """
        Calculate current portfolio value.

        For short positions:
        - shares are negative
        - position_value = shares * current_price (will be negative)
        - portfolio_value = cash + position_value (cash is high from short proceeds, position_value is negative liability)
        """
        # Sum up position values
        position_value = 0
        for ticker, position in self.positions.items():
            if ticker in self.stock_data and date in self.stock_data[ticker].index:
                current_price = self.stock_data[ticker].loc[date, 'Close']
                shares = position['shares']

                # For LONG: shares > 0, position_value = positive (asset)
                # For SHORT: shares < 0, position_value = negative (liability)
                position_value += shares * current_price

        self.portfolio_value = self.cash + position_value
        return self.portfolio_value

    def get_results(self):
        """Return backtest results."""
        equity_df = pd.DataFrame(self.equity_curve)
        trades_df = pd.DataFrame(self.trades)

        return {
            'equity_curve': equity_df,
            'trades': trades_df,
            'final_value': self.portfolio_value,
            'total_return': ((self.portfolio_value - self.config.INITIAL_CAPITAL) /
                           self.config.INITIAL_CAPITAL) * 100
        }


# Run the backtest
backtester = MomentumBacktester(stock_data, config, regime_data, benchmark_data)
results = backtester.run()


# =============================================================================
# SECTION 8: PERFORMANCE ANALYSIS
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 8: PERFORMANCE METRICS")
print("=" * 80)

equity_curve = results['equity_curve']
trades_df = results['trades']

# Calculate key metrics
initial_value = config.INITIAL_CAPITAL
final_value = results['final_value']
total_return = results['total_return']

# Calculate returns
equity_curve['Returns'] = equity_curve['Portfolio_Value'].pct_change()
equity_curve['Cumulative_Return'] = (equity_curve['Portfolio_Value'] / initial_value - 1) * 100

# Drawdown calculation
equity_curve['Peak'] = equity_curve['Portfolio_Value'].cummax()
equity_curve['Drawdown'] = ((equity_curve['Portfolio_Value'] - equity_curve['Peak']) /
                            equity_curve['Peak']) * 100

max_drawdown = equity_curve['Drawdown'].min()

# Trade statistics
winning_trades = trades_df[trades_df['Action'] == 'SELL'][trades_df['P&L'] > 0]
losing_trades = trades_df[trades_df['Action'] == 'SELL'][trades_df['P&L'] < 0]

num_trades = len(trades_df[trades_df['Action'] == 'SELL'])
num_wins = len(winning_trades)
num_losses = len(losing_trades)
win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0

avg_win = winning_trades['P&L'].mean() if len(winning_trades) > 0 else 0
avg_loss = losing_trades['P&L'].mean() if len(losing_trades) > 0 else 0
profit_factor = abs(winning_trades['P&L'].sum() / losing_trades['P&L'].sum()) if len(losing_trades) > 0 else 0

# Sharpe ratio (annualized)
returns = equity_curve['Returns'].dropna()
sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 0 else 0

# =============================================================================
# BENCHMARK COMPARISON (SPY Buy-and-Hold)
# =============================================================================

# Calculate benchmark returns
benchmark_start_date = equity_curve['Date'].iloc[0]
benchmark_end_date = equity_curve['Date'].iloc[-1]

# Filter benchmark to same dates as strategy
benchmark_filtered = benchmark_data[(benchmark_data.index >= benchmark_start_date) &
                                     (benchmark_data.index <= benchmark_end_date)]

# Calculate SPY buy-and-hold performance
spy_start_price = benchmark_filtered['Close'].iloc[0]
spy_end_price = benchmark_filtered['Close'].iloc[-1]
spy_return = ((spy_end_price / spy_start_price) - 1) * 100
spy_final_value = initial_value * (1 + spy_return / 100)

# Calculate benchmark daily returns for alpha/beta
benchmark_filtered['Returns'] = benchmark_filtered['Close'].pct_change()
benchmark_returns = benchmark_filtered['Returns'].dropna()

# Align strategy and benchmark returns by date
equity_curve_indexed = equity_curve.set_index('Date')
benchmark_indexed = benchmark_filtered[['Returns']].copy()
benchmark_indexed.columns = ['Benchmark_Returns']

# Merge on dates
aligned = equity_curve_indexed[['Returns']].join(benchmark_indexed, how='inner')
aligned = aligned.dropna()

# Calculate beta (correlation with market)
if len(aligned) > 0:
    covariance = aligned['Returns'].cov(aligned['Benchmark_Returns'])
    benchmark_variance = aligned['Benchmark_Returns'].var()
    beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

    # Calculate alpha (annualized excess return)
    strategy_annual_return = total_return / 5  # 5-year period
    spy_annual_return = spy_return / 5
    alpha = strategy_annual_return - spy_annual_return

    # Information Ratio (alpha / tracking error)
    tracking_error = (aligned['Returns'] - aligned['Benchmark_Returns']).std() * np.sqrt(252)
    information_ratio = (alpha / tracking_error) if tracking_error != 0 else 0
else:
    beta = 0
    alpha = 0
    information_ratio = 0

# Print summary
print(f"\n{'='*80}")
print(f"PERFORMANCE SUMMARY")
print(f"{'='*80}")
print(f"\nPORTFOLIO:")
print(f"  Initial Capital:      ${initial_value:>15,.2f}")
print(f"  Final Value:          ${final_value:>15,.2f}")
print(f"  Total Return:         {total_return:>15.2f}%")
print(f"  Max Drawdown:         {max_drawdown:>15.2f}%")
print(f"  Sharpe Ratio:         {sharpe_ratio:>15.2f}")

print(f"\nTRADING STATISTICS:")
print(f"  Total Trades:         {num_trades:>15,}")
print(f"  Winning Trades:       {num_wins:>15,}")
print(f"  Losing Trades:        {num_losses:>15,}")
print(f"  Win Rate:             {win_rate:>15.2f}%")
print(f"  Profit Factor:        {profit_factor:>15.2f}")

print(f"\nAVERAGE TRADE:")
print(f"  Avg Winner:           ${avg_win:>15,.2f}")
print(f"  Avg Loser:            ${avg_loss:>15,.2f}")
print(f"  Avg Win/Loss Ratio:   {abs(avg_win/avg_loss) if avg_loss != 0 else 0:>15.2f}")

# Add transaction cost summary
if config.ENABLE_TRANSACTION_COSTS:
    total_commissions = backtester.total_commissions
    total_slippage = backtester.total_slippage
    total_costs = backtester.total_transaction_costs
    cost_per_trade = total_costs / num_trades if num_trades > 0 else 0
    cost_pct_of_returns = (total_costs / (final_value - initial_value)) * 100 if final_value > initial_value else 0

    print(f"\nTRANSACTION COSTS:")
    print(f"  Total Commissions:    ${total_commissions:>15,.2f}")
    print(f"  Total Slippage:       ${total_slippage:>15,.2f}")
    print(f"  Total Costs:          ${total_costs:>15,.2f}")
    print(f"  Avg Cost per Trade:   ${cost_per_trade:>15,.2f}")
    print(f"  Costs as % of Gains:  {cost_pct_of_returns:>15.2f}%")

# Add benchmark comparison
print(f"\nBENCHMARK COMPARISON (SPY Buy-and-Hold):")
print(f"  SPY Total Return:     {spy_return:>15.2f}%")
print(f"  SPY Final Value:      ${spy_final_value:>15,.2f}")
print(f"  Strategy vs SPY:      {total_return - spy_return:>15.2f}%")
print(f"  {'OUTPERFORM' if total_return > spy_return else 'UNDERPERFORM':>15}")
print()
print(f"  Alpha (Annual):       {alpha:>15.2f}%")
print(f"  Beta:                 {beta:>15.2f}")
print(f"  Information Ratio:    {information_ratio:>15.2f}")

print(f"\n{'='*80}\n")


# =============================================================================
# SECTION 9: VISUALIZATION
# =============================================================================
print("=" * 80)
print("SECTION 9: GENERATING CHARTS")
print("=" * 80)

# Create output directory
import os
os.makedirs(config.OUTPUT_DIR, exist_ok=True)

# 1. Equity Curve
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

# Portfolio value
ax1.plot(equity_curve['Date'], equity_curve['Portfolio_Value'],
         linewidth=2, color='#2E86AB', label='Portfolio Value')
ax1.axhline(y=initial_value, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
ax1.set_title('Nick Radge Momentum Strategy - Equity Curve', fontsize=16, fontweight='bold')
ax1.set_xlabel('Date')
ax1.set_ylabel('Portfolio Value ($)')
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

# Drawdown
ax2.fill_between(equity_curve['Date'], equity_curve['Drawdown'], 0,
                  color='#A23B72', alpha=0.6)
ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
ax2.set_xlabel('Date')
ax2.set_ylabel('Drawdown (%)')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f'{config.OUTPUT_DIR}/equity_curve.png', dpi=150)
print(f"\n✅ Saved: {config.OUTPUT_DIR}/equity_curve.png")

# 2. Strategy vs Benchmark Comparison
fig, ax = plt.subplots(figsize=(14, 8))

# Calculate cumulative returns for both
strategy_cumulative = (equity_curve['Portfolio_Value'] / initial_value) * 100
spy_cumulative = (benchmark_filtered['Close'] / spy_start_price) * 100

# Plot both
ax.plot(equity_curve['Date'], strategy_cumulative, linewidth=2, color='#2E86AB', label='Strategy (with costs)')
ax.plot(benchmark_filtered.index, spy_cumulative, linewidth=2, color='#FF6B35', label='SPY Buy-and-Hold', linestyle='--')
ax.axhline(y=100, color='gray', linestyle=':', alpha=0.5, label='Initial Capital (100%)')

ax.set_title('Strategy vs SPY Benchmark - Cumulative Returns', fontsize=16, fontweight='bold')
ax.set_xlabel('Date')
ax.set_ylabel('Value (% of Initial Capital)')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)

# Add annotation with final values
textstr = f'Strategy: {total_return:.1f}%\\nSPY: {spy_return:.1f}%\\nAlpha: {total_return - spy_return:+.1f}%'
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=12,
        verticalalignment='top', bbox=props)

plt.tight_layout()
plt.savefig(f'{config.OUTPUT_DIR}/strategy_vs_spy.png', dpi=150)
print(f"✅ Saved: {config.OUTPUT_DIR}/strategy_vs_spy.png")

# 3. Monthly Returns Heatmap
equity_curve['Year'] = equity_curve['Date'].dt.year
equity_curve['Month'] = equity_curve['Date'].dt.month

monthly_returns = equity_curve.groupby(['Year', 'Month'])['Returns'].sum() * 100
monthly_pivot = monthly_returns.unstack(fill_value=0)

plt.figure(figsize=(12, 8))
sns.heatmap(monthly_pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=0,
            cbar_kws={'label': 'Return (%)'})
plt.title('Monthly Returns Heatmap', fontsize=16, fontweight='bold')
plt.xlabel('Month')
plt.ylabel('Year')
plt.tight_layout()
plt.savefig(f'{config.OUTPUT_DIR}/monthly_returns.png', dpi=150)
print(f"✅ Saved: {config.OUTPUT_DIR}/monthly_returns.png")

# 3. Trade Distribution
if num_trades > 0:
    sell_trades = trades_df[trades_df['Action'] == 'SELL'].copy()

    plt.figure(figsize=(12, 6))
    plt.hist(sell_trades['P&L%'], bins=50, edgecolor='black', alpha=0.7, color='#2E86AB')
    plt.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Breakeven')
    plt.title('Trade P&L Distribution', fontsize=16, fontweight='bold')
    plt.xlabel('P&L (%)')
    plt.ylabel('Number of Trades')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{config.OUTPUT_DIR}/trade_distribution.png', dpi=150)
    print(f"✅ Saved: {config.OUTPUT_DIR}/trade_distribution.png")

print(f"\n📊 All charts saved to: {config.OUTPUT_DIR}")


# =============================================================================
# SECTION 10: SAVE RESULTS
# =============================================================================
print("\n" + "=" * 80)
print("SECTION 10: SAVING RESULTS")
print("=" * 80)

if config.SAVE_RESULTS:
    # Save equity curve
    equity_curve.to_csv(f'{config.OUTPUT_DIR}/equity_curve.csv', index=False)
    print(f"\n✅ Saved equity curve: {config.OUTPUT_DIR}/equity_curve.csv")

    # Save trade log
    trades_df.to_csv(f'{config.OUTPUT_DIR}/trade_log.csv', index=False)
    print(f"✅ Saved trade log: {config.OUTPUT_DIR}/trade_log.csv")

    # Save summary report
    with open(f'{config.OUTPUT_DIR}/summary_report.txt', 'w') as f:
        f.write("="*80 + "\n")
        f.write("NICK RADGE MOMENTUM STRATEGY - BACKTEST REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Strategy: Nick Radge Momentum (Unholy Grails)\n")
        f.write(f"Period: {config.START_DATE.date()} to {config.END_DATE.date()}\n")
        f.write(f"Universe: S&P 500 (Top {config.NUM_TEST_STOCKS} stocks)\n")
        f.write(f"Portfolio Size: {config.PORTFOLIO_SIZE} positions\n")
        f.write(f"Rebalance: {config.REBALANCE_FREQ}\n")
        f.write(f"Risk per Position: {config.RISK_PER_POSITION*100:.2f}%\n\n")

        f.write("PERFORMANCE METRICS\n")
        f.write("-"*80 + "\n")
        f.write(f"Initial Capital:      ${initial_value:>15,.2f}\n")
        f.write(f"Final Value:          ${final_value:>15,.2f}\n")
        f.write(f"Total Return:         {total_return:>15.2f}%\n")
        f.write(f"Max Drawdown:         {max_drawdown:>15.2f}%\n")
        f.write(f"Sharpe Ratio:         {sharpe_ratio:>15.2f}\n\n")

        f.write("TRADING STATISTICS\n")
        f.write("-"*80 + "\n")
        f.write(f"Total Trades:         {num_trades:>15,}\n")
        f.write(f"Winning Trades:       {num_wins:>15,}\n")
        f.write(f"Losing Trades:        {num_losses:>15,}\n")
        f.write(f"Win Rate:             {win_rate:>15.2f}%\n")
        f.write(f"Profit Factor:        {profit_factor:>15.2f}\n")
        f.write(f"Avg Winner:           ${avg_win:>15,.2f}\n")
        f.write(f"Avg Loser:            ${avg_loss:>15,.2f}\n")

    print(f"✅ Saved summary report: {config.OUTPUT_DIR}/summary_report.txt")

# =============================================================================
# SECTION 11: QUANTSTATS ANALYSIS (OPTIONAL)
# =============================================================================
try:
    import quantstats as qs

    print("\n" + "=" * 80)
    print("SECTION 11: GENERATING QUANTSTATS REPORT")
    print("=" * 80)

    # Prepare returns series
    equity_curve_sorted = equity_curve.sort_values('Date')
    equity_curve_sorted = equity_curve_sorted.set_index('Date')
    returns = equity_curve_sorted['Returns'].fillna(0)

    # Generate comprehensive HTML report
    qs.reports.html(
        returns,
        output=f'{config.OUTPUT_DIR}/quantstats_report.html',
        title='Nick Radge Momentum Strategy',
        download_filename=f'{config.OUTPUT_DIR}/quantstats_report.html'
    )

    print(f"\n✅ QuantStats report generated: {config.OUTPUT_DIR}/quantstats_report.html")
    print(f"   Open this file in your browser for comprehensive analysis")

except ImportError:
    print("\n⚠️  QuantStats not installed. Skipping detailed report.")
    print("   Install with: pip install quantstats")

print("\n" + "="*80)
print("✅ BACKTEST COMPLETE!")
print("="*80)
print(f"\nAll results saved to: {config.OUTPUT_DIR}")
print("\nNext steps:")
print("1. Review the charts in output/momentum/")
print("2. Open quantstats_report.html in your browser for detailed analysis")
print("3. Analyze trade_log.csv to see all trades")
print("4. Adjust parameters in StrategyConfig and re-run")
print("\n" + "="*80)
