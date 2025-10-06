"""
Debug script to understand why triangle patterns aren't generating trades
"""
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import ForexDataLoader
from core.session_manager import TradingSession
from core.indicators import ema, atr
from strategies.pattern_detector import PatternDetector

print("=" * 80)
print("TRIANGLE PATTERN DETECTION DEBUG")
print("=" * 80)

# Load data
loader = ForexDataLoader()
h1_df = loader.load('EURUSD', 'H1')
h4_df = loader.load('EURUSD', 'H4')

# Filter to 2024 only for faster analysis
h1_df = h1_df[h1_df.index >= '2024-01-01']
h4_df = h4_df[h4_df.index >= '2024-01-01']

print(f"\nAnalyzing period: {h1_df.index.min()} to {h1_df.index.max()}")
print(f"H1 bars: {len(h1_df):,}\n")

# Calculate indicators
h1_df['ema_21'] = ema(h1_df['close'], 21)
h1_df['ema_50'] = ema(h1_df['close'], 50)
h1_df['atr'] = atr(h1_df['high'], h1_df['low'], h1_df['close'], 14)

# Initialize pattern detector
detector = PatternDetector(
    lookback=25,
    min_pivot_points=3,
    r_squared_min=0.9,
    slope_tolerance=0.00001
)

print("Finding pivot points...")
h1_df = detector.find_pivot_points(h1_df, left=3, right=3)
pivot_high_count = h1_df['pivot_high'].sum()
pivot_low_count = h1_df['pivot_low'].sum()
print(f"  Total pivot highs: {pivot_high_count}")
print(f"  Total pivot lows: {pivot_low_count}\n")

# Sample every 100 bars during London session to check for patterns
print("Scanning for patterns during London hours (3-5 AM)...")
patterns_found = 0
breakouts_found = 0

london_bars = h1_df[
    (h1_df.index.hour >= 3) &
    (h1_df.index.hour <= 5) &
    (h1_df.index.dayofweek < 5)  # Weekdays only
]

print(f"  London session bars to analyze: {len(london_bars)}\n")

# Sample every 50th bar to avoid too much output
sample_indices = list(range(50, len(h1_df), 50))[:20]  # Check 20 samples

for i, sample_idx in enumerate(sample_indices, 1):
    if sample_idx >= len(h1_df):
        break

    current_time = h1_df.index[sample_idx]

    # Only check during London hours
    if not (3 <= current_time.hour <= 5 and current_time.dayofweek < 5):
        continue

    # Try to detect patterns
    patterns = detector.detect_all_patterns(h1_df, sample_idx)

    if len(patterns) > 0:
        patterns_found += 1
        pattern = patterns[0]

        print(f"Sample {i} @ {current_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Pattern found: {pattern['type'].upper()}")
        print(f"  Resistance: ${pattern['resistance']['price']:.5f} "
              f"(slope: {pattern['resistance']['slope']:.8f}, R²: {pattern['resistance']['r2']:.3f})")
        print(f"  Support: ${pattern['support']['price']:.5f} "
              f"(slope: {pattern['support']['slope']:.8f}, R²: {pattern['support']['r2']:.3f})")
        print(f"  Pivot points: {len(pattern['pivot_highs'])} highs, {len(pattern['pivot_lows'])} lows")

        # Check for breakout
        current_price = h1_df.iloc[sample_idx]['close']
        breakout = detector.check_breakout(pattern, current_price, buffer_pct=0.0015)

        if breakout:
            breakouts_found += 1
            print(f"  ✅ BREAKOUT DETECTED: {breakout.upper()}")
        else:
            print(f"  ⏸️  No breakout (price: ${current_price:.5f})")
        print()

# Summary
print("=" * 80)
print(f"SUMMARY:")
print(f"  Patterns detected in samples: {patterns_found}")
print(f"  Breakouts found: {breakouts_found}")
print("=" * 80)

# Check specific requirements
print("\nChecking strategy filter requirements:")
print(f"  Lookback window: {detector.lookback} bars (covers {detector.lookback} hours)")
print(f"  Min pivot points: {detector.min_pivot_points}")
print(f"  R² threshold: {detector.r_squared_min}")
print(f"  Slope tolerance: {detector.slope_tolerance}")
print(f"  Time filter: Only 3-5 AM London")
print(f"  Pattern buffer: 0.15% (~1.5 pips for EURUSD)")

# Test if parameters are too strict
print("\nTrying relaxed parameters...")
relaxed_detector = PatternDetector(
    lookback=40,  # Longer lookback
    min_pivot_points=3,
    r_squared_min=0.7,  # Lower R² requirement
    slope_tolerance=0.0001  # More forgiving slope
)

patterns = relaxed_detector.detect_all_patterns(h1_df, len(h1_df)-1)
print(f"  Patterns found with relaxed params at end of data: {len(patterns)}")
if len(patterns) > 0:
    for i, p in enumerate(patterns[:3], 1):
        print(f"    {i}. {p['type']} - R² upper:{p['resistance']['r2']:.3f}, lower:{p['support']['r2']:.3f}")

print("\n" + "=" * 80)
print("✅ Debug complete")
print("=" * 80)
