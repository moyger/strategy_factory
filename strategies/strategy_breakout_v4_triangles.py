"""
Strategy: Edgerunner Breakout Framework

This refactor evolves the London Breakout v4 triangle module into a modular
price-action breakout engine that captures the shared DNA behind elite
"volatility contraction → expansion" setups championed by traders such as
Mark Minervini, David Ryan, Oliver Kell, Patrick Walker, Dan Zanger,
Nicolas Darvas, and other U.S. Investing Championship winners.

The framework organises breakout tactics into reusable pattern profiles:
- Volatility Contraction Pattern (VCP)
- High Tight Flag (HTF)
- Ascending / Descending / Symmetrical Triangles
- Flat Base / Shelf consolidations
- Tight Flag / Pennant continuations

Each profile encapsulates detection heuristics, breakout triggers, and
risk controls while sharing a common execution, sizing, and trade
management pipeline. The design allows systematic codification of the
"Edgerunner" playbook with configurable market regime filters,
universe screening, and pattern-specific breakout logic.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure parent directory on path for CLI execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.indicators import atr, ema
from strategies.pattern_detector import PatternDetector


@dataclass
class PatternProfile:
    """Configuration for a breakout base archetype."""

    name: str
    detection: str  # triangle | flag | pennant | vcp | htf | flat_base | custom
    direction: str = "long"  # long | short | both
    lookback: int = 60
    min_pivots: int = 3
    pivot_window: int = 3
    r_squared_min: float = 0.6
    slope_tolerance: float = 0.0002
    atr_percentile: float = 0.25
    range_pct_max: float = 0.12
    volume_multiplier: float = 1.5
    breakout_buffer_pct: float = 0.0015
    time_window: Tuple[int, int] = (0, 23)
    momentum_required: bool = False
    allow_counter_trend: bool = False
    contraction_steps: int = 3
    pre_run_bars: int = 35
    pre_run_return: float = 0.9
    risk_reward_ratio: float = 2.0
    atr_multiple: float = 2.0
    min_reward_ticks: float = 0.0
    add_on_allowed: bool = True
    notes: str = ""


@dataclass
class BreakoutSignal:
    """Represents a ready-to-execute breakout trade."""

    direction: str
    entry_price: float
    stop_price: float
    target_price: float
    profile: PatternProfile
    pattern_id: Tuple[str, int, int]
    quality: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class EdgerunnerBreakoutStrategy:
    """Shared execution engine for volatility-contraction breakout strategies."""

    def __init__(
        self,
        symbol: str = "EURUSD",
        risk_percent: float = 0.5,
        initial_capital: float = 100_000.0,
        profiles: Optional[List[PatternProfile]] = None,
        price_tick: float = 0.0001,
        min_price: float = 1.0,
        min_avg_volume: float = 0.0,
        universe_lookback: int = 50,
        require_rs_new_high: bool = False,
        rs_window: int = 20,
        commission_per_unit: float = 0.0,
        slippage_per_unit: float = 0.0,
        max_notional_multiplier: float = 4.0,
        market_bias_mode: str = "auto",
        use_trailing_stop: bool = True,
    ) -> None:
        self.symbol = symbol
        self.price_tick = price_tick
        self.risk_percent = risk_percent
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position: Optional[Dict[str, Any]] = None
        self.traded_patterns: set = set()
        self.pattern_profiles = profiles or self._build_default_profiles()

        self.min_price = min_price
        self.min_avg_volume = min_avg_volume
        self.universe_lookback = universe_lookback
        self.require_rs_new_high = require_rs_new_high
        self.rs_window = rs_window
        self.commission_per_unit = commission_per_unit
        self.slippage_per_unit = slippage_per_unit
        self.max_notional_multiplier = max_notional_multiplier
        self.market_bias_mode = market_bias_mode
        self.use_trailing_stop = use_trailing_stop

        self._detector_cache: Dict[Tuple, PatternDetector] = {}
        self._max_pattern_lookback = (
            max((p.lookback for p in self.pattern_profiles), default=0)
            if self.pattern_profiles
            else 0
        )

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _build_default_profiles(self) -> List[PatternProfile]:
        """Default breakout archetypes based on Edgerunner playbook."""

        return [
            PatternProfile(
                name="vcp",
                detection="vcp",
                direction="long",
                lookback=80,
                contraction_steps=3,
                atr_percentile=0.2,
                range_pct_max=0.12,
                breakout_buffer_pct=0.001,
                momentum_required=True,
                risk_reward_ratio=2.5,
                notes="Minervini-style Volatility Contraction Pattern",
            ),
            PatternProfile(
                name="high_tight_flag",
                detection="htf",
                direction="long",
                lookback=45,
                range_pct_max=0.25,
                pre_run_bars=35,
                pre_run_return=1.0,
                breakout_buffer_pct=0.0008,
                momentum_required=True,
                risk_reward_ratio=3.0,
                notes="100% advance followed by tight flag",
            ),
            PatternProfile(
                name="ascending_triangle",
                detection="triangle",
                direction="long",
                lookback=60,
                r_squared_min=0.55,
                slope_tolerance=0.0003,
                breakout_buffer_pct=0.0015,
                notes="Flat top with rising demand",
            ),
            PatternProfile(
                name="sym_triangle",
                detection="triangle",
                direction="both",
                lookback=70,
                r_squared_min=0.6,
                slope_tolerance=0.00025,
                breakout_buffer_pct=0.001,
                notes="Volatility contraction via symmetrical triangle",
            ),
            PatternProfile(
                name="flat_base",
                detection="flat_base",
                direction="long",
                lookback=35,
                atr_percentile=0.25,
                range_pct_max=0.08,
                breakout_buffer_pct=0.0008,
                momentum_required=True,
                notes="3-6 week shelf / tight flag",
            ),
            PatternProfile(
                name="tight_flag",
                detection="flag",
                direction="both",
                lookback=45,
                breakout_buffer_pct=0.0012,
                notes="Parallel channel consolidation",
            ),
            PatternProfile(
                name="descending_triangle",
                detection="triangle",
                direction="short",
                lookback=60,
                r_squared_min=0.55,
                slope_tolerance=0.0003,
                breakout_buffer_pct=0.0015,
                allow_counter_trend=True,
                notes="Distributional descending triangle (short bias)",
            ),
        ]

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------
    def prepare_market_data(self, benchmark_df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        if benchmark_df is None or benchmark_df.empty:
            return None

        df = benchmark_df.copy()
        df["ema_50"] = ema(df["close"], 50)
        df["ema_200"] = ema(df["close"], 200)
        df["atr"] = atr(df["high"], df["low"], df["close"], 14)
        df["trend"] = 0
        df.loc[df["ema_50"] > df["ema_200"], "trend"] = 1
        df.loc[df["ema_50"] < df["ema_200"], "trend"] = -1
        return df

    def prepare_price_data(
        self,
        price_df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        df = price_df.copy()

        # Trend and volatility gauges
        for period in (10, 21, 50, 100, 200):
            df[f"ema_{period}"] = ema(df["close"], period)

        df["atr"] = atr(df["high"], df["low"], df["close"], 14)
        df["atr_mean_63"] = df["atr"].rolling(63).mean()
        df["atr_percentile"] = (
            (df["atr"] - df["atr"].rolling(63).min())
            / (df["atr"].rolling(63).max() - df["atr"].rolling(63).min())
        ).clip(lower=0.0, upper=1.0)
        df["bb_mid"] = df["close"].rolling(20).mean()
        df["bb_std"] = df["close"].rolling(20).std()
        df["bb_width"] = (2 * df["bb_std"]) / df["close"]

        if benchmark_df is not None and not benchmark_df.empty:
            aligned = benchmark_df["close"].reindex(df.index).ffill()
            df["rs_line"] = df["close"] / aligned
            df["rs_smooth"] = df["rs_line"].ewm(span=21).mean()
            df["rs_trend"] = df["rs_line"] - df["rs_line"].shift(5)

        if self._max_pattern_lookback > 0:
            pivot_detector = PatternDetector(
                lookback=self._max_pattern_lookback,
                min_pivot_points=2,
                pivot_window=3,
                r_squared_min=0.5,
                slope_tolerance=0.0002,
            )
            df = pivot_detector.find_pivot_points(df, left=3, right=3)
        else:
            df["pivot_high"] = False
            df["pivot_low"] = False

        return df

    # ------------------------------------------------------------------
    # Universe / regime filters
    # ------------------------------------------------------------------
    def passes_universe_filters(
        self,
        df: pd.DataFrame,
        idx,
        benchmark_df: Optional[pd.DataFrame]
    ) -> bool:
        if idx not in df.index:
            return False

        row = df.loc[idx]
        if np.isnan(row.get("close", np.nan)):
            return False

        if row["close"] < self.min_price:
            return False

        if self.min_avg_volume > 0 and "volume" in df.columns:
            pos = df.index.get_loc(idx)
            if isinstance(pos, slice):
                pos = pos.start
            if pos is None or pos < self.universe_lookback:
                return False
            avg_volume = (
                df["volume"].iloc[pos - self.universe_lookback + 1: pos + 1].mean()
            )
            if np.isnan(avg_volume) or avg_volume < self.min_avg_volume:
                return False

        if benchmark_df is not None and not benchmark_df.empty:
            market_bias = self._market_bias(benchmark_df, idx)
            if market_bias == "long" and row["close"] < row.get("ema_50", row["close"]):
                return False
            if market_bias == "short" and row["close"] > row.get("ema_50", row["close"]):
                return False

        if self.require_rs_new_high and "rs_line" in df.columns:
            pos = df.index.get_loc(idx)
            if isinstance(pos, slice):
                pos = pos.start
            window = df["rs_line"].iloc[max(0, pos - self.rs_window + 1): pos + 1]
            if len(window) < self.rs_window:
                return False
            if row["rs_line"] < window.max():
                return False

        return True

    def _market_bias(self, benchmark_df: Optional[pd.DataFrame], idx) -> str:
        if benchmark_df is None or benchmark_df.empty or self.market_bias_mode == "off":
            return "both"

        if idx in benchmark_df.index:
            row = benchmark_df.loc[idx]
        else:
            earlier = benchmark_df.loc[benchmark_df.index <= idx]
            if earlier.empty:
                return "both"
            row = earlier.iloc[-1]

        if self.market_bias_mode == "long_only":
            return "long"
        if self.market_bias_mode == "short_only":
            return "short"

        ema_50 = row.get("ema_50")
        ema_200 = row.get("ema_200")
        if ema_50 is not None and ema_200 is not None:
            if ema_50 > ema_200:
                return "long"
            if ema_50 < ema_200:
                return "short"

        return "both"

    # ------------------------------------------------------------------
    # Pattern detection helpers
    # ------------------------------------------------------------------
    def _get_position(self, df: pd.DataFrame, idx) -> Optional[int]:
        try:
            pos = df.index.get_loc(idx)
        except KeyError:
            return None

        if isinstance(pos, slice):
            return pos.start
        if isinstance(pos, (list, np.ndarray)):
            return pos[0]
        return int(pos)

    def _get_detector(self, profile: PatternProfile) -> PatternDetector:
        key = (
            profile.lookback,
            profile.min_pivots,
            profile.pivot_window,
            profile.r_squared_min,
            profile.slope_tolerance,
        )
        if key not in self._detector_cache:
            self._detector_cache[key] = PatternDetector(
                lookback=profile.lookback,
                min_pivot_points=profile.min_pivots,
                pivot_window=profile.pivot_window,
                r_squared_min=profile.r_squared_min,
                slope_tolerance=profile.slope_tolerance,
            )
        return self._detector_cache[key]

    def _direction_hint_from_pattern(
        self, pattern: Dict[str, Any], profile: PatternProfile
    ) -> str:
        ptype = pattern.get("type", profile.detection)
        if ptype in ("ascending", "ascending_triangle"):
            return "long"
        if ptype in ("descending", "descending_triangle"):
            return "short"
        if ptype in ("flag", "pennant"):
            return profile.direction
        if ptype == "symmetrical":
            return "both"
        return profile.direction

    def _detect_with_profile(
        self,
        df: pd.DataFrame,
        idx,
        profile: PatternProfile,
    ) -> Optional[Dict[str, Any]]:
        pos = self._get_position(df, idx)
        if pos is None or pos < profile.lookback:
            return None

        time_ok = profile.time_window[0] <= idx.hour <= profile.time_window[1]
        if not time_ok:
            return None

        if profile.detection in {"triangle", "flag", "pennant"}:
            detector = self._get_detector(profile)
            pattern_df = df  # Already contains pivot columns
            detect_fn = getattr(detector, f"detect_{profile.detection}")
            pattern = detect_fn(pattern_df, pos)
            if not pattern:
                return None

            quality = (
                pattern["resistance"].get("r2", 0) + pattern["support"].get("r2", 0)
            ) / 2
            return {
                "profile": profile,
                "pattern": pattern,
                "source": "pattern_detector",
                "detector_key": (
                    profile.lookback,
                    profile.min_pivots,
                    profile.pivot_window,
                    profile.r_squared_min,
                    profile.slope_tolerance,
                ),
                "support_price": pattern["support"]["price"],
                "resistance_price": pattern["resistance"]["price"],
                "quality": quality,
                "direction_hint": self._direction_hint_from_pattern(pattern, profile),
            }

        if profile.detection == "flat_base":
            return self._detect_flat_base(df, idx, profile, pos)

        if profile.detection == "vcp":
            return self._detect_vcp(df, idx, profile, pos)

        if profile.detection == "htf":
            return self._detect_high_tight_flag(df, idx, profile, pos)

        return None

    def _detect_flat_base(
        self,
        df: pd.DataFrame,
        idx,
        profile: PatternProfile,
        pos: int,
    ) -> Optional[Dict[str, Any]]:
        start = max(0, pos - profile.lookback)
        window = df.iloc[start : pos + 1]
        if len(window) < 5:
            return None

        high = window["high"].max()
        low = window["low"].min()
        range_pct = (high - low) / max(high, 1e-6)
        if range_pct > profile.range_pct_max:
            return None

        atr_series = window["atr"].dropna()
        if len(atr_series) > 10:
            latest_atr = atr_series.iloc[-1]
            atr_threshold = atr_series.quantile(profile.atr_percentile)
            if latest_atr > atr_threshold:
                return None
        else:
            latest_atr = window["atr"].iloc[-1]

        quality = 1.0 - range_pct
        return {
            "profile": profile,
            "pattern": {
                "type": "flat_base",
                "start_index": start,
                "end_index": pos,
                "resistance": {"price": high, "r2": 1.0, "slope": 0.0},
                "support": {"price": low, "r2": 1.0, "slope": 0.0},
                "atr": latest_atr,
                "range_pct": range_pct,
            },
            "source": "heuristic",
            "support_price": low,
            "resistance_price": high,
            "quality": quality,
            "direction_hint": profile.direction,
        }

    def _detect_vcp(
        self,
        df: pd.DataFrame,
        idx,
        profile: PatternProfile,
        pos: int,
    ) -> Optional[Dict[str, Any]]:
        start = max(0, pos - profile.lookback)
        window = df.iloc[start : pos + 1]
        if len(window) < profile.contraction_steps * 4:
            return None

        swing_points: List[Tuple[str, int, float]] = []
        for offset, (time_idx, row) in enumerate(window.iterrows()):
            absolute_index = start + offset
            if row.get("pivot_high", False):
                swing_points.append(("high", absolute_index, row["high"]))
            if row.get("pivot_low", False):
                swing_points.append(("low", absolute_index, row["low"]))

        contractions: List[Dict[str, Any]] = []
        last_high: Optional[Tuple[int, float]] = None
        for kind, abs_idx, price in swing_points:
            if kind == "high":
                last_high = (abs_idx, price)
            elif kind == "low" and last_high:
                depth = (last_high[1] - price) / max(last_high[1], 1e-6)
                if depth <= 0:
                    continue
                contractions.append(
                    {
                        "high_index": last_high[0],
                        "low_index": abs_idx,
                        "depth": depth,
                        "high_price": last_high[1],
                        "low_price": price,
                    }
                )
                last_high = None

        if len(contractions) < profile.contraction_steps:
            return None

        recent = contractions[-profile.contraction_steps :]
        contraction_ok = all(
            recent[i]["depth"] > recent[i + 1]["depth"] * 0.9
            for i in range(len(recent) - 1)
        )
        if not contraction_ok:
            return None

        resistance_price = max(c["high_price"] for c in recent)
        support_price = max(c["low_price"] for c in recent)

        # Volatility contraction check
        atr_series = window["atr"].dropna()
        atr_ok = True
        if len(atr_series) > 10:
            latest_atr = atr_series.iloc[-1]
            atr_quantile = atr_series.quantile(profile.atr_percentile)
            if latest_atr > atr_quantile:
                atr_ok = False
        else:
            latest_atr = window["atr"].iloc[-1]

        range_pct = (window["high"].max() - window["low"].min()) / max(window["high"].max(), 1e-6)
        if range_pct > profile.range_pct_max or not atr_ok:
            return None

        quality = max(recent[0]["depth"] - recent[-1]["depth"], 0)
        return {
            "profile": profile,
            "pattern": {
                "type": "vcp",
                "start_index": start,
                "end_index": pos,
                "contractions": recent,
                "resistance": {"price": resistance_price, "r2": 1.0, "slope": 0.0},
                "support": {"price": support_price, "r2": 1.0, "slope": 0.0},
                "range_pct": range_pct,
                "atr": latest_atr,
            },
            "source": "heuristic",
            "support_price": support_price,
            "resistance_price": resistance_price,
            "quality": quality,
            "direction_hint": "long",
        }

    def _detect_high_tight_flag(
        self,
        df: pd.DataFrame,
        idx,
        profile: PatternProfile,
        pos: int,
    ) -> Optional[Dict[str, Any]]:
        start = max(0, pos - profile.lookback)
        window = df.iloc[start : pos + 1]
        if len(window) < 10:
            return None

        pre_run_start = max(0, start - profile.pre_run_bars)
        pre_window = df.iloc[pre_run_start:start]
        if pre_window.empty:
            return None

        pre_return = (
            pre_window["close"].iloc[-1] - pre_window["close"].iloc[0]
        ) / max(pre_window["close"].iloc[0], 1e-6)
        if pre_return < profile.pre_run_return:
            return None

        high = window["high"].max()
        low = window["low"].min()
        range_pct = (high - low) / max(high, 1e-6)
        if not (0.05 <= range_pct <= profile.range_pct_max):
            return None

        atr_series = window["atr"].dropna()
        if len(atr_series) > 5 and atr_series.iloc[-1] > atr_series.quantile(profile.atr_percentile):
            return None

        quality = pre_return - range_pct
        return {
            "profile": profile,
            "pattern": {
                "type": "high_tight_flag",
                "start_index": start,
                "end_index": pos,
                "resistance": {"price": high, "r2": 1.0, "slope": 0.0},
                "support": {"price": low, "r2": 1.0, "slope": 0.0},
                "range_pct": range_pct,
                "pre_run_return": pre_return,
            },
            "source": "heuristic",
            "support_price": low,
            "resistance_price": high,
            "quality": quality,
            "direction_hint": "long",
        }

    # ------------------------------------------------------------------
    # Breakout evaluation
    # ------------------------------------------------------------------
    def check_pattern_breakout_signal(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame],
        idx,
    ) -> Optional[BreakoutSignal]:
        if not self.pattern_profiles:
            return None

        if not self.passes_universe_filters(df, idx, benchmark_df):
            return None

        pos = self._get_position(df, idx)
        if pos is None:
            return None

        row = df.loc[idx]
        market_bias = self._market_bias(benchmark_df, idx)
        signals: List[BreakoutSignal] = []

        for profile in self.pattern_profiles:
            candidate = self._detect_with_profile(df, idx, profile)
            if not candidate:
                continue

            pattern = candidate["pattern"]
            pattern_id = (profile.name, pattern.get("start_index", 0), pattern.get("end_index", pos))
            if pattern_id in self.traded_patterns:
                continue

            breakout = self._evaluate_candidate_breakout(
                df=df,
                idx=idx,
                row=row,
                candidate=candidate,
                market_bias=market_bias,
                benchmark_df=benchmark_df,
            )
            if breakout:
                breakout.pattern_id = pattern_id
                signals.append(breakout)

        if not signals:
            return None

        signals.sort(key=lambda s: s.quality, reverse=True)
        best = signals[0]
        self.traded_patterns.add(best.pattern_id)
        return best

    def _evaluate_candidate_breakout(
        self,
        df: pd.DataFrame,
        idx,
        row: pd.Series,
        candidate: Dict[str, Any],
        market_bias: str,
        benchmark_df: Optional[pd.DataFrame],
    ) -> Optional[BreakoutSignal]:
        profile: PatternProfile = candidate["profile"]
        current_price = row["close"]
        resistance_price = candidate["resistance_price"]
        support_price = candidate["support_price"]
        direction_hint = candidate["direction_hint"]

        # Breakout direction selection respecting market bias
        allowed_directions = {profile.direction}
        if profile.direction == "both":
            allowed_directions = {"long", "short"}

        if direction_hint != "both":
            allowed_directions &= {direction_hint}
        if market_bias != "both" and not profile.allow_counter_trend:
            allowed_directions &= {market_bias}

        if not allowed_directions:
            return None

        volume_ok = True
        if profile.volume_multiplier > 0 and "volume" in df.columns:
            volume = row.get("volume")
            pos = self._get_position(df, idx)
            if volume is None or np.isnan(volume) or pos is None or pos < 20:
                volume_ok = False
            else:
                avg_volume = df["volume"].iloc[pos - 20 + 1 : pos + 1].mean()
                volume_ok = volume >= avg_volume * profile.volume_multiplier if avg_volume > 0 else True
        if not volume_ok:
            return None

        if profile.momentum_required:
            if row.get("close", 0) < max(row.get("ema_10", 0), row.get("ema_21", 0)):
                return None

        if "rs_line" in df.columns and benchmark_df is not None:
            rs_trend = row.get("rs_trend", 0)
            if rs_trend is not None and rs_trend < 0:
                return None

        buffer = profile.breakout_buffer_pct
        long_breakout = (
            "long" in allowed_directions
            and current_price >= resistance_price * (1 + buffer)
        )
        short_breakout = (
            "short" in allowed_directions
            and current_price <= support_price * (1 - buffer)
        )

        direction = None
        if long_breakout:
            direction = "long"
        elif short_breakout:
            direction = "short"
        else:
            return None

        if direction == "long":
            entry_price = resistance_price * (1 + buffer)
            stop_price = support_price * (1 - buffer * 0.5)
        else:
            entry_price = support_price * (1 - buffer)
            stop_price = resistance_price * (1 + buffer * 0.5)

        if direction == "long" and stop_price >= entry_price:
            stop_price = entry_price - max(buffer * entry_price, self.price_tick)
        if direction == "short" and stop_price <= entry_price:
            stop_price = entry_price + max(buffer * entry_price, self.price_tick)

        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return None

        atr_value = row.get("atr", np.nan)
        target_from_rr = entry_price + profile.risk_reward_ratio * risk_per_unit if direction == "long" else entry_price - profile.risk_reward_ratio * risk_per_unit
        if not np.isnan(atr_value) and atr_value > 0:
            atr_target = entry_price + profile.atr_multiple * atr_value if direction == "long" else entry_price - profile.atr_multiple * atr_value
        else:
            atr_target = target_from_rr

        target_price = max(target_from_rr, atr_target) if direction == "long" else min(target_from_rr, atr_target)

        signal = BreakoutSignal(
            direction=direction,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            profile=profile,
            pattern_id=(profile.name, 0, 0),  # placeholder, overwritten by caller
            quality=float(candidate.get("quality", 0.0)),
            metadata={
                "pattern": candidate["pattern"],
                "source": candidate.get("source", ""),
            },
        )
        return signal

    # ------------------------------------------------------------------
    # Position sizing and management
    # ------------------------------------------------------------------
    def calculate_position_size(self, entry_price: float, stop_price: float) -> Tuple[int, float]:
        risk_amount = self.current_capital * (self.risk_percent / 100.0)
        stop_distance = abs(entry_price - stop_price)
        if stop_distance <= 0:
            return 0, 0.0

        units_by_risk = int(risk_amount / stop_distance)
        if units_by_risk <= 0:
            return 0, 0.0

        max_notional = self.current_capital * self.max_notional_multiplier
        if max_notional <= 0:
            return 0, 0.0

        units_by_notional = int(max_notional / max(entry_price, self.price_tick))
        units = max(min(units_by_risk, units_by_notional), 0)
        return units, stop_distance

    def update_trailing_stop(self, position: Dict[str, Any], current_price: float) -> float:
        if not self.use_trailing_stop:
            return position["sl"]

        entry = position["entry_price"]
        sl = position["sl"]
        original_sl = position.get("original_sl", sl)
        risk = abs(entry - original_sl)
        if risk <= 0:
            return sl

        direction = position["type"]
        profit = current_price - entry if direction == "long" else entry - current_price
        r_multiple = profit / risk

        new_sl = sl
        if direction == "long":
            if r_multiple >= 2.5:
                new_sl = max(sl, current_price - 0.5 * risk)
            elif r_multiple >= 2.0:
                new_sl = max(sl, entry + 1.5 * risk)
            elif r_multiple >= 1.5:
                new_sl = max(sl, entry + 0.75 * risk)
            elif r_multiple >= 1.0:
                new_sl = max(sl, entry + 0.1 * risk)
        else:
            if r_multiple >= 2.5:
                new_sl = min(sl, current_price + 0.5 * risk)
            elif r_multiple >= 2.0:
                new_sl = min(sl, entry - 1.5 * risk)
            elif r_multiple >= 1.5:
                new_sl = min(sl, entry - 0.75 * risk)
            elif r_multiple >= 1.0:
                new_sl = min(sl, entry - 0.1 * risk)

        return new_sl

    def check_exit_signal(self, df: pd.DataFrame, idx) -> Optional[Tuple[str, float]]:
        if self.position is None or idx not in df.index:
            return None

        row = df.loc[idx]
        position = self.position
        direction = position["type"]
        high = row["high"]
        low = row["low"]
        close = row["close"]

        position["sl"] = self.update_trailing_stop(position, close)
        sl = position["sl"]
        tp = position["tp"]

        if direction == "long":
            if low <= sl:
                return "sl", sl
            if high >= tp:
                return "tp", tp
        else:
            if high >= sl:
                return "sl", sl
            if low <= tp:
                return "tp", tp

        return None

    # ------------------------------------------------------------------
    # Entry orchestration
    # ------------------------------------------------------------------
    def check_entry_signal(
        self,
        df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame],
        idx,
    ) -> Optional[BreakoutSignal]:
        return self.check_pattern_breakout_signal(df, benchmark_df, idx)

    # ------------------------------------------------------------------
    # Backtesting
    # ------------------------------------------------------------------
    def backtest(
        self,
        price_df: pd.DataFrame,
        benchmark_df: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        market_df = self.prepare_market_data(benchmark_df)
        df = self.prepare_price_data(price_df, market_df)

        trades: List[Dict[str, Any]] = []
        self.position = None
        self.traded_patterns = set()
        self.current_capital = self.initial_capital

        for idx in df.index:
            # Manage open trade first
            if self.position is not None:
                exit_signal = self.check_exit_signal(df, idx)
                if exit_signal:
                    reason, exit_price = exit_signal
                    entry_price = self.position["entry_price"]
                    units = self.position["units"]
                    direction = self.position["type"]

                    if direction == "long":
                        pnl = (exit_price - entry_price) * units
                    else:
                        pnl = (entry_price - exit_price) * units

                    commission = units * self.commission_per_unit
                    slippage = units * self.slippage_per_unit
                    pnl -= (commission + slippage)

                    self.current_capital += pnl

                    trades.append(
                        {
                            "entry_time": self.position["entry_time"],
                            "exit_time": idx,
                            "type": direction,
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "sl": self.position["sl"],
                            "tp": self.position["tp"],
                            "units": units,
                            "pnl": pnl,
                            "capital_after": self.current_capital,
                            "exit_reason": reason,
                            "signal_type": self.position.get("signal_type"),
                        }
                    )

                    self.position = None
                    continue

            if self.position is None:
                signal = self.check_entry_signal(df, market_df, idx)
                if not signal:
                    continue

                units, stop_distance = self.calculate_position_size(signal.entry_price, signal.stop_price)
                if units <= 0:
                    continue

                cost = signal.entry_price * units
                max_notional = self.current_capital * self.max_notional_multiplier
                if cost > max_notional:
                    continue

                self.position = {
                    "type": signal.direction,
                    "entry_price": signal.entry_price,
                    "sl": signal.stop_price,
                    "tp": signal.target_price,
                    "entry_time": idx,
                    "units": units,
                    "original_sl": signal.stop_price,
                    "stop_distance": stop_distance,
                    "signal_type": f"pattern_{signal.profile.name}",
                }

        return trades


class EdgerunnerMomentumBreakout(EdgerunnerBreakoutStrategy):
    """Long-biased momentum breakout variant (VCP, HTF, triangles, shelves)."""

    def __init__(self, **kwargs) -> None:
        profiles = [
            PatternProfile(
                name="vcp",
                detection="vcp",
                direction="long",
                lookback=80,
                contraction_steps=3,
                atr_percentile=0.2,
                range_pct_max=0.12,
                breakout_buffer_pct=0.001,
                momentum_required=True,
                risk_reward_ratio=2.5,
            ),
            PatternProfile(
                name="high_tight_flag",
                detection="htf",
                direction="long",
                lookback=45,
                range_pct_max=0.25,
                pre_run_return=1.0,
                breakout_buffer_pct=0.0008,
                momentum_required=True,
                risk_reward_ratio=3.0,
            ),
            PatternProfile(
                name="ascending_triangle",
                detection="triangle",
                direction="long",
                lookback=60,
                r_squared_min=0.55,
                slope_tolerance=0.0003,
                breakout_buffer_pct=0.0015,
            ),
            PatternProfile(
                name="flat_base",
                detection="flat_base",
                direction="long",
                lookback=35,
                atr_percentile=0.25,
                range_pct_max=0.08,
                breakout_buffer_pct=0.0008,
                momentum_required=True,
            ),
            PatternProfile(
                name="tight_flag",
                detection="flag",
                direction="long",
                lookback=40,
                breakout_buffer_pct=0.0012,
            ),
        ]
        kwargs.setdefault("profiles", profiles)
        kwargs.setdefault("min_price", 10.0)
        kwargs.setdefault("min_avg_volume", 500_000)
        kwargs.setdefault("require_rs_new_high", True)
        kwargs.setdefault("market_bias_mode", "auto")
        super().__init__(**kwargs)


class EdgerunnerBreakdownMomentum(EdgerunnerBreakoutStrategy):
    """Short-biased continuation / breakdown flavour."""

    def __init__(self, **kwargs) -> None:
        profiles = [
            PatternProfile(
                name="descending_triangle",
                detection="triangle",
                direction="short",
                lookback=60,
                r_squared_min=0.55,
                slope_tolerance=0.0003,
                breakout_buffer_pct=0.0015,
                allow_counter_trend=True,
            ),
            PatternProfile(
                name="bear_flag",
                detection="flag",
                direction="short",
                lookback=45,
                breakout_buffer_pct=0.0015,
                allow_counter_trend=True,
            ),
            PatternProfile(
                name="bear_flat_base",
                detection="flat_base",
                direction="short",
                lookback=35,
                atr_percentile=0.25,
                range_pct_max=0.1,
                breakout_buffer_pct=0.001,
                allow_counter_trend=True,
            ),
        ]
        kwargs.setdefault("profiles", profiles)
        kwargs.setdefault("min_price", 10.0)
        kwargs.setdefault("min_avg_volume", 500_000)
        kwargs.setdefault("market_bias_mode", "auto")
        super().__init__(**kwargs)


class LondonBreakoutV4Triangles(EdgerunnerMomentumBreakout):
    """
    Backward-compatible alias for existing scripts referencing the original
    triangle strategy. Defaults to the momentum breakout profile stack
    (VCP + triangles + flat bases) while retaining identical constructor
    signature.
    """

    def __init__(
        self,
        pair: str = "EURUSD",
        risk_percent: float = 0.5,
        initial_capital: float = 100_000.0,
        enable_asia_breakout: bool = False,
        enable_triangle_breakout: bool = True,
    ) -> None:
        super().__init__(
            symbol=pair,
            risk_percent=risk_percent,
            initial_capital=initial_capital,
            market_bias_mode="auto",
            price_tick=0.0001,
            min_price=1.0,
            min_avg_volume=0.0,
            require_rs_new_high=False,
            max_notional_multiplier=20.0,
        )
        self.enable_triangle_breakout = enable_triangle_breakout
        self.enable_asia_breakout = enable_asia_breakout

    def check_entry_signal(self, df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame], idx):
        if not self.enable_triangle_breakout:
            return None
        return super().check_entry_signal(df, benchmark_df, idx)


__all__ = [
    "PatternProfile",
    "BreakoutSignal",
    "EdgerunnerBreakoutStrategy",
    "EdgerunnerMomentumBreakout",
    "EdgerunnerBreakdownMomentum",
    "LondonBreakoutV4Triangles",
]
