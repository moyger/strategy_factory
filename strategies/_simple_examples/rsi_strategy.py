"""
RSI Mean Reversion Strategy

Buy when RSI crosses below oversold level, sell when RSI crosses above overbought level.
"""

import pandas as pd
import numpy as np


class RSIStrategy:
    """
    RSI Mean Reversion Strategy

    Parameters:
        period: RSI period (default 14)
        oversold: Oversold threshold (default 30)
        overbought: Overbought threshold (default 70)
    """

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"RSI_{period}_{oversold}_{overbought}"

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals column
        """
        df = df.copy()

        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['close'])

        # Generate signals
        df['signal'] = None
        df.loc[(df['rsi'] < self.oversold) & (df['rsi'].shift(1) >= self.oversold), 'signal'] = 'BUY'
        df.loc[(df['rsi'] > self.overbought) & (df['rsi'].shift(1) <= self.overbought), 'signal'] = 'SELL'

        return df

    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'period': self.period,
            'oversold': self.oversold,
            'overbought': self.overbought
        }

    def __str__(self):
        return f"RSI Mean Reversion ({self.period}, {self.oversold}/{self.overbought})"
