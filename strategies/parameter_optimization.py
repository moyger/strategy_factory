"""
Parameter Grid Search for Triangle Pattern Detection

Tests combinations of:
- R² threshold: 0.4, 0.5, 0.6, 0.7
- Slope tolerance: 0.0002, 0.0003, 0.0005
- Lookback: 40, 60, 80
- Time window end: 7, 9, 11 (hours)

Goal: Find optimal balance between trade frequency and quality
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path
import itertools
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import ForexDataLoader
from core.session_manager import TradingSession
from core.indicators import ema, atr
from strategies.pattern_detector import PatternDetector


def run_triangle_backtest(h1_df, h4_df, r2_min, slope_tol, lookback, time_end):
    """
    Run backtest with specific parameters (triangle-only, no Asia breakout)

    Returns: dict with results
    """
    # Calculate indicators
    h1_test = h1_df.copy()
    h4_test = h4_df.copy()

    h1_test['ema_21'] = ema(h1_test['close'], 21)
    h1_test['ema_50'] = ema(h1_test['close'], 50)
    h1_test['atr'] = atr(h1_test['high'], h1_test['low'], h1_test['close'], 14)
    h1_test['trend'] = 0
    h1_test.loc[h1_test['ema_21'] > h1_test['ema_50'], 'trend'] = 1
    h1_test.loc[h1_test['ema_21'] < h1_test['ema_50'], 'trend'] = -1

    h4_test['ema_21'] = ema(h4_test['close'], 21)
    h4_test['ema_50'] = ema(h4_test['close'], 50)
    h4_test['trend'] = 0
    h4_test.loc[h4_test['ema_21'] > h4_test['ema_50'], 'trend'] = 1
    h4_test.loc[h4_test['ema_21'] < h4_test['ema_50'], 'trend'] = -1

    # Initialize detector with test parameters
    detector = PatternDetector(
        lookback=lookback,
        min_pivot_points=3,
        r_squared_min=r2_min,
        slope_tolerance=slope_tol
    )

    # Find pivots
    h1_test = detector.find_pivot_points(h1_test)

    # Track trades
    trades = []
    traded_patterns = set()
    current_capital = 100000
    position = None
    pip_value = 0.0001
    risk_percent = 0.75

    for idx in h1_test.index:
        # Exit check
        if position is not None:
            row = h1_test.loc[idx]
            sl = position['sl']
            tp = position['tp']

            exit_price = None
            exit_reason = None

            # Check SL/TP
            if position['type'] == 'long':
                if row['low'] <= sl:
                    exit_price = sl
                    exit_reason = 'sl'
                elif row['high'] >= tp:
                    exit_price = tp
                    exit_reason = 'tp'
            else:
                if row['high'] >= sl:
                    exit_price = sl
                    exit_reason = 'sl'
                elif row['low'] <= tp:
                    exit_price = tp
                    exit_reason = 'tp'

            # Time exit
            if idx.hour >= 12 and idx.hour < 13 and exit_price is None:
                exit_price = row['close']
                exit_reason = 'time'

            if exit_price:
                # Calculate P&L
                if position['type'] == 'long':
                    pnl_pips = (exit_price - position['entry']) / pip_value
                else:
                    pnl_pips = (position['entry'] - exit_price) / pip_value

                pnl_dollars = pnl_pips * position['dollars_per_pip']
                pnl_dollars -= (0.0005 * position['lots'] * 100000 + 0.5 * position['dollars_per_pip'])

                current_capital += pnl_dollars

                trades.append({
                    'pnl_dollars': pnl_dollars,
                    'pnl_pips': pnl_pips,
                    'exit_reason': exit_reason,
                    'pattern_type': position['pattern_type']
                })

                position = None

        # Entry check
        if position is None:
            # Time window check
            if not (3 <= idx.hour <= time_end):
                continue

            if not TradingSession.is_in_session(idx, TradingSession.LONDON):
                continue

            current_pos = h1_test.index.get_loc(idx)

            if current_pos < lookback:
                continue

            # Detect patterns
            patterns = detector.detect_all_patterns(h1_test, current_pos)

            if len(patterns) == 0:
                continue

            pattern = patterns[0]

            pattern_id = (pattern['type'], pattern['start_index'], pattern['end_index'])

            if pattern_id in traded_patterns:
                continue

            row = h1_test.loc[idx]
            current_price = row['close']

            # Check breakout
            breakout = detector.check_breakout(pattern, current_price, 0.0015)

            if breakout is None:
                continue

            # Get H4 trend
            h4_bars = h4_test[h4_test.index <= idx]
            h4_trend = h4_bars.iloc[-1]['trend'] if len(h4_bars) > 0 else 0

            resistance = pattern['resistance']['price']
            support = pattern['support']['price']

            # LONG
            if breakout == 'long':
                if pattern['type'] == 'ascending' and h4_trend == -1:
                    continue
                elif pattern['type'] == 'descending' and h4_trend != 1:
                    continue
                elif h4_trend == -1:
                    continue

                entry = resistance * 1.0015
                sl = support * 0.99925
                sl_pips = (entry - sl) / pip_value

                if sl_pips > 50:
                    sl_pips = 50
                    sl = entry - (sl_pips * pip_value)

                tp = entry + (sl_pips * 1.3 * pip_value)

                risk_amount = current_capital * (risk_percent / 100)
                dollars_per_pip = risk_amount / sl_pips
                lots = round(dollars_per_pip / 10, 2)
                lots = max(0.01, lots)

                position = {
                    'type': 'long',
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'lots': lots,
                    'dollars_per_pip': dollars_per_pip,
                    'pattern_type': pattern['type']
                }

                traded_patterns.add(pattern_id)

            # SHORT
            elif breakout == 'short':
                if pattern['type'] == 'descending' and h4_trend == 1:
                    continue
                elif pattern['type'] == 'ascending' and h4_trend != -1:
                    continue
                elif h4_trend == 1:
                    continue

                entry = support * 0.9985
                sl = resistance * 1.00075
                sl_pips = (sl - entry) / pip_value

                if sl_pips > 50:
                    sl_pips = 50
                    sl = entry + (sl_pips * pip_value)

                tp = entry - (sl_pips * 1.3 * pip_value)

                risk_amount = current_capital * (risk_percent / 100)
                dollars_per_pip = risk_amount / sl_pips
                lots = round(dollars_per_pip / 10, 2)
                lots = max(0.01, lots)

                position = {
                    'type': 'short',
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'lots': lots,
                    'dollars_per_pip': dollars_per_pip,
                    'pattern_type': pattern['type']
                }

                traded_patterns.add(pattern_id)

    # Calculate metrics
    if len(trades) == 0:
        return None

    trades_df = pd.DataFrame(trades)
    wins = trades_df[trades_df['pnl_dollars'] > 0]

    days = (h1_test.index.max() - h1_test.index.min()).days
    years = days / 365.25

    return {
        'total_trades': len(trades_df),
        'trades_per_year': len(trades_df) / years,
        'win_rate': len(wins) / len(trades_df) * 100,
        'total_pnl': trades_df['pnl_dollars'].sum(),
        'annual_pnl': trades_df['pnl_dollars'].sum() / years,
        'avg_pnl': trades_df['pnl_dollars'].mean(),
        'profit_factor': abs(wins['pnl_dollars'].sum() / trades_df[trades_df['pnl_dollars'] <= 0]['pnl_dollars'].sum()) if len(trades_df[trades_df['pnl_dollars'] <= 0]) > 0 else 0
    }


if __name__ == '__main__':
    print("=" * 80)
    print("PARAMETER GRID SEARCH - Triangle Pattern Optimization")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Use 2020-2024 for optimization (save 2025 for validation)
    h1_train = h1_df[(h1_df.index >= '2020-01-01') & (h1_df.index < '2025-01-01')]
    h4_train = h4_df[(h4_df.index >= '2020-01-01') & (h4_df.index < '2025-01-01')]

    print(f"\nTraining period: {h1_train.index.min()} to {h1_train.index.max()}")
    print(f"Bars: {len(h1_train):,}\n")

    # Parameter grid
    r2_values = [0.4, 0.5, 0.6, 0.7]
    slope_values = [0.0002, 0.0003, 0.0005]
    lookback_values = [40, 60, 80]
    time_end_values = [7, 9, 11]

    total_combinations = len(r2_values) * len(slope_values) * len(lookback_values) * len(time_end_values)

    print(f"Testing {total_combinations} parameter combinations...")
    print(f"R² min: {r2_values}")
    print(f"Slope tolerance: {slope_values}")
    print(f"Lookback: {lookback_values}")
    print(f"Time window end: {time_end_values} (hours)\n")

    # Run grid search
    results = []

    count = 0
    for r2, slope, lookback, time_end in itertools.product(r2_values, slope_values, lookback_values, time_end_values):
        count += 1

        if count % 10 == 0:
            print(f"Progress: {count}/{total_combinations} ({count/total_combinations*100:.0f}%)")

        result = run_triangle_backtest(h1_train, h4_train, r2, slope, lookback, time_end)

        if result:
            result['r2_min'] = r2
            result['slope_tol'] = slope
            result['lookback'] = lookback
            result['time_end'] = time_end
            results.append(result)

    print(f"\nCompleted: {len(results)} valid combinations\n")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Sort by different metrics
    print("=" * 80)
    print("TOP 10 BY ANNUAL P&L")
    print("=" * 80)
    top_pnl = results_df.nlargest(10, 'annual_pnl')
    for i, row in top_pnl.iterrows():
        print(f"\n{row['r2_min']:.1f} R² | {row['slope_tol']:.4f} slope | {row['lookback']:.0f} bars | {row['time_end']:.0f}h end")
        print(f"  Trades/yr: {row['trades_per_year']:.1f} | WR: {row['win_rate']:.1f}% | Annual: ${row['annual_pnl']:,.0f}")
        print(f"  PF: {row['profit_factor']:.2f} | Avg: ${row['avg_pnl']:.0f}")

    print("\n" + "=" * 80)
    print("TOP 10 BY PROFIT FACTOR")
    print("=" * 80)
    top_pf = results_df.nlargest(10, 'profit_factor')
    for i, row in top_pf.iterrows():
        print(f"\n{row['r2_min']:.1f} R² | {row['slope_tol']:.4f} slope | {row['lookback']:.0f} bars | {row['time_end']:.0f}h end")
        print(f"  Trades/yr: {row['trades_per_year']:.1f} | WR: {row['win_rate']:.1f}% | Annual: ${row['annual_pnl']:,.0f}")
        print(f"  PF: {row['profit_factor']:.2f} | Avg: ${row['avg_pnl']:.0f}")

    print("\n" + "=" * 80)
    print("TOP 10 BY WIN RATE")
    print("=" * 80)
    top_wr = results_df.nlargest(10, 'win_rate')
    for i, row in top_wr.iterrows():
        print(f"\n{row['r2_min']:.1f} R² | {row['slope_tol']:.4f} slope | {row['lookback']:.0f} bars | {row['time_end']:.0f}h end")
        print(f"  Trades/yr: {row['trades_per_year']:.1f} | WR: {row['win_rate']:.1f}% | Annual: ${row['annual_pnl']:,.0f}")
        print(f"  PF: {row['profit_factor']:.2f} | Avg: ${row['avg_pnl']:.0f}")

    # Balanced score: combines frequency, WR, and profitability
    print("\n" + "=" * 80)
    print("TOP 10 BY BALANCED SCORE")
    print("=" * 80)

    # Normalize metrics
    results_df['trades_norm'] = (results_df['trades_per_year'] - results_df['trades_per_year'].min()) / (results_df['trades_per_year'].max() - results_df['trades_per_year'].min())
    results_df['wr_norm'] = (results_df['win_rate'] - results_df['win_rate'].min()) / (results_df['win_rate'].max() - results_df['win_rate'].min())
    results_df['pnl_norm'] = (results_df['annual_pnl'] - results_df['annual_pnl'].min()) / (results_df['annual_pnl'].max() - results_df['annual_pnl'].min())
    results_df['pf_norm'] = (results_df['profit_factor'] - results_df['profit_factor'].min()) / (results_df['profit_factor'].max() - results_df['profit_factor'].min())

    # Weighted score: 30% trades, 25% WR, 30% PnL, 15% PF
    results_df['score'] = (
        0.30 * results_df['trades_norm'] +
        0.25 * results_df['wr_norm'] +
        0.30 * results_df['pnl_norm'] +
        0.15 * results_df['pf_norm']
    )

    top_balanced = results_df.nlargest(10, 'score')
    for i, row in top_balanced.iterrows():
        print(f"\n{row['r2_min']:.1f} R² | {row['slope_tol']:.4f} slope | {row['lookback']:.0f} bars | {row['time_end']:.0f}h end | Score: {row['score']:.3f}")
        print(f"  Trades/yr: {row['trades_per_year']:.1f} | WR: {row['win_rate']:.1f}% | Annual: ${row['annual_pnl']:,.0f}")
        print(f"  PF: {row['profit_factor']:.2f} | Avg: ${row['avg_pnl']:.0f}")

    # Save results
    results_df.to_csv('parameter_optimization_results.csv', index=False)
    print(f"\n✅ Results saved to parameter_optimization_results.csv")

    # Recommended parameters
    print("\n" + "=" * 80)
    print("RECOMMENDED PARAMETERS (Top Balanced)")
    print("=" * 80)
    best = top_balanced.iloc[0]
    print(f"\nR² min: {best['r2_min']}")
    print(f"Slope tolerance: {best['slope_tol']}")
    print(f"Lookback: {int(best['lookback'])}")
    print(f"Time window: 3-{int(best['time_end'])} AM")
    print(f"\nExpected Performance:")
    print(f"  Trades/year: {best['trades_per_year']:.1f}")
    print(f"  Win rate: {best['win_rate']:.1f}%")
    print(f"  Annual P&L: ${best['annual_pnl']:,.0f}")
    print(f"  Profit factor: {best['profit_factor']:.2f}")
