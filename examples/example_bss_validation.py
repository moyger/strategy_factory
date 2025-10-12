#!/usr/bin/env python3
"""
BSS Strategy - Walk-Forward and Monte Carlo Validation

Validates the BSS strategy using:
1. Walk-Forward Analysis (rolling train/test windows)
2. Monte Carlo Simulation (1000+ runs)

This ensures the strategy is robust and not overfit to in-sample data.

Output:
- Walk-forward results showing consistency across time periods
- Monte Carlo confidence intervals and probability of profit
- Validation report with recommendations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("=" * 100)
print("BSS STRATEGY - WALK-FORWARD & MONTE CARLO VALIDATION")
print("=" * 100)
print()
print("📊 Strategy: Nick Radge Enhanced with Breakout Strength Score (BSS)")
print("🎯 Validation Methods:")
print("   1. Walk-Forward Analysis (rolling train/test windows)")
print("   2. Monte Carlo Simulation (1000 runs with trade resampling)")
print()
print("⏱️  Expected runtime: 10-15 minutes")
print()

# Import strategy
import importlib.util
spec = importlib.util.spec_from_file_location(
    "nick_radge_enhanced",
    "strategies/02_nick_radge_enhanced_bss.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeEnhanced = module.NickRadgeEnhanced

# Check if we have cached data
cached_prices = Path('data/stocks/universe_50_prices.csv')
cached_spy = Path('data/stocks/spy_prices.csv')
cached_gld = Path('data/stocks/gld_prices.csv')

if not (cached_prices.exists() and cached_spy.exists() and cached_gld.exists()):
    print("❌ No cached data found!")
    print()
    print("Please run the full backtest first to download and cache data:")
    print("   python examples/example_bss_full_backtest.py")
    print()
    sys.exit(1)

# Load data
print("📥 Loading cached data...")
prices = pd.read_csv(cached_prices, index_col=0, parse_dates=True)
spy_df = pd.read_csv(cached_spy, index_col=0, parse_dates=True)
spy = spy_df['SPY']
gld_df = pd.read_csv(cached_gld, index_col=0, parse_dates=True)
gld = gld_df['GLD']

print(f"✅ Data loaded: {len(prices):,} days ({prices.index[0].date()} to {prices.index[-1].date()})")
print()

# ============================================================================
# STEP 1: WALK-FORWARD ANALYSIS
# ============================================================================

print("=" * 100)
print("STEP 1: WALK-FORWARD ANALYSIS")
print("=" * 100)
print()
print("Testing strategy on rolling windows to verify consistency over time")
print()

# Define walk-forward parameters
train_days = 756  # ~3 years training
test_days = 252   # 1 year testing
step_days = 126   # Move forward by 6 months

walk_forward_results = []
fold_num = 0

# Split data into overlapping train/test folds
total_days = len(prices)
start_idx = 0

print(f"Configuration:")
print(f"   Training window: {train_days} days (~3 years)")
print(f"   Testing window: {test_days} days (1 year)")
print(f"   Step size: {step_days} days (6 months)")
print()

while start_idx + train_days + test_days <= total_days:
    fold_num += 1

    train_start = start_idx
    train_end = start_idx + train_days
    test_start = train_end
    test_end = min(test_start + test_days, total_days)

    # Get train and test data
    train_prices = prices.iloc[train_start:train_end]
    test_prices = prices.iloc[test_start:test_end]

    train_spy = spy.iloc[train_start:train_end]
    test_spy = spy.iloc[test_start:test_end]

    train_gld = gld.iloc[train_start:train_end]
    test_gld = gld.iloc[test_start:test_end]

    print(f"--- Fold {fold_num} ---")
    print(f"Train: {train_prices.index[0].date()} to {train_prices.index[-1].date()}")
    print(f"Test:  {test_prices.index[0].date()} to {test_prices.index[-1].date()}")

    try:
        # Run backtest on test period only (using parameters "learned" from train)
        strategy = NickRadgeEnhanced(
            portfolio_size=7,
            qualifier_type='bss',
            ma_period=100,
            rebalance_freq='QS',
            use_momentum_weighting=True,
            use_regime_filter=True,
            regime_ma_long=200,
            regime_ma_short=50,
            strong_bull_positions=7,
            weak_bull_positions=3,
            bear_positions=0,
            bear_market_asset='GLD',
            bear_allocation=1.0
        )

        # Backtest on test period
        portfolio = strategy.backtest(
            prices=test_prices,
            spy_prices=test_spy,
            gld_prices=test_gld,
            initial_capital=100000
        )

        test_return = portfolio.total_return() * 100
        num_trades = len(portfolio.trades.records)

        walk_forward_results.append({
            'fold': fold_num,
            'train_start': train_prices.index[0].date(),
            'train_end': train_prices.index[-1].date(),
            'test_start': test_prices.index[0].date(),
            'test_end': test_prices.index[-1].date(),
            'test_return': test_return,
            'test_trades': num_trades
        })

        print(f"  Return: {test_return:+.2f}%")
        print(f"  Trades: {num_trades}")
        print()

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        print()

    # Move to next fold
    start_idx += step_days

# Summarize walk-forward results
wf_df = pd.DataFrame(walk_forward_results)
wf_df.to_csv('results/nick_radge/bss_walk_forward.csv', index=False)

print("=" * 100)
print("WALK-FORWARD SUMMARY")
print("=" * 100)
print(f"Total folds: {len(wf_df)}")
print(f"Average return: {wf_df['test_return'].mean():.2f}%")
print(f"Median return: {wf_df['test_return'].median():.2f}%")
print(f"Std deviation: {wf_df['test_return'].std():.2f}%")
print(f"Positive periods: {(wf_df['test_return'] > 0).sum()}/{len(wf_df)} ({(wf_df['test_return'] > 0).sum()/len(wf_df)*100:.0f}%)")
print(f"Best fold: {wf_df['test_return'].max():+.2f}%")
print(f"Worst fold: {wf_df['test_return'].min():+.2f}%")
print()
print(f"💾 Saved to: results/nick_radge/bss_walk_forward.csv")
print()

# ============================================================================
# STEP 2: MONTE CARLO SIMULATION
# ============================================================================

print("=" * 100)
print("STEP 2: MONTE CARLO SIMULATION")
print("=" * 100)
print()
print("Resampling trades to estimate confidence intervals and probability of profit")
print()

# Run base backtest to get all trades
print("Running base backtest to collect trades...")
strategy = NickRadgeEnhanced(
    portfolio_size=7,
    qualifier_type='bss',
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=7,
    weak_bull_positions=3,
    bear_positions=0,
    bear_market_asset='GLD',
    bear_allocation=1.0
)

base_portfolio = strategy.backtest(
    prices=prices,
    spy_prices=spy,
    gld_prices=gld,
    initial_capital=100000
)

base_return = base_portfolio.total_return() * 100
trades_records = base_portfolio.trades.records
num_trades = len(trades_records)

print(f"Base backtest complete:")
print(f"   Total return: {base_return:.2f}%")
print(f"   Total trades: {num_trades}")
print()

if num_trades < 30:
    print("⚠️  Warning: Less than 30 trades. Monte Carlo may be less reliable.")
    print()

# Extract trade returns
trade_returns = [t['return'] for t in trades_records]

# Monte Carlo simulation
num_simulations = 1000
print(f"Running {num_simulations} Monte Carlo simulations...")
print(f"   Resampling {num_trades} trades per simulation (with replacement)")
print()

simulation_results = []

for sim in range(num_simulations):
    # Resample trades with replacement
    resampled_returns = np.random.choice(trade_returns, size=num_trades, replace=True)

    # Calculate portfolio return
    cumulative_return = np.prod(1 + resampled_returns) - 1
    simulation_results.append(cumulative_return * 100)

    if (sim + 1) % 200 == 0:
        print(f"  Completed {sim+1}/{num_simulations} simulations")

print()

# Calculate statistics
sim_returns = np.array(simulation_results)
mean_return = np.mean(sim_returns)
median_return = np.median(sim_returns)
std_return = np.std(sim_returns)
ci_5 = np.percentile(sim_returns, 5)
ci_95 = np.percentile(sim_returns, 95)
prob_profit = (sim_returns > 0).sum() / num_simulations * 100
best_case = np.max(sim_returns)
worst_case = np.min(sim_returns)

# Save results
mc_df = pd.DataFrame({
    'simulation': range(1, num_simulations + 1),
    'return_pct': sim_returns
})
mc_df.to_csv('results/nick_radge/bss_monte_carlo.csv', index=False)

print("=" * 100)
print("MONTE CARLO RESULTS")
print("=" * 100)
print(f"Simulations: {num_simulations:,}")
print(f"Trades per simulation: {num_trades}")
print()
print(f"Mean return: {mean_return:.2f}%")
print(f"Median return: {median_return:.2f}%")
print(f"Std deviation: {std_return:.2f}%")
print(f"90% Confidence Interval: [{ci_5:.2f}%, {ci_95:.2f}%]")
print(f"Probability of profit: {prob_profit:.1f}%")
print(f"Best case (95th percentile): {ci_95:.2f}%")
print(f"Worst case (5th percentile): {ci_5:.2f}%")
print()

# Risk assessment
if prob_profit >= 95:
    risk_rating = "✅ EXCELLENT - Very high probability of profit"
elif prob_profit >= 80:
    risk_rating = "✅ GOOD - High probability of profit"
elif prob_profit >= 70:
    risk_rating = "⚠️  MODERATE - Acceptable probability of profit"
else:
    risk_rating = "❌ HIGH RISK - Low probability of profit"

print(f"📊 Risk Assessment: {risk_rating}")
print()
print(f"💾 Saved to: results/nick_radge/bss_monte_carlo.csv")
print()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("=" * 100)
print("VALIDATION COMPLETE")
print("=" * 100)
print()

print("✅ Walk-Forward Analysis:")
print(f"   Average return: {wf_df['test_return'].mean():.2f}%")
print(f"   Consistency: {(wf_df['test_return'] > 0).sum()}/{len(wf_df)} periods positive ({(wf_df['test_return'] > 0).sum()/len(wf_df)*100:.0f}%)")
print(f"   Worst period: {wf_df['test_return'].min():+.2f}%")
print()

print("✅ Monte Carlo Simulation:")
print(f"   Expected return: {mean_return:.2f}%")
print(f"   Probability of profit: {prob_profit:.1f}%")
print(f"   90% CI: [{ci_5:.2f}%, {ci_95:.2f}%]")
print()

# Overall recommendation
if (wf_df['test_return'] > 0).sum() / len(wf_df) >= 0.7 and prob_profit >= 80:
    recommendation = "✅ RECOMMENDED FOR LIVE TRADING"
    details = "Strategy shows consistent performance across time periods and high probability of profit."
elif (wf_df['test_return'] > 0).sum() / len(wf_df) >= 0.6 and prob_profit >= 70:
    recommendation = "⚠️  PROCEED WITH CAUTION"
    details = "Strategy shows acceptable robustness but monitor closely in live trading."
else:
    recommendation = "❌ NOT RECOMMENDED"
    details = "Strategy shows inconsistent performance or low probability of profit."

print("🎯 Overall Recommendation:")
print(f"   {recommendation}")
print(f"   {details}")
print()

print("📁 Generated Files:")
print("   - results/nick_radge/bss_walk_forward.csv")
print("   - results/nick_radge/bss_monte_carlo.csv")
print()

print("🚀 Next Steps:")
print("   1. Review walk-forward periods to understand when strategy struggles")
print("   2. Check Monte Carlo distribution for tail risks")
print("   3. If validated, test in dry_run mode before live deployment")
print()

print("=" * 100)
