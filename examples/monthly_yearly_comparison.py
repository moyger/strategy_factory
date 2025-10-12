#!/usr/bin/env python3
"""
Monthly and Yearly Performance Comparison: BSS vs ROC

Comprehensive analysis of returns by month and year to understand
when each qualifier performs better.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy, download_sp500_stocks, download_spy
from strategy_factory.performance_qualifiers import get_qualifier


def run_strategy_with_qualifier(qualifier_name, prices, spy_prices, initial_capital=10000):
    """Run strategy and return portfolio equity curve"""

    strategy = NickRadgeMomentumStrategy(
        portfolio_size=7,
        roc_period=100,
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

    # Get qualifier
    if qualifier_name == 'roc':
        qualifier = None
    elif qualifier_name == 'bss':
        qualifier = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)
    else:
        qualifier = get_qualifier(qualifier_name)

    # Monkey-patch if needed
    if qualifier is not None:
        def new_rank_stocks(prices, indicators, date, benchmark_roc=None):
            if date not in prices.index:
                return pd.DataFrame()

            scores = qualifier.calculate(prices)
            if date not in scores.index:
                return pd.DataFrame()

            score_row = scores.loc[date]
            above_ma = indicators['above_ma'].loc[date]

            valid_stocks = above_ma[above_ma == True].index
            if strategy.bear_market_asset:
                valid_stocks = [s for s in valid_stocks if s != strategy.bear_market_asset]
            valid_stocks = [s for s in valid_stocks if pd.notna(score_row[s])]

            if len(valid_stocks) == 0:
                return pd.DataFrame()

            scores_valid = score_row[valid_stocks].dropna()
            if len(scores_valid) == 0:
                return pd.DataFrame()

            if strategy.use_relative_strength and benchmark_roc is not None and date in benchmark_roc.index:
                benchmark_score = benchmark_roc.loc[date]
                if pd.notna(benchmark_score):
                    scores_valid = scores_valid[scores_valid > benchmark_score]

            if len(scores_valid) == 0:
                return pd.DataFrame()

            ranked = scores_valid.sort_values(ascending=False)
            return pd.DataFrame({'ticker': ranked.index, 'roc': ranked.values})

        strategy.rank_stocks = new_rank_stocks

    # Run backtest
    portfolio = strategy.backtest(prices=prices, spy_prices=spy_prices,
                                 initial_capital=initial_capital, fees=0.001, slippage=0.0005)

    return portfolio


def calculate_monthly_returns(portfolio):
    """Calculate monthly returns from portfolio equity curve"""
    equity = portfolio.value()
    if isinstance(equity, pd.DataFrame):
        equity = equity.sum(axis=1)

    # Resample to month-end
    monthly_equity = equity.resample('M').last()
    monthly_returns = monthly_equity.pct_change() * 100

    return monthly_returns


def calculate_yearly_returns(portfolio):
    """Calculate yearly returns from portfolio equity curve"""
    equity = portfolio.value()
    if isinstance(equity, pd.DataFrame):
        equity = equity.sum(axis=1)

    # Resample to year-end
    yearly_equity = equity.resample('Y').last()
    yearly_returns = yearly_equity.pct_change() * 100

    return yearly_returns


def create_comparison_tables(roc_portfolio, bss_portfolio, spy_prices):
    """Create comprehensive comparison tables"""

    print("\n" + "="*100)
    print("MONTHLY PERFORMANCE COMPARISON: BSS vs ROC")
    print("="*100)

    # Get monthly returns
    roc_monthly = calculate_monthly_returns(roc_portfolio)
    bss_monthly = calculate_monthly_returns(bss_portfolio)

    # SPY monthly returns
    spy_monthly = spy_prices.resample('M').last().pct_change() * 100

    # Combine into dataframe
    comparison = pd.DataFrame({
        'ROC': roc_monthly,
        'BSS': bss_monthly,
        'SPY': spy_monthly
    }).dropna()

    comparison['BSS-ROC'] = comparison['BSS'] - comparison['ROC']
    comparison['BSS_Wins'] = comparison['BSS'] > comparison['ROC']

    # Add year and month columns
    comparison['Year'] = comparison.index.year
    comparison['Month'] = comparison.index.month_name()

    # Monthly statistics
    print("\n📊 MONTHLY STATISTICS")
    print("-" * 100)
    print(f"{'Metric':<30} {'ROC':>12} {'BSS':>12} {'SPY':>12} {'Difference':>12}")
    print("-" * 100)

    print(f"{'Average Monthly Return':<30} {comparison['ROC'].mean():>11.2f}% {comparison['BSS'].mean():>11.2f}% "
          f"{comparison['SPY'].mean():>11.2f}% {comparison['BSS-ROC'].mean():>11.2f}%")
    print(f"{'Median Monthly Return':<30} {comparison['ROC'].median():>11.2f}% {comparison['BSS'].median():>11.2f}% "
          f"{comparison['SPY'].median():>11.2f}% {comparison['BSS-ROC'].median():>11.2f}%")
    print(f"{'Monthly Volatility (Std)':<30} {comparison['ROC'].std():>11.2f}% {comparison['BSS'].std():>11.2f}% "
          f"{comparison['SPY'].std():>11.2f}% {comparison['BSS-ROC'].std():>11.2f}%")
    print(f"{'Best Month':<30} {comparison['ROC'].max():>11.2f}% {comparison['BSS'].max():>11.2f}% "
          f"{comparison['SPY'].max():>11.2f}%")
    print(f"{'Worst Month':<30} {comparison['ROC'].min():>11.2f}% {comparison['BSS'].min():>11.2f}% "
          f"{comparison['SPY'].min():>11.2f}%")
    print(f"{'Positive Months':<30} {(comparison['ROC'] > 0).sum():>11} {(comparison['BSS'] > 0).sum():>11} "
          f"{(comparison['SPY'] > 0).sum():>11}")
    print(f"{'Negative Months':<30} {(comparison['ROC'] < 0).sum():>11} {(comparison['BSS'] < 0).sum():>11} "
          f"{(comparison['SPY'] < 0).sum():>11}")
    print(f"{'BSS Wins (months)':<30} {comparison['BSS_Wins'].sum():>11} / {len(comparison)}")
    print(f"{'ROC Wins (months)':<30} {(~comparison['BSS_Wins']).sum():>11} / {len(comparison)}")
    print(f"{'BSS Win Rate':<30} {comparison['BSS_Wins'].mean()*100:>10.1f}%")

    # Show all months
    print("\n📅 MONTH-BY-MONTH BREAKDOWN")
    print("-" * 100)
    print(f"{'Date':<12} {'ROC':>10} {'BSS':>10} {'SPY':>10} {'Diff':>10} {'Winner':<10}")
    print("-" * 100)

    for idx, row in comparison.iterrows():
        winner = 'BSS ✓' if row['BSS'] > row['ROC'] else 'ROC ✓'
        date_str = idx.strftime('%Y-%m')
        print(f"{date_str:<12} {row['ROC']:>9.2f}% {row['BSS']:>9.2f}% {row['SPY']:>9.2f}% "
              f"{row['BSS-ROC']:>9.2f}% {winner:<10}")

    # Yearly comparison
    print("\n" + "="*100)
    print("YEARLY PERFORMANCE COMPARISON: BSS vs ROC")
    print("="*100)

    # Calculate cumulative returns by year
    yearly_comparison = comparison.groupby('Year').agg({
        'ROC': lambda x: ((1 + x/100).prod() - 1) * 100,
        'BSS': lambda x: ((1 + x/100).prod() - 1) * 100,
        'SPY': lambda x: ((1 + x/100).prod() - 1) * 100
    })

    yearly_comparison['BSS-ROC'] = yearly_comparison['BSS'] - yearly_comparison['ROC']
    yearly_comparison['BSS_Wins'] = yearly_comparison['BSS'] > yearly_comparison['ROC']

    print("\n📊 YEAR-BY-YEAR RETURNS")
    print("-" * 100)
    print(f"{'Year':<10} {'ROC':>12} {'BSS':>12} {'SPY':>12} {'Difference':>12} {'Winner':<10}")
    print("-" * 100)

    for year, row in yearly_comparison.iterrows():
        winner = 'BSS ✓' if row['BSS'] > row['ROC'] else 'ROC ✓'
        print(f"{year:<10} {row['ROC']:>11.2f}% {row['BSS']:>11.2f}% {row['SPY']:>11.2f}% "
              f"{row['BSS-ROC']:>11.2f}% {winner:<10}")

    print("-" * 100)
    print(f"{'AVERAGE':<10} {yearly_comparison['ROC'].mean():>11.2f}% {yearly_comparison['BSS'].mean():>11.2f}% "
          f"{yearly_comparison['SPY'].mean():>11.2f}% {yearly_comparison['BSS-ROC'].mean():>11.2f}%")

    print(f"\n🏆 BSS won {yearly_comparison['BSS_Wins'].sum()} out of {len(yearly_comparison)} years "
          f"({yearly_comparison['BSS_Wins'].mean()*100:.1f}%)")

    # Quarter-by-quarter analysis
    print("\n" + "="*100)
    print("QUARTERLY PERFORMANCE COMPARISON")
    print("="*100)

    comparison['Quarter'] = comparison.index.to_period('Q')
    quarterly_comparison = comparison.groupby('Quarter').agg({
        'ROC': lambda x: ((1 + x/100).prod() - 1) * 100,
        'BSS': lambda x: ((1 + x/100).prod() - 1) * 100,
        'SPY': lambda x: ((1 + x/100).prod() - 1) * 100
    })

    quarterly_comparison['BSS-ROC'] = quarterly_comparison['BSS'] - quarterly_comparison['ROC']
    quarterly_comparison['BSS_Wins'] = quarterly_comparison['BSS'] > quarterly_comparison['ROC']

    print("\n📊 QUARTER-BY-QUARTER RETURNS")
    print("-" * 100)
    print(f"{'Quarter':<12} {'ROC':>12} {'BSS':>12} {'SPY':>12} {'Difference':>12} {'Winner':<10}")
    print("-" * 100)

    for quarter, row in quarterly_comparison.iterrows():
        winner = 'BSS ✓' if row['BSS'] > row['ROC'] else 'ROC ✓'
        print(f"{str(quarter):<12} {row['ROC']:>11.2f}% {row['BSS']:>11.2f}% {row['SPY']:>11.2f}% "
              f"{row['BSS-ROC']:>11.2f}% {winner:<10}")

    print(f"\n🏆 BSS won {quarterly_comparison['BSS_Wins'].sum()} out of {len(quarterly_comparison)} quarters "
          f"({quarterly_comparison['BSS_Wins'].mean()*100:.1f}%)")

    return comparison, yearly_comparison, quarterly_comparison


def create_visualizations(comparison, yearly_comparison, quarterly_comparison):
    """Create comparison charts"""

    fig = plt.figure(figsize=(20, 12))

    # 1. Monthly returns comparison
    ax1 = plt.subplot(3, 2, 1)
    x = range(len(comparison))
    width = 0.35
    ax1.bar([i - width/2 for i in x], comparison['ROC'], width, label='ROC', alpha=0.7, color='blue')
    ax1.bar([i + width/2 for i in x], comparison['BSS'], width, label='BSS', alpha=0.7, color='red')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.set_title('Monthly Returns Comparison', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Return (%)')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # 2. Cumulative returns
    ax2 = plt.subplot(3, 2, 2)
    roc_cumulative = (1 + comparison['ROC']/100).cumprod() * 100 - 100
    bss_cumulative = (1 + comparison['BSS']/100).cumprod() * 100 - 100
    spy_cumulative = (1 + comparison['SPY']/100).cumprod() * 100 - 100

    ax2.plot(comparison.index, roc_cumulative, label='ROC', linewidth=2, color='blue')
    ax2.plot(comparison.index, bss_cumulative, label='BSS', linewidth=2, color='red')
    ax2.plot(comparison.index, spy_cumulative, label='SPY', linewidth=2, color='green', linestyle='--')
    ax2.set_title('Cumulative Returns Over Time', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Cumulative Return (%)')
    ax2.legend()
    ax2.grid(alpha=0.3)

    # 3. Yearly returns
    ax3 = plt.subplot(3, 2, 3)
    x = range(len(yearly_comparison))
    width = 0.35
    ax3.bar([i - width/2 for i in x], yearly_comparison['ROC'], width, label='ROC', alpha=0.7, color='blue')
    ax3.bar([i + width/2 for i in x], yearly_comparison['BSS'], width, label='BSS', alpha=0.7, color='red')
    ax3.set_xticks(x)
    ax3.set_xticklabels(yearly_comparison.index, rotation=0)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Yearly Returns Comparison', fontweight='bold', fontsize=12)
    ax3.set_ylabel('Annual Return (%)')
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    # 4. Monthly difference (BSS - ROC)
    ax4 = plt.subplot(3, 2, 4)
    colors = ['green' if x > 0 else 'red' for x in comparison['BSS-ROC']]
    ax4.bar(range(len(comparison)), comparison['BSS-ROC'], color=colors, alpha=0.6)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_title('Monthly Performance Difference (BSS - ROC)', fontweight='bold', fontsize=12)
    ax4.set_ylabel('Difference (%)')
    ax4.grid(axis='y', alpha=0.3)

    # 5. Win rate by year
    ax5 = plt.subplot(3, 2, 5)
    win_rates = []
    years = []
    for year in yearly_comparison.index:
        year_data = comparison[comparison['Year'] == year]
        win_rate = (year_data['BSS'] > year_data['ROC']).mean() * 100
        win_rates.append(win_rate)
        years.append(year)

    ax5.bar(range(len(years)), win_rates, alpha=0.7, color='purple')
    ax5.axhline(y=50, color='red', linestyle='--', label='50% threshold')
    ax5.set_xticks(range(len(years)))
    ax5.set_xticklabels(years, rotation=0)
    ax5.set_title('BSS Monthly Win Rate by Year', fontweight='bold', fontsize=12)
    ax5.set_ylabel('Win Rate (%)')
    ax5.legend()
    ax5.grid(axis='y', alpha=0.3)

    # 6. Quarterly returns
    ax6 = plt.subplot(3, 2, 6)
    x = range(len(quarterly_comparison))
    width = 0.35
    ax6.bar([i - width/2 for i in x], quarterly_comparison['ROC'], width, label='ROC', alpha=0.7, color='blue')
    ax6.bar([i + width/2 for i in x], quarterly_comparison['BSS'], width, label='BSS', alpha=0.7, color='red')
    ax6.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax6.set_title('Quarterly Returns Comparison', fontweight='bold', fontsize=12)
    ax6.set_ylabel('Quarterly Return (%)')
    ax6.legend()
    ax6.grid(axis='y', alpha=0.3)
    # Rotate x-labels for readability
    plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    # Save
    output_path = 'results/monthly_yearly_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✅ Chart saved: {output_path}")

    return fig


if __name__ == "__main__":
    print("="*100)
    print("MONTHLY & YEARLY COMPARISON: BSS vs ROC")
    print("="*100)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Capital: ${INITIAL_CAPITAL:,}")

    # Download data
    print(f"\n{'='*100}")
    print("DOWNLOADING DATA")
    print("="*100)

    prices = download_sp500_stocks(num_stocks=50, start_date=START_DATE, end_date=END_DATE)

    # Add GLD
    if 'GLD' not in prices.columns:
        print(f"\n⚠️  Adding GLD...")
        gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
        if isinstance(gld_data.columns, pd.MultiIndex):
            gld_data.columns = gld_data.columns.get_level_values(0)
        prices['GLD'] = gld_data['Close']
        prices = prices.dropna()
        print(f"✅ GLD added")

    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready: {len(prices)} days, {len(prices.columns)} stocks")

    # Run strategies
    print(f"\n{'='*100}")
    print("RUNNING BACKTESTS")
    print("="*100)

    print("\n🔵 Running ROC strategy...")
    roc_portfolio = run_strategy_with_qualifier('roc', prices, spy_prices, INITIAL_CAPITAL)

    print("\n🔴 Running BSS strategy...")
    bss_portfolio = run_strategy_with_qualifier('bss', prices, spy_prices, INITIAL_CAPITAL)

    # Create comparisons
    comparison, yearly_comparison, quarterly_comparison = create_comparison_tables(
        roc_portfolio, bss_portfolio, spy_prices
    )

    # Create visualizations
    create_visualizations(comparison, yearly_comparison, quarterly_comparison)

    # Save to CSV
    comparison.to_csv('results/monthly_comparison.csv')
    yearly_comparison.to_csv('results/yearly_comparison.csv')
    quarterly_comparison.to_csv('results/quarterly_comparison.csv')

    print(f"\n💾 Data saved:")
    print(f"   - results/monthly_comparison.csv")
    print(f"   - results/yearly_comparison.csv")
    print(f"   - results/quarterly_comparison.csv")
    print(f"   - results/monthly_yearly_comparison.png")

    print(f"\n{'='*100}")
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
