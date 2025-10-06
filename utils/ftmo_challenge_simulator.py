"""
FTMO Challenge Simulator

Runs 60-day rolling window backtests to estimate FTMO pass rate using the London Breakout strategy.

FTMO Swing Challenge Rules:
- 60 calendar days to reach +10% profit
- Maximum drawdown: -10%
- Maximum daily drawdown: -5%
- Initial capital: $100,000

Output:
- Pass rate across all 60-day windows
- Average days to pass (for successful windows)
- Common failure reasons
- Best/worst performing windows
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_loader import ForexDataLoader
from strategy_breakout_v3 import LondonBreakoutV3
from ftmo_risk_manager import FTMORiskManager

class FTMOChallengeSimulator:
    def __init__(self, start_date='2020-01-01', end_date='2025-09-26'):
        """
        Args:
        - start_date: Historical data start
        - end_date: Historical data end
        """
        self.start_date = start_date
        self.end_date = end_date

        # Load H1 and H4 data for v3 strategy
        print("Loading H1 and H4 data...")
        loader = ForexDataLoader()
        self.h1_df = loader.load('EURUSD', 'H1')
        self.h4_df = loader.load('EURUSD', 'H4')
        self.h1_df = self.h1_df[(self.h1_df.index >= start_date) & (self.h1_df.index <= end_date)]
        self.h4_df = self.h4_df[(self.h4_df.index >= start_date) & (self.h4_df.index <= end_date)]
        print(f"Loaded {len(self.h1_df):,} H1 bars and {len(self.h4_df):,} H4 bars")

        # Initialize strategy
        self.strategy = LondonBreakoutV3()

        # Results
        self.challenge_results = []

    def run_single_challenge(self, start_idx, max_days=60):
        """
        Run single 60-day FTMO challenge using v3 strategy

        Args:
        - start_idx: Starting timestamp
        - max_days: Challenge duration (60 days)

        Returns: dict with challenge results
        """
        risk_manager = FTMORiskManager(initial_equity=100000)
        equity = 100000.0
        end_date = start_idx + timedelta(days=max_days)

        # Filter data for this challenge period
        challenge_h1 = self.h1_df[(self.h1_df.index >= start_idx) & (self.h1_df.index < end_date)]
        challenge_h4 = self.h4_df[(self.h4_df.index >= start_idx) & (self.h4_df.index < end_date)]

        if len(challenge_h1) < 100:  # Need minimum bars
            return None

        # Run v3 backtest for this period
        strategy_instance = LondonBreakoutV3()
        all_trades = strategy_instance.backtest(challenge_h1, challenge_h4)

        if len(all_trades) == 0:
            return None

        # Process trades chronologically and track equity
        all_trades = all_trades.sort_values('exit_time')

        for _, trade in all_trades.iterrows():
            pnl = trade['pnl_dollars']
            exit_time = pd.to_datetime(trade['exit_time'])

            # Update equity
            equity += pnl
            risk_manager.record_trade(pnl, exit_time)
            risk_manager.update_daily(equity, exit_time.date())

            # Check if challenge ended (DD violation)
            if not risk_manager.is_challenge_active:
                break

        # Challenge results
        final_equity = equity
        total_return = (final_equity - 100000) / 100000
        passed = risk_manager.pass_date is not None
        failed = risk_manager.failure_reason is not None

        status = risk_manager.get_risk_status()

        return {
            'start_date': start_idx,
            'end_date': end_date,
            'initial_equity': 100000,
            'final_equity': final_equity,
            'total_return': total_return,
            'num_trades': len(all_trades),
            'passed': passed,
            'failed': failed,
            'failure_reason': risk_manager.failure_reason,
            'pass_date': risk_manager.pass_date,
            'max_dd': status['total_dd'],
            'days_to_pass': (risk_manager.pass_date - start_idx).days if passed else None
        }

    def run_all_challenges(self, window_step_days=30):
        """
        Run multiple 60-day challenges with rolling windows

        Args:
        - window_step_days: Days between each challenge start (30 = monthly)
        """
        print(f"\nRunning FTMO challenge simulations...")
        print(f"Window: 60 days, Step: {window_step_days} days\n")

        # Generate start dates
        current_date = self.h1_df.index.min().date()
        end_limit = self.h1_df.index.max().date() - timedelta(days=60)

        while current_date <= end_limit:
            # Convert to timestamp
            start_ts = pd.Timestamp(current_date)

            # Run challenge
            result = self.run_single_challenge(start_ts, max_days=60)

            if result:
                self.challenge_results.append(result)
                status = "PASS" if result['passed'] else ("FAIL" if result['failed'] else "INCOMPLETE")
                print(f"{current_date} | {status} | Return: {result['total_return']*100:+.2f}% | Trades: {result['num_trades']}")

            # Move to next window
            current_date += timedelta(days=window_step_days)

        return self.analyze_results()

    def analyze_results(self):
        """Analyze all challenge results"""
        if len(self.challenge_results) == 0:
            print("No challenge results to analyze")
            return

        df = pd.DataFrame(self.challenge_results)

        print("\n" + "=" * 60)
        print("FTMO CHALLENGE SIMULATION RESULTS")
        print("=" * 60)

        # Overall stats
        total_challenges = len(df)
        passed = df[df['passed'] == True]
        failed = df[df['failed'] == True]

        pass_rate = len(passed) / total_challenges * 100 if total_challenges > 0 else 0

        print(f"\nOverall Statistics:")
        print(f"  Total challenges simulated: {total_challenges}")
        print(f"  Passed: {len(passed)} ({len(passed)/total_challenges*100:.1f}%)")
        print(f"  Failed: {len(failed)} ({len(failed)/total_challenges*100:.1f}%)")
        print(f"  Incomplete: {total_challenges - len(passed) - len(failed)}")

        # Days to pass
        if len(passed) > 0:
            avg_days = passed['days_to_pass'].mean()
            median_days = passed['days_to_pass'].median()
            print(f"\nTime to Pass (for successful challenges):")
            print(f"  Average: {avg_days:.1f} days")
            print(f"  Median: {median_days:.1f} days")
            print(f"  Min: {passed['days_to_pass'].min():.0f} days")
            print(f"  Max: {passed['days_to_pass'].max():.0f} days")

        # Failure reasons
        if len(failed) > 0:
            print(f"\nFailure Reasons:")
            for reason in failed['failure_reason'].value_counts().items():
                print(f"  {reason[0]}: {reason[1]} ({reason[1]/len(failed)*100:.1f}%)")

        # Performance metrics
        print(f"\nPerformance Metrics:")
        print(f"  Avg return (all): {df['total_return'].mean()*100:+.2f}%")
        print(f"  Avg return (passed): {passed['total_return'].mean()*100:+.2f}%" if len(passed) > 0 else "  Avg return (passed): N/A")
        print(f"  Avg return (failed): {failed['total_return'].mean()*100:+.2f}%" if len(failed) > 0 else "  Avg return (failed): N/A")
        print(f"  Avg trades per challenge: {df['num_trades'].mean():.1f}")
        print(f"  Avg max DD: {df['max_dd'].mean()*100:.2f}%")

        # Best/worst
        best = df.loc[df['total_return'].idxmax()]
        worst = df.loc[df['total_return'].idxmin()]

        print(f"\nBest Challenge:")
        print(f"  Start: {best['start_date'].date()}")
        print(f"  Return: {best['total_return']*100:+.2f}%")
        print(f"  Passed: {best['passed']}")

        print(f"\nWorst Challenge:")
        print(f"  Start: {worst['start_date'].date()}")
        print(f"  Return: {worst['total_return']*100:+.2f}%")
        print(f"  Reason: {worst['failure_reason']}")

        # Save results
        df.to_csv('output/london_breakout/ftmo_simulation_results.csv', index=False)
        print(f"\n✅ Results saved to output/london_breakout/ftmo_simulation_results.csv")

        return df

if __name__ == '__main__':
    print("=" * 60)
    print("FTMO CHALLENGE SIMULATOR")
    print("=" * 60)

    # Run simulations
    simulator = FTMOChallengeSimulator(
        start_date='2020-01-01',
        end_date='2025-09-26'
    )

    results = simulator.run_all_challenges(window_step_days=30)

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)
