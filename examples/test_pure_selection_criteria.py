"""
Pure Selection Criteria Test - No Momentum Contamination

CRITICAL FIX: Previous test had a flaw!
- Universe selection: Different criteria (ROC, Breakout, RS, etc.)
- Position selection: ALWAYS ROC momentum (contaminated!)

This test uses PURE selection criteria:
- If testing Breakout method → Universe AND positions selected by breakout
- If testing RS method → Universe AND positions selected by RS
- No momentum contamination

Expected outcome: This should show the TRUE performance of each method.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("PURE SELECTION CRITERIA TEST (NO MOMENTUM CONTAMINATION)")
print("="*80)
print("\n🔧 CRITICAL FIX:")
print("   Previous test selected universe by different criteria (ROC, Breakout, etc.)")
print("   BUT always selected positions within that universe by ROC momentum")
print("   This contaminated the results!")
print("\n✅ This test uses PURE criteria:")
print("   - Breakout method → Universe AND positions by breakout score")
print("   - RS method → Universe AND positions by RS score")
print("   - etc.")

# Extended universe
EXTENDED_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
    'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'ETC-USD',
    'XLM-USD', 'ALGO-USD', 'VET-USD', 'FIL-USD', 'TRX-USD',
    'AAVE-USD', 'SAND-USD', 'MANA-USD', 'AXS-USD', 'NEAR-USD',
    'HBAR-USD', 'EGLD-USD', 'THETA-USD', 'FTM-USD', 'ICP-USD'
]

print("\n" + "="*80)
print("DOWNLOADING DATA")
print("="*80)

import yfinance as yf

print(f"\nDownloading {len(EXTENDED_UNIVERSE)} cryptos + SPY...")
data = yf.download(EXTENDED_UNIVERSE + ['SPY'], start='2020-01-01', end='2024-12-31',
                   progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
    volume = data['Volume'].copy() if 'Volume' in data else None
    high = data['High'].copy() if 'High' in data else None
    low = data['Low'].copy() if 'Low' in data else None
else:
    close = data[['Close']].copy()
    volume = None
    high = None
    low = None

close = close.ffill()
if volume is not None:
    volume = volume.ffill()
if high is not None:
    high = high.ffill()
if low is not None:
    low = low.ffill()

# Remove tickers with insufficient data
min_data_points = 100
valid_tickers = [col for col in close.columns if col == 'SPY' or close[col].count() >= min_data_points]

close = close[valid_tickers]
if volume is not None:
    volume = volume[[t for t in valid_tickers if t in volume.columns]]
if high is not None:
    high = high[[t for t in valid_tickers if t in high.columns]]
if low is not None:
    low = low[[t for t in valid_tickers if t in low.columns]]

print(f"✅ Data ready: {len(close)} days, {len(valid_tickers)-1} cryptos")

spy_prices = close['SPY']
crypto_prices = close[[t for t in valid_tickers if t != 'SPY']]
crypto_volume = volume[[t for t in valid_tickers if t != 'SPY' and t in volume.columns]] if volume is not None else None
crypto_high = high[[t for t in valid_tickers if t != 'SPY' and t in high.columns]] if high is not None else None
crypto_low = low[[t for t in valid_tickers if t != 'SPY' and t in low.columns]] if low is not None else None

start_backtest = '2020-01-01'
crypto_prices = crypto_prices[crypto_prices.index >= start_backtest]
spy_prices = spy_prices[spy_prices.index >= start_backtest]
if crypto_volume is not None:
    crypto_volume = crypto_volume[crypto_volume.index >= start_backtest]
if crypto_high is not None:
    crypto_high = crypto_high[crypto_high.index >= start_backtest]
if crypto_low is not None:
    crypto_low = crypto_low[crypto_low.index >= start_backtest]

print(f"Backtest period: {crypto_prices.index[0].date()} to {crypto_prices.index[-1].date()}")

# Quarterly rebalance dates
rebalance_dates = pd.date_range(start=crypto_prices.index[0], end=crypto_prices.index[-1], freq='QS-JAN')
print(f"Quarterly rebalances: {len(rebalance_dates)}")

# ============================================================================
# SCORING FUNCTIONS - Return scores for ALL cryptos
# ============================================================================

def score_by_roc(prices, lookback=90):
    """Score all cryptos by momentum"""
    if len(prices) < lookback:
        return pd.Series(0, index=prices.columns)
    roc = (prices.iloc[-1] / prices.iloc[-lookback] - 1)
    return roc.fillna(0)

def score_by_breakout_probability(prices, high_prices, volume):
    """Score all cryptos by breakout probability"""
    scores = {}
    lookback = 20

    if len(prices) < lookback + 20:
        return pd.Series(0, index=prices.columns)

    for ticker in prices.columns:
        try:
            high_20 = high_prices[ticker].rolling(lookback).max().iloc[-1] if high_prices is not None else prices[ticker].rolling(lookback).max().iloc[-1]
            current = prices[ticker].iloc[-1]
            proximity = current / high_20 if high_20 > 0 else 0

            if proximity < 0.90:
                scores[ticker] = 0
                continue

            returns = prices[ticker].pct_change()
            atr_recent = returns.tail(10).abs().mean()
            atr_older = returns.tail(30).head(20).abs().mean()
            vol_compression = (atr_older / atr_recent) if atr_recent > 0 else 0

            if volume is not None and ticker in volume.columns:
                vol_recent = volume[ticker].tail(5).mean()
                vol_older = volume[ticker].tail(30).head(25).mean()
                volume_ratio = (vol_recent / vol_older) if vol_older > 0 else 1
            else:
                volume_ratio = 1

            score = proximity * vol_compression * volume_ratio
            scores[ticker] = score
        except:
            scores[ticker] = 0

    return pd.Series(scores)

def score_by_volatility_squeeze(prices):
    """Score all cryptos by volatility squeeze"""
    scores = {}
    lookback = 20

    if len(prices) < lookback + 50:
        return pd.Series(0, index=prices.columns)

    for ticker in prices.columns:
        try:
            price_series = prices[ticker].tail(100)
            ma20 = price_series.rolling(lookback).mean().iloc[-1]
            std20 = price_series.rolling(lookback).std().iloc[-1]
            bb_width = (std20 / ma20) if ma20 > 0 else 999

            bb_width_series = price_series.rolling(lookback).std() / price_series.rolling(lookback).mean()
            bb_percentile = (bb_width_series < bb_width).sum() / len(bb_width_series)

            squeeze_score = 1 / (bb_width * 100) if bb_width > 0 else 0

            if bb_percentile < 0.20:
                squeeze_score *= 2

            scores[ticker] = squeeze_score
        except:
            scores[ticker] = 0

    return pd.Series(scores)

def score_by_relative_strength(prices, benchmark):
    """Score all cryptos by relative strength"""
    scores = {}

    if len(prices) < 90 or len(benchmark) < 90:
        return pd.Series(0, index=prices.columns)

    for ticker in prices.columns:
        try:
            rs_30 = (prices[ticker].pct_change(30).iloc[-1] - benchmark.pct_change(30).iloc[-1])
            rs_60 = (prices[ticker].pct_change(60).iloc[-1] - benchmark.pct_change(60).iloc[-1])
            rs_90 = (prices[ticker].pct_change(90).iloc[-1] - benchmark.pct_change(90).iloc[-1])

            consistency = 1.0
            if rs_30 > 0 and rs_60 > 0 and rs_90 > 0:
                consistency = 1.5

            avg_rs = (rs_30 + rs_60 + rs_90) / 3
            score = avg_rs * consistency
            scores[ticker] = score
        except:
            scores[ticker] = 0

    return pd.Series(scores)

def score_by_volume_profile(prices, volume):
    """Score all cryptos by volume profile"""
    scores = {}

    if volume is None or len(prices) < 60:
        return pd.Series(0, index=prices.columns)

    for ticker in prices.columns:
        if ticker not in volume.columns:
            scores[ticker] = 0
            continue

        try:
            price_series = prices[ticker].tail(60)
            volume_series = volume[ticker].tail(60)

            vol_recent = volume_series.tail(20).mean()
            vol_older = volume_series.head(20).mean()
            vol_trend = (vol_recent / vol_older) if vol_older > 0 else 1

            obv = (np.sign(price_series.diff()) * volume_series).cumsum()
            obv_slope = (obv.iloc[-1] - obv.iloc[0]) / len(obv)

            price_change = (price_series.iloc[-1] / price_series.iloc[0] - 1)

            score = vol_trend * obv_slope * (1 + price_change)
            scores[ticker] = score
        except:
            scores[ticker] = 0

    return pd.Series(scores)

# ============================================================================
# RUN PURE BACKTESTS
# ============================================================================
print("\n" + "="*80)
print("RUNNING PURE BACKTESTS")
print("="*80)

import vectorbt as vbt

results = []

def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

# Method 1: Pure ROC
print(f"\n{'='*80}")
print("METHOD 1: PURE ROC (Momentum)")
print(f"{'='*80}")
print("Select top 5 cryptos by 90-day ROC, rebalance quarterly")

allocations_roc = pd.DataFrame(0.0, index=crypto_prices.index, columns=crypto_prices.columns)

for date in crypto_prices.index:
    if date < crypto_prices.index[0] + pd.Timedelta(days=100):
        continue

    if date in rebalance_dates or (allocations_roc.loc[:date].sum(axis=1) == 0).all():
        prices_slice = crypto_prices.loc[:date]
        scores = score_by_roc(prices_slice, lookback=90)
        top_5 = scores.nlargest(5).index.tolist()

        for ticker in top_5:
            allocations_roc.loc[date, ticker] = 0.20

# Hold between rebalances
last_allocation = None
for date in crypto_prices.index:
    if date in rebalance_dates or last_allocation is None:
        last_allocation = allocations_roc.loc[date].copy()
    else:
        allocations_roc.loc[date] = last_allocation

portfolio_roc = vbt.Portfolio.from_orders(
    close=crypto_prices,
    size=allocations_roc.div(crypto_prices).mul(100000),
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

pf_value_roc = portfolio_roc.value()
final_value_roc = float(pf_value_roc.values[-1]) if isinstance(pf_value_roc, pd.Series) else float(pf_value_roc.values[-1][0])
total_return_roc = extract_value(portfolio_roc.total_return()) * 100
sharpe_roc = extract_value(portfolio_roc.sharpe_ratio())
max_dd_roc = extract_value(portfolio_roc.max_drawdown()) * 100

print(f"✅ Final Value: ${final_value_roc:,.0f}")
print(f"✅ Total Return: {total_return_roc:+.1f}%")
print(f"✅ Sharpe: {sharpe_roc:.2f}")

results.append({
    'Method': 'Pure ROC',
    'Final_Value': final_value_roc,
    'Total_Return': total_return_roc,
    'Max_DD': max_dd_roc,
    'Sharpe': sharpe_roc
})

# Method 2: Pure Breakout Probability
print(f"\n{'='*80}")
print("METHOD 2: PURE BREAKOUT PROBABILITY")
print(f"{'='*80}")
print("Select top 5 cryptos by breakout score, rebalance quarterly")

allocations_breakout = pd.DataFrame(0.0, index=crypto_prices.index, columns=crypto_prices.columns)

for date in crypto_prices.index:
    if date < crypto_prices.index[0] + pd.Timedelta(days=100):
        continue

    if date in rebalance_dates or (allocations_breakout.loc[:date].sum(axis=1) == 0).all():
        prices_slice = crypto_prices.loc[:date]
        high_slice = crypto_high.loc[:date] if crypto_high is not None else None
        vol_slice = crypto_volume.loc[:date] if crypto_volume is not None else None

        scores = score_by_breakout_probability(prices_slice, high_slice, vol_slice)
        top_5 = scores.nlargest(5).index.tolist()

        if len(top_5) > 0:
            for ticker in top_5:
                allocations_breakout.loc[date, ticker] = 0.20

last_allocation = None
for date in crypto_prices.index:
    if date in rebalance_dates or last_allocation is None:
        last_allocation = allocations_breakout.loc[date].copy()
    else:
        allocations_breakout.loc[date] = last_allocation

portfolio_breakout = vbt.Portfolio.from_orders(
    close=crypto_prices,
    size=allocations_breakout.div(crypto_prices).mul(100000),
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

pf_value_breakout = portfolio_breakout.value()
final_value_breakout = float(pf_value_breakout.values[-1]) if isinstance(pf_value_breakout, pd.Series) else float(pf_value_breakout.values[-1][0])
total_return_breakout = extract_value(portfolio_breakout.total_return()) * 100
sharpe_breakout = extract_value(portfolio_breakout.sharpe_ratio())
max_dd_breakout = extract_value(portfolio_breakout.max_drawdown()) * 100

print(f"✅ Final Value: ${final_value_breakout:,.0f}")
print(f"✅ Total Return: {total_return_breakout:+.1f}%")
print(f"✅ Sharpe: {sharpe_breakout:.2f}")

results.append({
    'Method': 'Pure Breakout',
    'Final_Value': final_value_breakout,
    'Total_Return': total_return_breakout,
    'Max_DD': max_dd_breakout,
    'Sharpe': sharpe_breakout
})

# Method 3: Pure Relative Strength
print(f"\n{'='*80}")
print("METHOD 3: PURE RELATIVE STRENGTH")
print(f"{'='*80}")
print("Select top 5 cryptos by RS score vs SPY, rebalance quarterly")

allocations_rs = pd.DataFrame(0.0, index=crypto_prices.index, columns=crypto_prices.columns)

for date in crypto_prices.index:
    if date < crypto_prices.index[0] + pd.Timedelta(days=100):
        continue

    if date in rebalance_dates or (allocations_rs.loc[:date].sum(axis=1) == 0).all():
        prices_slice = crypto_prices.loc[:date]
        spy_slice = spy_prices.loc[:date]

        scores = score_by_relative_strength(prices_slice, spy_slice)
        top_5 = scores.nlargest(5).index.tolist()

        for ticker in top_5:
            allocations_rs.loc[date, ticker] = 0.20

last_allocation = None
for date in crypto_prices.index:
    if date in rebalance_dates or last_allocation is None:
        last_allocation = allocations_rs.loc[date].copy()
    else:
        allocations_rs.loc[date] = last_allocation

portfolio_rs = vbt.Portfolio.from_orders(
    close=crypto_prices,
    size=allocations_rs.div(crypto_prices).mul(100000),
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

pf_value_rs = portfolio_rs.value()
final_value_rs = float(pf_value_rs.values[-1]) if isinstance(pf_value_rs, pd.Series) else float(pf_value_rs.values[-1][0])
total_return_rs = extract_value(portfolio_rs.total_return()) * 100
sharpe_rs = extract_value(portfolio_rs.sharpe_ratio())
max_dd_rs = extract_value(portfolio_rs.max_drawdown()) * 100

print(f"✅ Final Value: ${final_value_rs:,.0f}")
print(f"✅ Total Return: {total_return_rs:+.1f}%")
print(f"✅ Sharpe: {sharpe_rs:.2f}")

results.append({
    'Method': 'Pure Relative Strength',
    'Final_Value': final_value_rs,
    'Total_Return': total_return_rs,
    'Max_DD': max_dd_rs,
    'Sharpe': sharpe_rs
})

# Baseline: Fixed Universe
print(f"\n{'='*80}")
print("BASELINE: FIXED UNIVERSE")
print(f"{'='*80}")

FIXED_UNIVERSE = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
                  'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD']
fixed_universe = [t for t in FIXED_UNIVERSE if t in crypto_prices.columns]
fixed_prices = crypto_prices[fixed_universe]

allocations_fixed = pd.DataFrame(0.0, index=fixed_prices.index, columns=fixed_prices.columns)

for date in fixed_prices.index:
    if date < fixed_prices.index[0] + pd.Timedelta(days=100):
        continue

    if date in rebalance_dates or (allocations_fixed.loc[:date].sum(axis=1) == 0).all():
        prices_slice = fixed_prices.loc[:date]
        roc = (prices_slice.iloc[-1] / prices_slice.iloc[-100] - 1)
        top_5 = roc.nlargest(5).index.tolist()

        for ticker in top_5:
            allocations_fixed.loc[date, ticker] = 0.20

last_allocation = None
for date in fixed_prices.index:
    if date in rebalance_dates or last_allocation is None:
        last_allocation = allocations_fixed.loc[date].copy()
    else:
        allocations_fixed.loc[date] = last_allocation

portfolio_fixed = vbt.Portfolio.from_orders(
    close=fixed_prices,
    size=allocations_fixed.div(fixed_prices).mul(100000),
    size_type='amount',
    init_cash=100000,
    fees=0.001,
    freq='1D'
)

pf_value_fixed = portfolio_fixed.value()
final_value_fixed = float(pf_value_fixed.values[-1]) if isinstance(pf_value_fixed, pd.Series) else float(pf_value_fixed.values[-1][0])
total_return_fixed = extract_value(portfolio_fixed.total_return()) * 100
sharpe_fixed = extract_value(portfolio_fixed.sharpe_ratio())
max_dd_fixed = extract_value(portfolio_fixed.max_drawdown()) * 100

print(f"✅ Final Value: ${final_value_fixed:,.0f}")
print(f"✅ Total Return: {total_return_fixed:+.1f}%")
print(f"✅ Sharpe: {sharpe_fixed:.2f}")

results.append({
    'Method': 'Fixed Universe',
    'Final_Value': final_value_fixed,
    'Total_Return': total_return_fixed,
    'Max_DD': max_dd_fixed,
    'Sharpe': sharpe_fixed
})

# ============================================================================
# RESULTS
# ============================================================================
print("\n" + "="*80)
print("RESULTS COMPARISON - PURE METHODS")
print("="*80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('Total_Return', ascending=False)

print("\n" + results_df.to_string(index=False))

best = results_df.iloc[0]
print(f"\n{'='*80}")
print(f"🏆 WINNER: {best['Method']}")
print(f"{'='*80}")
print(f"\n  Final Value:  ${best['Final_Value']:,.0f}")
print(f"  Total Return: {best['Total_Return']:+.1f}%")
print(f"  Sharpe Ratio: {best['Sharpe']:.2f}")

# Save results
output_dir = Path('results/crypto')
output_dir.mkdir(parents=True, exist_ok=True)
results_df.to_csv(output_dir / 'pure_selection_criteria_test.csv', index=False)
print(f"\n📁 Results saved to: {output_dir}/pure_selection_criteria_test.csv")

print("\n✅ Pure selection criteria test complete!")
