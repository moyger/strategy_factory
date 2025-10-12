#!/usr/bin/env python3
"""
Quick Start Example - Strategy Factory

This script demonstrates the complete workflow:
1. Load data
2. Generate strategies
3. Optimize top performers
4. Analyze results
5. Export for deployment

Run: python quick_start.py
"""

import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from strategy_factory.generator import StrategyGenerator
from strategy_factory.optimizer import StrategyOptimizer
from strategy_factory.analyzer import StrategyAnalyzer

print("=" * 80)
print("STRATEGY FACTORY - QUICK START")
print("=" * 80)

# ==========================================
# 1. LOAD DATA
# ==========================================
print("\n📊 Step 1: Loading market data...")

df = pd.read_csv('data/crypto/BTCUSD_5m.csv')
df.columns = df.columns.str.lower()

if 'date' in df.columns:
    df = df.rename(columns={'date': 'timestamp'})

df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

print(f"✅ Loaded {len(df):,} bars")
print(f"   Period: {df.index[0]} to {df.index[-1]}")

# ==========================================
# 2. GENERATE STRATEGIES
# ==========================================
print("\n🔄 Step 2: Generating strategies...")

generator = StrategyGenerator(initial_capital=10000, commission=0.001)

# Generate SMA strategies
print("\n  Testing SMA crossovers...")
sma_results = generator.generate_sma_strategies(
    df=df,
    fast_range=[5, 10, 15, 20],
    slow_range=[50, 100, 150, 200],
    verbose=False
)

# Generate RSI strategies
print("  Testing RSI mean reversion...")
rsi_results = generator.generate_rsi_strategies(
    df=df,
    period_range=[7, 14, 21, 28],
    oversold_range=[20, 25, 30, 35],
    overbought_range=[65, 70, 75, 80],
    verbose=False
)

# Generate Breakout strategies
print("  Testing breakouts...")
breakout_results = generator.generate_breakout_strategies(
    df=df,
    lookback_range=[10, 20, 30, 50],
    breakout_pct_range=[0.5, 1.0, 1.5, 2.0],
    verbose=False
)

# Combine all results
all_results = pd.concat([sma_results, rsi_results, breakout_results], ignore_index=True)
all_results = all_results.sort_values('sharpe_ratio', ascending=False)

print(f"\n✅ Generated {len(all_results):,} strategies")
print(f"\n🏆 Top 10 Strategies:")
print("-" * 80)
for i, row in all_results.head(10).iterrows():
    print(f"{i+1}. {str(row['params']):60} Sharpe: {row['sharpe_ratio']:>6.2f}  Return: {row['total_return']:>7.2f}%")

# ==========================================
# 3. FILTER BY QUALITY CRITERIA
# ==========================================
print("\n🔍 Step 3: Filtering by quality criteria...")

filtered = generator.filter_strategies(
    results=all_results,
    min_sharpe=1.0,
    max_drawdown=20.0,
    min_trades=10,
    min_win_rate=0.45
)

print(f"   {len(filtered)} / {len(all_results)} strategies passed filters")

# ==========================================
# 4. OPTIMIZE TOP STRATEGY
# ==========================================
print("\n🧬 Step 4: Optimizing top strategy with genetic algorithm...")

optimizer = StrategyOptimizer(initial_capital=10000, commission=0.001)

# Get top strategy type
top_strategy = all_results.iloc[0]

if 'SMA' in str(top_strategy['params']):
    print("   Optimizing SMA parameters...")
    opt_result = optimizer.optimize_sma(
        df=df,
        fast_range=(5, 30),
        slow_range=(40, 200),
        generations=20,  # Reduced for quick start
        population=30,
        verbose=False
    )
    print(f"\n✅ Optimized SMA: {opt_result.best_params}")
    print(f"   Sharpe: {opt_result.best_fitness:.2f}")

elif 'RSI' in str(top_strategy['params']):
    print("   Optimizing RSI parameters...")
    opt_result = optimizer.optimize_rsi(
        df=df,
        period_range=(5, 30),
        oversold_range=(15, 40),
        overbought_range=(60, 85),
        generations=20,
        population=30,
        verbose=False
    )
    print(f"\n✅ Optimized RSI: {opt_result.best_params}")
    print(f"   Sharpe: {opt_result.best_fitness:.2f}")
else:
    print(f"   ⚠️  No optimizer available for {top_strategy['params']}")
    opt_result = None

# ==========================================
# 5. WALK-FORWARD VALIDATION
# ==========================================
if opt_result is not None:
    print("\n🚶 Step 5: Walk-forward validation...")

    wf_results = optimizer.walk_forward_analysis(
        df=df,
        strategy_params=opt_result.best_params,
        train_window=2000,
        test_window=500,
        step_size=300,
        verbose=False
    )

    print(f"✅ Completed {len(wf_results)} folds")
    print(f"   Avg test return: {wf_results['test_return'].mean():.2f}%")
    print(f"   Avg test Sharpe: {wf_results['test_sharpe'].mean():.2f}")
    print(f"   Consistency: {(wf_results['test_return'] > 0).sum() / len(wf_results) * 100:.0f}% positive folds")

# ==========================================
# 6. MONTE CARLO SIMULATION
# ==========================================
if opt_result is not None:
    print("\n🎲 Step 6: Monte Carlo simulation...")

    mc_results = optimizer.monte_carlo_simulation(
        df=df,
        strategy_params=opt_result.best_params,
        n_simulations=500,  # Reduced for quick start
        confidence_level=0.95,
        verbose=False
    )

    print(f"✅ Completed 500 simulations")
    print(f"   Mean return: {mc_results['mean_return']:.2f}%")
    print(f"   95% CI: [{mc_results['lower_95']:.2f}%, {mc_results['upper_95']:.2f}%]")
    print(f"   Probability of profit: {mc_results['probability_positive']:.1f}%")

# ==========================================
# 7. SAVE RESULTS
# ==========================================
print("\n💾 Step 7: Saving results...")

# Save top strategies
all_results.head(50).to_csv('results/top_50_strategies.csv', index=False)
filtered.to_csv('results/filtered_strategies.csv', index=False)

if opt_result is not None and 'wf_results' in locals():
    wf_results.to_csv('results/walk_forward_results.csv', index=False)

    # Save optimized strategy
    optimized = pd.DataFrame([{
        'strategy_type': opt_result.best_params.get('type', 'Unknown'),
        'parameters': str(opt_result.best_params),
        'sharpe_ratio': opt_result.best_fitness,
        'wf_avg_return': wf_results['test_return'].mean(),
        'wf_avg_sharpe': wf_results['test_sharpe'].mean(),
        'mc_mean_return': mc_results['mean_return'] if 'mc_results' in locals() else None,
        'mc_prob_positive': mc_results['probability_positive'] if 'mc_results' in locals() else None
    }])
    optimized.to_csv('results/optimized_strategy.csv', index=False)

print("✅ Results saved:")
print("   - results/top_50_strategies.csv")
print("   - results/filtered_strategies.csv")
print("   - results/walk_forward_results.csv")
print("   - results/optimized_strategy.csv")

# ==========================================
# 8. SUMMARY
# ==========================================
print("\n" + "=" * 80)
print("✅ QUICK START COMPLETE!")
print("=" * 80)
print(f"\n📊 Summary:")
print(f"   Total strategies tested: {len(all_results):,}")
print(f"   Strategies passed filters: {len(filtered)}")
if opt_result is not None:
    print(f"   Best strategy: {opt_result.best_params}")
    print(f"   Optimized Sharpe: {opt_result.best_fitness:.2f}")
if 'wf_results' in locals():
    print(f"   Walk-forward validated: {len(wf_results)} folds")
if 'mc_results' in locals():
    print(f"   Monte Carlo probability of profit: {mc_results['probability_positive']:.1f}%")

print(f"\n🚀 Next Steps:")
print(f"   1. Review results in results/ folder")
print(f"   2. Run Jupyter notebooks for detailed analysis:")
print(f"      - notebooks/01_strategy_generation.ipynb")
print(f"      - notebooks/02_strategy_optimization.ipynb")
print(f"   3. Deploy to brokers using deployment/strategy_deployer.py")
print(f"   4. Read MULTI_BROKER_DEPLOYMENT.md for deployment guide")

print("\n" + "=" * 80)
