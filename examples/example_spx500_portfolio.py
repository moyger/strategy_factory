#!/usr/bin/env python3
"""
Example: SPX500 Stock Portfolio Strategy

This example demonstrates:
1. Loading SPX500 constituents
2. Downloading sample stock data
3. Running portfolio allocation strategy
4. Comparing different allocation methods

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from strategies.multi_asset_portfolio_strategy import MultiAssetPortfolioStrategy

def download_stock_data(tickers, start_date='2020-01-01', end_date='2024-12-31'):
    """
    Download stock data using yfinance

    Args:
        tickers: List of stock symbols
        start_date: Start date for data
        end_date: End date for data

    Returns:
        DataFrame with columns = tickers, index = date, values = close prices
    """
    try:
        import yfinance as yf
    except ImportError:
        print("❌ yfinance not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
        import yfinance as yf

    print(f"📥 Downloading data for {len(tickers)} stocks...")
    print(f"   Period: {start_date} to {end_date}")

    prices_dict = {}
    failed = []

    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"   [{i}/{len(tickers)}] Downloading {ticker}...", end='\r')

            # Download data
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if len(df) > 0:
                prices_dict[ticker] = df['Close']
            else:
                failed.append(ticker)

        except Exception as e:
            failed.append(ticker)
            print(f"\n   ⚠️  Error downloading {ticker}: {e}")

    print(f"\n✅ Downloaded {len(prices_dict)}/{len(tickers)} stocks successfully")

    if failed:
        print(f"   ⚠️  Failed: {', '.join(failed)}")

    if len(prices_dict) == 0:
        raise ValueError("No stock data downloaded! Check your internet connection or ticker symbols.")

    # Combine into DataFrame
    prices = pd.DataFrame(prices_dict)

    # Forward fill missing values
    prices = prices.ffill()

    # Drop rows with any remaining NaN
    prices = prices.dropna()

    print(f"   Final dataset: {len(prices)} days, {len(prices.columns)} stocks")

    return prices


def load_spx500_constituents(file_path='data/stocks/SPX500.csv', sample_date='2020-01-02'):
    """
    Load SPX500 constituents for a specific date

    Args:
        file_path: Path to SPX500 constituents file
        sample_date: Date to extract constituents from

    Returns:
        List of ticker symbols
    """
    print(f"📂 Loading SPX500 constituents from {sample_date}...")

    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])

    # Find the date (or closest date)
    target_date = pd.to_datetime(sample_date)
    closest_date = df[df['date'] >= target_date]['date'].min()

    if pd.isna(closest_date):
        closest_date = df['date'].max()

    # Get tickers for that date
    tickers_str = df[df['date'] == closest_date]['tickers'].iloc[0]
    tickers = tickers_str.split(',')

    print(f"✅ Found {len(tickers)} constituents on {closest_date.date()}")

    return tickers


def main():
    print("="*80)
    print("EXAMPLE: SPX500 STOCK PORTFOLIO STRATEGY")
    print("="*80)

    # ========================================
    # STEP 1: LOAD SPX500 CONSTITUENTS
    # ========================================
    print("\n" + "="*80)
    print("STEP 1: LOADING SPX500 CONSTITUENTS")
    print("="*80 + "\n")

    # Get current constituents (or use a specific date)
    all_tickers = load_spx500_constituents(
        file_path='data/stocks/SPX500.csv',
        sample_date='2020-01-02'
    )

    # For demo purposes, use a sample of stocks
    # (Downloading all 500+ stocks takes too long)
    print("\n💡 For demo, selecting sample of 10 stocks...")

    # Select diverse stocks from different sectors
    sample_tickers = [
        'AAPL',  # Tech - Apple
        'MSFT',  # Tech - Microsoft
        'JPM',   # Finance - JPMorgan
        'JNJ',   # Healthcare - Johnson & Johnson
        'XOM',   # Energy - Exxon
        'WMT',   # Consumer - Walmart
        'BA',    # Industrial - Boeing
        'PG',    # Consumer Staples - Procter & Gamble
        'DIS',   # Entertainment - Disney
        'HD'     # Retail - Home Depot
    ]

    print(f"   Selected stocks: {', '.join(sample_tickers)}")

    # ========================================
    # STEP 2: DOWNLOAD STOCK DATA
    # ========================================
    print("\n" + "="*80)
    print("STEP 2: DOWNLOADING STOCK PRICE DATA")
    print("="*80 + "\n")

    prices = download_stock_data(
        tickers=sample_tickers,
        start_date='2020-01-01',
        end_date='2024-12-31'
    )

    # Use last 500 days for faster testing
    prices = prices.tail(500)

    print(f"\n✅ Final dataset ready:")
    print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"   Stocks: {len(prices.columns)}")
    print(f"   Days: {len(prices)}")

    # ========================================
    # STEP 3: RUN PORTFOLIO STRATEGIES
    # ========================================
    print("\n" + "="*80)
    print("STEP 3: TESTING PORTFOLIO ALLOCATION STRATEGIES")
    print("="*80)

    strategies_config = [
        {
            'name': 'Equal Weight (Top 5)',
            'allocation_method': 'equal_weight',
            'rebalance_freq': 'M',  # Monthly for stocks
            'top_n': 5,
            'lookback_period': 60,  # 60 days momentum
            'min_momentum': 0.0
        },
        {
            'name': 'Momentum (Top 5)',
            'allocation_method': 'momentum',
            'rebalance_freq': 'M',
            'top_n': 5,
            'lookback_period': 60,
            'min_momentum': 0.02  # Only >2% momentum
        },
        {
            'name': 'Risk Parity (Top 5)',
            'allocation_method': 'risk_parity',
            'rebalance_freq': 'M',
            'top_n': 5,
            'lookback_period': 60,
            'min_momentum': 0.0
        },
        {
            'name': 'Momentum (Top 3 Aggressive)',
            'allocation_method': 'momentum',
            'rebalance_freq': 'M',
            'top_n': 3,
            'lookback_period': 90,  # 3 months momentum
            'min_momentum': 0.05    # Only >5% momentum
        },
    ]

    results_summary = {}

    for config in strategies_config:
        print(f"\n{'='*80}")
        print(f"TESTING: {config['name'].upper()}")
        print(f"{'='*80}")

        # Create strategy
        strategy = MultiAssetPortfolioStrategy(
            allocation_method=config['allocation_method'],
            rebalance_freq=config['rebalance_freq'],
            top_n=config['top_n'],
            lookback_period=config['lookback_period'],
            min_momentum=config['min_momentum']
        )

        # Run backtest
        portfolio = strategy.backtest(prices, initial_capital=100000)

        # Store results (handle Series for multi-asset portfolios)
        total_return = portfolio.total_return()
        if isinstance(total_return, pd.Series):
            final_value = portfolio.value().iloc[-1].sum()
            init_cash = portfolio.init_cash.sum()
            total_return = ((final_value / init_cash) - 1) * 100
        else:
            total_return = total_return * 100

        sharpe = portfolio.sharpe_ratio()
        if isinstance(sharpe, pd.Series):
            sharpe = sharpe.mean()

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max() * 100
        else:
            max_dd = max_dd * 100

        trades = portfolio.trades.count()
        if isinstance(trades, pd.Series):
            trades = trades.sum()

        results_summary[config['name']] = {
            'return': total_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': trades
        }

        # Print results
        strategy.print_results(portfolio, prices)

    # ========================================
    # STEP 4: COMPARE RESULTS
    # ========================================
    print("\n" + "="*80)
    print("STEP 4: STRATEGY COMPARISON")
    print("="*80)

    print(f"\n{'Strategy':<35} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades':<10}")
    print("-" * 90)

    for name, metrics in results_summary.items():
        print(f"{name:<35} {metrics['return']:>10.2f}%  {metrics['sharpe']:>8.2f}  "
              f"{metrics['max_dd']:>10.2f}%  {metrics['trades']:>8}")

    # Find best strategy
    best_strategy = max(results_summary.items(), key=lambda x: x[1]['sharpe'])

    print(f"\n🏆 BEST STRATEGY (by Sharpe): {best_strategy[0]}")
    print(f"   Return: {best_strategy[1]['return']:.2f}%")
    print(f"   Sharpe: {best_strategy[1]['sharpe']:.2f}")
    print(f"   Max DD: {best_strategy[1]['max_dd']:.2f}%")

    # ========================================
    # NEXT STEPS
    # ========================================
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)

    print("""
1. EXPAND UNIVERSE:
   - Increase sample size from 10 to 20, 50, or all 500+ stocks
   - Group by sectors for sector rotation

2. OPTIMIZE PARAMETERS:
   - Test different lookback periods (30, 60, 90, 120 days)
   - Test different rebalancing frequencies (W, M, Q)
   - Test different top_n holdings (3, 5, 10, 20)

3. ADD FILTERS:
   - Minimum liquidity requirements
   - Sector diversification limits
   - Correlation filters
   - Volatility thresholds

4. ENHANCE ALLOCATION:
   - Add fundamental factors (P/E, ROE, etc.)
   - Add sentiment analysis
   - Add machine learning predictions

5. RISK MANAGEMENT:
   - Add portfolio-level stop loss
   - Add position size limits
   - Add leverage/margin controls
   - Add drawdown-based scaling
    """)

    print("\n✅ SPX500 portfolio example completed!")
    print("\nTo expand to full S&P 500:")
    print("   1. Change sample_tickers to all_tickers[:50]  # Start with 50")
    print("   2. Test different parameters")
    print("   3. Gradually increase universe size")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
