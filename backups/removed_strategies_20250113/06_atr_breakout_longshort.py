#!/usr/bin/env python3
"""
ATR Breakout Strategy - Tomas Nesnidal "Mr. Breakouts" Style
=============================================================

Based on the "Breakout Trading Revolution" concept.

Features:
---------
- Configurable Point of Initiation (POI): prev_close, prev_open, prev_high, prev_low
- ATR-based breakout levels: entry above/below POI by k * ATR(n)
- Optional filters: ADX threshold, SMA trend, ATR expansion
- ATR-based stops and targets (R-multiples)
- Volatility-based position sizing (risk % via ATR)
- Time-based exits (optional)

Strategy Logic:
--------------
1. Calculate POI (Point of Initiation) - typically previous close
2. Calculate ATR(n) - Average True Range
3. Long Entry: Price breaks above POI + (k * ATR)
4. Short Entry: Price breaks below POI - (k * ATR)
5. Stop: Entry ± (stop_r * ATR)
6. Target: Entry ± (target_r * ATR)
7. Optional filters: ADX > threshold, Price > SMA, ATR expanding

Typical Parameters:
------------------
- POI: prev_close
- ATR period: 40
- k (multiplier): 2.8
- ADX period: 25
- ADX minimum: 25
- SMA period: 100
- Stop R: 1.5x ATR
- Target R: 3.0x ATR
- Risk per trade: 0.5% of equity

Author: Strategy Factory (adapted from Tomas Nesnidal concept)
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ATRBreakoutParams:
    """Configuration parameters for ATR Breakout strategy"""
    poi: str = "prev_close"          # Point of Initiation
    atr_period: int = 40             # ATR calculation period
    k_multiplier: float = 2.8        # ATR multiplier for breakout
    adx_period: int = 25             # ADX calculation period
    adx_min: Optional[float] = 25.0  # Minimum ADX for trade (None = disabled)
    sma_period: Optional[int] = 100  # SMA trend filter (None = disabled)
    atr_expansion_period: Optional[int] = 20  # ATR expansion check (None = disabled)
    risk_per_trade: float = 0.005    # 0.5% risk per trade
    stop_r: float = 1.5              # Stop at 1.5 * ATR
    target_r: float = 3.0            # Target at 3.0 * ATR
    time_exit_bars: Optional[int] = None  # Time-based exit in bars (None = disabled)


class ATRBreakoutStrategy:
    """
    ATR Breakout Strategy using vectorbt framework

    This strategy enters on volatility breakouts above/below a Point of Initiation (POI),
    using ATR to define entry levels, stops, and targets.
    """

    def __init__(self, params: Optional[ATRBreakoutParams] = None):
        """
        Initialize ATR Breakout Strategy

        Args:
            params: Strategy parameters (uses defaults if None)
        """
        self.params = params or ATRBreakoutParams()
        self.name = f"ATR_Breakout_k{self.params.k_multiplier}_atr{self.params.atr_period}"

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
        tr = ATRBreakoutStrategy.calculate_true_range(high, low, close)
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
        tr = ATRBreakoutStrategy.calculate_true_range(high, low, close)

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
    def calculate_poi(open_prices: pd.Series, high: pd.Series, low: pd.Series,
                     close: pd.Series, mode: str = "prev_close") -> pd.Series:
        """
        Calculate Point of Initiation (POI)

        Args:
            open_prices: Open prices
            high: High prices
            low: Low prices
            close: Close prices
            mode: POI mode - "prev_close", "prev_open", "prev_high", "prev_low", "session_open"

        Returns:
            POI series
        """
        mode = mode.lower()

        if mode == "prev_close":
            return close.shift(1)
        elif mode == "prev_open":
            return open_prices.shift(1)
        elif mode == "prev_high":
            return high.shift(1)
        elif mode == "prev_low":
            return low.shift(1)
        elif mode == "session_open":
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

    # ==================== Signal Generation ====================

    def generate_signals(self, prices: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate entry signals and position sizing

        Args:
            prices: DataFrame with OHLC columns

        Returns:
            Tuple of (entries, sizes) DataFrames
        """
        print(f"\n📊 Generating ATR Breakout signals...")
        print(f"   Parameters: k={self.params.k_multiplier}, ATR={self.params.atr_period}")

        # Extract OHLC
        open_prices = prices['Open']
        high = prices['High']
        low = prices['Low']
        close = prices['Close']

        # Calculate indicators
        print(f"   Calculating indicators...")
        atr = self.calculate_atr(high, low, close, self.params.atr_period)
        poi = self.calculate_poi(open_prices, high, low, close, self.params.poi)

        # Calculate breakout levels
        long_trigger = poi + (self.params.k_multiplier * atr)
        short_trigger = poi - (self.params.k_multiplier * atr)

        # Initialize signals
        long_entries = pd.Series(False, index=prices.index)
        short_entries = pd.Series(False, index=prices.index)

        # Basic breakout condition
        long_breakout = high > long_trigger
        short_breakout = low < short_trigger

        # Apply filters
        filters = pd.Series(True, index=prices.index)

        # ADX filter
        if self.params.adx_min is not None:
            print(f"   Applying ADX filter (min={self.params.adx_min})...")
            adx = self.calculate_adx(high, low, close, self.params.adx_period)
            filters &= (adx >= self.params.adx_min)

        # SMA trend filter
        if self.params.sma_period is not None:
            print(f"   Applying SMA filter (period={self.params.sma_period})...")
            sma = close.rolling(window=self.params.sma_period, min_periods=1).mean()
            long_filters = filters & (close > sma)
            short_filters = filters & (close < sma)
        else:
            long_filters = filters
            short_filters = filters

        # ATR expansion filter
        if self.params.atr_expansion_period is not None:
            print(f"   Applying ATR expansion filter (period={self.params.atr_expansion_period})...")
            atr_expanding = self.check_atr_expansion(atr, self.params.atr_expansion_period)
            long_filters &= atr_expanding
            short_filters &= atr_expanding

        # Apply all filters to signals
        long_entries = long_breakout & long_filters
        short_entries = short_breakout & short_filters

        # Combine into entries DataFrame (1 = long, -1 = short, 0 = no trade)
        entries = pd.DataFrame(0, index=prices.index, columns=['signal'])
        entries.loc[long_entries, 'signal'] = 1
        entries.loc[short_entries, 'signal'] = -1

        # Calculate position sizes based on ATR risk
        stop_distance = atr * self.params.stop_r

        # Position sizing: Risk amount / stop distance
        # We'll return ATR for later use in portfolio construction
        sizes = pd.DataFrame({
            'atr': atr,
            'stop_distance': stop_distance
        })

        signal_count = (entries['signal'] != 0).sum()
        long_count = (entries['signal'] == 1).sum()
        short_count = (entries['signal'] == -1).sum()

        print(f"\n   ✅ Signals generated:")
        print(f"      Total signals: {signal_count}")
        print(f"      Long signals: {long_count}")
        print(f"      Short signals: {short_count}")

        return entries, sizes

    # ==================== Backtesting ====================

    def backtest(self, prices: pd.DataFrame, initial_capital: float = 100000,
                fees: float = 0.0005) -> vbt.Portfolio:
        """
        Backtest the ATR Breakout strategy

        Args:
            prices: DataFrame with OHLC columns
            initial_capital: Starting capital
            fees: Trading fees (0.0005 = 0.05%)

        Returns:
            vectorbt Portfolio object
        """
        print(f"\n📊 Running ATR Breakout Strategy Backtest...")
        print(f"   Initial Capital: ${initial_capital:,}")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"   Bars: {len(prices)}")

        # Generate signals
        entries, sizes = self.generate_signals(prices)

        # For vectorbt, we need to create entry/exit signals
        # Entry: when signal changes from 0 to 1 or -1
        # Exit: when signal changes back to 0, or at stop/target

        # Simple approach: enter on signal, exit after fixed bars or at stop/target
        # We'll use vectorbt's from_signals with stop loss and take profit

        close_prices = prices['Close']

        # Extract entry signals
        long_entries = entries['signal'] == 1
        short_entries = entries['signal'] == -1

        # Calculate stops and targets
        atr = sizes['atr']

        # Long stops and targets
        long_stop_prices = close_prices - (self.params.stop_r * atr)
        long_target_prices = close_prices + (self.params.target_r * atr)

        # Short stops and targets
        short_stop_prices = close_prices + (self.params.stop_r * atr)
        short_target_prices = close_prices - (self.params.target_r * atr)

        # Position sizing based on risk
        equity = initial_capital  # This should be dynamic but we'll use initial for simplicity
        risk_amount = equity * self.params.risk_per_trade
        position_sizes = (risk_amount / sizes['stop_distance']).fillna(0)
        position_sizes = position_sizes.clip(lower=1)  # At least 1 unit

        # Create portfolio with long positions
        print(f"\n📈 Running vectorbt backtest...")

        portfolio = vbt.Portfolio.from_signals(
            close=close_prices,
            entries=long_entries,
            exits=pd.Series(False, index=prices.index),  # Will use SL/TP
            short_entries=short_entries,
            short_exits=pd.Series(False, index=prices.index),
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
        print("ATR BREAKOUT STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"   Parameters:")
        print(f"      POI: {self.params.poi}")
        print(f"      ATR Period: {self.params.atr_period}")
        print(f"      K Multiplier: {self.params.k_multiplier}")
        print(f"      Stop R: {self.params.stop_r}")
        print(f"      Target R: {self.params.target_r}")

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
        return f"ATR Breakout (k={self.params.k_multiplier}, ATR={self.params.atr_period})"


# ==================== Standalone Testing ====================

if __name__ == "__main__":
    print("ATR Breakout Strategy - Test Mode")
    print("="*80)
    print("\nThis strategy requires OHLC data.")
    print("Run the example script: python examples/example_atr_breakout.py")
