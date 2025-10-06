"""
Debug why triangle patterns aren't triggering on XAUUSD
"""

import pandas as pd
import numpy as np
from strategies.pattern_detector import PatternDetector

# Load XAUUSD data
df_h1 = pd.read_csv('data/forex/XAUUSD/XAUUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h1 = df_h1[df_h1.index >= '2024-01-01']

print("Testing Triangle Detection on XAUUSD")
print("="*70)

# Test different slope tolerances
slope_tolerances = [0.1, 0.5, 0.75, 1.0, 2.0, 5.0]

for slope_tol in slope_tolerances:
    print(f"\nSlope Tolerance: {slope_tol}")

    detector = PatternDetector(
        lookback=60,
        min_pivot_points=3,
        r_squared_min=0.5,
        slope_tolerance=slope_tol
    )

    patterns_found = 0

    # Sample 100 random times during London session
    london_hours = df_h1[(df_h1.index.hour >= 3) & (df_h1.index.hour < 9)]

    if len(london_hours) > 100:
        sample_times = london_hours.sample(100, random_state=42).index
    else:
        sample_times = london_hours.index

    for current_time in sample_times:
        recent_data = df_h1[df_h1.index <= current_time].tail(60)

        if len(recent_data) == 60:
            pattern = detector.detect_triangle(recent_data)
            if pattern is not None:
                patterns_found += 1

    print(f"  Patterns found in {len(sample_times)} samples: {patterns_found}")
    if patterns_found > 0:
        print(f"  Detection rate: {patterns_found/len(sample_times)*100:.1f}%")

print("\n" + "="*70)
print("\nNow checking a specific example in detail...")

# Get a random London session time
sample_time = df_h1[(df_h1.index >= '2024-03-15') &
                     (df_h1.index.hour >= 3) &
                     (df_h1.index.hour < 9)].index[10]

recent_data = df_h1[df_h1.index <= sample_time].tail(60)

print(f"\nSample time: {sample_time}")
print(f"Price range: {recent_data['low'].min():.2f} - {recent_data['high'].max():.2f}")
print(f"Price range in points: {(recent_data['high'].max() - recent_data['low'].min()) / 0.1:.0f}")

# Try with very relaxed tolerance
detector_relaxed = PatternDetector(
    lookback=60,
    min_pivot_points=3,
    r_squared_min=0.5,
    slope_tolerance=5.0
)

pattern = detector_relaxed.detect_triangle(recent_data)

if pattern:
    print(f"\n✅ Pattern detected with slope_tolerance=5.0!")
    print(f"  Type: {pattern.get('pattern_type', 'N/A')}")
    print(f"  R²: {pattern['r_squared']:.3f}")
    print(f"  Resistance: {pattern['resistance']:.2f}")
    print(f"  Support: {pattern['support']:.2f}")
    print(f"  Resistance slope: {pattern['resistance_line'][0]:.4f}")
    print(f"  Support slope: {pattern['support_line'][0]:.4f}")
else:
    print(f"\n❌ No pattern detected even with slope_tolerance=5.0")
    print("\nTrying to understand why...")

    # Check pivot points
    df_pivots = detector_relaxed.find_pivot_points(recent_data)
    pivot_highs = df_pivots[df_pivots['pivot_high']].index
    pivot_lows = df_pivots[df_pivots['pivot_low']].index

    print(f"\nPivot Highs found: {len(pivot_highs)}")
    print(f"Pivot Lows found: {len(pivot_lows)}")

    if len(pivot_highs) >= 3:
        print(f"\nSample Pivot Highs:")
        for i, idx in enumerate(pivot_highs[:5]):
            print(f"  {idx}: {df_pivots.loc[idx, 'high']:.2f}")

    if len(pivot_lows) >= 3:
        print(f"\nSample Pivot Lows:")
        for i, idx in enumerate(pivot_lows[:5]):
            print(f"  {idx}: {df_pivots.loc[idx, 'low']:.2f}")

    # Calculate actual slopes
    print(f"\n{'='*70}")
    print("Calculating trendline slopes manually...")

    if len(pivot_highs) >= 3:
        # Get indices and prices
        indices = list(range(len(pivot_highs)))
        prices = [df_pivots.loc[idx, 'high'] for idx in pivot_highs]

        # Linear regression
        A = np.vstack([indices, np.ones(len(indices))]).T
        slope, intercept = np.linalg.lstsq(A, prices, rcond=None)[0]

        print(f"\nResistance Line (from {len(pivot_highs)} pivot highs):")
        print(f"  Slope: {slope:.6f}")
        print(f"  Price change over 60 bars: {slope * 60:.2f}")
        print(f"  Abs slope vs tolerance: {abs(slope):.6f} vs {5.0}")

    if len(pivot_lows) >= 3:
        indices = list(range(len(pivot_lows)))
        prices = [df_pivots.loc[idx, 'low'] for idx in pivot_lows]

        A = np.vstack([indices, np.ones(len(indices))]).T
        slope, intercept = np.linalg.lstsq(A, prices, rcond=None)[0]

        print(f"\nSupport Line (from {len(pivot_lows)} pivot lows):")
        print(f"  Slope: {slope:.6f}")
        print(f"  Price change over 60 bars: {slope * 60:.2f}")
        print(f"  Abs slope vs tolerance: {abs(slope):.6f} vs {5.0}")
