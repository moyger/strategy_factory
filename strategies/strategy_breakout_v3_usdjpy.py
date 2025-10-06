"""
Strategy: London Breakout v3.0 - USD/JPY Version

Adapted from EUR/USD v3 for USD/JPY:
- Pip value: 0.01 (vs 0.0001 for EUR/USD)
- Same logic: Asia range breakout + trend filter + momentum
- Parameters: Same as EUR/USD v3 (15 pips min range, 2 pip buffer, etc.)

Testing hypothesis: USD/JPY should perform similarly to EUR/USD
- Both are major pairs with good liquidity
- Both active during London session
- USD/JPY has Tokyo close → London open transition (good for breakouts)
- Negative correlation with EUR/USD (-35%) provides diversification
"""
import pandas as pd
import numpy as np
from session_manager import TradingSession
from indicators import ema, atr

class LondonBreakoutV3:
    def __init__(self, pair='USDJPY'):
        self.pair = pair
        # USD/JPY pip value is 0.01 (not 0.0001 like EUR/USD)
        self.pip_value = 0.01 if 'JPY' in pair else 0.0001

        # Strategy parameters (adjusted for USD/JPY volatility)
        # USD/JPY has ~2× the volatility of EUR/USD (136 pips/day vs 60-80)
        if 'JPY' in pair:
            self.min_asia_range_pips = 30   # 2× EUR/USD's 15
            self.max_asia_range_pips = 150  # 2.5× EUR/USD's 60
            self.breakout_buffer_pips = 4.0  # 2× EUR/USD's 2
            self.min_first_hour_move_pips = 30  # 2× EUR/USD's 15
        else:
            self.min_asia_range_pips = 15
            self.max_asia_range_pips = 60
            self.breakout_buffer_pips = 2.0
            self.min_first_hour_move_pips = 15

        # Risk/Reward
        self.risk_reward_ratio = 1.3    # Lowered from 1.5
        self.min_tp_pips = 25
        self.use_trailing_stop = True

        # Position tracking
        self.position = None
        self.asia_ranges = {}
        self.traded_ranges = set()

    def calculate_indicators(self, df):
        """Calculate H4 trend indicators"""
        df = df.copy()
        df['ema_21'] = ema(df['close'], 21)
        df['ema_50'] = ema(df['close'], 50)
        df['atr'] = atr(df['high'], df['low'], df['close'], 14)

        # Trend direction
        df['trend'] = 0
        df.loc[df['ema_21'] > df['ema_50'], 'trend'] = 1   # Uptrend
        df.loc[df['ema_21'] < df['ema_50'], 'trend'] = -1  # Downtrend

        return df

    def get_h4_trend(self, h4_df, current_time):
        """Get H4 trend at current time"""
        # Find most recent H4 bar
        h4_bars = h4_df[h4_df.index <= current_time]
        if len(h4_bars) == 0:
            return 0

        latest = h4_bars.iloc[-1]
        return latest.get('trend', 0)

    def get_asia_range(self, df, current_datetime):
        """Get Asia session range for the current day"""
        current_date = current_datetime.date()

        # Check cache
        if current_date in self.asia_ranges:
            return self.asia_ranges[current_date]

        # Calculate Asia range
        asia_range = TradingSession.get_asia_range(df, current_date)

        # FIX: Recalculate range_pips with correct pip_value for JPY pairs
        if asia_range:
            asia_range['range_pips'] = (asia_range['high'] - asia_range['low']) / self.pip_value

        # Validate range
        if asia_range is not None:
            range_pips = asia_range['range_pips']
            if self.min_asia_range_pips <= range_pips <= self.max_asia_range_pips:
                self.asia_ranges[current_date] = asia_range
                return asia_range

        return None

    def check_first_hour_momentum(self, df, london_open_time, direction):
        """
        Check if first hour of London session shows strong momentum

        Args:
        - df: H1 dataframe
        - london_open_time: Timestamp of London open (3 AM)
        - direction: 'long' or 'short'

        Returns: True if strong momentum, False otherwise
        """
        # Get the 3 AM bar (first hour of London)
        if london_open_time not in df.index:
            return False

        first_bar = df.loc[london_open_time]

        if direction == 'long':
            # For longs: require bullish bar with good range
            move_pips = (first_bar['high'] - first_bar['low']) / self.pip_value
            is_bullish = first_bar['close'] > first_bar['open']
            return is_bullish and move_pips >= self.min_first_hour_move_pips
        else:  # short
            # For shorts: require bearish bar with good range
            move_pips = (first_bar['high'] - first_bar['low']) / self.pip_value
            is_bearish = first_bar['close'] < first_bar['open']
            return is_bearish and move_pips >= self.min_first_hour_move_pips

    def check_entry_signal(self, df, h4_df, idx):
        """
        Check if there's a valid entry signal with all filters

        Returns: ('long', entry_price, sl, tp, asia_range) or ('short', ...) or None
        """
        # Only trade during London session
        if not TradingSession.is_in_session(idx, TradingSession.LONDON):
            return None

        # Check if we've already traded this Asia range
        current_date = idx.date()
        if current_date in self.traded_ranges:
            return None

        # Get Asia range
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

        # Get H4 trend
        h4_trend = self.get_h4_trend(h4_df, idx)

        # BULLISH BREAKOUT: Price breaks above Asia high
        if high > (asia_high + buffer):
            # Filter 1: Only trade if H4 trend is up (or neutral)
            if h4_trend == -1:  # Don't buy in downtrend
                return None

            # Filter 2: Check first hour momentum (if this is not 3 AM, skip)
            if idx.hour == 3:  # First hour of London
                if not self.check_first_hour_momentum(df, idx, 'long'):
                    return None
            elif idx.hour == 4:  # Second hour - check if 3 AM had momentum
                london_open = idx.replace(hour=3, minute=0)
                if not self.check_first_hour_momentum(df, london_open, 'long'):
                    return None
            else:
                # After 4 AM, don't take breakouts (late)
                return None

            entry_price = asia_high + buffer

            # Better stop loss: Use tighter stop (50% of Asia range below entry)
            sl_distance_pips = min(asia_range['range_pips'] * 0.6, 40)
            sl = entry_price - (sl_distance_pips * self.pip_value)

            # Dynamic TP: 1.5× risk or 2× ATR, whichever is larger
            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price + (tp_pips * self.pip_value)

            return ('long', entry_price, sl, tp, asia_range)

        # BEARISH BREAKOUT: Price breaks below Asia low
        elif low < (asia_low - buffer):
            # Filter 1: Only trade if H4 trend is down (or neutral)
            if h4_trend == 1:  # Don't sell in uptrend
                return None

            # Filter 2: Check first hour momentum
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

            # Better stop loss
            sl_distance_pips = min(asia_range['range_pips'] * 0.6, 40)
            sl = entry_price + (sl_distance_pips * self.pip_value)

            # Dynamic TP
            risk_pips = sl_distance_pips
            tp_from_rr = risk_pips * self.risk_reward_ratio
            tp_from_atr = (atr_val / self.pip_value) * 2
            tp_pips = max(tp_from_rr, tp_from_atr, self.min_tp_pips)
            tp = entry_price - (tp_pips * self.pip_value)

            return ('short', entry_price, sl, tp, asia_range)

        return None

    def update_trailing_stop(self, position, current_price):
        """
        Update stop loss to breakeven once 50% of TP reached

        Returns: updated stop loss price
        """
        if not self.use_trailing_stop:
            return position['sl']

        entry = position['entry_price']
        tp = position['tp']
        sl = position['sl']
        position_type = position['type']

        if position_type == 'long':
            # Calculate 50% of distance to TP
            halfway = entry + (tp - entry) * 0.5

            # If price reached halfway, move SL to breakeven
            if current_price >= halfway and sl < entry:
                return entry + (2 * self.pip_value)  # Breakeven + 2 pips
        else:  # short
            halfway = entry - (entry - tp) * 0.5

            if current_price <= halfway and sl > entry:
                return entry - (2 * self.pip_value)

        return sl

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

        # Check stop loss hit
        if position_type == 'long':
            if low <= sl:
                return ('sl', sl)
        else:
            if high >= sl:
                return ('sl', sl)

        # Check take profit hit
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
        """
        Run backtest on H1 data with H4 trend filter

        Args:
        - h1_df: H1 OHLCV dataframe
        - h4_df: H4 OHLCV dataframe (for trend)

        Returns: DataFrame with trades
        """
        # Calculate indicators
        h1_df = self.calculate_indicators(h1_df)
        h4_df = self.calculate_indicators(h4_df)

        trades = []
        self.position = None
        self.asia_ranges = {}
        self.traded_ranges = set()

        for idx in h1_df.index:
            # Check exit first
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

                    # Assume 1.0 lot, $10/pip
                    pnl_dollars = pnl_pips * 10.0

                    # Subtract costs
                    commission = 0.0005 * 100000
                    slippage = 0.5 * 10
                    pnl_dollars -= (commission + slippage)

                    trades.append({
                        'entry_time': self.position['entry_time'],
                        'exit_time': idx,
                        'type': position_type,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'sl': self.position['sl'],
                        'tp': self.position['tp'],
                        'pnl_pips': pnl_pips,
                        'pnl_dollars': pnl_dollars,
                        'exit_reason': exit_reason,
                        'hold_hours': (idx - self.position['entry_time']).total_seconds() / 3600
                    })

                    self.position = None

            # Check entry signal
            if self.position is None:
                entry_signal = self.check_entry_signal(h1_df, h4_df, idx)
                if entry_signal:
                    position_type, entry_price, sl, tp, asia_range = entry_signal
                    self.position = {
                        'type': position_type,
                        'entry_price': entry_price,
                        'entry_time': idx,
                        'sl': sl,
                        'tp': tp,
                        'asia_range': asia_range
                    }
                    self.traded_ranges.add(idx.date())

        return pd.DataFrame(trades)


if __name__ == '__main__':
    from data_loader import ForexDataLoader

    print("=" * 80)
    print("LONDON BREAKOUT v3.0 - USD/JPY")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('USDJPY', 'H1')
    h4_df = loader.load('USDJPY', 'H4')

    # Filter to 2023-2025
    h1_df = h1_df[h1_df.index >= '2023-01-01']
    h4_df = h4_df[h4_df.index >= '2023-01-01']

    print(f"\nTesting period: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"H1 bars: {len(h1_df):,}")
    print(f"H4 bars: {len(h4_df):,}\n")

    # Run backtest
    strategy = LondonBreakoutV3(pair='USDJPY')
    trades = strategy.backtest(h1_df, h4_df)

    if len(trades) == 0:
        print("❌ No trades generated. Filters may be too strict.")
    else:
        print(f"Total trades: {len(trades)}")

        # Analyze results
        wins = trades[trades['pnl_dollars'] > 0]
        losses = trades[trades['pnl_dollars'] <= 0]

        print(f"\nPerformance:")
        print(f"  Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
        print(f"  Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
        print(f"  Avg P&L per trade: ${trades['pnl_dollars'].mean():.2f}")
        print(f"  Total P&L: ${trades['pnl_dollars'].sum():,.2f}")
        print(f"  Avg hold time: {trades['hold_hours'].mean():.1f} hours")

        if len(wins) > 0 and len(losses) > 0:
            print(f"  Avg win: ${wins['pnl_dollars'].mean():.2f}")
            print(f"  Avg loss: ${losses['pnl_dollars'].mean():.2f}")
            profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())
            print(f"  Profit factor: {profit_factor:.2f}")

        # Exit reason breakdown
        print(f"\nExit reasons:")
        for reason in ['tp', 'sl', 'time']:
            count = len(trades[trades['exit_reason'] == reason])
            pct = count / len(trades) * 100 if len(trades) > 0 else 0
            avg_pnl = trades[trades['exit_reason'] == reason]['pnl_dollars'].mean() if count > 0 else 0
            print(f"  {reason.upper()}: {count} ({pct:.1f}%) - Avg P&L: ${avg_pnl:.2f}")

        # Sample trades
        print(f"\nSample trades (first 10):")
        sample_cols = ['entry_time', 'type', 'pnl_pips', 'pnl_dollars', 'exit_reason']
        print(trades[sample_cols].head(10).to_string(index=False))

        # Annualized metrics
        days = (h1_df.index.max() - h1_df.index.min()).days
        years = days / 365.25
        total_pnl_amt = trades['pnl_dollars'].sum()
        print(f"\nAnnualized:")
        print(f"  Trades/Year: {len(trades)/years:.1f}")
        print(f"  Annual P&L: ${total_pnl_amt/years:,.2f}")

        print("\n" + "=" * 80)
        print("✅ v3.0 OPTIMIZED backtest complete")

        # Comparison to v2
        profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 else 0
        print(f"\nIMPROVEMENT vs v2:")
        print(f"  v2: 34 trades/year, 44.2% WR, $846/year, PF 1.30")
        print(f"  v3: {len(trades)/years:.0f} trades/year, {len(wins)/len(trades)*100:.1f}% WR, ${total_pnl_amt/years:,.0f}/year, PF {profit_factor:.2f}")
