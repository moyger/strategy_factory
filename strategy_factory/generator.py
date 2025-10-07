"""
Strategy Generator - Generate thousands of trading strategies using vectorbt

This module generates trading strategies by testing combinations of indicators
and parameters across historical data. Uses vectorized operations for speed.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Tuple, Optional
from itertools import product
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class StrategyResult:
    """Results from a generated strategy"""
    strategy_id: int
    params: Dict
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    profit_factor: float
    avg_trade: float
    trades_per_year: float


class StrategyGenerator:
    """
    Generate and test thousands of strategy combinations using vectorbt

    Example:
        generator = StrategyGenerator()
        results = generator.generate_sma_strategies(df, fast_range=[5,10,20], slow_range=[50,100,200])
        top_10 = results.head(10)
    """

    def __init__(self, initial_capital: float = 10000, commission: float = 0.001):
        """
        Initialize strategy generator

        Args:
            initial_capital: Starting capital for backtests
            commission: Commission per trade (0.001 = 0.1%)
        """
        self.initial_capital = initial_capital
        self.commission = commission

    def generate_sma_strategies(self,
                                df: pd.DataFrame,
                                fast_range: List[int] = [5, 10, 15, 20],
                                slow_range: List[int] = [50, 100, 150, 200],
                                verbose: bool = True) -> pd.DataFrame:
        """
        Generate SMA crossover strategies

        Args:
            df: DataFrame with OHLCV data (must have 'close' column)
            fast_range: List of fast SMA periods to test
            slow_range: List of slow SMA periods to test
            verbose: Print progress

        Returns:
            DataFrame with all strategy results, sorted by Sharpe ratio
        """
        if verbose:
            print(f"🔄 Generating SMA strategies...")
            print(f"   Testing {len(fast_range)} x {len(slow_range)} = {len(fast_range) * len(slow_range)} combinations")

        results = []
        strategy_id = 0

        # Get close prices
        close = df['close'].values

        for fast_period, slow_period in product(fast_range, slow_range):
            # Skip if fast >= slow
            if fast_period >= slow_period:
                continue

            # Calculate SMAs
            fast_sma = pd.Series(close).rolling(fast_period).mean()
            slow_sma = pd.Series(close).rolling(slow_period).mean()

            # Generate signals
            entries = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
            exits = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))

            # Run backtest
            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            # Calculate metrics
            metrics = self._calculate_metrics(portfolio)

            results.append(StrategyResult(
                strategy_id=strategy_id,
                params={'type': 'SMA', 'fast': fast_period, 'slow': slow_period},
                **metrics
            ))

            strategy_id += 1

        # Convert to DataFrame and sort
        df_results = pd.DataFrame([vars(r) for r in results])
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        if verbose:
            print(f"✅ Generated {len(df_results)} strategies")
            print(f"   Best Sharpe: {df_results['sharpe_ratio'].max():.2f}")
            print(f"   Best Return: {df_results['total_return'].max():.1f}%")

        return df_results

    def generate_rsi_strategies(self,
                               df: pd.DataFrame,
                               period_range: List[int] = [7, 14, 21, 28],
                               oversold_range: List[int] = [20, 25, 30, 35],
                               overbought_range: List[int] = [65, 70, 75, 80],
                               verbose: bool = True) -> pd.DataFrame:
        """
        Generate RSI mean reversion strategies

        Args:
            df: DataFrame with OHLCV data
            period_range: RSI periods to test
            oversold_range: Oversold thresholds to test
            overbought_range: Overbought thresholds to test
            verbose: Print progress

        Returns:
            DataFrame with all strategy results
        """
        if verbose:
            total = len(period_range) * len(oversold_range) * len(overbought_range)
            print(f"🔄 Generating RSI strategies...")
            print(f"   Testing {total} combinations")

        results = []
        strategy_id = 0

        close = df['close'].values

        for period, oversold, overbought in product(period_range, oversold_range, overbought_range):
            # Skip if oversold >= overbought
            if oversold >= overbought:
                continue

            # Calculate RSI
            rsi = self._calculate_rsi(close, period)

            # Generate signals
            entries = rsi < oversold
            exits = rsi > overbought

            # Run backtest
            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            # Calculate metrics
            metrics = self._calculate_metrics(portfolio)

            results.append(StrategyResult(
                strategy_id=strategy_id,
                params={'type': 'RSI', 'period': period, 'oversold': oversold, 'overbought': overbought},
                **metrics
            ))

            strategy_id += 1

        df_results = pd.DataFrame([vars(r) for r in results])
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        if verbose:
            print(f"✅ Generated {len(df_results)} strategies")
            print(f"   Best Sharpe: {df_results['sharpe_ratio'].max():.2f}")

        return df_results

    def generate_breakout_strategies(self,
                                    df: pd.DataFrame,
                                    lookback_range: List[int] = [10, 20, 30, 50],
                                    breakout_pct_range: List[float] = [0.5, 1.0, 1.5, 2.0],
                                    verbose: bool = True) -> pd.DataFrame:
        """
        Generate breakout strategies

        Args:
            df: DataFrame with OHLCV data
            lookback_range: Lookback periods for high/low
            breakout_pct_range: Breakout percentages above high
            verbose: Print progress

        Returns:
            DataFrame with all strategy results
        """
        if verbose:
            total = len(lookback_range) * len(breakout_pct_range)
            print(f"🔄 Generating Breakout strategies...")
            print(f"   Testing {total} combinations")

        results = []
        strategy_id = 0

        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        for lookback, breakout_pct in product(lookback_range, breakout_pct_range):
            # Calculate rolling high/low
            rolling_high = pd.Series(high).rolling(lookback).max()
            rolling_low = pd.Series(low).rolling(lookback).min()

            # Generate signals
            entries = close > rolling_high * (1 + breakout_pct / 100)
            exits = close < rolling_low * (1 - breakout_pct / 100)

            # Run backtest
            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            # Calculate metrics
            metrics = self._calculate_metrics(portfolio)

            results.append(StrategyResult(
                strategy_id=strategy_id,
                params={'type': 'Breakout', 'lookback': lookback, 'breakout_pct': breakout_pct},
                **metrics
            ))

            strategy_id += 1

        df_results = pd.DataFrame([vars(r) for r in results])
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        if verbose:
            print(f"✅ Generated {len(df_results)} strategies")
            print(f"   Best Sharpe: {df_results['sharpe_ratio'].max():.2f}")

        return df_results

    def generate_macd_strategies(self,
                                fast_range: List[int] = [8, 12, 16],
                                slow_range: List[int] = [21, 26, 31],
                                signal_range: List[int] = [7, 9, 11],
                                df: pd.DataFrame = None,
                                verbose: bool = True) -> pd.DataFrame:
        """
        Generate MACD strategies

        Args:
            df: DataFrame with OHLCV data
            fast_range: Fast EMA periods
            slow_range: Slow EMA periods
            signal_range: Signal line periods
            verbose: Print progress

        Returns:
            DataFrame with all strategy results
        """
        if verbose:
            total = len(fast_range) * len(slow_range) * len(signal_range)
            print(f"🔄 Generating MACD strategies...")
            print(f"   Testing {total} combinations")

        results = []
        strategy_id = 0

        close = df['close'].values

        for fast, slow, signal in product(fast_range, slow_range, signal_range):
            if fast >= slow:
                continue

            # Calculate MACD
            macd_line, signal_line = self._calculate_macd(close, fast, slow, signal)

            # Generate signals
            entries = (macd_line > signal_line) & (pd.Series(macd_line).shift(1) <= pd.Series(signal_line).shift(1))
            exits = (macd_line < signal_line) & (pd.Series(macd_line).shift(1) >= pd.Series(signal_line).shift(1))

            # Run backtest
            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            # Calculate metrics
            metrics = self._calculate_metrics(portfolio)

            results.append(StrategyResult(
                strategy_id=strategy_id,
                params={'type': 'MACD', 'fast': fast, 'slow': slow, 'signal': signal},
                **metrics
            ))

            strategy_id += 1

        df_results = pd.DataFrame([vars(r) for r in results])
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        if verbose:
            print(f"✅ Generated {len(df_results)} strategies")
            print(f"   Best Sharpe: {df_results['sharpe_ratio'].max():.2f}")

        return df_results

    def _calculate_metrics(self, portfolio: vbt.Portfolio) -> Dict:
        """Calculate performance metrics from portfolio"""
        try:
            stats = portfolio.stats()

            return {
                'total_return': portfolio.total_return() * 100,  # Convert to percentage
                'sharpe_ratio': portfolio.sharpe_ratio() if portfolio.sharpe_ratio() is not None else 0,
                'max_drawdown': portfolio.max_drawdown() * 100,  # Convert to percentage
                'win_rate': portfolio.trades.win_rate() if portfolio.trades.count() > 0 else 0,
                'num_trades': portfolio.trades.count(),
                'profit_factor': portfolio.trades.profit_factor() if portfolio.trades.count() > 0 else 0,
                'avg_trade': portfolio.trades.pnl.mean() if portfolio.trades.count() > 0 else 0,
                'trades_per_year': portfolio.trades.count() / (len(portfolio.value()) / 252) if len(portfolio.value()) > 0 else 0
            }
        except Exception as e:
            # Return default values if calculation fails
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'num_trades': 0,
                'profit_factor': 0,
                'avg_trade': 0,
                'trades_per_year': 0
            }

    def _calculate_rsi(self, close: np.ndarray, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        close_series = pd.Series(close)
        delta = close_series.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, close: np.ndarray, fast: int, slow: int, signal: int) -> Tuple[pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        close_series = pd.Series(close)

        ema_fast = close_series.ewm(span=fast, adjust=False).mean()
        ema_slow = close_series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        return macd_line, signal_line

    def filter_strategies(self,
                         results: pd.DataFrame,
                         min_sharpe: float = 1.0,
                         max_drawdown: float = 20.0,
                         min_trades: int = 10,
                         min_win_rate: float = 0.45) -> pd.DataFrame:
        """
        Filter strategies by quality criteria

        Args:
            results: DataFrame of strategy results
            min_sharpe: Minimum Sharpe ratio
            max_drawdown: Maximum drawdown (%)
            min_trades: Minimum number of trades
            min_win_rate: Minimum win rate (0-1)

        Returns:
            Filtered DataFrame
        """
        filtered = results[
            (results['sharpe_ratio'] >= min_sharpe) &
            (results['max_drawdown'] <= max_drawdown) &
            (results['num_trades'] >= min_trades) &
            (results['win_rate'] >= min_win_rate)
        ]

        print(f"📊 Filtered: {len(filtered)} / {len(results)} strategies passed criteria")
        return filtered
