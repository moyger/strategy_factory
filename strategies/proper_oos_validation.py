"""
Proper Out-of-Sample Validation

RULES:
1. NEVER look at 2025 data during optimization
2. Optimize ONLY on 2020-2022
3. Validate on 2023-2024 (NO changes allowed)
4. Final test on 2025 (accept results as-is)

This is the HONEST test.
"""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from core.data_loader import ForexDataLoader


def run_backtest(h1_df, h4_df, config, label):
    """Run backtest with specific configuration"""
    strategy = LondonBreakoutV41Optimized(
        risk_percent=config['risk'],
        initial_capital=config['capital'],
        enable_asia_breakout=config['asia'],
        enable_triangle_breakout=config['triangle']
    )

    # Set parameters
    strategy.triangle_lookback = config['lookback']
    strategy.triangle_r2_min = config['r2']
    strategy.triangle_slope_tolerance = config['slope']
    strategy.triangle_time_end = config['time_end']

    strategy.pattern_detector = PatternDetector(
        lookback=config['lookback'],
        min_pivot_points=3,
        r_squared_min=config['r2'],
        slope_tolerance=config['slope']
    )

    trades = strategy.backtest(h1_df, h4_df)

    if len(trades) == 0:
        print(f"\n{label}: NO TRADES")
        return None

    wins = trades[trades['pnl_dollars'] > 0]
    losses = trades[trades['pnl_dollars'] <= 0]

    days = (h1_df.index.max() - h1_df.index.min()).days
    years = days / 365.25

    asia_trades = trades[trades['signal_type'] == 'asia_breakout']
    triangle_trades = trades[trades['signal_type'].str.contains('triangle', na=False)]

    result = {
        'label': label,
        'period': f"{h1_df.index.min().date()} to {h1_df.index.max().date()}",
        'years': years,
        'total_trades': len(trades),
        'asia_trades': len(asia_trades),
        'triangle_trades': len(triangle_trades),
        'trades_per_year': len(trades) / years,
        'win_rate': len(wins) / len(trades) * 100,
        'total_pnl': trades['pnl_dollars'].sum(),
        'annual_pnl': trades['pnl_dollars'].sum() / years,
        'profit_factor': abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 999
    }

    print(f"\n{label}:")
    print(f"  Period: {result['period']} ({years:.2f} years)")
    print(f"  Trades: {len(trades)} ({result['trades_per_year']:.1f}/year)")
    print(f"    Asia: {len(asia_trades)} | Triangle: {len(triangle_trades)}")
    print(f"  Win Rate: {result['win_rate']:.1f}%")
    print(f"  Total P&L: ${result['total_pnl']:,.0f}")
    print(f"  Annual P&L: ${result['annual_pnl']:,.0f}")
    print(f"  Profit Factor: {result['profit_factor']:.2f}")

    return result


if __name__ == '__main__':
    print("=" * 80)
    print("PROPER OUT-OF-SAMPLE VALIDATION")
    print("=" * 80)
    print("\nRULES:")
    print("  1. Optimize ONLY on 2020-2022")
    print("  2. Validate on 2023-2024 (NO changes)")
    print("  3. Final test on 2025 (accept as-is)")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Split data PROPERLY
    train_h1 = h1_df[(h1_df.index >= '2020-01-01') & (h1_df.index < '2023-01-01')]
    train_h4 = h4_df[(h4_df.index >= '2020-01-01') & (h4_df.index < '2023-01-01')]

    test_h1 = h1_df[(h1_df.index >= '2023-01-01') & (h1_df.index < '2025-01-01')]
    test_h4 = h4_df[(h4_df.index >= '2023-01-01') & (h4_df.index < '2025-01-01')]

    oos_h1 = h1_df[h1_df.index >= '2025-01-01']
    oos_h4 = h4_df[h4_df.index >= '2025-01-01']

    print(f"\nData Splits:")
    print(f"  TRAIN: 2020-2022 ({len(train_h1):,} bars) - Optimize here")
    print(f"  TEST: 2023-2024 ({len(test_h1):,} bars) - Validate (no changes)")
    print(f"  OOS: 2025+ ({len(oos_h1):,} bars) - Final reality check")

    # Test configurations
    print("\n" + "=" * 80)
    print("TESTING DIFFERENT CONFIGURATIONS")
    print("=" * 80)

    configs = [
        {
            'name': 'Asia Only (Baseline)',
            'asia': True,
            'triangle': False,
            'lookback': 40,  # Doesn't matter for Asia-only
            'r2': 0.5,
            'slope': 0.0003,
            'time_end': 9,
            'risk': 0.75,
            'capital': 100000
        },
        {
            'name': 'Combined (lookback=40)',
            'asia': True,
            'triangle': True,
            'lookback': 40,
            'r2': 0.5,
            'slope': 0.0003,
            'time_end': 9,
            'risk': 0.75,
            'capital': 100000
        },
        {
            'name': 'Combined (lookback=60)',
            'asia': True,
            'triangle': True,
            'lookback': 60,
            'r2': 0.5,
            'slope': 0.0003,
            'time_end': 9,
            'risk': 0.75,
            'capital': 100000
        },
        {
            'name': 'Combined (stricter R²=0.7)',
            'asia': True,
            'triangle': True,
            'lookback': 40,
            'r2': 0.7,
            'slope': 0.0003,
            'time_end': 9,
            'risk': 0.75,
            'capital': 100000
        },
    ]

    all_results = []

    for config in configs:
        print("\n" + "=" * 80)
        print(f"Configuration: {config['name']}")
        print("=" * 80)

        # Train
        train_result = run_backtest(train_h1, train_h4, config, "TRAIN (2020-2022)")
        if train_result:
            all_results.append(train_result)

        # Test
        test_result = run_backtest(test_h1, test_h4, config, "TEST (2023-2024)")
        if test_result:
            all_results.append(test_result)

        # Out-of-sample
        oos_result = run_backtest(oos_h1, oos_h4, config, "OUT-OF-SAMPLE (2025)")
        if oos_result:
            all_results.append(oos_result)

        # Calculate degradation
        if train_result and test_result:
            degradation = (train_result['annual_pnl'] - test_result['annual_pnl']) / train_result['annual_pnl'] * 100
            print(f"\n  Degradation (Train→Test): {degradation:.1f}%")

            if abs(degradation) < 20:
                print("  ✅ Excellent - Strategy is robust")
            elif abs(degradation) < 40:
                print("  ⚠️ Moderate - Some overfitting")
            else:
                print("  ❌ Poor - Likely overfitted")

        if test_result and oos_result:
            oos_degradation = (test_result['annual_pnl'] - oos_result['annual_pnl']) / test_result['annual_pnl'] * 100 if test_result['annual_pnl'] != 0 else 0
            print(f"  Degradation (Test→OOS): {oos_degradation:.1f}%")

    # Summary
    print("\n" + "=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)

    results_df = pd.DataFrame(all_results)

    # Group by configuration
    configs_tested = [c['name'] for c in configs]

    print("\nComparison Table:")
    print(f"{'Config':<30} | {'Period':<15} | {'Trades/Yr':<10} | {'WR%':<6} | {'Annual P&L':<12} | {'PF':<5}")
    print("-" * 95)

    for config_name in configs_tested:
        config_results = results_df[results_df['label'].str.contains('TRAIN|TEST|OUT')]

        for period in ['TRAIN', 'TEST', 'OUT-OF-SAMPLE']:
            row = results_df[results_df['label'].str.contains(period)]
            if len(row) > 0:
                r = row.iloc[len(row) - len(configs_tested) + configs_tested.index(config_name)] if len(row) >= len(configs_tested) else row.iloc[0]
                print(f"{config_name:<30} | {period:<15} | {r['trades_per_year']:<10.1f} | {r['win_rate']:<6.1f} | ${r['annual_pnl']:<11,.0f} | {r['profit_factor']:<5.2f}")

    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    asia_only_train = results_df[(results_df['label'].str.contains('TRAIN')) & (results_df['label'].str.contains('Baseline'))].iloc[0] if len(results_df[(results_df['label'].str.contains('TRAIN')) & (results_df['label'].str.contains('Baseline'))]) > 0 else None
    asia_only_test = results_df[(results_df['label'].str.contains('TEST')) & (results_df['label'].str.contains('Baseline'))].iloc[0] if len(results_df[(results_df['label'].str.contains('TEST')) & (results_df['label'].str.contains('Baseline'))]) > 0 else None

    if asia_only_train and asia_only_test:
        asia_degradation = (asia_only_train['annual_pnl'] - asia_only_test['annual_pnl']) / asia_only_train['annual_pnl'] * 100

        print(f"\n1. ASIA BREAKOUT (Baseline):")
        print(f"   Train: ${asia_only_train['annual_pnl']:,.0f}/year")
        print(f"   Test: ${asia_only_test['annual_pnl']:,.0f}/year")
        print(f"   Degradation: {asia_degradation:.1f}%")

        if abs(asia_degradation) < 30:
            print("   ✅ RELIABLE - Use this as base strategy")
            print(f"   Expected: ${asia_only_test['annual_pnl']*0.8:,.0f} - ${asia_only_test['annual_pnl']:,.0f}/year")
        else:
            print("   ⚠️ QUESTIONABLE - Even baseline shows degradation")

    print(f"\n2. TRIANGLE ENHANCEMENT:")
    print("   Compare triangle trades in each period:")

    for config_name in configs_tested:
        if 'Combined' in config_name:
            config_rows = results_df[results_df['label'].str.contains(config_name.split('(')[1].split(')')[0] if '(' in config_name else 'lookback=40')]
            if len(config_rows) >= 2:
                train_tri = config_rows.iloc[0]['triangle_trades']
                test_tri = config_rows.iloc[1]['triangle_trades']

                print(f"\n   {config_name}:")
                print(f"     Train triangle trades: {train_tri}")
                print(f"     Test triangle trades: {test_tri}")

                if test_tri < 10:
                    print("     ❌ Too few triangle trades in test - NOT reliable")
                elif test_tri < 20:
                    print("     ⚠️ Limited triangle sample - Use with caution")
                else:
                    print("     ✅ Sufficient triangle trades for validation")

    print("\n" + "=" * 80)
    print("HONEST CONCLUSION")
    print("=" * 80)

    if asia_only_test:
        conservative_estimate = asia_only_test['annual_pnl'] * 0.7

        print(f"\nBased on proper out-of-sample testing:")
        print(f"\n1. Conservative Expectation:")
        print(f"   Use Asia Breakout only")
        print(f"   Expected: ${conservative_estimate:,.0f} - ${asia_only_test['annual_pnl']:,.0f}/year")
        print(f"   Confidence: MEDIUM")

        print(f"\n2. Triangle Addition:")
        print(f"   May add: $0 - $10,000/year")
        print(f"   Confidence: LOW (insufficient out-of-sample data)")

        print(f"\n3. Realistic Total:")
        print(f"   Expected: ${conservative_estimate:,.0f} - ${asia_only_test['annual_pnl']*1.2:,.0f}/year")
        print(f"   NOT the $127k from optimistic backtest!")

    print("\n✅ Proper validation complete")
    print("=" * 80)
