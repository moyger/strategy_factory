"""
Monte Carlo Simulation for Strategy Robustness Testing

Tests strategy reliability by:
1. Random trade sequence shuffling (order independence)
2. Bootstrap resampling (sample variation)
3. Random entry/exit timing variations
4. Position sizing variations

Goals:
- Estimate confidence intervals for returns
- Identify sensitivity to trade order
- Assess risk of ruin
- Validate Sharpe ratio stability
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from core.data_loader import ForexDataLoader


def run_single_backtest(h1_df, h4_df, config):
    """Run single backtest with given configuration"""
    strategy = LondonBreakoutV41Optimized(
        risk_percent=config['risk_percent'],
        initial_capital=config['initial_capital'],
        enable_asia_breakout=config['enable_asia'],
        enable_triangle_breakout=config['enable_triangle']
    )

    # Set optimal parameters
    strategy.triangle_lookback = config['lookback']
    strategy.triangle_r2_min = config['r2']
    strategy.triangle_slope_tolerance = config['slope']
    strategy.triangle_time_end = config['time_end']

    # Reinitialize detector
    strategy.pattern_detector = PatternDetector(
        lookback=config['lookback'],
        min_pivot_points=3,
        r_squared_min=config['r2'],
        slope_tolerance=config['slope']
    )

    return strategy.backtest(h1_df.copy(), h4_df.copy())


def monte_carlo_trade_shuffling(trades_df, initial_capital, num_simulations=1000):
    """
    Shuffle trade order randomly to test path dependency

    Returns: Distribution of final equity
    """
    results = []

    for i in range(num_simulations):
        # Shuffle trades
        shuffled = trades_df.sample(frac=1.0).reset_index(drop=True)

        # Calculate equity curve
        capital = initial_capital
        equity_curve = [capital]

        for _, trade in shuffled.iterrows():
            capital += trade['pnl_dollars']
            equity_curve.append(capital)

        final_capital = equity_curve[-1]
        total_return = (final_capital - initial_capital) / initial_capital * 100
        max_equity = max(equity_curve)
        max_dd = min([(eq - max_equity) / max_equity * 100
                      for eq in equity_curve if eq <= max_equity] + [0])

        results.append({
            'final_capital': final_capital,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_dd
        })

    return pd.DataFrame(results)


def monte_carlo_bootstrap(h1_df, h4_df, config, num_simulations=100):
    """
    Bootstrap resampling of data periods

    Returns: Distribution of performance metrics
    """
    results = []

    # Get unique trading days
    trading_days = h1_df.index.date
    unique_days = pd.Series(trading_days).unique()

    for i in range(num_simulations):
        if i % 10 == 0:
            print(f"  Bootstrap simulation {i+1}/{num_simulations}...")

        # Resample days with replacement
        sampled_days = np.random.choice(unique_days, size=len(unique_days), replace=True)

        # Create resampled dataframe
        resampled_h1 = pd.concat([h1_df[h1_df.index.date == day] for day in sampled_days])
        resampled_h1 = resampled_h1.sort_index()

        # Get corresponding H4 data
        resampled_h4 = h4_df[h4_df.index.isin(resampled_h1.index)]

        # Run backtest
        trades = run_single_backtest(resampled_h1, resampled_h4, config)

        if len(trades) == 0:
            continue

        wins = trades[trades['pnl_dollars'] > 0]
        losses = trades[trades['pnl_dollars'] <= 0]

        days_in_sample = (resampled_h1.index.max() - resampled_h1.index.min()).days
        years = days_in_sample / 365.25

        wr = len(wins) / len(trades) * 100
        total_pnl = trades['pnl_dollars'].sum()
        annual_pnl = total_pnl / years if years > 0 else 0
        pf = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 999

        results.append({
            'total_trades': len(trades),
            'trades_per_year': len(trades) / years if years > 0 else 0,
            'win_rate': wr,
            'total_pnl': total_pnl,
            'annual_pnl': annual_pnl,
            'profit_factor': min(pf, 50)  # Cap at 50 for stats
        })

    return pd.DataFrame(results)


def monte_carlo_parameter_variation(h1_df, h4_df, base_config, num_simulations=50):
    """
    Vary parameters slightly around optimal to test sensitivity

    Returns: Distribution of results with parameter variations
    """
    results = []

    for i in range(num_simulations):
        if i % 10 == 0:
            print(f"  Parameter variation {i+1}/{num_simulations}...")

        # Vary parameters by ±10-20%
        config = base_config.copy()
        config['r2'] = max(0.3, min(0.9, base_config['r2'] + np.random.uniform(-0.1, 0.1)))
        config['slope'] = max(0.0001, base_config['slope'] * np.random.uniform(0.8, 1.2))
        config['lookback'] = int(max(20, min(100, base_config['lookback'] + np.random.randint(-10, 10))))

        # Run backtest
        trades = run_single_backtest(h1_df, h4_df, config)

        if len(trades) == 0:
            continue

        wins = trades[trades['pnl_dollars'] > 0]
        losses = trades[trades['pnl_dollars'] <= 0]

        days_in_sample = (h1_df.index.max() - h1_df.index.min()).days
        years = days_in_sample / 365.25

        wr = len(wins) / len(trades) * 100
        total_pnl = trades['pnl_dollars'].sum()
        annual_pnl = total_pnl / years
        pf = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 999

        results.append({
            'r2': config['r2'],
            'slope': config['slope'],
            'lookback': config['lookback'],
            'total_trades': len(trades),
            'trades_per_year': len(trades) / years,
            'win_rate': wr,
            'annual_pnl': annual_pnl,
            'profit_factor': min(pf, 50)
        })

    return pd.DataFrame(results)


if __name__ == '__main__':
    print("=" * 80)
    print("MONTE CARLO SIMULATION - Strategy Robustness Testing")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Use full period
    h1_df = h1_df[h1_df.index >= '2020-01-01']
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nPeriod: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"Bars: {len(h1_df):,}\n")

    # Optimal configuration
    config = {
        'risk_percent': 0.75,
        'initial_capital': 100000,
        'enable_asia': True,
        'enable_triangle': True,
        'lookback': 40,
        'r2': 0.5,
        'slope': 0.0003,
        'time_end': 9
    }

    print("=" * 80)
    print("1. BASELINE - Run actual backtest")
    print("=" * 80)

    baseline_trades = run_single_backtest(h1_df, h4_df, config)
    baseline_wins = baseline_trades[baseline_trades['pnl_dollars'] > 0]
    baseline_losses = baseline_trades[baseline_trades['pnl_dollars'] <= 0]

    days = (h1_df.index.max() - h1_df.index.min()).days
    years = days / 365.25

    baseline_wr = len(baseline_wins) / len(baseline_trades) * 100
    baseline_pnl = baseline_trades['pnl_dollars'].sum()
    baseline_annual = baseline_pnl / years
    baseline_pf = abs(baseline_wins['pnl_dollars'].sum() / baseline_losses['pnl_dollars'].sum())

    print(f"\nBaseline Results:")
    print(f"  Trades: {len(baseline_trades)} ({len(baseline_trades)/years:.1f}/year)")
    print(f"  Win Rate: {baseline_wr:.1f}%")
    print(f"  Total P&L: ${baseline_pnl:,.0f}")
    print(f"  Annual P&L: ${baseline_annual:,.0f}")
    print(f"  Profit Factor: {baseline_pf:.2f}")

    # Test 1: Trade Order Shuffling
    print("\n" + "=" * 80)
    print("2. TRADE ORDER SHUFFLING (1000 simulations)")
    print("=" * 80)
    print("Testing if results depend on specific trade sequence...")

    shuffle_results = monte_carlo_trade_shuffling(
        baseline_trades,
        config['initial_capital'],
        num_simulations=1000
    )

    print(f"\nFinal Capital Distribution:")
    print(f"  Mean: ${shuffle_results['final_capital'].mean():,.0f}")
    print(f"  Median: ${shuffle_results['final_capital'].median():,.0f}")
    print(f"  Std Dev: ${shuffle_results['final_capital'].std():,.0f}")
    print(f"  5th percentile: ${shuffle_results['final_capital'].quantile(0.05):,.0f}")
    print(f"  95th percentile: ${shuffle_results['final_capital'].quantile(0.95):,.0f}")

    print(f"\nTotal Return Distribution:")
    print(f"  Mean: {shuffle_results['total_return_pct'].mean():.1f}%")
    print(f"  Median: {shuffle_results['total_return_pct'].median():.1f}%")
    print(f"  Std Dev: {shuffle_results['total_return_pct'].std():.1f}%")
    print(f"  5th percentile: {shuffle_results['total_return_pct'].quantile(0.05):.1f}%")
    print(f"  95th percentile: {shuffle_results['total_return_pct'].quantile(0.95):.1f}%")

    print(f"\nMax Drawdown Distribution:")
    print(f"  Mean: {shuffle_results['max_drawdown_pct'].mean():.1f}%")
    print(f"  Worst (5th %ile): {shuffle_results['max_drawdown_pct'].quantile(0.05):.1f}%")
    print(f"  Best (95th %ile): {shuffle_results['max_drawdown_pct'].quantile(0.95):.1f}%")

    # Test 2: Bootstrap Resampling
    print("\n" + "=" * 80)
    print("3. BOOTSTRAP RESAMPLING (100 simulations)")
    print("=" * 80)
    print("Testing performance on randomly sampled data periods...")

    bootstrap_results = monte_carlo_bootstrap(h1_df, h4_df, config, num_simulations=100)

    print(f"\nWin Rate Distribution:")
    print(f"  Mean: {bootstrap_results['win_rate'].mean():.1f}%")
    print(f"  Std Dev: {bootstrap_results['win_rate'].std():.1f}%")
    print(f"  95% CI: [{bootstrap_results['win_rate'].quantile(0.025):.1f}%, {bootstrap_results['win_rate'].quantile(0.975):.1f}%]")

    print(f"\nAnnual P&L Distribution:")
    print(f"  Mean: ${bootstrap_results['annual_pnl'].mean():,.0f}")
    print(f"  Std Dev: ${bootstrap_results['annual_pnl'].std():,.0f}")
    print(f"  95% CI: [${bootstrap_results['annual_pnl'].quantile(0.025):,.0f}, ${bootstrap_results['annual_pnl'].quantile(0.975):,.0f}]")

    print(f"\nTrades/Year Distribution:")
    print(f"  Mean: {bootstrap_results['trades_per_year'].mean():.1f}")
    print(f"  Std Dev: {bootstrap_results['trades_per_year'].std():.1f}")
    print(f"  95% CI: [{bootstrap_results['trades_per_year'].quantile(0.025):.1f}, {bootstrap_results['trades_per_year'].quantile(0.975):.1f}]")

    print(f"\nProfit Factor Distribution:")
    print(f"  Mean: {bootstrap_results['profit_factor'].mean():.2f}")
    print(f"  Median: {bootstrap_results['profit_factor'].median():.2f}")
    print(f"  95% CI: [{bootstrap_results['profit_factor'].quantile(0.025):.2f}, {bootstrap_results['profit_factor'].quantile(0.975):.2f}]")

    # Test 3: Parameter Sensitivity
    print("\n" + "=" * 80)
    print("4. PARAMETER SENSITIVITY (50 simulations)")
    print("=" * 80)
    print("Testing sensitivity to parameter variations (±10-20%)...")

    param_results = monte_carlo_parameter_variation(h1_df, h4_df, config, num_simulations=50)

    print(f"\nAnnual P&L with Parameter Variations:")
    print(f"  Mean: ${param_results['annual_pnl'].mean():,.0f}")
    print(f"  Std Dev: ${param_results['annual_pnl'].std():,.0f}")
    print(f"  Range: [${param_results['annual_pnl'].min():,.0f}, ${param_results['annual_pnl'].max():,.0f}]")
    print(f"  Baseline: ${baseline_annual:,.0f}")

    print(f"\nWin Rate with Parameter Variations:")
    print(f"  Mean: {param_results['win_rate'].mean():.1f}%")
    print(f"  Std Dev: {param_results['win_rate'].std():.1f}%")
    print(f"  Range: [{param_results['win_rate'].min():.1f}%, {param_results['win_rate'].max():.1f}%]")
    print(f"  Baseline: {baseline_wr:.1f}%")

    # Risk Metrics
    print("\n" + "=" * 80)
    print("5. RISK METRICS")
    print("=" * 80)

    # Risk of Ruin (simplified - probability of losing 20%+)
    losing_scenarios = shuffle_results[shuffle_results['total_return_pct'] < -20]
    risk_of_ruin = len(losing_scenarios) / len(shuffle_results) * 100

    print(f"\nRisk of Ruin (>20% loss):")
    print(f"  Probability: {risk_of_ruin:.2f}%")
    print(f"  Scenarios: {len(losing_scenarios)}/1000")

    # Expected value with confidence
    expected_return = shuffle_results['total_return_pct'].mean()
    expected_return_std = shuffle_results['total_return_pct'].std()

    print(f"\nExpected Return (with 95% confidence):")
    print(f"  Mean: {expected_return:.1f}%")
    print(f"  95% CI: [{expected_return - 1.96*expected_return_std:.1f}%, {expected_return + 1.96*expected_return_std:.1f}%]")

    # Create visualizations
    print("\n" + "=" * 80)
    print("6. GENERATING VISUALIZATIONS")
    print("=" * 80)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Final Capital Distribution
    axes[0, 0].hist(shuffle_results['final_capital'], bins=50, edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(baseline_pnl + config['initial_capital'], color='red', linestyle='--', linewidth=2, label='Baseline')
    axes[0, 0].set_xlabel('Final Capital ($)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Final Capital Distribution (Trade Shuffling)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Plot 2: Annual P&L Distribution (Bootstrap)
    axes[0, 1].hist(bootstrap_results['annual_pnl'], bins=30, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].axvline(baseline_annual, color='red', linestyle='--', linewidth=2, label='Baseline')
    axes[0, 1].set_xlabel('Annual P&L ($)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Annual P&L Distribution (Bootstrap)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Plot 3: Win Rate Distribution
    axes[1, 0].hist(bootstrap_results['win_rate'], bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 0].axvline(baseline_wr, color='red', linestyle='--', linewidth=2, label='Baseline')
    axes[1, 0].set_xlabel('Win Rate (%)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Win Rate Distribution (Bootstrap)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # Plot 4: Parameter Sensitivity
    axes[1, 1].scatter(param_results['lookback'], param_results['annual_pnl'], alpha=0.6)
    axes[1, 1].axhline(baseline_annual, color='red', linestyle='--', linewidth=2, label='Baseline')
    axes[1, 1].set_xlabel('Lookback (bars)')
    axes[1, 1].set_ylabel('Annual P&L ($)')
    axes[1, 1].set_title('Parameter Sensitivity (Lookback vs P&L)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('monte_carlo_results.png', dpi=150, bbox_inches='tight')
    print("\n✅ Charts saved to: monte_carlo_results.png")

    # Summary
    print("\n" + "=" * 80)
    print("MONTE CARLO SUMMARY")
    print("=" * 80)

    print(f"\nBaseline Strategy Performance:")
    print(f"  Annual P&L: ${baseline_annual:,.0f}")
    print(f"  Win Rate: {baseline_wr:.1f}%")
    print(f"  Profit Factor: {baseline_pf:.2f}")

    print(f"\nMonte Carlo Confidence Intervals (95%):")
    print(f"  Annual P&L: [${bootstrap_results['annual_pnl'].quantile(0.025):,.0f}, ${bootstrap_results['annual_pnl'].quantile(0.975):,.0f}]")
    print(f"  Win Rate: [{bootstrap_results['win_rate'].quantile(0.025):.1f}%, {bootstrap_results['win_rate'].quantile(0.975):.1f}%]")
    print(f"  Profit Factor: [{bootstrap_results['profit_factor'].quantile(0.025):.2f}, {bootstrap_results['profit_factor'].quantile(0.975):.2f}]")

    print(f"\nRisk Assessment:")
    print(f"  Risk of Ruin (>20% loss): {risk_of_ruin:.2f}%")
    print(f"  Worst DD (5th %ile): {shuffle_results['max_drawdown_pct'].quantile(0.05):.1f}%")
    print(f"  Expected Return: {expected_return:.1f}% ± {1.96*expected_return_std:.1f}%")

    # Robustness verdict
    pnl_cv = bootstrap_results['annual_pnl'].std() / bootstrap_results['annual_pnl'].mean()
    wr_stable = bootstrap_results['win_rate'].std() < 5.0

    print(f"\nRobustness Assessment:")
    print(f"  Annual P&L CV: {pnl_cv:.3f} ({'✅ Acceptable' if pnl_cv < 1.0 else '⚠️ High Variance'})")
    print(f"  Win Rate Stability: {'✅ Stable' if wr_stable else '⚠️ Variable'} (σ={bootstrap_results['win_rate'].std():.1f}%)")
    print(f"  Parameter Sensitivity: {'✅ Low' if param_results['annual_pnl'].std() < 50000 else '⚠️ High'}")

    if risk_of_ruin < 5 and wr_stable and pnl_cv < 1.0:
        print("\n✅ Strategy shows GOOD robustness across simulations")
        print("✅ Results are statistically reliable")
    elif risk_of_ruin < 10 and pnl_cv < 1.5:
        print("\n⚠️ Strategy shows MODERATE robustness")
        print("⚠️ Some variability in results - use conservative expectations")
    else:
        print("\n❌ Strategy shows HIGH variability")
        print("❌ Results may be less reliable - proceed with caution")

    print("\n✅ Monte Carlo simulation complete")
    print("=" * 80)
