"""
Detailed debug - check what's failing in pattern detection
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import ForexDataLoader
from strategies.pattern_detector import PatternDetector

# Load small sample
loader = ForexDataLoader()
h1_df = loader.load('EURUSD', 'H1')
h1_df = h1_df['2024-01-01':'2024-03-31']  # Q1 2024 only

print(f"Analyzing Q1 2024: {len(h1_df)} bars\n")

# Very relaxed detector
detector = PatternDetector(
    lookback=50,
    min_pivot_points=3,
    r_squared_min=0.5,  # VERY relaxed
    slope_tolerance=0.001  # VERY relaxed
)

# Find pivots
h1_df = detector.find_pivot_points(h1_df)
print(f"Pivot highs: {h1_df['pivot_high'].sum()}")
print(f"Pivot lows: {h1_df['pivot_low'].sum()}\n")

# Manually test pattern detection at a specific point
test_index = len(h1_df) - 100  # 100 bars from end

print(f"Testing pattern detection at index {test_index}")
print(f"Time: {h1_df.index[test_index]}\n")

# Get lookback window
start_idx = max(0, test_index - detector.lookback)
end_idx = test_index
window_df = h1_df.iloc[start_idx:end_idx+1]

print(f"Window: {start_idx} to {end_idx} ({len(window_df)} bars)")

# Get pivot points in window
pivot_highs = []
pivot_lows = []

for i, (idx, row) in enumerate(window_df.iterrows()):
    actual_index = start_idx + i
    if row.get('pivot_high', False):
        pivot_highs.append((actual_index, row['high']))
    if row.get('pivot_low', False):
        pivot_lows.append((actual_index, row['low']))

print(f"Pivot highs in window: {len(pivot_highs)}")
print(f"Pivot lows in window: {len(pivot_lows)}\n")

if len(pivot_highs) >= 3 and len(pivot_lows) >= 3:
    print("✅ Enough pivots for pattern\n")

    # Calculate trendlines
    upper_slope, upper_intercept, upper_r2 = detector.calculate_trendline(pivot_highs)
    lower_slope, lower_intercept, lower_r2 = detector.calculate_trendline(pivot_lows)

    print(f"Upper trendline:")
    print(f"  Slope: {upper_slope:.10f}")
    print(f"  Intercept: {upper_intercept:.5f}")
    print(f"  R²: {upper_r2:.4f}")
    print(f"  {'✅' if upper_r2 >= detector.r_squared_min else '❌'} Passes R² threshold ({detector.r_squared_min})\n")

    print(f"Lower trendline:")
    print(f"  Slope: {lower_slope:.10f}")
    print(f"  Intercept: {lower_intercept:.5f}")
    print(f"  R²: {lower_r2:.4f}")
    print(f"  {'✅' if lower_r2 >= detector.r_squared_min else '❌'} Passes R² threshold ({detector.r_squared_min})\n")

    # Check pattern classification
    print("Pattern classification checks:")
    print(f"  Ascending? |upper_slope| <= {detector.slope_tolerance} AND lower_slope > {detector.slope_tolerance}")
    print(f"    |{upper_slope:.10f}| <= {detector.slope_tolerance}? {abs(upper_slope) <= detector.slope_tolerance}")
    print(f"    {lower_slope:.10f} > {detector.slope_tolerance}? {lower_slope > detector.slope_tolerance}")
    print(f"    Result: {'✅ ASCENDING' if (abs(upper_slope) <= detector.slope_tolerance and lower_slope > detector.slope_tolerance) else '❌ NOT ascending'}\n")

    print(f"  Descending? |lower_slope| <= {detector.slope_tolerance} AND upper_slope < -{detector.slope_tolerance}")
    print(f"    |{lower_slope:.10f}| <= {detector.slope_tolerance}? {abs(lower_slope) <= detector.slope_tolerance}")
    print(f"    {upper_slope:.10f} < -{detector.slope_tolerance}? {upper_slope < -detector.slope_tolerance}")
    print(f"    Result: {'✅ DESCENDING' if (abs(lower_slope) <= detector.slope_tolerance and upper_slope < -detector.slope_tolerance) else '❌ NOT descending'}\n")

    print(f"  Symmetrical? upper_slope < 0 AND lower_slope > 0 AND 0.5 <= |ratio| <= 2.0")
    slope_ratio = abs(upper_slope / lower_slope) if lower_slope != 0 else 0
    print(f"    {upper_slope:.10f} < 0? {upper_slope < 0}")
    print(f"    {lower_slope:.10f} > 0? {lower_slope > 0}")
    print(f"    Slope ratio: {slope_ratio:.4f}")
    print(f"    Ratio in range? {0.5 <= slope_ratio <= 2.0}")
    symmetrical = upper_slope < 0 and lower_slope > 0 and 0.5 <= slope_ratio <= 2.0
    print(f"    Result: {'✅ SYMMETRICAL' if symmetrical else '❌ NOT symmetrical'}\n")

else:
    print(f"❌ Not enough pivots (need 3+, have {len(pivot_highs)} highs, {len(pivot_lows)} lows)")

# Now test actual detection
print("\n" + "=" * 80)
print("Actual pattern detection result:")
pattern = detector.detect_triangle(h1_df, test_index)
if pattern:
    print(f"✅ Pattern detected: {pattern['type']}")
else:
    print("❌ No pattern detected")

print("\n" + "=" * 80)
print("Scanning all of Q1 2024 for ANY patterns...")
total_patterns = 0
pattern_types = {'ascending': 0, 'descending': 0, 'symmetrical': 0}

# Check every 10th bar
for idx in range(50, len(h1_df), 10):
    pattern = detector.detect_triangle(h1_df, idx)
    if pattern:
        total_patterns += 1
        pattern_types[pattern['type']] += 1

print(f"Total patterns found: {total_patterns}")
for ptype, count in pattern_types.items():
    if count > 0:
        print(f"  {ptype}: {count}")

if total_patterns == 0:
    print("\n❌ NO PATTERNS FOUND - Parameters may be too strict even with relaxed settings")
    print("\nSuggestions:")
    print("  1. Lower R² requirement further (try 0.3-0.5)")
    print("  2. Increase slope tolerance (try 0.01)")
    print("  3. Reduce min_pivot_points to 2")
    print("  4. Increase lookback window to 100+ bars")
