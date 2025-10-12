#!/usr/bin/env python3
"""
Nick Radge Momentum Strategy - Enhanced with ATR-Based Qualifiers

Extends original Nick Radge strategy with Tomas Nesnidal's ATR-based
performance qualifiers for stock ranking.

Supports multiple ranking methods:
- ROC (original)
- ATR-Normalized Momentum (ANM)
- Breakout Strength Score (BSS)
- Volatility Expansion Momentum (VEM)
- Trend Quality Score (TQS)
- Risk-Adjusted Momentum (RAM)
- Composite Score (weighted combination)

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, Optional, Union
from dataclasses import dataclass

from strategy_factory.performance_qualifiers import get_qualifier

# Import SizeType at module level
try:
    from vectorbt.portfolio.enums import SizeType
except ImportError:
    # Fallback for different vectorbt versions
    SizeType = None


def apply_weight_constraints(weights: pd.DataFrame,
                             max_position: float,
                             max_total: float = 1.0) -> pd.DataFrame:
    """Cap per-position exposure and optionally overall leverage while preserving cash."""
    constrained = weights.clip(lower=0.0, upper=max_position)

    if max_total is not None:
        row_sums = constrained.sum(axis=1)
        factors = pd.Series(
            np.where(row_sums > max_total, row_sums, max_total),
            index=row_sums.index
        )
        constrained = constrained.div(factors, axis=0)

    return constrained.fillna(0.0)


@dataclass
class PortfolioResult:
    """Lightweight container for backtest results."""
    equity_curve: pd.Series
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    initial_capital: float

    @property
    def final_value(self) -> float:
        return float(self.equity_curve.iloc[-1])

    @property
    def init_cash(self) -> float:
        return self.initial_capital

    def total_return(self) -> float:
        return (self.final_value / self.initial_capital) - 1.0

    def sharpe_ratio(self, freq: str = 'D') -> float:
        std = self.returns.std()
        if std == 0 or np.isnan(std):
            return 0.0
        annualization = {
            'D': np.sqrt(252),
            'W': np.sqrt(52),
            'M': np.sqrt(12)
        }.get(freq.upper(), np.sqrt(252))
        return float((self.returns.mean() / std) * annualization)

    def max_drawdown(self) -> float:
        running_max = self.equity_curve.cummax()
        drawdown = self.equity_curve / running_max - 1.0
        return float(drawdown.min())

    def trade_days(self, threshold: float = 1e-6) -> int:
        """Approximate number of trading days based on non-zero turnover."""
        return int((self.turnover.abs() > threshold).sum())


class NickRadgeEnhanced:
    """
    Nick Radge Momentum Strategy with ATR-Based Qualifiers

    Features:
    - Flexible ranking system (ROC, ANM, BSS, VEM, TQS, RAM, Composite)
    - Market regime filtering (3-tier: Strong Bull, Weak Bull, Bear)
    - Momentum-weighted allocation
    - Quarterly rebalancing
    - Bear market asset support (GLD)
    """

    def __init__(self,
                 portfolio_size: int = 7,
                 qualifier_type: str = 'roc',
                 ma_period: int = 100,
                 rebalance_freq: str = 'QS',
                 use_momentum_weighting: bool = True,
                 use_regime_filter: bool = True,
                 use_relative_strength: bool = True,
                 regime_ma_long: int = 200,
                 regime_ma_short: int = 50,
                 strong_bull_positions: int = 7,
                 weak_bull_positions: int = 3,
                 bear_positions: int = 0,
                 bear_market_asset: Optional[str] = None,
                 bear_allocation: float = 1.0,
                 qualifier_params: Optional[Dict] = None):
        """
        Initialize Enhanced Nick Radge Strategy

        Args:
            portfolio_size: Number of stocks to hold (default: 7)
            qualifier_type: Ranking method - 'roc', 'anm', 'bss', 'vem', 'tqs', 'ram', 'composite'
            ma_period: Moving average trend filter (default: 100)
            rebalance_freq: Rebalancing frequency ('QS' = quarterly)
            use_momentum_weighting: Weight positions by momentum strength
            use_regime_filter: Enable 3-tier regime-based adjustments
            use_relative_strength: Only buy stocks outperforming SPY
            regime_ma_long: Long-term MA for regime (200 days)
            regime_ma_short: Short-term MA for regime (50 days)
            strong_bull_positions: Positions in strong bull market
            weak_bull_positions: Positions in weak bull market
            bear_positions: Positions in bear market (0 = cash)
            bear_market_asset: Ticker to trade during BEAR (e.g., 'GLD')
            bear_allocation: Allocation % for bear asset (1.0 = 100%)
            qualifier_params: Additional parameters for qualifier (optional)
        """
        self.portfolio_size = portfolio_size
        self.qualifier_type = qualifier_type
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

        # Initialize performance qualifier
        params = qualifier_params or {}
        self.qualifier = get_qualifier(qualifier_type, **params)

        self.name = f"NickRadge_Enhanced_{qualifier_type.upper()}_Top{portfolio_size}"

    def calculate_indicators(self, prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Calculate indicators for all stocks

        IMPORTANT: All indicators are lagged by 1 day to prevent look-ahead bias.
        We use t-1 data to make decisions that execute at t.

        Args:
            prices: DataFrame with stock prices (columns = tickers)

        Returns:
            Dictionary with indicator DataFrames
        """
        # Calculate performance scores using selected qualifier
        # CRITICAL: Shift by 1 to prevent look-ahead bias
        scores = self.qualifier.calculate(prices).shift(1)

        # Calculate Moving Average on lagged prices
        ma = prices.rolling(window=self.ma_period).mean().shift(1)

        # Trend filter: Above MA (using lagged data)
        above_ma = (prices.shift(1) > ma)

        return {
            'scores': scores,
            'ma': ma,
            'above_ma': above_ma
        }

    def calculate_regime(self, spy_prices: pd.Series) -> pd.Series:
        """
        Calculate 3-tier market regime based on SPY

        IMPORTANT: Regime is lagged by 1 day to prevent look-ahead bias.

        Regimes:
        - STRONG_BULL: SPY > 200-day MA and SPY > 50-day MA
        - WEAK_BULL: SPY > 200-day MA but SPY < 50-day MA
        - BEAR: SPY < 200-day MA

        Args:
            spy_prices: SPY close prices

        Returns:
            Series with regime classification
        """
        # Lag MAs by 1 day to prevent look-ahead bias
        ma_long = spy_prices.rolling(window=self.regime_ma_long).mean().shift(1)
        ma_short = spy_prices.rolling(window=self.regime_ma_short).mean().shift(1)
        prices_lagged = spy_prices.shift(1)

        regime = pd.Series('UNKNOWN', index=spy_prices.index)

        # Classification using lagged data
        regime[(prices_lagged > ma_long) & (prices_lagged > ma_short)] = 'STRONG_BULL'
        regime[(prices_lagged > ma_long) & (prices_lagged <= ma_short)] = 'WEAK_BULL'
        regime[prices_lagged <= ma_long] = 'BEAR'

        return regime

    def rank_stocks(self,
                   prices: pd.DataFrame,
                   indicators: Dict[str, pd.DataFrame],
                   date: pd.Timestamp,
                   benchmark_scores: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Rank stocks by performance qualifier at given date

        Args:
            prices: Stock prices DataFrame
            indicators: Dictionary of indicator DataFrames
            date: Date to rank stocks
            benchmark_scores: SPY scores for relative strength filter

        Returns:
            DataFrame with top ranked stocks and their scores
        """
        if date not in prices.index:
            return pd.DataFrame()

        scores = indicators['scores'].loc[date]
        above_ma = indicators['above_ma'].loc[date]

        # Filter: Only stocks above MA and with valid scores
        valid_stocks = above_ma[above_ma == True].index

        # Exclude bear market asset from stock ranking
        if self.bear_market_asset:
            valid_stocks = [s for s in valid_stocks if s != self.bear_market_asset]

        valid_stocks = [s for s in valid_stocks if pd.notna(scores[s])]

        if len(valid_stocks) == 0:
            return pd.DataFrame()

        # Get scores for valid stocks
        scores_valid = scores[valid_stocks].dropna()

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Relative strength filter: Only stocks outperforming SPY
        if self.use_relative_strength and benchmark_scores is not None and date in benchmark_scores.index:
            spy_score = benchmark_scores.loc[date]
            if pd.notna(spy_score):
                scores_valid = scores_valid[scores_valid > spy_score]

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Sort by score (descending)
        ranked = scores_valid.sort_values(ascending=False)

        return pd.DataFrame({
            'ticker': ranked.index,
            'score': ranked.values
        })

    def generate_allocations(self,
                           prices: pd.DataFrame,
                           spy_prices: Optional[pd.Series] = None,
                           benchmark_scores: Optional[pd.Series] = None,
                           enable_regime_recovery: bool = True) -> pd.DataFrame:
        """
        Generate portfolio allocations over time with regime recovery

        Args:
            prices: DataFrame with stock prices (columns = tickers)
            spy_prices: SPY prices for regime filtering
            benchmark_scores: SPY scores for relative strength
            enable_regime_recovery: If True, re-enter positions when BEAR -> BULL

        Returns:
            DataFrame with allocation weights over time
        """
        print(f"\n📊 Calculating indicators for {len(prices.columns)} stocks...")
        print(f"   Using qualifier: {self.qualifier.name}")

        indicators = self.calculate_indicators(prices)

        # Calculate market regime if enabled
        regime = None
        if self.use_regime_filter and spy_prices is not None:
            print(f"   Calculating market regime...")
            regime = self.calculate_regime(spy_prices)

            # Show regime summary
            regime_counts = regime.value_counts()
            total_days = len(regime)
            print(f"\n   Market Regime Summary:")
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
        min_date = prices.index[0] + pd.Timedelta(days=self.ma_period)
        rebalance_dates = all_rebalance_dates[all_rebalance_dates >= min_date]

        print(f"\n   Quarterly rebalances: {len(rebalance_dates)}")
        if len(rebalance_dates) > 0:
            print(f"   First rebalance: {rebalance_dates[0].date()}")
            print(f"   Last rebalance: {rebalance_dates[-1].date()}")

        # Track current allocations and last regime
        current_weights = None
        last_regime = None
        regime_recoveries = 0

        # Process day by day for regime recovery
        rebalance_set = set(rebalance_dates)

        for date in prices.index:
            if date < min_date:
                continue

            # Check current regime
            current_regime = None
            if self.use_regime_filter and regime is not None and date in regime.index:
                current_regime = regime.loc[date]

            # Detect regime recovery (BEAR -> BULL)
            # Check if we're in bear-only portfolio (holding only bear asset like GLD)
            is_bear_only = False
            if current_weights is not None and self.bear_market_asset:
                is_bear_only = (
                    set(current_weights.index) == {self.bear_market_asset} and
                    current_weights.iloc[0] > 0
                )

            is_regime_recovery = False
            if (enable_regime_recovery and
                last_regime == 'BEAR' and
                current_regime in ['STRONG_BULL', 'WEAK_BULL'] and
                (current_weights is None or is_bear_only)):
                is_regime_recovery = True
                regime_recoveries += 1
                print(f"   🔄 Regime recovery on {date.date()} - Re-entering positions early")

            # Determine if we should rebalance
            is_rebalance_date = date in rebalance_set

            if is_rebalance_date or is_regime_recovery:
                # Determine portfolio size based on regime
                portfolio_size = self.portfolio_size

                if self.use_regime_filter and current_regime is not None:
                    if current_regime == 'STRONG_BULL':
                        portfolio_size = self.strong_bull_positions
                    elif current_regime == 'WEAK_BULL':
                        portfolio_size = self.weak_bull_positions
                    else:  # BEAR or UNKNOWN
                        portfolio_size = self.bear_positions

                # If bear market, go to cash OR bear market asset
                if portfolio_size == 0:
                    if self.bear_market_asset and self.bear_market_asset in allocations.columns:
                        # Allocate to bear market asset
                        allocations.loc[date, :] = 0.0
                        allocations.loc[date, self.bear_market_asset] = self.bear_allocation
                        current_weights = pd.Series({self.bear_market_asset: self.bear_allocation})
                    else:
                        # Go to cash
                        current_weights = None
                        allocations.loc[date, :] = 0.0
                else:
                    # Rank stocks by performance qualifier
                    ranked = self.rank_stocks(prices, indicators, date, benchmark_scores)

                    if len(ranked) > 0:
                        # Select top N stocks
                        top_stocks = ranked.head(portfolio_size)

                        # Calculate allocation weights
                        if self.use_momentum_weighting:
                            # Weight by score (clip at 0 for safety)
                            positive_scores = top_stocks['score'].clip(lower=0)
                            total_score = positive_scores.sum()

                            if total_score > 0:
                                weights = positive_scores / total_score
                                weights.index = top_stocks['ticker'].values
                            else:
                                weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)
                        else:
                            # Equal weight
                            weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)

                        current_weights = weights

                        # Apply weights
                        for ticker in allocations.columns:
                            allocations.loc[date, ticker] = weights.get(ticker, 0.0)
                    else:
                        current_weights = None
                        allocations.loc[date, :] = 0.0
            else:
                # Between rebalances - maintain current positions
                if current_weights is not None:
                    for ticker in allocations.columns:
                        allocations.loc[date, ticker] = current_weights.get(ticker, 0.0)
                else:
                    allocations.loc[date, :] = 0.0

            last_regime = current_regime

        if regime_recoveries > 0:
            print(f"   Total regime recoveries: {regime_recoveries}")

        return allocations

    def backtest(self,
                prices: pd.DataFrame,
                spy_prices: Optional[pd.Series] = None,
                initial_capital: float = 10000,
                fees: float = 0.001,
                slippage: float = 0.0005):
        """
        Backtest the strategy using vectorbt Portfolio

        Args:
            prices: DataFrame with stock prices (columns = tickers)
            spy_prices: SPY prices for regime filtering
            initial_capital: Starting capital
            fees: Trading fees (0.001 = 0.1%)
            slippage: Slippage (0.0005 = 0.05%)

        Returns:
            vectorbt Portfolio object with full backtest results
        """
        print(f"\n📊 Running Nick Radge Enhanced Strategy...")
        print(f"   Qualifier: {self.qualifier.name}")
        print(f"   Universe: {len(prices.columns)} stocks")
        print(f"   Portfolio Size: {self.portfolio_size} positions")
        print(f"   Rebalance: {self.rebalance_freq}")
        print(f"   Momentum Weighting: {self.use_momentum_weighting}")
        print(f"   Regime Filter: {self.use_regime_filter}")
        print(f"   Relative Strength: {self.use_relative_strength}")

        # Calculate benchmark scores if using relative strength
        # CRITICAL: Shift by 1 to prevent look-ahead bias
        benchmark_scores = None
        if self.use_relative_strength and spy_prices is not None:
            spy_df = spy_prices.to_frame(name='SPY')
            benchmark_scores = self.qualifier.calculate(spy_df)['SPY'].shift(1)

        # Generate allocations
        allocations = self.generate_allocations(prices, spy_prices, benchmark_scores)

        # Calculate rebalance dates for vol targeting
        ideal_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.rebalance_freq
        )
        all_rebalance_dates = []
        for ideal_date in ideal_dates:
            nearest_idx = prices.index.searchsorted(ideal_date)
            if nearest_idx < len(prices.index):
                nearest_date = prices.index[int(nearest_idx)]
                all_rebalance_dates.append(nearest_date)
        rebalance_dates = pd.DatetimeIndex(all_rebalance_dates).unique()

        # Ensure allocations and prices have same index AND columns
        common_idx = prices.index.intersection(allocations.index)
        common_cols = prices.columns.intersection(allocations.columns)

        prices_aligned = prices.loc[common_idx, common_cols]
        allocations_aligned = allocations.loc[common_idx, common_cols]

        # NOTE: We DON'T shift allocations when using vectorbt!
        # Vectorbt executes orders at the close of each bar automatically
        # Our allocations already have look-ahead bias removed (calculated with t-1 data)

        # CONCENTRATION LIMITS: Cap any single position at 25%
        max_position_weight = 0.25
        allocations_aligned = apply_weight_constraints(
            allocations_aligned,
            max_position=max_position_weight,
            max_total=1.0
        )

        # VOLATILITY TARGETING: Scale portfolio to target ~20% annual volatility
        # Calculate simple portfolio returns for vol estimation
        returns = prices_aligned.pct_change().fillna(0)
        port_ret_for_vol = (returns * allocations_aligned).sum(axis=1)

        # 20-day realized vol estimate
        realized_vol = port_ret_for_vol.rolling(window=20).std() * np.sqrt(252)
        target_vol = 0.20  # 20% annual

        # Vol scalar (clip to prevent extreme leverage)
        vol_scalar = (target_vol / realized_vol.replace(0, np.nan)).clip(lower=0.0, upper=2.0).fillna(1.0)

        # Apply volatility scaling ONLY on rebalance dates to reduce turnover
        rebalance_mask = pd.Series(False, index=allocations_aligned.index)
        rebalance_mask.loc[rebalance_dates] = True

        # Scale only on rebalance dates, forward-fill the scalar
        vol_scalar_rebalance = vol_scalar.where(rebalance_mask).ffill().fillna(1.0)
        allocations_aligned = allocations_aligned.mul(vol_scalar_rebalance, axis=0)

        # Re-apply constraints after scaling
        allocations_aligned = apply_weight_constraints(
            allocations_aligned,
            max_position=max_position_weight,
            max_total=1.0
        )

        # TURNOVER & POSITION STATS
        turnover = allocations_aligned.diff().abs().sum(axis=1).fillna(0)
        avg_turnover = turnover.mean()
        median_turnover = turnover.median()
        max_turnover = turnover.max()

        active_positions = (allocations_aligned > 0).sum(axis=1)
        print(f"\n   Avg positions held: {active_positions.mean():.1f}")
        print(f"   Max positions held: {active_positions.max():.0f}")

        print(f"\n💸 Turnover Analysis:")
        print(f"   Avg daily turnover: {avg_turnover:.3f}")
        print(f"   Median daily turnover: {median_turnover:.3f}")
        print(f"   Max daily turnover: {max_turnover:.3f}")
        if avg_turnover > 0.15:
            print("   ⚠️  High turnover detected - consider increasing fees/slippage")

        # PORTFOLIO SIMULATION using vectorbt
        # Use vectorbt's from_orders with TargetPercent
        # This handles the portfolio rebalancing and tracks all metrics properly
        portfolio = vbt.Portfolio.from_orders(
            close=prices_aligned,
            size=allocations_aligned,  # Already in 0-1 range, vectorbt handles it
            size_type='targetpercent',
            fees=fees,
            slippage=slippage,
            init_cash=initial_capital,
            cash_sharing=True,  # Share cash across all assets
            group_by=True,  # Treat as single portfolio
            call_seq='auto'  # Optimize order execution
        )

        print(f"\n✅ Vectorbt Portfolio Created Successfully")
        print(f"   Final Value: ${portfolio.final_value():,.2f}")
        print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
        try:
            print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='D'):.2f}")
        except:
            print(f"   Sharpe Ratio: (calculation error)")

        return portfolio

    def print_results(self, portfolio, prices: pd.DataFrame, spy_return: Optional[float] = None):
        """Print backtest results from vectorbt Portfolio"""
        print("\n" + "="*80)
        print("NICK RADGE ENHANCED STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Qualifier: {self.qualifier.name}")
        print(f"   Universe: {len(prices.columns)} stocks")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        if self.bear_market_asset:
            print(f"   Bear Market Asset: {self.bear_market_asset} ({self.bear_allocation*100:.0f}% allocation)")

        # Get metrics from vectorbt Portfolio (all are methods!)
        final_value = portfolio.final_value()
        total_return = portfolio.total_return() * 100
        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
        except:
            sharpe = 0.0
        max_dd = portfolio.max_drawdown()

        print(f"\n📈 Performance:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Final Equity: ${final_value:,.2f}")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_dd * 100:.2f}%")

        if spy_return is not None:
            print(f"\n📊 vs SPY Buy & Hold:")
            print(f"   SPY Return: {spy_return:.2f}%")
            print(f"   Outperformance: {total_return - spy_return:+.2f}%")
            if total_return > spy_return:
                print(f"   Status: ✅ OUTPERFORMED")
            else:
                print(f"   Status: ❌ UNDERPERFORMED")

        print(f"\n💼 Trading Activity:")
        # Get returns for win rate calculation
        returns = portfolio.returns()
        daily_win_rate = (returns > 0).mean() * 100
        print(f"   Daily Win Rate: {daily_win_rate:.1f}%")

        # Calculate profit factor
        profit_factor = np.nan
        gains = returns[returns > 0].sum()
        losses = -returns[returns < 0].sum()
        if losses > 0:
            profit_factor = gains / losses
            print(f"   Daily Profit Factor: {profit_factor:.2f}")
        else:
            print(f"   Daily Profit Factor: N/A")

        print("\n" + "="*80)


if __name__ == "__main__":
    print("="*80)
    print("NICK RADGE ENHANCED - ATR-BASED QUALIFIERS")
    print("="*80)

    print("\n⚙️  This script demonstrates the enhanced strategy with different qualifiers")
    print("    See examples/test_nick_radge_qualifiers.py for full comparison")
    print("\n" + "="*80)
