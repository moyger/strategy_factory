"""
Alpaca Data Loader - Free 1-minute historical data for backtesting

Uses Alpaca's paper trading API (FREE) to download historical 1-minute bars.
Perfect for backtesting small-cap short strategies.

Installation:
    pip install alpaca-trade-api

Setup:
    1. Sign up at https://alpaca.markets (free paper account)
    2. Get API keys from dashboard
    3. Set environment variables or pass keys directly
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from alpaca_trade_api import REST
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("⚠️  alpaca-trade-api not installed. Run: pip install alpaca-trade-api")


class AlpacaDataLoader:
    """
    Load 1-minute historical bars from Alpaca (FREE)

    Features:
    - 5 years of historical 1-minute data (FREE)
    - Pre-market and after-hours data included
    - Real-time quotes for paper trading
    - No rate limits on paper account
    """

    def __init__(self, api_key: str = None, secret_key: str = None, paper: bool = True):
        """
        Initialize Alpaca data loader

        Args:
            api_key: Alpaca API key (or set APCA_API_KEY_ID env var)
            secret_key: Alpaca secret key (or set APCA_API_SECRET_KEY env var)
            paper: Use paper trading endpoint (FREE, recommended for backtesting)
        """
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-trade-api not installed")

        base_url = 'https://paper-api.alpaca.markets' if paper else 'https://api.alpaca.markets'

        self.api = REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url
        )

        print(f"✅ Alpaca data loader initialized ({'PAPER' if paper else 'LIVE'} mode)")

    def get_1min_bars(self,
                      symbol: str,
                      start_date: str,
                      end_date: str,
                      extended_hours: bool = True) -> pd.DataFrame:
        """
        Get 1-minute bars for a single symbol

        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date ('2024-01-01')
            end_date: End date ('2024-12-31')
            extended_hours: Include pre-market and after-hours (default: True)

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
        """
        try:
            bars = self.api.get_bars(
                symbol,
                '1Min',
                start=start_date,
                end=end_date,
                adjustment='raw'  # Use raw prices (no split/dividend adjustments during backtest)
            ).df

            if bars.empty:
                print(f"   ⚠️  No data for {symbol}")
                return pd.DataFrame()

            # Filter extended hours if needed
            if not extended_hours:
                # Keep only regular market hours (9:30 AM - 4:00 PM ET)
                bars = bars.between_time('09:30', '16:00')

            # Rename columns to lowercase
            bars.columns = bars.columns.str.lower()

            # Reset index to have timestamp as column
            bars = bars.reset_index()
            bars = bars.rename(columns={'index': 'timestamp'})

            return bars

        except Exception as e:
            print(f"   ❌ Error downloading {symbol}: {str(e)}")
            return pd.DataFrame()

    def get_multiple_symbols(self,
                            symbols: List[str],
                            start_date: str,
                            end_date: str,
                            extended_hours: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Get 1-minute bars for multiple symbols

        Args:
            symbols: List of tickers
            start_date: Start date
            end_date: End date
            extended_hours: Include pre/post market

        Returns:
            Dictionary {symbol: DataFrame}
        """
        print(f"\n📥 Downloading 1-min bars for {len(symbols)} symbols...")
        print(f"   Period: {start_date} to {end_date}")

        data = {}

        for i, symbol in enumerate(symbols, 1):
            print(f"   [{i}/{len(symbols)}] {symbol}...", end=' ')

            bars = self.get_1min_bars(symbol, start_date, end_date, extended_hours)

            if not bars.empty:
                data[symbol] = bars
                print(f"✅ {len(bars):,} bars")
            else:
                print(f"❌ No data")

        print(f"\n✅ Downloaded {len(data)}/{len(symbols)} symbols successfully")
        return data

    def get_daily_bars(self,
                      symbol: str,
                      start_date: str,
                      end_date: str) -> pd.DataFrame:
        """
        Get daily bars (for gap calculation and multi-day patterns)

        Args:
            symbol: Stock ticker
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with daily OHLCV
        """
        try:
            bars = self.api.get_bars(
                symbol,
                '1Day',
                start=start_date,
                end=end_date,
                adjustment='raw'
            ).df

            if bars.empty:
                return pd.DataFrame()

            bars.columns = bars.columns.str.lower()
            bars = bars.reset_index()
            bars = bars.rename(columns={'index': 'timestamp'})

            return bars

        except Exception as e:
            print(f"   ❌ Error downloading daily bars for {symbol}: {str(e)}")
            return pd.DataFrame()

    def calculate_gap_pct(self, symbol: str, date: str) -> float:
        """
        Calculate gap percentage from previous close

        Args:
            symbol: Stock ticker
            date: Date to check (YYYY-MM-DD)

        Returns:
            Gap percentage (e.g., 0.25 for +25% gap)
        """
        # Get 5 days of data (to ensure we have previous close)
        end = datetime.strptime(date, '%Y-%m-%d')
        start = end - timedelta(days=5)

        daily = self.get_daily_bars(symbol, start.strftime('%Y-%m-%d'), date)

        if len(daily) < 2:
            return 0.0

        prev_close = daily.iloc[-2]['close']
        current_open = daily.iloc[-1]['open']

        gap_pct = (current_open - prev_close) / prev_close

        return gap_pct

    def get_snapshot(self, symbol: str) -> Dict:
        """
        Get current snapshot (real-time quote)

        Useful for paper trading, not needed for backtesting

        Returns:
            Dict with latest quote data
        """
        try:
            snapshot = self.api.get_snapshot(symbol)
            return {
                'symbol': symbol,
                'price': snapshot.latest_trade.price,
                'bid': snapshot.latest_quote.bid_price,
                'ask': snapshot.latest_quote.ask_price,
                'volume': snapshot.daily_bar.volume if snapshot.daily_bar else 0
            }
        except Exception as e:
            print(f"❌ Error getting snapshot for {symbol}: {e}")
            return {}


def example_usage():
    """Example: Download 1-min data for backtesting"""

    # Initialize (use your Alpaca paper API keys)
    loader = AlpacaDataLoader(
        api_key='YOUR_PAPER_KEY',
        secret_key='YOUR_PAPER_SECRET',
        paper=True  # FREE paper account
    )

    # Example 1: Single symbol
    print("\n=== Example 1: Single Symbol ===")
    aapl = loader.get_1min_bars('AAPL', '2024-01-01', '2024-01-31')
    print(f"AAPL: {len(aapl):,} 1-min bars")
    print(aapl.head())

    # Example 2: Multiple symbols (for backtesting watchlist)
    print("\n=== Example 2: Multiple Symbols ===")
    symbols = ['TSLA', 'GME', 'AMC']  # Small-cap runners
    data = loader.get_multiple_symbols(symbols, '2024-01-01', '2024-01-31')

    for symbol, bars in data.items():
        print(f"{symbol}: {len(bars):,} bars, {bars['volume'].sum():,.0f} total volume")

    # Example 3: Calculate gap
    print("\n=== Example 3: Gap Calculation ===")
    gap = loader.calculate_gap_pct('TSLA', '2024-01-15')
    print(f"TSLA gap on 2024-01-15: {gap:+.2%}")


if __name__ == '__main__':
    print("""
    Alpaca Data Loader
    ==================

    Setup instructions:
    1. Sign up at https://alpaca.markets (free)
    2. Get paper trading API keys
    3. Set environment variables:
       export APCA_API_KEY_ID='your_key'
       export APCA_API_SECRET_KEY='your_secret'

    Or pass keys directly to AlpacaDataLoader(api_key='...', secret_key='...')
    """)

    # Uncomment to run example
    # example_usage()
