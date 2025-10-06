"""
Analyze XAUUSD Asia session ranges to calibrate parameters
"""

import pandas as pd
import numpy as np

# Load data
df_h1 = pd.read_csv('data/forex/XAUUSD/XAUUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h1 = df_h1[df_h1.index >= '2022-01-01']

print("Analyzing XAUUSD Asia Session Ranges (2022-2025)")
print("="*70)

# Analyze Asia sessions
asia_ranges = []

for date in df_h1.index.date:
    if pd.Timestamp(date) in df_h1.index:
        # Get Asia session data (00:00-03:00 GMT)
        asia_data = df_h1[
            (df_h1.index.date == date) &
            (df_h1.index.hour >= 0) &
            (df_h1.index.hour < 3)
        ]

        if len(asia_data) >= 2:
            high = asia_data['high'].max()
            low = asia_data['low'].min()
            range_points = (high - low) / 0.1  # Convert to points

            asia_ranges.append({
                'date': date,
                'range_points': range_points
            })

df_ranges = pd.DataFrame(asia_ranges)

if len(df_ranges) > 0:
    print(f"\nTotal Asia sessions analyzed: {len(df_ranges)}")
    print(f"\nRange Statistics (in points):")
    print(f"  Min:  {df_ranges['range_points'].min():.0f}")
    print(f"  25%:  {df_ranges['range_points'].quantile(0.25):.0f}")
    print(f"  50%:  {df_ranges['range_points'].median():.0f}")
    print(f"  75%:  {df_ranges['range_points'].quantile(0.75):.0f}")
    print(f"  Max:  {df_ranges['range_points'].max():.0f}")
    print(f"  Mean: {df_ranges['range_points'].mean():.0f}")

    # Current parameters
    print(f"\n{'='*70}")
    print("Current Strategy Parameters:")
    print(f"  Min Asia Range: 150 points")
    print(f"  Max Asia Range: 600 points")

    # Check how many sessions qualify
    qualified = df_ranges[
        (df_ranges['range_points'] >= 150) &
        (df_ranges['range_points'] <= 600)
    ]

    print(f"\nQualified Sessions: {len(qualified)} / {len(df_ranges)} ({len(qualified)/len(df_ranges)*100:.1f}%)")

    # Recommended parameters
    print(f"\n{'='*70}")
    print("Recommended Parameters for XAUUSD:")

    # Use 25th to 75th percentile as range
    rec_min = df_ranges['range_points'].quantile(0.15)
    rec_max = df_ranges['range_points'].quantile(0.85)

    print(f"  Min Asia Range: {rec_min:.0f} points (15th percentile)")
    print(f"  Max Asia Range: {rec_max:.0f} points (85th percentile)")

    new_qualified = df_ranges[
        (df_ranges['range_points'] >= rec_min) &
        (df_ranges['range_points'] <= rec_max)
    ]
    print(f"  Would qualify: {len(new_qualified)} / {len(df_ranges)} ({len(new_qualified)/len(df_ranges)*100:.1f}%)")

    # Analyze typical movements
    print(f"\n{'='*70}")
    print("Typical first hour movements:")

    first_hour_moves = []
    for date in df_h1.index.date:
        first_hour = df_h1[
            (df_h1.index.date == date) &
            (df_h1.index.hour == 3)
        ]

        if len(first_hour) > 0:
            candle = first_hour.iloc[0]
            move = abs(candle['close'] - candle['open']) / 0.1
            first_hour_moves.append(move)

    if len(first_hour_moves) > 0:
        df_moves = pd.Series(first_hour_moves)
        print(f"  Min:  {df_moves.min():.0f} points")
        print(f"  25%:  {df_moves.quantile(0.25):.0f} points")
        print(f"  50%:  {df_moves.median():.0f} points")
        print(f"  75%:  {df_moves.quantile(0.75):.0f} points")
        print(f"  Mean: {df_moves.mean():.0f} points")

        print(f"\n  Current requirement: 180 points")
        print(f"  Recommended: {df_moves.quantile(0.50):.0f} points (median)")
