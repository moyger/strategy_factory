"""
Optimize ADAUSD Strategy Parameters
Test different configurations to find optimal settings for ADAUSD crypto pair
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from itertools import product

sys.path.insert(0, str(Path(__file__).parent))

from strategies.strategy_breakout_v4_1_adausd_bybit import LondonBreakoutV41ADAUSDBybit

# Load ADAUSD data
print("Loading ADAUSD data...")
df_h1 = pd.read_csv('data/crypto/ADAUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h4 = pd.read_csv('data/crypto/ADAUSD_4H.csv', parse_dates=['Datetime'], index_col='Datetime')

# Use recent data
df_h1 = df_h1[df_h1.index >= '2023-01-01']
df_h4 = df_h4[df_h4.index >= '2023-01-01']

# Split data
split_date = '2024-01-01'
train_h1 = df_h1[df_h1.index < split_date]
train_h4 = df_h4[df_h4.index < split_date]
test_h1 = df_h1[df_h1.index >= split_date]
test_h4 = df_h4[df_h4.index >= split_date]

print(f"Training: {train_h1.index[0]} to {train_h1.index[-1]}")
print(f"Testing:  {test_h1.index[0]} to {test_h1.index[-1]}")

print("\n" + "="*80)
print("ADAUSD STRATEGY OPTIMIZATION")
print("="*80)

# Current baseline parameters
baseline = {
    'min_range': 0.01,
    'max_range': 0.08,
    'buffer': 0.002,
    'min_momentum': 0.015,
    'rr_ratio': 1.3,
    'leverage': 3
}

print(f"\n📊 BASELINE PARAMETERS:")
for key, val in baseline.items():
    print(f"  {key}: {val}")

# Test baseline
print("\n" + "="*80)
print("BASELINE PERFORMANCE")
print("="*80)

strategy = LondonBreakoutV41ADAUSDBybit(
    risk_percent=1.0,
    initial_capital=10000,
    leverage=baseline['leverage']
)
trades, equity = strategy.run(test_h1.copy(), test_h4.copy())

if len(trades) > 0:
    wins = trades[trades['pnl'] > 0]
    total_pnl = trades['pnl'].sum()
    win_rate = len(wins) / len(trades) * 100
    profit_factor = abs(wins['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()) if len(trades[trades['pnl'] <= 0]) > 0 else float('inf')

    equity['peak'] = equity['equity'].cummax()
    equity['drawdown'] = (equity['equity'] - equity['peak']) / equity['peak'] * 100
    max_dd = equity['drawdown'].min()

    print(f"Trades: {len(trades)} | WR: {win_rate:.1f}% | P&L: ${total_pnl:,.0f} | PF: {profit_factor:.2f} | DD: {max_dd:.2f}%")

# Optimization tests
print("\n" + "="*80)
print("OPTIMIZATION TESTS")
print("="*80)

results = []

# Test 1: Asia Range Thresholds
print("\n1️⃣  TESTING ASIA RANGE THRESHOLDS")
print("-" * 80)

range_configs = [
    (0.008, 0.08, "Wider Range (0.8-8%)"),
    (0.01, 0.08, "Current (1-8%)"),
    (0.01, 0.10, "Higher Max (1-10%)"),
    (0.012, 0.08, "Narrower Min (1.2-8%)"),
    (0.015, 0.08, "Conservative (1.5-8%)"),
]

for min_r, max_r, desc in range_configs:
    strategy = LondonBreakoutV41ADAUSDBybit(
        risk_percent=1.0,
        initial_capital=10000,
        leverage=3
    )
    strategy.min_asia_range_pct = min_r
    strategy.max_asia_range_pct = max_r

    trades, equity = strategy.run(test_h1.copy(), test_h4.copy())

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        total_pnl = trades['pnl'].sum()
        win_rate = len(wins) / len(trades) * 100
        profit_factor = abs(wins['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()) if len(trades[trades['pnl'] <= 0]) > 0 else float('inf')

        equity['peak'] = equity['equity'].cummax()
        equity['drawdown'] = (equity['equity'] - equity['peak']) / equity['peak'] * 100
        max_dd = equity['drawdown'].min()

        print(f"  {desc:<25} | {len(trades):2} trades | WR: {win_rate:5.1f}% | P&L: ${total_pnl:>7,.0f} | PF: {profit_factor:4.2f} | DD: {max_dd:6.2f}%")

        results.append({
            'config': desc,
            'category': 'Range',
            'trades': len(trades),
            'win_rate': win_rate,
            'pnl': total_pnl,
            'pf': profit_factor,
            'dd': max_dd,
            'score': (total_pnl / 10000) * (win_rate / 100) * (profit_factor / 2) * (1 + max_dd / 100)  # Combined score
        })

# Test 2: Risk/Reward Ratios
print("\n2️⃣  TESTING RISK/REWARD RATIOS")
print("-" * 80)

rr_configs = [
    (1.0, "Conservative 1:1"),
    (1.2, "Moderate 1.2:1"),
    (1.3, "Current 1.3:1"),
    (1.5, "Aggressive 1.5:1"),
    (2.0, "Very Aggressive 2:1"),
]

for rr, desc in rr_configs:
    strategy = LondonBreakoutV41ADAUSDBybit(
        risk_percent=1.0,
        initial_capital=10000,
        leverage=3
    )
    strategy.risk_reward_ratio = rr

    trades, equity = strategy.run(test_h1.copy(), test_h4.copy())

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        total_pnl = trades['pnl'].sum()
        win_rate = len(wins) / len(trades) * 100
        profit_factor = abs(wins['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()) if len(trades[trades['pnl'] <= 0]) > 0 else float('inf')

        equity['peak'] = equity['equity'].cummax()
        equity['drawdown'] = (equity['equity'] - equity['peak']) / equity['peak'] * 100
        max_dd = equity['drawdown'].min()

        print(f"  {desc:<25} | {len(trades):2} trades | WR: {win_rate:5.1f}% | P&L: ${total_pnl:>7,.0f} | PF: {profit_factor:4.2f} | DD: {max_dd:6.2f}%")

        results.append({
            'config': desc,
            'category': 'RR_Ratio',
            'trades': len(trades),
            'win_rate': win_rate,
            'pnl': total_pnl,
            'pf': profit_factor,
            'dd': max_dd,
            'score': (total_pnl / 10000) * (win_rate / 100) * (profit_factor / 2) * (1 + max_dd / 100)
        })

# Test 3: Leverage Levels
print("\n3️⃣  TESTING LEVERAGE LEVELS")
print("-" * 80)

leverage_configs = [
    (2, "2x Leverage"),
    (3, "3x Leverage (Current)"),
    (4, "4x Leverage"),
    (5, "5x Leverage"),
]

for lev, desc in leverage_configs:
    strategy = LondonBreakoutV41ADAUSDBybit(
        risk_percent=1.0,
        initial_capital=10000,
        leverage=lev
    )

    trades, equity = strategy.run(test_h1.copy(), test_h4.copy())

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        total_pnl = trades['pnl'].sum()
        win_rate = len(wins) / len(trades) * 100
        profit_factor = abs(wins['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()) if len(trades[trades['pnl'] <= 0]) > 0 else float('inf')

        equity['peak'] = equity['equity'].cummax()
        equity['drawdown'] = (equity['equity'] - equity['peak']) / equity['peak'] * 100
        max_dd = equity['drawdown'].min()

        avg_margin = trades['margin'].mean()
        max_margin = trades['margin'].max()

        print(f"  {desc:<25} | {len(trades):2} trades | WR: {win_rate:5.1f}% | P&L: ${total_pnl:>7,.0f} | PF: {profit_factor:4.2f} | DD: {max_dd:6.2f}% | Margin: {avg_margin/10000*100:.0f}%/{max_margin/10000*100:.0f}%")

        results.append({
            'config': desc,
            'category': 'Leverage',
            'trades': len(trades),
            'win_rate': win_rate,
            'pnl': total_pnl,
            'pf': profit_factor,
            'dd': max_dd,
            'score': (total_pnl / 10000) * (win_rate / 100) * (profit_factor / 2) * (1 + max_dd / 100)
        })

# Test 4: Momentum Filters
print("\n4️⃣  TESTING MOMENTUM FILTERS")
print("-" * 80)

momentum_configs = [
    (0.010, "Low Filter (1%)"),
    (0.015, "Current (1.5%)"),
    (0.020, "High Filter (2%)"),
    (0.025, "Very High (2.5%)"),
]

for mom, desc in momentum_configs:
    strategy = LondonBreakoutV41ADAUSDBybit(
        risk_percent=1.0,
        initial_capital=10000,
        leverage=3
    )
    strategy.min_first_hour_move_pct = mom

    trades, equity = strategy.run(test_h1.copy(), test_h4.copy())

    if len(trades) > 0:
        wins = trades[trades['pnl'] > 0]
        total_pnl = trades['pnl'].sum()
        win_rate = len(wins) / len(trades) * 100
        profit_factor = abs(wins['pnl'].sum() / trades[trades['pnl'] <= 0]['pnl'].sum()) if len(trades[trades['pnl'] <= 0]) > 0 else float('inf')

        equity['peak'] = equity['equity'].cummax()
        equity['drawdown'] = (equity['equity'] - equity['peak']) / equity['peak'] * 100
        max_dd = equity['drawdown'].min()

        print(f"  {desc:<25} | {len(trades):2} trades | WR: {win_rate:5.1f}% | P&L: ${total_pnl:>7,.0f} | PF: {profit_factor:4.2f} | DD: {max_dd:6.2f}%")

        results.append({
            'config': desc,
            'category': 'Momentum',
            'trades': len(trades),
            'win_rate': win_rate,
            'pnl': total_pnl,
            'pf': profit_factor,
            'dd': max_dd,
            'score': (total_pnl / 10000) * (win_rate / 100) * (profit_factor / 2) * (1 + max_dd / 100)
        })

# Summary
print("\n" + "="*80)
print("OPTIMIZATION SUMMARY - TOP PERFORMERS BY CATEGORY")
print("="*80)

df_results = pd.DataFrame(results)

for category in df_results['category'].unique():
    cat_results = df_results[df_results['category'] == category].sort_values('score', ascending=False)
    print(f"\n🏆 {category} - Top 3:")
    for idx, row in cat_results.head(3).iterrows():
        print(f"  {idx+1}. {row['config']:<30} | Score: {row['score']:.3f} | P&L: ${row['pnl']:>7,.0f} | WR: {row['win_rate']:.1f}% | PF: {row['pf']:.2f}")

# Overall best
print("\n" + "="*80)
print("🥇 OVERALL BEST CONFIGURATION")
print("="*80)

best = df_results.sort_values('score', ascending=False).iloc[0]
print(f"\nCategory: {best['category']}")
print(f"Config: {best['config']}")
print(f"Score: {best['score']:.3f}")
print(f"Trades: {best['trades']}")
print(f"Win Rate: {best['win_rate']:.1f}%")
print(f"P&L: ${best['pnl']:,.0f}")
print(f"Profit Factor: {best['pf']:.2f}")
print(f"Max Drawdown: {best['dd']:.2f}%")

# Recommended configuration
print("\n" + "="*80)
print("💡 RECOMMENDED OPTIMIZED PARAMETERS")
print("="*80)

# Get best from each category
best_range = df_results[df_results['category'] == 'Range'].sort_values('score', ascending=False).iloc[0]
best_rr = df_results[df_results['category'] == 'RR_Ratio'].sort_values('score', ascending=False).iloc[0]
best_lev = df_results[df_results['category'] == 'Leverage'].sort_values('score', ascending=False).iloc[0]
best_mom = df_results[df_results['category'] == 'Momentum'].sort_values('score', ascending=False).iloc[0]

print(f"\nBest Asia Range: {best_range['config']}")
print(f"Best R/R Ratio: {best_rr['config']}")
print(f"Best Leverage: {best_lev['config']}")
print(f"Best Momentum: {best_mom['config']}")

print("\n📋 NEXT STEPS:")
print("1. Test combined optimal parameters")
print("2. Validate on full period (2023-2025)")
print("3. Create optimized strategy file")
print("4. Update trading plan with new parameters")
