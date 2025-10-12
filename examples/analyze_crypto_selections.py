"""
Analyze which cryptos were selected by the winning strategy

Shows:
1. Current top 5 selections (if we rebalance today)
2. Historical selections over the backtest period
3. Most frequently selected cryptos
4. Performance of selected vs non-selected
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# Configuration
START_DATE = '2019-01-01'
END_DATE = '2025-01-01'

CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'LTC-USD', 'LINK-USD',
    'DOT-USD', 'UNI-USD', 'DOGE-USD', 'MATIC-USD', 'AAVE-USD', 'MKR-USD',
    'ATOM-USD', 'ETC-USD', 'XLM-USD', 'VET-USD', 'FIL-USD', 'USDT-USD'
]

print("📊 Downloading crypto data...")
data = yf.download(CRYPTO_UNIVERSE, start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
prices = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
prices.columns = [col.replace('-USD', '') for col in prices.columns]
prices = prices.dropna(thresh=len(prices) * 0.5, axis=1).ffill().dropna()

print(f"✅ Got {len(prices.columns)} cryptos\n")

# Calculate indicators (30-day ROC, 50-day MA)
roc_period = 30
ma_period = 50

roc = prices.pct_change(roc_period) * 100
ma = prices.rolling(window=ma_period).mean()
above_ma = prices > ma

# Generate monthly rebalance dates
rebalance_dates = pd.date_range(
    start=prices.index[0],
    end=prices.index[-1],
    freq='MS'  # Monthly start
)

# Find actual trading dates close to rebalance dates
actual_rebalance_dates = []
for target_date in rebalance_dates:
    idx = prices.index.searchsorted(target_date)
    if idx < len(prices.index):
        actual_rebalance_dates.append(prices.index[idx])

# Skip early dates without enough data
min_date = prices.index[0] + pd.Timedelta(days=max(roc_period, ma_period))
actual_rebalance_dates = [d for d in actual_rebalance_dates if d >= min_date]

print(f"{'='*70}")
print(f"CRYPTO SELECTION ANALYSIS")
print(f"{'='*70}")
print(f"Strategy: Monthly ROC (30-day), Above 50-day MA")
print(f"Portfolio Size: Top 5 cryptos")
print(f"Rebalance Dates: {len(actual_rebalance_dates)} monthly rebalances")
print(f"Period: {actual_rebalance_dates[0].date()} to {actual_rebalance_dates[-1].date()}\n")

# Track selections
selection_history = []
selection_counts = {}

for date in actual_rebalance_dates:
    # Filter: Above MA
    valid_above_ma = above_ma.loc[date][above_ma.loc[date] == True].index
    valid_above_ma = [c for c in valid_above_ma if c != 'USDT']

    if len(valid_above_ma) == 0:
        continue

    # Get ROC for valid cryptos
    roc_valid = roc.loc[date][valid_above_ma].dropna()

    if len(roc_valid) == 0:
        continue

    # Rank by ROC
    ranked = roc_valid.sort_values(ascending=False).head(5)

    # Store selection
    for i, (crypto, roc_val) in enumerate(ranked.items(), 1):
        price = prices.loc[date, crypto]
        selection_history.append({
            'Date': date,
            'Rank': i,
            'Crypto': crypto,
            'ROC': roc_val,
            'Price': price
        })

        # Count selections
        if crypto not in selection_counts:
            selection_counts[crypto] = 0
        selection_counts[crypto] += 1

# Convert to DataFrame
selections_df = pd.DataFrame(selection_history)

print(f"{'='*70}")
print(f"MOST FREQUENTLY SELECTED CRYPTOS")
print(f"{'='*70}\n")

sorted_counts = sorted(selection_counts.items(), key=lambda x: x[1], reverse=True)
total_rebalances = len(actual_rebalance_dates)

print(f"{'Crypto':<10} {'Selections':<12} {'% of Time':<12} {'Avg Rank':<10}")
print(f"{'-'*50}")

for crypto, count in sorted_counts:
    pct = (count / total_rebalances) * 100

    # Calculate average rank when selected
    crypto_selections = selections_df[selections_df['Crypto'] == crypto]
    avg_rank = crypto_selections['Rank'].mean()

    print(f"{crypto:<10} {count:<12} {pct:<11.1f}% {avg_rank:<10.1f}")

print(f"\n{'='*70}")
print(f"LATEST SELECTION (Most Recent Rebalance)")
print(f"{'='*70}\n")

latest_date = actual_rebalance_dates[-1]
latest_selections = selections_df[selections_df['Date'] == latest_date].sort_values('Rank')

print(f"Date: {latest_date.date()}\n")
print(f"{'Rank':<6} {'Crypto':<10} {'30d ROC':<12} {'Price':<15} {'Current Price':<15}")
print(f"{'-'*70}")

for _, row in latest_selections.iterrows():
    current_price = prices.iloc[-1][row['Crypto']]
    gain = ((current_price / row['Price']) - 1) * 100

    print(f"#{row['Rank']:<5} {row['Crypto']:<10} {row['ROC']:>8.2f}% "
          f"${row['Price']:>12,.2f} ${current_price:>12,.2f} ({gain:+.1f}%)")

print(f"\n{'='*70}")
print(f"SELECTION TIMELINE (Last 12 Rebalances)")
print(f"{'='*70}\n")

recent_rebalances = actual_rebalance_dates[-12:]
for date in recent_rebalances:
    date_selections = selections_df[selections_df['Date'] == date].sort_values('Rank')
    cryptos = date_selections['Crypto'].tolist()

    print(f"{date.date()}: {', '.join(cryptos)}")

# Analyze performance by selection frequency
print(f"\n{'='*70}")
print(f"PERFORMANCE BY SELECTION FREQUENCY")
print(f"{'='*70}\n")

# Calculate performance since start of test
start_prices = prices.loc[actual_rebalance_dates[0]]
end_prices = prices.iloc[-1]
total_returns = ((end_prices / start_prices) - 1) * 100

print(f"{'Crypto':<10} {'Times Selected':<15} {'Total Return':<15} {'Status':<20}")
print(f"{'-'*70}")

for crypto in prices.columns:
    if crypto == 'USDT':
        continue

    times_selected = selection_counts.get(crypto, 0)
    total_return = total_returns[crypto]

    # Categorize
    if times_selected > 15:
        status = "⭐ FREQUENT PICK"
    elif times_selected > 5:
        status = "✅ REGULAR"
    elif times_selected > 0:
        status = "🔸 OCCASIONAL"
    else:
        status = "❌ NEVER SELECTED"

    print(f"{crypto:<10} {times_selected:<15} {total_return:>12.2f}% {status:<20}")

# Winners vs losers
print(f"\n{'='*70}")
print(f"KEY INSIGHTS")
print(f"{'='*70}\n")

frequent_picks = [c for c, count in sorted_counts[:5]]
never_picked = [c for c in prices.columns if c not in selection_counts and c != 'USDT']

print(f"🏆 TOP 5 MOST SELECTED:")
for i, crypto in enumerate(frequent_picks, 1):
    count = selection_counts[crypto]
    pct = (count / total_rebalances) * 100
    total_return = total_returns[crypto]
    print(f"   #{i}. {crypto:6s} - Selected {count:2d} times ({pct:4.1f}%) - Return: {total_return:>8.2f}%")

if len(never_picked) > 0:
    print(f"\n❌ NEVER SELECTED ({len(never_picked)} cryptos):")
    for crypto in never_picked[:5]:
        total_return = total_returns[crypto]
        print(f"   {crypto:6s} - Return: {total_return:>8.2f}%")

# Calculate average return of selected vs non-selected
selected_returns = [total_returns[c] for c in selection_counts.keys()]
non_selected_returns = [total_returns[c] for c in prices.columns
                        if c not in selection_counts and c != 'USDT']

if len(selected_returns) > 0:
    avg_selected = np.mean(selected_returns)
    print(f"\n📊 Avg return of SELECTED cryptos: {avg_selected:.2f}%")

if len(non_selected_returns) > 0:
    avg_non_selected = np.mean(non_selected_returns)
    print(f"📊 Avg return of NON-SELECTED cryptos: {avg_non_selected:.2f}%")

    if len(selected_returns) > 0:
        advantage = avg_selected - avg_non_selected
        print(f"\n💡 Selection advantage: +{advantage:.2f}% (strategy picked better cryptos!)")

print(f"\n{'='*70}\n")

# Save detailed history
output_file = Path(__file__).parent.parent / 'results' / 'crypto_selection_history.csv'
selections_df.to_csv(output_file, index=False)
print(f"✅ Full selection history saved to: {output_file}\n")
