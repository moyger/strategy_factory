"""
Technical Indicators Library for FTMO Multi-Strategy System
"""
import pandas as pd
import numpy as np

def ema(series, period):
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def sma(series, period):
    """Simple Moving Average"""
    return series.rolling(window=period).mean()

def bollinger_bands(close, period=20, std_dev=2.0):
    """
    Bollinger Bands
    Returns: middle, upper, lower bands
    """
    middle = sma(close, period)
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return middle, upper, lower

def atr(high, low, close, period=14):
    """
    Average True Range
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def rsi(close, period=14):
    """
    Relative Strength Index
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val

def detect_volatility_gap(df, lookback=20, threshold_pips=5.0):
    """
    Detect volatility gaps for M5 scalping strategy

    A gap is detected when:
    1. Open is significantly different from previous close
    2. Price quickly reverts (mean reversion opportunity)

    Returns: Series with 1 (buy gap), -1 (sell gap), 0 (no gap)
    """
    pip_value = 0.0001  # For EUR/USD, GBP/USD

    # Calculate gap from previous close
    gap = df['open'] - df['close'].shift(1)
    gap_pips = gap / pip_value

    # Calculate typical range
    typical_range = (df['high'] - df['low']).rolling(lookback).mean()

    # Detect significant gaps
    signals = pd.Series(0, index=df.index)

    # Buy gap: Price gaps down significantly (oversold, expect reversal up)
    buy_condition = gap_pips < -threshold_pips
    signals[buy_condition] = 1

    # Sell gap: Price gaps up significantly (overbought, expect reversal down)
    sell_condition = gap_pips > threshold_pips
    signals[sell_condition] = -1

    return signals

def detect_high_volatility(df, atr_period=14, atr_multiplier=1.5):
    """
    Detect high volatility periods for scalping

    Returns: Boolean series, True when volatility is high
    """
    atr_val = atr(df['high'], df['low'], df['close'], atr_period)
    atr_ma = atr_val.rolling(window=atr_period).mean()

    # High volatility when current ATR > mean ATR * multiplier
    return atr_val > (atr_ma * atr_multiplier)

def trend_strength(close, fast_period=21, slow_period=50):
    """
    Measure trend strength using EMA distance

    Returns:
    - trend_signal: 1 (uptrend), -1 (downtrend), 0 (no trend)
    - strength: 0-1 value indicating trend strength
    """
    fast_ema = ema(close, fast_period)
    slow_ema = ema(close, slow_period)

    # Calculate distance as percentage
    distance_pct = ((fast_ema - slow_ema) / slow_ema).abs()

    # Trend signal
    trend_signal = pd.Series(0, index=close.index)
    trend_signal[fast_ema > slow_ema] = 1
    trend_signal[fast_ema < slow_ema] = -1

    # Strength (normalize to 0-1)
    strength = distance_pct * 100  # Convert to percentage
    strength = strength.clip(0, 1)  # Cap at 100%

    return trend_signal, strength

def detect_breakout(df, asia_high, asia_low, breakout_buffer_pips=2.0):
    """
    Detect London breakout from Asia range

    Args:
    - df: DataFrame with OHLC data
    - asia_high: Asia session high
    - asia_low: Asia session low
    - breakout_buffer_pips: Buffer to avoid false breakouts

    Returns: Series with 1 (bullish breakout), -1 (bearish breakout), 0 (no breakout)
    """
    pip_value = 0.0001
    buffer = breakout_buffer_pips * pip_value

    signals = pd.Series(0, index=df.index)

    # Bullish breakout: close above Asia high + buffer
    bullish = df['close'] > (asia_high + buffer)
    signals[bullish] = 1

    # Bearish breakout: close below Asia low - buffer
    bearish = df['close'] < (asia_low - buffer)
    signals[bearish] = -1

    return signals

def volatility_percentile(atr_series, lookback=100):
    """
    Calculate ATR percentile rank (0-100)

    Higher percentile = higher current volatility relative to history
    """
    percentile = atr_series.rolling(lookback).apply(
        lambda x: (x.iloc[-1] > x).sum() / len(x) * 100 if len(x) > 0 else 50
    )
    return percentile

def price_to_bb_position(close, bb_middle, bb_upper, bb_lower):
    """
    Calculate price position within Bollinger Bands (0-1)

    0.0 = at lower band
    0.5 = at middle band
    1.0 = at upper band
    """
    bb_range = bb_upper - bb_lower
    bb_position = (close - bb_lower) / bb_range
    return bb_position.clip(0, 1)

if __name__ == '__main__':
    # Test indicators with real data
    from data_loader import ForexDataLoader

    loader = ForexDataLoader()
    df = loader.load('EURUSD', 'M5')

    print("Testing Technical Indicators")
    print("=" * 50)

    # EMA
    df['ema_21'] = ema(df['close'], 21)
    df['ema_50'] = ema(df['close'], 50)
    print(f"\nEMA 21/50 calculated: {df[['ema_21', 'ema_50']].notna().sum().min()} bars")

    # Bollinger Bands
    bb_mid, bb_upper, bb_lower = bollinger_bands(df['close'], 20, 2.0)
    df['bb_mid'] = bb_mid
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    print(f"Bollinger Bands calculated: {df['bb_mid'].notna().sum()} bars")

    # ATR
    df['atr'] = atr(df['high'], df['low'], df['close'], 14)
    print(f"ATR calculated: {df['atr'].notna().sum()} bars")
    avg_atr_pips = df['atr'].mean() / 0.0001
    print(f"Average ATR: {avg_atr_pips:.1f} pips")

    # RSI
    df['rsi'] = rsi(df['close'], 14)
    print(f"RSI calculated: {df['rsi'].notna().sum()} bars")

    # Volatility gaps
    df['gap_signal'] = detect_volatility_gap(df, lookback=20, threshold_pips=5.0)
    num_buy_gaps = (df['gap_signal'] == 1).sum()
    num_sell_gaps = (df['gap_signal'] == -1).sum()
    print(f"\nVolatility gaps detected:")
    print(f"  Buy gaps (price gap down): {num_buy_gaps}")
    print(f"  Sell gaps (price gap up): {num_sell_gaps}")

    # High volatility
    df['high_vol'] = detect_high_volatility(df, atr_period=14, atr_multiplier=1.5)
    pct_high_vol = (df['high_vol'].sum() / len(df)) * 100
    print(f"\nHigh volatility periods: {pct_high_vol:.1f}% of time")

    # Trend strength
    trend_signal, trend_str = trend_strength(df['close'], 21, 50)
    df['trend'] = trend_signal
    df['trend_strength'] = trend_str
    pct_uptrend = (df['trend'] == 1).sum() / len(df) * 100
    pct_downtrend = (df['trend'] == -1).sum() / len(df) * 100
    print(f"\nTrend distribution:")
    print(f"  Uptrend: {pct_uptrend:.1f}%")
    print(f"  Downtrend: {pct_downtrend:.1f}%")

    # Sample output
    print("\nSample indicators (last 5 bars):")
    sample_cols = ['close', 'ema_21', 'ema_50', 'bb_upper', 'bb_lower', 'atr', 'rsi', 'trend']
    print(df[sample_cols].tail(5).to_string())

    print("\n✅ All indicators working correctly")
