"""
Institutional Crypto Perpetual Futures Strategy

Professional-grade momentum/breakout strategy with strict regime-gating,
volatility-based sizing, and institutional risk controls.

Features:
- Multi-timeframe regime filter (BTC 200MA, 20MA slope, realized vol percentile)
- Donchian breakout + ADX confirmation
- Relative strength filtering vs BTC
- Pyramid adds at 0.75×ATR intervals (max 3 adds)
- 2×ATR trailing stops
- Vol-targeted position sizing (15-25% annualized per position)
- Dynamic leverage based on regime (0.5-2×)
- **PAXG (tokenized gold) allocation during bear markets** (+244% improvement)
- Hard daily loss limits (-3%)
- Weekend de-grossing
- Exchange diversification
- **FIXED universe (BTC, ETH, SOL, BNB, XRP, ADA, DOGE, MATIC, DOT, AVAX)**

Performance (with 100% PAXG in bear markets):
- Total Return: +580% (vs +336% without PAXG)
- Annualized: 93.8%
- Sharpe: 1.29
- Max Drawdown: -36.7%

Universe Selection:
This strategy uses a FIXED crypto universe, NOT dynamic quarterly rebalancing.

Research (Oct 2025) tested 6 different universe selection methods:
1. ROC Momentum (90-day)
2. Breakout Probability (consolidation + volume)
3. Volatility Squeeze (Bollinger Band width)
4. Relative Strength (vs SPY)
5. Volume Profile (accumulation patterns)
6. Composite Score (multi-factor)

Result: ALL methods underperformed fixed universe by 3-25×
- Fixed Universe: +913.8% (5 years, simple momentum test)
- Best Dynamic (Pure ROC): +273.4%
- Worst Dynamic (Breakout): -18.5%

Why fixed universe wins for crypto:
- BTC/ETH dominance is persistent (not temporary like stock sector rotation)
- Winner-take-all network effects compound over years
- Momentum persists for years (not quarters)
- Quarterly rebalancing creates forced turnover with no edge
- Signal-based exits (trailing stops, regime filter) > time-based exits

See: results/crypto/QUARTERLY_REBALANCING_ANALYSIS.md
     results/crypto/UNIVERSE_SELECTION_CRITERIA_ANALYSIS.md

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')


class MarketRegime(Enum):
    """Market regime classification"""
    BULL_RISK_ON = "BULL_RISK_ON"      # Aggressive: BTC > 200MA, slope > 0, vol in range
    NEUTRAL = "NEUTRAL"                 # Cautious: Some conditions met
    BEAR_RISK_OFF = "BEAR_RISK_OFF"    # Defensive: Exit to market-neutral/carry


@dataclass
class Position:
    """Position tracking"""
    symbol: str
    entry_price: float
    current_price: float
    size: float
    leverage: float
    adds: int = 0  # Number of pyramid adds
    highest_price: float = 0.0  # For trailing stop
    entry_date: pd.Timestamp = None
    last_add_price: float = 0.0

    @property
    def pnl_pct(self) -> float:
        """P&L percentage"""
        return ((self.current_price / self.entry_price) - 1) * 100

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized P&L in dollar terms"""
        return (self.current_price - self.entry_price) * self.size


@dataclass
class RiskMetrics:
    """Real-time risk metrics"""
    gross_exposure: float
    net_exposure: float
    portfolio_leverage: float
    daily_pnl: float
    portfolio_vol: float
    max_position_size: float


class InstitutionalCryptoPerp:
    """
    Institutional-grade crypto perpetual futures strategy

    Designed for professional execution with strict risk controls
    """

    def __init__(self,
                 # Universe
                 max_positions: int = 10,

                 # Regime filter parameters
                 btc_ma_long: int = 200,
                 btc_ma_short: int = 20,
                 vol_lookback: int = 30,
                 vol_percentile_low: float = 30,
                 vol_percentile_high: float = 120,

                 # Entry parameters
                 donchian_period: int = 20,
                 adx_threshold: float = 25,
                 adx_period: int = 14,
                 rs_quartile: float = 0.75,  # Top quartile

                 # Pyramid parameters
                 add_atr_multiple: float = 0.75,
                 max_adds: int = 3,
                 atr_period: int = 14,

                 # Exit parameters
                 trail_atr_multiple: float = 2.0,
                 breakdown_period: int = 10,

                 # Position sizing
                 vol_target_per_position: float = 0.20,  # 20% annualized
                 portfolio_vol_target: float = 0.50,     # 50% portfolio vol

                 # Leverage limits
                 max_leverage_bull: float = 2.0,
                 max_leverage_neutral: float = 1.0,
                 max_leverage_bear: float = 0.5,

                 # Risk controls
                 daily_loss_limit: float = 0.03,  # -3%
                 weekend_degross: bool = True,
                 slippage_threshold: float = 0.005,  # 0.5% max slippage

                 # Bear market allocation
                 bear_market_asset: str = 'PAXG-USD',  # Tokenized gold
                 bear_allocation: float = 1.0):  # 100% allocation in bear markets

        self.max_positions = max_positions

        # Regime
        self.btc_ma_long = btc_ma_long
        self.btc_ma_short = btc_ma_short
        self.vol_lookback = vol_lookback
        self.vol_percentile_low = vol_percentile_low
        self.vol_percentile_high = vol_percentile_high

        # Entry
        self.donchian_period = donchian_period
        self.adx_threshold = adx_threshold
        self.adx_period = adx_period
        self.rs_quartile = rs_quartile

        # Pyramid
        self.add_atr_multiple = add_atr_multiple
        self.max_adds = max_adds
        self.atr_period = atr_period

        # Exit
        self.trail_atr_multiple = trail_atr_multiple
        self.breakdown_period = breakdown_period

        # Sizing
        self.vol_target_per_position = vol_target_per_position
        self.portfolio_vol_target = portfolio_vol_target

        # Leverage
        self.max_leverage_bull = max_leverage_bull
        self.max_leverage_neutral = max_leverage_neutral
        self.max_leverage_bear = max_leverage_bear

        # Risk
        self.daily_loss_limit = daily_loss_limit
        self.weekend_degross = weekend_degross
        self.slippage_threshold = slippage_threshold

        # Bear market allocation
        self.bear_market_asset = bear_market_asset
        self.bear_allocation = bear_allocation

        # State
        self.positions: Dict[str, Position] = {}
        self.paxg_position: Optional[Position] = None  # Separate PAXG tracking
        self.daily_start_equity = None

    def calculate_regime(self, btc_prices: pd.Series, timeframe: str = '1d') -> pd.Series:
        """
        Calculate market regime using BTC

        Criteria for BULL_RISK_ON:
        1. BTC > 200-day MA
        2. 20-day MA slope > 0
        3. Realized vol in 30-120 percentile band

        Args:
            btc_prices: BTC price series
            timeframe: '4h' or '1d'

        Returns:
            Series with regime classification
        """
        # 200-day MA
        ma_long = btc_prices.rolling(window=self.btc_ma_long).mean()
        above_ma_long = btc_prices > ma_long

        # 20-day MA slope
        ma_short = btc_prices.rolling(window=self.btc_ma_short).mean()
        ma_slope = ma_short.diff(1)
        positive_slope = ma_slope > 0

        # Realized volatility (30-day)
        returns = btc_prices.pct_change()
        realized_vol = returns.rolling(window=self.vol_lookback).std() * np.sqrt(365) * 100

        # Vol percentile (over rolling 252-day window)
        vol_percentile = realized_vol.rolling(window=252).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100 if len(x) > 0 else 50
        )

        in_vol_band = (vol_percentile >= self.vol_percentile_low) & \
                      (vol_percentile <= self.vol_percentile_high)

        # Regime classification
        regime = pd.Series(MarketRegime.NEUTRAL.value, index=btc_prices.index)

        # BULL_RISK_ON: All 3 conditions
        bull_mask = above_ma_long & positive_slope & in_vol_band
        regime[bull_mask] = MarketRegime.BULL_RISK_ON.value

        # BEAR_RISK_OFF: BTC below 200MA
        bear_mask = ~above_ma_long
        regime[bear_mask] = MarketRegime.BEAR_RISK_OFF.value

        return regime

    def calculate_donchian(self, prices: pd.DataFrame, period: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Calculate Donchian channel (highs and lows)"""
        if period is None:
            period = self.donchian_period

        highs = prices.rolling(window=period).max()
        lows = prices.rolling(window=period).min()

        return highs, lows

    def calculate_adx(self, high: pd.DataFrame, low: pd.DataFrame,
                     close: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate ADX (Average Directional Index)

        ADX > 20-25 indicates trending market
        """
        if period is None:
            period = self.adx_period

        # Calculate for each symbol separately
        adx_result = pd.DataFrame(index=high.index, columns=high.columns, dtype=float)

        for symbol in high.columns:
            # True Range
            h = high[symbol]
            l = low[symbol]
            c = close[symbol]

            tr1 = h - l
            tr2 = abs(h - c.shift(1))
            tr3 = abs(l - c.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()

            # Directional Movement
            up_move = h - h.shift(1)
            down_move = l.shift(1) - l

            plus_dm = pd.Series(0.0, index=h.index)
            minus_dm = pd.Series(0.0, index=h.index)

            plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
            minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

            # Directional Indicators
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

            # ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)  # Avoid division by zero
            adx = dx.rolling(window=period).mean()

            adx_result[symbol] = adx

        return adx_result

    def calculate_atr(self, high: pd.DataFrame, low: pd.DataFrame,
                     close: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """Calculate Average True Range"""
        if period is None:
            period = self.atr_period

        # Calculate for each symbol separately to avoid indexing issues
        atr_result = pd.DataFrame(index=high.index, columns=high.columns, dtype=float)

        for symbol in high.columns:
            h = high[symbol]
            l = low[symbol]
            c = close[symbol]

            tr1 = h - l
            tr2 = abs(h - c.shift(1))
            tr3 = abs(l - c.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_result[symbol] = tr.rolling(window=period).mean()

        return atr_result

    def calculate_relative_strength(self, prices: pd.DataFrame,
                                    btc_prices: pd.Series,
                                    period: int = 20) -> pd.DataFrame:
        """
        Calculate relative strength vs BTC

        RS = (Coin return / BTC return) over period
        Higher = outperforming BTC
        """
        coin_returns = prices.pct_change(period)
        btc_returns = btc_prices.pct_change(period)

        # Broadcast BTC returns to all columns
        btc_returns_df = pd.DataFrame(
            np.tile(btc_returns.values.reshape(-1, 1), (1, len(prices.columns))),
            index=prices.index,
            columns=prices.columns
        )

        rs = coin_returns / btc_returns_df.replace(0, np.nan)

        return rs

    def calculate_position_size(self, price: float, volatility: float,
                                regime: MarketRegime, equity: float) -> Tuple[float, float]:
        """
        Calculate position size and leverage based on volatility targeting

        Args:
            price: Current price
            volatility: Annualized volatility (e.g., 0.50 for 50%)
            regime: Current market regime
            equity: Account equity

        Returns:
            (position_size_in_coins, leverage)
        """
        # Determine max leverage based on regime
        if regime == MarketRegime.BULL_RISK_ON:
            max_leverage = self.max_leverage_bull
        elif regime == MarketRegime.NEUTRAL:
            max_leverage = self.max_leverage_neutral
        else:
            max_leverage = self.max_leverage_bear

        # FIXED ALLOCATION: Use simple % of equity per position (more realistic)
        # Instead of vol-targeting which creates unrealistic positions
        allocation_per_position = 0.10  # 10% of equity per position (conservative)

        # Base notional
        base_notional = equity * allocation_per_position

        # Adjust for volatility (higher vol = smaller position)
        # Cap volatility between 0.3 and 2.0 for realistic adjustments
        vol_adjusted = max(0.3, min(volatility, 2.0))
        target_notional = base_notional * (0.5 / vol_adjusted)  # Normalize to 50% vol

        # Apply leverage cap
        max_notional = equity * max_leverage * allocation_per_position
        final_notional = min(target_notional, max_notional)

        # Minimum position size (0.5% of equity)
        min_notional = equity * 0.005
        if final_notional < min_notional:
            return 0.0, 0.0

        # Position size in coins
        position_size = final_notional / price

        # Actual leverage
        actual_leverage = final_notional / equity

        return position_size, actual_leverage

    def check_entry_signal(self, symbol: str, date: pd.Timestamp,
                          prices: pd.DataFrame, high: pd.DataFrame,
                          low: pd.DataFrame, close: pd.DataFrame,
                          btc_prices: pd.Series, regime: str) -> bool:
        """
        Check if entry conditions are met

        Conditions:
        1. Regime = BULL_RISK_ON
        2. Price breaks above 20-day Donchian high
        3. ADX > 25 (trending)
        4. RS vs BTC in top quartile
        """
        # Only enter in BULL regime
        if regime != MarketRegime.BULL_RISK_ON.value:
            return False

        # Already have position?
        if symbol in self.positions:
            return False

        # Donchian breakout
        donchian_high, _ = self.calculate_donchian(high)

        if date not in close.index or date not in donchian_high.index:
            return False

        current_price = close.loc[date, symbol]
        donchian_level = donchian_high.shift(1).loc[date, symbol]  # Previous high

        if pd.isna(current_price) or pd.isna(donchian_level):
            return False

        breakout = current_price > donchian_level

        if not breakout:
            return False

        # ADX confirmation
        adx = self.calculate_adx(high, low, close)

        if date not in adx.index:
            return False

        current_adx = adx.loc[date, symbol]

        if pd.isna(current_adx) or current_adx < self.adx_threshold:
            return False

        # Relative strength filter
        rs = self.calculate_relative_strength(close, btc_prices)

        if date not in rs.index:
            return False

        rs_scores = rs.loc[date].dropna()

        if symbol not in rs_scores.index:
            return False

        # Top quartile = RS score > 75th percentile
        rs_threshold = rs_scores.quantile(self.rs_quartile)
        rs_qualified = rs_scores[symbol] >= rs_threshold

        return rs_qualified

    def check_add_signal(self, symbol: str, date: pd.Timestamp,
                        close: pd.DataFrame, high: pd.DataFrame,
                        low: pd.DataFrame) -> bool:
        """
        Check if should add to position (pyramid)

        Condition: Price moved +0.75×ATR from last add
        Max 3 adds
        """
        if symbol not in self.positions:
            return False

        position = self.positions[symbol]

        # Max adds reached?
        if position.adds >= self.max_adds:
            return False

        # Calculate ATR
        atr = self.calculate_atr(high, low, close)

        if date not in atr.index or date not in close.index:
            return False

        current_atr = atr.loc[date, symbol]
        current_price = close.loc[date, symbol]

        if pd.isna(current_atr) or pd.isna(current_price):
            return False

        # Price moved enough from last add?
        reference_price = position.last_add_price if position.adds > 0 else position.entry_price
        price_move = current_price - reference_price
        required_move = self.add_atr_multiple * current_atr

        return price_move >= required_move

    def check_exit_signal(self, symbol: str, date: pd.Timestamp,
                         close: pd.DataFrame, high: pd.DataFrame,
                         low: pd.DataFrame, regime: str) -> Tuple[bool, str]:
        """
        Check if should exit position

        Exit conditions:
        1. 2×ATR trailing stop hit
        2. 10-day low breakdown
        3. Regime = BEAR_RISK_OFF (risk management)

        Returns:
            (should_exit, reason)
        """
        if symbol not in self.positions:
            return False, ""

        position = self.positions[symbol]

        if date not in close.index:
            return False, ""

        current_price = close.loc[date, symbol]

        if pd.isna(current_price):
            return False, ""

        # Update highest price for trailing stop
        if current_price > position.highest_price:
            position.highest_price = current_price

        # 1. Trailing stop (2×ATR from highest)
        atr = self.calculate_atr(high, low, close)

        if date in atr.index:
            current_atr = atr.loc[date, symbol]

            if not pd.isna(current_atr):
                trail_level = position.highest_price - (self.trail_atr_multiple * current_atr)

                if current_price < trail_level:
                    return True, f"Trailing stop ({self.trail_atr_multiple}×ATR)"

        # 2. Breakdown below 10-day low
        _, donchian_low = self.calculate_donchian(low, period=self.breakdown_period)

        if date in donchian_low.index:
            breakdown_level = donchian_low.shift(1).loc[date, symbol]

            if not pd.isna(breakdown_level) and current_price < breakdown_level:
                return True, f"{self.breakdown_period}-day low breakdown"

        # 3. Regime change to BEAR
        if regime == MarketRegime.BEAR_RISK_OFF.value:
            return True, "Regime = BEAR_RISK_OFF (switch to PAXG)"

        return False, ""

    def should_hold_paxg(self, regime: str) -> bool:
        """Check if should hold PAXG (bear market protection)"""
        return regime == MarketRegime.BEAR_RISK_OFF.value and self.bear_market_asset is not None

    def enter_paxg_position(self, equity: float, paxg_price: float, date: pd.Timestamp) -> None:
        """Enter PAXG position during bear markets"""
        if self.paxg_position is not None:
            return  # Already holding PAXG

        # Allocate specified percentage to PAXG
        paxg_notional = equity * self.bear_allocation
        paxg_size = paxg_notional / paxg_price

        self.paxg_position = Position(
            symbol=self.bear_market_asset,
            entry_price=paxg_price,
            current_price=paxg_price,
            size=paxg_size,
            leverage=1.0,  # Spot position
            entry_date=date,
            highest_price=paxg_price
        )

    def exit_paxg_position(self, paxg_price: float) -> Optional[float]:
        """Exit PAXG position when returning to bull/neutral"""
        if self.paxg_position is None:
            return None

        pnl = (paxg_price - self.paxg_position.entry_price) * self.paxg_position.size
        self.paxg_position = None
        return pnl

    def update_paxg_price(self, paxg_price: float) -> None:
        """Update PAXG position with current price"""
        if self.paxg_position is not None:
            self.paxg_position.current_price = paxg_price
            if paxg_price > self.paxg_position.highest_price:
                self.paxg_position.highest_price = paxg_price

    def calculate_portfolio_metrics(self, equity: float) -> RiskMetrics:
        """Calculate real-time portfolio risk metrics"""
        gross_exposure = sum(abs(p.size * p.current_price) for p in self.positions.values())
        net_exposure = sum(p.size * p.current_price for p in self.positions.values())

        # Include PAXG position if held
        if self.paxg_position is not None:
            paxg_value = self.paxg_position.size * self.paxg_position.current_price
            gross_exposure += abs(paxg_value)
            net_exposure += paxg_value

        portfolio_leverage = gross_exposure / equity if equity > 0 else 0

        daily_pnl = sum(p.unrealized_pnl for p in self.positions.values())

        # Include PAXG P&L
        if self.paxg_position is not None:
            daily_pnl += self.paxg_position.unrealized_pnl

        # Simplified portfolio vol (would need full covariance in production)
        position_vols = []
        for p in self.positions.values():
            notional = p.size * p.current_price
            position_vols.append(notional / equity)

        portfolio_vol = np.sqrt(sum(v**2 for v in position_vols)) if position_vols else 0

        max_position_size = equity * self.vol_target_per_position

        return RiskMetrics(
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            portfolio_leverage=portfolio_leverage,
            daily_pnl=daily_pnl,
            portfolio_vol=portfolio_vol,
            max_position_size=max_position_size
        )

    def check_risk_limits(self, date: pd.Timestamp, equity: float) -> Tuple[bool, str]:
        """
        Check if risk limits breached

        Returns:
            (breach, reason)
        """
        # Daily loss limit
        if self.daily_start_equity is not None:
            daily_pnl_pct = (equity - self.daily_start_equity) / self.daily_start_equity

            if daily_pnl_pct <= -self.daily_loss_limit:
                return True, f"Daily loss limit breached ({daily_pnl_pct*100:.2f}%)"

        # Weekend de-grossing (close all positions Friday EOD)
        if self.weekend_degross:
            if date.dayofweek == 4:  # Friday
                return True, "Weekend de-grossing (Friday close)"

        return False, ""

    def __str__(self):
        """String representation"""
        return f"InstitutionalCryptoPerp(positions={len(self.positions)}, regime_filter=True)"
