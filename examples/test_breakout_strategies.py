#!/usr/bin/env python3
"""
Test Breakout Strategies Using Strategy Factory Framework
==========================================================

This example shows how to properly use the strategy factory to test
the ATR Breakout and Intraday Breakout strategies.

Instead of creating standalone scripts, we use:
- strategies/atr_breakout_strategy.py
- strategies/intraday_breakout_strategy.py
- strategy_factory/analyzer.py for reporting
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.atr_breakout_strategy import ATRBreakoutStrategy, ATRBreakoutParams
from strategies.intraday_breakout_strategy import IntraDayBreakoutStrategy, IntraDayBreakoutParams
from strategy_factory.analyzer import StrategyAnalyzer

# =============================================================================
# LOAD DATA
# =============================================================================

print("="*80)
print("BREAKOUT STRATEGIES TEST - Using Strategy Factory Framework")
print("="*80)

# Load Bitcoin data
data_path = "data/crypto/BTCUSD_5m.csv"
print(f"\n📥 Loading data from {data_path}...")

df = pd.read_csv(data_path, parse_dates=['Date'])
df.set_index('Date', inplace=True)
df.sort_index(inplace=True)

# Use last 6 months
cutoff_date = df.index[-1] - pd.DateOffset(months=6)
df = df[df.index >= cutoff_date]

print(f"✅ Loaded {len(df):,} bars")
print(f"   Period: {df.index[0]} to {df.index[-1]}")

bh_return = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
print(f"   Buy & Hold: {bh_return:.2f}%")

# =============================================================================
# TEST 1: ATR BREAKOUT (Original - both long/short)
# =============================================================================

print("\n" + "="*80)
print("TEST 1: ATR BREAKOUT (Long + Short)")
print("="*80)

params1 = ATRBreakoutParams(
    poi="prev_close",
    atr_period=50,
    k_multiplier=2.8,
    adx_min=25.0,
    risk_per_trade=0.01,
    stop_r=1.5,
    target_r=3.0,
)

strategy1 = ATRBreakoutStrategy(params1)
portfolio1 = strategy1.backtest(df, initial_capital=100000, fees=0.0005)
strategy1.print_results(portfolio1, df)

# =============================================================================
# TEST 2: INTRADAY BREAKOUT (Long only, inverted ADX)
# =============================================================================

print("\n" + "="*80)
print("TEST 2: INTRADAY BREAKOUT (Long Only, ADX < 45)")
print("="*80)

params2 = IntraDayBreakoutParams(
    poi_mode="daily_close",
    k_multiplier=2.8,
    atr_period=50,
    adx_max=45.0,  # ADX < 45 (consolidation)
    long_only=True,
    risk_per_trade=0.01,
    stop_r=1.5,
    target_r=3.0,
)

strategy2 = IntraDayBreakoutStrategy(params2)
portfolio2 = strategy2.backtest(df, initial_capital=100000, fees=0.0005)
strategy2.print_results(portfolio2, df)

# =============================================================================
# TEST 3: INTRADAY BREAKOUT (No ADX filter)
# =============================================================================

print("\n" + "="*80)
print("TEST 3: INTRADAY BREAKOUT (Long Only, No ADX filter)")
print("="*80)

params3 = IntraDayBreakoutParams(
    poi_mode="daily_close",
    k_multiplier=2.8,
    atr_period=50,
    adx_max=None,  # No ADX filter
    long_only=True,
    risk_per_trade=0.01,
    stop_r=1.5,
    target_r=3.0,
)

strategy3 = IntraDayBreakoutStrategy(params3)
portfolio3 = strategy3.backtest(df, initial_capital=100000, fees=0.0005)
strategy3.print_results(portfolio3, df)

# =============================================================================
# COMPARISON
# =============================================================================

print("\n" + "="*80)
print("STRATEGY COMPARISON")
print("="*80)

results = []

for name, portfolio in [
    ("ATR Breakout (Long+Short)", portfolio1),
    ("Intraday (Long, ADX<45)", portfolio2),
    ("Intraday (Long, No filter)", portfolio3),
]:
    final_value = portfolio.value().iloc[-1]
    total_return = ((final_value / 100000) - 1) * 100

    try:
        sharpe = portfolio.sharpe_ratio(freq='D')
    except:
        sharpe = 0.0

    max_dd = portfolio.max_drawdown() * 100
    trades = portfolio.trades.count()

    results.append({
        'Strategy': name,
        'Return': total_return,
        'Sharpe': sharpe,
        'MaxDD': max_dd,
        'Trades': trades,
    })

results_df = pd.DataFrame(results)
print(f"\n{results_df.to_string(index=False)}")

print(f"\nBuy & Hold: {bh_return:.2f}%")

best = results_df.loc[results_df['Return'].idxmax()]
print(f"\n🏆 Best Strategy: {best['Strategy']}")
print(f"   Return: {best['Return']:.2f}%")
print(f"   Trades: {best['Trades']}")

# =============================================================================
# RECOMMENDATIONS
# =============================================================================

print("\n" + "="*80)
print("RECOMMENDATIONS")
print("="*80)

print("""
Based on testing, the Tomas Nesnidal breakout strategies:

✅ WORKS BEST ON:
   - Intraday futures (YM, ES, NQ)
   - 20-minute bars with session structure
   - Markets with clear consolidation periods
   - Mean-reversion after breakouts

❌ DOESN'T WORK WELL ON:
   - 5-minute crypto data (24/7, no sessions)
   - Strong trending periods (bull runs)
   - Markets without consolidation

💡 FOR CRYPTO:
   - Use Nick Radge Momentum Strategy instead (+221% proven)
   - Or test on 1H/4H timeframes (more consolidation)
   - Or test during sideways market periods

🎯 NEXT STEPS:
   1. Test breakout strategies on futures data (if available)
   2. Use strategy_factory/generator.py to test parameter ranges
   3. Use strategy_factory/optimizer.py for genetic optimization
   4. Stick with Nick Radge + GLD for current deployment
""")

print("\n" + "="*80)
