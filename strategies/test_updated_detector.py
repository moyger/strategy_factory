"""Test with updated Pattern Detector defaults"""
import sys
sys.path.insert(0, '.')

from core.data_loader import ForexDataLoader
from strategies.pattern_detector import PatternDetector

# Load Q1 2024
loader = ForexDataLoader()
h1_df = loader.load('EURUSD', 'H1')
h1_df = h1_df['2024-01-01':'2024-12-31']  # Full 2024

print(f"Testing 2024: {len(h1_df)} bars\n")

# Use updated defaults
detector = PatternDetector()  # Uses new defaults: R²=0.7, slope_tol=0.0001
print(f"Parameters: lookback={detector.lookback}, R²={detector.r_squared_min}, slope_tol={detector.slope_tolerance}\n")

# Find pivots
h1_df = detector.find_pivot_points(h1_df)
print(f"Pivot highs: {h1_df['pivot_high'].sum()}")
print(f"Pivot lows: {h1_df['pivot_low'].sum()}\n")

# Scan for patterns
print("Scanning for patterns...")
total_patterns = 0
pattern_types = {'ascending': 0, 'descending': 0, 'symmetrical': 0, 'flag': 0, 'pennant': 0}
sample_patterns = []

# Check every 20th bar
for idx in range(detector.lookback, len(h1_df), 20):
    patterns = detector.detect_all_patterns(h1_df, idx)
    if patterns:
        total_patterns += len(patterns)
        for pattern in patterns:
            pattern_types[pattern['type']] += 1
            if len(sample_patterns) < 5:  # Keep first 5 samples
                sample_patterns.append((h1_df.index[idx], pattern))

print(f"Total patterns found: {total_patterns}")
for ptype, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True):
    if count > 0:
        print(f"  {ptype}: {count}")

if sample_patterns:
    print(f"\nSample patterns (first {len(sample_patterns)}):")
    for i, (time, pattern) in enumerate(sample_patterns, 1):
        print(f"\n{i}. {time.strftime('%Y-%m-%d %H:%M')} - {pattern['type'].upper()}")
        print(f"   Resistance: ${pattern['resistance']['price']:.5f} (R²={pattern['resistance']['r2']:.3f})")
        print(f"   Support: ${pattern['support']['price']:.5f} (R²={pattern['support']['r2']:.3f})")
        print(f"   Pivots: {len(pattern['pivot_highs'])} highs, {len(pattern['pivot_lows'])} lows")
else:
    print("\n❌ Still no patterns found")
    print("Consider:")
    print("  - R² may still be too strict (try 0.5)")
    print("  - Lookback may need to be longer (try 60-100)")
    print("  - Slope ratios for symmetrical may be off")
