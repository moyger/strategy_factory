"""
Intraday Indicators - For 1-minute bar analysis

Implements indicators for Temiz day trading strategy:
- VWAP (Volume-Weighted Average Price)
- VWAP Z-score (price extension detection)
- Volume percentiles (climax detection)
- Candle pattern detection (blow-off tops)
- Price momentum metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_vwap(bars: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume-Weighted Average Price

    VWAP is the intraday benchmark - acts as support/resistance.
    Used to identify when price is extended from fair value.

    Args:
        bars: DataFrame with high, low, close, volume

    Returns:
        Series with VWAP values
    """
    typical_price = (bars['high'] + bars['low'] + bars['close']) / 3
    vwap = (typical_price * bars['volume']).cumsum() / bars['volume'].cumsum()
    return vwap


def calculate_vwap_zscore(bars: pd.DataFrame, vwap: pd.Series = None) -> pd.Series:
    """
    Calculate price extension from VWAP in standard deviations

    Z-score > 2.0 indicates parabolic extension (short signal)
    Z-score > 3.0 indicates extreme extension (high-probability short)

    Args:
        bars: DataFrame with OHLCV data
        vwap: Pre-calculated VWAP (optional, will calculate if not provided)

    Returns:
        Series with Z-score values
    """
    if vwap is None:
        vwap = calculate_vwap(bars)

    typical_price = (bars['high'] + bars['low'] + bars['close']) / 3

    # Calculate running variance weighted by volume
    variance = ((typical_price - vwap)**2 * bars['volume']).cumsum() / bars['volume'].cumsum()
    std = np.sqrt(variance)

    # Avoid division by zero
    std = std.replace(0, np.nan)

    zscore = (bars['close'] - vwap) / std

    return zscore


def calculate_volume_percentiles(bars: pd.DataFrame, window: int = 60) -> Dict[str, pd.Series]:
    """
    Calculate rolling volume percentiles for climax detection

    Volume climax = volume spike 3-10× average
    - 95th percentile: Moderate climax
    - 99th percentile: Extreme climax (blow-off top)

    Args:
        bars: DataFrame with volume column
        window: Rolling window in minutes (default: 60 = 1 hour)

    Returns:
        Dict with '95th', '99th', 'mean' volume levels
    """
    return {
        'mean': bars['volume'].rolling(window).mean(),
        '95th': bars['volume'].rolling(window).quantile(0.95),
        '99th': bars['volume'].rolling(window).quantile(0.99)
    }


def detect_blowoff_candle(bars: pd.DataFrame, wick_threshold: float = 0.6) -> pd.Series:
    """
    Detect blow-off candle pattern

    Characteristics:
    - Upper wick >60% of total range (long upper shadow)
    - High volume (climax)
    - Indicates selling pressure at top

    Args:
        bars: DataFrame with OHLC data
        wick_threshold: Minimum wick ratio (default: 0.6 = 60%)

    Returns:
        Boolean Series (True = blow-off candle detected)
    """
    candle_range = bars['high'] - bars['low']
    upper_wick = bars['high'] - bars[['open', 'close']].max(axis=1)

    # Avoid division by zero
    wick_ratio = upper_wick / candle_range.replace(0, np.nan)

    return wick_ratio > wick_threshold


def calculate_price_velocity(bars: pd.DataFrame, period: int = 5) -> pd.Series:
    """
    Calculate price velocity (rate of change per minute)

    Used to detect parabolic moves:
    - Normal: <1% per minute
    - Parabolic: 1-3% per minute
    - Blow-off: >3% per minute

    Args:
        bars: DataFrame with close prices
        period: Lookback period in minutes

    Returns:
        Series with % change per minute
    """
    pct_change = (bars['close'] - bars['close'].shift(period)) / bars['close'].shift(period) * 100
    velocity = pct_change / period  # Normalize to per-minute rate

    return velocity


def detect_volume_climax(bars: pd.DataFrame,
                        volume_percentiles: Dict[str, pd.Series],
                        threshold: str = '99th') -> pd.Series:
    """
    Detect volume climax (spike to 95th-99th percentile)

    Args:
        bars: DataFrame with volume
        volume_percentiles: Output from calculate_volume_percentiles()
        threshold: '95th' or '99th' percentile

    Returns:
        Boolean Series (True = volume climax detected)
    """
    return bars['volume'] > volume_percentiles[threshold]


def calculate_relative_volume(bars: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate relative volume (current / average)

    RVOL interpretation:
    - <1.0: Below average (avoid)
    - 1.0-2.0: Normal
    - 2.0-5.0: High volume (good for shorts)
    - >5.0: Climax volume (best for shorts)

    Args:
        bars: DataFrame with volume
        window: Rolling window for average (default: 20 minutes)

    Returns:
        Series with relative volume ratio
    """
    avg_volume = bars['volume'].rolling(window).mean()
    rvol = bars['volume'] / avg_volume

    return rvol


def calculate_gap_from_premarket(daily_close: float,
                                 intraday_open: float) -> float:
    """
    Calculate gap percentage from previous day's close

    Gap types:
    - Gap up 5-15%: Normal runner (trade)
    - Gap up 15-30%: Strong runner (trade)
    - Gap up >30%: Parabolic gap (high risk, wait for pullback)

    Args:
        daily_close: Previous day's close price
        intraday_open: Current day's open price

    Returns:
        Gap percentage (0.10 = +10% gap)
    """
    gap_pct = (intraday_open - daily_close) / daily_close
    return gap_pct


def detect_first_red_candle(bars: pd.DataFrame) -> pd.Series:
    """
    Detect first red candle after series of green candles

    Temiz's "First Red Day" setup:
    - After 3+ green candles
    - First close < open
    - Signals exhaustion

    Args:
        bars: DataFrame with OHLC data

    Returns:
        Boolean Series (True = first red candle)
    """
    is_green = bars['close'] > bars['open']
    is_red = bars['close'] < bars['open']

    # Count consecutive green candles before current bar
    # Fill NaN with False to avoid ~ operator issues
    green_shifted = is_green.shift(1).fillna(False)
    not_green = ~green_shifted

    green_streak = (green_shifted
                   .groupby(not_green.cumsum())
                   .cumsum())

    # First red after 3+ greens
    first_red = is_red & (green_streak >= 3)

    return first_red


def calculate_float_rotation(volume_today: float,
                             float_shares: float) -> float:
    """
    Calculate how many times the float has traded today

    Float rotation interpretation:
    - <0.5×: Low volume (avoid)
    - 0.5-2×: Normal (tradeable)
    - 2-5×: High volume (good)
    - >5×: Extreme rotation (exhaustion likely)

    Args:
        volume_today: Cumulative volume for the day
        float_shares: Number of shares in the float

    Returns:
        Float rotation multiplier
    """
    if float_shares == 0:
        return 0.0

    return volume_today / float_shares


def detect_parabolic_move(bars: pd.DataFrame,
                         vwap_zscore: pd.Series,
                         price_velocity: pd.Series,
                         volume_climax: pd.Series) -> pd.Series:
    """
    Detect parabolic move using composite criteria

    Parabolic criteria (Temiz):
    1. VWAP Z-score > 2.0 (price extended)
    2. Price velocity > 1.0% per minute
    3. Volume climax (99th percentile)
    4. Uptrend for 5+ minutes

    Args:
        bars: DataFrame with OHLC data
        vwap_zscore: Output from calculate_vwap_zscore()
        price_velocity: Output from calculate_price_velocity()
        volume_climax: Output from detect_volume_climax()

    Returns:
        Boolean Series (True = parabolic conditions met)
    """
    # Check uptrend (5-min high > 5-min low)
    recent_high = bars['high'].rolling(5).max()
    recent_low = bars['low'].rolling(5).min()
    is_uptrend = bars['close'] > recent_low * 1.02  # At least 2% above 5-min low

    parabolic = (
        (vwap_zscore > 2.0) &          # Extended from VWAP
        (price_velocity > 1.0) &       # Fast price movement
        (volume_climax) &              # Volume spike
        (is_uptrend)                   # Trending up
    )

    return parabolic


def calculate_all_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all intraday indicators at once

    Convenience function for backtesting.

    Args:
        bars: DataFrame with OHLCV data

    Returns:
        DataFrame with all indicator columns added
    """
    df = bars.copy()

    # VWAP and extensions
    df['vwap'] = calculate_vwap(df)
    df['vwap_zscore'] = calculate_vwap_zscore(df, df['vwap'])

    # Volume analysis
    volume_pcts = calculate_volume_percentiles(df)
    df['volume_mean'] = volume_pcts['mean']
    df['volume_95th'] = volume_pcts['95th']
    df['volume_99th'] = volume_pcts['99th']
    df['rvol'] = calculate_relative_volume(df)

    # Price patterns
    df['price_velocity'] = calculate_price_velocity(df)
    df['blowoff_candle'] = detect_blowoff_candle(df)
    df['first_red_candle'] = detect_first_red_candle(df)

    # Composite signals
    df['volume_climax'] = detect_volume_climax(df, volume_pcts, '99th')
    df['parabolic'] = detect_parabolic_move(
        df,
        df['vwap_zscore'],
        df['price_velocity'],
        df['volume_climax']
    )

    return df


if __name__ == '__main__':
    print("""
    Intraday Indicators Module
    ==========================

    Usage example:

    from data.alpaca_data_loader import AlpacaDataLoader
    from indicators.intraday_indicators import calculate_all_indicators

    # Load 1-minute data
    loader = AlpacaDataLoader(api_key='...', secret_key='...')
    bars = loader.get_1min_bars('TSLA', '2024-01-15', '2024-01-15')

    # Calculate all indicators
    df = calculate_all_indicators(bars)

    # Check for parabolic setup
    parabolic_times = df[df['parabolic']]['timestamp']
    print(f"Parabolic signals at: {parabolic_times}")
    """)
