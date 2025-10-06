"""
Simplified Monte Carlo Simulation

Focus on:
1. Trade order shuffling (path independence)
2. Random win/loss sampling (bootstrap trades)
3. Confidence intervals for key metrics

Faster and more reliable than full bootstrap resampling.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from core.data_loader import ForexDataLoader


def simulate_equity_curve(trades, initial_capital):
    """Calculate equity curve from trades"""
    capital = initial_capital
    equity = [capital]
    peak = capital
    drawdowns = []

    for _, trade in trades.iterrows():
        capital += trade['pnl_dollars']
        equity.append(capital)

        if capital > peak:
            peak = capital

        dd = (capital - peak) / peak * 100 if peak > 0 else 0
        drawdowns.append(dd)

    max_dd = min(drawdowns) if drawdowns else 0
    final_capital = equity[-1]
    total_return = (final_capital - initial_capital) / initial_capital * 100

    return {
        'final_capital': final_capital,
        'total_return_pct': total_return,
        'max_drawdown_pct': max_dd,
        'equity_curve': equity
    }


def monte_carlo_shuffle(trades_df, initial_capital, num_simulations=1000):
    """Shuffle trade order to test path independence"""
    print(f"\n  Running {num_simulations} shuffling simulations...")

    results = []
    for i in range(num_simulations):
        if i % 200 == 0 and i > 0:
            print(f"    Progress: {i}/{num_simulations}")

        shuffled = trades_df.sample(frac=1.0).reset_index(drop=True)
        result = simulate_equity_curve(shuffled, initial_capital)
        results.append(result)

    return pd.DataFrame(results)


def monte_carlo_trade_sampling(trades_df, initial_capital, num_simulations=1000):
    """Bootstrap resample trades (with replacement)"""
    print(f"\n  Running {num_simulations} trade sampling simulations...")

    num_trades = len(trades_df)
    results = []

    for i in range(num_simulations):
        if i % 200 == 0 and i > 0:
            print(f"    Progress: {i}/{num_simulations}")

        # Sample trades with replacement
        sampled = trades_df.sample(n=num_trades, replace=True).reset_index(drop=True)
        result = simulate_equity_curve(sampled, initial_capital)

        # Calculate metrics
        wins = sampled[sampled['pnl_dollars'] > 0]
        wr = len(wins) / len(sampled) * 100 if len(sampled) > 0 else 0

        results.append({
            'final_capital': result['final_capital'],
            'total_return_pct': result['total_return_pct'],
            'max_drawdown_pct': result['max_drawdown_pct'],
            'win_rate': wr,
            'total_pnl': sampled['pnl_dollars'].sum()
        })

    return pd.DataFrame(results)


def print_distribution(name, data, units='', percentiles=[5, 25, 50, 75, 95]):
    """Print distribution statistics"""
    print(f"\n{name}:")
    print(f"  Mean: {units}{data.mean():,.1f}")
    print(f"  Std Dev: {units}{data.std():,.1f}")
    print(f"  Min: {units}{data.min():,.1f}")
    print(f"  Max: {units}{data.max():,.1f}")

    print(f"  Percentiles:")
    for p in percentiles:
        print(f"    {p}th: {units}{data.quantile(p/100):,.1f}")


if __name__ == '__main__':
    print("=" * 80)
    print("SIMPLIFIED MONTE CARLO SIMULATION")
    print("=" * 80)

    # Load data and run baseline
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    h1_df = h1_df[h1_df.index >= '2020-01-01']
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nPeriod: {h1_df.index.min().date()} to {h1_df.index.max().date()}")

    # Run baseline backtest
    print("\n" + "=" * 80)
    print("BASELINE BACKTEST")
    print("=" * 80)

    config = {
        'risk_percent': 0.75,
        'initial_capital': 100000
    }

    strategy = LondonBreakoutV41Optimized(
        risk_percent=config['risk_percent'],
        initial_capital=config['initial_capital'],
        enable_asia_breakout=True,
        enable_triangle_breakout=True
    )

    # Set optimal parameters
    strategy.triangle_lookback = 40
    strategy.triangle_r2_min = 0.5
    strategy.triangle_slope_tolerance = 0.0003
    strategy.triangle_time_end = 9

    strategy.pattern_detector = PatternDetector(
        lookback=40,
        min_pivot_points=3,
        r_squared_min=0.5,
        slope_tolerance=0.0003
    )

    trades = strategy.backtest(h1_df, h4_df)

    wins = trades[trades['pnl_dollars'] > 0]
    losses = trades[trades['pnl_dollars'] <= 0]

    days = (h1_df.index.max() - h1_df.index.min()).days
    years = days / 365.25

    baseline_wr = len(wins) / len(trades) * 100
    baseline_pnl = trades['pnl_dollars'].sum()
    baseline_annual = baseline_pnl / years
    baseline_pf = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())

    print(f"\nBaseline Performance:")
    print(f"  Period: {years:.2f} years")
    print(f"  Total Trades: {len(trades)} ({len(trades)/years:.1f}/year)")
    print(f"    Asia: {len(trades[trades['signal_type']=='asia_breakout'])}")
    print(f"    Triangle: {len(trades[trades['signal_type'].str.contains('triangle', na=False)])}")
    print(f"  Win Rate: {baseline_wr:.1f}%")
    print(f"  Total P&L: ${baseline_pnl:,.0f}")
    print(f"  Annual P&L: ${baseline_annual:,.0f}")
    print(f"  Profit Factor: {baseline_pf:.2f}")

    baseline_equity = simulate_equity_curve(trades, config['initial_capital'])
    print(f"  Max Drawdown: {baseline_equity['max_drawdown_pct']:.1f}%")

    # Monte Carlo 1: Trade Order Shuffling
    print("\n" + "=" * 80)
    print("1. TRADE ORDER SHUFFLING")
    print("=" * 80)
    print("Testing if results depend on trade sequence...")

    shuffle_results = monte_carlo_shuffle(trades, config['initial_capital'], 1000)

    print_distribution("Final Capital", shuffle_results['final_capital'], '$')
    print_distribution("Total Return", shuffle_results['total_return_pct'], '', [5, 50, 95])
    print_distribution("Max Drawdown", shuffle_results['max_drawdown_pct'], '', [5, 50, 95])

    # Check if all shuffles give same final capital
    if shuffle_results['final_capital'].std() < 1:
        print("\n  ✅ Trade order does NOT affect final P&L (as expected)")
        print("  ✅ Only affects drawdown path")
    else:
        print("\n  ⚠️ Unexpected: Trade order affects results")

    # Monte Carlo 2: Trade Sampling
    print("\n" + "=" * 80)
    print("2. TRADE BOOTSTRAP SAMPLING")
    print("=" * 80)
    print("Testing variability by resampling trades with replacement...")

    sampling_results = monte_carlo_trade_sampling(trades, config['initial_capital'], 1000)

    print_distribution("Final Capital", sampling_results['final_capital'], '$')
    print_distribution("Total P&L", sampling_results['total_pnl'], '$')
    print_distribution("Win Rate", sampling_results['win_rate'], '', [5, 25, 50, 75, 95])
    print_distribution("Max Drawdown", sampling_results['max_drawdown_pct'], '', [5, 50, 95])

    # Confidence Intervals
    print("\n" + "=" * 80)
    print("CONFIDENCE INTERVALS (95%)")
    print("=" * 80)

    print(f"\nTotal P&L:")
    print(f"  Baseline: ${baseline_pnl:,.0f}")
    print(f"  95% CI: [${sampling_results['total_pnl'].quantile(0.025):,.0f}, ${sampling_results['total_pnl'].quantile(0.975):,.0f}]")

    print(f"\nWin Rate:")
    print(f"  Baseline: {baseline_wr:.1f}%")
    print(f"  95% CI: [{sampling_results['win_rate'].quantile(0.025):.1f}%, {sampling_results['win_rate'].quantile(0.975):.1f}%]")

    print(f"\nMax Drawdown (worst case scenarios):")
    print(f"  Baseline: {baseline_equity['max_drawdown_pct']:.1f}%")
    print(f"  95% CI: [{sampling_results['max_drawdown_pct'].quantile(0.025):.1f}%, {sampling_results['max_drawdown_pct'].quantile(0.975):.1f}%]")
    print(f"  Worst 5%: {sampling_results['max_drawdown_pct'].quantile(0.05):.1f}%")

    # Risk Metrics
    print("\n" + "=" * 80)
    print("RISK ASSESSMENT")
    print("=" * 80)

    # Probability of various outcomes
    prob_positive = (sampling_results['total_pnl'] > 0).sum() / len(sampling_results) * 100
    prob_double = (sampling_results['total_pnl'] > config['initial_capital']).sum() / len(sampling_results) * 100
    prob_loss_10 = (sampling_results['total_pnl'] < -config['initial_capital'] * 0.1).sum() / len(sampling_results) * 100
    prob_loss_20 = (sampling_results['total_pnl'] < -config['initial_capital'] * 0.2).sum() / len(sampling_results) * 100

    print(f"\nProbability of Outcomes (based on 1000 simulations):")
    print(f"  Positive P&L: {prob_positive:.1f}%")
    print(f"  Doubling capital: {prob_double:.1f}%")
    print(f"  Losing >10%: {prob_loss_10:.1f}%")
    print(f"  Losing >20%: {prob_loss_20:.1f}%")

    # Sharpe-like metric
    annual_pnl_samples = sampling_results['total_pnl'] / years
    sharpe_approx = annual_pnl_samples.mean() / annual_pnl_samples.std()

    print(f"\nRisk-Adjusted Return:")
    print(f"  Mean Annual P&L: ${annual_pnl_samples.mean():,.0f}")
    print(f"  Std Dev: ${annual_pnl_samples.std():,.0f}")
    print(f"  Sharpe-like ratio: {sharpe_approx:.2f}")

    # Expected Value
    print(f"\nExpected Value:")
    print(f"  Mean total return: {sampling_results['total_pnl'].mean() / config['initial_capital'] * 100:.1f}%")
    print(f"  Median total return: {sampling_results['total_pnl'].median() / config['initial_capital'] * 100:.1f}%")

    # Worst/Best Case Scenarios
    worst_case = sampling_results.nsmallest(10, 'total_pnl')
    best_case = sampling_results.nlargest(10, 'total_pnl')

    print(f"\nWorst 10 Scenarios:")
    print(f"  Avg P&L: ${worst_case['total_pnl'].mean():,.0f}")
    print(f"  Avg WR: {worst_case['win_rate'].mean():.1f}%")
    print(f"  Avg DD: {worst_case['max_drawdown_pct'].mean():.1f}%")

    print(f"\nBest 10 Scenarios:")
    print(f"  Avg P&L: ${best_case['total_pnl'].mean():,.0f}")
    print(f"  Avg WR: {best_case['win_rate'].mean():.1f}%")
    print(f"  Avg DD: {best_case['max_drawdown_pct'].mean():.1f}%")

    # Final Assessment
    print("\n" + "=" * 80)
    print("ROBUSTNESS VERDICT")
    print("=" * 80)

    # Check criteria
    positive_rate_good = prob_positive > 90
    loss_risk_low = prob_loss_20 < 5
    wr_stable = sampling_results['win_rate'].std() < 5
    pnl_ci_reasonable = (sampling_results['total_pnl'].quantile(0.025) / baseline_pnl) > 0.3

    print(f"\nRobustness Checks:")
    print(f"  Positive P&L >90%: {'✅' if positive_rate_good else '❌'} ({prob_positive:.1f}%)")
    print(f"  Risk of ruin <5%: {'✅' if loss_risk_low else '❌'} ({prob_loss_20:.1f}%)")
    print(f"  Win rate stable: {'✅' if wr_stable else '❌'} (σ={sampling_results['win_rate'].std():.1f}%)")
    print(f"  95% CI reasonable: {'✅' if pnl_ci_reasonable else '❌'} (lower bound {sampling_results['total_pnl'].quantile(0.025)/baseline_pnl*100:.0f}% of baseline)")

    checks_passed = sum([positive_rate_good, loss_risk_low, wr_stable, pnl_ci_reasonable])

    print(f"\nOverall Assessment:")
    if checks_passed >= 3:
        print("  ✅ ROBUST - Strategy shows good statistical reliability")
        print("  ✅ Results are trustworthy across different trade samples")
    elif checks_passed >= 2:
        print("  ⚠️ MODERATE - Strategy shows some variability")
        print("  ⚠️ Use conservative expectations")
    else:
        print("  ❌ HIGH VARIANCE - Results show significant variability")
        print("  ❌ Proceed with caution")

    print(f"\nRecommended Conservative Estimates:")
    print(f"  Annual P&L: ${annual_pnl_samples.quantile(0.25):,.0f} (25th percentile)")
    print(f"  Win Rate: {sampling_results['win_rate'].quantile(0.25):.1f}% (25th percentile)")
    print(f"  Max Drawdown: {sampling_results['max_drawdown_pct'].quantile(0.75):.1f}% (75th percentile - worse than typical)")

    print("\n" + "=" * 80)
    print("✅ Monte Carlo simulation complete")
    print("=" * 80)
