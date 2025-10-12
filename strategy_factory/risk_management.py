"""
Risk Management Module

Provides utilities for:
- Position sizing (Fixed %, Kelly Criterion, Volatility-based)
- Stop loss/Take profit calculation (ATR-based, Fixed %, etc.)
- FTMO challenge rule compliance
- Session-based filters
- Volatility filters
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import time


class PositionSizer:
    """
    Calculate position sizes using various methods

    Methods:
    - Fixed percentage risk
    - Kelly Criterion
    - Volatility-based (ATR)
    - Fixed dollar amount
    """

    @staticmethod
    def fixed_percent_risk(account_balance: float,
                          risk_percent: float,
                          stop_distance: pd.Series) -> pd.Series:
        """
        Calculate position size based on fixed risk percentage

        Args:
            account_balance: Current account balance
            risk_percent: Risk per trade as percentage (e.g., 1.0 for 1%)
            stop_distance: Distance to stop loss in price units

        Returns:
            Series with position sizes

        Example:
            Account: $10,000
            Risk: 1% = $100
            Stop: $2 away
            Position size: $100 / $2 = 50 units
        """
        risk_amount = account_balance * (risk_percent / 100)
        position_size = risk_amount / stop_distance
        return position_size.fillna(0)

    @staticmethod
    def kelly_criterion(win_rate: float,
                       avg_win: float,
                       avg_loss: float,
                       account_balance: float,
                       kelly_fraction: float = 0.5) -> float:
        """
        Calculate Kelly Criterion position size

        Formula: f = (p*b - q) / b
        where:
            f = fraction of capital to bet
            p = probability of winning
            q = probability of losing (1-p)
            b = ratio of win to loss

        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive number)
            account_balance: Current account balance
            kelly_fraction: Fraction of Kelly to use (0.5 = half Kelly)

        Returns:
            Position size in dollars

        Note:
            Full Kelly can be aggressive. Using kelly_fraction=0.5 (Half Kelly)
            is recommended for safer sizing.
        """
        if avg_loss == 0:
            return 0

        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss

        kelly = (p * b - q) / b

        # Apply fraction (e.g., half Kelly)
        kelly_adjusted = kelly * kelly_fraction

        # Ensure non-negative
        kelly_adjusted = max(0, kelly_adjusted)

        # Calculate position size
        position_size = account_balance * kelly_adjusted

        return position_size

    @staticmethod
    def volatility_based(df: pd.DataFrame,
                        account_balance: float,
                        target_volatility: float = 0.01,
                        atr_period: int = 14) -> pd.Series:
        """
        Calculate position size based on volatility targeting

        Adjusts position size to maintain constant portfolio volatility

        Args:
            df: DataFrame with OHLCV data
            account_balance: Current account balance
            target_volatility: Target daily volatility (e.g., 0.01 for 1%)
            atr_period: ATR period for volatility calculation

        Returns:
            Series with position sizes
        """
        # Calculate ATR as volatility measure
        atr = RiskCalculator.calculate_atr(df, period=atr_period)

        # Normalize ATR by price
        normalized_volatility = atr / df['close']

        # Position size = (Target Vol / Actual Vol) * Account Balance
        position_size = (target_volatility / normalized_volatility) * account_balance / df['close']

        return position_size.fillna(0)


class RiskCalculator:
    """
    Calculate various risk metrics and stop loss/take profit levels
    """

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            df: DataFrame with high, low, close columns
            period: ATR period

        Returns:
            Series with ATR values
        """
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def atr_stop_loss(df: pd.DataFrame,
                     entry_price: pd.Series,
                     atr_multiplier: float = 2.0,
                     atr_period: int = 14,
                     direction: str = 'long') -> pd.Series:
        """
        Calculate ATR-based stop loss

        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price series
            atr_multiplier: Multiplier for ATR (e.g., 2.0 = 2x ATR)
            atr_period: ATR period
            direction: 'long' or 'short'

        Returns:
            Series with stop loss prices
        """
        atr = RiskCalculator.calculate_atr(df, period=atr_period)

        if direction == 'long':
            stop_loss = entry_price - (atr * atr_multiplier)
        else:  # short
            stop_loss = entry_price + (atr * atr_multiplier)

        return stop_loss

    @staticmethod
    def atr_take_profit(df: pd.DataFrame,
                       entry_price: pd.Series,
                       atr_multiplier: float = 3.0,
                       atr_period: int = 14,
                       direction: str = 'long') -> pd.Series:
        """
        Calculate ATR-based take profit

        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price series
            atr_multiplier: Multiplier for ATR (e.g., 3.0 = 3x ATR)
            atr_period: ATR period
            direction: 'long' or 'short'

        Returns:
            Series with take profit prices
        """
        atr = RiskCalculator.calculate_atr(df, period=atr_period)

        if direction == 'long':
            take_profit = entry_price + (atr * atr_multiplier)
        else:  # short
            take_profit = entry_price - (atr * atr_multiplier)

        return take_profit

    @staticmethod
    def fixed_percent_stops(entry_price: pd.Series,
                           stop_loss_pct: float = 2.0,
                           take_profit_pct: float = 6.0,
                           direction: str = 'long') -> Tuple[pd.Series, pd.Series]:
        """
        Calculate fixed percentage stop loss and take profit

        Args:
            entry_price: Entry price series
            stop_loss_pct: Stop loss percentage (e.g., 2.0 for 2%)
            take_profit_pct: Take profit percentage (e.g., 6.0 for 6%)
            direction: 'long' or 'short'

        Returns:
            Tuple of (stop_loss_prices, take_profit_prices)
        """
        if direction == 'long':
            stop_loss = entry_price * (1 - stop_loss_pct / 100)
            take_profit = entry_price * (1 + take_profit_pct / 100)
        else:  # short
            stop_loss = entry_price * (1 + stop_loss_pct / 100)
            take_profit = entry_price * (1 - take_profit_pct / 100)

        return stop_loss, take_profit


class FTMOChecker:
    """
    FTMO Challenge Rule Compliance Checker

    Implements FTMO prop firm challenge rules:
    - Daily loss limit
    - Maximum total loss (drawdown)
    - Minimum trading days
    - Profit target
    """

    # FTMO Challenge Specifications
    CHALLENGE_SPECS = {
        '10k': {
            'balance': 10000,
            'daily_loss_limit': 500,    # 5%
            'max_total_loss': 1000,     # 10%
            'profit_target': 1000,      # 10%
            'min_trading_days': 4
        },
        '25k': {
            'balance': 25000,
            'daily_loss_limit': 1250,
            'max_total_loss': 2500,
            'profit_target': 2500,
            'min_trading_days': 4
        },
        '50k': {
            'balance': 50000,
            'daily_loss_limit': 2500,
            'max_total_loss': 5000,
            'profit_target': 5000,
            'min_trading_days': 4
        },
        '100k': {
            'balance': 100000,
            'daily_loss_limit': 5000,
            'max_total_loss': 10000,
            'profit_target': 10000,
            'min_trading_days': 4
        },
        '200k': {
            'balance': 200000,
            'daily_loss_limit': 10000,
            'max_total_loss': 20000,
            'profit_target': 20000,
            'min_trading_days': 4
        }
    }

    def __init__(self, challenge_size: str = '50k'):
        """
        Initialize FTMO checker

        Args:
            challenge_size: '10k', '25k', '50k', '100k', or '200k'
        """
        if challenge_size not in self.CHALLENGE_SPECS:
            raise ValueError(f"Invalid challenge size. Choose from: {list(self.CHALLENGE_SPECS.keys())}")

        self.challenge_size = challenge_size
        self.specs = self.CHALLENGE_SPECS[challenge_size]

    def check_daily_loss(self, daily_pnl: pd.Series) -> Dict:
        """
        Check if any day exceeded daily loss limit

        Args:
            daily_pnl: Series of daily P&L values

        Returns:
            Dict with results
        """
        violations = daily_pnl < -self.specs['daily_loss_limit']
        num_violations = violations.sum()

        worst_day = daily_pnl.min()

        return {
            'passed': num_violations == 0,
            'num_violations': num_violations,
            'worst_day_pnl': worst_day,
            'limit': -self.specs['daily_loss_limit'],
            'message': f"{'PASS' if num_violations == 0 else 'FAIL'}: {num_violations} daily loss violations"
        }

    def check_max_drawdown(self, equity_curve: pd.Series) -> Dict:
        """
        Check if maximum loss (drawdown) was exceeded

        Args:
            equity_curve: Series of equity values

        Returns:
            Dict with results
        """
        starting_balance = self.specs['balance']

        # Calculate drawdown from starting balance
        drawdown = equity_curve - starting_balance
        max_loss = drawdown.min()

        passed = max_loss >= -self.specs['max_total_loss']

        return {
            'passed': passed,
            'max_loss': max_loss,
            'limit': -self.specs['max_total_loss'],
            'max_loss_pct': (max_loss / starting_balance) * 100,
            'message': f"{'PASS' if passed else 'FAIL'}: Max loss ${max_loss:.2f} (limit: ${-self.specs['max_total_loss']})"
        }

    def check_profit_target(self, final_equity: float) -> Dict:
        """
        Check if profit target was reached

        Args:
            final_equity: Final account equity

        Returns:
            Dict with results
        """
        starting_balance = self.specs['balance']
        profit = final_equity - starting_balance

        passed = profit >= self.specs['profit_target']

        return {
            'passed': passed,
            'profit': profit,
            'target': self.specs['profit_target'],
            'profit_pct': (profit / starting_balance) * 100,
            'message': f"{'PASS' if passed else 'FAIL'}: Profit ${profit:.2f} (target: ${self.specs['profit_target']})"
        }

    def check_trading_days(self, trade_dates: pd.Series) -> Dict:
        """
        Check if minimum trading days requirement was met

        Args:
            trade_dates: Series of dates when trades occurred

        Returns:
            Dict with results
        """
        unique_days = trade_dates.dt.date.nunique()
        passed = unique_days >= self.specs['min_trading_days']

        return {
            'passed': passed,
            'trading_days': unique_days,
            'required': self.specs['min_trading_days'],
            'message': f"{'PASS' if passed else 'FAIL'}: {unique_days} trading days (required: {self.specs['min_trading_days']})"
        }

    def check_all_rules(self,
                       equity_curve: pd.Series,
                       trade_dates: pd.Series) -> Dict:
        """
        Check all FTMO rules at once

        Args:
            equity_curve: Series of equity values over time
            trade_dates: Series of dates when trades occurred

        Returns:
            Dict with all results
        """
        # Calculate daily P&L
        daily_equity = equity_curve.resample('D').last().fillna(method='ffill')
        daily_pnl = daily_equity.diff()

        # Check each rule
        daily_loss = self.check_daily_loss(daily_pnl)
        max_dd = self.check_max_drawdown(equity_curve)
        profit = self.check_profit_target(equity_curve.iloc[-1])
        trading_days = self.check_trading_days(trade_dates)

        # Overall pass/fail
        all_passed = (
            daily_loss['passed'] and
            max_dd['passed'] and
            profit['passed'] and
            trading_days['passed']
        )

        return {
            'challenge_passed': all_passed,
            'challenge_size': self.challenge_size,
            'starting_balance': self.specs['balance'],
            'daily_loss_check': daily_loss,
            'max_drawdown_check': max_dd,
            'profit_target_check': profit,
            'trading_days_check': trading_days,
            'summary': f"{'✅ CHALLENGE PASSED!' if all_passed else '❌ CHALLENGE FAILED'}"
        }


class SessionFilter:
    """
    Trading session filters (London, New York, Asia, etc.)
    """

    # Session times in UTC
    SESSIONS = {
        'sydney': (time(22, 0), time(7, 0)),    # 22:00-07:00 UTC
        'tokyo': (time(0, 0), time(9, 0)),      # 00:00-09:00 UTC
        'london': (time(8, 0), time(16, 30)),   # 08:00-16:30 UTC
        'new_york': (time(13, 0), time(22, 0))  # 13:00-22:00 UTC
    }

    @staticmethod
    def is_in_session(timestamps: pd.DatetimeIndex,
                     session: str = 'london') -> pd.Series:
        """
        Check if timestamps fall within trading session

        Args:
            timestamps: DatetimeIndex
            session: 'sydney', 'tokyo', 'london', or 'new_york'

        Returns:
            Boolean series, True when in session
        """
        if session not in SessionFilter.SESSIONS:
            raise ValueError(f"Invalid session. Choose from: {list(SessionFilter.SESSIONS.keys())}")

        start_time, end_time = SessionFilter.SESSIONS[session]

        # Get time component
        times = timestamps.time

        # Handle sessions that cross midnight
        if start_time > end_time:
            in_session = (times >= start_time) | (times <= end_time)
        else:
            in_session = (times >= start_time) & (times <= end_time)

        return pd.Series(in_session, index=timestamps)

    @staticmethod
    def is_session_open(timestamps: pd.DatetimeIndex,
                       sessions: list = ['london', 'new_york']) -> pd.Series:
        """
        Check if any of the specified sessions are open

        Args:
            timestamps: DatetimeIndex
            sessions: List of session names

        Returns:
            Boolean series, True when any session is open
        """
        result = pd.Series(False, index=timestamps)

        for session in sessions:
            result |= SessionFilter.is_in_session(timestamps, session)

        return result


class VolatilityFilter:
    """
    Volatility-based filters for strategy entry/exit
    """

    @staticmethod
    def is_high_volatility(df: pd.DataFrame,
                          atr_period: int = 14,
                          threshold_multiplier: float = 1.5) -> pd.Series:
        """
        Detect high volatility periods

        Args:
            df: DataFrame with OHLCV data
            atr_period: ATR period
            threshold_multiplier: Multiplier for ATR threshold

        Returns:
            Boolean series, True when volatility is high
        """
        atr = RiskCalculator.calculate_atr(df, period=atr_period)
        atr_ma = atr.rolling(window=atr_period).mean()

        # High volatility when ATR > mean ATR * multiplier
        return atr > (atr_ma * threshold_multiplier)

    @staticmethod
    def is_low_volatility(df: pd.DataFrame,
                         atr_period: int = 14,
                         threshold_multiplier: float = 0.7) -> pd.Series:
        """
        Detect low volatility periods

        Args:
            df: DataFrame with OHLCV data
            atr_period: ATR period
            threshold_multiplier: Multiplier for ATR threshold

        Returns:
            Boolean series, True when volatility is low
        """
        atr = RiskCalculator.calculate_atr(df, period=atr_period)
        atr_ma = atr.rolling(window=atr_period).mean()

        # Low volatility when ATR < mean ATR * multiplier
        return atr < (atr_ma * threshold_multiplier)
