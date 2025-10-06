"""
Strategy: London Breakout v4.1 - ADAUSD (Cardano) Adaptation

Key differences from EURUSD:
1. No pip conversion - prices are in actual USD (e.g., $0.50)
2. Position sizing: contracts/lots based on dollar risk
3. Higher volatility - adjusted parameters for crypto

ADAUSD characteristics:
- Much higher volatility than forex
- 24/7 market but still respects London session patterns
- Price in dollars (e.g., $0.30 - $0.60 range)
- Typical moves: 2-10% in Asia/London sessions
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_manager import TradingSession
from core.indicators import ema, atr
from strategies.pattern_detector import PatternDetector


class LondonBreakoutV41ADAUSD:
    def __init__(self, pair='ADAUSD', risk_percent=1.0, initial_capital=100000,
                 enable_asia_breakout=True, enable_triangle_breakout=True):
        self.pair = pair

        # Strategy toggles
        self.enable_asia_breakout = enable_asia_breakout
        self.enable_triangle_breakout = enable_triangle_breakout

        # ADAUSD Asia breakout parameters (% based for crypto)
        # Typical Asia range: 1-5% of price
        self.min_asia_range_pct = 0.01   # 1% minimum range
        self.max_asia_range_pct = 0.08   # 8% maximum range
        self.breakout_buffer_pct = 0.002  # 0.2% buffer
        self.min_first_hour_move_pct = 0.015  # 1.5% first hour move

        # ADAUSD Triangle pattern parameters
        self.triangle_lookback = 60
        self.triangle_min_pivots = 3
        self.triangle_r2_min = 0.3  # Relaxed - crypto is noisy
        self.triangle_slope_tolerance = 0.005  # 0.5% tolerance
        self.triangle_buffer_pct = 0.003  # 0.3% breakout buffer
        self.triangle_time_start = 3  # 3 AM
        self.triangle_time_end = 9  # 9 AM

        # Risk/Reward
        self.risk_reward_ratio = 1.3
        self.min_tp_pct = 0.02  # Minimum 2% TP
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

        # Initialize pattern detector
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

    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calculate position size based on risk percentage

        For ADAUSD:
        - Position size = Risk $ / (Entry - Stop Loss) in dollars
        - Example: Risk $1000, Entry $0.50, SL $0.48 = $1000 / $0.02 = 50,000 ADA
        - In lots: 50,000 / 100,000 = 0.5 lots (assuming 1 lot = 100,000 ADA)
        """
        risk_amount = self.current_capital * (self.risk_percent / 100)
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            return 0.01, 0

        # Calculate units needed
        units = risk_amount / risk_per_unit

        # Convert to lots (assuming 1 lot = 100,000 ADA)
        lots = units / 100000
        lots = round(lots, 2)
        lots = max(0.01, lots)  # Minimum 0.01 lots

        return lots, units

    def identify_asia_range(self, df_h1, current_date):
        """Identify Asia session range (00:00-03:00 GMT)"""
        asia_data = df_h1[
            (df_h1.index.date == current_date) &
            (df_h1.index.hour >= 0) &
            (df_h1.index.hour < 3)
        ]

        if len(asia_data) < 2:
            return None

        high = asia_data['high'].max()
        low = asia_data['low'].min()
        mid_price = (high + low) / 2
        range_pct = (high - low) / mid_price

        if self.min_asia_range_pct <= range_pct <= self.max_asia_range_pct:
            return {
                'date': current_date,
                'high': high,
                'low': low,
                'range_pct': range_pct,
                'range_dollars': high - low
            }
        return None

    def check_first_hour_momentum(self, df_h1, current_time, direction):
        """Check if first London hour (3-4 AM) had sufficient momentum"""
        first_hour = current_time.replace(hour=3, minute=0, second=0)
        first_hour_data = df_h1[df_h1.index == first_hour]

        if len(first_hour_data) == 0:
            return False

        candle = first_hour_data.iloc[0]
        move_pct = abs(candle['close'] - candle['open']) / candle['open']

        if direction == 1:
            return candle['close'] > candle['open'] and move_pct >= self.min_first_hour_move_pct
        else:
            return candle['close'] < candle['open'] and move_pct >= self.min_first_hour_move_pct

    def check_asia_breakout_entry(self, df_h1, df_h4, current_time):
        """Check for Asia range breakout entry signal"""
        if not self.enable_asia_breakout:
            return None

        if self.position is not None:
            return None

        current_date = current_time.date()
        hour = current_time.hour

        # Only trade during London session (3-11 AM)
        if hour < 3 or hour >= 11:
            return None

        # Identify Asia range for current date
        if current_date not in self.asia_ranges:
            asia_range = self.identify_asia_range(df_h1, current_date)
            if asia_range:
                self.asia_ranges[current_date] = asia_range

        if current_date not in self.asia_ranges:
            return None

        range_key = f"{current_date}_asia"
        if range_key in self.traded_ranges:
            return None

        asia_range = self.asia_ranges[current_date]
        current_bar = df_h1[df_h1.index == current_time]

        if len(current_bar) == 0:
            return None

        current_bar = current_bar.iloc[0]
        current_price = current_bar['close']

        # Get H4 trend
        h4_bar = df_h4[df_h4.index <= current_time].iloc[-1]
        trend = h4_bar['trend']

        breakout_high = asia_range['high'] * (1 + self.breakout_buffer_pct)
        breakout_low = asia_range['low'] * (1 - self.breakout_buffer_pct)

        # Bullish breakout
        if current_price > breakout_high and trend >= 0:
            if not self.check_first_hour_momentum(df_h1, current_time, direction=1):
                return None

            entry_price = breakout_high
            stop_loss = asia_range['low']

            stop_loss_pct = (entry_price - stop_loss) / entry_price
            take_profit_pct = stop_loss_pct * self.risk_reward_ratio
            take_profit_pct = max(take_profit_pct, self.min_tp_pct)
            take_profit = entry_price * (1 + take_profit_pct)

            lots, units = self.calculate_position_size(entry_price, stop_loss)

            self.traded_ranges.add(range_key)

            return {
                'type': 'ASIA_BREAKOUT',
                'direction': 1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct,
                'asia_range_pct': asia_range['range_pct']
            }

        # Bearish breakout
        elif current_price < breakout_low and trend <= 0:
            if not self.check_first_hour_momentum(df_h1, current_time, direction=-1):
                return None

            entry_price = breakout_low
            stop_loss = asia_range['high']

            stop_loss_pct = (stop_loss - entry_price) / entry_price
            take_profit_pct = stop_loss_pct * self.risk_reward_ratio
            take_profit_pct = max(take_profit_pct, self.min_tp_pct)
            take_profit = entry_price * (1 - take_profit_pct)

            lots, units = self.calculate_position_size(entry_price, stop_loss)

            self.traded_ranges.add(range_key)

            return {
                'type': 'ASIA_BREAKOUT',
                'direction': -1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct,
                'asia_range_pct': asia_range['range_pct']
            }

        return None

    def check_triangle_breakout_entry(self, df_h1, df_h4, current_time):
        """Check for triangle pattern breakout entry signal"""
        if not self.enable_triangle_breakout:
            return None

        if self.position is not None:
            return None

        hour = current_time.hour
        if hour < self.triangle_time_start or hour >= self.triangle_time_end:
            return None

        # Get recent data
        recent_data = df_h1[df_h1.index <= current_time].tail(self.triangle_lookback)
        if len(recent_data) < self.triangle_lookback:
            return None

        # Detect triangle
        pattern = self.pattern_detector.detect_triangle(recent_data)
        if pattern is None:
            return None

        # Check if already traded this pattern
        pattern_key = f"{current_time.date()}_{pattern['resistance']['slope']:.5f}_{pattern['support']['slope']:.5f}"
        if pattern_key in self.traded_patterns:
            return None

        current_bar = df_h1[df_h1.index == current_time].iloc[0]
        current_price = current_bar['close']

        resistance = pattern['resistance']['price']
        support = pattern['support']['price']

        # Get H4 trend
        h4_bar = df_h4[df_h4.index <= current_time].iloc[-1]
        trend = h4_bar['trend']

        # Bullish breakout
        if current_price > resistance * (1 + self.triangle_buffer_pct) and trend >= 0:
            entry_price = resistance * (1 + self.triangle_buffer_pct)
            stop_loss = support

            stop_loss_pct = (entry_price - stop_loss) / entry_price
            take_profit_pct = stop_loss_pct * self.risk_reward_ratio
            take_profit_pct = max(take_profit_pct, self.min_tp_pct)
            take_profit = entry_price * (1 + take_profit_pct)

            lots, units = self.calculate_position_size(entry_price, stop_loss)

            self.traded_patterns.add(pattern_key)

            return {
                'type': 'TRIANGLE_BREAKOUT',
                'direction': 1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct,
                'pattern_quality': pattern['resistance']['r2']
            }

        # Bearish breakout
        elif current_price < support * (1 - self.triangle_buffer_pct) and trend <= 0:
            entry_price = support * (1 - self.triangle_buffer_pct)
            stop_loss = resistance

            stop_loss_pct = (stop_loss - entry_price) / entry_price
            take_profit_pct = stop_loss_pct * self.risk_reward_ratio
            take_profit_pct = max(take_profit_pct, self.min_tp_pct)
            take_profit = entry_price * (1 - take_profit_pct)

            lots, units = self.calculate_position_size(entry_price, stop_loss)

            self.traded_patterns.add(pattern_key)

            return {
                'type': 'TRIANGLE_BREAKOUT',
                'direction': -1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct,
                'pattern_quality': pattern['resistance']['r2']
            }

        return None

    def check_exit(self, df_h1, current_time):
        """Check if position should be exited"""
        if self.position is None:
            return None

        current_bar = df_h1[df_h1.index == current_time]
        if len(current_bar) == 0:
            return None

        current_bar = current_bar.iloc[0]
        direction = self.position['direction']

        # Check stop loss
        if direction == 1:
            if current_bar['low'] <= self.position['stop_loss']:
                return {'exit_type': 'STOP_LOSS', 'exit_price': self.position['stop_loss']}
            if current_bar['high'] >= self.position['take_profit']:
                return {'exit_type': 'TAKE_PROFIT', 'exit_price': self.position['take_profit']}
        else:
            if current_bar['high'] >= self.position['stop_loss']:
                return {'exit_type': 'STOP_LOSS', 'exit_price': self.position['stop_loss']}
            if current_bar['low'] <= self.position['take_profit']:
                return {'exit_type': 'TAKE_PROFIT', 'exit_price': self.position['take_profit']}

        # Trailing stop (percentage based)
        if self.use_trailing_stop:
            if direction == 1:
                profit_pct = (current_bar['close'] - self.position['entry_price']) / self.position['entry_price']
                if profit_pct > 0.02:  # If up 2%+, trail
                    new_sl = current_bar['close'] * (1 - self.position['stop_loss_pct'] * 0.5)
                    if new_sl > self.position['stop_loss']:
                        self.position['stop_loss'] = new_sl
            else:
                profit_pct = (self.position['entry_price'] - current_bar['close']) / self.position['entry_price']
                if profit_pct > 0.02:
                    new_sl = current_bar['close'] * (1 + self.position['stop_loss_pct'] * 0.5)
                    if new_sl < self.position['stop_loss']:
                        self.position['stop_loss'] = new_sl

        return None

    def execute_trade(self, signal, current_time):
        """Execute a trade based on signal"""
        self.position = {
            'entry_time': current_time,
            'entry_price': signal['entry_price'],
            'direction': signal['direction'],
            'lots': signal['lots'],
            'units': signal['units'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'stop_loss_pct': signal['stop_loss_pct'],
            'take_profit_pct': signal['take_profit_pct'],
            'type': signal['type']
        }

    def close_position(self, exit_info, current_time):
        """Close current position"""
        if self.position is None:
            return None

        exit_price = exit_info['exit_price']
        direction = self.position['direction']

        # Calculate P&L in dollars
        if direction == 1:
            price_change = exit_price - self.position['entry_price']
        else:
            price_change = self.position['entry_price'] - exit_price

        pnl = price_change * self.position['units']

        # Subtract commission (e.g., 0.1% of notional)
        notional = self.position['units'] * self.position['entry_price']
        commission = notional * 0.001
        pnl -= commission

        self.current_capital += pnl

        trade_result = {
            'entry_time': self.position['entry_time'],
            'exit_time': current_time,
            'type': self.position['type'],
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': self.position['entry_price'],
            'exit_price': exit_price,
            'lots': self.position['lots'],
            'units': self.position['units'],
            'pct_change': (price_change / self.position['entry_price']) * 100,
            'pnl': pnl,
            'balance': self.current_capital,
            'exit_type': exit_info['exit_type']
        }

        self.position = None
        return trade_result

    def run(self, df_h1, df_h4):
        """Run backtest on historical data"""
        df_h4 = self.calculate_indicators(df_h4)

        trades = []
        equity_curve = []

        for i, (current_time, row) in enumerate(df_h1.iterrows()):
            # Check exits first
            if self.position is not None:
                exit_info = self.check_exit(df_h1, current_time)
                if exit_info:
                    trade = self.close_position(exit_info, current_time)
                    if trade:
                        trades.append(trade)

            # Check entries
            if self.position is None:
                # Check Asia breakout first (higher priority)
                signal = self.check_asia_breakout_entry(df_h1, df_h4, current_time)
                if signal:
                    self.execute_trade(signal, current_time)

                # Check triangle breakout if no Asia signal
                if self.position is None:
                    signal = self.check_triangle_breakout_entry(df_h1, df_h4, current_time)
                    if signal:
                        self.execute_trade(signal, current_time)

            # Record equity
            equity_curve.append({
                'time': current_time,
                'equity': self.current_capital,
                'in_position': self.position is not None
            })

        return pd.DataFrame(trades), pd.DataFrame(equity_curve)
