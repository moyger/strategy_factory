"""
Multi-Timeframe Forex Data Loader
Handles M1, M5, M15, H1, H4, D1 timeframes for EUR/USD, GBP/USD, EUR/GBP, and USD/JPY
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta


class ForexDataLoader:
    """
    Unified data loader for all timeframes
    Loads CSV files from data/forex/ directory
    """

    def __init__(self, data_dir='data/forex'):
        self.data_dir = Path(data_dir)

        # File mapping
        self.pairs = {
            'EURUSD': {
                'M1': self.data_dir / 'EURUSD' / 'EURUSD_1m.csv',
                'M5': self.data_dir / 'EURUSD' / 'EURUSD_5m.csv',
                'M15': self.data_dir / 'EURUSD' / 'EURUSD_15m.csv',
                'H1': self.data_dir / 'EURUSD' / 'EURUSD_1H.csv',
                'H4': self.data_dir / 'EURUSD' / 'EURUSD_4H.csv',
                'D1': self.data_dir / 'EURUSD' / 'EURUSD_1D.csv',
            },
            'GBPUSD': {
                'M1': self.data_dir / 'GBPUSD' / 'GBPUSD_1m.csv',
                'M5': self.data_dir / 'GBPUSD' / 'GBPUSD_5m.csv',
                'M15': self.data_dir / 'GBPUSD' / 'GBPUSD_15m.csv',
                'H1': self.data_dir / 'GBPUSD' / 'GBPUSD_1H.csv',
                'H4': self.data_dir / 'GBPUSD' / 'GBPUSD_4H.csv',
                'D1': self.data_dir / 'GBPUSD' / 'GBPUSD_1D.csv',
            },
            'EURGBP': {
                'H1': self.data_dir / 'EURGBP' / 'EURGBP_1H.csv',
                'H4': self.data_dir / 'EURGBP' / 'EURGBP_4H.csv',
            },
            'USDJPY': {
                'H1': self.data_dir / 'USDJPY' / 'USDJPY_1H.csv',
                'H4': self.data_dir / 'USDJPY' / 'USDJPY_4H.csv',
            }
        }

        # Cache loaded data
        self._cache = {}

    def load(self, pair, timeframe):
        """
        Load OHLCV data for specific pair and timeframe

        Args:
            pair: 'EURUSD' or 'GBPUSD'
            timeframe: 'M1', 'M5', 'M15', 'H1', 'H4', or 'D1'

        Returns:
            DataFrame with columns: Datetime (index), open, high, low, close, volume
        """
        cache_key = f"{pair}_{timeframe}"

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key].copy()

        # Validate inputs
        if pair not in self.pairs:
            raise ValueError(f"Invalid pair: {pair}. Must be 'EURUSD' or 'GBPUSD'")

        if timeframe not in self.pairs[pair]:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be M1, M5, M15, H1, H4, or D1")

        # Load CSV
        file_path = self.pairs[pair][timeframe]

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        print(f"Loading {pair} {timeframe} data from {file_path.name}...")

        # Read CSV with datetime index
        df = pd.read_csv(
            file_path,
            parse_dates=['Datetime'],
            index_col='Datetime'
        )

        # Rename columns to lowercase
        df.columns = [c.lower() for c in df.columns]

        # Drop duplicates (if any)
        df = df[~df.index.duplicated(keep='first')]

        # Sort by datetime
        df = df.sort_index()

        print(f"  Loaded {len(df)} bars from {df.index.min()} to {df.index.max()}")

        # Cache it
        self._cache[cache_key] = df.copy()

        return df

    def load_multiple_timeframes(self, pair, timeframes):
        """
        Load multiple timeframes at once

        Args:
            pair: 'EURUSD' or 'GBPUSD'
            timeframes: List of timeframes e.g. ['M5', 'H1', 'D1']

        Returns:
            Dict with timeframe as key, DataFrame as value
        """
        data = {}
        for tf in timeframes:
            data[tf] = self.load(pair, tf)
        return data

    def get_aligned_bar(self, data_dict, target_time):
        """
        Get bars from multiple timeframes aligned to target_time

        Args:
            data_dict: Dict of {timeframe: DataFrame}
            target_time: datetime to align to

        Returns:
            Dict of {timeframe: Series} with bar data at target_time
        """
        aligned = {}

        for tf, df in data_dict.items():
            # Find closest bar at or before target_time
            mask = df.index <= target_time
            if mask.any():
                aligned[tf] = df[mask].iloc[-1]
            else:
                aligned[tf] = None

        return aligned

    def get_session_data(self, df, session_start, session_end):
        """
        Filter data by time of day (for session trading)

        Args:
            df: DataFrame with datetime index
            session_start: String like '08:00' (EST)
            session_end: String like '12:00' (EST)

        Returns:
            Filtered DataFrame with only bars during session hours
        """
        start_hour, start_min = map(int, session_start.split(':'))
        end_hour, end_min = map(int, session_end.split(':'))

        mask = (
            ((df.index.hour > start_hour) |
             ((df.index.hour == start_hour) & (df.index.minute >= start_min))) &
            ((df.index.hour < end_hour) |
             ((df.index.hour == end_hour) & (df.index.minute < end_min)))
        )

        return df[mask]

    def resample_to_higher_tf(self, df, target_timeframe):
        """
        Resample data to higher timeframe

        Args:
            df: DataFrame with M1/M5/M15 data
            target_timeframe: 'H1', 'H4', or 'D1'

        Returns:
            Resampled DataFrame
        """
        resample_map = {
            'H1': '1H',
            'H4': '4H',
            'D1': '1D'
        }

        if target_timeframe not in resample_map:
            raise ValueError(f"Invalid target timeframe: {target_timeframe}")

        freq = resample_map[target_timeframe]

        resampled = df.resample(freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return resampled


# Example usage
if __name__ == '__main__':
    loader = ForexDataLoader()

    # Load single timeframe
    eurusd_h1 = loader.load('EURUSD', 'H1')
    print(f"\nEURUSD H1: {len(eurusd_h1)} bars")
    print(eurusd_h1.head())

    # Load multiple timeframes
    eurusd_data = loader.load_multiple_timeframes('EURUSD', ['M5', 'H1', 'H4', 'D1'])
    print(f"\nLoaded {len(eurusd_data)} timeframes")

    # Session filtering
    london_session = loader.get_session_data(eurusd_h1, '03:00', '12:00')
    print(f"\nLondon session bars: {len(london_session)}")
