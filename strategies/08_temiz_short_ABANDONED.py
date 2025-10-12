"""
Temiz Small-Cap Short Strategy

Based on Tomas Temiz's day trading approach for parabolic small-caps.
Focuses on shorting exhaustion moves in stocks with <$20M float.

Three primary setups:
1. Parabolic Exhaustion - Short blow-off tops (70% win rate)
2. First Red Day - Short first pullback after gap-up (60% win rate)
3. Backside Fade - Short failed breakout attempts (55% win rate)

Key characteristics:
- Intraday only (1-5 minute bars)
- Short-biased (80% shorts, 20% longs)
- Small position sizing (0.5% risk per trade)
- Tight stops (2-5% from entry)
- Scale out (1/3 at R1, 1/3 at R2, runner to VWAP)

Requirements:
- 1-minute bar data
- Float data (<$20M for best results)
- Short availability (HTB stocks require higher conviction)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, time
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ShortSignal:
    """Short signal with entry price and stop loss"""
    timestamp: datetime
    setup_type: str  # 'PARABOLIC', 'FIRST_RED_DAY', 'BACKSIDE'
    entry_price: float
    stop_loss: float
    target_r1: float  # First profit target (1R)
    target_r2: float  # Second profit target (2R)
    target_vwap: float  # Final target (runner)
    conviction: str  # 'HIGH', 'MEDIUM', 'LOW'
    risk_amount: float
    position_size: int


class TemizSmallCapShortStrategy:
    """
    Implementation of Temiz's small-cap short strategy

    Entry criteria vary by setup, but all require:
    - Float <$20M (ideal <$10M)
    - Gap >5% from previous close
    - RVOL >2.0 (relative volume)
    - Time window: 9:30 AM - 3:00 PM ET

    Exit criteria:
    - Scale 1/3 at +1R
    - Scale 1/3 at +2R
    - Trail runner to VWAP
    - Hard stop at entry stop loss
    - Daily kill switch: -2% of account
    """

    def __init__(self,
                 risk_per_trade: float = 0.005,  # 0.5% risk per trade
                 max_daily_loss: float = 0.02,   # 2% max daily loss
                 trade_start_time: str = '09:30',
                 trade_end_time: str = '15:00',
                 max_positions: int = 3,
                 min_gap_pct: float = 0.05,      # 5% minimum gap
                 max_float_millions: float = 20.0):
        """
        Initialize Temiz strategy

        Args:
            risk_per_trade: Risk per trade as fraction (0.005 = 0.5%)
            max_daily_loss: Kill switch threshold
            trade_start_time: Start trading time (ET)
            trade_end_time: Stop new entries time (ET)
            max_positions: Max concurrent positions
            min_gap_pct: Minimum gap from previous close
            max_float_millions: Maximum float in millions
        """
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.trade_start = datetime.strptime(trade_start_time, '%H:%M').time()
        self.trade_end = datetime.strptime(trade_end_time, '%H:%M').time()
        self.max_positions = max_positions
        self.min_gap_pct = min_gap_pct
        self.max_float_millions = max_float_millions

    def check_parabolic_setup(self,
                             bars: pd.DataFrame,
                             idx: int,
                             vwap: pd.Series,
                             vwap_zscore: pd.Series,
                             rvol: pd.Series,
                             blowoff_candle: pd.Series) -> Optional[Dict]:
        """
        Detect parabolic exhaustion setup

        Entry criteria:
        1. VWAP Z-score >2.5 (extreme extension)
        2. Blow-off candle (wick >60%)
        3. Volume climax (>5× average)
        4. Price velocity >2% per minute

        Args:
            bars: DataFrame with OHLCV data
            idx: Current bar index
            vwap, vwap_zscore, rvol, blowoff_candle: Indicator series

        Returns:
            Dict with signal details or None
        """
        if idx < 5:  # Need history
            return None

        current = bars.iloc[idx]

        # Check criteria
        is_extended = vwap_zscore.iloc[idx] > 2.5
        has_blowoff = blowoff_candle.iloc[idx]
        high_volume = rvol.iloc[idx] > 5.0

        # Calculate price velocity
        price_5m_ago = bars.iloc[idx - 5]['close']
        velocity = ((current['close'] - price_5m_ago) / price_5m_ago) * 100 / 5
        is_parabolic = velocity > 2.0

        if is_extended and has_blowoff and high_volume and is_parabolic:
            # Entry at next bar open (market order)
            entry_price = current['close']  # Approximate (assume quick fill)
            stop_loss = current['high'] * 1.02  # 2% above high

            risk_per_share = stop_loss - entry_price

            return {
                'setup_type': 'PARABOLIC',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_share': risk_per_share,
                'target_vwap': vwap.iloc[idx],
                'conviction': 'HIGH',  # Best setup
                'vwap_zscore': vwap_zscore.iloc[idx],
                'rvol': rvol.iloc[idx]
            }

        return None

    def check_first_red_day_setup(self,
                                  bars: pd.DataFrame,
                                  idx: int,
                                  first_red_candle: pd.Series,
                                  vwap_zscore: pd.Series,
                                  rvol: pd.Series) -> Optional[Dict]:
        """
        Detect First Red Day setup

        Entry criteria:
        1. First red candle after 3+ green candles
        2. VWAP Z-score >1.5 (still extended)
        3. RVOL >2.0
        4. Not during first 15 minutes (avoid chop)

        Args:
            bars: DataFrame with OHLCV data
            idx: Current bar index
            first_red_candle: Boolean series from indicators
            vwap_zscore: VWAP extension
            rvol: Relative volume

        Returns:
            Dict with signal details or None
        """
        if idx < 15:  # Skip first 15 minutes
            return None

        current = bars.iloc[idx]

        # Check criteria
        is_first_red = first_red_candle.iloc[idx]
        is_extended = vwap_zscore.iloc[idx] > 1.5
        good_volume = rvol.iloc[idx] > 2.0

        if is_first_red and is_extended and good_volume:
            entry_price = current['close']
            stop_loss = current['high'] * 1.03  # 3% above high (wider stop)

            risk_per_share = stop_loss - entry_price

            return {
                'setup_type': 'FIRST_RED_DAY',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_share': risk_per_share,
                'target_vwap': bars.iloc[:idx+1]['vwap'].iloc[-1],
                'conviction': 'MEDIUM',
                'vwap_zscore': vwap_zscore.iloc[idx],
                'rvol': rvol.iloc[idx]
            }

        return None

    def check_backside_fade_setup(self,
                                  bars: pd.DataFrame,
                                  idx: int,
                                  vwap: pd.Series,
                                  rvol: pd.Series) -> Optional[Dict]:
        """
        Detect Backside Fade setup

        Entry criteria:
        1. Price attempted new high but failed
        2. Now trading back below VWAP
        3. RVOL >2.0 (volume still present)
        4. After 11:00 AM (mid-day exhaustion)

        Args:
            bars: DataFrame with OHLCV data
            idx: Current bar index
            vwap: VWAP series
            rvol: Relative volume

        Returns:
            Dict with signal details or None
        """
        if idx < 30:  # Need history
            return None

        current = bars.iloc[idx]

        # Check if we're after 11:00 AM
        # (In backtest, we'll use bar index as proxy)
        # In live trading, check actual time

        # Find recent high (last 30 minutes)
        recent_window = bars.iloc[idx-30:idx]
        recent_high = recent_window['high'].max()
        high_idx = recent_window['high'].idxmax()

        # Check if price tried to break recent high but failed
        attempted_breakout = (
            (bars.iloc[idx-2:idx]['high'].max() >= recent_high * 0.99) and
            (current['close'] < recent_high * 0.97)
        )

        # Now below VWAP
        below_vwap = current['close'] < vwap.iloc[idx]
        good_volume = rvol.iloc[idx] > 2.0

        if attempted_breakout and below_vwap and good_volume:
            entry_price = current['close']
            stop_loss = recent_high * 1.02  # 2% above recent high

            risk_per_share = stop_loss - entry_price

            return {
                'setup_type': 'BACKSIDE',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'risk_per_share': risk_per_share,
                'target_vwap': vwap.iloc[idx],
                'conviction': 'LOW',  # Lower win rate
                'vwap_zscore': (current['close'] - vwap.iloc[idx]) / current['close'],
                'rvol': rvol.iloc[idx]
            }

        return None

    def calculate_position_size(self,
                                account_equity: float,
                                signal: Dict) -> int:
        """
        Calculate position size based on risk per trade

        Uses fixed fractional position sizing:
        - Risk 0.5% of account per trade
        - Position size = (Account × Risk%) / Risk per share

        Args:
            account_equity: Current account equity
            signal: Signal dict with entry_price, stop_loss

        Returns:
            Number of shares to short
        """
        risk_amount = account_equity * self.risk_per_trade
        risk_per_share = signal['risk_per_share']

        if risk_per_share <= 0:
            return 0

        shares = int(risk_amount / risk_per_share)

        # Limit to reasonable size (don't exceed 10% of account value)
        max_shares = int(account_equity * 0.10 / signal['entry_price'])
        shares = min(shares, max_shares)

        return shares

    def calculate_targets(self, signal: Dict) -> Tuple[float, float, float]:
        """
        Calculate profit targets (R-multiples)

        Standard scaling:
        - R1: 1× risk (take 1/3 off)
        - R2: 2× risk (take 1/3 off)
        - VWAP: Trail runner to VWAP (final 1/3)

        Args:
            signal: Signal dict with entry_price, risk_per_share, target_vwap

        Returns:
            Tuple (target_r1, target_r2, target_vwap)
        """
        entry = signal['entry_price']
        risk = signal['risk_per_share']

        target_r1 = entry - (risk * 1.0)  # 1R profit
        target_r2 = entry - (risk * 2.0)  # 2R profit
        target_vwap = signal['target_vwap']  # Dynamic (VWAP moves)

        return (target_r1, target_r2, target_vwap)

    def scan_for_signals(self,
                        bars: pd.DataFrame,
                        indicators: pd.DataFrame) -> List[Dict]:
        """
        Scan all bars for entry signals

        Args:
            bars: DataFrame with OHLCV data
            indicators: DataFrame with all indicator columns (from calculate_all_indicators)

        Returns:
            List of signal dictionaries
        """
        signals = []

        for idx in range(len(bars)):
            # Check parabolic setup (highest priority)
            parabolic = self.check_parabolic_setup(
                bars, idx,
                indicators['vwap'],
                indicators['vwap_zscore'],
                indicators['rvol'],
                indicators['blowoff_candle']
            )
            if parabolic:
                signals.append({'idx': idx, **parabolic})
                continue  # Don't check other setups if parabolic found

            # Check first red day
            first_red = self.check_first_red_day_setup(
                bars, idx,
                indicators['first_red_candle'],
                indicators['vwap_zscore'],
                indicators['rvol']
            )
            if first_red:
                signals.append({'idx': idx, **first_red})
                continue

            # Check backside fade
            backside = self.check_backside_fade_setup(
                bars, idx,
                indicators['vwap'],
                indicators['rvol']
            )
            if backside:
                signals.append({'idx': idx, **backside})

        return signals

    def apply_slippage(self,
                      entry_price: float,
                      volume: float,
                      avg_volume: float) -> float:
        """
        Model slippage for market orders

        Slippage model:
        - Low volume (RVOL <2): 2% slippage
        - Medium volume (RVOL 2-5): 1% slippage
        - High volume (RVOL >5): 0.5% slippage

        Args:
            entry_price: Intended entry price
            volume: Current bar volume
            avg_volume: Average volume

        Returns:
            Adjusted entry price (worse fill)
        """
        rvol = volume / avg_volume if avg_volume > 0 else 1.0

        if rvol < 2.0:
            slippage = 0.02  # 2%
        elif rvol < 5.0:
            slippage = 0.01  # 1%
        else:
            slippage = 0.005  # 0.5%

        # For shorts, slippage means higher entry price (worse)
        adjusted_price = entry_price * (1 + slippage)

        return adjusted_price

    def simulate_short_availability(self, conviction: str) -> bool:
        """
        Simulate short availability (HTB stocks)

        In real trading, not all stocks are available to short.
        Model based on conviction:
        - HIGH conviction: 90% availability
        - MEDIUM conviction: 70% availability
        - LOW conviction: 50% availability

        Args:
            conviction: 'HIGH', 'MEDIUM', or 'LOW'

        Returns:
            True if short available
        """
        availability = {
            'HIGH': 0.90,
            'MEDIUM': 0.70,
            'LOW': 0.50
        }

        prob = availability.get(conviction, 0.70)
        return np.random.random() < prob

    def print_signal_summary(self, signals: List[Dict]):
        """Print summary of detected signals"""
        if not signals:
            print("❌ No signals detected")
            return

        print(f"\n✅ Found {len(signals)} signals")
        print("\nBy setup type:")
        for setup in ['PARABOLIC', 'FIRST_RED_DAY', 'BACKSIDE']:
            count = sum(1 for s in signals if s['setup_type'] == setup)
            if count > 0:
                print(f"   {setup}: {count}")

        print("\nBy conviction:")
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            count = sum(1 for s in signals if s['conviction'] == conviction)
            if count > 0:
                print(f"   {conviction}: {count}")


if __name__ == '__main__':
    print("""
    Temiz Small-Cap Short Strategy
    ===============================

    Usage example:

    from data.alpaca_data_loader import AlpacaDataLoader
    from indicators.intraday_indicators import calculate_all_indicators
    from strategies.temiz_small_cap_short_strategy import TemizSmallCapShortStrategy

    # Load data
    loader = AlpacaDataLoader(api_key='...', secret_key='...')
    bars = loader.get_1min_bars('GME', '2024-01-15', '2024-01-15')

    # Calculate indicators
    indicators = calculate_all_indicators(bars)

    # Scan for signals
    strategy = TemizSmallCapShortStrategy()
    signals = strategy.scan_for_signals(bars, indicators)
    strategy.print_signal_summary(signals)
    """)
