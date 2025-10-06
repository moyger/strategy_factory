"""
Quick Parameter Test - Focused Grid Search

Tests only the most promising combinations based on v4.1 results
"""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from core.data_loader import ForexDataLoader

# Load data
loader = ForexDataLoader()
h1_df = loader.load('EURUSD', 'H1')
h4_df = loader.load('EURUSD', 'H4')

# Use 2020-2024 for optimization
h1_train = h1_df[(h1_df.index >= '2020-01-01') & (h1_df.index < '2025-01-01')]
h4_train = h4_df[(h4_df.index >= '2020-01-01') & (h4_df.index < '2025-01-01')]

print("=" * 80)
print("QUICK PARAMETER OPTIMIZATION")
print("=" * 80)
print(f"\nTraining: {h1_train.index.min()} to {h1_train.index.max()}")
print(f"Bars: {len(h1_train):,}\n")

# Test configurations (focused around v4.1 settings)
test_configs = [
    # (r2, slope_tol, lookback, time_end, name)
    (0.5, 0.0003, 60, 9, "v4.1 baseline"),
    (0.4, 0.0003, 60, 9, "Lower R²"),
    (0.6, 0.0003, 60, 9, "Higher R²"),
    (0.5, 0.0002, 60, 9, "Stricter slope"),
    (0.5, 0.0005, 60, 9, "Looser slope"),
    (0.5, 0.0003, 40, 9, "Shorter lookback"),
    (0.5, 0.0003, 80, 9, "Longer lookback"),
    (0.5, 0.0003, 60, 7, "Narrower time"),
    (0.5, 0.0003, 60, 11, "Wider time"),
]

results = []

for r2, slope, lookback, time_end, name in test_configs:
    print(f"Testing: {name} (R²={r2}, slope={slope}, lookback={lookback}, time={time_end}h)...")

    # Create custom strategy instance
    strategy = LondonBreakoutV41Optimized(
        risk_percent=0.75,
        initial_capital=100000,
        enable_asia_breakout=False,  # Triangle only
        enable_triangle_breakout=True
    )

    # Override parameters
    strategy.triangle_lookback = lookback
    strategy.triangle_r2_min = r2
    strategy.triangle_slope_tolerance = slope
    strategy.triangle_time_end = time_end

    # Reinitialize detector
    from strategies.pattern_detector import PatternDetector
    strategy.pattern_detector = PatternDetector(
        lookback=lookback,
        min_pivot_points=3,
        r_squared_min=r2,
        slope_tolerance=slope
    )

    # Run backtest
    trades = strategy.backtest(h1_train.copy(), h4_train.copy())

    if len(trades) == 0:
        print(f"  ❌ No trades\n")
        continue

    wins = trades[trades['pnl_dollars'] > 0]
    losses = trades[trades['pnl_dollars'] <= 0]

    days = (h1_train.index.max() - h1_train.index.min()).days
    years = days / 365.25

    wr = len(wins) / len(trades) * 100
    total_pnl = trades['pnl_dollars'].sum()
    annual_pnl = total_pnl / years
    pf = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 999

    print(f"  Trades: {len(trades)} ({len(trades)/years:.1f}/yr)")
    print(f"  WR: {wr:.1f}% | PF: {pf:.2f} | Annual: ${annual_pnl:,.0f}\n")

    results.append({
        'name': name,
        'r2': r2,
        'slope': slope,
        'lookback': lookback,
        'time_end': time_end,
        'total_trades': len(trades),
        'trades_per_year': len(trades) / years,
        'win_rate': wr,
        'total_pnl': total_pnl,
        'annual_pnl': annual_pnl,
        'profit_factor': pf,
        'avg_pnl': trades['pnl_dollars'].mean()
    })

# Results table
print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)

results_df = pd.DataFrame(results)

# Sort by annual P&L
print("\nRanked by Annual P&L:")
for i, row in results_df.sort_values('annual_pnl', ascending=False).iterrows():
    print(f"\n{row['name']}")
    print(f"  R²={row['r2']}, slope={row['slope']}, lookback={row['lookback']}, time={row['time_end']}h")
    print(f"  {row['trades_per_year']:.1f} trades/yr | {row['win_rate']:.1f}% WR | ${row['annual_pnl']:,.0f}/yr | PF: {row['profit_factor']:.2f}")

# Best overall
print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

best = results_df.loc[results_df['annual_pnl'].idxmax()]
print(f"\nBest Configuration: {best['name']}")
print(f"  R² min: {best['r2']}")
print(f"  Slope tolerance: {best['slope']}")
print(f"  Lookback: {int(best['lookback'])}")
print(f"  Time window: 3-{int(best['time_end'])} AM")
print(f"\nExpected Performance (2020-2024):")
print(f"  Trades/year: {best['trades_per_year']:.1f}")
print(f"  Win rate: {best['win_rate']:.1f}%")
print(f"  Annual P&L: ${best['annual_pnl']:,.0f}")
print(f"  Profit factor: {best['profit_factor']:.2f}")
print(f"  Avg P&L/trade: ${best['avg_pnl']:,.0f}")

print("\n✅ Quick optimization complete")
