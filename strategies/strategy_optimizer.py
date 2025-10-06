"""
Strategy Parameter Optimizer

Tests multiple parameter combinations to find optimal settings for:
1. Trade frequency (target: 150-200 trades/year)
2. Win rate (target: >50%)
3. Profit factor (target: >1.5)
4. Risk/reward ratio (target: >1.3:1)
"""
import pandas as pd
import numpy as np
from itertools import product
from strategy_breakout_v2 import EnhancedLondonBreakout
from data_loader import ForexDataLoader

class StrategyOptimizer:
    def __init__(self, h1_df, h4_df):
        self.h1_df = h1_df
        self.h4_df = h4_df

    def test_parameters(self, params):
        """
        Test single parameter combination

        Returns: dict with performance metrics
        """
        strategy = EnhancedLondonBreakout()

        # Apply parameters
        strategy.min_asia_range_pips = params['min_range']
        strategy.max_asia_range_pips = params['max_range']
        strategy.breakout_buffer_pips = params['buffer']
        strategy.min_first_hour_move_pips = params['momentum']
        strategy.risk_reward_ratio = params['rr_ratio']

        # Run backtest
        try:
            trades = strategy.backtest(self.h1_df, self.h4_df)

            if len(trades) == 0:
                return None

            wins = trades[trades['pnl_dollars'] > 0]
            losses = trades[trades['pnl_dollars'] <= 0]

            win_rate = len(wins) / len(trades)
            total_pnl = trades['pnl_dollars'].sum()
            avg_pnl = trades['pnl_dollars'].mean()

            profit_factor = 0
            if len(wins) > 0 and len(losses) > 0:
                profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())

            # Calculate annualized metrics
            days = (self.h1_df.index.max() - self.h1_df.index.min()).days
            years = days / 365.25
            trades_per_year = len(trades) / years
            annual_pnl = total_pnl / years

            return {
                'params': params,
                'trades': len(trades),
                'trades_per_year': trades_per_year,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'annual_pnl': annual_pnl,
                'avg_pnl': avg_pnl,
                'profit_factor': profit_factor,
                'avg_win': wins['pnl_dollars'].mean() if len(wins) > 0 else 0,
                'avg_loss': losses['pnl_dollars'].mean() if len(losses) > 0 else 0,
            }
        except Exception as e:
            print(f"Error testing params {params}: {e}")
            return None

    def optimize(self):
        """
        Test multiple parameter combinations

        Parameter ranges to test:
        - min_range: 15, 20, 25 pips
        - momentum: 10, 12, 15 pips
        - buffer: 2, 3, 4 pips
        - rr_ratio: 1.3, 1.5, 1.8
        """
        print("=" * 80)
        print("STRATEGY PARAMETER OPTIMIZATION")
        print("=" * 80)
        print("\nTesting parameter combinations...")

        # Define parameter grid
        param_grid = {
            'min_range': [15, 20],
            'max_range': [60],  # Keep constant
            'buffer': [2, 3],
            'momentum': [10, 12, 15],
            'rr_ratio': [1.3, 1.5, 1.8],
        }

        # Generate all combinations
        keys = list(param_grid.keys())
        combinations = list(product(*[param_grid[k] for k in keys]))

        print(f"Total combinations to test: {len(combinations)}\n")

        results = []
        for i, combo in enumerate(combinations):
            params = dict(zip(keys, combo))

            result = self.test_parameters(params)
            if result:
                results.append(result)

            if (i + 1) % 5 == 0:
                print(f"Tested {i+1}/{len(combinations)} combinations...")

        results_df = pd.DataFrame(results)

        # Sort by different criteria
        print("\n" + "=" * 80)
        print("OPTIMIZATION RESULTS")
        print("=" * 80)

        # Filter for viable strategies (profit factor > 1.2, win rate > 40%)
        viable = results_df[
            (results_df['profit_factor'] > 1.2) &
            (results_df['win_rate'] > 0.40)
        ].copy()

        if len(viable) == 0:
            print("\n❌ No viable parameter combinations found!")
            return results_df

        print(f"\nViable strategies: {len(viable)} out of {len(results_df)}")

        # Find best by different metrics
        print("\n--- TOP 5 BY TRADE FREQUENCY ---")
        top_freq = viable.nlargest(5, 'trades_per_year')
        for idx, row in top_freq.iterrows():
            print(f"Trades/Year: {row['trades_per_year']:.0f} | Win Rate: {row['win_rate']*100:.1f}% | "
                  f"Annual P&L: ${row['annual_pnl']:,.0f} | PF: {row['profit_factor']:.2f}")
            print(f"  Params: {row['params']}")

        print("\n--- TOP 5 BY ANNUAL P&L ---")
        top_pnl = viable.nlargest(5, 'annual_pnl')
        for idx, row in top_pnl.iterrows():
            print(f"Annual P&L: ${row['annual_pnl']:,.0f} | Trades/Year: {row['trades_per_year']:.0f} | "
                  f"Win Rate: {row['win_rate']*100:.1f}% | PF: {row['profit_factor']:.2f}")
            print(f"  Params: {row['params']}")

        print("\n--- TOP 5 BY PROFIT FACTOR ---")
        top_pf = viable.nlargest(5, 'profit_factor')
        for idx, row in top_pf.iterrows():
            print(f"Profit Factor: {row['profit_factor']:.2f} | Win Rate: {row['win_rate']*100:.1f}% | "
                  f"Annual P&L: ${row['annual_pnl']:,.0f} | Trades/Year: {row['trades_per_year']:.0f}")
            print(f"  Params: {row['params']}")

        # Find balanced best (score = trades_per_year × profit_factor × annual_pnl / 1000)
        viable['score'] = (
            viable['trades_per_year'] / 100 *
            viable['profit_factor'] *
            viable['annual_pnl'] / 1000
        )

        print("\n--- TOP 5 BY BALANCED SCORE ---")
        print("(Score = frequency × profit_factor × annual_pnl)")
        top_balanced = viable.nlargest(5, 'score')
        for idx, row in top_balanced.iterrows():
            print(f"Score: {row['score']:.2f} | Trades/Year: {row['trades_per_year']:.0f} | "
                  f"Win Rate: {row['win_rate']*100:.1f}% | Annual P&L: ${row['annual_pnl']:,.0f} | "
                  f"PF: {row['profit_factor']:.2f}")
            print(f"  Params: {row['params']}")

        # Recommend best
        best = viable.nlargest(1, 'score').iloc[0]

        print("\n" + "=" * 80)
        print("RECOMMENDED PARAMETERS")
        print("=" * 80)
        print(f"\nMin Asia Range: {best['params']['min_range']} pips")
        print(f"Breakout Buffer: {best['params']['buffer']} pips")
        print(f"Momentum Requirement: {best['params']['momentum']} pips")
        print(f"Risk/Reward Ratio: {best['params']['rr_ratio']}")

        print(f"\nExpected Performance:")
        print(f"  Trades per year: {best['trades_per_year']:.0f}")
        print(f"  Win rate: {best['win_rate']*100:.1f}%")
        print(f"  Annual P&L: ${best['annual_pnl']:,.0f}")
        print(f"  Profit factor: {best['profit_factor']:.2f}")
        print(f"  Avg P&L per trade: ${best['avg_pnl']:.2f}")

        # Save results
        results_df.to_csv('output/london_breakout/optimization_results.csv', index=False)
        print(f"\n✅ All results saved to output/london_breakout/optimization_results.csv")

        return results_df, best


if __name__ == '__main__':
    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Filter to 2023-2025
    h1_df = h1_df[h1_df.index >= '2023-01-01']
    h4_df = h4_df[h4_df.index >= '2023-01-01']

    print(f"Data period: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"H1 bars: {len(h1_df):,}")
    print(f"H4 bars: {len(h4_df):,}\n")

    # Run optimization
    optimizer = StrategyOptimizer(h1_df, h4_df)
    results_df, best_params = optimizer.optimize()
