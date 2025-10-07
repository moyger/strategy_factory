"""
Breakout Strategy

Buy when price breaks above recent high, sell when price breaks below recent low.
"""

import pandas as pd
import numpy as np


class BreakoutStrategy:
    """
    Breakout Strategy

    Parameters:
        lookback: Lookback period for high/low (default 20)
        breakout_pct: Breakout percentage threshold (default 1.0%)
    """

    def __init__(self, lookback: int = 20, breakout_pct: float = 1.0):
        self.lookback = lookback
        self.breakout_pct = breakout_pct
        self.name = f"Breakout_{lookback}_{breakout_pct}"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals column
        """
        df = df.copy()

        # Calculate rolling high/low
        df['rolling_high'] = df['high'].rolling(self.lookback).max()
        df['rolling_low'] = df['low'].rolling(self.lookback).min()

        # Calculate breakout thresholds
        df['buy_threshold'] = df['rolling_high'] * (1 + self.breakout_pct / 100)
        df['sell_threshold'] = df['rolling_low'] * (1 - self.breakout_pct / 100)

        # Generate signals
        df['signal'] = None
        df.loc[df['close'] > df['buy_threshold'], 'signal'] = 'BUY'
        df.loc[df['close'] < df['sell_threshold'], 'signal'] = 'SELL'

        return df

    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'lookback': self.lookback,
            'breakout_pct': self.breakout_pct
        }

    def __str__(self):
        return f"Breakout ({self.lookback} bars, {self.breakout_pct}%)"
