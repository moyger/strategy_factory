#!/usr/bin/env python3
"""
Test Nick Radge Strategy with Different Performance Qualifiers

Compares ROC (original) vs ATR-based qualifiers:
- ROC (Rate of Change)
- ANM (ATR-Normalized Momentum)
- BSS (Breakout Strength Score)
- VEM (Volatility Expansion Momentum)
- TQS (Trend Quality Score)
- RAM (Risk-Adjusted Momentum)
- Composite (Weighted combination)

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_enhanced import NickRadgeEnhanced


def download_sp500_stocks(num_stocks: int = 50, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Download S&P 500 stock data"""
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
    ][:num_stocks]

    # Add GLD for bear market allocation
    if 'GLD' not in tickers:
        tickers.append('GLD')

    print(f"📥 Downloading {len(tickers)} stocks...")
    print(f"   Period: {start_date} to {end_date}")

    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)

    if len(tickers) == 1:
        prices = data['Close'].to_frame()
        prices.columns = tickers
    else:
        prices = data['Close']

    # Remove any stocks with insufficient data
    prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)

    print(f"✅ Downloaded {len(prices.columns)} stocks with sufficient data")

    return prices


def download_spy(start_date: str, end_date: str) -> pd.Series:
    """Download SPY data for regime filtering and benchmark"""
    print(f"\n📊 Downloading SPY (benchmark)...")

    lookback_start = pd.to_datetime(start_date) - timedelta(days=400)
    df = yf.download('SPY', start=lookback_start, end=end_date, auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    spy_prices = df['Close']
    spy_prices = spy_prices[spy_prices.index >= start_date]

    print(f"✅ SPY data loaded ({len(spy_prices)} days)")

    return spy_prices


def run_comparison(qualifiers: list, prices: pd.DataFrame, spy_prices: pd.Series, initial_capital: float = 10000):
    """
    Run backtest comparison for multiple qualifiers

    Args:
        qualifiers: List of qualifier types to test
        prices: Stock prices DataFrame
        spy_prices: SPY prices
        initial_capital: Starting capital

    Returns:
        DataFrame with comparison results
    """
    print("\n" + "="*80)
    print("RUNNING QUALIFIER COMPARISON")
    print("="*80)

    results = []

    for qualifier_type in qualifiers:
        print(f"\n{'='*80}")
        print(f"Testing Qualifier: {qualifier_type.upper()}")
        print(f"{'='*80}")

        try:
            # Create strategy
            strategy = NickRadgeEnhanced(
                portfolio_size=7,
                qualifier_type=qualifier_type,
                ma_period=100,
                rebalance_freq='QS',
                use_momentum_weighting=True,
                use_regime_filter=True,
                use_relative_strength=True,
                strong_bull_positions=7,
                weak_bull_positions=3,
                bear_positions=0,
                bear_market_asset='GLD',
                bear_allocation=1.0
            )

            # Run backtest
            portfolio = strategy.backtest(
                prices=prices,
                spy_prices=spy_prices,
                initial_capital=initial_capital,
                fees=0.001,
                slippage=0.0005
            )

            # Extract metrics
            final_value = portfolio.value().iloc[-1]
            if isinstance(final_value, pd.Series):
                final_value = final_value.sum()

            init_cash = portfolio.init_cash
            if isinstance(init_cash, pd.Series):
                init_cash = init_cash.sum()

            total_return = ((final_value / init_cash) - 1) * 100

            try:
                sharpe = portfolio.sharpe_ratio(freq='D')
                if isinstance(sharpe, pd.Series):
                    sharpe = sharpe.mean()
            except:
                sharpe = 0.0

            max_dd = portfolio.max_drawdown()
            if isinstance(max_dd, pd.Series):
                max_dd = max_dd.max()

            trades_count = portfolio.trades.count()
            if isinstance(trades_count, pd.Series):
                trades_count = trades_count.sum()

            try:
                win_rate = portfolio.trades.win_rate()
                if isinstance(win_rate, pd.Series):
                    win_rate = win_rate.mean()
            except:
                win_rate = 0.0

            try:
                profit_factor = portfolio.trades.profit_factor()
                if isinstance(profit_factor, pd.Series):
                    profit_factor = profit_factor.mean()
            except:
                profit_factor = 0.0

            # Calculate annualized return
            days = (prices.index[-1] - prices.index[0]).days
            years = days / 365.25
            annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0

            # Store results
            results.append({
                'Qualifier': qualifier_type.upper(),
                'Total Return %': total_return,
                'Annualized %': annualized_return,
                'Sharpe Ratio': sharpe,
                'Max Drawdown %': max_dd * 100,
                'Total Trades': trades_count,
                'Win Rate %': win_rate * 100,
                'Profit Factor': profit_factor,
                'Final Value': final_value
            })

            print(f"\n✅ {qualifier_type.upper()} backtest complete")
            print(f"   Total Return: {total_return:.2f}%")
            print(f"   Sharpe Ratio: {sharpe:.2f}")
            print(f"   Max Drawdown: {max_dd * 100:.2f}%")

        except Exception as e:
            print(f"\n❌ Error testing {qualifier_type}: {e}")
            import traceback
            traceback.print_exc()

    return pd.DataFrame(results)


if __name__ == "__main__":
    print("="*80)
    print("NICK RADGE STRATEGY - PERFORMANCE QUALIFIER COMPARISON")
    print("="*80)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000
    NUM_STOCKS = 50

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks + GLD")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Portfolio Size: 7 stocks")
    print(f"   Rebalance: Quarterly (QS)")
    print(f"   Bear Asset: GLD (100% allocation)")

    # Download data
    print(f"\n" + "="*80)
    print("DOWNLOADING DATA")
    print("="*80)

    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)
    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align dates
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")

    # Calculate SPY return for comparison
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Qualifiers to test
    qualifiers_to_test = [
        'roc',        # Original (baseline)
        'anm',        # ATR-Normalized Momentum
        'bss',        # Breakout Strength Score
        'vem',        # Volatility Expansion Momentum
        'tqs',        # Trend Quality Score
        'ram',        # Risk-Adjusted Momentum
        'composite'   # Weighted combination
    ]

    # Run comparison
    comparison_df = run_comparison(qualifiers_to_test, prices, spy_prices, INITIAL_CAPITAL)

    # Print comparison table
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON - ALL QUALIFIERS")
    print("="*80)

    print("\n" + comparison_df.to_string(index=False))

    # Find best performers
    print("\n" + "="*80)
    print("BEST PERFORMERS")
    print("="*80)

    best_return = comparison_df.loc[comparison_df['Total Return %'].idxmax()]
    best_sharpe = comparison_df.loc[comparison_df['Sharpe Ratio'].idxmax()]
    best_drawdown = comparison_df.loc[comparison_df['Max Drawdown %'].idxmin()]

    print(f"\n🏆 Highest Return: {best_return['Qualifier']} ({best_return['Total Return %']:.2f}%)")
    print(f"🏆 Best Sharpe: {best_sharpe['Qualifier']} ({best_sharpe['Sharpe Ratio']:.2f})")
    print(f"🏆 Lowest Drawdown: {best_drawdown['Qualifier']} ({best_drawdown['Max Drawdown %']:.2f}%)")

    print(f"\n📊 SPY Buy & Hold Return: {spy_return:.2f}%")

    # Save results
    output_file = 'results/qualifier_comparison.csv'
    Path('results').mkdir(exist_ok=True)
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to: {output_file}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    print("\n💡 Key Insights:")
    print("   1. Compare Total Return % across qualifiers")
    print("   2. Check Sharpe Ratio (risk-adjusted returns)")
    print("   3. Evaluate Max Drawdown (worst loss)")
    print("   4. Look for consistency (Win Rate, Profit Factor)")
    print("   5. Consider trade frequency (Total Trades)")
    print("\n   ATR-based qualifiers should show:")
    print("   - More consistent returns (higher Sharpe)")
    print("   - Lower drawdowns (volatility-adjusted)")
    print("   - Better risk management (higher Profit Factor)")

    print("\n" + "="*80)
