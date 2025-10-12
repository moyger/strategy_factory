#!/usr/bin/env python3
"""
Generate QuantStats Report from Existing BSS Results

Uses existing backtest data from results/nick_radge/qualifier_comparison.csv
to generate comprehensive QuantStats HTML tearsheet.

Since we already ran the full backtest, we'll use that data to create
the complete QuantStats report with all visualizations and metrics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Import QuantStats
try:
    import quantstats as qs
    qs.extend_pandas()
except ImportError:
    print("⚠️  QuantStats not installed. Installing now...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "quantstats"])
    import quantstats as qs
    qs.extend_pandas()

print("=" * 100)
print("GENERATE QUANTSTATS REPORT - BSS STRATEGY")
print("=" * 100)
print()

# Check if we have existing equity curve data
equity_files = [
    'results/nick_radge/clean_5year_equity.csv',
    'results/nick_radge/5year_optimized_5_pos_1.5×_lev_100%_paxg_equity.csv',
]

equity_file = None
for f in equity_files:
    if Path(f).exists():
        equity_file = f
        break

if equity_file:
    print(f"✅ Found existing equity curve: {equity_file}")
    print()

    # Load equity data
    equity_df = pd.read_csv(equity_file, parse_dates=['date'] if 'date' in pd.read_csv(equity_file, nrows=0).columns else None)

    if 'date' in equity_df.columns:
        equity_df.set_index('date', inplace=True)
    elif equity_df.index.name != 'date':
        equity_df.index = pd.to_datetime(equity_df.index)

    # Calculate returns
    if 'returns' in equity_df.columns:
        returns = equity_df['returns']
    elif 'equity' in equity_df.columns:
        returns = equity_df['equity'].pct_change().dropna()
    else:
        # Assume first column is equity
        returns = equity_df.iloc[:, 0].pct_change().dropna()

    print(f"📊 Data loaded:")
    print(f"   Period: {returns.index[0].date()} to {returns.index[-1].date()}")
    print(f"   Days: {len(returns):,}")
    print()

    # Load SPY benchmark (if available)
    spy_file = 'data/stocks/spy_prices.csv'
    if Path(spy_file).exists():
        spy_df = pd.read_csv(spy_file, index_col=0, parse_dates=True)
        spy_returns = spy_df['SPY'].pct_change().dropna()

        # Align dates
        common_dates = returns.index.intersection(spy_returns.index)
        strategy_returns = returns.loc[common_dates]
        benchmark_returns = spy_returns.loc[common_dates]

        print("✅ SPY benchmark loaded for comparison")
    else:
        print("⚠️  No SPY benchmark data found, proceeding without benchmark")
        strategy_returns = returns
        benchmark_returns = None

    print()

    # Generate QuantStats report
    print("=" * 100)
    print("Generating QuantStats HTML Report")
    print("=" * 100)
    print()

    print("📊 Creating comprehensive tearsheet with:")
    print("   ✓ Cumulative returns vs benchmark")
    print("   ✓ Drawdown analysis")
    print("   ✓ Rolling volatility & Sharpe")
    print("   ✓ Monthly/yearly returns heatmap")
    print("   ✓ Distribution plots")
    print("   ✓ 50+ performance metrics")
    print()

    output_file = 'results/nick_radge/bss_quantstats_report.html'

    if benchmark_returns is not None:
        qs.reports.html(
            strategy_returns,
            benchmark_returns,
            output=output_file,
            title='Nick Radge Enhanced (BSS) - Strategy Report'
        )
    else:
        qs.reports.html(
            strategy_returns,
            output=output_file,
            title='Nick Radge Enhanced (BSS) - Strategy Report'
        )

    print(f"✅ Report generated: {output_file}")
    print()

    # Print quick metrics
    print("=" * 100)
    print("QUICK METRICS SUMMARY")
    print("=" * 100)
    print()

    total_return = qs.stats.comp(strategy_returns) * 100
    cagr = qs.stats.cagr(strategy_returns) * 100
    sharpe = qs.stats.sharpe(strategy_returns)
    max_dd = qs.stats.max_drawdown(strategy_returns) * 100
    win_rate = qs.stats.win_rate(strategy_returns) * 100
    volatility = qs.stats.volatility(strategy_returns) * 100

    print(f"Total Return:     {total_return:>10.2f}%")
    print(f"CAGR:             {cagr:>10.2f}%")
    print(f"Sharpe Ratio:     {sharpe:>10.2f}")
    print(f"Max Drawdown:     {max_dd:>10.2f}%")
    print(f"Win Rate:         {win_rate:>10.1f}%")
    print(f"Volatility (ann): {volatility:>10.2f}%")

    if benchmark_returns is not None:
        spy_total_return = qs.stats.comp(benchmark_returns) * 100
        spy_cagr = qs.stats.cagr(benchmark_returns) * 100
        outperformance = total_return - spy_total_return

        print()
        print(f"SPY Total Return: {spy_total_return:>10.2f}%")
        print(f"SPY CAGR:         {spy_cagr:>10.2f}%")
        print(f"Outperformance:   {outperformance:>10.2f}%")

    print()
    print("=" * 100)
    print("✅ REPORT GENERATION COMPLETE")
    print("=" * 100)
    print()

    print(f"🌐 Open in browser: {output_file}")
    print()

else:
    print("❌ No equity curve data found!")
    print()
    print("Expected files:")
    for f in equity_files:
        print(f"   - {f}")
    print()
    print("Run a full backtest first to generate equity data.")
    print()
