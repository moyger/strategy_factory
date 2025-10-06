"""
Prepare ADAUSD data: Create H4 timeframe from H1 data
"""

import pandas as pd

# Load H1 data
print("Loading ADAUSD H1 data...")
df_h1 = pd.read_csv('data/crypto/ADAUSD_1H.csv', parse_dates=['Date'])
df_h1.rename(columns={'Date': 'Datetime', 'Open': 'open', 'High': 'high',
                      'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
df_h1.set_index('Datetime', inplace=True)

print(f"H1 Data: {len(df_h1)} bars from {df_h1.index[0]} to {df_h1.index[-1]}")

# Resample to H4
print("Creating H4 timeframe...")
df_h4 = df_h1.resample('4H').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()

print(f"H4 Data: {len(df_h4)} bars from {df_h4.index[0]} to {df_h4.index[-1]}")

# Save both files
print("\nSaving files...")
df_h1.to_csv('data/crypto/ADAUSD_1H.csv')
df_h4.to_csv('data/crypto/ADAUSD_4H.csv')

print("✅ Data preparation complete!")
print(f"  - data/crypto/ADAUSD_1H.csv: {len(df_h1)} bars")
print(f"  - data/crypto/ADAUSD_4H.csv: {len(df_h4)} bars")
