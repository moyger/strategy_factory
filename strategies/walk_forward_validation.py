"""
Walk-Forward Validation

Tests robustness of optimized parameters across different time periods:
- Train: 2020-2022 (optimize parameters)
- Test: 2023-2024 (validate on unseen data)
- Final: 2025 (out-of-sample validation)

This ensures we're not overfitting to specific market conditions.
"""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from core.data_loader import ForexDataLoader


def run_backtest(h1_df, h4_df, r2, slope, lookback, time_end, label):
    """Run backtest with specific parameters"""
    strategy = LondonBreakoutV41Optimized(
        risk_percent=0.75,
        initial_capital=100000,
        enable_asia_breakout=True,  # Combined strategy
        enable_triangle_breakout=True
    )

    # Override triangle parameters
    strategy.triangle_lookback = lookback
    strategy.triangle_r2_min = r2
    strategy.triangle_slope_tolerance = slope
    strategy.triangle_time_end = time_end

    # Reinitialize detector
    strategy.pattern_detector = PatternDetector(
        lookback=lookback,
        min_pivot_points=3,
        r_squared_min=r2,
        slope_tolerance=slope
    )

    # Run backtest
    trades = strategy.backtest(h1_df.copy(), h4_df.copy())

    if len(trades) == 0:
        print(f"  ❌ {label}: No trades\n")
        return None

    wins = trades[trades['pnl_dollars'] > 0]
    losses = trades[trades['pnl_dollars'] <= 0]

    days = (h1_df.index.max() - h1_df.index.min()).days
    years = days / 365.25

    wr = len(wins) / len(trades) * 100
    total_pnl = trades['pnl_dollars'].sum()
    annual_pnl = total_pnl / years
    pf = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 999

    # Signal breakdown
    asia_trades = trades[trades['signal_type'] == 'asia_breakout']
    triangle_trades = trades[trades['signal_type'].str.contains('triangle', na=False)]

    print(f"\n{label}:")
    print(f"  Period: {h1_df.index.min().date()} to {h1_df.index.max().date()} ({years:.2f} years)")
    print(f"  Total trades: {len(trades)} ({len(trades)/years:.1f}/yr)")
    print(f"    Asia: {len(asia_trades)} | Triangle: {len(triangle_trades)}")
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Total P&L: ${total_pnl:,.0f}")
    print(f"  Annual P&L: ${annual_pnl:,.0f}")
    print(f"  Profit factor: {pf:.2f}")

    return {
        'label': label,
        'start': h1_df.index.min(),
        'end': h1_df.index.max(),
        'years': years,
        'total_trades': len(trades),
        'trades_per_year': len(trades) / years,
        'asia_trades': len(asia_trades),
        'triangle_trades': len(triangle_trades),
        'win_rate': wr,
        'total_pnl': total_pnl,
        'annual_pnl': annual_pnl,
        'profit_factor': pf
    }


if __name__ == '__main__':
    print("=" * 80)
    print("WALK-FORWARD VALIDATION")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Split into periods
    train_h1 = h1_df[(h1_df.index >= '2020-01-01') & (h1_df.index < '2023-01-01')]
    train_h4 = h4_df[(h4_df.index >= '2020-01-01') & (h4_df.index < '2023-01-01')]

    test_h1 = h1_df[(h1_df.index >= '2023-01-01') & (h1_df.index < '2025-01-01')]
    test_h4 = h4_df[(h4_df.index >= '2023-01-01') & (h4_df.index < '2025-01-01')]

    validate_h1 = h1_df[h1_df.index >= '2025-01-01']
    validate_h4 = h4_df[h4_df.index >= '2025-01-01']

    full_h1 = h1_df[h1_df.index >= '2020-01-01']
    full_h4 = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nData splits:")
    print(f"  Train: 2020-2022 ({len(train_h1):,} bars)")
    print(f"  Test: 2023-2024 ({len(test_h1):,} bars)")
    print(f"  Validate: 2025+ ({len(validate_h1):,} bars)")
    print(f"  Full: 2020-2025 ({len(full_h1):,} bars)\n")

    # Optimal parameters from optimization
    optimal = {
        'r2': 0.5,
        'slope': 0.0003,
        'lookback': 40,
        'time_end': 9
    }

    print("=" * 80)
    print("OPTIMAL PARAMETERS (from optimization)")
    print("=" * 80)
    print(f"R² min: {optimal['r2']}")
    print(f"Slope tolerance: {optimal['slope']}")
    print(f"Lookback: {optimal['lookback']}")
    print(f"Time window: 3-{optimal['time_end']} AM")

    print("\n" + "=" * 80)
    print("TESTING ON DIFFERENT PERIODS")
    print("=" * 80)

    results = []

    # Test on train period (should match optimization results)
    result = run_backtest(train_h1, train_h4, optimal['r2'], optimal['slope'],
                         optimal['lookback'], optimal['time_end'], "TRAIN (2020-2022)")
    if result:
        results.append(result)

    # Test on test period (unseen data)
    result = run_backtest(test_h1, test_h4, optimal['r2'], optimal['slope'],
                         optimal['lookback'], optimal['time_end'], "TEST (2023-2024)")
    if result:
        results.append(result)

    # Test on validation period (most recent data)
    result = run_backtest(validate_h1, validate_h4, optimal['r2'], optimal['slope'],
                         optimal['lookback'], optimal['time_end'], "VALIDATE (2025+)")
    if result:
        results.append(result)

    # Full period
    result = run_backtest(full_h1, full_h4, optimal['r2'], optimal['slope'],
                         optimal['lookback'], optimal['time_end'], "FULL (2020-2025)")
    if result:
        results.append(result)

    # Analysis
    print("\n" + "=" * 80)
    print("CONSISTENCY ANALYSIS")
    print("=" * 80)

    results_df = pd.DataFrame(results)

    print(f"\nWin Rate Consistency:")
    print(f"  Mean: {results_df['win_rate'].mean():.1f}%")
    print(f"  Std Dev: {results_df['win_rate'].std():.1f}%")
    print(f"  Range: {results_df['win_rate'].min():.1f}% - {results_df['win_rate'].max():.1f}%")

    print(f"\nAnnual P&L Consistency:")
    print(f"  Mean: ${results_df['annual_pnl'].mean():,.0f}")
    print(f"  Std Dev: ${results_df['annual_pnl'].std():,.0f}")
    print(f"  Range: ${results_df['annual_pnl'].min():,.0f} - ${results_df['annual_pnl'].max():,.0f}")

    print(f"\nTrades/Year Consistency:")
    print(f"  Mean: {results_df['trades_per_year'].mean():.1f}")
    print(f"  Std Dev: {results_df['trades_per_year'].std():.1f}")
    print(f"  Range: {results_df['trades_per_year'].min():.1f} - {results_df['trades_per_year'].max():.1f}")

    print(f"\nProfit Factor Consistency:")
    print(f"  Mean: {results_df['profit_factor'].mean():.2f}")
    print(f"  Std Dev: {results_df['profit_factor'].std():.2f}")
    print(f"  Range: {results_df['profit_factor'].min():.2f} - {results_df['profit_factor'].max():.2f}")

    # Robustness check
    print("\n" + "=" * 80)
    print("ROBUSTNESS ASSESSMENT")
    print("=" * 80)

    wr_cv = results_df['win_rate'].std() / results_df['win_rate'].mean()
    pnl_cv = results_df['annual_pnl'].std() / results_df['annual_pnl'].mean()

    print(f"\nCoefficient of Variation (lower = more stable):")
    print(f"  Win Rate CV: {wr_cv:.3f} ({'✅ Stable' if wr_cv < 0.2 else '⚠️ Variable'})")
    print(f"  Annual P&L CV: {pnl_cv:.3f} ({'✅ Stable' if pnl_cv < 0.5 else '⚠️ Variable'})")

    # Out-of-sample degradation
    if len(results) >= 2:
        train_pnl = results[0]['annual_pnl']
        test_pnl = results[1]['annual_pnl']
        degradation = (train_pnl - test_pnl) / train_pnl * 100

        print(f"\nOut-of-Sample Performance:")
        print(f"  Train (2020-2022): ${train_pnl:,.0f}/year")
        print(f"  Test (2023-2024): ${test_pnl:,.0f}/year")
        print(f"  Degradation: {degradation:.1f}%")

        if abs(degradation) < 20:
            print("  ✅ Performance maintained well (< 20% degradation)")
        elif abs(degradation) < 40:
            print("  ⚠️ Moderate degradation (20-40%)")
        else:
            print("  ❌ Significant degradation (> 40%) - possible overfitting")

    print("\n" + "=" * 80)
    print("FINAL RECOMMENDATION")
    print("=" * 80)

    full_result = results[-1]
    print(f"\nOptimized Parameters:")
    print(f"  R² min: {optimal['r2']}")
    print(f"  Slope tolerance: {optimal['slope']}")
    print(f"  Lookback: {optimal['lookback']} bars")
    print(f"  Time window: 3-{optimal['time_end']} AM")

    print(f"\nExpected Performance (Full Period 2020-2025):")
    print(f"  Total trades: {full_result['total_trades']} ({full_result['trades_per_year']:.1f}/year)")
    print(f"    Asia breakout: {full_result['asia_trades']}")
    print(f"    Triangle: {full_result['triangle_trades']}")
    print(f"  Win rate: {full_result['win_rate']:.1f}%")
    print(f"  Annual P&L: ${full_result['annual_pnl']:,.0f}")
    print(f"  Profit factor: {full_result['profit_factor']:.2f}")

    if wr_cv < 0.2 and abs(degradation) < 30:
        print("\n✅ Strategy shows good robustness across different periods")
        print("✅ Ready for live trading consideration")
    else:
        print("\n⚠️ Strategy shows some period-dependent variability")
        print("⚠️ Consider additional testing or parameter adjustment")

    print("\n✅ Walk-forward validation complete")
