"""
Debug: Track how many times triangle patterns are detected vs traded
"""

import pandas as pd
import numpy as np
from strategies.pattern_detector import PatternDetector
from core.indicators import ema, atr

# Load data
df_h1 = pd.read_csv('data/forex/XAUUSD/XAUUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h4 = pd.read_csv('data/forex/XAUUSD/XAUUSD_4H.csv', parse_dates=['Datetime'], index_col='Datetime')

df_h1 = df_h1[df_h1.index >= '2024-01-01']
df_h4 = df_h4[df_h4.index >= '2024-01-01']

# Calculate H4 indicators
df_h4['ema_21'] = ema(df_h4['close'], 21)
df_h4['ema_50'] = ema(df_h4['close'], 50)
df_h4['atr'] = atr(df_h4['high'], df_h4['low'], df_h4['close'], 14)
df_h4['trend'] = 0
df_h4.loc[df_h4['ema_21'] > df_h4['ema_50'], 'trend'] = 1
df_h4.loc[df_h4['ema_21'] < df_h4['ema_50'], 'trend'] = -1

print("Analyzing Triangle Pattern Detection on XAUUSD (2024-2025)")
print("="*70)

# Initialize pattern detector with EXTREMELY relaxed params
detector = PatternDetector(
    lookback=60,
    min_pivot_points=3,
    r_squared_min=0.3,  # Very low R² requirement
    slope_tolerance=10.0  # Very high tolerance
)

triangle_time_start = 3
triangle_time_end = 9
triangle_buffer_pct = 0.0015

patterns_detected = 0
patterns_with_breakout = 0
patterns_with_trend_aligned = 0
patterns_traded = 0

# Check all London session times
london_times = df_h1[(df_h1.index.hour >= triangle_time_start) &
                      (df_h1.index.hour < triangle_time_end)]

print(f"\nTotal London session candles to check: {len(london_times)}")

pivot_highs_found = []
pivot_lows_found = []

for i, (current_time, row) in enumerate(london_times.iterrows()):
    if i % 500 == 0:
        print(f"  Checking {i}/{len(london_times)}...")

    # Get recent data
    recent_data = df_h1[df_h1.index <= current_time].tail(60)
    if len(recent_data) < 60:
        continue

    # IMPORTANT: Need to add pivot points to dataframe first!
    recent_data = detector.find_pivot_points(recent_data)

    # Track pivot counts
    pivot_highs_found.append(recent_data['pivot_high'].sum())
    pivot_lows_found.append(recent_data['pivot_low'].sum())

    # Detect triangle
    pattern = detector.detect_triangle(recent_data)

    if pattern is not None:
        patterns_detected += 1

        resistance = pattern['resistance']['price']
        support = pattern['support']['price']
        current_price = row['close']

        breakout_buffer = (resistance - support) * triangle_buffer_pct

        # Check for breakout
        has_breakout = False
        if current_price > resistance + breakout_buffer:
            has_breakout = True
            direction = 1
        elif current_price < support - breakout_buffer:
            has_breakout = True
            direction = -1

        if has_breakout:
            patterns_with_breakout += 1

            # Check trend alignment
            h4_bar = df_h4[df_h4.index <= current_time].iloc[-1]
            trend = h4_bar['trend']

            trend_aligned = False
            if direction == 1 and trend >= 0:
                trend_aligned = True
            elif direction == -1 and trend <= 0:
                trend_aligned = True

            if trend_aligned:
                patterns_with_trend_aligned += 1
                patterns_traded += 1
                print(f"\n  ✅ TRADE SIGNAL: {current_time}")
                print(f"     Pattern R² (resistance): {pattern['resistance']['r2']:.3f}")
                print(f"     Direction: {'LONG' if direction == 1 else 'SHORT'}")
                print(f"     Price: {current_price:.2f}")
                print(f"     Resistance: {resistance:.2f}, Support: {support:.2f}")
                print(f"     Trend: {trend}")

print(f"\n{'='*70}")
print("PIVOT POINT STATISTICS:")
if len(pivot_highs_found) > 0:
    print(f"  Avg pivot highs per window: {np.mean(pivot_highs_found):.1f}")
    print(f"  Avg pivot lows per window: {np.mean(pivot_lows_found):.1f}")
    print(f"  Windows with 3+ highs: {sum(1 for x in pivot_highs_found if x >= 3)}")
    print(f"  Windows with 3+ lows: {sum(1 for x in pivot_lows_found if x >= 3)}")
    print(f"  Windows with both 3+ highs AND 3+ lows: {sum(1 for h, l in zip(pivot_highs_found, pivot_lows_found) if h >= 3 and l >= 3)}")

print(f"\n{'='*70}")
print("PATTERN RESULTS:")
print(f"  Patterns detected: {patterns_detected}")
print(f"  Patterns with breakout: {patterns_with_breakout}")
print(f"  Patterns with trend aligned: {patterns_with_trend_aligned}")
print(f"  Patterns traded: {patterns_traded}")

if patterns_detected > 0:
    print(f"\n  Detection → Breakout: {patterns_with_breakout/patterns_detected*100:.1f}%")
    if patterns_with_breakout > 0:
        print(f"  Breakout → Trend Aligned: {patterns_with_trend_aligned/patterns_with_breakout*100:.1f}%")

print("\nNOTE: This checks EVERY candle. The actual strategy only checks when")
print("      no position is open, so duplicate signals are filtered out.")
