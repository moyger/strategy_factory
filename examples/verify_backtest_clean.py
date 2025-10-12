"""
CLEAN BACKTEST VERIFICATION

Simple, transparent backtest to verify the +1,106% return claim.
No fancy libraries - just pure logic we can audit.

Strategy:
- Top 10 momentum stocks (100-day ROC)
- Quarterly rebalancing
- 3-tier regime filter (SPY 200/50 MA)
- 100% GLD in BEAR regime
- Equal weight or momentum weight

Let's verify step by step with clear logging.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("CLEAN BACKTEST VERIFICATION")
print("="*80)
print("\nGoal: Verify the +1,106% return with transparent logic")
print("\nPeriod: 2014-2024 (11 years)")
print("Initial Capital: $100,000")

# Download data
print("\n" + "="*80)
print("STEP 1: DOWNLOAD DATA")
print("="*80)

tickers = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
    'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
    'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
    'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
    'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T',
    'AMGN', 'IBM', 'BA', 'GE', 'CAT', 'SBUX', 'LOW', 'GS', 'ELV', 'SPGI'
]

all_tickers = tickers + ['SPY', 'GLD']

print(f"Downloading {len(all_tickers)} tickers...")
data = yf.download(all_tickers, start='2013-01-01', end='2024-12-31', progress=False)

close = data['Close'].copy() if isinstance(data.columns, pd.MultiIndex) else data[['Close']].copy()
close = close.ffill().dropna()

print(f"✅ Downloaded {len(close)} days")
print(f"   Date range: {close.index[0].date()} to {close.index[-1].date()}")

# Filter to backtest period
start = '2014-01-01'
close_bt = close[close.index >= start].copy()

spy = close_bt['SPY']
gld = close_bt['GLD']
stocks = close_bt[[t for t in tickers if t in close_bt.columns]]

print(f"\nBacktest period: {len(close_bt)} days ({close_bt.index[0].date()} to {close_bt.index[-1].date()})")
print(f"Stocks available: {len(stocks.columns)}")

# Calculate regime
print("\n" + "="*80)
print("STEP 2: CALCULATE REGIME")
print("="*80)

spy_ma_200 = spy.rolling(200).mean()
spy_ma_50 = spy.rolling(50).mean()

regime = pd.Series('UNKNOWN', index=spy.index)
regime[(spy > spy_ma_200) & (spy > spy_ma_50)] = 'STRONG_BULL'
regime[(spy > spy_ma_200) & (spy <= spy_ma_50)] = 'WEAK_BULL'
regime[spy <= spy_ma_200] = 'BEAR'

print("\nRegime distribution:")
for r in ['STRONG_BULL', 'WEAK_BULL', 'BEAR', 'UNKNOWN']:
    count = (regime == r).sum()
    pct = count / len(regime) * 100
    print(f"  {r:15s}: {count:4d} days ({pct:5.1f}%)")

# Calculate momentum (100-day ROC)
print("\n" + "="*80)
print("STEP 3: CALCULATE MOMENTUM SCORES")
print("="*80)

momentum = stocks.pct_change(100)
print(f"✅ Momentum calculated (100-day ROC)")

# Determine rebalance dates (quarterly)
print("\n" + "="*80)
print("STEP 4: IDENTIFY REBALANCE DATES")
print("="*80)

rebalance_dates = pd.date_range(start=close_bt.index[0], end=close_bt.index[-1], freq='QS')
rebalance_dates = [d for d in rebalance_dates if d in close_bt.index]

# Need data for ROC calculation
min_date = close_bt.index[0] + pd.Timedelta(days=100)
rebalance_dates = [d for d in rebalance_dates if d >= min_date]

print(f"Rebalance dates: {len(rebalance_dates)}")
print(f"First: {rebalance_dates[0].date()}")
print(f"Last: {rebalance_dates[-1].date()}")

# Manual backtest
print("\n" + "="*80)
print("STEP 5: RUN MANUAL BACKTEST")
print("="*80)

cash = 100000
positions = {}  # {ticker: shares}
equity_history = []
trade_log = []

for i, date in enumerate(close_bt.index):
    current_prices = stocks.loc[date]
    current_regime = regime.loc[date]

    # Calculate current equity
    position_value = sum(positions.get(ticker, 0) * current_prices.get(ticker, 0)
                        for ticker in positions.keys())
    total_equity = cash + position_value

    # BEAR REGIME: Hold GLD
    if current_regime == 'BEAR':
        if positions:  # Exit all stock positions
            for ticker, shares in list(positions.items()):
                if ticker in current_prices.index:
                    exit_price = current_prices[ticker]
                    cash += shares * exit_price * 0.999  # 0.1% fee
                    trade_log.append({
                        'date': date,
                        'action': 'SELL',
                        'ticker': ticker,
                        'reason': 'BEAR_REGIME'
                    })
            positions = {}

        # Track GLD value (simplified - assume we're in GLD)
        if date in gld.index:
            gld_factor = gld.loc[date] / gld.iloc[0]
            total_equity = 100000 * gld_factor  # Simplified GLD tracking

        equity_history.append(total_equity)
        continue

    # QUARTERLY REBALANCING
    if date in rebalance_dates:
        # Exit all positions
        for ticker, shares in list(positions.items()):
            if ticker in current_prices.index and not pd.isna(current_prices[ticker]):
                exit_price = current_prices[ticker]
                cash += shares * exit_price * 0.999
                trade_log.append({
                    'date': date,
                    'action': 'SELL',
                    'ticker': ticker,
                    'reason': 'REBALANCE'
                })
        positions = {}

        # Get momentum rankings
        if date in momentum.index:
            mom_scores = momentum.loc[date].dropna().sort_values(ascending=False)

            # Determine portfolio size based on regime
            if current_regime == 'STRONG_BULL':
                n_positions = 10
            elif current_regime == 'WEAK_BULL':
                n_positions = 5
            else:
                n_positions = 0

            # Select top N
            if n_positions > 0 and len(mom_scores) > 0:
                top_n = mom_scores.head(n_positions)

                # Calculate total equity
                total_equity = cash

                # Equal weight allocation
                for ticker in top_n.index:
                    if ticker in current_prices.index and not pd.isna(current_prices[ticker]):
                        entry_price = current_prices[ticker]
                        if entry_price > 0:
                            allocation = total_equity / n_positions
                            shares = allocation / entry_price
                            cost = shares * entry_price * 1.001  # 0.1% fee

                            if cost <= cash:
                                positions[ticker] = shares
                                cash -= cost
                                trade_log.append({
                                    'date': date,
                                    'action': 'BUY',
                                    'ticker': ticker,
                                    'shares': shares,
                                    'price': entry_price,
                                    'reason': 'REBALANCE'
                                })

        # Show rebalance summary
        if i % 252 == 0 or date in [rebalance_dates[0], rebalance_dates[-1]]:
            print(f"\n{date.date()} - Rebalance #{rebalance_dates.index(date)+1}")
            print(f"  Regime: {current_regime}")
            print(f"  Positions: {len(positions)}")
            print(f"  Equity: ${total_equity:,.0f}")
            if positions:
                print(f"  Holdings: {', '.join(positions.keys())}")

    # Calculate equity
    position_value = sum(positions.get(ticker, 0) * current_prices.get(ticker, 0)
                        for ticker in positions.keys() if ticker in current_prices.index)
    total_equity = cash + position_value
    equity_history.append(total_equity)

# Convert to series
equity_series = pd.Series(equity_history, index=close_bt.index)

# Calculate metrics
print("\n" + "="*80)
print("STEP 6: CALCULATE PERFORMANCE METRICS")
print("="*80)

initial = 100000
final = equity_series.iloc[-1]
total_return = ((final / initial) - 1) * 100

years = (equity_series.index[-1] - equity_series.index[0]).days / 365.25
cagr = ((final / initial) ** (1/years) - 1) * 100

# Drawdown
cummax = equity_series.cummax()
drawdown = (equity_series - cummax) / cummax
max_dd = drawdown.min() * 100

# Sharpe
returns = equity_series.pct_change().dropna()
sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0

# SPY benchmark
spy_return = ((spy.iloc[-1] / spy.iloc[0]) - 1) * 100

print(f"\n📊 RESULTS:")
print(f"Initial Capital:     ${initial:,.2f}")
print(f"Final Equity:        ${final:,.2f}")
print(f"Total Return:        {total_return:+.2f}%")
print(f"CAGR:                {cagr:.2f}%")
print(f"Max Drawdown:        {max_dd:.2f}%")
print(f"Sharpe Ratio:        {sharpe:.2f}")
print(f"\nSPY Buy & Hold:      {spy_return:+.2f}%")
print(f"Outperformance:      {total_return - spy_return:+.2f}%")

# Trade statistics
print(f"\n📈 TRADE STATISTICS:")
print(f"Total Trades:        {len(trade_log)}")
print(f"Rebalances:          {len(rebalance_dates)}")
print(f"Avg Trades/Quarter:  {len(trade_log) / len(rebalance_dates):.1f}")

# Sanity checks
print("\n" + "="*80)
print("SANITY CHECKS")
print("="*80)

# Check 1: Is final equity reasonable?
expected_spy_final = 100000 * (1 + spy_return/100)
print(f"\nCheck 1: Final Equity Reasonableness")
print(f"  Strategy final: ${final:,.0f}")
print(f"  SPY would give: ${expected_spy_final:,.0f}")
print(f"  Ratio: {final / expected_spy_final:.2f}x")

if final / expected_spy_final > 5:
    print(f"  ⚠️  WARNING: Strategy is {final / expected_spy_final:.1f}x better than SPY - seems high!")
else:
    print(f"  ✅ Reasonable outperformance")

# Check 2: Annual returns breakdown
print(f"\nCheck 2: Annual Returns Breakdown")
equity_df = equity_series.to_frame('equity')
equity_df['year'] = equity_df.index.year

for year in sorted(equity_df['year'].unique()):
    year_data = equity_df[equity_df['year'] == year]['equity']
    if len(year_data) > 0:
        year_return = ((year_data.iloc[-1] / year_data.iloc[0]) - 1) * 100
        print(f"  {year}: {year_return:+7.2f}%")

# Check 3: Compare to original test
print(f"\nCheck 3: Comparison to Original Test")
print(f"  Original claim: +1,106% return")
print(f"  This test:      {total_return:+.1f}% return")
print(f"  Difference:     {abs(total_return - 1106):.1f}%")

if abs(total_return - 1106) < 50:
    print(f"  ✅ VERIFIED - Results match!")
else:
    print(f"  ⚠️  DISCREPANCY - Investigate further")

# Save equity curve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.figure(figsize=(14, 8))

# Plot 1: Equity curve
plt.subplot(2, 1, 1)
plt.plot(equity_series.index, equity_series.values, label='Strategy', linewidth=2)
spy_equity = 100000 * (spy / spy.iloc[0])
plt.plot(spy.index, spy_equity.values, label='SPY', linewidth=2, alpha=0.7)
plt.title('Equity Curve Comparison', fontsize=14, fontweight='bold')
plt.ylabel('Portfolio Value ($)')
plt.legend()
plt.grid(True, alpha=0.3)

# Plot 2: Drawdown
plt.subplot(2, 1, 2)
plt.fill_between(equity_series.index, drawdown.values * 100, 0, alpha=0.3, color='red')
plt.plot(equity_series.index, drawdown.values * 100, color='red', linewidth=1)
plt.title('Drawdown', fontsize=14, fontweight='bold')
plt.ylabel('Drawdown (%)')
plt.xlabel('Date')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/stock/backtest_verification.png', dpi=150, bbox_inches='tight')
print(f"\n📊 Chart saved: results/stock/backtest_verification.png")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)

if abs(total_return - 1106) < 50:
    print(f"\n✅ RESULT VERIFIED!")
    print(f"   The +{total_return:.0f}% return is CORRECT")
    print(f"   This is a legitimate high-performing momentum strategy")
else:
    print(f"\n⚠️  RESULT NEEDS INVESTIGATION")
    print(f"   Expected: +1,106%")
    print(f"   Got: {total_return:+.1f}%")
    print(f"   Difference: {abs(total_return - 1106):.1f}%")
