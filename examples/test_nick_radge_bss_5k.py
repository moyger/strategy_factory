"""
Test Nick Radge BSS Strategy with $5,000 starting capital

Shows monthly and yearly performance summary
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from strategies.nick_radge_bss_strategy import NickRadgeBSS, download_sp500_stocks, download_spy

print("="*80)
print("NICK RADGE BSS STRATEGY - $5,000 STARTING CAPITAL")
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

# Create strategy
print(f"\n" + "="*80)
print("RUNNING BACKTEST")
print("="*80)

strategy = NickRadgeBSS(
    portfolio_size=7,
    poi_period=100,
    atr_period=14,
    atr_multiplier=2.0,
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
# MONTHLY & YEARLY SUMMARY
# =============================================================================

print("\n" + "="*80)
print("MONTHLY PERFORMANCE SUMMARY")
print("="*80)

# Get portfolio value series
pf_value = portfolio.value()
if isinstance(pf_value, pd.DataFrame):
    pf_value = pf_value.iloc[:, 0]

# Calculate monthly returns
monthly_values = pf_value.resample('M').last()
monthly_returns = monthly_values.pct_change() * 100

# Calculate SPY monthly returns
spy_monthly_values = spy_prices.resample('M').last()
spy_monthly_returns = spy_monthly_values.pct_change() * 100

# Create monthly summary
print(f"\n{'Month':<12} {'Portfolio Value':<18} {'Return':<12} {'SPY Return':<12} {'Difference':<12}")
print("-" * 80)

for date, value in monthly_values.items():
    if pd.isna(monthly_returns.get(date)):
        continue

    ret = monthly_returns.get(date, 0)
    spy_ret = spy_monthly_returns.get(date, 0)
    diff = ret - spy_ret

    date_str = date.strftime('%Y-%m')
    print(f"{date_str:<12} ${value:>15,.2f}   {ret:>9.2f}%   {spy_ret:>9.2f}%   {diff:>9.2f}%")

# =============================================================================
# YEARLY SUMMARY
# =============================================================================

print("\n" + "="*80)
print("YEARLY PERFORMANCE SUMMARY")
print("="*80)

# Calculate yearly returns
yearly_values = pf_value.resample('Y').last()
yearly_returns = yearly_values.pct_change() * 100

# SPY yearly returns
spy_yearly_values = spy_prices.resample('Y').last()
spy_yearly_returns = spy_yearly_values.pct_change() * 100

# Calculate YTD for current year if not complete
current_year = datetime.now().year
if pf_value.index[-1].year == current_year:
    # YTD return
    year_start = pd.Timestamp(f'{current_year}-01-01')
    if year_start in pf_value.index:
        ytd_start_value = pf_value[pf_value.index >= year_start].iloc[0]
    else:
        ytd_start_value = pf_value[pf_value.index >= year_start.replace(year=current_year-1)].iloc[-1]

    ytd_current_value = pf_value.iloc[-1]
    ytd_return = ((ytd_current_value / ytd_start_value) - 1) * 100

    # SPY YTD
    if year_start in spy_prices.index:
        spy_ytd_start = spy_prices[spy_prices.index >= year_start].iloc[0]
    else:
        spy_ytd_start = spy_prices[spy_prices.index >= year_start.replace(year=current_year-1)].iloc[-1]
    spy_ytd_current = spy_prices.iloc[-1]
    spy_ytd_return = ((spy_ytd_current / spy_ytd_start) - 1) * 100

print(f"\n{'Year':<8} {'Start Value':<15} {'End Value':<15} {'Return':<12} {'SPY Return':<12} {'Difference':<12}")
print("-" * 90)

# Track year-over-year
prev_year_value = INITIAL_CAPITAL
years_processed = set()

for date, value in yearly_values.items():
    year = date.year
    if year in years_processed:
        continue
    years_processed.add(year)

    ret = yearly_returns.get(date, 0)
    spy_ret = spy_yearly_returns.get(date, 0)
    diff = ret - spy_ret

    # If first year, calculate from initial capital
    if pd.isna(ret):
        ret = ((value / INITIAL_CAPITAL) - 1) * 100
        # Get SPY return from start
        spy_start = spy_prices[spy_prices.index.year == year].iloc[0]
        spy_end = spy_prices[spy_prices.index.year == year].iloc[-1]
        spy_ret = ((spy_end / spy_start) - 1) * 100
        diff = ret - spy_ret

    print(f"{year:<8} ${prev_year_value:>13,.2f} ${value:>13,.2f}   {ret:>9.2f}%   {spy_ret:>9.2f}%   {diff:>9.2f}%")
    prev_year_value = value

# Add YTD if current year
if pf_value.index[-1].year == current_year and current_year not in years_processed:
    ytd_start_date = pd.Timestamp(f'{current_year}-01-01')

    # Find actual start value for this year
    year_start_idx = pf_value.index.searchsorted(ytd_start_date)
    if year_start_idx > 0:
        year_start_value = pf_value.iloc[year_start_idx - 1]
    else:
        year_start_value = INITIAL_CAPITAL

    current_value = pf_value.iloc[-1]

    print(f"{current_year} (YTD) ${year_start_value:>13,.2f} ${current_value:>13,.2f}   {ytd_return:>9.2f}%   {spy_ytd_return:>9.2f}%   {ytd_return - spy_ytd_return:>9.2f}%")

# =============================================================================
# GROWTH CHART (ASCII)
# =============================================================================

print("\n" + "="*80)
print("PORTFOLIO GROWTH OVER TIME")
print("="*80)

# Sample portfolio value at regular intervals for chart
chart_dates = pd.date_range(start=pf_value.index[0], end=pf_value.index[-1], freq='3M')
chart_values = []
chart_labels = []

for date in chart_dates:
    nearest_idx = pf_value.index.searchsorted(date)
    if nearest_idx < len(pf_value):
        chart_values.append(pf_value.iloc[nearest_idx])
        chart_labels.append(date.strftime('%Y-%m'))

# Add final value
chart_values.append(pf_value.iloc[-1])
chart_labels.append(pf_value.index[-1].strftime('%Y-%m'))

# Create ASCII chart
max_val = max(chart_values)
min_val = min(chart_values)
chart_height = 15
scale = (max_val - min_val) / chart_height if max_val > min_val else 1

print(f"\n${max_val:,.0f} |")
for i in range(chart_height, -1, -1):
    threshold = min_val + (i * scale)
    line = f"${threshold:>6,.0f} |"

    for val in chart_values:
        if val >= threshold:
            line += "██"
        else:
            line += "  "
    print(line)

print(f"${min_val:,.0f} |" + "──" * len(chart_values))
print("        " + "".join([f"{i:>2}" for i in range(len(chart_values))]))

print("\n" + " " * 8 + "  ".join(chart_labels))

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
years = (pf_value.index[-1] - pf_value.index[0]).days / 365.25
cagr = (((final_value / INITIAL_CAPITAL) ** (1 / years)) - 1) * 100

# Calculate best/worst months
best_month = monthly_returns.max()
best_month_date = monthly_returns.idxmax().strftime('%Y-%m')
worst_month = monthly_returns.min()
worst_month_date = monthly_returns.idxmin().strftime('%Y-%m')

# Winning months
winning_months = (monthly_returns > 0).sum()
total_months = len(monthly_returns.dropna())
win_rate_monthly = (winning_months / total_months * 100) if total_months > 0 else 0

print(f"\n💰 Final Results:")
print(f"   Starting Capital:     ${INITIAL_CAPITAL:,}")
print(f"   Final Value:          ${final_value:,.2f}")
print(f"   Total Profit:         ${total_profit:,.2f}")
print(f"   Total Return:         {total_return:.2f}%")
print(f"   CAGR:                 {cagr:.2f}%")
print(f"   Time Period:          {years:.2f} years")

print(f"\n📊 Monthly Statistics:")
print(f"   Best Month:           {best_month:+.2f}% ({best_month_date})")
print(f"   Worst Month:          {worst_month:+.2f}% ({worst_month_date})")
print(f"   Winning Months:       {winning_months}/{total_months} ({win_rate_monthly:.1f}%)")
print(f"   Avg Monthly Return:   {monthly_returns.mean():.2f}%")
print(f"   Monthly Volatility:   {monthly_returns.std():.2f}%")

print(f"\n📈 vs SPY:")
spy_total_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100
spy_final_value = INITIAL_CAPITAL * (1 + spy_total_return / 100)
spy_cagr = (((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / years)) - 1) * 100

print(f"   SPY Final Value:      ${spy_final_value:,.2f}")
print(f"   SPY Total Return:     {spy_total_return:.2f}%")
print(f"   SPY CAGR:             {spy_cagr:.2f}%")
print(f"   Outperformance:       {total_return - spy_total_return:+.2f}%")
print(f"   Extra Profit:         ${final_value - spy_final_value:+,.2f}")

print("\n" + "="*80)
print("✅ Analysis Complete!")
print("="*80)
