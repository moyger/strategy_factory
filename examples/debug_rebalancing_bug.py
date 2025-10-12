"""
Debug Rebalancing Bug

The verification test showed rebalancing portfolios are broken:
- Expected: ~40 trades (2 per rebalance × 20 quarters)
- Actual: 2 trades total
- Result: Massive underperformance

This script debugs the issue and finds the root cause.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import vectorbt as vbt

print("="*80)
print("DEBUGGING REBALANCING BUG")
print("="*80)

# Download BTC and ETH
print("\nDownloading BTC-USD and ETH-USD...")
data = yf.download(['BTC-USD', 'ETH-USD'], start='2020-01-01', end='2021-01-01', progress=False)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill()

print(f"✅ Data: {len(close)} days, 2 cryptos")

# ============================================================================
# METHOD 1: CURRENT APPROACH (BROKEN)
# ============================================================================
print("\n" + "="*80)
print("METHOD 1: CURRENT APPROACH (from_orders with allocations)")
print("="*80)

allocations = pd.DataFrame(0.0, index=close.index, columns=close.columns)
rebalance_dates = pd.date_range(start=close.index[0], end=close.index[-1], freq='QS-JAN')

print(f"Rebalance dates: {len(rebalance_dates)}")
for date in rebalance_dates:
    print(f"  {date.date()}")

# Set 50/50 allocation at each rebalance
for date in close.index:
    if date in rebalance_dates:
        allocations.loc[date, 'BTC-USD'] = 0.50
        allocations.loc[date, 'ETH-USD'] = 0.50

# Hold between rebalances
last_allocation = None
for date in close.index:
    if date in rebalance_dates or last_allocation is None:
        last_allocation = allocations.loc[date].copy()
    else:
        allocations.loc[date] = last_allocation

print(f"\nAllocations created:")
print(f"  Total rows: {len(allocations)}")
print(f"  Non-zero rows: {(allocations.sum(axis=1) > 0).sum()}")
print(f"  Sum check: {allocations.sum(axis=1).unique()}")

print(f"\nFirst 20 rows of allocations:")
print(allocations.head(20))

# Convert to order sizes (CURRENT METHOD)
print(f"\n📊 Current method: size = allocations / prices * capital")
order_sizes = allocations.div(close).mul(100000)

print(f"\nOrder sizes (first 20 rows):")
print(order_sizes.head(20))

# Backtest
portfolio = vbt.Portfolio.from_orders(
    close=close,
    size=order_sizes,
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0]) if len(val) > 0 else 0.0
    elif isinstance(val, pd.DataFrame):
        return float(val.values[0][0]) if len(val) > 0 else 0.0
    return float(val)

total_return = extract_value(portfolio.total_return()) * 100
num_trades = portfolio.trades.count()
if isinstance(num_trades, pd.Series):
    num_trades = int(num_trades.sum())

print(f"\n📊 RESULTS (Current Method):")
print(f"   Total Return: {total_return:+.1f}%")
print(f"   Num Trades: {num_trades}")
print(f"   Expected: ~{len(rebalance_dates) * 2} trades")

print(f"\n❌ PROBLEM: Only {num_trades} trades instead of {len(rebalance_dates) * 2}!")

# ============================================================================
# METHOD 2: TARGET PERCENT (FIX ATTEMPT)
# ============================================================================
print("\n" + "="*80)
print("METHOD 2: USING size_type='targetpercent'")
print("="*80)

print(f"Try using targetpercent instead of amount...")

portfolio2 = vbt.Portfolio.from_orders(
    close=close,
    size=allocations,  # Use allocations directly (0.0-1.0)
    size_type='targetpercent',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

total_return2 = extract_value(portfolio2.total_return()) * 100
num_trades2 = portfolio2.trades.count()
if isinstance(num_trades2, pd.Series):
    num_trades2 = int(num_trades2.sum())

print(f"\n📊 RESULTS (targetpercent):")
print(f"   Total Return: {total_return2:+.1f}%")
print(f"   Num Trades: {num_trades2}")

if num_trades2 > num_trades:
    print(f"   ✅ BETTER! {num_trades2} trades vs {num_trades}")
else:
    print(f"   ❌ SAME PROBLEM: Still only {num_trades2} trades")

# ============================================================================
# METHOD 3: SIGNAL-BASED APPROACH
# ============================================================================
print("\n" + "="*80)
print("METHOD 3: SIGNAL-BASED REBALANCING")
print("="*80)

print(f"Create entry/exit signals at rebalance dates...")

# Create signals: enter at each rebalance date
entries = pd.DataFrame(False, index=close.index, columns=close.columns)
exits = pd.DataFrame(False, index=close.index, columns=close.columns)

for i, date in enumerate(rebalance_dates):
    if date in close.index:
        # Enter both positions at each rebalance
        entries.loc[date, :] = True

        # Exit at next rebalance (to rebalance)
        if i > 0:
            prev_date = rebalance_dates[i-1]
            if prev_date in close.index:
                exits.loc[date, :] = True

print(f"Entry signals: {entries.sum().sum()}")
print(f"Exit signals: {exits.sum().sum()}")

# Equal weight at each entry
portfolio3 = vbt.Portfolio.from_signals(
    close=close,
    entries=entries,
    exits=exits,
    size=0.50,  # 50% of capital per asset
    size_type='percent',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

total_return3 = extract_value(portfolio3.total_return()) * 100
num_trades3 = portfolio3.trades.count()
if isinstance(num_trades3, pd.Series):
    num_trades3 = int(num_trades3.sum())

print(f"\n📊 RESULTS (Signal-based):")
print(f"   Total Return: {total_return3:+.1f}%")
print(f"   Num Trades: {num_trades3}")

if num_trades3 >= len(rebalance_dates) * 2:
    print(f"   ✅ WORKING! {num_trades3} trades ≈ {len(rebalance_dates) * 2} expected")
else:
    print(f"   ❌ STILL BROKEN: Only {num_trades3} trades")

# ============================================================================
# DIAGNOSIS
# ============================================================================
print("\n" + "="*80)
print("DIAGNOSIS")
print("="*80)

print(f"\nTested 3 methods:")
print(f"  Method 1 (from_orders + amount): {num_trades} trades, {total_return:+.1f}%")
print(f"  Method 2 (from_orders + targetpercent): {num_trades2} trades, {total_return2:+.1f}%")
print(f"  Method 3 (from_signals): {num_trades3} trades, {total_return3:+.1f}%")

best_method = None
best_trades = 0

if num_trades >= len(rebalance_dates) * 2 * 0.8:  # Within 80% of expected
    best_method = "Method 1 (from_orders + amount)"
    best_trades = num_trades
elif num_trades2 >= len(rebalance_dates) * 2 * 0.8:
    best_method = "Method 2 (from_orders + targetpercent)"
    best_trades = num_trades2
elif num_trades3 >= len(rebalance_dates) * 2 * 0.8:
    best_method = "Method 3 (from_signals)"
    best_trades = num_trades3

if best_method:
    print(f"\n✅ SOLUTION FOUND: {best_method}")
    print(f"   Trades: {best_trades} (close to expected {len(rebalance_dates) * 2})")
else:
    print(f"\n❌ NO SOLUTION: All methods are broken")
    print(f"   This is a fundamental issue with how we're using vectorbt")

# ============================================================================
# ROOT CAUSE ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("ROOT CAUSE ANALYSIS")
print("="*80)

print("""
The issue is likely one of these:

1. ❌ HOLDING BETWEEN REBALANCES:
   We're copying last_allocation forward, so vectorbt sees no change
   If allocation is 0.5 on day 1 and 0.5 on day 100, no order is placed

2. ❌ SIZE CALCULATION:
   Converting allocations to shares might be wrong
   size = allocation / price * capital doesn't account for current holdings

3. ❌ from_orders() BEHAVIOR:
   from_orders() might not work as expected for rebalancing
   It's designed for discrete orders, not target allocations

4. ✅ CORRECT APPROACH:
   Use from_signals() with entries at each rebalance date
   Or use a different vectorbt method designed for rebalancing
""")

print("\nRecommendation: Switch to signal-based approach in StrategyGenerator")
