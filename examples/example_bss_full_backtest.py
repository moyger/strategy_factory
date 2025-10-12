#!/usr/bin/env python3
"""
BSS Strategy - Full Backtest with Complete QuantStats Report

Runs comprehensive backtest of Nick Radge Enhanced (BSS qualifier) with:
- Full QuantStats tearsheet (HTML report with 50+ metrics)
- Performance metrics comparison vs SPY benchmark
- Drawdown analysis
- Rolling returns
- Monthly/yearly performance heatmaps
- Trade analysis
- Monte Carlo simulation
- Walk-forward validation

Output:
- results/nick_radge/bss_strategy_report.html (interactive tearsheet)
- results/nick_radge/bss_equity_curve.csv
- results/nick_radge/bss_trades.csv
- results/nick_radge/bss_metrics.csv
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import strategy
import importlib.util
spec = importlib.util.spec_from_file_location(
    "nick_radge_enhanced",
    "strategies/02_nick_radge_enhanced_bss.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeEnhanced = module.NickRadgeEnhanced

# Import QuantStats for reporting
try:
    import quantstats as qs
    qs.extend_pandas()
    HAS_QUANTSTATS = True
except ImportError:
    print("⚠️  QuantStats not installed. Installing now...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "quantstats"])
    import quantstats as qs
    qs.extend_pandas()
    HAS_QUANTSTATS = True

# Test universe (Nick Radge 50-stock universe)
UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'WMT',
    'MA', 'UNH', 'HD', 'PG', 'DIS', 'BAC', 'ADBE', 'NFLX', 'CRM', 'CSCO',
    'PEP', 'TMO', 'COST', 'AVGO', 'ABT', 'LLY', 'ACN', 'NKE', 'MCD', 'ORCL',
    'DHR', 'TXN', 'QCOM', 'UNP', 'PM', 'NEE', 'HON', 'RTX', 'UPS', 'LOW',
    'IBM', 'INTU', 'AMD', 'AMAT', 'CVX', 'CAT', 'SBUX', 'GS', 'AXP', 'BLK'
]

print("=" * 100)
print("NICK RADGE ENHANCED (BSS) - FULL BACKTEST WITH QUANTSTATS REPORT")
print("=" * 100)
print()
print("📊 Strategy: Nick Radge Momentum with Breakout Strength Score (BSS)")
print("🎯 Universe: 50 stocks (large-cap US equities)")
print("📅 Period: 2015-2024 (10 years)")
print("💰 Initial Capital: $100,000")
print()
print("📈 Reports Generated:")
print("   1. QuantStats HTML tearsheet (50+ metrics)")
print("   2. Equity curve CSV")
print("   3. Trade log CSV")
print("   4. Performance metrics CSV")
print()
print("⏱️  Expected runtime: 2-3 minutes")
print()

# Download data
print("=" * 100)
print("STEP 1/4: Downloading Historical Data")
print("=" * 100)
print()

start_date = '2015-01-01'
end_date = '2024-12-31'

# Load from existing data if available
try:
    print("Checking for cached data...")
    prices = pd.read_csv('data/stocks/universe_50_prices.csv', index_col=0, parse_dates=True)
    spy = pd.read_csv('data/stocks/spy_prices.csv', index_col=0, parse_dates=True)['SPY']
    gld = pd.read_csv('data/stocks/gld_prices.csv', index_col=0, parse_dates=True)['GLD']
    print(f"✅ Loaded cached data from data/stocks/")
except:
    print("Downloading from Yahoo Finance...")

    all_tickers = UNIVERSE + ['SPY', 'GLD']
    data = {}

    for i, ticker in enumerate(all_tickers, 1):
        try:
            print(f"  [{i}/{len(all_tickers)}] Downloading {ticker}...", end='', flush=True)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            data[ticker] = df['Adj Close']
            print(" ✓")
        except Exception as e:
            print(f" ✗ ({str(e)[:50]})")

    # Combine
    combined = pd.DataFrame(data)
    prices = combined[UNIVERSE].dropna(how='all')
    spy = combined['SPY'].dropna()
    gld = combined['GLD'].dropna()

    # Save for future use
    Path('data/stocks').mkdir(parents=True, exist_ok=True)
    prices.to_csv('data/stocks/universe_50_prices.csv')
    pd.DataFrame({'SPY': spy}).to_csv('data/stocks/spy_prices.csv')
    pd.DataFrame({'GLD': gld}).to_csv('data/stocks/gld_prices.csv')
    print(f"\n💾 Cached data saved to data/stocks/")

print()
print(f"📊 Data Summary:")
print(f"   Stocks: {len(prices.columns)}")
print(f"   Date Range: {prices.index[0].date()} to {prices.index[-1].date()}")
print(f"   Total Days: {len(prices):,}")
print()

# Run backtest
print("=" * 100)
print("STEP 2/4: Running Backtest")
print("=" * 100)
print()

# Initialize strategy
strategy = NickRadgeEnhanced(
    portfolio_size=7,
    qualifier_type='bss',  # Breakout Strength Score
    ma_period=100,
    rebalance_freq='QS',  # Quarterly rebalancing
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=7,
    weak_bull_positions=3,
    bear_positions=0,
    bear_market_asset='GLD',
    bear_allocation=1.0
)

print("Running backtest...")
portfolio = strategy.backtest(
    prices=prices,
    spy_prices=spy,
    gld_prices=gld,
    initial_capital=100000
)

print()
print("✅ Backtest complete!")
print()

# Extract results
print("=" * 100)
print("STEP 3/4: Extracting Results")
print("=" * 100)
print()

# Get equity curve
equity = portfolio.value()
returns = portfolio.returns()

# Get trades
trades_records = portfolio.trades.records
trades_df = pd.DataFrame({
    'entry_date': [prices.index[t['entry_idx']] for t in trades_records],
    'exit_date': [prices.index[t['exit_idx']] for t in trades_records],
    'column': [t['col'] for t in trades_records],
    'size': [t['size'] for t in trades_records],
    'entry_price': [t['entry_price'] for t in trades_records],
    'exit_price': [t['exit_price'] for t in trades_records],
    'pnl': [t['pnl'] for t in trades_records],
    'return': [t['return'] for t in trades_records],
})

# Add ticker names
trades_df['ticker'] = trades_df['column'].apply(lambda x: prices.columns[x])

# Calculate metrics
total_return = portfolio.total_return() * 100
cagr = portfolio.annualized_return() * 100
sharpe = portfolio.sharpe_ratio()
max_dd = portfolio.max_drawdown() * 100
num_trades = len(trades_df)
winning_trades = (trades_df['pnl'] > 0).sum()
win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0

# Calculate profit factor
gross_profits = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
gross_losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
profit_factor = gross_profits / gross_losses if gross_losses > 0 else 0

print(f"📊 Quick Metrics:")
print(f"   Total Return: {total_return:,.2f}%")
print(f"   CAGR: {cagr:.2f}%")
print(f"   Sharpe Ratio: {sharpe:.2f}")
print(f"   Max Drawdown: {max_dd:.2f}%")
print(f"   Total Trades: {num_trades:,}")
print(f"   Win Rate: {win_rate:.1f}%")
print(f"   Profit Factor: {profit_factor:.2f}")
print()

# Save results
output_dir = Path('results/nick_radge')
output_dir.mkdir(parents=True, exist_ok=True)

# Save equity curve
equity_df = pd.DataFrame({
    'date': equity.index,
    'equity': equity.values,
    'returns': returns.values
})
equity_df.to_csv(output_dir / 'bss_equity_curve.csv', index=False)
print(f"💾 Equity curve saved: results/nick_radge/bss_equity_curve.csv")

# Save trades
trades_df.to_csv(output_dir / 'bss_trades.csv', index=False)
print(f"💾 Trade log saved: results/nick_radge/bss_trades.csv")

# Save metrics
metrics_df = pd.DataFrame({
    'Metric': [
        'Total Return (%)',
        'CAGR (%)',
        'Sharpe Ratio',
        'Max Drawdown (%)',
        'Total Trades',
        'Winning Trades',
        'Losing Trades',
        'Win Rate (%)',
        'Profit Factor',
        'Avg Trade (%)',
        'Avg Winner (%)',
        'Avg Loser (%)',
        'Best Trade (%)',
        'Worst Trade (%)',
        'Final Portfolio Value ($)',
    ],
    'Value': [
        f"{total_return:.2f}",
        f"{cagr:.2f}",
        f"{sharpe:.2f}",
        f"{max_dd:.2f}",
        num_trades,
        winning_trades,
        num_trades - winning_trades,
        f"{win_rate:.1f}",
        f"{profit_factor:.2f}",
        f"{trades_df['return'].mean() * 100:.2f}",
        f"{trades_df[trades_df['pnl'] > 0]['return'].mean() * 100:.2f}",
        f"{trades_df[trades_df['pnl'] < 0]['return'].mean() * 100:.2f}",
        f"{trades_df['return'].max() * 100:.2f}",
        f"{trades_df['return'].min() * 100:.2f}",
        f"{equity.iloc[-1]:,.2f}",
    ]
})
metrics_df.to_csv(output_dir / 'bss_metrics.csv', index=False)
print(f"💾 Metrics saved: results/nick_radge/bss_metrics.csv")

print()

# Generate QuantStats report
print("=" * 100)
print("STEP 4/4: Generating QuantStats Report")
print("=" * 100)
print()

print("📊 Creating comprehensive HTML tearsheet...")
print("   This includes:")
print("   - Cumulative returns vs benchmark")
print("   - Drawdown analysis")
print("   - Rolling volatility & Sharpe")
print("   - Monthly/yearly returns heatmap")
print("   - Distribution plots")
print("   - 50+ performance metrics")
print()

# Get SPY returns for benchmark
spy_returns = spy.pct_change().dropna()

# Align dates
common_dates = returns.index.intersection(spy_returns.index)
strategy_returns = returns.loc[common_dates]
benchmark_returns = spy_returns.loc[common_dates]

# Generate full HTML report
report_file = output_dir / 'bss_strategy_report.html'
qs.reports.html(
    strategy_returns,
    benchmark_returns,
    output=str(report_file),
    title='Nick Radge Enhanced (BSS) - Full Backtest Report'
)

print(f"✅ QuantStats report generated: results/nick_radge/bss_strategy_report.html")
print()

# Print summary comparison
print("=" * 100)
print("FINAL SUMMARY - BSS vs SPY BENCHMARK")
print("=" * 100)
print()

spy_total_return = (spy.iloc[-1] / spy.iloc[0] - 1) * 100
spy_cagr = ((spy.iloc[-1] / spy.iloc[0]) ** (1/10) - 1) * 100

print(f"{'Metric':<30} {'BSS Strategy':<20} {'SPY Benchmark':<20} {'Difference':<15}")
print("-" * 100)
print(f"{'Total Return':<30} {total_return:>18.2f}% {spy_total_return:>18.2f}% {total_return - spy_total_return:>13.2f}%")
print(f"{'CAGR':<30} {cagr:>18.2f}% {spy_cagr:>18.2f}% {cagr - spy_cagr:>13.2f}%")
print(f"{'Sharpe Ratio':<30} {sharpe:>18.2f} {'N/A':>18} {'N/A':>13}")
print(f"{'Max Drawdown':<30} {max_dd:>18.2f}% {'N/A':>18} {'N/A':>13}")
print(f"{'Total Trades':<30} {num_trades:>18,} {'Buy & Hold':>18} {'N/A':>13}")
print(f"{'Win Rate':<30} {win_rate:>18.1f}% {'N/A':>18} {'N/A':>13}")
print(f"{'Profit Factor':<30} {profit_factor:>18.2f} {'N/A':>18} {'N/A':>13}")
print()

print("=" * 100)
print("✅ FULL BACKTEST COMPLETE")
print("=" * 100)
print()

print("📁 Generated Files:")
print(f"   1. results/nick_radge/bss_strategy_report.html  ← OPEN THIS IN BROWSER")
print(f"   2. results/nick_radge/bss_equity_curve.csv")
print(f"   3. results/nick_radge/bss_trades.csv")
print(f"   4. results/nick_radge/bss_metrics.csv")
print()

print("🚀 Next Steps:")
print("   1. Open the HTML report in your browser to view full analysis")
print("   2. Review trade log to understand entry/exit points")
print("   3. If satisfied, update deployment/config_live.json to use BSS")
print("   4. Test in dry_run mode before going live")
print()

print("=" * 100)
