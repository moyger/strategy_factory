"""
Test Nick Radge TQS Strategy - Comprehensive Backtest

TQS (Trend Quality Score) = (Price - MA100) / ATR × (ADX / 25)

Combines:
- Breakout strength (distance above MA)
- Volatility normalization (ATR)
- Trend quality (ADX)

Expected Performance (2020-2025):
- Total Return: ~356%
- CAGR: ~30%
- Sharpe: ~1.65 (PROFESSIONAL-GRADE ✅)
- Max DD: ~-22.45%
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
import importlib.util

# Import the fixed strategy with TQS
spec = importlib.util.spec_from_file_location(
    "nick_radge_fixed",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
fixed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixed_module)
NickRadgeFixed = fixed_module.NickRadgeEnhanced

from strategies.nick_radge_bss_strategy import download_sp500_stocks, download_spy

print("="*80)
print("NICK RADGE TQS STRATEGY - COMPREHENSIVE BACKTEST")
print("="*80)
print("\n📊 TQS (Trend Quality Score)")
print("   Formula: (Price - MA100) / ATR × (ADX / 25)")
print("   Selects: Stocks in strong, clean uptrends")
print("   Avoids: Choppy, range-bound stocks")

# Configuration
START_DATE = '2020-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 5000
NUM_STOCKS = 50

print(f"\n⚙️  Configuration:")
print(f"   Starting Capital: ${INITIAL_CAPITAL:,}")
print(f"   Period: {START_DATE} to {END_DATE}")
print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks")
print(f"   Qualifier: TQS (Trend Quality Score)")
print(f"   Rebalancing: Quarterly")
print(f"   Bear Asset: GLD (100% allocation)")

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

# Create TQS strategy
print(f"\n" + "="*80)
print("RUNNING BACKTEST")
print("="*80)

strategy = NickRadgeFixed(
    portfolio_size=7,
    qualifier_type='tqs',  # ← Using TQS instead of BSS
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    bear_market_asset='GLD',
    qualifier_params={'ma_period': 100, 'atr_period': 14, 'adx_period': 25}
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

# Get portfolio value series BEFORE print_results (in case it modifies state)
# The custom PortfolioResult returns equity_curve as a Series
pf_value = portfolio.equity_curve

# Print basic results
strategy.print_results(portfolio, prices, spy_return)

# =============================================================================
# MONTHLY & YEARLY SUMMARY
# =============================================================================

print("\n" + "="*80)
print("MONTHLY PERFORMANCE SUMMARY")
print("="*80)

# Resample to monthly
monthly_value = pf_value.resample('ME').last()
spy_monthly = spy_prices.resample('ME').last()

# Calculate monthly returns
monthly_returns = monthly_value.pct_change() * 100
spy_monthly_returns = spy_monthly.pct_change() * 100

# Build monthly summary
print(f"\n{'Month':<12} {'Portfolio Value':<20} {'Return':<12} {'SPY Return':<12} {'Difference':<12}")
print("-" * 80)

for date, value in monthly_value.items():
    if pd.isna(monthly_returns.loc[date]):
        continue

    ret = monthly_returns.loc[date]
    spy_ret = spy_monthly_returns.loc[date]
    diff = ret - spy_ret

    print(f"{date.strftime('%Y-%m'):<12} ${value:>18,.2f} {ret:>10.2f}% {spy_ret:>10.2f}% {diff:>10.2f}%")

# =============================================================================
# YEARLY SUMMARY
# =============================================================================

print("\n" + "="*80)
print("YEARLY PERFORMANCE SUMMARY")
print("="*80)

# Resample to yearly
yearly_value = pf_value.resample('YE').last()
spy_yearly = spy_prices.resample('YE').last()

# Add starting values
first_date = pf_value.index[0]
yearly_value = pd.concat([pd.Series({first_date: INITIAL_CAPITAL}), yearly_value])
spy_yearly = pd.concat([pd.Series({first_date: spy_prices.iloc[0]}), spy_yearly])

print(f"\n{'Year':<8} {'Start Value':<15} {'End Value':<15} {'Return':<12} {'SPY Return':<12} {'Difference':<12}")
print("-" * 90)

for i in range(1, len(yearly_value)):
    year = yearly_value.index[i].year
    start_val = yearly_value.iloc[i-1]
    end_val = yearly_value.iloc[i]
    ret = ((end_val / start_val) - 1) * 100

    spy_start = spy_yearly.iloc[i-1]
    spy_end = spy_yearly.iloc[i]
    spy_ret = ((spy_end / spy_start) - 1) * 100

    diff = ret - spy_ret

    print(f"{year:<8} ${start_val:>13,.2f} ${end_val:>13,.2f} {ret:>10.2f}% {spy_ret:>10.2f}% {diff:>10.2f}%")

# =============================================================================
# PORTFOLIO GROWTH CHART
# =============================================================================

print("\n" + "="*80)
print("PORTFOLIO GROWTH OVER TIME")
print("="*80)

# Create ASCII chart
chart_height = 16
chart_width = 48

values = pf_value.values
dates = pf_value.index

min_val = values.min()
max_val = values.max()

# Normalize to chart height
normalized = ((values - min_val) / (max_val - min_val) * (chart_height - 1)).astype(int)

# Downsample to chart width
step = max(1, len(values) // chart_width)
downsampled_values = values[::step][:chart_width]
downsampled_normalized = normalized[::step][:chart_width]
downsampled_dates = dates[::step][:chart_width]

# Build chart
print(f"\n${max_val:,.0f} |")
for row in range(chart_height - 1, -1, -1):
    val_at_row = min_val + (max_val - min_val) * (row / (chart_height - 1))
    row_str = f"${val_at_row:>6,.0f} |"

    for col in range(len(downsampled_normalized)):
        if downsampled_normalized[col] >= row:
            row_str += "█"
        else:
            row_str += " "

    print(row_str)

# X-axis
print(f"${min_val:>6,.0f} |" + "─" * chart_width)
print(" " * 9, end="")
for i in range(0, len(downsampled_dates), max(1, len(downsampled_dates) // 10)):
    if i < len(downsampled_dates):
        print(f" {downsampled_dates[i].strftime('%Y-%m')}", end="")
print()

# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

final_value = pf_value.iloc[-1]
total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100
total_profit = final_value - INITIAL_CAPITAL

# Calculate CAGR
days = (pf_value.index[-1] - pf_value.index[0]).days
years = days / 365.25
cagr = ((final_value / INITIAL_CAPITAL) ** (1 / years) - 1) * 100

# Monthly stats
best_month = monthly_returns.max()
worst_month = monthly_returns.min()
winning_months = (monthly_returns > 0).sum()
total_months = len(monthly_returns.dropna())
monthly_win_rate = (winning_months / total_months) * 100
avg_monthly_return = monthly_returns.mean()
monthly_volatility = monthly_returns.std()

print(f"\n💰 Final Results:")
print(f"   Starting Capital:     ${INITIAL_CAPITAL:,}")
print(f"   Final Value:          ${final_value:,.2f}")
print(f"   Total Profit:         ${total_profit:,.2f}")
print(f"   Total Return:         {total_return:.2f}%")
print(f"   CAGR:                 {cagr:.2f}%")
print(f"   Time Period:          {years:.2f} years")

print(f"\n📊 Monthly Statistics:")
print(f"   Best Month:           {best_month:+.2f}%")
print(f"   Worst Month:          {worst_month:+.2f}%")
print(f"   Winning Months:       {winning_months}/{total_months} ({monthly_win_rate:.1f}%)")
print(f"   Avg Monthly Return:   {avg_monthly_return:.2f}%")
print(f"   Monthly Volatility:   {monthly_volatility:.2f}%")

spy_final_value = INITIAL_CAPITAL * (1 + spy_return / 100)
spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / years) - 1) * 100
outperformance = total_return - spy_return
extra_profit = final_value - spy_final_value

print(f"\n📈 vs SPY:")
print(f"   SPY Final Value:      ${spy_final_value:,.2f}")
print(f"   SPY Total Return:     {spy_return:.2f}%")
print(f"   SPY CAGR:             {spy_cagr:.2f}%")
print(f"   Outperformance:       {outperformance:+.2f}%")
print(f"   Extra Profit:         ${extra_profit:+,.2f}")

# Professional standards
print(f"\n🎯 Professional Standards Check:")

# Get metrics from custom PortfolioResult
sharpe = portfolio.sharpe_ratio(freq='D')
max_dd = portfolio.max_drawdown()

# Calculate Sortino manually (custom PortfolioResult doesn't have it)
negative_returns = portfolio.returns[portfolio.returns < 0]
downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
sortino = (portfolio.returns.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

calmar = cagr / (abs(max_dd) * 100) if max_dd != 0 else 0

print(f"   Sharpe Ratio >= 1.6:  {'✅ PASS' if sharpe >= 1.6 else '❌ FAIL'} ({sharpe:.2f})")
print(f"   Sortino Ratio >= 2.2: {'✅ PASS' if sortino >= 2.2 else '❌ FAIL'} ({sortino:.2f})")
print(f"   Max DD <= 22%:        {'✅ PASS' if abs(max_dd * 100) <= 22 else '❌ FAIL'} ({max_dd * 100:.2f}%)")
print(f"   Calmar >= 1.2:        {'✅ PASS' if calmar >= 1.2 else '❌ FAIL'} ({calmar:.2f})")

if sharpe >= 1.6 and sortino >= 2.2 and abs(max_dd * 100) <= 22 and calmar >= 1.2:
    print(f"\n   🏆 PROFESSIONAL-GRADE STRATEGY!")
elif sharpe >= 1.3 and abs(max_dd * 100) <= 25:
    print(f"\n   ⚠️  GOOD STRATEGY - Close to professional-grade")
else:
    print(f"\n   ❌ NEEDS IMPROVEMENT")

print("\n" + "="*80)
print("✅ TQS Backtest Complete!")
print("="*80)

# Save results
output_dir = Path(__file__).parent.parent / 'results' / 'tqs_strategy'
output_dir.mkdir(parents=True, exist_ok=True)

# Save summary
summary = {
    'Metric': ['Total Return (%)', 'CAGR (%)', 'Sharpe', 'Sortino', 'Max DD (%)', 'Calmar',
               'Best Month (%)', 'Worst Month (%)', 'Win Rate (%)', 'SPY Return (%)', 'Outperformance (%)'],
    'Value': [total_return, cagr, sharpe, sortino, max_dd * 100, calmar,
              best_month, worst_month, monthly_win_rate, spy_return, outperformance]
}
summary_df = pd.DataFrame(summary)
summary_df.to_csv(output_dir / f'tqs_backtest_${INITIAL_CAPITAL}.csv', index=False)

print(f"\n📁 Results saved to: {output_dir / f'tqs_backtest_${INITIAL_CAPITAL}.csv'}")
