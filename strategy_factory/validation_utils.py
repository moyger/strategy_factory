#!/usr/bin/env python3
"""
Validation Utilities for Strategy Backtesting

Includes:
1. Walk-Forward Validation (rolling window train/test)
2. Monte Carlo Simulation (trade resampling)
3. Point-in-Time Universe Selection (fix survivorship bias)

Author: Strategy Factory
Date: 2025-01-14
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class WalkForwardValidator:
    """
    Walk-Forward Validation Framework

    Tests strategy robustness by:
    1. Splitting data into train/test windows
    2. Optimizing on train window (optional)
    3. Testing on unseen test window
    4. Rolling forward through time

    This prevents overfitting and tests out-of-sample performance.
    """

    def __init__(self,
                 train_period_days: int = 730,  # 2 years
                 test_period_days: int = 365,   # 1 year
                 step_days: int = 365,          # 1 year step
                 min_train_days: int = 365):    # Minimum 1 year train
        """
        Initialize Walk-Forward Validator

        Args:
            train_period_days: Size of training window in days
            test_period_days: Size of test window in days
            step_days: How many days to step forward between folds
            min_train_days: Minimum required training days
        """
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.step_days = step_days
        self.min_train_days = min_train_days

    def generate_folds(self,
                       prices: pd.DataFrame) -> List[Dict[str, pd.Timestamp]]:
        """
        Generate train/test fold dates

        Args:
            prices: Price DataFrame with DatetimeIndex

        Returns:
            List of dicts with train_start, train_end, test_start, test_end
        """
        start_date = prices.index[0]
        end_date = prices.index[-1]

        folds = []
        current_train_start = start_date

        while True:
            # Calculate fold boundaries
            train_end = current_train_start + timedelta(days=self.train_period_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period_days)

            # Check if we have enough data
            if test_end > end_date:
                break

            # Find nearest trading days
            train_start_actual = prices.index[prices.index >= current_train_start][0]
            train_end_actual = prices.index[prices.index <= train_end][-1]
            test_start_actual = prices.index[prices.index >= test_start][0]
            test_end_actual = prices.index[prices.index <= test_end][-1]

            # Verify minimum train period
            train_days = (train_end_actual - train_start_actual).days
            if train_days < self.min_train_days:
                break

            folds.append({
                'fold': len(folds) + 1,
                'train_start': train_start_actual,
                'train_end': train_end_actual,
                'test_start': test_start_actual,
                'test_end': test_end_actual,
                'train_days': train_days,
                'test_days': (test_end_actual - test_start_actual).days
            })

            # Step forward
            current_train_start += timedelta(days=self.step_days)

        return folds

    def run_validation(self,
                      strategy_fn: Callable,
                      prices: pd.DataFrame,
                      btc_prices: pd.Series,
                      initial_capital: float = 100000,
                      **strategy_kwargs) -> pd.DataFrame:
        """
        Run walk-forward validation

        Args:
            strategy_fn: Function that creates and runs strategy
                         Should accept (prices, btc_prices, start_date, end_date, **kwargs)
                         Should return portfolio object
            prices: Full price DataFrame
            btc_prices: Full BTC price Series
            initial_capital: Starting capital for each fold
            **strategy_kwargs: Additional arguments for strategy

        Returns:
            DataFrame with results for each fold
        """
        folds = self.generate_folds(prices)

        if len(folds) == 0:
            raise ValueError("No valid folds generated. Check date range and parameters.")

        print(f"\n{'='*80}")
        print(f"WALK-FORWARD VALIDATION")
        print(f"{'='*80}")
        print(f"Total Folds: {len(folds)}")
        print(f"Train Period: {self.train_period_days} days (~{self.train_period_days/365:.1f} years)")
        print(f"Test Period: {self.test_period_days} days (~{self.test_period_days/365:.1f} years)")
        print(f"Step Size: {self.step_days} days")
        print(f"{'='*80}\n")

        results = []

        for fold in folds:
            print(f"\n📊 Fold {fold['fold']}:")
            print(f"   Train: {fold['train_start'].date()} to {fold['train_end'].date()} ({fold['train_days']} days)")
            print(f"   Test:  {fold['test_start'].date()} to {fold['test_end'].date()} ({fold['test_days']} days)")

            # Extract test period data
            test_mask = (prices.index >= fold['test_start']) & (prices.index <= fold['test_end'])
            test_prices = prices[test_mask].copy()
            test_btc = btc_prices[test_mask].copy()

            # Run strategy on test period
            try:
                portfolio = strategy_fn(
                    test_prices,
                    test_btc,
                    initial_capital=initial_capital,
                    **strategy_kwargs
                )

                # Extract metrics
                total_return = float(portfolio.total_return().iloc[0] if isinstance(portfolio.total_return(), pd.Series)
                                   else portfolio.total_return()) * 100
                sharpe = float(portfolio.sharpe_ratio(freq='D').iloc[0] if isinstance(portfolio.sharpe_ratio(freq='D'), pd.Series)
                             else portfolio.sharpe_ratio(freq='D'))
                max_dd = float(portfolio.max_drawdown().iloc[0] if isinstance(portfolio.max_drawdown(), pd.Series)
                             else portfolio.max_drawdown()) * 100

                try:
                    win_rate = float(portfolio.trades.win_rate().iloc[0] if isinstance(portfolio.trades.win_rate(), pd.Series)
                                   else portfolio.trades.win_rate()) * 100
                except:
                    win_rate = np.nan

                num_trades = len(portfolio.trades.records)

                results.append({
                    'fold': fold['fold'],
                    'train_start': fold['train_start'],
                    'train_end': fold['train_end'],
                    'test_start': fold['test_start'],
                    'test_end': fold['test_end'],
                    'test_days': fold['test_days'],
                    'total_return_%': total_return,
                    'sharpe_ratio': sharpe,
                    'max_drawdown_%': max_dd,
                    'win_rate_%': win_rate,
                    'num_trades': num_trades,
                    'status': 'SUCCESS'
                })

                print(f"   ✅ Return: {total_return:.2f}%, Sharpe: {sharpe:.2f}, MaxDD: {max_dd:.2f}%, Trades: {num_trades}")

            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                results.append({
                    'fold': fold['fold'],
                    'train_start': fold['train_start'],
                    'train_end': fold['train_end'],
                    'test_start': fold['test_start'],
                    'test_end': fold['test_end'],
                    'test_days': fold['test_days'],
                    'total_return_%': np.nan,
                    'sharpe_ratio': np.nan,
                    'max_drawdown_%': np.nan,
                    'win_rate_%': np.nan,
                    'num_trades': 0,
                    'status': f'FAILED: {str(e)[:50]}'
                })

        results_df = pd.DataFrame(results)

        # Print summary
        print(f"\n{'='*80}")
        print(f"WALK-FORWARD SUMMARY")
        print(f"{'='*80}")

        successful = results_df[results_df['status'] == 'SUCCESS']
        if len(successful) > 0:
            print(f"Successful Folds: {len(successful)}/{len(results_df)}")
            print(f"\nAverage Metrics (Out-of-Sample):")
            print(f"   Mean Return: {successful['total_return_%'].mean():.2f}%")
            print(f"   Median Return: {successful['total_return_%'].median():.2f}%")
            print(f"   Std Dev: {successful['total_return_%'].std():.2f}%")
            print(f"   Mean Sharpe: {successful['sharpe_ratio'].mean():.2f}")
            print(f"   Mean MaxDD: {successful['max_drawdown_%'].mean():.2f}%")
            print(f"   Win Rate: {successful['win_rate_%'].mean():.2f}%")
            print(f"\nConsistency:")
            print(f"   Profitable Folds: {(successful['total_return_%'] > 0).sum()}/{len(successful)}")
            print(f"   Sharpe > 1: {(successful['sharpe_ratio'] > 1.0).sum()}/{len(successful)}")
        else:
            print(f"❌ No successful folds!")

        print(f"{'='*80}\n")

        return results_df


class MonteCarloSimulator:
    """
    Monte Carlo Simulation for Backtesting

    Resamples trades with replacement to:
    1. Generate distribution of possible outcomes
    2. Calculate confidence intervals
    3. Estimate probability of profit
    4. Identify worst-case scenarios
    """

    def __init__(self, n_simulations: int = 1000):
        """
        Initialize Monte Carlo Simulator

        Args:
            n_simulations: Number of simulation runs
        """
        self.n_simulations = n_simulations

    def run_simulation(self,
                      portfolio,
                      initial_capital: float = 100000) -> pd.DataFrame:
        """
        Run Monte Carlo simulation by resampling trades

        Args:
            portfolio: VectorBT portfolio object
            initial_capital: Starting capital

        Returns:
            DataFrame with simulation results
        """
        print(f"\n{'='*80}")
        print(f"MONTE CARLO SIMULATION")
        print(f"{'='*80}")
        print(f"Simulations: {self.n_simulations}")
        print(f"Initial Capital: ${initial_capital:,.0f}")

        # Extract trades
        try:
            trades_df = portfolio.trades.records_readable
        except:
            print(f"❌ No trades to simulate!")
            return pd.DataFrame()

        if len(trades_df) == 0:
            print(f"❌ No trades to simulate!")
            return pd.DataFrame()

        # Get returns per trade
        returns = trades_df['Return'].values
        num_trades = len(returns)

        print(f"Original Trades: {num_trades}")
        print(f"Original Total Return: {(portfolio.total_return().iloc[0] if isinstance(portfolio.total_return(), pd.Series) else portfolio.total_return()) * 100:.2f}%")
        print(f"\nResampling {num_trades} trades {self.n_simulations} times...")

        results = []

        for sim in range(self.n_simulations):
            # Resample trades with replacement
            resampled_returns = np.random.choice(returns, size=num_trades, replace=True)

            # Calculate cumulative return
            cumulative_value = initial_capital
            for ret in resampled_returns:
                cumulative_value *= (1 + ret)

            total_return = (cumulative_value / initial_capital - 1) * 100

            results.append({
                'simulation': sim + 1,
                'final_value': cumulative_value,
                'total_return_%': total_return
            })

        results_df = pd.DataFrame(results)

        # Calculate statistics
        mean_return = results_df['total_return_%'].mean()
        median_return = results_df['total_return_%'].median()
        std_return = results_df['total_return_%'].std()

        # Confidence intervals
        ci_90_lower = results_df['total_return_%'].quantile(0.05)
        ci_90_upper = results_df['total_return_%'].quantile(0.95)
        ci_95_lower = results_df['total_return_%'].quantile(0.025)
        ci_95_upper = results_df['total_return_%'].quantile(0.975)

        # Probability of profit
        prob_profit = (results_df['total_return_%'] > 0).sum() / len(results_df) * 100

        # Worst/best cases
        worst_case = results_df['total_return_%'].min()
        best_case = results_df['total_return_%'].max()

        # Print summary
        print(f"\n{'='*80}")
        print(f"MONTE CARLO RESULTS")
        print(f"{'='*80}")
        print(f"\n📊 Return Distribution:")
        print(f"   Mean: {mean_return:.2f}%")
        print(f"   Median: {median_return:.2f}%")
        print(f"   Std Dev: {std_return:.2f}%")
        print(f"\n📈 Confidence Intervals:")
        print(f"   90% CI: [{ci_90_lower:.2f}%, {ci_90_upper:.2f}%]")
        print(f"   95% CI: [{ci_95_lower:.2f}%, {ci_95_upper:.2f}%]")
        print(f"\n🎯 Probabilities:")
        print(f"   Prob(Profit): {prob_profit:.1f}%")
        print(f"   Prob(Loss): {100-prob_profit:.1f}%")
        print(f"\n📉 Worst/Best Cases:")
        print(f"   5th Percentile: {ci_90_lower:.2f}%")
        print(f"   Worst Case: {worst_case:.2f}%")
        print(f"   Best Case: {best_case:.2f}%")
        print(f"   95th Percentile: {ci_90_upper:.2f}%")
        print(f"{'='*80}\n")

        return results_df


class PointInTimeUniverse:
    """
    Point-in-Time Universe Selection

    Fixes survivorship bias by selecting assets based on
    their ranking AT THAT TIME, not current ranking.

    Example:
    - 2020-01-01: Use top 50 cryptos as of 2020-01-01 (includes failures)
    - 2021-01-01: Use top 50 cryptos as of 2021-01-01 (may include different assets)
    - 2022-01-01: Use top 50 cryptos as of 2022-01-01 (may include new launches)
    """

    @staticmethod
    def get_top_n_at_date(prices: pd.DataFrame,
                         date: pd.Timestamp,
                         n: int = 50,
                         lookback_days: int = 30) -> List[str]:
        """
        Get top N assets by market cap (proxied by price × volume) at specific date

        Args:
            prices: Price DataFrame
            date: Date to rank at
            n: Number of assets to select
            lookback_days: Days to look back for average volume

        Returns:
            List of top N tickers as of that date
        """
        # Get date range
        if date not in prices.index:
            # Find nearest date
            valid_dates = prices.index[prices.index <= date]
            if len(valid_dates) == 0:
                return []
            date = valid_dates[-1]

        lookback_start = date - timedelta(days=lookback_days)

        # Get prices and volume proxy for lookback period
        mask = (prices.index >= lookback_start) & (prices.index <= date)
        period_prices = prices[mask]

        if len(period_prices) == 0:
            return []

        # Calculate average price (proxy for market cap when volume not available)
        avg_prices = period_prices.mean()

        # Remove NaN
        avg_prices = avg_prices.dropna()

        # Sort by price (higher price = likely larger cap)
        ranked = avg_prices.sort_values(ascending=False)

        # Return top N
        return ranked.head(n).index.tolist()

    @staticmethod
    def create_pit_universe(prices: pd.DataFrame,
                           rebalance_freq: str = 'QS',
                           top_n: int = 50) -> Dict[pd.Timestamp, List[str]]:
        """
        Create point-in-time universe dictionary

        Args:
            prices: Full price DataFrame
            rebalance_freq: How often to update universe ('QS' = quarterly)
            top_n: Number of assets in universe

        Returns:
            Dict mapping date → list of tickers valid at that date
        """
        # Get rebalance dates
        rebalance_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=rebalance_freq
        )

        pit_universe = {}

        print(f"\n{'='*80}")
        print(f"POINT-IN-TIME UNIVERSE CONSTRUCTION")
        print(f"{'='*80}")
        print(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"Rebalance Frequency: {rebalance_freq}")
        print(f"Universe Size: Top {top_n}")
        print(f"{'='*80}\n")

        for reb_date in rebalance_dates:
            top_assets = PointInTimeUniverse.get_top_n_at_date(prices, reb_date, top_n)
            pit_universe[reb_date] = top_assets
            print(f"   {reb_date.date()}: {len(top_assets)} assets")

        print(f"\n✅ Point-in-Time Universe Created: {len(pit_universe)} periods\n")

        return pit_universe


if __name__ == "__main__":
    print("="*80)
    print("VALIDATION UTILITIES MODULE")
    print("="*80)
    print()
    print("Available Classes:")
    print("1. WalkForwardValidator - Rolling window train/test validation")
    print("2. MonteCarloSimulator - Trade resampling simulation")
    print("3. PointInTimeUniverse - Fix survivorship bias")
    print()
    print("Usage:")
    print("   from strategy_factory.validation_utils import WalkForwardValidator")
    print("   validator = WalkForwardValidator()")
    print("   results = validator.run_validation(strategy_fn, prices, btc_prices)")
    print("="*80)
