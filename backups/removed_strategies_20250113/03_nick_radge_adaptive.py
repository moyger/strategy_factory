#!/usr/bin/env python3
"""
Nick Radge Adaptive Qualifier Strategy

Dynamically switches between qualifiers based on market regime:
- STRONG_BULL: Use ROC (captures explosive momentum)
- WEAK_BULL: Use BSS (safer, more selective)
- BEAR: Use BSS or 100% GLD (defensive)

This combines the best of both worlds.

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy, download_sp500_stocks, download_spy
from strategy_factory.performance_qualifiers import get_qualifier


class NickRadgeAdaptiveQualifier(NickRadgeMomentumStrategy):
    """
    Adaptive qualifier strategy that switches based on market regime

    Regime-Based Qualifier Selection:
    - STRONG_BULL (SPY > 200MA & > 50MA): ROC (max momentum)
    - WEAK_BULL (SPY > 200MA but < 50MA): BSS (selective)
    - BEAR (SPY < 200MA): BSS or GLD 100%
    """

    def __init__(self,
                 portfolio_size: int = 7,
                 roc_period: int = 100,
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
                 strong_bull_qualifier: str = 'roc',
                 weak_bull_qualifier: str = 'bss',
                 bear_qualifier: str = 'bss'):
        """
        Initialize Adaptive Qualifier Strategy

        Args:
            All standard Nick Radge parameters, plus:
            strong_bull_qualifier: Qualifier for STRONG_BULL regime ('roc', 'bss', etc.)
            weak_bull_qualifier: Qualifier for WEAK_BULL regime ('roc', 'bss', etc.)
            bear_qualifier: Qualifier for BEAR regime (usually 'bss' or ignored if 100% GLD)
        """
        super().__init__(
            portfolio_size=portfolio_size,
            roc_period=roc_period,
            ma_period=ma_period,
            rebalance_freq=rebalance_freq,
            use_momentum_weighting=use_momentum_weighting,
            use_regime_filter=use_regime_filter,
            use_relative_strength=use_relative_strength,
            regime_ma_long=regime_ma_long,
            regime_ma_short=regime_ma_short,
            strong_bull_positions=strong_bull_positions,
            weak_bull_positions=weak_bull_positions,
            bear_positions=bear_positions,
            bear_market_asset=bear_market_asset,
            bear_allocation=bear_allocation
        )

        self.strong_bull_qualifier = strong_bull_qualifier
        self.weak_bull_qualifier = weak_bull_qualifier
        self.bear_qualifier = bear_qualifier

        # Initialize qualifiers
        self.qualifiers = {
            'roc': None,  # Will use default ROC from parent
            'bss': get_qualifier('bss', poi_period=100, atr_period=14, k=2.0),
            'anm': get_qualifier('anm', momentum_period=100, atr_period=14),
            'vem': get_qualifier('vem', roc_period=100, atr_period=14, atr_avg_period=50),
            'tqs': get_qualifier('tqs', ma_period=100, atr_period=14, adx_period=25)
        }

        self.name = f"NickRadge_Adaptive_{strong_bull_qualifier.upper()}_BULL_{weak_bull_qualifier.upper()}_WEAK"

    def rank_stocks_adaptive(self,
                            prices: pd.DataFrame,
                            indicators: Dict[str, pd.DataFrame],
                            date: pd.Timestamp,
                            benchmark_roc: Optional[pd.Series] = None,
                            regime: str = 'UNKNOWN') -> pd.DataFrame:
        """
        Rank stocks using regime-appropriate qualifier

        Args:
            prices: Stock prices
            indicators: Indicators dict
            date: Current date
            benchmark_roc: SPY ROC for relative strength
            regime: Current market regime

        Returns:
            DataFrame with ranked stocks
        """
        if date not in prices.index:
            return pd.DataFrame()

        # Select qualifier based on regime
        if regime == 'STRONG_BULL':
            qualifier_name = self.strong_bull_qualifier
        elif regime == 'WEAK_BULL':
            qualifier_name = self.weak_bull_qualifier
        else:  # BEAR or UNKNOWN
            qualifier_name = self.bear_qualifier

        # Get qualifier
        qualifier = self.qualifiers.get(qualifier_name)

        # Calculate scores
        if qualifier is None:
            # Use ROC from indicators (parent class)
            scores = indicators['roc'].loc[date]
        else:
            # Use custom qualifier
            qualifier_scores = qualifier.calculate(prices)
            if date not in qualifier_scores.index:
                return pd.DataFrame()
            scores = qualifier_scores.loc[date]

        # Filter stocks
        above_ma = indicators['above_ma'].loc[date]

        valid_stocks = above_ma[above_ma == True].index
        if self.bear_market_asset:
            valid_stocks = [s for s in valid_stocks if s != self.bear_market_asset]
        valid_stocks = [s for s in valid_stocks if pd.notna(scores[s])]

        if len(valid_stocks) == 0:
            return pd.DataFrame()

        scores_valid = scores[valid_stocks].dropna()

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Relative strength filter
        if self.use_relative_strength and benchmark_roc is not None and date in benchmark_roc.index:
            spy_score = benchmark_roc.loc[date]
            if pd.notna(spy_score):
                scores_valid = scores_valid[scores_valid > spy_score]

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Sort by score (descending)
        ranked = scores_valid.sort_values(ascending=False)

        return pd.DataFrame({
            'ticker': ranked.index,
            'roc': ranked.values  # Keep key name for compatibility
        })

    def generate_allocations(self,
                           prices: pd.DataFrame,
                           spy_prices: Optional[pd.Series] = None,
                           benchmark_roc: Optional[pd.Series] = None,
                           enable_regime_recovery: bool = True) -> pd.DataFrame:
        """
        Generate allocations with adaptive qualifier selection

        Overrides parent method to use regime-based qualifier switching
        """
        print(f"\n📊 Calculating indicators for {len(prices.columns)} stocks...")
        print(f"   Adaptive Qualifiers:")
        print(f"   - STRONG_BULL: {self.strong_bull_qualifier.upper()}")
        print(f"   - WEAK_BULL: {self.weak_bull_qualifier.upper()}")
        print(f"   - BEAR: {self.bear_qualifier.upper()} (or GLD 100%)")

        indicators = self.calculate_indicators(prices)

        # Calculate market regime
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
                qualifier_used = None
                if reg == 'STRONG_BULL':
                    qualifier_used = self.strong_bull_qualifier.upper()
                elif reg == 'WEAK_BULL':
                    qualifier_used = self.weak_bull_qualifier.upper()
                elif reg == 'BEAR':
                    qualifier_used = f"{self.bear_qualifier.upper()} or GLD"

                print(f"   - {reg}: {count} days ({pct:.1f}%) → Using {qualifier_used}")

        # Initialize allocations
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        # Determine rebalance dates
        ideal_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.rebalance_freq
        )

        all_rebalance_dates = []
        for ideal_date in ideal_dates:
            nearest_idx = prices.index.searchsorted(ideal_date)
            if nearest_idx < len(prices.index):
                nearest_date = prices.index[nearest_idx]
                all_rebalance_dates.append(nearest_date)

        all_rebalance_dates = pd.DatetimeIndex(all_rebalance_dates).unique()

        min_date = prices.index[0] + pd.Timedelta(days=max(self.roc_period, self.ma_period))
        rebalance_dates = all_rebalance_dates[all_rebalance_dates >= min_date]

        print(f"\n   Quarterly rebalances: {len(rebalance_dates)}")
        if len(rebalance_dates) > 0:
            print(f"   First rebalance: {rebalance_dates[0].date()}")
            print(f"   Last rebalance: {rebalance_dates[-1].date()}")

        # Track state
        current_weights = None
        last_regime = None
        regime_recoveries = 0
        qualifier_switches = 0
        last_qualifier = None

        # Track qualifier usage
        qualifier_usage = {'STRONG_BULL': {}, 'WEAK_BULL': {}, 'BEAR': {}}

        rebalance_set = set(rebalance_dates)

        for date in prices.index:
            if date < min_date:
                continue

            # Check current regime
            current_regime = None
            if self.use_regime_filter and regime is not None and date in regime.index:
                current_regime = regime.loc[date]

            # Detect regime recovery
            is_regime_recovery = False
            if (enable_regime_recovery and
                last_regime == 'BEAR' and
                current_regime in ['STRONG_BULL', 'WEAK_BULL'] and
                current_weights is None):
                is_regime_recovery = True
                regime_recoveries += 1
                print(f"   🔄 Regime recovery on {date.date()} - Re-entering positions early")

            is_rebalance_date = date in rebalance_set

            if is_rebalance_date or is_regime_recovery:
                # Determine portfolio size based on regime
                portfolio_size = self.portfolio_size

                if self.use_regime_filter and current_regime is not None:
                    if current_regime == 'STRONG_BULL':
                        portfolio_size = self.strong_bull_positions
                        current_qualifier = self.strong_bull_qualifier
                    elif current_regime == 'WEAK_BULL':
                        portfolio_size = self.weak_bull_positions
                        current_qualifier = self.weak_bull_qualifier
                    else:  # BEAR or UNKNOWN
                        portfolio_size = self.bear_positions
                        current_qualifier = self.bear_qualifier

                    # Track qualifier switches
                    if last_qualifier and last_qualifier != current_qualifier:
                        qualifier_switches += 1
                        print(f"   🔄 Qualifier switch on {date.date()}: {last_qualifier.upper()} → {current_qualifier.upper()}")

                    last_qualifier = current_qualifier

                # Bear market handling
                if portfolio_size == 0:
                    if self.bear_market_asset and self.bear_market_asset in allocations.columns:
                        allocations.loc[date, :] = 0.0
                        allocations.loc[date, self.bear_market_asset] = self.bear_allocation
                        current_weights = pd.Series({self.bear_market_asset: self.bear_allocation})
                    else:
                        current_weights = None
                        allocations.loc[date, :] = 0.0
                else:
                    # Rank stocks using ADAPTIVE qualifier
                    ranked = self.rank_stocks_adaptive(prices, indicators, date, benchmark_roc, current_regime)

                    # Track qualifier usage
                    if current_regime and len(ranked) > 0:
                        if current_qualifier not in qualifier_usage[current_regime]:
                            qualifier_usage[current_regime][current_qualifier] = 0
                        qualifier_usage[current_regime][current_qualifier] += 1

                    if len(ranked) > 0:
                        top_stocks = ranked.head(portfolio_size)

                        if self.use_momentum_weighting:
                            positive_roc = top_stocks['roc'].clip(lower=0)
                            total_roc = positive_roc.sum()

                            if total_roc > 0:
                                weights = positive_roc / total_roc
                                weights.index = top_stocks['ticker'].values
                            else:
                                weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)
                        else:
                            weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)

                        current_weights = weights
                        for ticker in allocations.columns:
                            allocations.loc[date, ticker] = weights.get(ticker, 0.0)
                    else:
                        current_weights = None
                        allocations.loc[date, :] = 0.0
            else:
                # Between rebalances - maintain positions
                if current_weights is not None:
                    for ticker in allocations.columns:
                        allocations.loc[date, ticker] = current_weights.get(ticker, 0.0)
                else:
                    allocations.loc[date, :] = 0.0

            last_regime = current_regime

        if regime_recoveries > 0:
            print(f"   Total regime recoveries: {regime_recoveries}")

        if qualifier_switches > 0:
            print(f"   Total qualifier switches: {qualifier_switches}")

        print(f"\n   Qualifier Usage by Regime:")
        for reg, usage in qualifier_usage.items():
            if usage:
                print(f"   {reg}:")
                for qual, count in usage.items():
                    print(f"     - {qual.upper()}: {count} rebalances")

        return allocations


if __name__ == "__main__":
    print("="*80)
    print("NICK RADGE ADAPTIVE QUALIFIER STRATEGY")
    print("="*80)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000
    NUM_STOCKS = 50

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Strategy: Adaptive (ROC in STRONG_BULL, BSS otherwise)")

    # Download data
    print(f"\n{'='*80}")
    print("DOWNLOADING DATA")
    print("="*80)

    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)

    # Add GLD
    if 'GLD' not in prices.columns:
        print(f"\n⚠️  Adding GLD...")
        gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
        if isinstance(gld_data.columns, pd.MultiIndex):
            gld_data.columns = gld_data.columns.get_level_values(0)
        prices['GLD'] = gld_data['Close']
        prices = prices.dropna()
        print(f"✅ GLD added")

    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready: {len(prices)} days, {len(prices.columns)} stocks")

    # Create adaptive strategy
    print(f"\n{'='*80}")
    print("RUNNING ADAPTIVE STRATEGY")
    print("="*80)

    strategy = NickRadgeAdaptiveQualifier(
        portfolio_size=7,
        strong_bull_qualifier='roc',  # Use ROC in strong bull
        weak_bull_qualifier='bss',    # Use BSS in weak bull
        bear_qualifier='bss',          # Use BSS in bear (or GLD 100%)
        bear_market_asset='GLD',
        bear_allocation=1.0,
        use_regime_filter=True
    )

    # Run backtest
    portfolio = strategy.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.001,
        slippage=0.0005
    )

    # Calculate SPY return
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Print results
    strategy.print_results(portfolio, prices, spy_return)

    print(f"\n{'='*80}")
    print("✅ ADAPTIVE STRATEGY BACKTEST COMPLETE")
    print("="*80)
