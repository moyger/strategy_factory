"""
Strategy: London Breakout v4.1 - OPTIMIZED TRIANGLE PARAMETERS

Changes from v4.0:
1. Relaxed triangle parameters for more trades
   - R² min: 0.6 → 0.5
   - Slope tolerance: 0.0002 → 0.0003
   - Lookback: 40 → 60 bars
2. Removed first-hour momentum filter for triangle trades
3. Extended time window: 3-5 AM → 3-10 AM for triangles
4. Independent triangle logic (doesn't block on Asia range)

Expected improvements:
- Triangle trades: 1.6/year → 8-12/year
- Maintains high quality (65-75% WR expected)
- Better diversification between strategies
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_manager import TradingSession
from core.indicators import ema, atr
from strategies.pattern_detector import PatternDetector


class LondonBreakoutV41Optimized:
    def __init__(self, pair='EURUSD', risk_percent=1.0, initial_capital=100000,
                 enable_asia_breakout=True, enable_triangle_breakout=True):
        self.pair = pair
        self.pip_value = 0.0001

        # Strategy toggles
        self.enable_asia_breakout = enable_asia_breakout
        self.enable_triangle_breakout = enable_triangle_breakout

        # OPTIMIZED Asia breakout parameters (from v3.1 - unchanged)
        self.min_asia_range_pips = 15
        self.max_asia_range_pips = 60
        self.breakout_buffer_pips = 1.5
        self.min_first_hour_move_pips = 18

        # OPTIMIZED Triangle pattern parameters (v4.1)
        self.triangle_lookback = 60  # Increased from 40 for better validation
        self.triangle_min_pivots = 3
        self.triangle_r2_min = 0.5  # Relaxed from 0.6
        self.triangle_slope_tolerance = 0.0003  # Relaxed from 0.0002
        self.triangle_buffer_pct = 0.0015  # 0.15% breakout buffer (≈1.5 pips)
        self.triangle_time_start = 3  # 3 AM
        self.triangle_time_end = 9  # 10 AM (extended from 5 AM)

        # Risk/Reward
        self.risk_reward_ratio = 1.3
        self.min_tp_pips = 25
        self.use_trailing_stop = True

        # Position Sizing
        self.risk_percent = risk_percent
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Position tracking
        self.position = None
        self.asia_ranges = {}
        self.traded_ranges = set()
        self.traded_patterns = set()

        # Initialize pattern detector with optimized parameters
        self.pattern_detector = PatternDetector(
            lookback=self.triangle_lookback,
            min_pivot_points=self.triangle_min_pivots,
            r_squared_min=self.triangle_r2_min,
            slope_tolerance=self.triangle_slope_tolerance
        )

    def calculate_indicators(self, df):
        """Calculate H4 trend indicators"""
        df = df.copy()
        df['ema_21'] = ema(df['close'], 21)
        df['ema_50'] = ema(df['close'], 50)
        df['atr'] = atr(df['high'], df['low'], df['close'], 14)

        df['trend'] = 0
        df.loc[df['ema_21'] > df['ema_50'], 'trend'] = 1
        df.loc[df['ema_21'] < df['ema_50'], 'trend'] = -1

        return df

    def calculate_position_size(self, stop_loss_pips):
        """Calculate position size based on risk percentage"""
        risk_amount = self.current_capital * (self.risk_percent / 100)
        dollars_per_pip = risk_amount / stop_loss_pips
        lots = round(dollars_per_pip / 10, 2)
        lots = max(0.01, lots)
        return lots, dollars_per_pip

    def get_h4_trend(self, h4_df, current_time):
        """Get H4 trend at current time"""
        h4_bars = h4_df[h4_df.index <= current_time]
        if len(h4_bars) == 0:
            return 0
        latest = h4_bars.iloc[-1]
        return latest.get('trend', 0)

    def get_asia_range(self, df, current_datetime):
        """Get Asia session range for the current day"""
        current_date = current_datetime.date()

        if current_date in self.asia_ranges:
            return self.asia_ranges[current_date]

        asia_range = TradingSession.get_asia_range(df, current_date)

        if asia_range is not None:
            range_pips = asia_range['range_pips']
            if self.min_asia_range_pips <= range_pips <= self.max_asia_range_pips:
                self.asia_ranges[current_date] = asia_range
                return asia_range

        return None

    def check_first_hour_momentum(self, df, london_open_time, direction):
        """Check if first hour of London session shows strong momentum"""
        if london_open_time not in df.index:
            return False

        first_bar = df.loc[london_open_time]

        if direction == 'long':
            move_pips = (first_bar['high'] - first_bar['low']) / self.pip_value
            is_bullish = first_bar['close'] > first_bar['open']
            return is_bullish and move_pips >= self.min_first_hour_move_pips
        else:
            move_pips = (first_bar['high'] - first_bar['low']) / self.pip_value
            is_bearish = first_bar['close'] < first_bar['open']
            return is_bearish and move_pips >= self.min_first_hour_move_pips

    def check_asia_breakout_signal(self, df, h4_df, idx):
        """Check for Asia range breakout (v3.1 logic - unchanged)"""
        if not self.enable_asia_breakout:
            return None

        if not TradingSession.is_in_session(idx, TradingSession.LONDON):
            return None

        current_date = idx.date()
        if current_date in self.traded_ranges:
            return None

        asia_range = self.get_asia_range(df, idx)
        if asia_range is None:
            return None

        row = df.loc[idx]
        high = row['high']
        low = row['low']
        atr_val = row.get('atr', 0.0004)

        asia_high = asia_range['high']
        asia_low = asia_range['low']
        buffer = self.breakout_buffer_pips * self.pip_value

        h4_trend = self.get_h4_trend(h4_df, idx)

        # BULLISH BREAKOUT
        if high > (asia_high + buffer):
            if h4_trend == -1:
                return None

            if idx.hour == 3:
                if not self.check_first_hour_momentum(df, idx, 'long'):
                    return None
            elif idx.hour == 4:
                london_open = idx.replace(hour=3, minute=0)
                if not self.check_first_hour_momentum(df, london_open, 'long'):
                    return None
            else:
                return None

            entry_price = asia_high + buffer
            sl_distance_pips = min(asia_range['range_pips'] * 0.6, 40)
            sl = entry_price - (sl_distance_pips * self.pip_value)

            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price + (tp_pips * self.pip_value)

            return ('long', entry_price, sl, tp, 'asia_breakout')

        # BEARISH BREAKOUT
        elif low < (asia_low - buffer):
            if h4_trend == 1:
                return None

            if idx.hour == 3:
                if not self.check_first_hour_momentum(df, idx, 'short'):
                    return None
            elif idx.hour == 4:
                london_open = idx.replace(hour=3, minute=0)
                if not self.check_first_hour_momentum(df, london_open, 'short'):
                    return None
            else:
                return None

            entry_price = asia_low - buffer
            sl_distance_pips = min(asia_range['range_pips'] * 0.6, 40)
            sl = entry_price + (sl_distance_pips * self.pip_value)

            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price - (tp_pips * self.pip_value)

            return ('short', entry_price, sl, tp, 'asia_breakout')

        return None

    def check_triangle_breakout_signal(self, df, h4_df, idx):
        """
        v4.1 OPTIMIZED: Check for triangle pattern breakout

        Changes:
        - Extended time window (3-10 AM)
        - NO momentum filter (pattern is self-validating)
        - Independent from Asia range
        """
        if not self.enable_triangle_breakout:
            return None

        # Extended time window: 3-10 AM (was 3-5 AM)
        if not (self.triangle_time_start <= idx.hour <= self.triangle_time_end):
            return None

        # Must be London session
        if not TradingSession.is_in_session(idx, TradingSession.LONDON):
            return None

        current_pos = df.index.get_loc(idx)

        if current_pos < self.triangle_lookback:
            return None

        # Detect patterns
        patterns = self.pattern_detector.detect_all_patterns(df, current_pos)

        if len(patterns) == 0:
            return None

        pattern = patterns[0]

        # Check if pattern already traded
        pattern_id = (
            pattern['type'],
            pattern['start_index'],
            pattern['end_index']
        )

        if pattern_id in self.traded_patterns:
            return None

        row = df.loc[idx]
        current_price = row['close']
        atr_val = row.get('atr', 0.0004)

        # Check for breakout
        breakout_direction = self.pattern_detector.check_breakout(
            pattern,
            current_price,
            self.triangle_buffer_pct
        )

        if breakout_direction is None:
            return None

        h4_trend = self.get_h4_trend(h4_df, idx)

        resistance_price = pattern['resistance']['price']
        support_price = pattern['support']['price']

        # LONG BREAKOUT
        if breakout_direction == 'long':
            # Filter by pattern type and trend
            if pattern['type'] == 'ascending':
                if h4_trend == -1:
                    return None
            elif pattern['type'] == 'descending':
                if h4_trend != 1:
                    return None
            elif h4_trend == -1:
                return None

            # NO MOMENTUM FILTER - Pattern geometry is the setup

            # Entry and stops
            entry_price = resistance_price * (1 + self.triangle_buffer_pct)

            sl = support_price * (1 - self.triangle_buffer_pct * 0.5)
            sl_distance_pips = (entry_price - sl) / self.pip_value

            # Cap stop loss
            if sl_distance_pips > 50:
                sl_distance_pips = 50
                sl = entry_price - (sl_distance_pips * self.pip_value)

            # Take profit
            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price + (tp_pips * self.pip_value)

            self.traded_patterns.add(pattern_id)

            return ('long', entry_price, sl, tp, f'triangle_{pattern["type"]}')

        # SHORT BREAKOUT
        elif breakout_direction == 'short':
            # Filter by pattern type and trend
            if pattern['type'] == 'descending':
                if h4_trend == 1:
                    return None
            elif pattern['type'] == 'ascending':
                if h4_trend != -1:
                    return None
            elif h4_trend == 1:
                return None

            # NO MOMENTUM FILTER

            entry_price = support_price * (1 - self.triangle_buffer_pct)

            sl = resistance_price * (1 + self.triangle_buffer_pct * 0.5)
            sl_distance_pips = (sl - entry_price) / self.pip_value

            if sl_distance_pips > 50:
                sl_distance_pips = 50
                sl = entry_price + (sl_distance_pips * self.pip_value)

            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price - (tp_pips * self.pip_value)

            self.traded_patterns.add(pattern_id)

            return ('short', entry_price, sl, tp, f'triangle_{pattern["type"]}')

        return None

    def check_entry_signal(self, df, h4_df, idx):
        """Check for entry signals from both strategies"""
        # Try Asia breakout first
        asia_signal = self.check_asia_breakout_signal(df, h4_df, idx)
        if asia_signal:
            return asia_signal

        # Try triangle breakout (independent)
        triangle_signal = self.check_triangle_breakout_signal(df, h4_df, idx)
        if triangle_signal:
            return triangle_signal

        return None

    def update_trailing_stop(self, position, current_price):
        """Enhanced stepped trailing stop (v3.1 logic)"""
        if not self.use_trailing_stop:
            return position['sl']

        entry = position['entry_price']
        sl = position['sl']
        position_type = position['type']

        original_sl = position.get('original_sl', sl)
        risk = abs(entry - original_sl)

        if position_type == 'long':
            profit = current_price - entry
            r_multiple = profit / risk if risk > 0 else 0

            if r_multiple >= 2.5:
                new_sl = current_price - (0.5 * risk)
            elif r_multiple >= 2.0:
                new_sl = entry + (1.5 * risk)
            elif r_multiple >= 1.5:
                new_sl = entry + (0.75 * risk)
            elif r_multiple >= 1.0:
                new_sl = entry + (2 * self.pip_value)
            else:
                return sl

            return max(new_sl, sl)

        else:
            profit = entry - current_price
            r_multiple = profit / risk if risk > 0 else 0

            if r_multiple >= 2.5:
                new_sl = current_price + (0.5 * risk)
            elif r_multiple >= 2.0:
                new_sl = entry - (1.5 * risk)
            elif r_multiple >= 1.5:
                new_sl = entry - (0.75 * risk)
            elif r_multiple >= 1.0:
                new_sl = entry - (2 * self.pip_value)
            else:
                return sl

            return min(new_sl, sl)

    def check_exit_signal(self, df, idx):
        """Check if open position should be closed"""
        if self.position is None:
            return None

        row = df.loc[idx]
        position_type = self.position['type']
        sl = self.position['sl']
        tp = self.position['tp']

        high = row['high']
        low = row['low']
        close = row['close']

        # Update trailing stop
        sl = self.update_trailing_stop(self.position, close)
        self.position['sl'] = sl

        # Check stop loss
        if position_type == 'long':
            if low <= sl:
                return ('sl', sl)
        else:
            if high >= sl:
                return ('sl', sl)

        # Check take profit
        if position_type == 'long':
            if high >= tp:
                return ('tp', tp)
        else:
            if low <= tp:
                return ('tp', tp)

        # Time-based exit: Close at London close (12 PM)
        if idx.hour >= 12 and idx.hour < 13:
            return ('time', close)

        return None

    def backtest(self, h1_df, h4_df):
        """Run backtest on H1 data"""
        # Calculate indicators
        h1_df = self.calculate_indicators(h1_df)
        h4_df = self.calculate_indicators(h4_df)

        # Add pivot points for pattern detection
        if self.enable_triangle_breakout:
            h1_df = self.pattern_detector.find_pivot_points(h1_df)

        # Reset backtest state
        trades = []
        self.position = None
        self.asia_ranges = {}
        self.traded_ranges = set()
        self.traded_patterns = set()
        self.current_capital = self.initial_capital

        for idx in h1_df.index:
            # Check exit
            if self.position is not None:
                exit_signal = self.check_exit_signal(h1_df, idx)
                if exit_signal:
                    exit_reason, exit_price = exit_signal
                    entry_price = self.position['entry_price']
                    position_type = self.position['type']

                    # Calculate P&L
                    if position_type == 'long':
                        pnl_pips = (exit_price - entry_price) / self.pip_value
                    else:
                        pnl_pips = (entry_price - exit_price) / self.pip_value

                    lots = self.position['lots']
                    dollars_per_pip = self.position['dollars_per_pip']
                    pnl_dollars = pnl_pips * dollars_per_pip

                    # Subtract costs
                    commission = 0.0005 * (lots * 100000)
                    slippage = 0.5 * dollars_per_pip
                    pnl_dollars -= (commission + slippage)

                    # Update capital
                    self.current_capital += pnl_dollars

                    trades.append({
                        'entry_time': self.position['entry_time'],
                        'exit_time': idx,
                        'type': position_type,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'sl': self.position['sl'],
                        'tp': self.position['tp'],
                        'lots': lots,
                        'dollars_per_pip': dollars_per_pip,
                        'pnl_pips': pnl_pips,
                        'pnl_dollars': pnl_dollars,
                        'capital_after': self.current_capital,
                        'exit_reason': exit_reason,
                        'signal_type': self.position.get('signal_type', 'unknown'),
                        'hold_hours': (idx - self.position['entry_time']).total_seconds() / 3600
                    })

                    self.position = None

            # Check entry
            if self.position is None:
                entry_signal = self.check_entry_signal(h1_df, h4_df, idx)
                if entry_signal:
                    position_type, entry_price, sl, tp, signal_type = entry_signal

                    sl_distance_pips = abs(entry_price - sl) / self.pip_value
                    lots, dollars_per_pip = self.calculate_position_size(sl_distance_pips)

                    self.position = {
                        'type': position_type,
                        'entry_price': entry_price,
                        'entry_time': idx,
                        'sl': sl,
                        'original_sl': sl,
                        'tp': tp,
                        'lots': lots,
                        'dollars_per_pip': dollars_per_pip,
                        'signal_type': signal_type
                    }

                    # Mark range as traded if Asia breakout
                    if signal_type == 'asia_breakout':
                        self.traded_ranges.add(idx.date())

        return pd.DataFrame(trades)


if __name__ == '__main__':
    from core.data_loader import ForexDataLoader

    print("=" * 80)
    print("LONDON BREAKOUT v4.1 - OPTIMIZED TRIANGLE PARAMETERS")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Test on full 2020-2025 period
    h1_df = h1_df[h1_df.index >= '2020-01-01']
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nTesting period: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"H1 bars: {len(h1_df):,}")
    print(f"H4 bars: {len(h4_df):,}\n")

    # Test 3 configurations
    configs = [
        ("Asia Breakout Only", True, False),
        ("Triangle Breakout Only (v4.1 Optimized)", False, True),
        ("Combined (Both)", True, True)
    ]

    results_summary = []

    for config_name, enable_asia, enable_triangle in configs:
        print(f"\n{'='*80}")
        print(f"Testing: {config_name}")
        print(f"{'='*80}")

        strategy = LondonBreakoutV41Optimized(
            risk_percent=0.75,
            initial_capital=100000,
            enable_asia_breakout=enable_asia,
            enable_triangle_breakout=enable_triangle
        )

        trades = strategy.backtest(h1_df, h4_df)

        if len(trades) == 0:
            print("❌ No trades generated.")
            results_summary.append({
                'config': config_name,
                'trades': 0,
                'wr': 0,
                'pnl': 0
            })
            continue

        wins = trades[trades['pnl_dollars'] > 0]
        losses = trades[trades['pnl_dollars'] <= 0]

        print(f"\nTotal trades: {len(trades)}")
        print(f"Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
        print(f"Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
        print(f"Avg P&L per trade: ${trades['pnl_dollars'].mean():.2f}")
        print(f"Total P&L: ${trades['pnl_dollars'].sum():,.2f}")

        if len(wins) > 0 and len(losses) > 0:
            print(f"Avg win: ${wins['pnl_dollars'].mean():.2f}")
            print(f"Avg loss: ${losses['pnl_dollars'].mean():.2f}")
            profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())
            print(f"Profit factor: {profit_factor:.2f}")

        # Signal type breakdown
        if 'signal_type' in trades.columns:
            print(f"\nSignal types:")
            for sig_type in trades['signal_type'].unique():
                sig_trades = trades[trades['signal_type'] == sig_type]
                sig_wins = sig_trades[sig_trades['pnl_dollars'] > 0]
                wr = len(sig_wins) / len(sig_trades) * 100 if len(sig_trades) > 0 else 0
                avg_pnl = sig_trades['pnl_dollars'].mean()
                print(f"  {sig_type}: {len(sig_trades)} trades, {wr:.1f}% WR, "
                      f"Avg P&L: ${avg_pnl:.2f}")

        # Annualized
        days = (h1_df.index.max() - h1_df.index.min()).days
        years = days / 365.25
        total_pnl = trades['pnl_dollars'].sum()
        print(f"\nAnnualized:")
        print(f"  Trades/Year: {len(trades)/years:.1f}")
        print(f"  Annual P&L: ${total_pnl/years:,.2f}")

        results_summary.append({
            'config': config_name,
            'trades': len(trades),
            'trades_per_year': len(trades)/years,
            'wr': len(wins)/len(trades)*100,
            'total_pnl': total_pnl,
            'annual_pnl': total_pnl/years,
            'pf': profit_factor if len(wins) > 0 and len(losses) > 0 else 0
        })

    # Comparison table
    print("\n" + "=" * 80)
    print("v4.0 vs v4.1 COMPARISON")
    print("=" * 80)
    print("\n Triangle-Only Results:")
    print(f"  v4.0: 9 trades (1.6/year), 100% WR, $10,057 total ($1,754/year)")
    for r in results_summary:
        if 'Triangle' in r['config'] and 'Only' in r['config']:
            print(f"  v4.1: {r['trades']} trades ({r['trades_per_year']:.1f}/year), "
                  f"{r['wr']:.1f}% WR, ${r['total_pnl']:,.0f} total (${r['annual_pnl']:,.0f}/year)")

    print("\n Combined Results:")
    print(f"  v4.0: 243 trades (42.4/year), 58.4% WR, $107,404 total ($18,734/year)")
    for r in results_summary:
        if 'Combined' in r['config']:
            print(f"  v4.1: {r['trades']} trades ({r['trades_per_year']:.1f}/year), "
                  f"{r['wr']:.1f}% WR, ${r['total_pnl']:,.0f} total (${r['annual_pnl']:,.0f}/year)")

    print("\n" + "=" * 80)
    print("✅ v4.1 OPTIMIZED backtest complete")
    print("=" * 80)
