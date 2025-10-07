"""
SMA Crossover Strategy

Simple Moving Average crossover - buy when fast SMA crosses above slow SMA,
sell when fast SMA crosses below slow SMA.
"""

import pandas as pd
import numpy as np


class SMAStrategy:
    """
    SMA Crossover Strategy

    Parameters:
        fast_period: Fast SMA period (default 10)
        slow_period: Slow SMA period (default 50)
    """

    def __init__(self, fast_period: int = 10, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"SMA_{fast_period}_{slow_period}"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals column
        """
        df = df.copy()

        # Calculate SMAs
        df['sma_fast'] = df['close'].rolling(self.fast_period).mean()
        df['sma_slow'] = df['close'].rolling(self.slow_period).mean()

        # Generate signals
        df['signal'] = None
        df.loc[(df['sma_fast'] > df['sma_slow']) & (df['sma_fast'].shift(1) <= df['sma_slow'].shift(1)), 'signal'] = 'BUY'
        df.loc[(df['sma_fast'] < df['sma_slow']) & (df['sma_fast'].shift(1) >= df['sma_slow'].shift(1)), 'signal'] = 'SELL'

        return df

    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period
        }

    def __str__(self):
        return f"SMA Crossover ({self.fast_period}/{self.slow_period})"
