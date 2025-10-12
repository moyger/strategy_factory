"""
Quarterly Universe Rebalancing - Crypto Strategy Enhancement

Tests whether quarterly rebalancing of crypto universe improves performance.

Current approach (BASELINE):
- Fixed 10-crypto universe (BTC, ETH, SOL, BNB, XRP, ADA, DOGE, MATIC, DOT, AVAX)
- Continuous entry/exit based on signals
- No universe updates

Proposed approach (TEST):
- Quarterly rebalancing to top N cryptos by market cap
- Exit positions that fall out of top N
- Continue entry/exit signals within current universe

Expected benefits:
- Automatically captures new rising cryptos
- Exits declining cryptos losing market share
- Adapts to changing market leadership
- Should improve long-term performance

Hypothesis: Quarterly rebalancing will improve returns by 10-20% and reduce drawdown slightly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("QUARTERLY UNIVERSE REBALANCING TEST - CRYPTO STRATEGY")
print("="*80)
print("\n🎯 Goal: Test if quarterly rebalancing improves crypto strategy performance")
print("\nComparing:")
print("  1. BASELINE: Fixed 10-crypto universe (current approach)")
print("  2. TEST: Quarterly rebalancing to top N cryptos by market cap")

# For this test, we'll simulate quarterly rebalancing by:
# 1. Using different universes for different time periods
# 2. Exiting positions when crypto falls out of top N
# 3. Allowing new entries from updated universe

# Since we don't have historical market cap data readily available,
# we'll use a simplified approach:
# - Simulate market cap changes based on price momentum
# - Top performers stay, bottom performers get replaced
# - This approximates what would happen with real market cap ranking

print("\n" + "="*80)
print("APPROACH")
print("="*80)
print("""
For this test, we'll use a practical approximation:

1. Start with initial top 10 cryptos (current universe)
2. Every quarter, rank all cryptos by:
   - 90-day ROC (momentum proxy for market cap changes)
3. Update universe to top 10 by momentum
4. Exit positions that fall out of top 10
5. Continue strategy signals within current universe

This simulates what would happen with real market cap rebalancing,
since market cap changes correlate strongly with price momentum.

Real implementation would use CoinGecko API for actual market cap data.
""")

# Extended universe for rebalancing (top 30 cryptos by historical significance)
EXTENDED_UNIVERSE = [
    # Current top 10
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
    # Additional candidates
    'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'ETC-USD',
    'XLM-USD', 'ALGO-USD', 'VET-USD', 'FIL-USD', 'TRX-USD',
    'AAVE-USD', 'SAND-USD', 'MANA-USD', 'AXS-USD', 'NEAR-USD',
    'HBAR-USD', 'EGLD-USD', 'THETA-USD', 'FTM-USD', 'ICP-USD'
]

print("\n" + "="*80)
print("DOWNLOADING DATA")
print("="*80)
print(f"\nExtended universe: {len(EXTENDED_UNIVERSE)} cryptos")
print("Period: 2020-01-01 to 2024-12-31")

import yfinance as yf

# Download extended universe
print("\nDownloading extended crypto universe...")
data = yf.download(EXTENDED_UNIVERSE + ['SPY'], start='2020-01-01', end='2024-12-31',
                   progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill()

# Remove tickers with insufficient data
min_data_points = 100
valid_tickers = []
for col in close.columns:
    if col == 'SPY':
        valid_tickers.append(col)
        continue
    if close[col].count() >= min_data_points:
        valid_tickers.append(col)
    else:
        print(f"   Removing {col} (insufficient data: {close[col].count()} points)")

close = close[valid_tickers]
print(f"✅ Data ready: {len(close)} days, {len(valid_tickers)-1} cryptos (+ SPY)")

spy_prices = close['SPY']
crypto_prices = close[[t for t in valid_tickers if t != 'SPY']]

# Filter to 2020+
start_backtest = '2020-01-01'
crypto_prices = crypto_prices[crypto_prices.index >= start_backtest]
spy_prices = spy_prices[spy_prices.index >= start_backtest]

print(f"\nBacktest period: {crypto_prices.index[0].date()} to {crypto_prices.index[-1].date()}")
print(f"Available cryptos: {len(crypto_prices.columns)}")

# Helper function: Select top N by momentum
def select_top_n_by_momentum(prices, n=10, lookback=90):
    """
    Select top N cryptos by momentum (ROC over lookback period).
    This approximates market cap ranking since market cap changes correlate with price momentum.
    """
    roc = prices.pct_change(lookback)
    current_roc = roc.iloc[-1]
    top_n = current_roc.nlargest(n).index.tolist()
    return top_n

# Generate quarterly rebalance dates
def get_quarterly_dates(start_date, end_date):
    """Generate quarterly rebalance dates (Jan 1, Apr 1, Jul 1, Oct 1)"""
    dates = pd.date_range(start=start_date, end=end_date, freq='QS-JAN')
    return dates

rebalance_dates = get_quarterly_dates(crypto_prices.index[0], crypto_prices.index[-1])
print(f"\nQuarterly rebalance dates: {len(rebalance_dates)}")
for date in rebalance_dates[:5]:
    print(f"  {date.date()}")
if len(rebalance_dates) > 5:
    print(f"  ... and {len(rebalance_dates)-5} more")

# Test 1: BASELINE - Fixed Universe
print("\n" + "="*80)
print("TEST 1: BASELINE - FIXED UNIVERSE")
print("="*80)

# Use original top 10
FIXED_UNIVERSE = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
                  'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD']

# Filter to available tickers
fixed_universe = [t for t in FIXED_UNIVERSE if t in crypto_prices.columns]
print(f"\nFixed universe: {len(fixed_universe)} cryptos")
print(f"{', '.join([t.replace('-USD', '') for t in fixed_universe])}")

fixed_prices = crypto_prices[fixed_universe].copy()

# Simple momentum strategy for baseline (buy top 5, hold until rebalance)
print("\nRunning simple momentum strategy on fixed universe...")
print("Strategy: Buy top 5 by 100-day ROC, rebalance quarterly")

# Generate signals
roc_period = 100
allocations_fixed = pd.DataFrame(0.0, index=fixed_prices.index, columns=fixed_prices.columns)

for date in fixed_prices.index:
    if date < fixed_prices.index[0] + pd.Timedelta(days=roc_period):
        continue

    # Get ROC at this date
    prices_slice = fixed_prices.loc[:date]
    roc = prices_slice.iloc[-1] / prices_slice.iloc[-roc_period] - 1

    # Select top 5
    top_5 = roc.nlargest(5).index.tolist()

    # Equal weight allocation
    for ticker in top_5:
        allocations_fixed.loc[date, ticker] = 0.20  # 20% each (5 positions)

# Rebalance only on quarterly dates
last_allocation = None
for date in fixed_prices.index:
    if date in rebalance_dates or last_allocation is None:
        # This is a rebalance date, recalculate
        last_allocation = allocations_fixed.loc[date].copy()
    else:
        # Copy previous allocation
        allocations_fixed.loc[date] = last_allocation

print(f"✅ Allocations generated: {(allocations_fixed.sum(axis=1) > 0).sum()} active days")

# Backtest with vectorbt
import vectorbt as vbt

print("\n📊 Running backtest...")

position_sizes_fixed = allocations_fixed.div(fixed_prices).mul(100000)

portfolio_fixed = vbt.Portfolio.from_orders(
    close=fixed_prices,
    size=position_sizes_fixed,
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

# Extract metrics
pf_value_fixed = portfolio_fixed.value()
if isinstance(pf_value_fixed, pd.DataFrame):
    final_value_fixed = float(pf_value_fixed.values[-1][0])
elif isinstance(pf_value_fixed, pd.Series):
    final_value_fixed = float(pf_value_fixed.values[-1])
else:
    final_value_fixed = float(pf_value_fixed)

total_return_fixed = extract_value(portfolio_fixed.total_return()) * 100
annualized_fixed = extract_value(portfolio_fixed.annualized_return()) * 100
sharpe_fixed = extract_value(portfolio_fixed.sharpe_ratio())
max_dd_fixed = extract_value(portfolio_fixed.max_drawdown()) * 100

print(f"\n📊 BASELINE RESULTS (Fixed Universe):")
print(f"Initial Capital:     $100,000")
print(f"Final Value:         ${final_value_fixed:,.2f}")
print(f"Total Return:        {total_return_fixed:+.2f}%")
print(f"Annualized Return:   {annualized_fixed:.2f}%")
print(f"Max Drawdown:        {max_dd_fixed:.2f}%")
print(f"Sharpe Ratio:        {sharpe_fixed:.2f}")

# Test 2: QUARTERLY REBALANCING UNIVERSE
print("\n" + "="*80)
print("TEST 2: QUARTERLY REBALANCING UNIVERSE")
print("="*80)

print(f"\nDynamic universe: Top 10 cryptos by 90-day momentum")
print(f"Rebalancing: Quarterly ({len(rebalance_dates)} times)")
print(f"Pool: {len(crypto_prices.columns)} cryptos")

# Track universe changes
universe_history = {}

allocations_dynamic = pd.DataFrame(0.0, index=crypto_prices.index, columns=crypto_prices.columns)

current_universe = []
for i, date in enumerate(crypto_prices.index):
    if date < crypto_prices.index[0] + pd.Timedelta(days=100):
        continue

    # Check if rebalance date
    if date in rebalance_dates or len(current_universe) == 0:
        # Select top 10 by 90-day momentum
        prices_slice = crypto_prices.loc[:date].tail(90)
        roc_90 = (prices_slice.iloc[-1] / prices_slice.iloc[0] - 1).dropna()
        new_universe = roc_90.nlargest(10).index.tolist()

        # Log universe change
        if len(current_universe) > 0:
            removed = set(current_universe) - set(new_universe)
            added = set(new_universe) - set(current_universe)
            if removed or added:
                universe_history[date] = {
                    'removed': list(removed),
                    'added': list(added),
                    'universe': new_universe
                }

        current_universe = new_universe

    # Calculate allocations within current universe
    prices_in_universe = crypto_prices[current_universe].loc[:date]
    roc = prices_in_universe.iloc[-1] / prices_in_universe.iloc[-roc_period] - 1

    # Select top 5 from current universe
    top_5 = roc.nlargest(5).index.tolist()

    # Equal weight allocation
    for ticker in top_5:
        allocations_dynamic.loc[date, ticker] = 0.20  # 20% each

# Apply quarterly rebalancing (only update on rebalance dates)
last_allocation = None
current_rebalance_universe = []

for date in crypto_prices.index:
    if date in rebalance_dates or last_allocation is None:
        # Rebalance date - update universe and recalculate
        if date in universe_history:
            current_rebalance_universe = universe_history[date]['universe']

        last_allocation = allocations_dynamic.loc[date].copy()
    else:
        # Non-rebalance date - hold previous allocation
        allocations_dynamic.loc[date] = last_allocation

print(f"\n✅ Dynamic allocations generated")
print(f"Universe changes: {len(universe_history)} times")

# Show universe changes
if len(universe_history) > 0:
    print(f"\n📋 Sample Universe Changes:")
    for i, (date, changes) in enumerate(list(universe_history.items())[:3]):
        print(f"\n{date.date()}:")
        if changes['removed']:
            print(f"  Removed: {', '.join([t.replace('-USD', '') for t in changes['removed']])}")
        if changes['added']:
            print(f"  Added: {', '.join([t.replace('-USD', '') for t in changes['added']])}")
        print(f"  New universe: {', '.join([t.replace('-USD', '') for t in changes['universe']])}")

    if len(universe_history) > 3:
        print(f"\n  ... and {len(universe_history)-3} more changes")

print("\n📊 Running backtest...")

position_sizes_dynamic = allocations_dynamic.div(crypto_prices).mul(100000)

portfolio_dynamic = vbt.Portfolio.from_orders(
    close=crypto_prices,
    size=position_sizes_dynamic,
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

# Extract metrics
pf_value_dynamic = portfolio_dynamic.value()
if isinstance(pf_value_dynamic, pd.DataFrame):
    final_value_dynamic = float(pf_value_dynamic.values[-1][0])
elif isinstance(pf_value_dynamic, pd.Series):
    final_value_dynamic = float(pf_value_dynamic.values[-1])
else:
    final_value_dynamic = float(pf_value_dynamic)

total_return_dynamic = extract_value(portfolio_dynamic.total_return()) * 100
annualized_dynamic = extract_value(portfolio_dynamic.annualized_return()) * 100
sharpe_dynamic = extract_value(portfolio_dynamic.sharpe_ratio())
max_dd_dynamic = extract_value(portfolio_dynamic.max_drawdown()) * 100

print(f"\n📊 TEST RESULTS (Quarterly Rebalancing Universe):")
print(f"Initial Capital:     $100,000")
print(f"Final Value:         ${final_value_dynamic:,.2f}")
print(f"Total Return:        {total_return_dynamic:+.2f}%")
print(f"Annualized Return:   {annualized_dynamic:.2f}%")
print(f"Max Drawdown:        {max_dd_dynamic:.2f}%")
print(f"Sharpe Ratio:        {sharpe_dynamic:.2f}")

# Comparison
print("\n" + "="*80)
print("COMPREHENSIVE COMPARISON")
print("="*80)

comparison = pd.DataFrame([
    {
        'Approach': 'Fixed Universe',
        'Final Value': f"${final_value_fixed:,.0f}",
        'Total Return': f"{total_return_fixed:+.1f}%",
        'Annualized': f"{annualized_fixed:.1f}%",
        'Max Drawdown': f"{max_dd_fixed:.1f}%",
        'Sharpe': f"{sharpe_fixed:.2f}"
    },
    {
        'Approach': 'Quarterly Rebalancing',
        'Final Value': f"${final_value_dynamic:,.0f}",
        'Total Return': f"{total_return_dynamic:+.1f}%",
        'Annualized': f"{annualized_dynamic:.1f}%",
        'Max Drawdown': f"{max_dd_dynamic:.1f}%",
        'Sharpe': f"{sharpe_dynamic:.2f}"
    }
])

print("\n" + comparison.to_string(index=False))

# Analysis
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)

return_improvement = total_return_dynamic - total_return_fixed
dd_improvement = max_dd_fixed - max_dd_dynamic
sharpe_improvement = sharpe_dynamic - sharpe_fixed
value_difference = final_value_dynamic - final_value_fixed

print(f"\n📊 IMPACT OF QUARTERLY REBALANCING:")
print(f"   Return improvement:   {return_improvement:+.1f}% (from {total_return_fixed:+.1f}% to {total_return_dynamic:+.1f}%)")
print(f"   Drawdown change:      {dd_improvement:+.1f}% (from {max_dd_fixed:.1f}% to {max_dd_dynamic:.1f}%)")
print(f"   Sharpe change:        {sharpe_improvement:+.2f} (from {sharpe_fixed:.2f} to {sharpe_dynamic:.2f})")
print(f"   Value difference:     ${value_difference:+,.0f}")

# Verdict
print("\n" + "="*80)
print("🎯 VERDICT")
print("="*80)

if return_improvement > 0 and sharpe_improvement > 0:
    print(f"\n✅ QUARTERLY REBALANCING IS BETTER!")
    print(f"\nBenefits:")
    print(f"   ✅ Higher returns: +{return_improvement:.1f}%")
    if dd_improvement > 0:
        print(f"   ✅ Lower drawdown: {dd_improvement:.1f}% reduction")
    print(f"   ✅ Better risk-adjusted: Sharpe +{sharpe_improvement:.2f}")
    print(f"   ✅ Adapts to market changes ({len(universe_history)} universe updates)")
    print(f"\n💰 $100K INVESTED:")
    print(f"   Fixed Universe:         ${final_value_fixed:,.0f}")
    print(f"   Quarterly Rebalancing:  ${final_value_dynamic:,.0f}")
    print(f"   Extra Profit:           ${value_difference:,.0f}")

    print(f"\n📋 RECOMMENDATION:")
    print(f"   ⭐⭐⭐ IMPLEMENT QUARTERLY REBALANCING ⭐⭐⭐")
    print(f"\n   Next steps:")
    print(f"   1. Integrate into InstitutionalCryptoPerp strategy class")
    print(f"   2. Use CoinGecko API for real market cap data")
    print(f"   3. Add universe_rebalance_freq parameter")
    print(f"   4. Test with full crypto perp strategy (not just momentum)")

elif return_improvement > 0 and sharpe_improvement < 0:
    print(f"\n⚠️ MIXED RESULTS")
    print(f"\n   ✅ Higher returns: +{return_improvement:.1f}%")
    print(f"   ❌ Lower Sharpe: {sharpe_improvement:.2f}")
    print(f"\n   Interpretation:")
    print(f"   - Quarterly rebalancing captures more upside")
    print(f"   - But adds volatility or drawdown")
    print(f"   - May be worth it for absolute return seekers")
    print(f"\n   Recommendation: TEST with full strategy before implementing")

else:
    print(f"\n❌ QUARTERLY REBALANCING UNDERPERFORMED")
    print(f"\n   Fixed universe delivered:")
    print(f"   - Higher returns: {total_return_fixed:+.1f}% vs {total_return_dynamic:+.1f}%")
    print(f"   - Better Sharpe: {sharpe_fixed:.2f} vs {sharpe_dynamic:.2f}")
    print(f"\n   Possible reasons:")
    print(f"   - Market leaders stayed consistent (BTC/ETH dominance)")
    print(f"   - Rebalancing costs hurt performance")
    print(f"   - 90-day momentum doesn't predict next quarter well")
    print(f"\n   Recommendation: KEEP fixed universe approach")

# Save results
output_dir = Path('results/crypto')
output_dir.mkdir(parents=True, exist_ok=True)

summary = pd.DataFrame([
    {
        'Approach': 'Fixed Universe',
        'Final_Value': final_value_fixed,
        'Total_Return_Pct': total_return_fixed,
        'Annualized_Pct': annualized_fixed,
        'Max_Drawdown_Pct': max_dd_fixed,
        'Sharpe_Ratio': sharpe_fixed,
        'Universe_Changes': 0
    },
    {
        'Approach': 'Quarterly Rebalancing',
        'Final_Value': final_value_dynamic,
        'Total_Return_Pct': total_return_dynamic,
        'Annualized_Pct': annualized_dynamic,
        'Max_Drawdown_Pct': max_dd_dynamic,
        'Sharpe_Ratio': sharpe_dynamic,
        'Universe_Changes': len(universe_history)
    }
])

summary.to_csv(output_dir / 'quarterly_rebalancing_test.csv', index=False)

# Save universe history
if len(universe_history) > 0:
    universe_changes_df = pd.DataFrame([
        {
            'Date': date,
            'Removed': ', '.join([t.replace('-USD', '') for t in changes['removed']]),
            'Added': ', '.join([t.replace('-USD', '') for t in changes['added']]),
            'New_Universe': ', '.join([t.replace('-USD', '') for t in changes['universe']])
        }
        for date, changes in universe_history.items()
    ])
    universe_changes_df.to_csv(output_dir / 'universe_changes.csv', index=False)
    print(f"\n📁 Universe changes saved to: {output_dir}/universe_changes.csv")

print(f"\n📁 Results saved to: {output_dir}/quarterly_rebalancing_test.csv")

print("\n✅ Quarterly rebalancing test complete!")
