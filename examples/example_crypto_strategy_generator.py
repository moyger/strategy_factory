"""
Example: Using StrategyGenerator for Crypto Strategy Testing

This demonstrates the CORRECT way to test crypto strategies using the
strategy factory framework instead of standalone backtest scripts.

Usage:
    python examples/example_crypto_strategy_generator.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import yfinance as yf
from strategy_factory.generator import StrategyGenerator
from strategy_factory.analyzer import StrategyAnalyzer

print("="*80)
print("CRYPTO STRATEGY TESTING - USING STRATEGY FACTORY FRAMEWORK")
print("="*80)
print("\n✅ This is the CORRECT approach:")
print("   - Uses StrategyGenerator from framework")
print("   - Tests multiple parameter combinations")
print("   - Returns sorted results by Sharpe ratio")
print("   - Can be extended with StrategyOptimizer for walk-forward validation")
print("\n❌ Instead of creating standalone backtest scripts")

# ============================================================================
# STEP 1: DOWNLOAD DATA
# ============================================================================
print("\n" + "="*80)
print("STEP 1: DOWNLOAD CRYPTO DATA")
print("="*80)

# Fixed crypto universe (proven optimal from research)
CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD'
]

print(f"\nDownloading {len(CRYPTO_UNIVERSE)} cryptos...")
print(f"Period: 2020-01-01 to 2024-12-31")

data = yf.download(CRYPTO_UNIVERSE, start='2020-01-01', end='2024-12-31',
                   progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill()

# Remove cryptos with insufficient data
min_data_points = 100
valid_tickers = [col for col in close.columns if close[col].count() >= min_data_points]
crypto_prices = close[valid_tickers]

print(f"✅ Data ready: {len(crypto_prices)} days, {len(valid_tickers)} cryptos")
print(f"   Tickers: {', '.join([t.replace('-USD', '') for t in valid_tickers])}")

# ============================================================================
# STEP 2: INITIALIZE STRATEGY GENERATOR
# ============================================================================
print("\n" + "="*80)
print("STEP 2: INITIALIZE STRATEGY GENERATOR")
print("="*80)

generator = StrategyGenerator(
    initial_capital=100000,
    commission=0.001  # 0.1% per trade
)

print("\n✅ StrategyGenerator initialized")
print(f"   Initial Capital: $100,000")
print(f"   Commission: 0.1%")

# ============================================================================
# STEP 3: TEST FIXED UNIVERSE WITH DIFFERENT PARAMETERS
# ============================================================================
print("\n" + "="*80)
print("STEP 3: TEST FIXED UNIVERSE (BASELINE)")
print("="*80)
print("\nTesting different parameter combinations:")
print("  - ROC periods: [60, 90, 100]")
print("  - Rebalance frequency: ['quarterly', 'monthly']")
print("  - Num positions: [5, 7]")

results_fixed = generator.generate_crypto_momentum_strategies(
    prices=crypto_prices,
    universe_type='fixed',
    roc_periods=[60, 90, 100],
    rebalance_freq=['quarterly', 'monthly'],
    num_positions=[5, 7],
    verbose=True
)

print("\n📊 TOP 5 FIXED UNIVERSE CONFIGURATIONS:")
print(results_fixed.head(5).to_string(index=False))

# ============================================================================
# STEP 4: TEST DYNAMIC UNIVERSE (ROC MOMENTUM)
# ============================================================================
print("\n" + "="*80)
print("STEP 4: TEST DYNAMIC UNIVERSE (ROC MOMENTUM)")
print("="*80)
print("\nComparing to dynamic rebalancing approach...")

results_dynamic = generator.generate_crypto_momentum_strategies(
    prices=crypto_prices,
    universe_type='roc_momentum',
    roc_periods=[90],
    rebalance_freq=['quarterly'],
    num_positions=[5, 7],
    verbose=True
)

print("\n📊 DYNAMIC UNIVERSE RESULTS:")
print(results_dynamic.head(3).to_string(index=False))

# ============================================================================
# STEP 5: COMPARISON
# ============================================================================
print("\n" + "="*80)
print("STEP 5: COMPARISON - FIXED VS DYNAMIC")
print("="*80)

best_fixed = results_fixed.iloc[0]
best_dynamic = results_dynamic.iloc[0]

comparison = pd.DataFrame([
    {
        'Approach': 'Fixed Universe',
        'ROC Period': best_fixed['params']['roc_period'],
        'Rebalance': best_fixed['params']['rebalance_freq'],
        'Positions': best_fixed['params']['num_positions'],
        'Total Return %': f"{best_fixed['total_return']:.1f}",
        'Sharpe': f"{best_fixed['sharpe_ratio']:.2f}",
        'Max DD %': f"{best_fixed['max_drawdown']:.1f}",
        'Trades/Year': f"{best_fixed['trades_per_year']:.1f}"
    },
    {
        'Approach': 'Dynamic (ROC)',
        'ROC Period': best_dynamic['params']['roc_period'],
        'Rebalance': best_dynamic['params']['rebalance_freq'],
        'Positions': best_dynamic['params']['num_positions'],
        'Total Return %': f"{best_dynamic['total_return']:.1f}",
        'Sharpe': f"{best_dynamic['sharpe_ratio']:.2f}",
        'Max DD %': f"{best_dynamic['max_drawdown']:.1f}",
        'Trades/Year': f"{best_dynamic['trades_per_year']:.1f}"
    }
])

print("\n" + comparison.to_string(index=False))

# Analysis
print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

return_diff = best_fixed['total_return'] - best_dynamic['total_return']
sharpe_diff = best_fixed['sharpe_ratio'] - best_dynamic['sharpe_ratio']

print(f"\n📊 PERFORMANCE DIFFERENCE (Fixed vs Dynamic):")
print(f"   Return: {return_diff:+.1f}% {'✅ Fixed wins' if return_diff > 0 else '❌ Dynamic wins'}")
print(f"   Sharpe: {sharpe_diff:+.2f} {'✅ Fixed wins' if sharpe_diff > 0 else '❌ Dynamic wins'}")

if return_diff > 0 and sharpe_diff > 0:
    print(f"\n✅ VERDICT: Fixed universe is superior")
    print(f"   Use: {int(best_fixed['params']['num_positions'])} positions, "
          f"{best_fixed['params']['rebalance_freq']} rebalancing, "
          f"{int(best_fixed['params']['roc_period'])}-day ROC")
else:
    print(f"\n⚠️ VERDICT: Dynamic universe performed better in this test")
    print(f"   However, research shows fixed universe more robust long-term")

# ============================================================================
# STEP 6: OPTIONAL - FILTER BY QUALITY CRITERIA
# ============================================================================
print("\n" + "="*80)
print("STEP 6: FILTER BY QUALITY CRITERIA")
print("="*80)

print("\nApplying quality filters:")
print("  - Min Sharpe: 0.80")
print("  - Max Drawdown: 50%")
print("  - Min Trades: 20")
print("  - Min Win Rate: 40%")

filtered = generator.filter_strategies(
    results=results_fixed,
    min_sharpe=0.80,
    max_drawdown=50.0,
    min_trades=20,
    min_win_rate=0.40
)

if len(filtered) > 0:
    print("\n📊 FILTERED STRATEGIES (Quality-Passed):")
    print(filtered.head(5).to_string(index=False))
else:
    print("\n⚠️ No strategies passed quality filters (criteria too strict)")

# ============================================================================
# STEP 7: SAVE RESULTS
# ============================================================================
print("\n" + "="*80)
print("STEP 7: SAVE RESULTS")
print("="*80)

output_dir = Path('results/crypto')
output_dir.mkdir(parents=True, exist_ok=True)

results_fixed.to_csv(output_dir / 'strategy_generator_fixed_universe.csv', index=False)
results_dynamic.to_csv(output_dir / 'strategy_generator_dynamic_universe.csv', index=False)

print(f"\n✅ Results saved:")
print(f"   {output_dir}/strategy_generator_fixed_universe.csv")
print(f"   {output_dir}/strategy_generator_dynamic_universe.csv")

# ============================================================================
# NEXT STEPS
# ============================================================================
print("\n" + "="*80)
print("NEXT STEPS")
print("="*80)

print("""
✅ This example demonstrates the CORRECT workflow:
   1. Use StrategyGenerator for parameter testing
   2. Get sorted results by Sharpe ratio
   3. Filter by quality criteria
   4. Save results for analysis

🔧 To extend this:
   1. Add walk-forward validation:
      from strategy_factory.optimizer import StrategyOptimizer
      optimizer = StrategyOptimizer()
      optimizer.walk_forward_validation(...)

   2. Add Monte Carlo simulation:
      optimizer.monte_carlo_simulation(...)

   3. Add QuantStats report:
      analyzer = StrategyAnalyzer()
      analyzer.generate_tearsheet(...)

📚 See also:
   - examples/test_breakout_strategies.py
   - notebooks/01_strategy_generation.ipynb
   - strategy_factory/optimizer.py
""")

print("\n✅ Example complete!")
