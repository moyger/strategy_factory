"""
Generate QuantStats Report for FIXED Nick Radge BSS Strategy

Creates comprehensive HTML report with:
- 50+ performance metrics
- Cumulative returns chart
- Drawdown analysis
- Monthly/yearly returns heatmaps
- Rolling statistics
- Risk metrics
- Distribution plots
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
import quantstats as qs
import importlib.util

# Extend pandas for QuantStats
qs.extend_pandas()

# Import the fixed strategy
spec = importlib.util.spec_from_file_location(
    "nick_radge_bss_fixed",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
bss_fixed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bss_fixed_module)
NickRadgeFixed = bss_fixed_module.NickRadgeEnhanced

from strategies.nick_radge_bss_strategy import download_sp500_stocks, download_spy

print("="*80)
print("GENERATING QUANTSTATS REPORT - FIXED NICK RADGE BSS")
print("="*80)

# Configuration
START_DATE = '2020-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 5000
NUM_STOCKS = 50

print(f"\n⚙️  Configuration:")
print(f"   Starting Capital: ${INITIAL_CAPITAL:,}")
print(f"   Period: {START_DATE} to {END_DATE}")
print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks")

# Download data
print(f"\n" + "="*80)
print("DOWNLOADING DATA")
print("="*80)

prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)
spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

# Add GLD
print(f"\n📊 Downloading GLD (bear market asset)...")
gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
if isinstance(gld_data.columns, pd.MultiIndex):
    gld_data.columns = gld_data.columns.get_level_values(0)
prices['GLD'] = gld_data['Close']

# Align dates
common_dates = prices.index.intersection(spy_prices.index)
prices = prices.loc[common_dates]
spy_prices = spy_prices.loc[common_dates]

print(f"\n✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")

# Run backtest
print(f"\n" + "="*80)
print("RUNNING BACKTEST")
print("="*80)

strategy = NickRadgeFixed(
    portfolio_size=7,
    qualifier_type='bss',
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    bear_market_asset='GLD',
    qualifier_params={'poi_period': 100, 'atr_period': 14, 'k': 2.0}
)

portfolio = strategy.backtest(
    prices=prices,
    spy_prices=spy_prices,
    initial_capital=INITIAL_CAPITAL,
    fees=0.001,
    slippage=0.0005
)

# Extract returns
print(f"\n📊 Extracting returns for QuantStats...")

# Get portfolio value over time
portfolio_value = portfolio.value()
if isinstance(portfolio_value, pd.DataFrame):
    portfolio_value = portfolio_value.sum(axis=1)

# Calculate returns
strategy_returns = portfolio_value.pct_change().dropna()

# Get SPY returns
spy_returns = spy_prices.pct_change().dropna()

# Align returns
common_dates = strategy_returns.index.intersection(spy_returns.index)
strategy_returns = strategy_returns.loc[common_dates]
spy_returns = spy_returns.loc[common_dates]

print(f"   Strategy returns: {len(strategy_returns)} days")
print(f"   Benchmark returns: {len(spy_returns)} days")

# Generate report
print(f"\n" + "="*80)
print("GENERATING QUANTSTATS REPORT")
print("="*80)

output_dir = Path(__file__).parent.parent / 'results' / 'nick_radge_bss_fixed'
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / f'quantstats_report_fixed_${INITIAL_CAPITAL}.html'

print(f"\n📊 Generating comprehensive HTML report...")
print(f"   This includes:")
print(f"   - 50+ performance metrics")
print(f"   - Monthly/yearly returns heatmaps")
print(f"   - Drawdown analysis with underwater plot")
print(f"   - Rolling Sharpe, volatility, beta charts")
print(f"   - Distribution plots")
print(f"   - Monte Carlo simulation")
print(f"   - And much more...")

# Generate full HTML report
qs.reports.html(
    strategy_returns,
    benchmark=spy_returns,
    output=str(output_file),
    title=f'Nick Radge BSS FIXED Strategy - ${INITIAL_CAPITAL:,} Starting Capital',
    download_filename=f'nick_radge_bss_fixed_report_${INITIAL_CAPITAL}.html'
)

print(f"\n✅ Report generated successfully!")
print(f"   Location: {output_file}")

# Generate detailed metrics CSV
print(f"\n📊 Generating detailed metrics CSV...")

# Calculate metrics
total_return = qs.stats.comp(strategy_returns) * 100
cagr = qs.stats.cagr(strategy_returns) * 100
sharpe = qs.stats.sharpe(strategy_returns)
sortino = qs.stats.sortino(strategy_returns)
max_dd = qs.stats.max_drawdown(strategy_returns) * 100
calmar = qs.stats.calmar(strategy_returns)
volatility = qs.stats.volatility(strategy_returns) * 100
win_rate = qs.stats.win_rate(strategy_returns) * 100
best_day = strategy_returns.max() * 100
worst_day = strategy_returns.min() * 100
avg_return = strategy_returns.mean() * 100

# SPY metrics
spy_total = qs.stats.comp(spy_returns) * 100
spy_cagr = qs.stats.cagr(spy_returns) * 100

# Beta and correlation
covariance = strategy_returns.cov(spy_returns)
variance = spy_returns.var()
beta = covariance / variance if variance != 0 else 0

correlation = strategy_returns.corr(spy_returns)

# Information ratio
ir = qs.stats.information_ratio(strategy_returns, spy_returns)

# Build metrics dataframe
metrics_data = {
    'Metric': [],
    'Value': []
}

metrics_data['Metric'].append('Starting Capital')
metrics_data['Value'].append(f'${INITIAL_CAPITAL:,}')

final_value = portfolio_value.iloc[-1]
metrics_data['Metric'].append('Final Value')
metrics_data['Value'].append(f'${final_value:,.2f}')

metrics_data['Metric'].append('Total Return')
metrics_data['Value'].append(f'{total_return:.2f}%')

metrics_data['Metric'].append('CAGR')
metrics_data['Value'].append(f'{cagr:.2f}%')

metrics_data['Metric'].append('Sharpe Ratio')
metrics_data['Value'].append(f'{sharpe:.2f}')

metrics_data['Metric'].append('Sortino Ratio')
metrics_data['Value'].append(f'{sortino:.2f}')

metrics_data['Metric'].append('Max Drawdown')
metrics_data['Value'].append(f'{max_dd:.2f}%')

metrics_data['Metric'].append('Calmar Ratio')
metrics_data['Value'].append(f'{calmar:.2f}')

metrics_data['Metric'].append('Volatility (Annual)')
metrics_data['Value'].append(f'{volatility:.2f}%')

metrics_data['Metric'].append('Win Rate')
metrics_data['Value'].append(f'{win_rate:.2f}%')

metrics_data['Metric'].append('Best Day')
metrics_data['Value'].append(f'{best_day:.2f}%')

metrics_data['Metric'].append('Worst Day')
metrics_data['Value'].append(f'{worst_day:.2f}%')

metrics_data['Metric'].append('Avg Daily Return')
metrics_data['Value'].append(f'{avg_return:.4f}%')

positive_days = (strategy_returns > 0).sum()
negative_days = (strategy_returns < 0).sum()

metrics_data['Metric'].append('Positive Days')
metrics_data['Value'].append(f'{positive_days}')

metrics_data['Metric'].append('Negative Days')
metrics_data['Value'].append(f'{negative_days}')

metrics_data['Metric'].append('SPY Total Return')
metrics_data['Value'].append(f'{spy_total:.2f}%')

metrics_data['Metric'].append('SPY CAGR')
metrics_data['Value'].append(f'{spy_cagr:.2f}%')

metrics_data['Metric'].append('Outperformance vs SPY')
outperformance = total_return - spy_total
metrics_data['Value'].append(f'{outperformance:+.2f}%')

metrics_data['Metric'].append('Beta to SPY')
metrics_data['Value'].append(f'{beta:.2f}')

metrics_data['Metric'].append('Correlation to SPY')
metrics_data['Value'].append(f'{correlation:.2f}')

metrics_data['Metric'].append('Information Ratio')
metrics_data['Value'].append(f'{ir:.2f}')

# Professional standards
metrics_data['Metric'].append('')
metrics_data['Value'].append('')

metrics_data['Metric'].append('=== PROFESSIONAL STANDARDS ===')
metrics_data['Value'].append('')

metrics_data['Metric'].append('Sharpe >= 1.6')
metrics_data['Value'].append('✅ PASS' if sharpe >= 1.6 else '❌ FAIL')

metrics_data['Metric'].append('Sortino >= 2.2')
metrics_data['Value'].append('✅ PASS' if sortino >= 2.2 else '❌ FAIL')

metrics_data['Metric'].append('Max DD <= 22%')
metrics_data['Value'].append('✅ PASS' if abs(max_dd) <= 22 else '❌ FAIL')

metrics_data['Metric'].append('Calmar >= 1.2')
metrics_data['Value'].append('✅ PASS' if calmar >= 1.2 else '❌ FAIL')

# Save metrics
metrics_df = pd.DataFrame(metrics_data)
metrics_file = output_dir / f'metrics_fixed_${INITIAL_CAPITAL}.csv'
metrics_df.to_csv(metrics_file, index=False)
print(f"✅ Metrics saved: {metrics_file}")

# Generate monthly returns table
print(f"\n📊 Generating monthly returns table...")
monthly_returns = qs.stats.monthly_returns(strategy_returns) * 100
monthly_file = output_dir / f'monthly_returns_fixed_${INITIAL_CAPITAL}.csv'
monthly_returns.to_csv(monthly_file)
print(f"✅ Monthly returns saved: {monthly_file}")

# Summary
print(f"\n" + "="*80)
print("REPORT GENERATION COMPLETE")
print("="*80)

print(f"\n📂 Generated Files:")
print(f"   1. {output_file.name}")
print(f"      → Full HTML report with 50+ metrics and charts")
print(f"   2. {metrics_file.name}")
print(f"      → CSV with key performance metrics")
print(f"   3. {monthly_file.name}")
print(f"      → CSV with monthly returns breakdown")

print(f"\n🌐 To view the report:")
print(f"   Option 1: Open in browser")
print(f"      open {output_file}")
print(f"   Option 2: Double-click the file in Finder/Explorer")

print(f"\n📊 Report Contents:")
print(f"   ✅ Cumulative Returns Chart")
print(f"   ✅ Drawdown Chart (underwater plot)")
print(f"   ✅ Monthly Returns Heatmap")
print(f"   ✅ Distribution of Returns")
print(f"   ✅ Rolling Sharpe Ratio")
print(f"   ✅ Rolling Volatility")
print(f"   ✅ Rolling Beta")
print(f"   ✅ Daily Returns")
print(f"   ✅ Risk Metrics Table")
print(f"   ✅ Worst 5 Drawdowns")
print(f"   ✅ Monthly Returns Table")
print(f"   ✅ Yearly Returns Comparison")
print(f"   ✅ And much more...")

print(f"\n" + "="*80)
print("✅ Done!")
print("="*80)
