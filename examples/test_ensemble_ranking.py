"""
Test Ensemble Ranking - Combine Multiple Qualifiers

Tests the composite qualifier that combines:
- BSS (Breakout Strength Score)
- ANM (ATR-Normalized Momentum)
- VEM (Volatility Expansion Momentum)
- TQS (Trend Quality Score)
- RAM (Risk-Adjusted Momentum)

Expected benefit: +0.2 Sharpe improvement through ensemble stability
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
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
print("ENSEMBLE RANKING TEST - COMPOSITE QUALIFIER")
print("="*80)

# Configuration
START_DATE = '2020-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
INITIAL_CAPITAL = 5000
NUM_STOCKS = 50

print(f"\n⚙️  Configuration:")
print(f"   Starting Capital: ${INITIAL_CAPITAL:,}")
print(f"   Period: {START_DATE} to {END_DATE}")
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

# Test configurations
qualifiers = ['bss', 'anm', 'vem', 'tqs', 'ram', 'composite']
results = {}

for qual in qualifiers:
    print(f"\n" + "="*80)
    print(f"TESTING: {qual.upper()}")
    print("="*80)

    try:
        # Set appropriate params for each qualifier
        if qual == 'bss':
            params = {'poi_period': 100, 'atr_period': 14, 'k': 2.0}
        elif qual in ['anm', 'vem', 'ram']:
            params = {'roc_period': 100, 'atr_period': 14}
        elif qual == 'tqs':
            params = {'ma_period': 100, 'atr_period': 14}
        elif qual == 'composite':
            params = {}  # Uses defaults for all sub-qualifiers
        else:
            params = {}

        strategy = NickRadgeFixed(
            portfolio_size=7,
            qualifier_type=qual,
            ma_period=100,
            rebalance_freq='QS',
            use_momentum_weighting=True,
            use_regime_filter=True,
            use_relative_strength=True,
            bear_market_asset='GLD',
            qualifier_params=params
        )

        portfolio = strategy.backtest(
            prices=prices,
            spy_prices=spy_prices,
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

        # Calculate CAGR
        days = (prices.index[-1] - prices.index[0]).days
        years = days / 365.25
        cagr = ((final_value / INITIAL_CAPITAL) ** (1 / years) - 1) * 100

        # Calculate Calmar
        calmar = cagr / (abs(max_dd) * 100) if max_dd != 0 else 0

        results[qual] = {
            'Final Value': final_value,
            'Total Return (%)': total_return,
            'CAGR (%)': cagr,
            'Sharpe': sharpe,
            'Sortino': sortino,
            'Max DD (%)': max_dd * 100,
            'Calmar': calmar
        }

        print(f"\n✅ {qual.upper()} Results:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   CAGR: {cagr:.2f}%")
        print(f"   Sharpe: {sharpe:.2f}")
        print(f"   Sortino: {sortino:.2f}")
        print(f"   Max DD: {max_dd * 100:.2f}%")
        print(f"   Calmar: {calmar:.2f}")

    except Exception as e:
        print(f"❌ Error testing {qual}: {str(e)}")
        results[qual] = None

# Summary comparison
print(f"\n" + "="*80)
print("ENSEMBLE RANKING COMPARISON")
print("="*80)

df_results = pd.DataFrame(results).T
df_results = df_results.dropna()
df_results = df_results.sort_values('Sharpe', ascending=False)

print(f"\n{df_results.to_string()}")

# Highlight best
print(f"\n" + "="*80)
print("WINNER")
print("="*80)

if len(df_results) > 0:
    best = df_results.iloc[0]
    best_name = df_results.index[0].upper()

    print(f"\n🏆 Best Qualifier: {best_name}")
    print(f"   Total Return: {best['Total Return (%)']:.2f}%")
    print(f"   CAGR: {best['CAGR (%)']:.2f}%")
    print(f"   Sharpe: {best['Sharpe']:.2f}")
    print(f"   Sortino: {best['Sortino']:.2f}")
    print(f"   Max DD: {best['Max DD (%)']:.2f}%")
    print(f"   Calmar: {best['Calmar']:.2f}")

    print(f"\n🎯 Professional Standards Check:")
    print(f"   Sharpe >= 1.6:  {'✅ PASS' if best['Sharpe'] >= 1.6 else '❌ FAIL'}")
    print(f"   Sortino >= 2.2: {'✅ PASS' if best['Sortino'] >= 2.2 else '❌ FAIL'}")
    print(f"   Max DD <= 22%:  {'✅ PASS' if best['Max DD (%)'] <= 22 else '❌ FAIL'}")
    print(f"   Calmar >= 1.2:  {'✅ PASS' if best['Calmar'] >= 1.2 else '❌ FAIL'}")

    # Compare to BSS
    if 'bss' in df_results.index:
        bss_sharpe = df_results.loc['bss', 'Sharpe']
        improvement = best['Sharpe'] - bss_sharpe
        print(f"\n📊 Improvement vs BSS:")
        print(f"   Sharpe improvement: {improvement:+.2f}")
        if improvement > 0:
            print(f"   ✅ Ensemble is better!")
        elif improvement == 0:
            print(f"   ⚠️  No improvement from ensemble")
        else:
            print(f"   ❌ BSS alone is better")

# Save results
output_dir = Path(__file__).parent.parent / 'results' / 'ensemble_ranking'
output_dir.mkdir(parents=True, exist_ok=True)

df_results.to_csv(output_dir / 'ensemble_comparison.csv')
print(f"\n✅ Results saved to: {output_dir / 'ensemble_comparison.csv'}")

print(f"\n" + "="*80)
print("✅ Ensemble Ranking Test Complete!")
print("="*80)
