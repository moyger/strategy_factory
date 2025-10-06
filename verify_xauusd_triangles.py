"""
Verify if any triangle trades occurred but weren't logged properly
"""

import pandas as pd
from strategies.strategy_breakout_v4_1_xauusd import LondonBreakoutV41XAUUSD

# Load data
df_h1 = pd.read_csv('data/forex/XAUUSD/XAUUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h4 = pd.read_csv('data/forex/XAUUSD/XAUUSD_4H.csv', parse_dates=['Datetime'], index_col='Datetime')

# Use full dataset
df_h1 = df_h1[df_h1.index >= '2022-01-01']
df_h4 = df_h4[df_h4.index >= '2022-01-01']

print("Running full backtest with detailed trade type tracking...")
print("="*70)

strategy = LondonBreakoutV41XAUUSD(
    pair='XAUUSD',
    risk_percent=1.5,
    initial_capital=100000,
    enable_asia_breakout=True,
    enable_triangle_breakout=True
)

trades, equity = strategy.run(df_h1.copy(), df_h4.copy())

print(f"\nTotal Trades: {len(trades)}")

# Count by type
trade_types = trades['type'].value_counts()
print(f"\nBreakdown by Type:")
for trade_type, count in trade_types.items():
    print(f"  {trade_type}: {count} trades ({count/len(trades)*100:.1f}%)")

# Show all unique trade types
print(f"\nAll unique trade types found:")
print(trades['type'].unique())

# Show sample trades
print(f"\n{'='*70}")
print("Sample of first 10 trades:")
print(trades[['entry_time', 'type', 'direction', 'pips', 'pnl']].head(10))

print(f"\n{'='*70}")
print("Sample of last 10 trades:")
print(trades[['entry_time', 'type', 'direction', 'pips', 'pnl']].tail(10))
