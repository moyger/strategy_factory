"""
Compare BSS Strategy Performance BEFORE and AFTER Critical Fixes

Critical Fixes Applied:
1. Look-ahead bias elimination (lag all signals by 1 day)
2. Execution realism (decide at close, execute at next open)
3. Concentration limits (max 25% per position)
4. Volatility targeting (target 20% annual volatility)
5. Turnover tracking

Expected Impact:
- Lower returns (more realistic)
- Better risk-adjusted metrics (Sharpe, Sortino)
- Lower maximum drawdown
- More stable performance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf

# Import the FIXED strategy from 02_nick_radge_bss.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "nick_radge_bss_fixed",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
bss_fixed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bss_fixed_module)
NickRadgeFixed = bss_fixed_module.NickRadgeEnhanced

# Import the ORIGINAL strategy
from strategies.nick_radge_bss_strategy import NickRadgeBSS, download_sp500_stocks, download_spy

print("="*80)
print("BSS STRATEGY: BEFORE vs AFTER CRITICAL FIXES")
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

# =============================================================================
# TEST 1: ORIGINAL STRATEGY (WITHOUT FIXES)
# =============================================================================

print(f"\n" + "="*80)
print("TEST 1: ORIGINAL STRATEGY (WITHOUT FIXES)")
print("="*80)
print("\n⚠️  This version has:")
print("   - Look-ahead bias (uses same-day data for signals)")
print("   - Unrealistic execution (instant fills)")
print("   - No concentration limits")
print("   - No volatility targeting")

strategy_original = NickRadgeBSS(
    portfolio_size=7,
    poi_period=100,
    atr_period=14,
    atr_multiplier=2.0,
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    bear_market_asset='GLD'
)

portfolio_original = strategy_original.backtest(
    prices=prices,
    spy_prices=spy_prices,
    initial_capital=INITIAL_CAPITAL,
    fees=0.001,
    slippage=0.0005
)

# =============================================================================
# TEST 2: FIXED STRATEGY (WITH ALL IMPROVEMENTS)
# =============================================================================

print(f"\n" + "="*80)
print("TEST 2: FIXED STRATEGY (WITH ALL IMPROVEMENTS)")
print("="*80)
print("\n✅ This version has:")
print("   - No look-ahead bias (all signals lagged by 1 day)")
print("   - Realistic execution (decide at close, execute at open)")
print("   - Concentration limits (max 25% per position)")
print("   - Volatility targeting (20% annual)")
print("   - Turnover tracking")

strategy_fixed = NickRadgeFixed(
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

portfolio_fixed = strategy_fixed.backtest(
    prices=prices,
    spy_prices=spy_prices,
    initial_capital=INITIAL_CAPITAL,
    fees=0.001,
    slippage=0.0005
)

# =============================================================================
# COMPARISON
# =============================================================================

print(f"\n" + "="*80)
print("SIDE-BY-SIDE COMPARISON")
print("="*80)

def get_metrics(portfolio, init_cash):
    """Extract metrics from portfolio"""
    final_value = portfolio.value().iloc[-1]
    if isinstance(final_value, pd.Series):
        final_value = final_value.sum()

    total_return = ((final_value / init_cash) - 1) * 100

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

    trades_count = portfolio.trades.count()
    if isinstance(trades_count, pd.Series):
        trades_count = trades_count.sum()

    try:
        win_rate = portfolio.trades.win_rate()
        if isinstance(win_rate, pd.Series):
            win_rate = win_rate.mean()
    except:
        win_rate = 0.0

    try:
        profit_factor = portfolio.trades.profit_factor()
        if isinstance(profit_factor, pd.Series):
            profit_factor = profit_factor.mean()
    except:
        profit_factor = 0.0

    # Calculate CAGR
    days = (prices.index[-1] - prices.index[0]).days
    years = days / 365.25
    cagr = ((final_value / init_cash) ** (1 / years) - 1) * 100 if years > 0 else 0

    # Calculate Calmar Ratio
    calmar = cagr / (abs(max_dd) * 100) if max_dd != 0 else 0

    return {
        'Final Value': final_value,
        'Total Return (%)': total_return,
        'CAGR (%)': cagr,
        'Sharpe Ratio': sharpe,
        'Sortino Ratio': sortino,
        'Max Drawdown (%)': max_dd * 100,
        'Calmar Ratio': calmar,
        'Total Trades': trades_count,
        'Win Rate (%)': win_rate * 100,
        'Profit Factor': profit_factor
    }

metrics_original = get_metrics(portfolio_original, INITIAL_CAPITAL)
metrics_fixed = get_metrics(portfolio_fixed, INITIAL_CAPITAL)

# SPY metrics
spy_final = spy_prices.iloc[-1]
spy_initial = spy_prices.iloc[0]
spy_return = ((spy_final / spy_initial) - 1) * 100
days = (spy_prices.index[-1] - spy_prices.index[0]).days
years = days / 365.25
spy_cagr = ((spy_final / spy_initial) ** (1 / years) - 1) * 100

print(f"\n{'Metric':<25} {'Original':<20} {'Fixed':<20} {'Difference':<15}")
print("-" * 80)

for metric in metrics_original.keys():
    orig_val = metrics_original[metric]
    fixed_val = metrics_fixed[metric]
    diff = fixed_val - orig_val

    if 'Return' in metric or 'CAGR' in metric or 'Drawdown' in metric or 'Win Rate' in metric:
        print(f"{metric:<25} {orig_val:>18.2f}% {fixed_val:>18.2f}% {diff:>13.2f}%")
    elif 'Value' in metric:
        print(f"{metric:<25} ${orig_val:>17,.2f} ${fixed_val:>17,.2f} ${diff:>12,.2f}")
    elif 'Trades' in metric:
        print(f"{metric:<25} {orig_val:>18.0f}   {fixed_val:>18.0f}   {diff:>13.0f}")
    else:
        print(f"{metric:<25} {orig_val:>18.2f}   {fixed_val:>18.2f}   {diff:>13.2f}")

print(f"\n{'Metric':<25} {'SPY':<20}")
print("-" * 50)
print(f"{'Total Return (%)':<25} {spy_return:>18.2f}%")
print(f"{'CAGR (%)':<25} {spy_cagr:>18.2f}%")

print(f"\n" + "="*80)
print("ANALYSIS")
print("="*80)

print(f"\n📊 Performance Impact:")
return_diff = metrics_fixed['Total Return (%)'] - metrics_original['Total Return (%)']
if abs(return_diff) < 5:
    print(f"   ✅ Returns barely changed ({return_diff:+.2f}%) - Good sign!")
else:
    print(f"   📉 Returns decreased by {abs(return_diff):.2f}% - More realistic")

sharpe_diff = metrics_fixed['Sharpe Ratio'] - metrics_original['Sharpe Ratio']
if sharpe_diff > 0:
    print(f"   ✅ Sharpe improved by {sharpe_diff:+.2f} - Better risk-adjusted returns")
else:
    print(f"   📉 Sharpe decreased by {abs(sharpe_diff):.2f} - Still acceptable if >1.0")

dd_diff = metrics_fixed['Max Drawdown (%)'] - metrics_original['Max Drawdown (%)']
if dd_diff < 0:
    print(f"   ✅ Max DD improved by {abs(dd_diff):.2f}% - Lower risk")
else:
    print(f"   ⚠️  Max DD increased by {dd_diff:.2f}% - Higher risk")

print(f"\n🎯 Professional Standards Check:")
print(f"   Sharpe Ratio >= 1.6:  {'✅ PASS' if metrics_fixed['Sharpe Ratio'] >= 1.6 else '❌ FAIL'}")
print(f"   Sortino Ratio >= 2.2: {'✅ PASS' if metrics_fixed['Sortino Ratio'] >= 2.2 else '❌ FAIL'}")
print(f"   Max DD <= 22%:        {'✅ PASS' if metrics_fixed['Max Drawdown (%)'] <= 22 else '❌ FAIL'}")
print(f"   Calmar >= 1.2:        {'✅ PASS' if metrics_fixed['Calmar Ratio'] >= 1.2 else '❌ FAIL'}")

print(f"\n📝 Conclusion:")
if (metrics_fixed['Sharpe Ratio'] >= 1.6 and
    metrics_fixed['Sortino Ratio'] >= 2.2 and
    metrics_fixed['Max Drawdown (%)'] <= 22 and
    metrics_fixed['Calmar Ratio'] >= 1.2):
    print(f"   ✅ PROFESSIONAL-GRADE: Strategy meets all professional standards!")
elif (metrics_fixed['Sharpe Ratio'] >= 1.3 and
      metrics_fixed['Max Drawdown (%)'] <= 25):
    print(f"   ⚠️  GOOD: Strategy is solid but has room for improvement")
else:
    print(f"   ❌ NEEDS WORK: Strategy requires further optimization")

print(f"\n" + "="*80)
print("✅ Comparison Complete!")
print("="*80)
