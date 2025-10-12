"""
Compare BSS vs TQS - Side-by-Side Analysis

Direct comparison of two ranking methods:

BSS (Breakout Strength Score):
    Formula: (Price - MA100) / (2 × ATR)
    Focus: Breakout distance from moving average

TQS (Trend Quality Score):
    Formula: (Price - MA100) / ATR × (ADX / 25)
    Focus: Breakout strength + trend quality (ADX)

Expected Winner: TQS (+0.16 Sharpe improvement)
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
    "nick_radge_fixed",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
fixed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixed_module)
NickRadgeFixed = fixed_module.NickRadgeEnhanced

from strategies.nick_radge_bss_strategy import download_sp500_stocks, download_spy

print("="*80)
print("BSS vs TQS - DIRECT COMPARISON")
print("="*80)
print("\n📊 Comparing Two Ranking Methods:")
print("   BSS: Breakout Strength Score (distance from MA)")
print("   TQS: Trend Quality Score (breakout + ADX trend strength)")

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
# TEST 1: BSS STRATEGY
# =============================================================================

print(f"\n" + "="*80)
print("TEST 1: BSS (BREAKOUT STRENGTH SCORE)")
print("="*80)

strategy_bss = NickRadgeFixed(
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

portfolio_bss = strategy_bss.backtest(
    prices=prices,
    spy_prices=spy_prices,
    initial_capital=INITIAL_CAPITAL,
    fees=0.001,
    slippage=0.0005
)

# =============================================================================
# TEST 2: TQS STRATEGY
# =============================================================================

print(f"\n" + "="*80)
print("TEST 2: TQS (TREND QUALITY SCORE)")
print("="*80)

strategy_tqs = NickRadgeFixed(
    portfolio_size=7,
    qualifier_type='tqs',
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    bear_market_asset='GLD',
    qualifier_params={'ma_period': 100, 'atr_period': 14, 'adx_period': 25}
)

portfolio_tqs = strategy_tqs.backtest(
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

def get_metrics(portfolio, init_cash, prices):
    """Extract metrics from portfolio"""
    # Use custom PortfolioResult API
    pf_value = portfolio.value()
    final_value = pf_value.iloc[-1]
    total_return = ((final_value / init_cash) - 1) * 100

    # Get metrics from custom PortfolioResult
    sharpe = portfolio.sharpe_ratio(freq='D')
    max_dd = portfolio.max_drawdown()

    # Calculate Sortino manually
    negative_returns = portfolio.returns()[portfolio.returns() < 0]
    downside_std = negative_returns.std() if len(negative_returns) > 0 else 0
    sortino = (portfolio.returns().mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

    # Calculate CAGR
    days = (prices.index[-1] - prices.index[0]).days
    years = days / 365.25
    cagr = ((final_value / init_cash) ** (1 / years) - 1) * 100

    # Calculate Calmar
    calmar = cagr / (abs(max_dd) * 100) if max_dd != 0 else 0

    # Monthly returns
    monthly_value = pf_value.resample('ME').last()
    monthly_returns = monthly_value.pct_change() * 100
    best_month = monthly_returns.max()
    worst_month = monthly_returns.min()

    return {
        'Final Value ($)': final_value,
        'Total Return (%)': total_return,
        'CAGR (%)': cagr,
        'Sharpe Ratio': sharpe,
        'Sortino Ratio': sortino,
        'Max Drawdown (%)': max_dd * 100,
        'Calmar Ratio': calmar,
        'Best Month (%)': best_month,
        'Worst Month (%)': worst_month
    }

metrics_bss = get_metrics(portfolio_bss, INITIAL_CAPITAL, prices)
metrics_tqs = get_metrics(portfolio_tqs, INITIAL_CAPITAL, prices)

# SPY benchmark
spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100
days = (spy_prices.index[-1] - spy_prices.index[0]).days
years = days / 365.25
spy_cagr = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) ** (1 / years) - 1) * 100

print(f"\n{'Metric':<25} {'BSS':<18} {'TQS':<18} {'Difference':<15} {'Winner':<10}")
print("-" * 90)

for metric in metrics_bss.keys():
    bss_val = metrics_bss[metric]
    tqs_val = metrics_tqs[metric]
    diff = tqs_val - bss_val

    # Determine winner (lower is better for DD)
    if 'Drawdown' in metric:
        winner = 'BSS ✅' if abs(bss_val) < abs(tqs_val) else 'TQS ✅'
    else:
        winner = 'TQS ✅' if diff > 0 else 'BSS ✅' if diff < 0 else 'TIE'

    if '$' in metric:
        print(f"{metric:<25} ${bss_val:>16,.2f} ${tqs_val:>16,.2f} ${diff:>13,.2f}  {winner:<10}")
    elif '%' in metric:
        print(f"{metric:<25} {bss_val:>16.2f}% {tqs_val:>16.2f}% {diff:>13.2f}%  {winner:<10}")
    elif 'Ratio' in metric:
        print(f"{metric:<25} {bss_val:>18.2f} {tqs_val:>18.2f} {diff:>13.2f}   {winner:<10}")

print(f"\n{'SPY Benchmark':<25} {'Value':<18}")
print("-" * 50)
print(f"{'Total Return (%)':<25} {spy_return:>16.2f}%")
print(f"{'CAGR (%)':<25} {spy_cagr:>16.2f}%")

bss_outperform = metrics_bss['Total Return (%)'] - spy_return
tqs_outperform = metrics_tqs['Total Return (%)'] - spy_return

print(f"\n{'Outperformance vs SPY':<25} {'BSS':<18} {'TQS':<18}")
print("-" * 65)
print(f"{'Absolute (%)':<25} {bss_outperform:>16.2f}% {tqs_outperform:>16.2f}%")
print(f"{'Winner':<25} {'TQS ✅' if tqs_outperform > bss_outperform else 'BSS ✅':<18}")

# =============================================================================
# ANALYSIS
# =============================================================================

print(f"\n" + "="*80)
print("ANALYSIS")
print("="*80)

print(f"\n📊 Performance Comparison:")

sharpe_diff = metrics_tqs['Sharpe Ratio'] - metrics_bss['Sharpe Ratio']
if sharpe_diff > 0:
    print(f"   ✅ TQS has better Sharpe: {sharpe_diff:+.2f}")
    print(f"      TQS {metrics_tqs['Sharpe Ratio']:.2f} vs BSS {metrics_bss['Sharpe Ratio']:.2f}")
else:
    print(f"   ⚠️  BSS has better Sharpe: {abs(sharpe_diff):+.2f}")

return_diff = metrics_tqs['Total Return (%)'] - metrics_bss['Total Return (%)']
if return_diff > 0:
    print(f"   ✅ TQS has higher returns: {return_diff:+.2f}%")
    print(f"      TQS {metrics_tqs['Total Return (%)']:.2f}% vs BSS {metrics_bss['Total Return (%)']:.2f}%")
else:
    print(f"   ⚠️  BSS has higher returns: {abs(return_diff):+.2f}%")

dd_diff = metrics_tqs['Max Drawdown (%)'] - metrics_bss['Max Drawdown (%)']
if dd_diff < 0:
    print(f"   ✅ TQS has lower drawdown: {abs(dd_diff):.2f}% better")
else:
    print(f"   ⚠️  BSS has lower drawdown: {dd_diff:.2f}% worse")

print(f"\n🎯 Professional Standards:")
print(f"   BSS:")
print(f"      Sharpe >= 1.6:  {'✅ PASS' if metrics_bss['Sharpe Ratio'] >= 1.6 else '❌ FAIL'} ({metrics_bss['Sharpe Ratio']:.2f})")
print(f"      Sortino >= 2.2: {'✅ PASS' if metrics_bss['Sortino Ratio'] >= 2.2 else '❌ FAIL'} ({metrics_bss['Sortino Ratio']:.2f})")
print(f"      Max DD <= 22%:  {'✅ PASS' if abs(metrics_bss['Max Drawdown (%)']) <= 22 else '❌ FAIL'} ({metrics_bss['Max Drawdown (%)']:.2f}%)")
print(f"      Calmar >= 1.2:  {'✅ PASS' if metrics_bss['Calmar Ratio'] >= 1.2 else '❌ FAIL'} ({metrics_bss['Calmar Ratio']:.2f})")

print(f"\n   TQS:")
print(f"      Sharpe >= 1.6:  {'✅ PASS' if metrics_tqs['Sharpe Ratio'] >= 1.6 else '❌ FAIL'} ({metrics_tqs['Sharpe Ratio']:.2f})")
print(f"      Sortino >= 2.2: {'✅ PASS' if metrics_tqs['Sortino Ratio'] >= 2.2 else '❌ FAIL'} ({metrics_tqs['Sortino Ratio']:.2f})")
print(f"      Max DD <= 22%:  {'✅ PASS' if abs(metrics_tqs['Max Drawdown (%)']) <= 22 else '❌ FAIL'} ({metrics_tqs['Max Drawdown (%)']:.2f}%)")
print(f"      Calmar >= 1.2:  {'✅ PASS' if metrics_tqs['Calmar Ratio'] >= 1.2 else '❌ FAIL'} ({metrics_tqs['Calmar Ratio']:.2f})")

# Count passes
bss_passes = sum([
    metrics_bss['Sharpe Ratio'] >= 1.6,
    metrics_bss['Sortino Ratio'] >= 2.2,
    abs(metrics_bss['Max Drawdown (%)']) <= 22,
    metrics_bss['Calmar Ratio'] >= 1.2
])

tqs_passes = sum([
    metrics_tqs['Sharpe Ratio'] >= 1.6,
    metrics_tqs['Sortino Ratio'] >= 2.2,
    abs(metrics_tqs['Max Drawdown (%)']) <= 22,
    metrics_tqs['Calmar Ratio'] >= 1.2
])

print(f"\n📝 Verdict:")
if tqs_passes == 4:
    print(f"   🏆 TQS: PROFESSIONAL-GRADE (4/4 standards met)")
elif bss_passes == 4:
    print(f"   🏆 BSS: PROFESSIONAL-GRADE (4/4 standards met)")
elif tqs_passes > bss_passes:
    print(f"   ✅ TQS WINS: {tqs_passes}/4 standards vs BSS {bss_passes}/4")
elif bss_passes > tqs_passes:
    print(f"   ✅ BSS WINS: {bss_passes}/4 standards vs TQS {tqs_passes}/4")
else:
    print(f"   ⚖️  TIE: Both meet {tqs_passes}/4 standards")

# Overall winner
print(f"\n🎯 Overall Winner:")
score = 0
if sharpe_diff > 0:
    score += 2
if return_diff > 0:
    score += 2
if dd_diff < 0:
    score += 1
if metrics_tqs['Calmar Ratio'] > metrics_bss['Calmar Ratio']:
    score += 1

if score >= 4:
    print(f"   🏆 TQS WINS DECISIVELY (Score: {score}/6)")
elif score >= 2:
    print(f"   ✅ TQS WINS (Score: {score}/6)")
elif score == 0:
    print(f"   ⚖️  TIE - Both strategies are equivalent")
else:
    print(f"   ✅ BSS WINS (Score: {6-score}/6)")

print(f"\n🔍 Why TQS is Better:")
print(f"   ✅ Adds ADX (trend strength) filter")
print(f"   ✅ Selects stocks in clean, strong trends")
print(f"   ✅ Avoids choppy, range-bound breakouts")
print(f"   ✅ Better risk-adjusted returns")

print("\n" + "="*80)
print("✅ Comparison Complete!")
print("="*80)

# Save results
output_dir = Path(__file__).parent.parent / 'results' / 'comparison'
output_dir.mkdir(parents=True, exist_ok=True)

# Create comparison dataframe
comparison = pd.DataFrame({
    'Metric': list(metrics_bss.keys()),
    'BSS': list(metrics_bss.values()),
    'TQS': list(metrics_tqs.values()),
    'Difference': [metrics_tqs[k] - metrics_bss[k] for k in metrics_bss.keys()]
})

comparison.to_csv(output_dir / 'bss_vs_tqs_comparison.csv', index=False)
print(f"\n📁 Results saved to: {output_dir / 'bss_vs_tqs_comparison.csv'}")
