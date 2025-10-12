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

            # Calculate breakout bands
            upper_band = rolling_high * (1 + breakout_pct / 100)
            lower_band = rolling_low * (1 - breakout_pct / 100)

            # Generate signals (compare to previous period's band to avoid lookahead)
            entries = pd.Series(close) > upper_band.shift(1)
            exits = pd.Series(close) < lower_band.shift(1)

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
            # Extract values safely
            def extract_value(val):
                if isinstance(val, pd.Series):
                    return float(val.values[0]) if len(val) > 0 else 0.0
                elif isinstance(val, pd.DataFrame):
                    return float(val.values[0][0]) if len(val) > 0 else 0.0
                return float(val)

            # Calculate total return
            total_return = extract_value(portfolio.total_return()) * 100

            # Calculate Sharpe ratio
            try:
                sharpe = extract_value(portfolio.sharpe_ratio())
            except:
                try:
                    sharpe = extract_value(portfolio.sharpe_ratio(freq='1D'))
                except:
                    sharpe = 0.0

            # Calculate max drawdown
            max_dd = extract_value(portfolio.max_drawdown()) * 100

            # Calculate trade metrics
            trades = portfolio.trades
            num_trades = trades.count() if hasattr(trades, 'count') else 0

            if isinstance(num_trades, pd.Series):
                num_trades = int(num_trades.sum())
            else:
                num_trades = int(num_trades) if num_trades > 0 else 0

            win_rate = 0
            profit_factor = 0
            avg_trade = 0

            if num_trades > 0:
                try:
                    win_rate = extract_value(trades.win_rate())
                except:
                    win_rate = 0

                try:
                    profit_factor = extract_value(trades.profit_factor())
                except:
                    profit_factor = 0

                try:
                    avg_trade = extract_value(trades.pnl.mean())
                except:
                    avg_trade = 0

            # Calculate trades per year
            portfolio_value = portfolio.value()
            if isinstance(portfolio_value, pd.DataFrame):
                num_days = len(portfolio_value)
            elif isinstance(portfolio_value, pd.Series):
                num_days = len(portfolio_value)
            else:
                num_days = 252

            trades_per_year = (num_trades / (num_days / 252)) if num_days > 0 else 0

            return {
                'total_return': total_return,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_dd,
                'win_rate': win_rate,
                'num_trades': num_trades,
                'profit_factor': profit_factor,
                'avg_trade': avg_trade,
                'trades_per_year': trades_per_year
            }
        except Exception as e:
            print(f"      Warning: Metrics calculation error: {e}")
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

    def generate_crypto_momentum_strategies(self,
                                           prices: pd.DataFrame,
                                           universe_type: str = 'fixed',
                                           roc_periods: List[int] = [30, 60, 90, 100],
                                           rebalance_freq: List[str] = ['quarterly'],
                                           num_positions: List[int] = [5, 7, 10],
                                           verbose: bool = True) -> pd.DataFrame:
        """
        Generate crypto momentum strategies with different universe selection methods.

        This method tests different approaches to crypto portfolio construction:
        - Fixed universe (baseline)
        - Dynamic rebalancing with different selection criteria
        - Various rebalancing frequencies
        - Different portfolio sizes

        Based on research showing fixed universe outperforms dynamic rebalancing
        for crypto due to winner-take-all dynamics and persistent BTC/ETH dominance.

        Args:
            prices: DataFrame with crypto prices (columns = tickers, index = dates)
            universe_type: 'fixed', 'roc_momentum', 'relative_strength', 'breakout'
            roc_periods: ROC lookback periods to test
            rebalance_freq: ['quarterly', 'monthly', 'annual', 'none']
            num_positions: Number of positions to hold
            verbose: Print progress

        Returns:
            DataFrame with all strategy results, sorted by Sharpe ratio

        Example:
            >>> generator = StrategyGenerator()
            >>> # Test fixed universe with different parameters
            >>> results = generator.generate_crypto_momentum_strategies(
            ...     prices=crypto_prices,
            ...     universe_type='fixed',
            ...     roc_periods=[90, 100],
            ...     num_positions=[5, 7]
            ... )
            >>> print(results.head(10))
        """
        if verbose:
            total_combos = len(roc_periods) * len(rebalance_freq) * len(num_positions)
            print(f"🔄 Generating Crypto Momentum strategies...")
            print(f"   Universe type: {universe_type}")
            print(f"   Testing {total_combos} combinations")

        results = []
        strategy_id = 0

        # Define rebalance dates based on frequency
        def get_rebalance_dates(freq: str) -> pd.DatetimeIndex:
            if freq == 'none':
                return pd.DatetimeIndex([])  # No rebalancing
            elif freq == 'quarterly':
                return pd.date_range(start=prices.index[0], end=prices.index[-1], freq='QS-JAN')
            elif freq == 'monthly':
                return pd.date_range(start=prices.index[0], end=prices.index[-1], freq='MS')
            elif freq == 'annual':
                return pd.date_range(start=prices.index[0], end=prices.index[-1], freq='AS-JAN')
            else:
                return pd.date_range(start=prices.index[0], end=prices.index[-1], freq='QS-JAN')

        for roc_period, rebal_freq, n_positions in product(roc_periods, rebalance_freq, num_positions):
            try:
                # Generate allocations
                allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
                rebalance_dates = get_rebalance_dates(rebal_freq)

                # Fixed universe (baseline)
                if universe_type == 'fixed':
                    # Use top cryptos by market cap (BTC, ETH always included)
                    # For this test, use first N columns (assumes prices sorted by importance)
                    universe = prices.columns[:min(10, len(prices.columns))]
                    universe_prices = prices[universe]

                    for date in prices.index:
                        if date < prices.index[0] + pd.Timedelta(days=roc_period):
                            continue

                        # Rebalance logic
                        if len(rebalance_dates) == 0 or date in rebalance_dates:
                            # Calculate ROC
                            price_slice = universe_prices.loc[:date]
                            if len(price_slice) < roc_period:
                                continue

                            roc = (price_slice.iloc[-1] / price_slice.iloc[-roc_period] - 1).fillna(0)
                            top_n = roc.nlargest(n_positions).index.tolist()

                            # Equal weight allocation
                            for ticker in top_n:
                                allocations.loc[date, ticker] = 1.0 / n_positions

                # Dynamic universe with ROC momentum
                elif universe_type == 'roc_momentum':
                    for date in prices.index:
                        if date < prices.index[0] + pd.Timedelta(days=roc_period):
                            continue

                        if len(rebalance_dates) == 0 or date in rebalance_dates:
                            # Select from full universe
                            price_slice = prices.loc[:date]
                            if len(price_slice) < roc_period:
                                continue

                            roc = (price_slice.iloc[-1] / price_slice.iloc[-roc_period] - 1).fillna(0)
                            top_n = roc.nlargest(n_positions).index.tolist()

                            for ticker in top_n:
                                allocations.loc[date, ticker] = 1.0 / n_positions

                # Relative Strength
                elif universe_type == 'relative_strength':
                    # Use BTC as benchmark (first column assumed to be BTC)
                    btc_prices = prices.iloc[:, 0]

                    for date in prices.index:
                        if date < prices.index[0] + pd.Timedelta(days=roc_period):
                            continue

                        if len(rebalance_dates) == 0 or date in rebalance_dates:
                            price_slice = prices.loc[:date]
                            btc_slice = btc_prices.loc[:date]

                            if len(price_slice) < roc_period:
                                continue

                            # Calculate relative strength vs BTC
                            crypto_roc = (price_slice.iloc[-1] / price_slice.iloc[-roc_period] - 1).fillna(0)
                            btc_roc = (btc_slice.iloc[-1] / btc_slice.iloc[-roc_period] - 1)
                            relative_strength = crypto_roc - btc_roc

                            top_n = relative_strength.nlargest(n_positions).index.tolist()

                            for ticker in top_n:
                                allocations.loc[date, ticker] = 1.0 / n_positions

                # Hold positions between rebalance dates
                last_allocation = None
                for date in prices.index:
                    if len(rebalance_dates) == 0:
                        break  # No rebalancing, keep daily updates

                    if date in rebalance_dates or last_allocation is None:
                        last_allocation = allocations.loc[date].copy()
                    else:
                        allocations.loc[date] = last_allocation

                # Backtest with vectorbt
                # FIXED: Use 'targetpercent' for rebalancing portfolios
                # This tells vectorbt the TARGET allocation, so it automatically rebalances
                # Bug was: size_type='amount' doesn't trigger rebalancing
                portfolio = vbt.Portfolio.from_orders(
                    close=prices,
                    size=allocations,  # Use allocations directly (0.0-1.0)
                    size_type='targetpercent',
                    init_cash=self.initial_capital,
                    fees=self.commission,
                    freq='1D'
                )

                # Calculate metrics
                metrics = self._calculate_metrics(portfolio)

                results.append(StrategyResult(
                    strategy_id=strategy_id,
                    params={
                        'type': f'Crypto_{universe_type}',
                        'roc_period': roc_period,
                        'rebalance_freq': rebal_freq,
                        'num_positions': n_positions,
                        'universe_type': universe_type
                    },
                    **metrics
                ))

                strategy_id += 1

            except Exception as e:
                if verbose:
                    print(f"   ⚠️ Failed combo: roc={roc_period}, freq={rebal_freq}, n={n_positions}: {e}")
                continue

        df_results = pd.DataFrame([vars(r) for r in results])
        df_results = df_results.sort_values('sharpe_ratio', ascending=False)

        if verbose:
            print(f"✅ Generated {len(df_results)} strategies")
            if len(df_results) > 0:
                print(f"   Best Sharpe: {df_results['sharpe_ratio'].max():.2f}")
                print(f"   Best Return: {df_results['total_return'].max():.1f}%")

        return df_results
