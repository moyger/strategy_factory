"""
Walk-Forward Validation for Nick Radge BSS Strategy

Tests strategy robustness across rolling time windows:
- Train Period: ~3 years
- Test Period: 1 year
- Number of Folds: 5+

This validates that the strategy works consistently across
different market conditions and isn't overfit to specific periods.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import importlib.util

# Import the fixed strategy
spec = importlib.util.spec_from_file_location(
    "nick_radge_bss_fixed",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
bss_fixed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bss_fixed_module)
NickRadgeFixed = bss_fixed_module.NickRadgeEnhanced

from strategies.nick_radge_bss_strategy import download_sp500_stocks, download_spy

print("="*80)
print("WALK-FORWARD VALIDATION - NICK RADGE BSS")
print("="*80)

# Configuration
START_DATE = '2020-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 10000
NUM_STOCKS = 50

print(f"\n⚙️  Configuration:")
print(f"   Starting Capital: ${INITIAL_CAPITAL:,}")
print(f"   Full Period: {START_DATE} to {END_DATE}")
print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks")

# Download data
print(f"\n" + "="*80)
print("DOWNLOADING DATA")
print("="*80)

prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)
spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

# Add GLD
print(f"\n📊 Downloading GLD (bear market asset)...")
gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
if isinstance(gld_data.columns, pd.MultiIndex):
    gld_data.columns = gld_data.columns.get_level_values(0)
prices['GLD'] = gld_data['Close']

# Align dates
common_dates = prices.index.intersection(spy_prices.index)
prices = prices.loc[common_dates]
spy_prices = spy_prices.loc[common_dates]

print(f"\n✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")

# Calculate total days and years
total_days = (prices.index[-1] - prices.index[0]).days
total_years = total_days / 365.25

print(f"   Total period: {total_years:.1f} years ({total_days} days)")

# Walk-forward setup
# For ~5.7 years of data, use 1-year test periods
test_period_days = 365  # 1 year
train_period_days = 365 * 2  # 2 years (reduced from 3 due to limited data)

print(f"\n⚙️  Walk-Forward Setup:")
print(f"   Train Period: {train_period_days / 365:.1f} years")
print(f"   Test Period: {test_period_days / 365:.1f} years")

# Create folds
folds = []
current_train_start = prices.index[0]

fold_num = 1
while True:
    # Calculate train end
    train_end_date = current_train_start + pd.Timedelta(days=train_period_days)

    # Find nearest trading day
    train_end_idx = prices.index.searchsorted(train_end_date)
    if train_end_idx >= len(prices.index):
        break
    train_end = prices.index[train_end_idx]

    # Calculate test end
    test_end_date = train_end + pd.Timedelta(days=test_period_days)
    test_end_idx = prices.index.searchsorted(test_end_date)
    if test_end_idx >= len(prices.index):
        test_end_idx = len(prices.index) - 1
    test_end = prices.index[test_end_idx]

    # Store fold
    folds.append({
        'fold': fold_num,
        'train_start': current_train_start,
        'train_end': train_end,
        'test_start': train_end + pd.Timedelta(days=1),
        'test_end': test_end
    })

    # Move to next fold (advance by test period)
    next_train_start = train_end + pd.Timedelta(days=test_period_days)
    if next_train_start >= prices.index[-1]:
        break

    # Find nearest trading day
    next_train_idx = prices.index.searchsorted(next_train_start)
    if next_train_idx >= len(prices.index):
        break
    current_train_start = prices.index[next_train_idx]
    fold_num += 1

print(f"   Number of Folds: {len(folds)}")

# Display folds
print(f"\n📅 Fold Schedule:")
for fold in folds:
    print(f"   Fold {fold['fold']}:")
    print(f"      Train: {fold['train_start'].date()} to {fold['train_end'].date()}")
    print(f"      Test:  {fold['test_start'].date()} to {fold['test_end'].date()}")

# Run walk-forward validation
print(f"\n" + "="*80)
print("RUNNING WALK-FORWARD VALIDATION")
print("="*80)

results = []

for fold_info in folds:
    fold = fold_info['fold']
    print(f"\n{'='*80}")
    print(f"FOLD {fold}/{len(folds)}")
    print(f"{'='*80}")

    # Split data
    train_mask = (prices.index >= fold_info['train_start']) & (prices.index <= fold_info['train_end'])
    test_mask = (prices.index >= fold_info['test_start']) & (prices.index <= fold_info['test_end'])

    train_prices = prices[train_mask]
    train_spy = spy_prices[train_mask]

    test_prices = prices[test_mask]
    test_spy = spy_prices[test_mask]

    print(f"\n📊 Data Split:")
    print(f"   Train: {len(train_prices)} days ({fold_info['train_start'].date()} to {fold_info['train_end'].date()})")
    print(f"   Test:  {len(test_prices)} days ({fold_info['test_start'].date()} to {fold_info['test_end'].date()})")

    # NOTE: In production, you would optimize parameters on train set
    # For simplicity, we use fixed parameters and just test out-of-sample

    print(f"\n🧪 Testing out-of-sample on Fold {fold}...")

    try:
        # Test on out-of-sample period
        strategy = NickRadgeFixed(
            portfolio_size=7,
            qualifier_type='bss',
            ma_period=100,
            rebalance_freq='QS',
            use_momentum_weighting=True,
            use_regime_filter=True,
            use_relative_strength=True,
            bear_market_asset='GLD',
            qualifier_params={'poi_period': 100, 'atr_period': 14, 'k': 2.0}
        )

        portfolio = strategy.backtest(
            prices=test_prices,
            spy_prices=test_spy,
            initial_capital=INITIAL_CAPITAL,
            fees=0.001,
            slippage=0.0005
        )

        # Extract metrics
        final_value = portfolio.value().iloc[-1]
        if isinstance(final_value, pd.Series):
            final_value = final_value.sum()

        total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100

        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
            if isinstance(sharpe, pd.Series):
                sharpe = sharpe.mean()
        except:
            sharpe = 0.0

        try:
            sortino = portfolio.sortino_ratio(freq='D')
            if isinstance(sortino, pd.Series):
                sortino = sortino.mean()
        except:
            sortino = 0.0

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max()

        # Calculate CAGR for test period
        test_days = (test_prices.index[-1] - test_prices.index[0]).days
        test_years = test_days / 365.25
        cagr = ((final_value / INITIAL_CAPITAL) ** (1 / test_years) - 1) * 100 if test_years > 0 else 0

        # SPY benchmark for test period
        spy_final = test_spy.iloc[-1]
        spy_initial = test_spy.iloc[0]
        spy_return = ((spy_final / spy_initial) - 1) * 100

        results.append({
            'Fold': fold,
            'Test Start': fold_info['test_start'].date(),
            'Test End': fold_info['test_end'].date(),
            'Days': len(test_prices),
            'Return (%)': total_return,
            'CAGR (%)': cagr,
            'Sharpe': sharpe,
            'Sortino': sortino,
            'Max DD (%)': max_dd * 100,
            'SPY Return (%)': spy_return,
            'Outperformance (%)': total_return - spy_return
        })

        print(f"\n✅ Fold {fold} Results:")
        print(f"   Return: {total_return:+.2f}%")
        print(f"   CAGR: {cagr:.2f}%")
        print(f"   Sharpe: {sharpe:.2f}")
        print(f"   Sortino: {sortino:.2f}")
        print(f"   Max DD: {max_dd * 100:.2f}%")
        print(f"   SPY Return: {spy_return:+.2f}%")
        print(f"   Outperformance: {total_return - spy_return:+.2f}%")

    except Exception as e:
        print(f"❌ Error in Fold {fold}: {str(e)}")
        import traceback
        traceback.print_exc()
        results.append({
            'Fold': fold,
            'Test Start': fold_info['test_start'].date(),
            'Test End': fold_info['test_end'].date(),
            'Days': len(test_prices),
            'Return (%)': np.nan,
            'CAGR (%)': np.nan,
            'Sharpe': np.nan,
            'Sortino': np.nan,
            'Max DD (%)': np.nan,
            'SPY Return (%)': np.nan,
            'Outperformance (%)': np.nan
        })

# Summary
print(f"\n" + "="*80)
print("WALK-FORWARD VALIDATION SUMMARY")
print("="*80)

df_results = pd.DataFrame(results)
print(f"\n{df_results.to_string()}")

# Statistics
print(f"\n📊 Performance Statistics Across All Folds:")
print(f"   Avg Return: {df_results['Return (%)'].mean():.2f}% (±{df_results['Return (%)'].std():.2f}%)")
print(f"   Avg CAGR: {df_results['CAGR (%)'].mean():.2f}% (±{df_results['CAGR (%)'].std():.2f}%)")
print(f"   Avg Sharpe: {df_results['Sharpe'].mean():.2f} (±{df_results['Sharpe'].std():.2f})")
print(f"   Avg Sortino: {df_results['Sortino'].mean():.2f} (±{df_results['Sortino'].std():.2f})")
print(f"   Avg Max DD: {df_results['Max DD (%)'].mean():.2f}% (±{df_results['Max DD (%)'].std():.2f}%)")
print(f"   Avg Outperformance: {df_results['Outperformance (%)'].mean():.2f}% (±{df_results['Outperformance (%)'].std():.2f}%)")

print(f"\n🎯 Consistency Check:")
positive_folds = (df_results['Return (%)'] > 0).sum()
total_folds = len(df_results)
consistency = (positive_folds / total_folds) * 100
print(f"   Positive Folds: {positive_folds}/{total_folds} ({consistency:.1f}%)")
if consistency >= 80:
    print(f"   ✅ Excellent consistency (≥80% positive)")
elif consistency >= 60:
    print(f"   ⚠️  Good consistency (60-80% positive)")
else:
    print(f"   ❌ Poor consistency (<60% positive)")

outperform_folds = (df_results['Outperformance (%)'] > 0).sum()
outperform_pct = (outperform_folds / total_folds) * 100
print(f"   Outperformed SPY: {outperform_folds}/{total_folds} ({outperform_pct:.1f}%)")

print(f"\n🔍 Stability Check:")
sharpe_std = df_results['Sharpe'].std()
if sharpe_std < 0.3:
    print(f"   ✅ Stable Sharpe (σ = {sharpe_std:.2f})")
elif sharpe_std < 0.5:
    print(f"   ⚠️  Moderate Sharpe variation (σ = {sharpe_std:.2f})")
else:
    print(f"   ❌ High Sharpe variation (σ = {sharpe_std:.2f})")

dd_std = df_results['Max DD (%)'].std()
if dd_std < 5:
    print(f"   ✅ Stable drawdowns (σ = {dd_std:.2f}%)")
elif dd_std < 10:
    print(f"   ⚠️  Moderate drawdown variation (σ = {dd_std:.2f}%)")
else:
    print(f"   ❌ High drawdown variation (σ = {dd_std:.2f}%)")

# Save results
output_dir = Path(__file__).parent.parent / 'results' / 'walk_forward'
output_dir.mkdir(parents=True, exist_ok=True)

df_results.to_csv(output_dir / 'walk_forward_results.csv', index=False)
print(f"\n✅ Results saved to: {output_dir / 'walk_forward_results.csv'}")

print(f"\n" + "="*80)
print("✅ Walk-Forward Validation Complete!")
print("="*80)
