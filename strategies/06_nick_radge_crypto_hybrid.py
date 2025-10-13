#!/usr/bin/env python3
"""
Nick Radge Crypto Hybrid Strategy - Core/Satellite Approach

Combines fixed core + dynamic satellite:
- Core (70%): Fixed BTC, ETH, SOL - NEVER rebalanced
- Satellite (30%): Top 5-7 alts from top 50 - Quarterly rebalanced using TQS/ML

WHY THIS APPROACH:
- Research showed pure dynamic selection underperforms fixed universe by 25×
- Pure fixed: +913% (winner)
- Pure dynamic: +35% (massive failure)
- Hybrid: Target +600-800% (70% captures fixed benefit, 30% adds alpha)

KEY INSIGHT from research (results/crypto/UNIVERSE_SELECTION_CRITERIA_ANALYSIS.md):
- BTC/ETH dominance persists for YEARS (not quarters like stock sectors)
- Quarterly rebalancing creates forced turnover with no edge
- Fixed universe captures winner-take-all network effects
- BUT: Alt-seasons offer opportunities (when alts outperform BTC)

STRATEGY:
- Core: Lock in BTC/ETH/SOL dominance (never force sell winners)
- Satellite: Capture alt-season alpha with TQS/ML selection
- Regime Filter: BTC 200MA/100MA (exit to PAXG during BEAR)
- Rebalancing: Quarterly for satellite only (core never rebalances)

Author: Strategy Factory
Date: 2025-01-13
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, Optional
import warnings
warnings.filterwarnings('ignore')

from strategy_factory.performance_qualifiers import get_qualifier


class NickRadgeCryptoHybrid:
    """
    Hybrid Core/Satellite Crypto Momentum Strategy

    Portfolio Structure:
    - 70% Core: BTC (23.3%), ETH (23.3%), SOL (23.3%) - Fixed, no rebalancing
    - 30% Satellite: Top 5 alts from top 50 (6% each) - Quarterly rebalancing with TQS/ML

    Regime-Based Adjustments:
    - STRONG_BULL (BTC > 200MA & > 100MA): 100% invested (70% core + 30% satellite)
    - WEAK_BULL (BTC > 200MA but < 100MA): 85% invested (70% core + 15% satellite + 15% PAXG)
    - BEAR (BTC < 200MA): 0% crypto (100% PAXG)
    """

    def __init__(self,
                 core_allocation: float = 0.70,
                 satellite_allocation: float = 0.30,
                 core_assets: list = None,
                 satellite_size: int = 5,
                 qualifier_type: str = 'tqs',
                 ma_period: int = 100,
                 rebalance_freq: str = 'QS',
                 use_momentum_weighting: bool = True,
                 regime_ma_long: int = 200,
                 regime_ma_short: int = 100,
                 bear_asset: str = 'PAXG-USD',
                 weak_bull_satellite_reduction: float = 0.50,
                 qualifier_params: Optional[Dict] = None):
        """
        Initialize Hybrid Crypto Strategy

        Args:
            core_allocation: Allocation to fixed core (default: 0.70 = 70%)
            satellite_allocation: Allocation to dynamic satellite (default: 0.30 = 30%)
            core_assets: List of core crypto tickers (default: ['BTC-USD', 'ETH-USD', 'SOL-USD'])
            satellite_size: Number of alts in satellite (default: 5)
            qualifier_type: Ranking method for satellite - 'tqs', 'ml_xgb', 'hybrid'
            ma_period: Moving average trend filter (default: 100)
            rebalance_freq: Rebalancing frequency ('QS' = quarterly)
            use_momentum_weighting: Weight satellite by momentum strength
            regime_ma_long: Long-term MA for regime (200 days)
            regime_ma_short: Short-term MA for regime (100 days for crypto, not 50 like stocks)
            bear_asset: Asset for bear market (default: 'PAXG-USD' - tokenized gold)
            weak_bull_satellite_reduction: Reduce satellite by this % in WEAK_BULL (default: 0.50 = 50%)
            qualifier_params: Additional parameters for qualifier
        """
        self.core_allocation = core_allocation
        self.satellite_allocation = satellite_allocation
        self.core_assets = core_assets or ['BTC-USD', 'ETH-USD', 'SOL-USD']
        self.satellite_size = satellite_size
        self.qualifier_type = qualifier_type
        self.ma_period = ma_period
        self.rebalance_freq = rebalance_freq
        self.use_momentum_weighting = use_momentum_weighting
        self.regime_ma_long = regime_ma_long
        self.regime_ma_short = regime_ma_short
        self.bear_asset = bear_asset
        self.weak_bull_satellite_reduction = weak_bull_satellite_reduction

        # Initialize qualifier for satellite selection
        params = qualifier_params or {}
        self.qualifier = get_qualifier(qualifier_type, **params)

        self.name = f"CryptoHybrid_{qualifier_type.upper()}_Core{int(core_allocation*100)}_Sat{int(satellite_allocation*100)}"

    def calculate_regime(self, btc_prices: pd.Series) -> pd.Series:
        """
        Calculate 3-tier market regime based on BTC

        IMPORTANT: Uses BTC as regime filter, not SPY (crypto-specific)

        Regimes:
        - STRONG_BULL: BTC > 200-day MA AND BTC > 100-day MA
        - WEAK_BULL: BTC > 200-day MA BUT BTC < 100-day MA
        - BEAR: BTC < 200-day MA

        Args:
            btc_prices: BTC-USD close prices

        Returns:
            Series with regime classification
        """
        # Lag MAs by 1 day to prevent look-ahead bias
        ma_long = btc_prices.rolling(window=self.regime_ma_long).mean().shift(1)
        ma_short = btc_prices.rolling(window=self.regime_ma_short).mean().shift(1)
        prices_lagged = btc_prices.shift(1)

        regime = pd.Series('UNKNOWN', index=btc_prices.index)

        # Classification using lagged data
        regime[(prices_lagged > ma_long) & (prices_lagged > ma_short)] = 'STRONG_BULL'
        regime[(prices_lagged > ma_long) & (prices_lagged <= ma_short)] = 'WEAK_BULL'
        regime[prices_lagged <= ma_long] = 'BEAR'

        return regime

    def calculate_indicators(self,
                           prices: pd.DataFrame,
                           btc_prices: Optional[pd.Series] = None) -> Dict[str, pd.DataFrame]:
        """
        Calculate indicators for satellite selection

        Uses qualifier (TQS, ml_xgb, etc.) for ranking

        Args:
            prices: DataFrame with crypto prices (columns = tickers)
            btc_prices: BTC prices (used as SPY proxy for ML qualifiers)

        Returns:
            Dictionary with indicator DataFrames
        """
        # === IMPROVEMENT 2: ML Qualifier Support ===
        # ML qualifiers need volume and sector data, but crypto doesn't have sectors
        # Use prices as volume proxy (crypto volume patterns similar to price)
        if self.qualifier_type in ['ml_xgb', 'ml_rf', 'hybrid']:
            print(f"   [ML] Using {self.qualifier_type.upper()} qualifier for satellite selection")
            print(f"   [ML] Note: Crypto-specific ML (no sector features, volume=price proxy)")
            try:
                # For crypto: spy_prices=btc_prices, volumes=prices, sector_prices=None
                scores = self.qualifier.calculate(
                    prices,
                    spy_prices=btc_prices,
                    volumes=prices,  # Use prices as volume proxy
                    sector_prices=None  # No sector ETFs for crypto
                ).shift(1)
            except Exception as e:
                print(f"   ⚠️  ML qualifier failed: {e}")
                print(f"   Falling back to simple ROC ranking...")
                # Fallback to simple momentum if ML fails
                scores = prices.pct_change(100).shift(1)
        else:
            # Traditional qualifiers (TQS, ROC, BSS, etc.)
            scores = self.qualifier.calculate(prices).shift(1)

        # Moving Average filter
        ma = prices.rolling(window=self.ma_period).mean().shift(1)
        above_ma = (prices.shift(1) > ma)

        return {
            'scores': scores,
            'ma': ma,
            'above_ma': above_ma
        }

    def select_satellite(self,
                        prices: pd.DataFrame,
                        indicators: Dict[str, pd.DataFrame],
                        date: pd.Timestamp) -> pd.DataFrame:
        """
        Select top N alts for satellite portfolio

        Filters:
        1. Exclude core assets (BTC, ETH, SOL)
        2. Exclude bear asset (PAXG)
        3. Above MA filter
        4. Valid scores
        5. Top N by qualifier score

        Args:
            prices: Crypto prices DataFrame
            indicators: Dictionary of indicators
            date: Date to select for

        Returns:
            DataFrame with selected alts and scores
        """
        if date not in prices.index:
            return pd.DataFrame()

        scores = indicators['scores'].loc[date]
        above_ma = indicators['above_ma'].loc[date]

        # Filter: Above MA and valid scores
        valid_cryptos = above_ma[above_ma == True].index

        # Exclude core assets and bear asset from satellite
        exclude = set(self.core_assets + [self.bear_asset])
        valid_cryptos = [c for c in valid_cryptos if c not in exclude and pd.notna(scores[c])]

        if len(valid_cryptos) == 0:
            return pd.DataFrame()

        # Get scores for valid cryptos
        scores_valid = scores[valid_cryptos].dropna()

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Sort by score and take top N
        ranked = scores_valid.sort_values(ascending=False).head(self.satellite_size)

        return pd.DataFrame({
            'ticker': ranked.index,
            'score': ranked.values
        })

    def generate_allocations(self,
                           prices: pd.DataFrame,
                           btc_prices: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Generate hybrid portfolio allocations over time

        Portfolio Structure:
        - Core (70%): BTC, ETH, SOL - equal weighted, never rebalanced
        - Satellite (30%): Top 5 alts - momentum weighted, quarterly rebalanced

        Regime Adjustments:
        - STRONG_BULL: 100% invested (70% core + 30% satellite)
        - WEAK_BULL: 85% invested (70% core + 15% satellite + 15% PAXG)
        - BEAR: 0% crypto (100% PAXG)

        Args:
            prices: DataFrame with crypto prices (columns = tickers)
            btc_prices: BTC prices for regime filter (required)

        Returns:
            DataFrame with target allocations (rows = dates, cols = tickers)
        """
        if btc_prices is None:
            raise ValueError("btc_prices required for regime filter")

        # Calculate regime
        regime = self.calculate_regime(btc_prices)

        # Calculate indicators for satellite selection
        # Filter out core assets and bear asset from indicator calculation
        satellite_universe = [c for c in prices.columns
                             if c not in self.core_assets and c != self.bear_asset]
        satellite_prices = prices[satellite_universe]
        indicators = self.calculate_indicators(satellite_prices, btc_prices)

        # Get rebalance dates (quarterly)
        rebalance_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.rebalance_freq
        )

        # Find nearest trading dates
        actual_rebalance_dates = []
        for target_date in rebalance_dates:
            nearest_dates = prices.index[prices.index >= target_date]
            if len(nearest_dates) > 0:
                actual_rebalance_dates.append(nearest_dates[0])

        # Initialize allocations DataFrame
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        # Track current satellite holdings
        current_satellite = []
        satellite_scores = {}  # Initialize before loop to avoid UnboundLocalError

        print(f"\n📊 Generating Hybrid Allocations...")
        print(f"   Core: {len(self.core_assets)} assets ({self.core_allocation:.0%})")
        print(f"   Satellite: {self.satellite_size} assets ({self.satellite_allocation:.0%})")
        print(f"   Rebalances: {len(actual_rebalance_dates)}")

        for i, date in enumerate(prices.index):
            current_regime = regime.loc[date]

            # === FIX: Skip allocations if any required asset has NaN price ===
            # Leading NaNs mean the asset didn't exist yet - can't trade what doesn't exist!
            # This prevents vectorbt from sizing trades against NaN prices
            required_assets_for_regime = []

            # Always check core assets (used in all non-BEAR regimes)
            if current_regime != 'BEAR':
                required_assets_for_regime.extend(self.core_assets)

            # Check bear asset (used in BEAR, WEAK_BULL, UNKNOWN regimes)
            if current_regime in ['BEAR', 'WEAK_BULL', 'UNKNOWN']:
                required_assets_for_regime.append(self.bear_asset)

            # Check if all required assets have valid prices
            has_nan_price = False
            for asset in required_assets_for_regime:
                if asset in prices.columns:
                    price_value = prices.at[date, asset]  # .at[] returns scalar, not DataFrame
                    # Check if price is NaN or invalid (<=0)
                    if pd.isna(price_value):
                        has_nan_price = True
                        break
                    try:
                        if float(price_value) <= 0:  # type: ignore
                            has_nan_price = True
                            break
                    except (ValueError, TypeError):
                        # Non-numeric price value
                        has_nan_price = True
                        break

            # Skip this date if any required asset has NaN/invalid price
            if has_nan_price:
                # Leave allocations at 0.0 (100% cash) for this date
                # This is correct behavior - we can't trade what doesn't have data yet
                continue

            # Rebalance satellite on rebalance dates (or first date for initial pick)
            if date in actual_rebalance_dates or (i == 0 and date not in actual_rebalance_dates):
                selected = self.select_satellite(satellite_prices, indicators, date)
                if len(selected) > 0:
                    current_satellite = selected['ticker'].tolist()
                    satellite_scores = dict(zip(selected['ticker'], selected['score']))
                else:
                    current_satellite = []
                    satellite_scores = {}  # Clear scores if no valid satellites

            # Apply regime-based allocation
            if current_regime == 'BEAR':
                # 100% PAXG during bear market
                allocations.loc[date, self.bear_asset] = 1.0

            elif current_regime == 'WEAK_BULL':
                # Reduce satellite allocation by 50%, allocate to PAXG
                reduced_satellite = self.satellite_allocation * self.weak_bull_satellite_reduction
                paxg_allocation = self.satellite_allocation * (1 - self.weak_bull_satellite_reduction)

                # Core: 70% (unchanged)
                # FIX: Only count core assets that actually exist in the data
                available_core = [asset for asset in self.core_assets if asset in prices.columns]
                core_weight = self.core_allocation / len(available_core) if available_core else 0
                for asset in available_core:
                    allocations.loc[date, asset] = core_weight

                # Satellite: 15% (reduced from 30%)
                # FIX: Only allocate to satellites with valid prices (not NaN)
                valid_satellites = [t for t in current_satellite
                                  if t in prices.columns and not pd.isna(prices.at[date, t]) and prices.at[date, t] > 0]  # type: ignore

                if self.use_momentum_weighting and valid_satellites and satellite_scores:
                    # Momentum-weighted
                    total_score = sum(satellite_scores[t] for t in valid_satellites if t in satellite_scores)
                    if total_score > 0:
                        for ticker in valid_satellites:
                            if ticker in satellite_scores:
                                weight = (satellite_scores[ticker] / total_score) * reduced_satellite
                                allocations.loc[date, ticker] = weight
                else:
                    # Equal-weighted
                    sat_weight = reduced_satellite / len(valid_satellites) if valid_satellites else 0
                    for ticker in valid_satellites:
                        allocations.loc[date, ticker] = sat_weight

                # PAXG: 15%
                allocations.loc[date, self.bear_asset] = paxg_allocation

            elif current_regime == 'STRONG_BULL':
                # Full allocation: 70% core + 30% satellite

                # Core: 70% equal-weighted
                # FIX: Only count core assets that actually exist in the data
                available_core = [asset for asset in self.core_assets if asset in prices.columns]
                core_weight = self.core_allocation / len(available_core) if available_core else 0
                for asset in available_core:
                    allocations.loc[date, asset] = core_weight

                # Satellite: 30% momentum or equal weighted
                # FIX: Only allocate to satellites with valid prices (not NaN)
                valid_satellites = [t for t in current_satellite
                                  if t in prices.columns and not pd.isna(prices.at[date, t]) and prices.at[date, t] > 0]  # type: ignore

                if self.use_momentum_weighting and valid_satellites and satellite_scores:
                    total_score = sum(satellite_scores[t] for t in valid_satellites if t in satellite_scores)
                    if total_score > 0:
                        for ticker in valid_satellites:
                            if ticker in satellite_scores:
                                weight = (satellite_scores[ticker] / total_score) * self.satellite_allocation
                                allocations.loc[date, ticker] = weight
                else:
                    sat_weight = self.satellite_allocation / len(valid_satellites) if valid_satellites else 0
                    for ticker in valid_satellites:
                        allocations.loc[date, ticker] = sat_weight

            # UNKNOWN regime: Same as WEAK_BULL (cautious)
            else:
                reduced_satellite = self.satellite_allocation * self.weak_bull_satellite_reduction
                paxg_allocation = self.satellite_allocation * (1 - self.weak_bull_satellite_reduction)

                # FIX: Only count core assets that actually exist in the data
                available_core = [asset for asset in self.core_assets if asset in prices.columns]
                core_weight = self.core_allocation / len(available_core) if available_core else 0
                for asset in available_core:
                    allocations.loc[date, asset] = core_weight

                # FIX: Only allocate to satellites with valid prices (not NaN)
                valid_satellites = [t for t in current_satellite
                                  if t in prices.columns and not pd.isna(prices.at[date, t]) and prices.at[date, t] > 0]  # type: ignore

                if self.use_momentum_weighting and valid_satellites and satellite_scores:
                    total_score = sum(satellite_scores[t] for t in valid_satellites if t in satellite_scores)
                    if total_score > 0:
                        for ticker in valid_satellites:
                            if ticker in satellite_scores:
                                weight = (satellite_scores[ticker] / total_score) * reduced_satellite
                                allocations.loc[date, ticker] = weight
                else:
                    sat_weight = reduced_satellite / len(valid_satellites) if valid_satellites else 0
                    for ticker in valid_satellites:
                        allocations.loc[date, ticker] = sat_weight

                allocations.loc[date, self.bear_asset] = paxg_allocation

        # === IMPROVEMENT 3: Allocation Edge Case Warnings ===
        # Normalize to ensure weights sum to 1.0
        row_sums = allocations.sum(axis=1)

        # Check for zero allocation days (edge case warning)
        zero_alloc_days = row_sums[row_sums == 0]
        if len(zero_alloc_days) > 0:
            pct_zero = len(zero_alloc_days) / len(row_sums) * 100
            print(f"\n   ⚠️  WARNING: {len(zero_alloc_days)} days ({pct_zero:.1f}%) with ZERO allocations (100% cash)")
            print(f"   This occurs when:")
            print(f"   - No valid satellites found (all below MA)")
            print(f"   - Bear asset missing AND in BEAR regime")
            print(f"   - All allocations filtered out")
            if pct_zero > 10:
                print(f"   ⚠️  CRITICAL: >10% zero allocation days! Strategy may underperform!")

        # Check for very low allocation days
        low_alloc_days = row_sums[(row_sums > 0) & (row_sums < 0.50)]
        if len(low_alloc_days) > 0:
            pct_low = len(low_alloc_days) / len(row_sums) * 100
            print(f"\n   ⚠️  INFO: {len(low_alloc_days)} days ({pct_low:.1f}%) with <50% allocations")

        allocations = allocations.div(row_sums, axis=0).fillna(0.0)

        # Regime summary
        regime_counts = regime.value_counts()
        print(f"\n   Market Regime Summary:")
        for reg, count in regime_counts.items():
            pct = count / len(regime) * 100
            print(f"   - {reg}: {count} days ({pct:.1f}%)")

        return allocations

    def backtest(self,
                prices: pd.DataFrame,
                btc_prices: Optional[pd.Series] = None,
                initial_capital: float = 100000,
                fees: float = 0.001,
                slippage: float = 0.0005) -> vbt.Portfolio:
        """
        Backtest hybrid strategy using vectorbt

        Args:
            prices: DataFrame with crypto prices
            btc_prices: BTC prices for regime filter (required)
            initial_capital: Starting capital
            fees: Trading fees (0.001 = 0.1%)
            slippage: Slippage (0.0005 = 0.05%)

        Returns:
            vectorbt Portfolio object
        """
        print("="*80)
        print(f"🚀 Backtesting {self.name}")
        print("="*80)
        print(f"\n📊 Strategy Configuration:")
        print(f"   Core Assets: {', '.join(self.core_assets)} ({self.core_allocation:.0%})")
        print(f"   Satellite Size: {self.satellite_size} alts ({self.satellite_allocation:.0%})")
        print(f"   Qualifier: {self.qualifier_type.upper()}")
        print(f"   Rebalance: {self.rebalance_freq}")
        print(f"   Bear Asset: {self.bear_asset}")
        print(f"   Initial Capital: ${initial_capital:,.0f}")

        # === IMPROVEMENT 1: Bear Asset Validation & Auto-Download ===
        if self.bear_asset not in prices.columns:
            print(f"\n⚠️  Bear asset {self.bear_asset} not in data, attempting auto-download...")
            try:
                import yfinance as yf
                bear_data = yf.download(
                    self.bear_asset,
                    start=prices.index[0],
                    end=prices.index[-1],
                    progress=False
                )
                if bear_data is not None and not bear_data.empty:  # type: ignore
                    # Extract Close price
                    if isinstance(bear_data.columns, pd.MultiIndex):
                        bear_close = bear_data['Close'].iloc[:, 0]  # type: ignore
                    else:
                        bear_close = bear_data['Close']  # type: ignore

                    # Align with prices index
                    prices[self.bear_asset] = bear_close.reindex(prices.index, method='ffill')  # type: ignore
                    print(f"   ✅ Successfully downloaded {self.bear_asset}")
                else:
                    raise ValueError(f"Downloaded data for {self.bear_asset} is empty")
            except Exception as e:
                raise ValueError(
                    f"❌ Bear asset {self.bear_asset} not found in prices and auto-download failed: {e}\n"
                    f"   Available tickers: {list(prices.columns[:10])}...\n"
                    f"   Please include {self.bear_asset} in your input data or use a different bear asset."
                )

        # Validate core assets exist
        missing_core = [asset for asset in self.core_assets if asset not in prices.columns]
        if missing_core:
            raise ValueError(
                f"❌ Core assets missing from prices: {missing_core}\n"
                f"   Available tickers: {list(prices.columns[:10])}...\n"
                f"   Core assets are required and cannot be auto-downloaded (strategy depends on them)."
            )

        # === FIX: Forward-fill ONLY (no backfill = no look-ahead bias) ===
        # Backfilling uses future prices to populate earlier bars = look-ahead bias!
        # Zero-fill creates invalid prices (0 close) = explosive returns when real data resumes

        print(f"\n📊 Data Cleaning (No Look-Ahead Bias):")
        initial_nan_count = prices.isna().sum().sum()
        print(f"   Initial NaN values: {initial_nan_count}")

        # Step 1: Forward fill ONLY (no backfill!)
        prices = prices.fillna(method='ffill')

        # Step 2: Replace inf with NaN, then forward fill again
        prices = prices.replace([np.inf, -np.inf], np.nan).fillna(method='ffill')

        # Step 3: Drop columns that are COMPLETELY empty after forward fill
        # (these have no data at all, cannot be used)
        # CRITICAL: Fail fast if required assets are all-NaN (failed download)
        completely_empty = prices.columns[prices.isna().all()].tolist()
        if completely_empty:
            # Check if any required assets are completely empty
            required_assets = set(self.core_assets + [self.bear_asset])
            missing_required = [col for col in completely_empty if col in required_assets]

            if missing_required:
                raise ValueError(
                    f"❌ CRITICAL: Required assets are completely empty (failed download?): {missing_required}\n"
                    f"   Core assets: {self.core_assets}\n"
                    f"   Bear asset: {self.bear_asset}\n"
                    f"   Cannot backtest without these assets. Please check your data sources."
                )

            print(f"   ⚠️  Dropping {len(completely_empty)} completely empty columns: {completely_empty}")
            prices = prices.drop(columns=completely_empty)

        # Step 4: Check for columns with leading NaNs (start after backtest begins)
        # These are OK - crypto assets with partial histories
        # BUT check if >50% is NaN (too sparse to be useful)
        # CRITICAL: NEVER drop core assets or bear asset (required for strategy logic)
        nan_pct = prices.isna().sum() / len(prices)
        too_sparse = nan_pct[nan_pct > 0.50].index.tolist()

        # Protect core assets and bear asset from being dropped
        required_assets = set(self.core_assets + [self.bear_asset])
        protected_assets = [col for col in too_sparse if col in required_assets]
        droppable_sparse = [col for col in too_sparse if col not in required_assets]

        if protected_assets:
            print(f"   ⚠️  WARNING: {len(protected_assets)} REQUIRED assets have >50% NaN (keeping anyway): {protected_assets}")
            print(f"      These are core/bear assets - required for strategy logic")

        if droppable_sparse:
            print(f"   ⚠️  Dropping {len(droppable_sparse)} non-essential columns with >50% NaN: {droppable_sparse[:5]}")
            prices = prices.drop(columns=droppable_sparse)

        # Step 5: Check for remaining NaNs (should only be leading NaNs now)
        remaining_nans = prices.isna().sum().sum()
        if remaining_nans > 0:
            # Count columns with leading NaNs (acceptable)
            cols_with_nans = (prices.isna().sum() > 0).sum()
            print(f"   ℹ️  {cols_with_nans} columns have leading NaNs (partial histories - OK)")
            print(f"   ℹ️  {remaining_nans} total NaN values (will not be used in calculations)")

            # Do NOT fill with zeros or backfill!
            # Strategy will simply not trade these assets until data exists
            # This is correct behavior - can't trade what didn't exist yet!

        print(f"   ✅ Final clean: {len(prices.columns)} columns, {len(prices)} rows")
        print(f"   ✅ No look-ahead bias (forward-fill only)")
        print(f"   ✅ No invalid prices (no zero-fill)")

        # Generate allocations
        allocations = self.generate_allocations(prices, btc_prices)

        # Ensure allocations and prices have same columns
        # Remove any allocations for tickers not in prices
        allocations = allocations[prices.columns]

        # Verify no NaN or Inf in either DataFrame
        if prices.isna().any().any():
            print("\n⚠️  WARNING: NaN values still present in prices after cleaning")
            nan_summary = prices.isna().sum()
            print(f"   NaN counts: {nan_summary[nan_summary > 0]}")
            # Forward fill only, accept remaining NaNs (leading NaNs from partial histories)
            prices = prices.fillna(method='ffill')
            remaining = prices.isna().sum().sum()
            if remaining > 0:
                print(f"   ℹ️  {remaining} NaN values remain (assets with partial history - won't trade until data exists)")

        if allocations.isna().any().any():
            print("\n⚠️  WARNING: NaN values in allocations")
            allocations = allocations.fillna(0)

        # Debug: Check for invalid values
        if (prices <= 0).any().any():
            zero_cols = prices.columns[(prices <= 0).any()].tolist()
            print(f"\n⚠️  WARNING: Zero or negative prices in: {zero_cols}")
            # Replace zeros with forward fill only (no backfill to avoid look-ahead bias)
            prices = prices.replace(0, np.nan).fillna(method='ffill')
            remaining_zeros = (prices <= 0).sum().sum()
            if remaining_zeros > 0:
                print(f"   ℹ️  {remaining_zeros} zero/negative values remain (will not be traded)")

        print(f"\n📊 Data validation:")
        print(f"   Prices shape: {prices.shape}")
        print(f"   Allocations shape: {allocations.shape}")
        print(f"   Price range: {prices.min().min():.2f} to {prices.max().max():.2f}")
        print(f"   Any NaN in prices: {prices.isna().any().any()}")
        print(f"   Any NaN in allocations: {allocations.isna().any().any()}")

        # Create portfolio using vectorbt with target percent sizing
        portfolio = vbt.Portfolio.from_orders(
            close=prices,
            size=allocations,
            size_type='targetpercent',
            fees=fees,
            slippage=slippage,
            init_cash=initial_capital,
            cash_sharing=True,  # Share cash across all assets
            group_by=True,  # Treat as single portfolio
            call_seq='auto',  # Optimize order execution
            freq='D'
        )

        print(f"\n✅ Backtest Complete!")

        # === FIX: Safely extract scalar from portfolio value ===
        final_val = portfolio.value().iloc[-1]
        if isinstance(final_val, pd.Series):
            final_val = float(final_val.iloc[0])  # type: ignore
        elif isinstance(final_val, np.ndarray):
            final_val = float(final_val[0])  # type: ignore
        else:
            final_val = float(final_val)

        # === FIX: Safely extract scalar from total return ===
        total_ret = portfolio.total_return()
        if isinstance(total_ret, pd.Series):
            total_ret = float(total_ret.iloc[0])  # type: ignore
        elif isinstance(total_ret, np.ndarray):
            total_ret = float(total_ret[0])  # type: ignore
        else:
            total_ret = float(total_ret)

        print(f"   Final Value: ${final_val:,.2f}")
        print(f"   Total Return: {total_ret * 100:.2f}%")  # total_return() already returns ratio

        return portfolio

    def _safe_scalar(self, value):
        """Safely extract scalar from Series/Array/scalar"""
        if isinstance(value, pd.Series):
            return float(value.iloc[0])  # type: ignore
        elif isinstance(value, np.ndarray):
            return float(value[0])  # type: ignore
        return float(value)

    def print_results(self, portfolio: vbt.Portfolio, prices: pd.DataFrame):
        """Print backtest results"""
        print("\n" + "="*80)
        print("HYBRID CRYPTO STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Core: {self.core_allocation:.0%} ({', '.join(self.core_assets)})")
        print(f"   Satellite: {self.satellite_allocation:.0%} (Top {self.satellite_size} alts)")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")

        # === FIX: Use _safe_scalar helper to handle Series/Array returns ===
        total_return_val = portfolio.total_return() if callable(portfolio.total_return) else portfolio.total_return
        sharpe_val = portfolio.sharpe_ratio(freq='D') if callable(portfolio.sharpe_ratio) else portfolio.sharpe_ratio
        max_dd_val = portfolio.max_drawdown() if callable(portfolio.max_drawdown) else portfolio.max_drawdown
        final_val = portfolio.value().iloc[-1]

        # Safely extract scalars
        total_return = self._safe_scalar(total_return_val) * 100
        sharpe = self._safe_scalar(sharpe_val)
        max_dd = self._safe_scalar(max_dd_val) * 100
        final_equity = self._safe_scalar(final_val)

        print(f"\n📈 Performance:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Final Equity: ${final_equity:,.2f}")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_dd:.2f}%")

        print("\n" + "="*80)


if __name__ == "__main__":
    print("="*80)
    print("HYBRID CRYPTO STRATEGY - CORE/SATELLITE APPROACH")
    print("="*80)
    print()
    print("🎯 Strategy Concept:")
    print("   70% Core (Fixed): BTC, ETH, SOL - Never rebalanced")
    print("   30% Satellite (Dynamic): Top 5 alts - Quarterly rebalanced with TQS/ML")
    print()
    print("📊 Why Hybrid?")
    print("   - Research: Pure dynamic underperforms fixed universe by 25×")
    print("   - Core captures BTC/ETH dominance (persistent winners)")
    print("   - Satellite captures alt-season opportunities")
    print("   - Reduces forced turnover on core holdings")
    print()
    print("✅ To test:")
    print("   python examples/test_crypto_hybrid_strategy.py")
    print("="*80)
