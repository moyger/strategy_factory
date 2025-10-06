"""
Strategy: London Breakout v4.1 - ADAUSD (Cardano) for Bybit with 5x Leverage

Key features:
1. No pip conversion - prices in actual USD (e.g., $0.50)
2. 5x leverage for amplified returns
3. Position sizing accounts for leverage
4. Percentage-based parameters for crypto volatility

Bybit specifics:
- 5x leverage multiplies both gains and losses
- Position size = (Risk $ * Leverage) / Price Distance
- Requires less capital per trade
- Taker fee: 0.055%, Maker fee: 0.02%
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_manager import TradingSession
from core.indicators import ema, atr
from strategies.pattern_detector import PatternDetector


class LondonBreakoutV41ADAUSDBybit:
    def __init__(self, pair='ADAUSD', risk_percent=1.0, initial_capital=100000,
                 enable_asia_breakout=True, enable_triangle_breakout=True,
                 leverage=5):
        self.pair = pair
        self.leverage = leverage

        # Strategy toggles
        self.enable_asia_breakout = enable_asia_breakout
        self.enable_triangle_breakout = enable_triangle_breakout

        # ADAUSD Asia breakout parameters (% based for crypto)
        self.min_asia_range_pct = 0.01   # 1% minimum range
        self.max_asia_range_pct = 0.08   # 8% maximum range
        self.breakout_buffer_pct = 0.002  # 0.2% buffer
        self.min_first_hour_move_pct = 0.015  # 1.5% first hour move

        # ADAUSD Triangle pattern parameters
        self.triangle_lookback = 60
        self.triangle_min_pivots = 3
        self.triangle_r2_min = 0.3
        self.triangle_slope_tolerance = 0.005
        self.triangle_buffer_pct = 0.003
        self.triangle_time_start = 3
        self.triangle_time_end = 9

        # Risk/Reward
        self.risk_reward_ratio = 1.3
        self.min_tp_pct = 0.02  # Minimum 2% TP
        self.use_trailing_stop = True

        # Position Sizing
        self.risk_percent = risk_percent
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # Bybit fees
        self.taker_fee = 0.00055  # 0.055%
        self.maker_fee = 0.0002   # 0.02%

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
        """Calculate position size based on risk percentage with leverage

        For Bybit with 5x leverage:
        - Leverage amplifies position size
        - Margin required = Position Value / Leverage
        - Risk per unit still based on stop loss distance

        Example:
        - Capital: $100,000
        - Risk: 1% = $1,000
        - Entry: $0.50, SL: $0.48 (2% move = $0.02)
        - Without leverage: $1,000 / $0.02 = 50,000 ADA
        - With 5x leverage: 50,000 * 5 = 250,000 ADA
        - Margin needed: 250,000 * $0.50 / 5 = $25,000
        """
        risk_amount = self.current_capital * (self.risk_percent / 100)
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            return 0.01, 0, 0

        # Base position size (without leverage)
        base_units = risk_amount / risk_per_unit

        # With leverage, we can take a larger position
        leveraged_units = base_units * self.leverage

        # Margin required (what we actually need to lock up)
        notional_value = leveraged_units * entry_price
        margin_required = notional_value / self.leverage

        # Make sure we have enough margin
        if margin_required > self.current_capital * 0.95:  # Leave 5% buffer
            # Scale down position
            margin_required = self.current_capital * 0.95
            notional_value = margin_required * self.leverage
            leveraged_units = notional_value / entry_price

        # Convert to lots (1 lot = 100,000 ADA on some exchanges)
        # Or use leveraged_units directly if exchange quotes in units
        lots = leveraged_units / 100000
        lots = round(lots, 2)
        lots = max(0.01, lots)

        return lots, leveraged_units, margin_required

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

        if hour < 3 or hour >= 11:
            return None

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

            lots, units, margin = self.calculate_position_size(entry_price, stop_loss)

            self.traded_ranges.add(range_key)

            return {
                'type': 'ASIA_BREAKOUT',
                'direction': 1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'margin': margin,
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

            lots, units, margin = self.calculate_position_size(entry_price, stop_loss)

            self.traded_ranges.add(range_key)

            return {
                'type': 'ASIA_BREAKOUT',
                'direction': -1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'margin': margin,
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

        recent_data = df_h1[df_h1.index <= current_time].tail(self.triangle_lookback)
        if len(recent_data) < self.triangle_lookback:
            return None

        pattern = self.pattern_detector.detect_triangle(recent_data)
        if pattern is None:
            return None

        pattern_key = f"{current_time.date()}_{pattern['resistance']['slope']:.5f}_{pattern['support']['slope']:.5f}"
        if pattern_key in self.traded_patterns:
            return None

        current_bar = df_h1[df_h1.index == current_time].iloc[0]
        current_price = current_bar['close']

        resistance = pattern['resistance']['price']
        support = pattern['support']['price']

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

            lots, units, margin = self.calculate_position_size(entry_price, stop_loss)

            self.traded_patterns.add(pattern_key)

            return {
                'type': 'TRIANGLE_BREAKOUT',
                'direction': 1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'margin': margin,
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

            lots, units, margin = self.calculate_position_size(entry_price, stop_loss)

            self.traded_patterns.add(pattern_key)

            return {
                'type': 'TRIANGLE_BREAKOUT',
                'direction': -1,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lots': lots,
                'units': units,
                'margin': margin,
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

        # Trailing stop
        if self.use_trailing_stop:
            if direction == 1:
                profit_pct = (current_bar['close'] - self.position['entry_price']) / self.position['entry_price']
                if profit_pct > 0.02:
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
            'margin': signal['margin'],
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

        # Calculate P&L (with leverage, gains/losses are amplified)
        if direction == 1:
            price_change = exit_price - self.position['entry_price']
        else:
            price_change = self.position['entry_price'] - exit_price

        # P&L in dollars (leveraged position)
        pnl = price_change * self.position['units']

        # Calculate fees (on notional value)
        entry_notional = self.position['units'] * self.position['entry_price']
        exit_notional = self.position['units'] * exit_price
        entry_fee = entry_notional * self.taker_fee
        exit_fee = exit_notional * self.taker_fee
        total_fees = entry_fee + exit_fee

        pnl -= total_fees

        self.current_capital += pnl

        # Calculate ROI based on margin used
        roi_pct = (pnl / self.position['margin']) * 100

        trade_result = {
            'entry_time': self.position['entry_time'],
            'exit_time': current_time,
            'type': self.position['type'],
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': self.position['entry_price'],
            'exit_price': exit_price,
            'lots': self.position['lots'],
            'units': self.position['units'],
            'margin': self.position['margin'],
            'pct_change': (price_change / self.position['entry_price']) * 100,
            'pnl': pnl,
            'fees': total_fees,
            'roi_pct': roi_pct,  # Return on margin
            'balance': self.current_capital,
            'exit_type': exit_info['exit_type'],
            'leverage': self.leverage
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
                signal = self.check_asia_breakout_entry(df_h1, df_h4, current_time)
                if signal:
                    self.execute_trade(signal, current_time)

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
