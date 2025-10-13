"""
Nick Radge Momentum Strategy - Crypto Adaptation

Key differences from stock version:
1. Faster parameters (30-day vs 100-day) - crypto moves faster
2. BTC as regime filter instead of SPY
3. USDT/stablecoins as bear asset instead of GLD
4. Weekly/monthly rebalancing instead of quarterly
5. Higher expected volatility (-30-50% drawdowns vs -15%)

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import vectorbt as vbt
import warnings
warnings.filterwarnings('ignore')


class NickRadgeCryptoStrategy:
    """
    Crypto-adapted momentum strategy with BSS ranking

    Modifications for crypto:
    - ROC period: 30 days (vs 100 for stocks)
    - MA period: 50 days (vs 100 for stocks)
    - Regime MA: 100/50 days (vs 200/50 for stocks)
    - Rebalance: Weekly/Monthly (vs Quarterly for stocks)
    - Bear asset: USDT (vs GLD for stocks)
    """

    def __init__(self,
                 portfolio_size: int = 7,
                 roc_period: int = 30,  # Faster for crypto
                 ma_period: int = 50,   # Faster for crypto
                 rebalance_freq: str = 'W-SUN',  # Weekly on Sundays
                 use_momentum_weighting: bool = True,
                 use_regime_filter: bool = True,
                 use_relative_strength: bool = False,  # DISABLED for crypto (too restrictive)
                 regime_ma_long: int = 100,  # BTC regime filter
                 regime_ma_short: int = 50,
                 strong_bull_positions: int = 7,
                 weak_bull_positions: int = 3,
                 bear_positions: int = 0,
                 bear_market_asset: str = 'USDT',  # Stablecoin
                 bear_allocation: float = 1.0):
        """
        Initialize Crypto Momentum Strategy

        Args:
            portfolio_size: Number of cryptos to hold (default: 7)
            roc_period: ROC lookback period (default: 30 days for crypto)
            ma_period: Moving average period (default: 50 days)
            rebalance_freq: 'W-SUN' (weekly), 'MS' (monthly start)
            use_momentum_weighting: Weight by momentum scores
            use_regime_filter: Use BTC 100MA/50MA regime filter
            regime_ma_long: Long MA for BTC regime (default: 100)
            regime_ma_short: Short MA for BTC regime (default: 50)
            strong_bull_positions: Positions in STRONG_BULL (default: 7)
            weak_bull_positions: Positions in WEAK_BULL (default: 3)
            bear_positions: Positions in BEAR (default: 0)
            bear_market_asset: Asset for bear market (default: USDT)
            bear_allocation: % allocation to bear asset (default: 100%)
        """
        self.portfolio_size = portfolio_size
        self.roc_period = roc_period
        self.ma_period = ma_period
        self.rebalance_freq = rebalance_freq
        self.use_momentum_weighting = use_momentum_weighting
        self.use_regime_filter = use_regime_filter
        self.use_relative_strength = use_relative_strength
        self.regime_ma_long = regime_ma_long
        self.regime_ma_short = regime_ma_short
        self.strong_bull_positions = strong_bull_positions
        self.weak_bull_positions = weak_bull_positions
        self.bear_positions = bear_positions
        self.bear_market_asset = bear_market_asset
        self.bear_allocation = bear_allocation

    def calculate_indicators(self, prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Calculate ROC and MA indicators"""
        roc = prices.pct_change(self.roc_period) * 100
        ma = prices.rolling(window=self.ma_period).mean()
        above_ma = prices > ma

        return {
            'roc': roc,
            'ma': ma,
            'above_ma': above_ma
        }

    def calculate_regime(self, btc_prices: pd.Series) -> pd.Series:
        """
        Calculate 3-tier market regime based on BTC

        Regimes:
        - STRONG_BULL: BTC > 100-day MA AND BTC > 50-day MA
        - WEAK_BULL: BTC > 100-day MA BUT BTC < 50-day MA
        - BEAR: BTC < 100-day MA
        """
        ma_long = btc_prices.rolling(window=self.regime_ma_long).mean()
        ma_short = btc_prices.rolling(window=self.regime_ma_short).mean()

        regime = pd.Series('UNKNOWN', index=btc_prices.index)

        # STRONG_BULL: Above both MAs
        regime[(btc_prices > ma_long) & (btc_prices > ma_short)] = 'STRONG_BULL'
        # WEAK_BULL: Above long MA but below short MA
        regime[(btc_prices > ma_long) & (btc_prices < ma_short)] = 'WEAK_BULL'
        # BEAR: Below long MA
        regime[btc_prices < ma_long] = 'BEAR'

        return regime

    def rank_cryptos(self,
                     prices: pd.DataFrame,
                     indicators: Dict[str, pd.DataFrame],
                     date: pd.Timestamp,
                     benchmark_roc: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Rank cryptos by momentum at given date

        Returns:
            DataFrame with top ranked cryptos and their ROC
        """
        if date not in prices.index:
            return pd.DataFrame()

        roc = indicators['roc'].loc[date]
        above_ma = indicators['above_ma'].loc[date]

        # Filter: Only cryptos above MA and with valid ROC
        valid_cryptos = above_ma[above_ma == True].index
        # Exclude bear market asset (USDT) from ranking
        if self.bear_market_asset:
            valid_cryptos = [c for c in valid_cryptos if c != self.bear_market_asset]
        valid_cryptos = [c for c in valid_cryptos if pd.notna(roc[c])]

        if len(valid_cryptos) == 0:
            return pd.DataFrame()

        # Get ROC for valid cryptos
        roc_valid = roc[valid_cryptos]
        roc_valid = roc_valid.dropna()

        if len(roc_valid) == 0:
            return pd.DataFrame()

        # Relative strength filter: Only cryptos outperforming BTC (if enabled)
        if self.use_relative_strength and benchmark_roc is not None and date in benchmark_roc.index:
            btc_roc = benchmark_roc.loc[date]
            if pd.notna(btc_roc):
                roc_valid = roc_valid[roc_valid > btc_roc]

        if len(roc_valid) == 0:
            return pd.DataFrame()

        # Sort by ROC (descending)
        ranked = roc_valid.sort_values(ascending=False)

        return pd.DataFrame({
            'ticker': ranked.index,
            'roc': ranked.values
        })

    def generate_allocations(self,
                           prices: pd.DataFrame,
                           btc_prices: Optional[pd.Series] = None,
                           benchmark_roc: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Generate portfolio allocations over time with regime filtering

        Args:
            prices: DataFrame with crypto prices (columns = tickers)
            btc_prices: BTC prices for regime filtering
            benchmark_roc: BTC ROC for relative strength

        Returns:
            DataFrame with allocation weights over time
        """
        print(f"\n📊 Calculating indicators for {len(prices.columns)} cryptos...")
        indicators = self.calculate_indicators(prices)

        # Calculate market regime if enabled
        regime = None
        if self.use_regime_filter and btc_prices is not None:
            print(f"   Calculating BTC market regime...")
            regime = self.calculate_regime(btc_prices)

            # Show regime summary
            regime_counts = regime.value_counts()
            total_days = len(regime)
            print(f"\n   BTC Market Regime Summary:")
            for reg, count in regime_counts.items():
                pct = (count / total_days) * 100
                print(f"   - {reg}: {count} days ({pct:.1f}%)")

        # Initialize allocations
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        # Determine rebalance dates
        ideal_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.rebalance_freq
        )

        # Find nearest trading day for each ideal date
        all_rebalance_dates = []
        for ideal_date in ideal_dates:
            nearest_idx = prices.index.searchsorted(ideal_date)
            if nearest_idx < len(prices.index):
                nearest_date = prices.index[nearest_idx]
                all_rebalance_dates.append(nearest_date)

        all_rebalance_dates = pd.DatetimeIndex(all_rebalance_dates).unique()

        # Skip early rebalances where we don't have enough data
        min_date = prices.index[0] + pd.Timedelta(days=max(self.roc_period, self.ma_period))
        rebalance_dates = all_rebalance_dates[all_rebalance_dates >= min_date]

        print(f"\n   Rebalances: {len(rebalance_dates)}")
        if len(rebalance_dates) > 0:
            print(f"   First rebalance: {rebalance_dates[0].date()}")
            print(f"   Last rebalance: {rebalance_dates[-1].date()}")

        # Process rebalances
        rebalance_set = set(rebalance_dates)
        current_weights = None

        for date in prices.index:
            if date < min_date:
                continue

            # Check current regime
            current_regime = None
            if self.use_regime_filter and regime is not None and date in regime.index:
                current_regime = regime.loc[date]

            # Determine if we should rebalance
            should_rebalance = date in rebalance_set

            if should_rebalance:
                # Determine position count based on regime
                target_positions = self.portfolio_size
                if self.use_regime_filter and current_regime is not None:
                    if current_regime == 'STRONG_BULL':
                        target_positions = self.strong_bull_positions
                    elif current_regime == 'WEAK_BULL':
                        target_positions = self.weak_bull_positions
                    elif current_regime == 'BEAR':
                        target_positions = self.bear_positions

                # BEAR regime: Allocate to bear asset
                if target_positions == 0 and self.bear_market_asset:
                    weights = pd.Series(0.0, index=prices.columns)
                    if self.bear_market_asset in weights.index:
                        weights[self.bear_market_asset] = self.bear_allocation
                    current_weights = weights
                else:
                    # Rank cryptos
                    ranked = self.rank_cryptos(prices, indicators, date, benchmark_roc)

                    if len(ranked) == 0:
                        current_weights = pd.Series(0.0, index=prices.columns)
                    else:
                        top_stocks = ranked.head(target_positions)

                        # Calculate weights
                        if self.use_momentum_weighting:
                            # Momentum weighting
                            positive_roc = top_stocks['roc'].clip(lower=0)
                            if positive_roc.sum() > 0:
                                weights_dict = (positive_roc / positive_roc.sum()).to_dict()
                            else:
                                # Equal weight if no positive momentum
                                weights_dict = {ticker: 1.0 / len(top_stocks)
                                              for ticker in top_stocks['ticker']}
                        else:
                            # Equal weight
                            weights_dict = {ticker: 1.0 / len(top_stocks)
                                          for ticker in top_stocks['ticker']}

                        weights = pd.Series(0.0, index=prices.columns)
                        for ticker, weight in weights_dict.items():
                            if ticker in weights.index:
                                weights[ticker] = weight

                        current_weights = weights

            # Apply current weights
            if current_weights is not None:
                allocations.loc[date] = current_weights

        # Show average positions
        avg_positions = (allocations > 0).sum(axis=1).mean()
        max_positions = (allocations > 0).sum(axis=1).max()
        print(f"\n   Avg positions held: {avg_positions:.1f}")
        print(f"   Max positions held: {max_positions:.0f}")

        return allocations

    def backtest(self,
                prices: pd.DataFrame,
                btc_prices: Optional[pd.Series] = None,
                initial_capital: float = 10000,
                fees: float = 0.001,
                slippage: float = 0.001) -> vbt.Portfolio:
        """
        Backtest the crypto strategy using vectorbt

        Args:
            prices: DataFrame with crypto prices (columns = tickers)
            btc_prices: BTC prices for regime filtering
            initial_capital: Starting capital
            fees: Trading fees (0.001 = 0.1%, typical for CEX)
            slippage: Slippage (0.001 = 0.1%, higher for crypto)

        Returns:
            vectorbt Portfolio object
        """
        print(f"\n📊 Running Nick Radge Crypto Strategy...")
        print(f"   Universe: {len(prices.columns)} cryptos")
        print(f"   Portfolio Size: {self.portfolio_size} positions")
        print(f"   Rebalance: {self.rebalance_freq}")
        print(f"   Momentum Weighting: {self.use_momentum_weighting}")
        print(f"   Regime Filter: {self.use_regime_filter}")
        print(f"   Relative Strength: {self.use_relative_strength}")

        # Calculate benchmark ROC
        benchmark_roc = None
        if btc_prices is not None:
            benchmark_roc = btc_prices.pct_change(self.roc_period) * 100

        # Generate allocations
        allocations = self.generate_allocations(prices, btc_prices, benchmark_roc)

        # Align prices and allocations
        common_idx = prices.index.intersection(allocations.index)
        common_cols = prices.columns.intersection(allocations.columns)

        prices_aligned = prices.loc[common_idx, common_cols]
        allocations_aligned = allocations.loc[common_idx, common_cols]

        print(f"\n📈 Running vectorbt backtest...")

        # Create portfolio
        portfolio = vbt.Portfolio.from_orders(
            close=prices_aligned,
            size=allocations_aligned,
            size_type='targetpercent',
            init_cash=initial_capital,
            fees=fees,
            slippage=slippage,
            group_by=True,
            cash_sharing=True,
            freq='D'  # Specify daily frequency
        )

        return portfolio

    def print_results(self, portfolio: vbt.Portfolio):
        """Print backtest results"""
        total_return = portfolio.total_return() * 100
        sharpe = portfolio.sharpe_ratio(freq='D')
        max_dd = portfolio.max_drawdown() * 100

        print(f"\n{'='*70}")
        print(f"📊 CRYPTO STRATEGY RESULTS")
        print(f"{'='*70}")
        print(f"Total Return:    {total_return:>10.2f}%")
        print(f"Sharpe Ratio:    {sharpe:>10.2f}")
        print(f"Max Drawdown:    {max_dd:>10.2f}%")
        print(f"Final Value:     ${portfolio.total_profit() + portfolio.init_cash:>10,.2f}")
        print(f"{'='*70}\n")
