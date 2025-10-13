#!/usr/bin/env python3
"""
Intraday Breakout Strategy - Tomas Nesnidal "Breakout Trading Revolution"
===========================================================================

Based on the authentic Tomas Nesnidal breakout codes from:
- BREAKOUT_TRADING_REVOLUTION_CODE_1
- BREAKOUT_TRADING_REVOLUTION_CODE_2

KEY DIFFERENCES from standard ATR breakout:
-------------------------------------------
1. LONG ONLY - No short positions (designed for indices/crypto bull bias)
2. INVERTED ADX LOGIC - ADX < threshold (trade consolidation breakouts, not trends)
3. DAILY POI - Uses previous day's close for intraday breakouts
4. TIME WINDOWS - Optional time-based entry filters
5. END-OF-DAY EXIT - Closes all positions at session end
6. FIXED OR ATR STOPS - Choice between fixed dollar or dynamic ATR stops

Strategy Logic:
--------------
1. Calculate POI = Previous Day's Close (or previous bar's close)
2. Calculate SPACE = k * ATR(n)
3. Long Entry: Price breaks above POI + SPACE
4. Filter: ADX(25) < threshold (LOW trend = consolidation → breakout)
5. Optional: Time window filter (trade only during specific hours)
6. Exit: End of day OR stop/target hit
7. Stop: Fixed USD amount OR stop_r * ATR
8. Target: target_r * ATR

Original Parameters (YM emini Dow, 20-min bars):
------------------------------------------------
- POI: Previous day's close
- k: 2.8
- ATR period: 40
- ADX period: 25
- ADX max: 45 (trade when ADX < 45)
- Stop: $1500 fixed
- Exit: End of day
- Time windows: Various 1-hour windows (8:30-15:15)

Crypto/Bitcoin Adaptations:
---------------------------
- 5-min bars: Use shorter periods (ATR=50-100, ADX=25)
- 24/7 market: Use session-based exit (e.g., close at midnight UTC)
- Volatility: Use ATR-based stops instead of fixed
- Time windows: Asian/London/NY session filters

Author: Strategy Factory (adapted from Tomas Nesnidal)
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import time


@dataclass
class IntraDayBreakoutParams:
    """Configuration parameters for Intraday Breakout strategy"""
    # Core Breakout Parameters
    poi_mode: str = "daily_close"     # "daily_close", "prev_close", "session_open"
    k_multiplier: float = 2.8         # ATR multiplier for breakout
    atr_period: int = 40              # ATR calculation period

    # ADX Filter (INVERTED LOGIC)
    adx_period: int = 25              # ADX calculation period
    adx_max: Optional[float] = 45.0   # ADX < threshold (low trend = consolidation)

    # Additional Filters
    sma_period: Optional[int] = None  # SMA trend filter (None = disabled)
    atr_expansion_period: Optional[int] = None  # ATR expansion check (None = disabled)

    # Position Management
    long_only: bool = True            # Long only (no shorts)
    risk_per_trade: float = 0.01      # 1% risk per trade
    stop_type: str = "atr"            # "atr" or "fixed"
    stop_r: float = 1.5               # Stop at 1.5 * ATR (if stop_type="atr")
    fixed_stop_usd: float = 1500.0    # Fixed stop (if stop_type="fixed")
    target_r: float = 3.0             # Target at 3.0 * ATR

    # Time-Based Filters
    time_window_start: Optional[str] = None  # e.g., "08:30" (None = no filter)
    time_window_end: Optional[str] = None    # e.g., "09:30"
    eod_exit_time: Optional[str] = None      # e.g., "15:15" (None = no EOD exit)

    # Session Management (for 24/7 markets like crypto)
    session_start_hour: int = 0       # Session reset hour (0-23)
    session_end_hour: int = 23        # Session close hour (0-23)


class IntraDayBreakoutStrategy:
    """
    Intraday Breakout Strategy using vectorbt framework

    This is the authentic Tomas Nesnidal "Breakout Trading Revolution" approach:
    - Long only during consolidation (ADX < threshold)
    - Breaks above previous day's close + ATR space
    - Time-based entry windows
    - End-of-day exits
    """

    def __init__(self, params: Optional[IntraDayBreakoutParams] = None):
        """
        Initialize Intraday Breakout Strategy

        Args:
            params: Strategy parameters (uses defaults if None)
        """
        self.params = params or IntraDayBreakoutParams()
        self.name = f"IntraDay_Breakout_k{self.params.k_multiplier}_atr{self.params.atr_period}"

    # ==================== Indicators ====================

    @staticmethod
    def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """Calculate True Range"""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr

    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        tr = IntraDayBreakoutStrategy.calculate_true_range(high, low, close)
        atr = tr.rolling(window=period, min_periods=1).mean()
        return atr

    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX)
        Measures trend strength (not direction)
        """
        # Calculate +DM and -DM
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        # Calculate True Range
        tr = IntraDayBreakoutStrategy.calculate_true_range(high, low, close)

        # Calculate smoothed TR
        atr_sum = tr.rolling(window=period, min_periods=1).sum()

        # Calculate +DI and -DI
        plus_di = 100 * pd.Series(plus_dm, index=high.index).rolling(period, min_periods=1).sum() / atr_sum.replace(0, np.nan)
        minus_di = 100 * pd.Series(minus_dm, index=high.index).rolling(period, min_periods=1).sum() / atr_sum.replace(0, np.nan)

        # Calculate DX and ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.rolling(window=period, min_periods=1).mean()

        return adx.fillna(0)

    @staticmethod
    def calculate_daily_close(close: pd.Series, session_end_hour: int = 23) -> pd.Series:
        """
        Calculate previous day's close for intraday data

        Args:
            close: Close prices (intraday bars)
            session_end_hour: Hour when day ends (default 23 = 11 PM)

        Returns:
            Series with previous day's close value for each bar
        """
        if not isinstance(close.index, pd.DatetimeIndex):
            raise ValueError("Price data must have DatetimeIndex")

        # Resample to daily, taking last close of each day
        daily_close = close.resample('D').last()

        # Forward fill to all intraday bars
        prev_day_close = daily_close.shift(1).reindex(close.index, method='ffill')

        return prev_day_close

    def calculate_poi(self, open_prices: pd.Series, high: pd.Series, low: pd.Series,
                     close: pd.Series) -> pd.Series:
        """
        Calculate Point of Initiation (POI)

        Args:
            open_prices: Open prices
            high: High prices
            low: Low prices
            close: Close prices

        Returns:
            POI series
        """
        mode = self.params.poi_mode.lower()

        if mode == "daily_close":
            # Previous day's close (for intraday trading)
            return self.calculate_daily_close(close, self.params.session_end_hour)
        elif mode == "prev_close":
            # Previous bar's close
            return close.shift(1)
        elif mode == "prev_open":
            return open_prices.shift(1)
        elif mode == "session_open":
            # Today's opening price
            return open_prices
        else:
            raise ValueError(f"Unknown POI mode: {mode}")

    @staticmethod
    def check_atr_expansion(atr: pd.Series, ma_period: int = 20) -> pd.Series:
        """
        Check if ATR is expanding (above its moving average)

        Args:
            atr: ATR series
            ma_period: Moving average period for comparison

        Returns:
            Boolean series (True = ATR expanding)
        """
        atr_ma = atr.rolling(window=ma_period, min_periods=1).mean()
        return atr > atr_ma

    def apply_time_filter(self, prices: pd.DataFrame) -> pd.Series:
        """
        Apply time window filter

        Args:
            prices: DataFrame with DatetimeIndex

        Returns:
            Boolean series (True = within time window)
        """
        if not isinstance(prices.index, pd.DatetimeIndex):
            raise ValueError("Price data must have DatetimeIndex")

        time_filter = pd.Series(True, index=prices.index)

        if self.params.time_window_start and self.params.time_window_end:
            # Parse time strings (e.g., "08:30")
            start_hour, start_min = map(int, self.params.time_window_start.split(':'))
            end_hour, end_min = map(int, self.params.time_window_end.split(':'))

            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)

            bar_times = prices.index.time
            time_filter = (bar_times >= start_time) & (bar_times <= end_time)

        return time_filter

    # ==================== Signal Generation ====================

    def generate_signals(self, prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate entry signals and position sizing

        Args:
            prices: DataFrame with OHLC columns

        Returns:
            Tuple of (entries, sizes) DataFrames
        """
        print(f"\n📊 Generating Intraday Breakout signals...")
        print(f"   Strategy: Long-Only, ADX < {self.params.adx_max}")
        print(f"   Parameters: k={self.params.k_multiplier}, ATR={self.params.atr_period}")

        # Extract OHLC
        open_prices = prices['Open']
        high = prices['High']
        low = prices['Low']
        close = prices['Close']

        # Calculate indicators
        print(f"   Calculating indicators...")
        atr = self.calculate_atr(high, low, close, self.params.atr_period)
        poi = self.calculate_poi(open_prices, high, low, close)

        # Calculate breakout level (LONG ONLY)
        space = self.params.k_multiplier * atr
        long_trigger = poi + space

        print(f"   POI mode: {self.params.poi_mode}")
        print(f"   Breakout level: POI + {self.params.k_multiplier} * ATR({self.params.atr_period})")

        # Initialize signals
        long_entries = pd.Series(False, index=prices.index)

        # Basic breakout condition (price breaks above trigger)
        long_breakout = high > long_trigger

        # Apply filters
        filters = pd.Series(True, index=prices.index)

        # INVERTED ADX filter (ADX < threshold = low trend = consolidation)
        if self.params.adx_max is not None:
            print(f"   Applying INVERTED ADX filter (ADX < {self.params.adx_max})...")
            adx = self.calculate_adx(high, low, close, self.params.adx_period)
            filters &= (adx < self.params.adx_max)  # NOTE: < not >= (inverted logic!)
            print(f"      → Trade during CONSOLIDATION (low ADX), not trends")

        # SMA trend filter (optional - for long-term trend alignment)
        if self.params.sma_period is not None:
            print(f"   Applying SMA filter (period={self.params.sma_period})...")
            sma = close.rolling(window=self.params.sma_period, min_periods=1).mean()
            filters &= (close > sma)  # Only long above SMA

        # ATR expansion filter (optional)
        if self.params.atr_expansion_period is not None:
            print(f"   Applying ATR expansion filter (period={self.params.atr_expansion_period})...")
            atr_expanding = self.check_atr_expansion(atr, self.params.atr_expansion_period)
            filters &= atr_expanding

        # Time window filter
        if self.params.time_window_start and self.params.time_window_end:
            print(f"   Applying time window filter ({self.params.time_window_start}-{self.params.time_window_end})...")
            time_filter = self.apply_time_filter(prices)
            filters &= time_filter

        # Apply all filters to signals
        long_entries = long_breakout & filters

        # Combine into entries DataFrame (1 = long, 0 = no trade)
        entries = pd.DataFrame(0, index=prices.index, columns=['signal'])
        entries.loc[long_entries, 'signal'] = 1

        # Calculate position sizes based on ATR risk
        if self.params.stop_type == "atr":
            stop_distance = atr * self.params.stop_r
        else:  # fixed
            # For fixed stops, we need to convert USD to points
            # This is approximate - assumes price level matters
            stop_distance = pd.Series(self.params.fixed_stop_usd, index=prices.index)

        # Position sizing: Risk amount / stop distance
        sizes = pd.DataFrame({
            'atr': atr,
            'stop_distance': stop_distance,
            'poi': poi,
            'long_trigger': long_trigger
        })

        signal_count = (entries['signal'] != 0).sum()
        long_count = (entries['signal'] == 1).sum()

        print(f"\n   ✅ Signals generated:")
        print(f"      Total signals: {signal_count}")
        print(f"      Long signals: {long_count}")
        print(f"      Short signals: 0 (long-only strategy)")

        return entries, sizes

    # ==================== Backtesting ====================

    def backtest(self, prices: pd.DataFrame, initial_capital: float = 100000,
                fees: float = 0.0005) -> vbt.Portfolio:
        """
        Backtest the Intraday Breakout strategy

        Args:
            prices: DataFrame with OHLC columns and DatetimeIndex
            initial_capital: Starting capital
            fees: Trading fees (0.0005 = 0.05%)

        Returns:
            vectorbt Portfolio object
        """
        print(f"\n📊 Running Intraday Breakout Strategy Backtest...")
        print(f"   Initial Capital: ${initial_capital:,}")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"   Bars: {len(prices)}")

        # Generate signals
        entries, sizes = self.generate_signals(prices)

        close_prices = prices['Close']

        # Extract entry signals
        long_entries = entries['signal'] == 1

        # Calculate stops and targets
        atr = sizes['atr']

        # Long stops and targets
        long_stop_prices = close_prices - sizes['stop_distance']
        long_target_prices = close_prices + (self.params.target_r * atr)

        # End-of-day exit (if specified)
        eod_exits = pd.Series(False, index=prices.index)
        if self.params.eod_exit_time and isinstance(prices.index, pd.DatetimeIndex):
            eod_hour, eod_min = map(int, self.params.eod_exit_time.split(':'))
            eod_time = time(eod_hour, eod_min)
            bar_times = prices.index.time
            eod_exits = (bar_times >= eod_time)
            print(f"   End-of-day exit enabled: {self.params.eod_exit_time}")

        # Position sizing based on risk
        equity = initial_capital  # Simplified - should be dynamic
        risk_amount = equity * self.params.risk_per_trade
        position_sizes = (risk_amount / sizes['stop_distance']).fillna(0)
        position_sizes = position_sizes.clip(lower=1)  # At least 1 unit

        # Create portfolio with long positions only
        print(f"\n📈 Running vectorbt backtest...")

        portfolio = vbt.Portfolio.from_signals(
            close=close_prices,
            entries=long_entries,
            exits=eod_exits,  # EOD exit + SL/TP
            size=position_sizes,
            size_type='amount',
            init_cash=initial_capital,
            fees=fees,
            sl_stop=long_stop_prices,
            sl_trail=False,
            tp_stop=long_target_prices,
        )

        return portfolio

    def print_results(self, portfolio: vbt.Portfolio, prices: pd.DataFrame):
        """Print backtest results"""
        print("\n" + "="*80)
        print("INTRADAY BREAKOUT STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"   Mode: LONG ONLY")
        print(f"   Parameters:")
        print(f"      POI: {self.params.poi_mode}")
        print(f"      ATR Period: {self.params.atr_period}")
        print(f"      K Multiplier: {self.params.k_multiplier}")
        print(f"      ADX Filter: ADX < {self.params.adx_max} (consolidation)")
        print(f"      Stop Type: {self.params.stop_type}")
        print(f"      Stop R: {self.params.stop_r}")
        print(f"      Target R: {self.params.target_r}")

        if self.params.time_window_start:
            print(f"      Time Window: {self.params.time_window_start} - {self.params.time_window_end}")
        if self.params.eod_exit_time:
            print(f"      EOD Exit: {self.params.eod_exit_time}")

        # Get metrics
        final_value = portfolio.value().iloc[-1]
        init_cash = portfolio.init_cash
        total_return = ((final_value / init_cash) - 1) * 100

        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
        except:
            sharpe = 0.0

        max_dd = portfolio.max_drawdown()

        print(f"\n📈 Performance:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Final Equity: ${final_value:,.2f}")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_dd * 100:.2f}%")

        trades = portfolio.trades
        trades_count = trades.count()

        print(f"\n💼 Trading:")
        print(f"   Total Trades: {trades_count}")

        if trades_count > 0:
            try:
                win_rate = trades.win_rate()
                print(f"   Win Rate: {win_rate * 100:.1f}%")
            except:
                pass

            try:
                profit_factor = trades.profit_factor()
                print(f"   Profit Factor: {profit_factor:.2f}")
            except:
                pass

        print("\n" + "="*80)

    def __str__(self):
        return f"Intraday Breakout (LONG-ONLY, ADX<{self.params.adx_max}, k={self.params.k_multiplier})"


# ==================== Standalone Testing ====================

if __name__ == "__main__":
    print("Intraday Breakout Strategy - Test Mode")
    print("="*80)
    print("\nThis strategy requires OHLC data with DatetimeIndex.")
    print("Key features:")
    print("  - LONG ONLY (no shorts)")
    print("  - INVERTED ADX (ADX < threshold = consolidation)")
    print("  - Previous day's close as POI")
    print("  - Time window filters")
    print("  - End-of-day exits")
    print("\nRun the example script to test.")
