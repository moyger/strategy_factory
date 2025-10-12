"""
Generate QuantStats Report for Nick Radge BSS Strategy

Creates comprehensive HTML report with 50+ metrics and charts
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import quantstats as qs
from strategies.nick_radge_bss_strategy import NickRadgeBSS, download_sp500_stocks, download_spy

# Extend pandas plotting backend (required for quantstats)
qs.extend_pandas()

print("="*80)
print("GENERATING QUANTSTATS REPORT - NICK RADGE BSS STRATEGY")
print("="*80)

# Configuration
START_DATE = '2020-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 5000  # Use $5,000 as requested
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

# Create strategy
print(f"\n" + "="*80)
print("RUNNING BACKTEST")
print("="*80)

strategy = NickRadgeBSS(
    portfolio_size=7,
    poi_period=100,
    atr_period=14,
    atr_multiplier=2.0,
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
    initial_capital=INITIAL_CAPITAL,
    fees=0.001,
    slippage=0.0005
)

# Calculate SPY return
spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

# Print basic results
strategy.print_results(portfolio, prices, spy_return)

# =============================================================================
# GENERATE QUANTSTATS REPORT
# =============================================================================

print("\n" + "="*80)
print("GENERATING QUANTSTATS REPORT")
print("="*80)

# Get strategy returns
pf_value = portfolio.value()
if isinstance(pf_value, pd.DataFrame):
    pf_value = pf_value.iloc[:, 0]

strategy_returns = pf_value.pct_change().fillna(0)

# Get benchmark (SPY) returns
benchmark_returns = spy_prices.pct_change().fillna(0)

# Align returns
common_idx = strategy_returns.index.intersection(benchmark_returns.index)
strategy_returns = strategy_returns.loc[common_idx]
benchmark_returns = benchmark_returns.loc[common_idx]

# Create output directory
output_dir = Path('results/nick_radge_bss')
output_dir.mkdir(parents=True, exist_ok=True)

# Generate HTML report
output_file = output_dir / f'nick_radge_bss_quantstats_report_${INITIAL_CAPITAL}.html'

print(f"\n📊 Generating comprehensive HTML report...")
print(f"   This includes:")
print(f"   - 50+ performance metrics")
print(f"   - Monthly/yearly returns heatmaps")
print(f"   - Drawdown analysis with underwater plot")
print(f"   - Rolling Sharpe, volatility, beta charts")
print(f"   - Distribution plots")
print(f"   - Monte Carlo simulation")
print(f"   - And much more...")

# Generate full HTML report with all metrics
qs.reports.html(
    strategy_returns,
    benchmark=benchmark_returns,
    output=str(output_file),
    title=f'Nick Radge BSS Strategy - ${INITIAL_CAPITAL:,} Starting Capital',
    download_filename=f'nick_radge_bss_report_${INITIAL_CAPITAL}.html'
)

print(f"\n✅ Report generated successfully!")
print(f"   Location: {output_file}")

# Generate additional standalone metrics file
print(f"\n📊 Generating detailed metrics CSV...")

metrics_data = {
    'Metric': [],
    'Value': []
}

# Calculate comprehensive metrics
metrics_data['Metric'].append('Starting Capital')
metrics_data['Value'].append(f'${INITIAL_CAPITAL:,}')

metrics_data['Metric'].append('Final Value')
final_value = pf_value.iloc[-1]
metrics_data['Value'].append(f'${final_value:,.2f}')

metrics_data['Metric'].append('Total Return')
total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100
metrics_data['Value'].append(f'{total_return:.2f}%')

metrics_data['Metric'].append('CAGR')
years = (pf_value.index[-1] - pf_value.index[0]).days / 365.25
cagr = (((final_value / INITIAL_CAPITAL) ** (1 / years)) - 1) * 100
metrics_data['Value'].append(f'{cagr:.2f}%')

metrics_data['Metric'].append('Sharpe Ratio')
sharpe = qs.stats.sharpe(strategy_returns)
metrics_data['Value'].append(f'{sharpe:.2f}')

metrics_data['Metric'].append('Sortino Ratio')
sortino = qs.stats.sortino(strategy_returns)
metrics_data['Value'].append(f'{sortino:.2f}')

metrics_data['Metric'].append('Max Drawdown')
max_dd = qs.stats.max_drawdown(strategy_returns)
metrics_data['Value'].append(f'{max_dd*100:.2f}%')

metrics_data['Metric'].append('Calmar Ratio')
calmar = qs.stats.calmar(strategy_returns)
metrics_data['Value'].append(f'{calmar:.2f}')

metrics_data['Metric'].append('Volatility (Annual)')
volatility = qs.stats.volatility(strategy_returns)
metrics_data['Value'].append(f'{volatility*100:.2f}%')

metrics_data['Metric'].append('Win Rate')
win_rate = len(strategy_returns[strategy_returns > 0]) / len(strategy_returns[strategy_returns != 0])
metrics_data['Value'].append(f'{win_rate*100:.2f}%')

metrics_data['Metric'].append('Best Day')
best_day = strategy_returns.max()
metrics_data['Value'].append(f'{best_day*100:.2f}%')

metrics_data['Metric'].append('Worst Day')
worst_day = strategy_returns.min()
metrics_data['Value'].append(f'{worst_day*100:.2f}%')

metrics_data['Metric'].append('Avg Daily Return')
avg_return = strategy_returns.mean()
metrics_data['Value'].append(f'{avg_return*100:.4f}%')

metrics_data['Metric'].append('Positive Days')
positive_days = (strategy_returns > 0).sum()
metrics_data['Value'].append(f'{positive_days}')

metrics_data['Metric'].append('Negative Days')
negative_days = (strategy_returns < 0).sum()
metrics_data['Value'].append(f'{negative_days}')

# Benchmark comparison
metrics_data['Metric'].append('SPY Total Return')
spy_total_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100
metrics_data['Value'].append(f'{spy_total_return:.2f}%')

metrics_data['Metric'].append('SPY CAGR')
spy_cagr = (((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / years)) - 1) * 100
metrics_data['Value'].append(f'{spy_cagr:.2f}%')

metrics_data['Metric'].append('Outperformance vs SPY')
outperformance = total_return - spy_total_return
metrics_data['Value'].append(f'{outperformance:+.2f}%')

metrics_data['Metric'].append('Beta to SPY')
# Calculate beta manually: Cov(strategy, benchmark) / Var(benchmark)
covariance = strategy_returns.cov(benchmark_returns)
variance = benchmark_returns.var()
beta = covariance / variance if variance != 0 else 0
metrics_data['Value'].append(f'{beta:.2f}')

metrics_data['Metric'].append('Information Ratio')
ir = qs.stats.information_ratio(strategy_returns, benchmark_returns)
metrics_data['Value'].append(f'{ir:.2f}')

# Save metrics
metrics_df = pd.DataFrame(metrics_data)
metrics_file = output_dir / f'nick_radge_bss_metrics_${INITIAL_CAPITAL}.csv'
metrics_df.to_csv(metrics_file, index=False)

print(f"✅ Metrics saved: {metrics_file}")

# Generate monthly returns table
print(f"\n📊 Generating monthly returns table...")
monthly_returns = strategy_returns.resample('ME').apply(lambda x: (1 + x).prod() - 1)
monthly_table = qs.stats.monthly_returns(strategy_returns)
monthly_file = output_dir / f'nick_radge_bss_monthly_returns_${INITIAL_CAPITAL}.csv'
monthly_table.to_csv(monthly_file)
print(f"✅ Monthly returns saved: {monthly_file}")

# Generate trade log (if available)
print(f"\n📊 Extracting trade information...")
try:
    trades = portfolio.trades.records_readable
    if len(trades) > 0:
        trade_file = output_dir / f'nick_radge_bss_trades_${INITIAL_CAPITAL}.csv'
        trades.to_csv(trade_file, index=False)
        print(f"✅ Trade log saved: {trade_file} ({len(trades)} trades)")
except Exception as e:
    print(f"⚠️  Could not extract trade log: {e}")

# =============================================================================
# SUMMARY
# =============================================================================

print("\n" + "="*80)
print("REPORT GENERATION COMPLETE")
print("="*80)

print(f"\n📂 Generated Files:")
print(f"   1. {output_file}")
print(f"      → Full HTML report with 50+ metrics and charts")
print(f"   2. {metrics_file}")
print(f"      → CSV with key performance metrics")
print(f"   3. {monthly_file}")
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

print("\n" + "="*80)
print("✅ Done!")
print("="*80)
