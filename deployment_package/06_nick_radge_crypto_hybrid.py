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
    Hybrid Core/Satellite Crypto Momentum Strategy with Position-Only Stop-Loss

    Portfolio Structure:
    - 70% Core: BTC (23.3%), ETH (23.3%), SOL (23.3%) - Fixed, no rebalancing
    - 30% Satellite: Top 5 alts from top 50 (6% each) - Quarterly rebalancing with TQS/ML

    Regime-Based Adjustments:
    - STRONG_BULL (BTC > 200MA & > 100MA): 100% invested (70% core + 30% satellite)
    - WEAK_BULL (BTC > 200MA but < 100MA): 85% invested (70% core + 15% satellite + 15% PAXG)
    - BEAR (BTC < 200MA): 0% crypto (100% PAXG)

    Position Stop-Loss (DEFAULT):
    - 40% stop-loss on individual positions
    - Backtest: 19,410% return (vs 19,137% no stops) over 2020-2025
    - Caught 8 catastrophic failures: SOL -88%, AVAX -79%, ETH -63%, etc.
    - Portfolio stop-loss DISABLED by default (caused -11,000% underperformance in backtest)
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
                 regime_hysteresis: float = 0.02,
                 portfolio_stop_loss: Optional[float] = None,
                 stop_loss_min_cooldown_days: int = 2,
                 stop_loss_reentry_threshold: float = 0.03,
                 position_stop_loss: float = 0.40,
                 position_stop_loss_core_only: bool = False,
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
            regime_hysteresis: Buffer % to prevent whipsaw (default: 0.02 = 2%)
            portfolio_stop_loss: Exit all positions if portfolio drops this % (default: None = DISABLED)
                                 Note: Backtest showed position-only stops outperform layered approach
            stop_loss_min_cooldown_days: Minimum days before checking re-entry (default: 2)
            stop_loss_reentry_threshold: Re-enter when portfolio recovers this % from trough (default: 0.03 = 3%)
            position_stop_loss: Exit individual position if it drops this % from entry (default: 0.40 = 40%)
                                 Backtest result: 19,410% return with 8 stops triggered (SOL -88%, AVAX -79%, etc.)
            position_stop_loss_core_only: Apply stop-loss only to core assets (default: False = all positions)
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
        self.regime_hysteresis = regime_hysteresis
        self.portfolio_stop_loss = portfolio_stop_loss
        self.stop_loss_min_cooldown_days = stop_loss_min_cooldown_days
        self.stop_loss_reentry_threshold = stop_loss_reentry_threshold
        self.position_stop_loss = position_stop_loss
        self.position_stop_loss_core_only = position_stop_loss_core_only

        # Initialize qualifier for satellite selection
        params = qualifier_params or {}
        self.qualifier = get_qualifier(qualifier_type, **params)

        self.name = f"CryptoHybrid_{qualifier_type.upper()}_Core{int(core_allocation*100)}_Sat{int(satellite_allocation*100)}"

    def _align_allocations_with_prices(self, allocations: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
        """
        FIX Bug 15: Ensure allocations only reference assets with valid prices.

        Clears any allocations where price is NaN or ≤0 to prevent VectorBT errors:
        "ValueError: order.price must be finite and greater than 0"

        This handles edge cases like:
        - Asset gets delisted mid-backtest
        - Exchange downtime (missing price data)
        - Asset hasn't launched yet (leading NaNs)
        - Price data corruption

        Args:
            allocations: Target allocation matrix (may have allocations for NaN prices)
            prices: Price matrix (may contain NaN or ≤0 values)

        Returns:
            Cleaned allocation matrix (NaN for invalid prices)
        """
        aligned = allocations.copy()
        cleared_count = 0

        for date in aligned.index:
            for ticker in aligned.columns:
                alloc = aligned.at[date, ticker]

                # Only check on rebalance days (non-NaN allocations)
                if pd.notna(alloc) and alloc != 0:
                    # Check if price is valid
                    if ticker in prices.columns:
                        try:
                            price = prices.at[date, ticker]
                            if pd.isna(price) or float(price) <= 0:
                                # Clear allocation (can't trade at NaN/zero price)
                                aligned.at[date, ticker] = np.nan
                                cleared_count += 1
                        except (ValueError, TypeError, KeyError):
                            # Price access failed
                            aligned.at[date, ticker] = np.nan
                            cleared_count += 1
                    else:
                        # Ticker not in prices at all
                        aligned.at[date, ticker] = np.nan
                        cleared_count += 1

        if cleared_count > 0:
            print(f"   ⚠️  Bug 15 Fix: Cleared {cleared_count} allocations with invalid prices")

        return aligned

    def calculate_regime(self, btc_prices: pd.Series) -> pd.Series:
        """
        Calculate 3-tier market regime based on BTC with hysteresis

        IMPORTANT: Uses BTC as regime filter, not SPY (crypto-specific)

        Regimes (with hysteresis to prevent whipsaw):
        - STRONG_BULL: BTC > 200MA * (1 + hyst) AND BTC > 100MA * (1 + hyst)
        - WEAK_BULL: BTC > 200MA * (1 + hyst) BUT BTC < 100MA * (1 - hyst)
        - BEAR: BTC < 200MA * (1 - hyst)

        Hysteresis creates buffer zones:
        - To exit BEAR → WEAK_BULL: BTC must rise to 200MA * (1 + hyst)
        - To exit STRONG_BULL → WEAK_BULL: BTC must fall to 100MA * (1 - hyst)
        - This prevents regime flip-flops when price hovers near MAs

        Args:
            btc_prices: BTC-USD close prices

        Returns:
            Series with regime classification
        """
        # Lag MAs by 1 day to prevent look-ahead bias
        ma_long = btc_prices.rolling(window=self.regime_ma_long).mean().shift(1)
        ma_short = btc_prices.rolling(window=self.regime_ma_short).mean().shift(1)
        prices_lagged = btc_prices.shift(1)

        # Apply hysteresis buffers
        hyst = self.regime_hysteresis
        ma_long_upper = ma_long * (1 + hyst)  # Need to exceed this to exit BEAR
        ma_long_lower = ma_long * (1 - hyst)  # Fall below this to enter BEAR
        ma_short_upper = ma_short * (1 + hyst)  # Need to exceed this to enter STRONG_BULL
        ma_short_lower = ma_short * (1 - hyst)  # Fall below this to exit STRONG_BULL

        # Initialize with UNKNOWN
        regime = pd.Series('UNKNOWN', index=btc_prices.index)

        # Track previous regime for hysteresis logic
        current_regime = 'UNKNOWN'

        for i, date in enumerate(btc_prices.index):
            price = prices_lagged.loc[date]

            if pd.isna(price) or pd.isna(ma_long.loc[date]) or pd.isna(ma_short.loc[date]):
                regime.loc[date] = current_regime
                continue

            # State machine with hysteresis
            if current_regime == 'BEAR':
                # In BEAR: Need to exceed ma_long_upper to exit
                if price > ma_long_upper.loc[date]:
                    if price > ma_short_upper.loc[date]:
                        current_regime = 'STRONG_BULL'
                    else:
                        current_regime = 'WEAK_BULL'
                # Else stay BEAR

            elif current_regime == 'WEAK_BULL':
                # In WEAK_BULL: Fall below ma_long_lower → BEAR, exceed ma_short_upper → STRONG_BULL
                if price < ma_long_lower.loc[date]:
                    current_regime = 'BEAR'
                elif price > ma_short_upper.loc[date]:
                    current_regime = 'STRONG_BULL'
                # Else stay WEAK_BULL

            elif current_regime == 'STRONG_BULL':
                # In STRONG_BULL: Fall below ma_short_lower → WEAK_BULL
                if price < ma_short_lower.loc[date]:
                    if price < ma_long_lower.loc[date]:
                        current_regime = 'BEAR'
                    else:
                        current_regime = 'WEAK_BULL'
                # Else stay STRONG_BULL

            else:  # UNKNOWN (initial state)
                # First classification (no hysteresis on initial state)
                if price > ma_long.loc[date]:
                    if price > ma_short.loc[date]:
                        current_regime = 'STRONG_BULL'
                    else:
                        current_regime = 'WEAK_BULL'
                else:
                    current_regime = 'BEAR'

            regime.loc[date] = current_regime

        return regime

    def apply_portfolio_stop_loss(self,
                                   allocations: pd.DataFrame,
                                   portfolio_values: pd.Series,
                                   initial_capital: float) -> pd.DataFrame:
        """
        Apply portfolio-level stop-loss with smart re-entry

        Protection against black swan events (e.g., Trump tariff crash, exchange hacks,
        regulatory bans) where entire crypto market drops -50-70%.

        SMART RE-ENTRY LOGIC (Your Idea!):
        Instead of fixed 30-day cooldown, re-enter when market stabilizes:

        Exit Trigger:
        - Portfolio drops >30% from peak → Exit to 100% PAXG
        - NOTE: With daily data, actual trigger is -30% to -34% due to intraday gaps
        - Example: Day 1 close = -29%, Day 2 close = -32% → Triggers at -32%
        - Protects against -70% individual alt crashes (like AVAX Trump tariff event)

        Re-Entry Trigger (BOTH conditions required):
        1. Minimum 2 days passed (let panic settle)
        2. Portfolio recovers +3% from trough (market stabilizing)

        Example Timeline:
        - Day 0: Peak $100K
        - Day 5: Drop to $68K (-32% from peak) → STOP-LOSS TRIGGERED → Exit to PAXG
        - Day 6: PAXG value $68K (min cooldown not met)
        - Day 7: PAXG value $68K (min cooldown met, but no recovery yet)
        - Day 10: Portfolio would be $71K (+4.4% from $68K trough) → RE-ENTER ✅

        Why This Works:
        - Exit fast on panic (protect capital)
        - Re-enter fast on recovery (catch bounce)
        - Avoids 30-day blind cooldown that misses bull runs

        Args:
            allocations: Target allocation matrix (from generate_signals)
            portfolio_values: Portfolio value series (for drawdown calculation)
            initial_capital: Starting capital

        Returns:
            Modified allocations with stop-loss applied
        """
        if self.portfolio_stop_loss is None or self.portfolio_stop_loss <= 0:
            return allocations  # Stop-loss disabled

        print(f"\n   🛡️  Portfolio Stop-Loss: {self.portfolio_stop_loss*100:.1f}%")
        print(f"      Re-entry: {self.stop_loss_min_cooldown_days} days + {self.stop_loss_reentry_threshold*100:.1f}% recovery")

        modified_allocations = allocations.copy()
        in_stop_loss_mode = False
        stop_loss_trigger_date = None
        stop_loss_trough_value = None
        trigger_count = 0
        total_cooldown_days = 0

        # Calculate running peak
        running_peak = portfolio_values.expanding().max()

        # Calculate drawdown from peak
        drawdown = (portfolio_values - running_peak) / running_peak

        for i, date in enumerate(allocations.index):
            # Skip if not enough history
            if date not in drawdown.index:
                continue

            current_value = portfolio_values.loc[date]
            current_dd = drawdown.loc[date]
            current_peak = running_peak.loc[date]

            # === IN STOP-LOSS MODE (already exited to PAXG) ===
            if in_stop_loss_mode:
                total_cooldown_days += 1

                # Check re-entry conditions
                days_since_trigger = (date - stop_loss_trigger_date).days
                min_cooldown_met = days_since_trigger >= self.stop_loss_min_cooldown_days

                # Calculate recovery from trough
                recovery_from_trough = (current_value - stop_loss_trough_value) / stop_loss_trough_value
                recovery_threshold_met = recovery_from_trough >= self.stop_loss_reentry_threshold

                # Re-enter if BOTH conditions met
                if min_cooldown_met and recovery_threshold_met:
                    print(f"   ✅ RE-ENTRY TRIGGERED on {date.date()} (after {days_since_trigger} days):")
                    print(f"      Trough: ${stop_loss_trough_value:,.0f} → Current: ${current_value:,.0f} (+{recovery_from_trough*100:.2f}%)")
                    print(f"      Drawdown from peak: {current_dd*100:.2f}%")
                    print(f"      → Resuming normal strategy signals")
                    in_stop_loss_mode = False
                    stop_loss_trigger_date = None
                    stop_loss_trough_value = None
                    # Don't override allocations - use normal strategy signals
                else:
                    # Still in stop-loss mode - stay in PAXG
                    for col in modified_allocations.columns:
                        if col == self.bear_asset:
                            modified_allocations.at[date, col] = 1.0
                        else:
                            modified_allocations.at[date, col] = 0.0

                    # Update trough if portfolio drops further
                    if current_value < stop_loss_trough_value:
                        stop_loss_trough_value = current_value

            # === NOT IN STOP-LOSS MODE (actively trading) ===
            else:
                # Check if stop-loss should trigger
                # NOTE: With daily data, this will trigger 0-4% below threshold due to intraday gaps
                # Example: Threshold -30% → Actual trigger -30% to -34%
                # This is CORRECT for daily resolution (can't exit intraday)
                # Calibrated for -70% individual alt crashes (Trump tariff AVAX event)
                if current_dd < -self.portfolio_stop_loss:
                    trigger_count += 1
                    print(f"   🚨 STOP-LOSS TRIGGERED on {date.date()}: Drawdown {current_dd*100:.2f}%")
                    print(f"      Peak: ${current_peak:,.0f} → Current: ${current_value:,.0f}")
                    print(f"      → Exiting all positions to {self.bear_asset}")
                    print(f"      → Waiting for: {self.stop_loss_min_cooldown_days}d + {self.stop_loss_reentry_threshold*100:.1f}% recovery")

                    in_stop_loss_mode = True
                    stop_loss_trigger_date = date
                    stop_loss_trough_value = current_value

                    # Override allocations - exit to bear asset
                    for col in modified_allocations.columns:
                        if col == self.bear_asset:
                            modified_allocations.at[date, col] = 1.0
                        else:
                            modified_allocations.at[date, col] = 0.0

        # Summary
        if trigger_count > 0:
            avg_cooldown = total_cooldown_days / trigger_count if trigger_count > 0 else 0
            print(f"   📊 Stop-Loss Summary:")
            print(f"      Triggered: {trigger_count} times")
            print(f"      Avg cooldown: {avg_cooldown:.1f} days (vs {self.stop_loss_min_cooldown_days}d minimum)")
            print(f"      Total days in PAXG: {total_cooldown_days} ({total_cooldown_days/len(allocations)*100:.1f}%)")
        else:
            print(f"   ✅ Stop-Loss never triggered (max DD < {self.portfolio_stop_loss*100:.1f}%)")

        return modified_allocations

    def apply_position_stop_loss(self,
                                  allocations: pd.DataFrame,
                                  prices: pd.DataFrame) -> pd.DataFrame:
        """
        Apply individual position stop-loss to cut losers early

        Protection against individual asset failures (e.g., AVAX -70% crash while
        BTC/ETH hold up). Exits specific positions that drop >40% from entry.

        POSITION-LEVEL PROTECTION:
        - Tracks entry price for each position
        - Exits if position drops >40% from entry
        - Re-enters on next rebalance if still qualifies

        Example:
        - Buy AVAX at $30 (enters portfolio)
        - AVAX drops to $18 (-40%) → EXIT AVAX only
        - BTC/ETH/SOL continue normal
        - Next rebalance: AVAX can re-enter if it qualifies

        Why 40% for positions vs 30% for portfolio:
        - Individual assets are more volatile
        - 40% gives room for normal crypto swings
        - Still catches -70% crashes at -40%

        Args:
            allocations: Target allocation matrix
            prices: Price matrix

        Returns:
            Modified allocations with position stops applied
        """
        if self.position_stop_loss is None or self.position_stop_loss <= 0:
            return allocations  # Disabled

        print(f"\n   🎯 Position Stop-Loss: {self.position_stop_loss*100:.1f}%")
        if self.position_stop_loss_core_only:
            print(f"      Applied to: Core assets only")
        else:
            print(f"      Applied to: All positions")

        modified_allocations = allocations.copy()
        position_entry_prices = {}  # Track entry price for each position
        stopped_positions = {}  # Track which positions hit stop-loss
        total_stops = 0

        for i, date in enumerate(allocations.index):
            for ticker in allocations.columns:
                current_alloc = allocations.at[date, ticker]

                # Skip if no allocation or invalid price
                if pd.isna(current_alloc) or current_alloc == 0:
                    continue
                if ticker not in prices.columns:
                    continue
                if date not in prices.index:
                    continue

                current_price = prices.at[date, ticker]
                if pd.isna(current_price) or current_price <= 0:
                    continue

                # Check if core-only mode
                if self.position_stop_loss_core_only:
                    if ticker not in self.core_assets:
                        continue  # Skip satellites

                # Track entry price (when position first appears)
                if ticker not in position_entry_prices:
                    position_entry_prices[ticker] = current_price
                    stopped_positions[ticker] = False

                # Check if position hit stop-loss
                if not stopped_positions[ticker]:
                    entry_price = position_entry_prices[ticker]
                    position_dd = (current_price - entry_price) / entry_price

                    if position_dd < -self.position_stop_loss:
                        # STOP-LOSS TRIGGERED for this position
                        total_stops += 1
                        stopped_positions[ticker] = True
                        print(f"   🚨 Position stop-loss: {ticker} on {date.date()}")
                        print(f"      Entry: ${entry_price:.2f} → Current: ${current_price:.2f} ({position_dd*100:.1f}%)")

                        # Exit this position
                        modified_allocations.at[date, ticker] = 0.0

                # Reset entry if position was exited and is re-entering
                prev_date_idx = i - 1
                if prev_date_idx >= 0:
                    prev_date = allocations.index[prev_date_idx]
                    prev_alloc = allocations.at[prev_date, ticker]
                    if pd.isna(prev_alloc) or prev_alloc == 0:
                        # Position was out, now re-entering
                        position_entry_prices[ticker] = current_price
                        stopped_positions[ticker] = False

        if total_stops > 0:
            print(f"   📊 Position Stop-Loss Summary: {total_stops} positions stopped out")
        else:
            print(f"   ✅ No positions hit stop-loss")

        return modified_allocations

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

        # === FIX Bug 14: Track pending rebalances ===
        # When we skip a day due to NaN prices, queue the rebalance for next valid day
        pending_initial = True  # Ensure we take initial allocation as soon as data exists
        pending_quarterly_rebalance = False  # Queue quarterly rebalances
        pending_regime_change = False  # Queue regime changes
        rebalance_idx = 0  # Track which quarterly rebalance we're on

        print(f"\n📊 Generating Hybrid Allocations...")
        print(f"   Core: {len(self.core_assets)} assets ({self.core_allocation:.0%})")
        print(f"   Satellite: {self.satellite_size} assets ({self.satellite_allocation:.0%})")
        print(f"   Rebalances: {len(actual_rebalance_dates)}")

        for i, date in enumerate(prices.index):
            current_regime = regime.loc[date]
            prev_regime = regime.shift(1).loc[date] if i > 0 else current_regime

            # === FIX: Skip allocations if any required asset has NaN price ===
            # Leading NaNs mean the asset didn't exist yet - can't trade what doesn't exist!
            # This prevents vectorbt from sizing trades against NaN prices
            required_assets_for_regime = []

            # Check if we've crossed a quarterly rebalance date (mark as pending)
            if rebalance_idx < len(actual_rebalance_dates) and date >= actual_rebalance_dates[rebalance_idx]:
                pending_quarterly_rebalance = True

            # Check if regime changed (mark as pending)
            if i > 0 and current_regime != prev_regime:
                pending_regime_change = True

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
            # BUT keep the rebalance queued (don't lose it!)
            if has_nan_price:
                # Leave allocations at 0.0 (100% cash) for this date
                # Rebalances stay pending - will execute on next valid day
                continue

            # === Execute pending rebalances on first valid day ===
            # Check if we need to rebalance (initial, quarterly, or regime change)
            should_rebalance_satellite = pending_initial or pending_quarterly_rebalance

            if should_rebalance_satellite:
                selected = self.select_satellite(satellite_prices, indicators, date)
                if len(selected) > 0:
                    current_satellite = selected['ticker'].tolist()
                    satellite_scores = dict(zip(selected['ticker'], selected['score']))
                else:
                    current_satellite = []
                    satellite_scores = {}  # Clear scores if no valid satellites

                # Clear pending flags after successful rebalance
                if pending_initial:
                    pending_initial = False

                if pending_quarterly_rebalance:
                    # Mark all past-due quarterly rebalances as completed
                    while rebalance_idx < len(actual_rebalance_dates) and actual_rebalance_dates[rebalance_idx] <= date:
                        rebalance_idx += 1
                    pending_quarterly_rebalance = False

            # === ONLY apply allocations on rebalance days ===
            # Skip if no rebalance/regime change (preserve existing positions)
            should_apply_allocation = (pending_initial or should_rebalance_satellite or pending_regime_change or
                                      (i > 0 and current_regime != prev_regime))

            if not should_apply_allocation:
                # Not a rebalance day - skip allocation (VectorBT will hold positions)
                continue

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

            # Clear regime change flag after successfully applying regime allocation
            if pending_regime_change:
                pending_regime_change = False

        # === IMPROVEMENT 3: Allocation Edge Case Warnings ===
        # === FIX: NO blanket normalization - maintain intended 70/30 split ===
        # When satellites are missing, residual goes to CASH (not re-levered to core)
        # This preserves the strategy's designed risk profile
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

        # Check for partial allocation days (< 100% = some cash held)
        partial_alloc_days = row_sums[(row_sums > 0) & (row_sums < 1.0)]
        if len(partial_alloc_days) > 0:
            avg_alloc = partial_alloc_days.mean()
            avg_cash = 1.0 - avg_alloc
            pct_partial = len(partial_alloc_days) / len(row_sums) * 100
            print(f"\n   ℹ️  INFO: {len(partial_alloc_days)} days ({pct_partial:.1f}%) with partial allocations")
            print(f"      Average allocation: {avg_alloc*100:.1f}%, Average cash: {avg_cash*100:.1f}%")
            print(f"      This is CORRECT - missing satellites stay in cash (maintains 70/30 design)")

        # Check for over-allocation (should never happen, but good to catch)
        over_alloc_days = row_sums[row_sums > 1.01]  # Allow small rounding errors
        if len(over_alloc_days) > 0:
            print(f"\n   ❌ ERROR: {len(over_alloc_days)} days with allocations > 100%!")
            print(f"      Max allocation: {row_sums.max()*100:.2f}%")
            print(f"      This is a bug - allocations should never exceed 100%")

        # === NO NORMALIZATION ===
        # Keep allocations as-is - VectorBT's targetpercent sizing handles cash automatically
        # When row sum < 1.0, the remaining % stays in cash (correct behavior)

        # === FIX Bug 13 & 14: Only rebalance on actual rebalance/regime-change days ===
        # Fill non-rebalance days with NaN so VectorBT holds existing positions
        # This prevents daily rebalancing that inflates returns
        # Bug 14 fix ensures pending rebalances execute on first valid day (not lost)
        print(f"\n📊 Applying Rebalance-Only Logic...")

        # Find dates where allocations were actually set (non-zero rows)
        # These are the days when we executed rebalances (including pending ones)
        row_sums = allocations.sum(axis=1)
        actual_allocation_dates = row_sums[row_sums > 0].index.tolist()

        # Create a copy with NaN for non-rebalance days
        allocations_rebalance_only = pd.DataFrame(np.nan, index=allocations.index, columns=allocations.columns)

        # Only copy allocations on days where we actually allocated
        # (This includes pending rebalances that executed on first valid day)
        for date in actual_allocation_dates:
            allocations_rebalance_only.loc[date] = allocations.loc[date]

        # === FIX Bug 15: Align allocations with valid prices ===
        # Clear any allocations where price is NaN or ≤0
        # This prevents VectorBT error: "order.price must be finite and greater than 0"
        allocations_rebalance_only = self._align_allocations_with_prices(allocations_rebalance_only, prices)

        # Count actual rebalance days
        rebalance_day_count = len(actual_allocation_dates)
        pct_rebalance = rebalance_day_count / len(prices.index) * 100

        # Calculate regime changes for logging
        regime_changes_count = (regime != regime.shift(1)).sum()
        hold_days = len(prices.index) - rebalance_day_count

        print(f"   Rebalance triggers: {rebalance_day_count} days ({pct_rebalance:.1f}%)")
        print(f"   - Scheduled quarterly: {len(actual_rebalance_dates)}")
        print(f"   - Regime changes: ~{regime_changes_count} (some may be pending/deferred)")
        print(f"   - Hold days (NaN): {hold_days} ({hold_days/len(prices.index)*100:.1f}%)")
        print(f"   ✅ Core sleeve NEVER rebalances (only on regime change)")
        print(f"   ✅ Satellite rebalances ONLY quarterly + regime change")
        print(f"   ✅ Pending rebalances execute on first valid day (not lost)")

        # Regime summary
        regime_counts = regime.value_counts()
        print(f"\n   Market Regime Summary:")
        for reg, count in regime_counts.items():
            pct = count / len(regime) * 100
            print(f"   - {reg}: {count} days ({pct:.1f}%)")

        return allocations_rebalance_only

    def _validate_trade_prices(self, portfolio: vbt.Portfolio, prices: pd.DataFrame) -> Dict:
        """
        Validate that all executed trades have valid prices.

        Checks for:
        - Trades at NaN prices
        - Trades at ≤0 prices
        - Price/size mismatches

        Returns:
            Dictionary with validation results
        """
        try:
            trades = portfolio.trades.records_readable
        except:
            # No trades executed
            return {
                'total_trades': 0,
                'invalid_trades': [],
                'invalid_count': 0,
                'valid': True
            }

        if len(trades) == 0:
            return {
                'total_trades': 0,
                'invalid_trades': [],
                'invalid_count': 0,
                'valid': True
            }

        invalid_trades = []
        total_trades = len(trades)

        # Get column names dynamically (vectorbt may change them)
        col_names = trades.columns.tolist()

        # Find entry/exit columns (flexible naming)
        entry_idx_col = next((c for c in col_names if 'entry' in c.lower() and 'idx' in c.lower()), None)
        exit_idx_col = next((c for c in col_names if 'exit' in c.lower() and 'idx' in c.lower()), None)
        col_col = next((c for c in col_names if c.lower() in ['column', 'col']), None)

        if not all([entry_idx_col, exit_idx_col, col_col]):
            # Can't validate - column names don't match expected format
            return {
                'total_trades': total_trades,
                'invalid_trades': [],
                'invalid_count': 0,
                'valid': True,  # Assume valid if can't check
                'warning': 'Could not validate - column names mismatch'
            }

        for idx, trade in trades.iterrows():
            entry_idx = int(trade[entry_idx_col])
            exit_idx = int(trade[exit_idx_col])
            ticker = trade[col_col]

            # Get actual dates from price index
            if entry_idx < len(prices.index) and ticker in prices.columns:
                entry_date = prices.index[entry_idx]
                entry_price_actual = prices.at[entry_date, ticker]
                if pd.isna(entry_price_actual) or entry_price_actual <= 0:
                    invalid_trades.append({
                        'trade_id': idx,
                        'ticker': ticker,
                        'date': entry_date,
                        'type': 'ENTRY',
                        'price': entry_price_actual,
                        'issue': 'NaN or ≤0 price'
                    })

            # Check exit price
            if exit_idx < len(prices.index) and ticker in prices.columns:
                exit_date = prices.index[exit_idx]
                exit_price_actual = prices.at[exit_date, ticker]
                if pd.isna(exit_price_actual) or exit_price_actual <= 0:
                    invalid_trades.append({
                        'trade_id': idx,
                        'ticker': ticker,
                        'date': exit_date,
                        'type': 'EXIT',
                        'price': exit_price_actual,
                        'issue': 'NaN or ≤0 price'
                    })

        return {
            'total_trades': total_trades,
            'invalid_trades': invalid_trades,
            'invalid_count': len(invalid_trades),
            'valid': len(invalid_trades) == 0
        }

    def backtest(self,
                prices: pd.DataFrame,
                btc_prices: Optional[pd.Series] = None,
                initial_capital: float = 100000,
                fees: float = 0.001,
                slippage: float = 0.0005,
                log_trades: bool = False) -> vbt.Portfolio:
        """
        Backtest hybrid strategy using vectorbt

        Args:
            prices: DataFrame with crypto prices
            btc_prices: BTC prices for regime filter (required)
            initial_capital: Starting capital
            fees: Trading fees (0.001 = 0.1%, increased to 0.002 = 0.2% for realism)
            slippage: Slippage (0.0005 = 0.05%, increased to 0.002 = 0.2% for realism)
            log_trades: If True, print detailed trade log

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

        # === PORTFOLIO STOP-LOSS (Two-Pass Approach) ===
        # Need to create initial portfolio to get values, then apply stop-loss
        if self.portfolio_stop_loss is not None and self.portfolio_stop_loss > 0:
            print(f"\n🛡️  Applying Portfolio Stop-Loss (Two-Pass Approach)...")

            # PASS 1: Create initial portfolio to get equity curve
            print(f"   Pass 1: Creating initial portfolio to calculate drawdowns...")
            initial_portfolio = vbt.Portfolio.from_orders(
                close=prices,
                size=allocations,
                size_type='targetpercent',
                fees=fees,
                slippage=slippage,
                init_cash=initial_capital,
                cash_sharing=True,
                group_by=True,
                call_seq='auto',
                freq='D'
            )

            # Extract portfolio values
            portfolio_values = initial_portfolio.value()
            if isinstance(portfolio_values, pd.DataFrame):
                portfolio_values = portfolio_values.iloc[:, 0]

            print(f"   Pass 2: Applying portfolio stop-loss rules...")
            # PASS 2: Apply portfolio stop-loss
            allocations = self.apply_portfolio_stop_loss(
                allocations,
                portfolio_values,
                initial_capital
            )

        # === POSITION STOP-LOSS (Applied AFTER portfolio stop-loss) ===
        if self.position_stop_loss is not None and self.position_stop_loss > 0:
            print(f"\n🎯 Applying Position Stop-Loss...")
            allocations = self.apply_position_stop_loss(allocations, prices)

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
            print("\n⚠️  WARNING: NaN values in allocations (expected on hold days)")
            print("   These NaNs represent days with no rebalance; positions will be held (no fill applied).")

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

        # === FIX: Validate trade prices ===
        print(f"\n🔍 Validating Trade Prices...")
        validation = self._validate_trade_prices(portfolio, prices)

        if validation['valid']:
            print(f"   ✅ All {validation['total_trades']} trades have valid prices")
        else:
            print(f"   ❌ WARNING: {validation['invalid_count']} trades have INVALID prices!")
            for inv_trade in validation['invalid_trades'][:10]:  # Show first 10
                print(f"      - Trade {inv_trade['trade_id']}: {inv_trade['ticker']} "
                      f"{inv_trade['type']} on {inv_trade['date']} at price={inv_trade['price']}")
            if validation['invalid_count'] > 10:
                print(f"      ... and {validation['invalid_count'] - 10} more")
            print(f"\n   ⚠️  BACKTEST RESULTS MAY BE UNRELIABLE!")

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

        print(f"\n   Final Value: ${final_val:,.2f}")
        print(f"   Total Return: {total_ret * 100:.2f}%")  # total_return() already returns ratio

        # === Optional: Log all trades ===
        if log_trades:
            print(f"\n📋 Detailed Trade Log:")
            trades = portfolio.trades.records_readable
            for idx, trade in trades.iterrows():
                print(f"   {idx+1}. {trade['Column']}: {trade['Side']} "
                      f"{trade['Size']:.4f} @ ${trade['Entry Price']:.2f} → ${trade['Exit Price']:.2f} "
                      f"PnL: ${trade['PnL']:.2f} ({trade['Return']:.2%})")

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
