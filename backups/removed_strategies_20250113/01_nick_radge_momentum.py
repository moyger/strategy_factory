#!/usr/bin/env python3
"""
Nick Radge Momentum Strategy - Framework Implementation

Based on Nick Radge's "Unholy Grails" momentum trading system.
Refactored to use the Strategy Factory multi-asset portfolio framework.

Strategy Overview:
------------------
1. Universe: S&P 500 stocks
2. Ranking: 100-day Rate of Change (ROC)
3. Portfolio: Hold top 7-10 momentum stocks
4. Rebalance: Quarterly (reduces costs vs weekly/monthly)
5. Position Sizing: Momentum-weighted (stronger momentum = more allocation)
6. Regime Filter: Adjust positions based on SPY's 200-day and 50-day MA
7. Exit: Automatic on rebalance (drop out of top N)

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import yfinance as yf


class NickRadgeMomentumStrategy:
    """
    Nick Radge Momentum Strategy using Strategy Factory framework

    Features:
    - ROC (Rate of Change) momentum ranking
    - Market regime filtering (3-tier: Strong Bull, Weak Bull, Bear)
    - Momentum-weighted allocation
    - Quarterly rebalancing (cost-effective)
    - Relative strength filter (vs SPY)
    """

    def __init__(self,
                 portfolio_size: int = 7,
                 roc_period: int = 100,
                 ma_period: int = 100,
                 rebalance_freq: str = 'QS',  # Quarter Start
                 use_momentum_weighting: bool = True,
                 use_regime_filter: bool = True,
                 use_relative_strength: bool = True,
                 regime_ma_long: int = 200,
                 regime_ma_short: int = 50,
                 strong_bull_positions: int = 7,
                 weak_bull_positions: int = 3,
                 bear_positions: int = 0,
                 bear_market_asset: Optional[str] = None,
                 bear_allocation: float = 1.0):
        """
        Initialize Nick Radge Momentum Strategy

        Args:
            portfolio_size: Number of stocks to hold (default: 7)
            roc_period: ROC lookback period (default: 100 days)
            ma_period: Moving average trend filter (default: 100 days)
            rebalance_freq: Rebalancing frequency ('QS' = quarterly)
            use_momentum_weighting: Weight positions by momentum strength
            use_regime_filter: Enable 3-tier regime-based adjustments
            use_relative_strength: Only buy stocks outperforming SPY
            regime_ma_long: Long-term MA for regime (200 days)
            regime_ma_short: Short-term MA for regime (50 days)
            strong_bull_positions: Positions in strong bull market
            weak_bull_positions: Positions in weak bull market
            bear_positions: Positions in bear market (0 = cash)
            bear_market_asset: Ticker to trade during BEAR (e.g., 'SQQQ', 'SPXU', 'SH')
            bear_allocation: Allocation % for bear asset (1.0 = 100%)
        """
        self.portfolio_size = portfolio_size
        self.roc_period = roc_period
        self.ma_period = ma_period
        self.rebalance_freq = rebalance_freq
        self.use_momentum_weighting = use_momentum_weighting
        self.use_regime_filter = use_regime_filter
        self.use_relative_strength = use_relative_strength
        self.regime_ma_long = regime_ma_long
        self.regime_ma_short = regime_ma_short
        self.strong_bull_positions = strong_bull_positions
        self.weak_bull_positions = weak_bull_positions
        self.bear_positions = bear_positions
        self.bear_market_asset = bear_market_asset
        self.bear_allocation = bear_allocation
        self.name = f"NickRadge_Momentum_Top{portfolio_size}"

    def calculate_indicators(self, prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Calculate momentum indicators for all stocks

        Args:
            prices: DataFrame with stock prices (columns = tickers)

        Returns:
            Dictionary with 'roc', 'ma', 'above_ma' DataFrames
        """
        # Calculate ROC (Rate of Change) for all stocks
        roc = prices.pct_change(self.roc_period) * 100

        # Calculate Moving Average
        ma = prices.rolling(window=self.ma_period).mean()

        # Trend filter: Above MA
        above_ma = prices > ma

        return {
            'roc': roc,
            'ma': ma,
            'above_ma': above_ma
        }

    def calculate_regime(self, spy_prices: pd.Series) -> pd.Series:
        """
        Calculate 3-tier market regime based on SPY

        Regimes:
        - STRONG_BULL: SPY > 200-day MA
        - WEAK_BULL: SPY between 50-day and 200-day MA
        - BEAR: SPY < 50-day MA

        Args:
            spy_prices: SPY close prices

        Returns:
            Series with regime classification
        """
        ma_long = spy_prices.rolling(window=self.regime_ma_long).mean()
        ma_short = spy_prices.rolling(window=self.regime_ma_short).mean()

        regime = pd.Series('UNKNOWN', index=spy_prices.index)

        # Classification (matching original logic exactly)
        regime[spy_prices > ma_long] = 'STRONG_BULL'
        regime[(spy_prices < ma_long) & (spy_prices > ma_short)] = 'WEAK_BULL'
        regime[spy_prices < ma_short] = 'BEAR'

        return regime

    def rank_stocks(self,
                   prices: pd.DataFrame,
                   indicators: Dict[str, pd.DataFrame],
                   date: pd.Timestamp,
                   benchmark_roc: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Rank stocks by momentum at given date

        Args:
            prices: Stock prices DataFrame
            indicators: Dictionary of indicator DataFrames
            date: Date to rank stocks
            benchmark_roc: SPY ROC for relative strength filter

        Returns:
            DataFrame with top ranked stocks and their ROC
        """
        if date not in prices.index:
            return pd.DataFrame()

        roc = indicators['roc'].loc[date]
        above_ma = indicators['above_ma'].loc[date]

        # Filter: Only stocks above MA and with valid ROC
        valid_stocks = above_ma[above_ma == True].index
        # Exclude bear market asset from stock ranking
        if self.bear_market_asset:
            valid_stocks = [s for s in valid_stocks if s != self.bear_market_asset]
        valid_stocks = [s for s in valid_stocks if pd.notna(roc[s])]

        if len(valid_stocks) == 0:
            return pd.DataFrame()

        # Get ROC for valid stocks
        roc_valid = roc[valid_stocks]

        # Remove any remaining NaN
        roc_valid = roc_valid.dropna()

        if len(roc_valid) == 0:
            return pd.DataFrame()

        # Relative strength filter: Only stocks outperforming SPY
        stocks_before_rs = len(roc_valid)
        if self.use_relative_strength and benchmark_roc is not None and date in benchmark_roc.index:
            spy_roc = benchmark_roc.loc[date]
            if pd.notna(spy_roc):
                roc_valid = roc_valid[roc_valid > spy_roc]

        stocks_after_rs = len(roc_valid)

        if len(roc_valid) == 0:
            return pd.DataFrame()

        # Sort by ROC (descending)
        ranked = roc_valid.sort_values(ascending=False)

        return pd.DataFrame({
            'ticker': ranked.index,
            'roc': ranked.values
        })

    def generate_allocations(self,
                           prices: pd.DataFrame,
                           spy_prices: Optional[pd.Series] = None,
                           benchmark_roc: Optional[pd.Series] = None,
                           enable_regime_recovery: bool = True) -> pd.DataFrame:
        """
        Generate portfolio allocations over time with regime recovery

        Args:
            prices: DataFrame with stock prices (columns = tickers)
            spy_prices: SPY prices for regime filtering
            benchmark_roc: SPY ROC for relative strength
            enable_regime_recovery: If True, re-enter positions when BEAR -> BULL (default: True)

        Returns:
            DataFrame with allocation weights over time
        """
        print(f"\n📊 Calculating indicators for {len(prices.columns)} stocks...")
        indicators = self.calculate_indicators(prices)

        # Calculate market regime if enabled
        regime = None
        if self.use_regime_filter and spy_prices is not None:
            print(f"   Calculating market regime...")
            regime = self.calculate_regime(spy_prices)

            # Show regime summary
            regime_counts = regime.value_counts()
            total_days = len(regime)
            print(f"\n   Market Regime Summary:")
            for reg, count in regime_counts.items():
                pct = (count / total_days) * 100
                print(f"   - {reg}: {count} days ({pct:.1f}%)")

        # Initialize allocations
        allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        # Determine rebalance dates
        # Generate ideal rebalance dates (quarter starts)
        ideal_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.rebalance_freq
        )

        # Find nearest trading day for each ideal date
        all_rebalance_dates = []
        for ideal_date in ideal_dates:
            # Find nearest date in prices.index
            nearest_idx = prices.index.searchsorted(ideal_date)
            if nearest_idx < len(prices.index):
                nearest_date = prices.index[nearest_idx]
                all_rebalance_dates.append(nearest_date)

        all_rebalance_dates = pd.DatetimeIndex(all_rebalance_dates).unique()

        # Skip early rebalances where we don't have enough data for indicators
        # Need at least max(roc_period, ma_period) days (they overlap)
        min_date = prices.index[0] + pd.Timedelta(days=max(self.roc_period, self.ma_period))
        rebalance_dates = all_rebalance_dates[all_rebalance_dates >= min_date]

        print(f"\n   Quarterly rebalances: {len(rebalance_dates)}")
        if len(rebalance_dates) > 0:
            print(f"   First rebalance: {rebalance_dates[0].date()}")
            print(f"   Last rebalance: {rebalance_dates[-1].date()}")

        # Track current allocations and last regime for regime recovery
        current_weights = None
        last_regime = None
        regime_recoveries = 0

        # Process day by day for regime recovery
        rebalance_set = set(rebalance_dates)

        for date in prices.index:
            if date < min_date:
                continue

            # Check current regime
            current_regime = None
            if self.use_regime_filter and regime is not None and date in regime.index:
                current_regime = regime.loc[date]

            # Detect regime recovery (BEAR -> BULL) and we're in cash
            # Only trigger on BEAR (not UNKNOWN) to match original
            is_regime_recovery = False
            if (enable_regime_recovery and
                last_regime == 'BEAR' and
                current_regime in ['STRONG_BULL', 'WEAK_BULL'] and
                current_weights is None):
                is_regime_recovery = True
                regime_recoveries += 1
                print(f"   🔄 Regime recovery on {date.date()} - Re-entering positions early")

            # Determine if we should rebalance
            is_rebalance_date = date in rebalance_set

            if is_rebalance_date or is_regime_recovery:
                # Determine portfolio size based on regime
                portfolio_size = self.portfolio_size

                if self.use_regime_filter and current_regime is not None:
                    if current_regime == 'STRONG_BULL':
                        portfolio_size = self.strong_bull_positions
                    elif current_regime == 'WEAK_BULL':
                        portfolio_size = self.weak_bull_positions
                    else:  # BEAR or UNKNOWN
                        portfolio_size = self.bear_positions

                # If bear market, go to cash OR bear market asset
                if portfolio_size == 0:
                    # Check if we have a bear market asset to trade
                    if self.bear_market_asset and self.bear_market_asset in allocations.columns:
                        # Allocate to bear market asset (e.g., SQQQ)
                        allocations.loc[date, :] = 0.0
                        allocations.loc[date, self.bear_market_asset] = self.bear_allocation
                        current_weights = pd.Series({self.bear_market_asset: self.bear_allocation})
                    else:
                        # No bear asset, go to cash
                        current_weights = None
                        allocations.loc[date, :] = 0.0
                else:
                    # Rank stocks by momentum
                    ranked = self.rank_stocks(prices, indicators, date, benchmark_roc)

                    if len(ranked) > 0:
                        # Select top N stocks
                        top_stocks = ranked.head(portfolio_size)

                        # Calculate allocation weights
                        if self.use_momentum_weighting:
                            # Momentum-weighted
                            positive_roc = top_stocks['roc'].clip(lower=0)
                            total_roc = positive_roc.sum()

                            if total_roc > 0:
                                weights = positive_roc / total_roc
                                weights.index = top_stocks['ticker'].values
                            else:
                                weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)
                        else:
                            # Equal weight
                            weights = pd.Series(1.0 / len(top_stocks), index=top_stocks['ticker'].values)

                        current_weights = weights
                        # Apply weights
                        for ticker in allocations.columns:
                            allocations.loc[date, ticker] = weights.get(ticker, 0.0)
                    else:
                        current_weights = None
                        allocations.loc[date, :] = 0.0
            else:
                # Between rebalances - maintain current positions
                if current_weights is not None:
                    for ticker in allocations.columns:
                        allocations.loc[date, ticker] = current_weights.get(ticker, 0.0)
                else:
                    allocations.loc[date, :] = 0.0

            last_regime = current_regime

        if regime_recoveries > 0:
            print(f"   Total regime recoveries: {regime_recoveries}")

        return allocations

    def backtest(self,
                prices: pd.DataFrame,
                spy_prices: Optional[pd.Series] = None,
                initial_capital: float = 10000,
                fees: float = 0.001,
                slippage: float = 0.0005) -> vbt.Portfolio:
        """
        Backtest the strategy using vectorbt

        Args:
            prices: DataFrame with stock prices (columns = tickers)
            spy_prices: SPY prices for regime filtering
            initial_capital: Starting capital
            fees: Trading fees (0.001 = 0.1%)
            slippage: Slippage (0.0005 = 0.05%)

        Returns:
            vectorbt Portfolio object
        """
        print(f"\n📊 Running Nick Radge Momentum Strategy...")
        print(f"   Universe: {len(prices.columns)} stocks")
        print(f"   Portfolio Size: {self.portfolio_size} positions")
        print(f"   Rebalance: {self.rebalance_freq}")
        print(f"   Momentum Weighting: {self.use_momentum_weighting}")
        print(f"   Regime Filter: {self.use_regime_filter}")
        print(f"   Relative Strength: {self.use_relative_strength}")

        # Calculate benchmark ROC if using relative strength
        benchmark_roc = None
        if self.use_relative_strength and spy_prices is not None:
            benchmark_roc = spy_prices.pct_change(self.roc_period) * 100

        # Generate allocations
        allocations = self.generate_allocations(prices, spy_prices, benchmark_roc)

        # Ensure allocations and prices have same index AND columns
        common_idx = prices.index.intersection(allocations.index)
        common_cols = prices.columns.intersection(allocations.columns)

        prices_aligned = prices.loc[common_idx, common_cols]
        allocations_aligned = allocations.loc[common_idx, common_cols]

        # Count active positions
        active_positions = (allocations_aligned > 0).sum(axis=1)
        print(f"\n   Avg positions held: {active_positions.mean():.1f}")
        print(f"   Max positions held: {active_positions.max():.0f}")

        # Run backtest with vectorbt
        print(f"\n📈 Running vectorbt backtest...")

        portfolio = vbt.Portfolio.from_orders(
            close=prices_aligned,
            size=allocations_aligned,
            size_type='targetpercent',
            init_cash=initial_capital,
            fees=fees,
            slippage=slippage,
            group_by=True,  # Treat all columns as single portfolio
            cash_sharing=True  # Share cash across all positions
        )

        return portfolio

    def print_results(self, portfolio: vbt.Portfolio, prices: pd.DataFrame, spy_return: Optional[float] = None):
        """Print backtest results"""
        print("\n" + "="*80)
        print("NICK RADGE MOMENTUM STRATEGY - BACKTEST RESULTS")
        print("="*80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Universe: {len(prices.columns)} stocks")
        print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
        if self.bear_market_asset:
            print(f"   Bear Market Asset: {self.bear_market_asset} ({self.bear_allocation*100:.0f}% allocation)")

        # Get scalar metrics
        final_value = portfolio.value().iloc[-1]
        if isinstance(final_value, pd.Series):
            final_value = final_value.sum()

        init_cash = portfolio.init_cash
        if isinstance(init_cash, pd.Series):
            init_cash = init_cash.sum()

        total_return = ((final_value / init_cash) - 1) * 100

        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
            if isinstance(sharpe, pd.Series):
                sharpe = sharpe.mean()
        except:
            sharpe = 0.0

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max()

        print(f"\n📈 Performance:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Final Equity: ${final_value:,.2f}")
        print(f"   Sharpe Ratio: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_dd * 100:.2f}%")

        if spy_return is not None:
            print(f"\n📊 vs SPY Buy & Hold:")
            print(f"   SPY Return: {spy_return:.2f}%")
            print(f"   Outperformance: {total_return - spy_return:+.2f}%")
            if total_return > spy_return:
                print(f"   Status: ✅ OUTPERFORMED")
            else:
                print(f"   Status: ❌ UNDERPERFORMED")

        trades_count = portfolio.trades.count()
        if isinstance(trades_count, pd.Series):
            trades_count = trades_count.sum()

        print(f"\n💼 Trading:")
        print(f"   Total Trades: {trades_count}")

        if trades_count > 0:
            try:
                win_rate = portfolio.trades.win_rate()
                if isinstance(win_rate, pd.Series):
                    win_rate = win_rate.mean()
                print(f"   Win Rate: {win_rate * 100:.1f}%")
            except:
                pass

            try:
                profit_factor = portfolio.trades.profit_factor()
                if isinstance(profit_factor, pd.Series):
                    profit_factor = profit_factor.mean()
                print(f"   Profit Factor: {profit_factor:.2f}")
            except:
                pass

        print("\n" + "="*80)

    def __str__(self):
        return f"Nick Radge Momentum (Top {self.portfolio_size}, {self.rebalance_freq} rebal)"


def download_sp500_stocks(num_stocks: int = 50, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Download S&P 500 stock data

    Args:
        num_stocks: Number of stocks to download
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        DataFrame with close prices (columns = tickers)
    """
    # Top S&P 500 stocks
    tickers = [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
        'CRM', 'AMD', 'INTC', 'CSCO', 'QCOM', 'INTU', 'NOW', 'AMAT', 'MU', 'PLTR',
        # Finance
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW', 'AXP', 'SPGI',
        # Healthcare
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
        # Consumer
        'WMT', 'HD', 'MCD', 'NKE', 'COST', 'SBUX', 'TGT', 'LOW', 'DIS', 'CMCSA',
    ][:num_stocks]

    print(f"📥 Downloading {len(tickers)} stocks...")
    print(f"   Period: {start_date} to {end_date}")

    # Download data
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)

    # Extract close prices
    if len(tickers) == 1:
        prices = data['Close'].to_frame()
        prices.columns = tickers
    else:
        prices = data['Close']

    # Remove any stocks with insufficient data
    prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)

    print(f"✅ Downloaded {len(prices.columns)} stocks with sufficient data")

    return prices


def download_spy(start_date: str, end_date: str) -> pd.Series:
    """Download SPY data for regime filtering and benchmark"""
    print(f"\n📊 Downloading SPY (benchmark)...")

    # Add extra lookback for MA calculation
    lookback_start = pd.to_datetime(start_date) - timedelta(days=400)

    df = yf.download('SPY', start=lookback_start, end=end_date, auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    spy_prices = df['Close']

    # Filter to requested date range
    spy_prices = spy_prices[spy_prices.index >= start_date]

    print(f"✅ SPY data loaded ({len(spy_prices)} days)")

    return spy_prices


if __name__ == "__main__":
    print("="*80)
    print("NICK RADGE MOMENTUM STRATEGY - FRAMEWORK VERSION")
    print("="*80)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 5000
    NUM_STOCKS = 50

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")

    # Download data
    print(f"\n" + "="*80)
    print("DOWNLOADING DATA")
    print("="*80)

    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)
    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align dates
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")

    # Create strategy
    print(f"\n" + "="*80)
    print("RUNNING BACKTEST")
    print("="*80)

    strategy = NickRadgeMomentumStrategy(
        portfolio_size=7,
        roc_period=100,
        ma_period=100,
        rebalance_freq='QS',  # Quarterly
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,  # Filter stocks outperforming SPY
        strong_bull_positions=7,
        weak_bull_positions=3,
        bear_positions=0
    )

    # Run backtest
    portfolio = strategy.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.001,
        slippage=0.0005
    )

    # Calculate SPY return for comparison
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Print results
    strategy.print_results(portfolio, prices, spy_return)

    print(f"\n✅ Backtest complete!")
    print("="*80)
