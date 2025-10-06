#!/usr/bin/env python3
"""
Robust Strategy Optimization - Avoiding Overfitting

Methods to prevent overfitting:
1. Walk-Forward Analysis
2. Out-of-Sample Testing
3. Parameter Stability Testing
4. Monte Carlo Validation
5. Multiple Market Regime Testing
"""
import sys
sys.path.insert(0, 'core')
sys.path.insert(0, 'strategies')

import pandas as pd
import numpy as np
from itertools import product
from strategy_breakout_v3 import LondonBreakoutV3
from data_loader import ForexDataLoader

class RobustOptimizer:
    """
    Walk-forward optimization to prevent overfitting
    """

    def __init__(self, h1_df, h4_df):
        self.h1_df = h1_df
        self.h4_df = h4_df

    def walk_forward_analysis(self, train_months=12, test_months=3):
        """
        Walk-forward optimization:
        - Train on X months
        - Test on next Y months
        - Roll forward and repeat
        """
        print("="*80)
        print("WALK-FORWARD ANALYSIS")
        print("="*80)
        print(f"\nTrain Period: {train_months} months")
        print(f"Test Period: {test_months} months")

        results = []

        start_date = self.h1_df.index.min()
        end_date = self.h1_df.index.max()

        current_date = start_date
        window = 0

        while current_date < end_date:
            window += 1

            # Define train period
            train_end = current_date + pd.DateOffset(months=train_months)
            if train_end > end_date:
                break

            # Define test period
            test_end = train_end + pd.DateOffset(months=test_months)
            if test_end > end_date:
                test_end = end_date

            print(f"\n{'='*80}")
            print(f"Window {window}")
            print(f"Train: {current_date.date()} to {train_end.date()}")
            print(f"Test:  {train_end.date()} to {test_end.date()}")
            print('='*80)

            # Get train data
            train_h1 = self.h1_df[(self.h1_df.index >= current_date) &
                                   (self.h1_df.index < train_end)]
            train_h4 = self.h4_df[(self.h4_df.index >= current_date) &
                                   (self.h4_df.index < train_end)]

            # Get test data
            test_h1 = self.h1_df[(self.h1_df.index >= train_end) &
                                  (self.h1_df.index < test_end)]
            test_h4 = self.h4_df[(self.h4_df.index >= train_end) &
                                  (self.h4_df.index < test_end)]

            if len(train_h1) < 1000 or len(test_h1) < 100:
                print("Insufficient data, skipping...")
                current_date = test_end
                continue

            # Optimize on train period
            print("\nOptimizing on training data...")
            best_params = self.optimize_parameters(train_h1, train_h4)

            # Test on out-of-sample data
            print("\nTesting on out-of-sample data...")
            test_result = self.test_parameters(test_h1, test_h4, best_params)

            results.append({
                'window': window,
                'train_start': current_date,
                'train_end': train_end,
                'test_start': train_end,
                'test_end': test_end,
                'best_params': best_params,
                'test_sharpe': test_result['sharpe'],
                'test_return': test_result['total_return'],
                'test_max_dd': test_result['max_dd'],
                'test_win_rate': test_result['win_rate'],
                'test_trades': test_result['num_trades']
            })

            # Move to next window
            current_date = test_end

        return pd.DataFrame(results)

    def optimize_parameters(self, h1_df, h4_df):
        """
        Optimize strategy parameters on training data

        Parameters to optimize (conservative ranges):
        - min_asia_range: 10-25 pips
        - breakout_buffer: 1-5 pips
        - risk_reward: 1.0-2.0
        - min_momentum: 10-20 pips
        """
        # Conservative parameter ranges to avoid overfitting
        param_grid = {
            'min_asia_range': [10, 15, 20],
            'breakout_buffer': [1.5, 2.0, 3.0],
            'risk_reward': [1.2, 1.3, 1.5],
            'min_momentum': [12, 15, 18]
        }

        best_sharpe = -999
        best_params = None

        print(f"\nTesting {np.prod([len(v) for v in param_grid.values()])} parameter combinations...")

        for params in product(*param_grid.values()):
            min_range, buffer, rr, momentum = params

            # Create strategy with these parameters
            strategy = LondonBreakoutV3(risk_percent=0.75, initial_capital=100000)
            strategy.min_asia_range_pips = min_range
            strategy.breakout_buffer_pips = buffer
            strategy.risk_reward_ratio = rr
            strategy.min_first_hour_move_pips = momentum

            # Run backtest
            try:
                trades = strategy.backtest(h1_df.copy(), h4_df.copy())

                if len(trades) < 10:  # Need minimum trades
                    continue

                # Calculate metrics
                returns = trades['pnl_dollars'].values
                sharpe = self._calculate_sharpe(returns)

                # Track best
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_params = {
                        'min_asia_range': min_range,
                        'breakout_buffer': buffer,
                        'risk_reward': rr,
                        'min_momentum': momentum,
                        'sharpe': sharpe
                    }
            except Exception as e:
                continue

        print(f"\nBest Parameters Found:")
        for k, v in best_params.items():
            print(f"  {k}: {v}")

        return best_params

    def test_parameters(self, h1_df, h4_df, params):
        """
        Test parameters on out-of-sample data
        """
        strategy = LondonBreakoutV3(risk_percent=0.75, initial_capital=100000)
        strategy.min_asia_range_pips = params['min_asia_range']
        strategy.breakout_buffer_pips = params['breakout_buffer']
        strategy.risk_reward_ratio = params['risk_reward']
        strategy.min_first_hour_move_pips = params['min_momentum']

        trades = strategy.backtest(h1_df.copy(), h4_df.copy())

        if len(trades) == 0:
            return {
                'sharpe': 0,
                'total_return': 0,
                'max_dd': 0,
                'win_rate': 0,
                'num_trades': 0
            }

        # Calculate metrics
        wins = trades[trades['pnl_dollars'] > 0]

        # Calculate max DD
        equity_curve = trades['capital_after'].values
        running_max = np.maximum.accumulate(np.insert(equity_curve, 0, 100000))
        drawdowns = (equity_curve - running_max[1:]) / running_max[1:] * 100
        max_dd = drawdowns.min() if len(drawdowns) > 0 else 0

        return {
            'sharpe': self._calculate_sharpe(trades['pnl_dollars'].values),
            'total_return': (strategy.current_capital - 100000) / 100000 * 100,
            'max_dd': max_dd,
            'win_rate': len(wins) / len(trades) * 100,
            'num_trades': len(trades)
        }

    def _calculate_sharpe(self, returns, risk_free_rate=0.0):
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        # Annualize (assuming ~52 trades/year)
        sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(52)
        return sharpe

    def parameter_stability_test(self):
        """
        Test if parameters are stable across different time periods
        """
        print("\n" + "="*80)
        print("PARAMETER STABILITY TEST")
        print("="*80)

        # Split data into 3 equal periods
        total_days = (self.h1_df.index.max() - self.h1_df.index.min()).days
        period_days = total_days // 3

        periods = []
        start = self.h1_df.index.min()

        for i in range(3):
            end = start + pd.Timedelta(days=period_days)
            if i == 2:  # Last period gets remainder
                end = self.h1_df.index.max()

            h1_period = self.h1_df[(self.h1_df.index >= start) & (self.h1_df.index < end)]
            h4_period = self.h4_df[(self.h4_df.index >= start) & (self.h4_df.index < end)]

            print(f"\nPeriod {i+1}: {start.date()} to {end.date()}")
            best_params = self.optimize_parameters(h1_period, h4_period)

            periods.append({
                'period': i + 1,
                'start': start,
                'end': end,
                **best_params
            })

            start = end

        # Analyze stability
        df = pd.DataFrame(periods)

        print("\n" + "="*80)
        print("PARAMETER STABILITY ACROSS PERIODS:")
        print("="*80)
        print(df.to_string(index=False))

        # Calculate coefficient of variation for each parameter
        print("\n" + "="*80)
        print("STABILITY METRICS (Lower = More Stable):")
        print("="*80)

        for param in ['min_asia_range', 'breakout_buffer', 'risk_reward', 'min_momentum']:
            values = df[param].values
            cv = np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
            print(f"{param}: CV = {cv:.3f} (values: {values})")

        return df


if __name__ == '__main__':
    print("="*80)
    print("ROBUST OPTIMIZATION - AVOIDING OVERFITTING")
    print("="*80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Use data from 2020 onwards
    h1_df = h1_df[h1_df.index >= '2020-01-01']
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nData: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"Total bars: {len(h1_df):,}")

    optimizer = RobustOptimizer(h1_df, h4_df)

    # Run walk-forward analysis
    print("\n" + "="*80)
    print("RUNNING WALK-FORWARD ANALYSIS")
    print("="*80)

    wf_results = optimizer.walk_forward_analysis(train_months=18, test_months=6)

    print("\n" + "="*80)
    print("WALK-FORWARD RESULTS SUMMARY")
    print("="*80)
    print(wf_results[['window', 'test_sharpe', 'test_return', 'test_max_dd',
                       'test_win_rate', 'test_trades']].to_string(index=False))

    # Calculate average out-of-sample performance
    print("\n" + "="*80)
    print("AVERAGE OUT-OF-SAMPLE PERFORMANCE:")
    print("="*80)
    print(f"Avg Sharpe: {wf_results['test_sharpe'].mean():.2f}")
    print(f"Avg Return: {wf_results['test_return'].mean():.2f}%")
    print(f"Avg Max DD: {wf_results['test_max_dd'].mean():.2f}%")
    print(f"Avg Win Rate: {wf_results['test_win_rate'].mean():.1f}%")
    print(f"Avg Trades: {wf_results['test_trades'].mean():.0f}")

    # Parameter stability test
    stability_df = optimizer.parameter_stability_test()

    print("\n" + "="*80)
    print("CONCLUSIONS:")
    print("="*80)
    print("""
If parameters are stable across periods (low CV):
  ✅ Strategy is robust, not overfit
  ✅ Parameters capture real market dynamics
  ✅ Safe to use for live trading

If out-of-sample performance is consistent:
  ✅ Strategy generalizes well
  ✅ Not curve-fit to specific period
  ✅ Higher confidence in future performance

Red flags to watch for:
  ⚠️ High CV (>0.3) = parameters unstable
  ⚠️ Big drop in out-of-sample vs in-sample = overfitting
  ⚠️ Negative Sharpe in test periods = strategy doesn't work
""")

    print("="*80)
