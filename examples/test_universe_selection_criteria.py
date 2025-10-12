"""
Alternative Universe Selection Criteria - Crypto Strategy

Tests different methods of selecting top N cryptos for quarterly rebalancing.

HYPOTHESIS: The problem isn't quarterly rebalancing itself, but the selection criteria.

Selection Methods to Test:
1. ❌ ROC (Rate of Change) - FAILED in previous test (momentum chasing)
2. ✅ Breakout Probability - Cryptos near breakout (consolidation → expansion)
3. ✅ Volatility Squeeze - Low volatility → High volatility transition
4. ✅ Relative Strength - Outperforming benchmark consistently
5. ✅ Volume Surge - Accumulation phase (smart money buying)
6. ✅ Composite Score - Weighted combination of multiple factors

GOAL: Find a selection method that identifies cryptos BEFORE major moves,
      not AFTER (which is what ROC does).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("ALTERNATIVE UNIVERSE SELECTION CRITERIA TEST")
print("="*80)
print("\n🎯 Goal: Find better way to select top cryptos for quarterly rebalancing")
print("\nTesting 6 different selection methods:")
print("  1. ROC (Momentum) - BASELINE from previous test")
print("  2. Breakout Probability - Donchian breakout + consolidation")
print("  3. Volatility Squeeze - Bollinger Band squeeze indicator")
print("  4. Relative Strength - Consistent outperformance vs benchmark")
print("  5. Volume Profile - Accumulation vs distribution")
print("  6. Composite Score - Multi-factor model")

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
valid_tickers = []
for col in close.columns:
    if col == 'SPY':
        valid_tickers.append(col)
        continue
    if close[col].count() >= min_data_points:
        valid_tickers.append(col)

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
# SELECTION METHOD 1: ROC (MOMENTUM) - BASELINE
# ============================================================================
print("\n" + "="*80)
print("METHOD 1: ROC (MOMENTUM) - BASELINE")
print("="*80)
print("\nLogic: Select top 10 by 90-day rate of change")
print("Problem: Chases recent winners (buys high, sells low)")

def select_by_roc(prices, n=10, lookback=90):
    """Select top N by momentum (90-day ROC)"""
    if len(prices) < lookback:
        return []
    roc = (prices.iloc[-1] / prices.iloc[-lookback] - 1).dropna()
    return roc.nlargest(n).index.tolist()

# ============================================================================
# SELECTION METHOD 2: BREAKOUT PROBABILITY
# ============================================================================
print("\n" + "="*80)
print("METHOD 2: BREAKOUT PROBABILITY")
print("="*80)
print("\nLogic: Select cryptos near breakout from consolidation")
print("Indicators:")
print("  - Price near 20-day high (within 5%)")
print("  - ATR decreasing (consolidation)")
print("  - Volume increasing (accumulation)")
print("Score = (proximity to high) × (1 / ATR%) × (volume ratio)")

def select_by_breakout_probability(prices, high_prices, volume, n=10, lookback=20):
    """
    Select cryptos with highest breakout probability:
    - Near 20-day high (consolidation at resistance)
    - Decreasing volatility (coiling)
    - Increasing volume (accumulation)
    """
    if len(prices) < lookback + 20:
        return []

    scores = {}
    for ticker in prices.columns:
        try:
            # 1. Proximity to 20-day high (0-1, higher = closer)
            high_20 = high_prices[ticker].rolling(lookback).max().iloc[-1] if high_prices is not None else prices[ticker].rolling(lookback).max().iloc[-1]
            current = prices[ticker].iloc[-1]
            proximity = current / high_20 if high_20 > 0 else 0

            # Only consider if within 10% of high
            if proximity < 0.90:
                continue

            # 2. Volatility compression (ATR decreasing)
            returns = prices[ticker].pct_change()
            atr_recent = returns.tail(10).abs().mean()
            atr_older = returns.tail(30).head(20).abs().mean()
            volatility_compression = (atr_older / atr_recent) if atr_recent > 0 else 0

            # 3. Volume surge (accumulation)
            if volume is not None and ticker in volume.columns:
                vol_recent = volume[ticker].tail(5).mean()
                vol_older = volume[ticker].tail(30).head(25).mean()
                volume_ratio = (vol_recent / vol_older) if vol_older > 0 else 1
            else:
                volume_ratio = 1

            # Composite score
            score = proximity * volatility_compression * volume_ratio
            scores[ticker] = score

        except:
            continue

    if len(scores) == 0:
        return []

    scores_series = pd.Series(scores)
    return scores_series.nlargest(n).index.tolist()

# ============================================================================
# SELECTION METHOD 3: VOLATILITY SQUEEZE
# ============================================================================
print("\n" + "="*80)
print("METHOD 3: VOLATILITY SQUEEZE")
print("="*80)
print("\nLogic: Select cryptos in Bollinger Band squeeze (low vol → high vol)")
print("Indicators:")
print("  - Bollinger Band Width at multi-month lows")
print("  - Price near middle of range (consolidation)")
print("Score = (1 / BB Width) × (range position)")

def select_by_volatility_squeeze(prices, n=10, lookback=20):
    """
    Select cryptos with tightest Bollinger Bands (volatility squeeze).
    Low volatility often precedes high volatility moves.
    """
    if len(prices) < lookback + 50:
        return []

    scores = {}
    for ticker in prices.columns:
        try:
            price_series = prices[ticker].tail(100)

            # Calculate Bollinger Bands
            ma20 = price_series.rolling(lookback).mean().iloc[-1]
            std20 = price_series.rolling(lookback).std().iloc[-1]
            bb_width = (std20 / ma20) if ma20 > 0 else 999

            # Compare to historical BB width (is it unusually tight?)
            bb_width_series = price_series.rolling(lookback).std() / price_series.rolling(lookback).mean()
            bb_percentile = (bb_width_series < bb_width).sum() / len(bb_width_series)

            # Lower BB width = higher score
            squeeze_score = 1 / (bb_width * 100) if bb_width > 0 else 0

            # Bonus if at historical low volatility
            if bb_percentile < 0.20:  # Bottom 20% of volatility
                squeeze_score *= 2

            scores[ticker] = squeeze_score

        except:
            continue

    if len(scores) == 0:
        return []

    scores_series = pd.Series(scores)
    return scores_series.nlargest(n).index.tolist()

# ============================================================================
# SELECTION METHOD 4: RELATIVE STRENGTH
# ============================================================================
print("\n" + "="*80)
print("METHOD 4: RELATIVE STRENGTH")
print("="*80)
print("\nLogic: Select cryptos with CONSISTENT outperformance vs benchmark")
print("Indicators:")
print("  - Outperforming SPY over 30, 60, 90 days")
print("  - Rising relative strength (not just high, but improving)")
print("Score = Average RS across multiple timeframes")

def select_by_relative_strength(prices, benchmark, n=10):
    """
    Select cryptos with strongest CONSISTENT relative strength vs benchmark.
    Not just recent outperformance, but sustained over multiple timeframes.
    """
    if len(prices) < 90 or len(benchmark) < 90:
        return []

    scores = {}
    for ticker in prices.columns:
        try:
            # Calculate RS over multiple timeframes
            rs_30 = (prices[ticker].pct_change(30).iloc[-1] - benchmark.pct_change(30).iloc[-1])
            rs_60 = (prices[ticker].pct_change(60).iloc[-1] - benchmark.pct_change(60).iloc[-1])
            rs_90 = (prices[ticker].pct_change(90).iloc[-1] - benchmark.pct_change(90).iloc[-1])

            # Consistency bonus: all periods positive
            consistency = 1.0
            if rs_30 > 0 and rs_60 > 0 and rs_90 > 0:
                consistency = 1.5  # 50% bonus for consistent outperformance

            # Average RS across timeframes
            avg_rs = (rs_30 + rs_60 + rs_90) / 3

            # Score = average RS × consistency multiplier
            score = avg_rs * consistency
            scores[ticker] = score

        except:
            continue

    if len(scores) == 0:
        return []

    scores_series = pd.Series(scores)
    return scores_series.nlargest(n).index.tolist()

# ============================================================================
# SELECTION METHOD 5: VOLUME PROFILE (ACCUMULATION)
# ============================================================================
print("\n" + "="*80)
print("METHOD 5: VOLUME PROFILE (ACCUMULATION)")
print("="*80)
print("\nLogic: Select cryptos with smart money accumulation")
print("Indicators:")
print("  - Volume increasing while price stable/rising (accumulation)")
print("  - OBV (On-Balance Volume) trending up")
print("Score = Volume trend × OBV slope")

def select_by_volume_profile(prices, volume, n=10):
    """
    Select cryptos showing accumulation patterns:
    - Rising volume
    - Rising On-Balance Volume
    - Price stable or rising (not distributing)
    """
    if volume is None or len(prices) < 60:
        # Fallback to RS if no volume data
        return []

    scores = {}
    for ticker in prices.columns:
        if ticker not in volume.columns:
            continue

        try:
            price_series = prices[ticker].tail(60)
            volume_series = volume[ticker].tail(60)

            # 1. Volume trend (increasing?)
            vol_recent = volume_series.tail(20).mean()
            vol_older = volume_series.head(20).mean()
            vol_trend = (vol_recent / vol_older) if vol_older > 0 else 1

            # 2. On-Balance Volume (OBV)
            obv = (np.sign(price_series.diff()) * volume_series).cumsum()
            obv_slope = (obv.iloc[-1] - obv.iloc[0]) / len(obv)

            # 3. Price action (accumulation = rising or stable, not dumping)
            price_change = (price_series.iloc[-1] / price_series.iloc[0] - 1)

            # Score: volume trend × OBV slope × (1 + price change)
            # Positive when volume + OBV rising and price not dumping
            score = vol_trend * obv_slope * (1 + price_change)
            scores[ticker] = score

        except:
            continue

    if len(scores) == 0:
        return []

    scores_series = pd.Series(scores)
    return scores_series.nlargest(n).index.tolist()

# ============================================================================
# SELECTION METHOD 6: COMPOSITE SCORE (MULTI-FACTOR)
# ============================================================================
print("\n" + "="*80)
print("METHOD 6: COMPOSITE SCORE (MULTI-FACTOR)")
print("="*80)
print("\nLogic: Weighted combination of all factors")
print("Weights:")
print("  - Breakout Probability: 30%")
print("  - Relative Strength: 30%")
print("  - Volatility Squeeze: 20%")
print("  - Volume Profile: 20%")

def select_by_composite(prices, high_prices, low_prices, volume, benchmark, n=10):
    """
    Multi-factor model combining all selection methods.
    Weighted average of normalized scores.
    """
    if len(prices) < 90:
        return []

    # Calculate all scores for each crypto
    all_scores = pd.DataFrame(index=prices.columns)

    # Method 2: Breakout Probability
    breakout_scores = {}
    for ticker in prices.columns:
        try:
            high_20 = high_prices[ticker].rolling(20).max().iloc[-1] if high_prices is not None else prices[ticker].rolling(20).max().iloc[-1]
            current = prices[ticker].iloc[-1]
            proximity = current / high_20 if high_20 > 0 else 0
            if proximity >= 0.90:
                returns = prices[ticker].pct_change()
                atr_recent = returns.tail(10).abs().mean()
                atr_older = returns.tail(30).head(20).abs().mean()
                vol_compression = (atr_older / atr_recent) if atr_recent > 0 else 0
                breakout_scores[ticker] = proximity * vol_compression
        except:
            pass
    all_scores['breakout'] = pd.Series(breakout_scores)

    # Method 3: Volatility Squeeze
    squeeze_scores = {}
    for ticker in prices.columns:
        try:
            price_series = prices[ticker].tail(100)
            ma20 = price_series.rolling(20).mean().iloc[-1]
            std20 = price_series.rolling(20).std().iloc[-1]
            bb_width = (std20 / ma20) if ma20 > 0 else 999
            squeeze_scores[ticker] = 1 / (bb_width * 100) if bb_width > 0 else 0
        except:
            pass
    all_scores['squeeze'] = pd.Series(squeeze_scores)

    # Method 4: Relative Strength
    rs_scores = {}
    for ticker in prices.columns:
        try:
            rs_30 = (prices[ticker].pct_change(30).iloc[-1] - benchmark.pct_change(30).iloc[-1])
            rs_60 = (prices[ticker].pct_change(60).iloc[-1] - benchmark.pct_change(60).iloc[-1])
            rs_90 = (prices[ticker].pct_change(90).iloc[-1] - benchmark.pct_change(90).iloc[-1])
            avg_rs = (rs_30 + rs_60 + rs_90) / 3
            rs_scores[ticker] = avg_rs
        except:
            pass
    all_scores['rs'] = pd.Series(rs_scores)

    # Method 5: Volume Profile
    vol_scores = {}
    if volume is not None:
        for ticker in prices.columns:
            if ticker not in volume.columns:
                continue
            try:
                volume_series = volume[ticker].tail(60)
                vol_recent = volume_series.tail(20).mean()
                vol_older = volume_series.head(20).mean()
                vol_trend = (vol_recent / vol_older) if vol_older > 0 else 1
                vol_scores[ticker] = vol_trend
            except:
                pass
    all_scores['volume'] = pd.Series(vol_scores)

    # Normalize each score to 0-1 range
    for col in all_scores.columns:
        if all_scores[col].std() > 0:
            all_scores[col] = (all_scores[col] - all_scores[col].min()) / (all_scores[col].max() - all_scores[col].min())

    # Fill NaN with 0
    all_scores = all_scores.fillna(0)

    # Weighted composite score
    all_scores['composite'] = (
        all_scores['breakout'] * 0.30 +
        all_scores['rs'] * 0.30 +
        all_scores['squeeze'] * 0.20 +
        all_scores['volume'] * 0.20
    )

    return all_scores['composite'].nlargest(n).index.tolist()

# ============================================================================
# RUN BACKTESTS FOR ALL METHODS
# ============================================================================
print("\n" + "="*80)
print("RUNNING BACKTESTS")
print("="*80)

import vectorbt as vbt

results = []

selection_methods = [
    ('ROC (Momentum)', lambda p, h, l, v, b: select_by_roc(p, n=10, lookback=90)),
    ('Breakout Probability', lambda p, h, l, v, b: select_by_breakout_probability(p, h, v, n=10)),
    ('Volatility Squeeze', lambda p, h, l, v, b: select_by_volatility_squeeze(p, n=10)),
    ('Relative Strength', lambda p, h, l, v, b: select_by_relative_strength(p, b, n=10)),
    ('Volume Profile', lambda p, h, l, v, b: select_by_volume_profile(p, v, n=10)),
    ('Composite Score', lambda p, h, l, v, b: select_by_composite(p, h, l, v, b, n=10))
]

def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

for method_name, selection_func in selection_methods:
    print(f"\n{'='*80}")
    print(f"Testing: {method_name}")
    print(f"{'='*80}")

    # Generate allocations with this selection method
    allocations = pd.DataFrame(0.0, index=crypto_prices.index, columns=crypto_prices.columns)

    current_universe = []
    roc_period = 100

    for date in crypto_prices.index:
        if date < crypto_prices.index[0] + pd.Timedelta(days=roc_period):
            continue

        # Rebalance on quarterly dates
        if date in rebalance_dates or len(current_universe) == 0:
            try:
                prices_slice = crypto_prices.loc[:date]
                high_slice = crypto_high.loc[:date] if crypto_high is not None else None
                low_slice = crypto_low.loc[:date] if crypto_low is not None else None
                vol_slice = crypto_volume.loc[:date] if crypto_volume is not None else None
                spy_slice = spy_prices.loc[:date]

                current_universe = selection_func(prices_slice, high_slice, low_slice, vol_slice, spy_slice)

                if len(current_universe) == 0:
                    continue

            except Exception as e:
                continue

        # Within current universe, select top 5 by ROC
        if len(current_universe) > 0:
            try:
                prices_in_universe = crypto_prices[current_universe].loc[:date]
                if len(prices_in_universe) < roc_period:
                    continue
                roc = prices_in_universe.iloc[-1] / prices_in_universe.iloc[-roc_period] - 1
                top_5 = roc.nlargest(5).index.tolist()

                for ticker in top_5:
                    allocations.loc[date, ticker] = 0.20
            except:
                pass

    # Apply quarterly rebalancing (hold positions between rebalance dates)
    last_allocation = None
    for date in crypto_prices.index:
        if date in rebalance_dates or last_allocation is None:
            last_allocation = allocations.loc[date].copy()
        else:
            allocations.loc[date] = last_allocation

    print(f"  Allocations generated: {(allocations.sum(axis=1) > 0).sum()} active days")

    # Backtest
    try:
        portfolio = vbt.Portfolio.from_orders(
            close=crypto_prices,
            size=allocations.div(crypto_prices).mul(100000),
            size_type='amount',
            init_cash=100000,
            fees=0.001,
            freq='1D'
        )

        pf_value = portfolio.value()
        if isinstance(pf_value, pd.DataFrame):
            final_value = float(pf_value.values[-1][0])
        elif isinstance(pf_value, pd.Series):
            final_value = float(pf_value.values[-1])
        else:
            final_value = float(pf_value)

        total_return = extract_value(portfolio.total_return()) * 100
        annualized = extract_value(portfolio.annualized_return()) * 100
        sharpe = extract_value(portfolio.sharpe_ratio())
        max_dd = extract_value(portfolio.max_drawdown()) * 100

        results.append({
            'Method': method_name,
            'Final_Value': final_value,
            'Total_Return': total_return,
            'Annualized': annualized,
            'Max_DD': max_dd,
            'Sharpe': sharpe
        })

        print(f"  ✅ Final Value: ${final_value:,.0f}")
        print(f"  ✅ Total Return: {total_return:+.1f}%")
        print(f"  ✅ Sharpe: {sharpe:.2f}")

    except Exception as e:
        print(f"  ❌ Backtest failed: {e}")
        results.append({
            'Method': method_name,
            'Final_Value': 0,
            'Total_Return': 0,
            'Annualized': 0,
            'Max_DD': 0,
            'Sharpe': 0
        })

# Add fixed universe baseline
print(f"\n{'='*80}")
print("BASELINE: Fixed Universe (Current Approach)")
print(f"{'='*80}")

FIXED_UNIVERSE = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
                  'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD']
fixed_universe = [t for t in FIXED_UNIVERSE if t in crypto_prices.columns]
fixed_prices = crypto_prices[fixed_universe]

allocations_fixed = pd.DataFrame(0.0, index=fixed_prices.index, columns=fixed_prices.columns)
roc_period = 100

for date in fixed_prices.index:
    if date < fixed_prices.index[0] + pd.Timedelta(days=roc_period):
        continue
    prices_slice = fixed_prices.loc[:date]
    roc = prices_slice.iloc[-1] / prices_slice.iloc[-roc_period] - 1
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
if isinstance(pf_value_fixed, pd.DataFrame):
    final_value_fixed = float(pf_value_fixed.values[-1][0])
elif isinstance(pf_value_fixed, pd.Series):
    final_value_fixed = float(pf_value_fixed.values[-1])
else:
    final_value_fixed = float(pf_value_fixed)

total_return_fixed = extract_value(portfolio_fixed.total_return()) * 100
annualized_fixed = extract_value(portfolio_fixed.annualized_return()) * 100
sharpe_fixed = extract_value(portfolio_fixed.sharpe_ratio())
max_dd_fixed = extract_value(portfolio_fixed.max_drawdown()) * 100

results.append({
    'Method': 'FIXED UNIVERSE (Baseline)',
    'Final_Value': final_value_fixed,
    'Total_Return': total_return_fixed,
    'Annualized': annualized_fixed,
    'Max_DD': max_dd_fixed,
    'Sharpe': sharpe_fixed
})

print(f"  ✅ Final Value: ${final_value_fixed:,.0f}")
print(f"  ✅ Total Return: {total_return_fixed:+.1f}%")
print(f"  ✅ Sharpe: {sharpe_fixed:.2f}")

# ============================================================================
# RESULTS COMPARISON
# ============================================================================
print("\n" + "="*80)
print("COMPREHENSIVE COMPARISON")
print("="*80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('Total_Return', ascending=False)

print("\n" + results_df.to_string(index=False))

# Find best method
best = results_df.iloc[0]
print(f"\n{'='*80}")
print(f"🏆 WINNER: {best['Method']}")
print(f"{'='*80}")
print(f"\n  Final Value:   ${best['Final_Value']:,.0f}")
print(f"  Total Return:  {best['Total_Return']:+.1f}%")
print(f"  Annualized:    {best['Annualized']:.1f}%")
print(f"  Max Drawdown:  {best['Max_DD']:.1f}%")
print(f"  Sharpe Ratio:  {best['Sharpe']:.2f}")

baseline_return = results_df[results_df['Method'] == 'FIXED UNIVERSE (Baseline)']['Total_Return'].values[0]
improvement = best['Total_Return'] - baseline_return

if improvement > 0:
    print(f"\n  ✅ IMPROVEMENT vs Fixed Universe: +{improvement:.1f}%")
    print(f"\n  💡 RECOMMENDATION: Implement {best['Method']} for quarterly rebalancing!")
else:
    print(f"\n  ❌ NO IMPROVEMENT vs Fixed Universe: {improvement:.1f}%")
    print(f"\n  💡 RECOMMENDATION: Keep fixed universe approach")

# Save results
output_dir = Path('results/crypto')
output_dir.mkdir(parents=True, exist_ok=True)
results_df.to_csv(output_dir / 'universe_selection_methods_comparison.csv', index=False)
print(f"\n📁 Results saved to: {output_dir}/universe_selection_methods_comparison.csv")

print("\n✅ Universe selection criteria test complete!")
