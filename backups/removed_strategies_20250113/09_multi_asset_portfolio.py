#!/usr/bin/env python3
"""
Multi-Asset Portfolio Strategy

Scans a universe of assets and dynamically allocates capital based on:
- Momentum ranking
- Volatility adjustment
- Periodic rebalancing
- Risk parity allocation
- Equal weight / Market cap weight

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Tuple
from pathlib import Path


class MultiAssetPortfolioStrategy:
    """
    Multi-Asset Portfolio Strategy

    Features:
    - Scans multiple assets
    - Ranks by momentum/volatility/other factors
    - Dynamically allocates capital
    - Rebalances periodically
    - Multiple allocation methods

    Parameters:
        allocation_method: 'equal_weight', 'momentum', 'risk_parity', 'min_variance'
        rebalance_freq: Rebalancing frequency ('D', 'W', 'M', 'Q')
        top_n: Number of assets to hold (if None, holds all)
        lookback_period: Lookback for momentum/volatility calculation
        min_momentum: Minimum momentum threshold to enter
        max_assets: Maximum number of assets to hold
    """

    def __init__(self,
                 allocation_method: str = 'momentum',
                 rebalance_freq: str = 'W',
                 top_n: int = 5,
                 lookback_period: int = 100,
                 min_momentum: float = 0.0,
                 max_assets: int = 10):

        self.allocation_method = allocation_method
        self.rebalance_freq = rebalance_freq
        self.top_n = top_n
        self.lookback_period = lookback_period
        self.min_momentum = min_momentum
        self.max_assets = max_assets
        self.name = f"MultiAsset_{allocation_method}_{rebalance_freq}"

    def calculate_momentum(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum for each asset

        Args:
            prices: DataFrame with asset prices (columns = assets)

        Returns:
            DataFrame with momentum scores
        """
        # Simple momentum = % return over lookback period
        momentum = prices.pct_change(self.lookback_period)
        return momentum

    def calculate_volatility(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volatility for each asset

        Args:
            prices: DataFrame with asset prices

        Returns:
            DataFrame with volatility scores
        """
        returns = prices.pct_change()
        volatility = returns.rolling(self.lookback_period).std()
        return volatility

    def rank_assets(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Rank assets by momentum

        Args:
            prices: DataFrame with asset prices

        Returns:
            DataFrame with ranks (1 = best, N = worst)
        """
        momentum = self.calculate_momentum(prices)

        # Rank assets (higher momentum = lower rank number)
        ranks = momentum.rank(axis=1, ascending=False)

        return ranks

    def calculate_equal_weight_allocation(self,
                                         prices: pd.DataFrame,
                                         rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Equal weight allocation across top N assets
        """
        ranks = self.rank_assets(prices)
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        for date in rebalance_dates:
            if date not in ranks.index:
                continue

            # Get top N assets by momentum
            rank_row = ranks.loc[date]
            top_assets = rank_row.nsmallest(self.top_n).index

            # Filter by minimum momentum
            momentum = self.calculate_momentum(prices).loc[date]
            valid_assets = [a for a in top_assets if momentum[a] >= self.min_momentum]

            if len(valid_assets) == 0:
                continue

            # Equal weight allocation
            weight = 1.0 / len(valid_assets)

            # Forward fill until next rebalance
            next_rebalance_idx = rebalance_dates.get_loc(date) + 1
            if next_rebalance_idx < len(rebalance_dates):
                end_date = rebalance_dates[next_rebalance_idx]
            else:
                end_date = prices.index[-1]

            mask = (allocations.index >= date) & (allocations.index < end_date)
            allocations.loc[mask, valid_assets] = weight

        return allocations

    def calculate_momentum_allocation(self,
                                     prices: pd.DataFrame,
                                     rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Momentum-weighted allocation (higher momentum = more weight)
        """
        momentum = self.calculate_momentum(prices)
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        for date in rebalance_dates:
            if date not in momentum.index:
                continue

            # Get top N assets by momentum
            mom_row = momentum.loc[date]
            top_assets = mom_row.nlargest(self.top_n).index

            # Filter by minimum momentum
            valid_assets = [a for a in top_assets if mom_row[a] >= self.min_momentum]

            if len(valid_assets) == 0:
                continue

            # Weight by momentum (normalized)
            mom_values = mom_row[valid_assets]
            mom_values = mom_values.clip(lower=0)  # Only positive momentum

            if mom_values.sum() == 0:
                continue

            weights = mom_values / mom_values.sum()

            # Forward fill
            next_rebalance_idx = rebalance_dates.get_loc(date) + 1
            if next_rebalance_idx < len(rebalance_dates):
                end_date = rebalance_dates[next_rebalance_idx]
            else:
                end_date = prices.index[-1]

            mask = (allocations.index >= date) & (allocations.index < end_date)
            for asset in valid_assets:
                allocations.loc[mask, asset] = weights[asset]

        return allocations

    def calculate_risk_parity_allocation(self,
                                        prices: pd.DataFrame,
                                        rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Risk parity allocation (inverse volatility weighting)
        Lower volatility = higher allocation
        """
        volatility = self.calculate_volatility(prices)
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        for date in rebalance_dates:
            if date not in volatility.index:
                continue

            vol_row = volatility.loc[date]

            # Get top N by momentum, then weight by inverse volatility
            momentum = self.calculate_momentum(prices).loc[date]
            top_assets = momentum.nlargest(self.top_n).index

            valid_assets = [a for a in top_assets if momentum[a] >= self.min_momentum]

            if len(valid_assets) == 0:
                continue

            # Inverse volatility weights
            inv_vol = 1.0 / vol_row[valid_assets]
            inv_vol = inv_vol.fillna(0)

            if inv_vol.sum() == 0:
                continue

            weights = inv_vol / inv_vol.sum()

            # Forward fill
            next_rebalance_idx = rebalance_dates.get_loc(date) + 1
            if next_rebalance_idx < len(rebalance_dates):
                end_date = rebalance_dates[next_rebalance_idx]
            else:
                end_date = prices.index[-1]

            mask = (allocations.index >= date) & (allocations.index < end_date)
            for asset in valid_assets:
                allocations.loc[mask, asset] = weights[asset]

        return allocations

    def generate_allocations(self, prices: pd.DataFrame) -> pd.DataFrame:
        """
        Generate portfolio allocations over time

        Args:
            prices: DataFrame with asset prices (columns = asset names)

        Returns:
            DataFrame with allocation weights over time
        """
        # Determine rebalance dates
        rebalance_dates = prices.resample(self.rebalance_freq).last().index
        rebalance_dates = rebalance_dates[rebalance_dates.isin(prices.index)]

        print(f"   Rebalancing {len(rebalance_dates)} times ({self.rebalance_freq} frequency)")

        # Calculate allocations based on method
        if self.allocation_method == 'equal_weight':
            allocations = self.calculate_equal_weight_allocation(prices, rebalance_dates)
        elif self.allocation_method == 'momentum':
            allocations = self.calculate_momentum_allocation(prices, rebalance_dates)
        elif self.allocation_method == 'risk_parity':
            allocations = self.calculate_risk_parity_allocation(prices, rebalance_dates)
        else:
            raise ValueError(f"Unknown allocation method: {self.allocation_method}")

        return allocations

    def backtest(self, prices: pd.DataFrame, initial_capital: float = 10000) -> vbt.Portfolio:
        """
        Backtest the multi-asset portfolio strategy

        Args:
            prices: DataFrame with asset prices (columns = asset names)
            initial_capital: Starting capital

        Returns:
            vectorbt Portfolio object
        """
        print(f"\n📊 Scanning {len(prices.columns)} assets...")
        print(f"   Allocation method: {self.allocation_method}")
        print(f"   Top N holdings: {self.top_n}")
        print(f"   Lookback period: {self.lookback_period}")

        # Generate allocations
        allocations = self.generate_allocations(prices)

        # Count active positions
        active_positions = (allocations > 0).sum(axis=1)
        print(f"   Avg positions held: {active_positions.mean():.1f}")
        print(f"   Max positions held: {active_positions.max():.0f}")

        # Run portfolio backtest with vectorbt
        portfolio = vbt.Portfolio.from_orders(
            close=prices,
            size=allocations,
            size_type='targetpercent',  # Allocations are target percentages
            init_cash=initial_capital,
            fees=0.001,  # 0.1% trading fee
            slippage=0.0005  # 0.05% slippage
        )

        return portfolio

    def print_results(self, portfolio: vbt.Portfolio, prices: pd.DataFrame):
        """Print backtest results"""
        print("\n" + "="*80)
        print("MULTI-ASSET PORTFOLIO - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Universe: {len(prices.columns)} assets")
        print(f"   Period: {prices.index[0]} to {prices.index[-1]}")

        # Get scalar metrics (for multi-asset portfolios, sum across assets)
        final_value = portfolio.value().iloc[-1].sum() if isinstance(portfolio.value().iloc[-1], pd.Series) else portfolio.value().iloc[-1]
        init_cash = portfolio.init_cash.sum() if isinstance(portfolio.init_cash, pd.Series) else portfolio.init_cash
        total_return = (final_value / init_cash) - 1

        sharpe = portfolio.sharpe_ratio(freq='5min')
        if isinstance(sharpe, pd.Series):
            sharpe = sharpe.mean()

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max()

        print(f"\n📈 Performance:")
        print(f"   Total Return: {total_return * 100:.2f}%")
        print(f"   Final Equity: ${final_value:,.2f}")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_dd * 100:.2f}%")

        print(f"\n💼 Trading:")
        trades_count = portfolio.trades.count()
        if isinstance(trades_count, pd.Series):
            trades_count = trades_count.sum()
        print(f"   Total Trades: {trades_count}")

        if trades_count > 0:
            win_rate = portfolio.trades.win_rate()
            if isinstance(win_rate, pd.Series):
                win_rate = win_rate.mean()
            print(f"   Win Rate: {win_rate * 100:.1f}%")

            try:
                avg_win = portfolio.trades.winning.pnl.mean()
                if isinstance(avg_win, pd.Series):
                    avg_win = avg_win.mean()
                print(f"   Avg Win: ${avg_win:.2f}")
            except:
                pass

            try:
                avg_loss = portfolio.trades.losing.pnl.mean()
                if isinstance(avg_loss, pd.Series):
                    avg_loss = avg_loss.mean()
                print(f"   Avg Loss: ${avg_loss:.2f}")
            except:
                pass

        print("\n" + "="*80)

    def __str__(self):
        return f"Multi-Asset Portfolio ({self.allocation_method}, {self.top_n} assets, {self.rebalance_freq} rebal)"


def load_multiple_assets(asset_files: List[str]) -> pd.DataFrame:
    """
    Load multiple asset CSV files and combine into single DataFrame

    Args:
        asset_files: List of file paths to CSV files

    Returns:
        DataFrame with columns = asset names, index = timestamp
    """
    prices_dict = {}

    for file_path in asset_files:
        # Extract asset name from filename
        asset_name = Path(file_path).stem.split('_')[0]

        # Load data
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.lower()

        if 'date' in df.columns:
            df = df.rename(columns={'date': 'timestamp'})

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')

        # Remove duplicate timestamps (keep last)
        df = df[~df.index.duplicated(keep='last')]

        # Use close price
        prices_dict[asset_name] = df['close']

    # Combine into single DataFrame
    prices = pd.DataFrame(prices_dict)

    # Forward fill missing values
    prices = prices.ffill()

    # Drop rows with any remaining NaN
    prices = prices.dropna()

    return prices


if __name__ == "__main__":
    print("="*80)
    print("EXAMPLE: MULTI-ASSET PORTFOLIO STRATEGY")
    print("="*80)

    # Load multiple crypto assets
    print("\n📂 Loading asset universe...")

    asset_files = [
        'data/crypto/BTCUSD_5m.csv',
        'data/crypto/ADAUSD_5m.csv',
        # Add more assets here
    ]

    prices = load_multiple_assets(asset_files)

    # Use recent data for speed
    prices = prices.tail(50000)

    print(f"✅ Loaded {len(prices.columns)} assets: {list(prices.columns)}")
    print(f"   Period: {prices.index[0]} to {prices.index[-1]}")
    print(f"   Total bars: {len(prices):,}")

    # Test different allocation methods
    methods = ['equal_weight', 'momentum', 'risk_parity']

    for method in methods:
        print(f"\n{'='*80}")
        print(f"TESTING: {method.upper()}")
        print(f"{'='*80}")

        # Create strategy
        strategy = MultiAssetPortfolioStrategy(
            allocation_method=method,
            rebalance_freq='W',  # Weekly rebalancing
            top_n=2,  # Hold top 2 assets (since we only have 2)
            lookback_period=500,  # ~40 hours lookback
            min_momentum=0.0
        )

        # Run backtest
        portfolio = strategy.backtest(prices, initial_capital=10000)

        # Print results
        strategy.print_results(portfolio, prices)

    print("\n" + "="*80)
    print("✅ Multi-asset portfolio testing complete!")
    print("\nKey Features Demonstrated:")
    print("   ✓ Scan multiple assets")
    print("   ✓ Dynamic position sizing")
    print("   ✓ Periodic rebalancing")
    print("   ✓ Multiple allocation methods")
    print("   ✓ Risk-adjusted weighting")
    print("="*80 + "\n")
