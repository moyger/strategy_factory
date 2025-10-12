"""
Analyze leverage risk for crypto strategy

Shows:
1. Maximum drawdown with different leverage levels
2. Liquidation risk analysis
3. Volatility impact on leveraged positions
4. Safe vs unsafe leverage levels
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

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

# Calculate daily returns
daily_returns = prices.pct_change()

# Simulate strategy portfolio
# Use equal-weight simplification for risk analysis
# Exclude USDT (bear asset)
crypto_prices = prices.drop(columns=['USDT'], errors='ignore')
portfolio_returns = crypto_prices.pct_change().mean(axis=1)  # Equal weight avg

# Calculate cumulative returns
cumulative_returns = (1 + portfolio_returns).cumprod()

# Calculate drawdowns (no leverage)
running_max = cumulative_returns.expanding().max()
drawdown = (cumulative_returns - running_max) / running_max * 100

# Find worst drawdown periods
max_dd = drawdown.min()
max_dd_date = drawdown.idxmin()

print(f"{'='*70}")
print(f"LEVERAGE RISK ANALYSIS - CRYPTO STRATEGY")
print(f"{'='*70}")
print(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
print(f"Strategy: Monthly ROC, No Regime Filter (always invested)\n")

print(f"{'='*70}")
print(f"BASELINE (NO LEVERAGE) PERFORMANCE")
print(f"{'='*70}\n")

total_return = (cumulative_returns.iloc[-1] - 1) * 100
print(f"Total Return:    {total_return:>8.2f}%")
print(f"Max Drawdown:    {max_dd:>8.2f}%")
print(f"Worst DD Date:   {max_dd_date.date()}")

# Calculate volatility
annual_volatility = portfolio_returns.std() * np.sqrt(365) * 100
print(f"Annual Volatility: {annual_volatility:>6.2f}%")

# Find worst single day
worst_day = portfolio_returns.min() * 100
worst_day_date = portfolio_returns.idxmin()
print(f"Worst Single Day: {worst_day:>7.2f}% on {worst_day_date.date()}")

# Find worst week
worst_week = portfolio_returns.rolling(7).sum().min() * 100
worst_week_date = portfolio_returns.rolling(7).sum().idxmin()
print(f"Worst Week:       {worst_week:>7.2f}% ending {worst_week_date.date()}")

# Find worst month
worst_month = portfolio_returns.rolling(30).sum().min() * 100
worst_month_date = portfolio_returns.rolling(30).sum().idxmin()
print(f"Worst Month:      {worst_month:>7.2f}% ending {worst_month_date.date()}")

print(f"\n{'='*70}")
print(f"LEVERAGE SCENARIO ANALYSIS")
print(f"{'='*70}\n")

leverage_levels = [1, 2, 3, 4, 5, 10]

print(f"{'Leverage':<10} {'Total Return':<15} {'Max Drawdown':<15} {'Liquidation Risk':<20}")
print(f"{'-'*70}")

for leverage in leverage_levels:
    # Leveraged returns
    leveraged_returns = portfolio_returns * leverage
    leveraged_cumulative = (1 + leveraged_returns).cumprod()

    # Leveraged drawdown
    leveraged_running_max = leveraged_cumulative.expanding().max()
    leveraged_dd = (leveraged_cumulative - leveraged_running_max) / leveraged_running_max * 100
    leveraged_max_dd = leveraged_dd.min()

    # Total return
    leveraged_total_return = (leveraged_cumulative.iloc[-1] - 1) * 100

    # Liquidation risk (assuming exchange liquidates at -50% equity for isolated margin)
    # For cross margin, typically -80% to -90%
    liquidation_threshold = -50  # Typical for isolated margin
    equity_loss = leveraged_max_dd

    if equity_loss <= liquidation_threshold:
        risk = "❌ LIQUIDATED"
    elif equity_loss <= liquidation_threshold * 0.8:  # Within 20% of liquidation
        risk = "🔴 EXTREME RISK"
    elif equity_loss <= liquidation_threshold * 0.6:
        risk = "🟠 HIGH RISK"
    elif equity_loss <= liquidation_threshold * 0.4:
        risk = "🟡 MODERATE RISK"
    else:
        risk = "🟢 LOW RISK"

    print(f"{leverage}x{'':<8} {leveraged_total_return:>12.2f}% {leveraged_max_dd:>13.2f}% {risk:<20}")

print(f"\n{'='*70}")
print(f"DETAILED LEVERAGE SCENARIOS")
print(f"{'='*70}\n")

# Scenario 1: 2x Leverage
print(f"📊 2x LEVERAGE SCENARIO:")
print(f"   Total Return:     {total_return * 2:>8.2f}%")
print(f"   Max Drawdown:     {max_dd * 2:>8.2f}%")
print(f"   Liquidation at:   -50% (typical isolated margin)")
print(f"   Your max loss:    {max_dd * 2:>8.2f}%")
print(f"   Safety margin:    {-50 - (max_dd * 2):>8.2f}%")
if max_dd * 2 < -50:
    print(f"   ❌ WOULD LIQUIDATE - Your account blown!")
else:
    print(f"   ✅ SAFE - Would survive worst drawdown")

# Scenario 2: 3x Leverage
print(f"\n📊 3x LEVERAGE SCENARIO:")
print(f"   Total Return:     {total_return * 3:>8.2f}%")
print(f"   Max Drawdown:     {max_dd * 3:>8.2f}%")
print(f"   Liquidation at:   -50% (typical isolated margin)")
print(f"   Your max loss:    {max_dd * 3:>8.2f}%")
print(f"   Safety margin:    {-50 - (max_dd * 3):>8.2f}%")
if max_dd * 3 < -50:
    print(f"   ❌ WOULD LIQUIDATE - Your account blown!")
else:
    print(f"   ✅ SAFE - Would survive worst drawdown")

# Scenario 3: 5x Leverage
print(f"\n📊 5x LEVERAGE SCENARIO:")
print(f"   Total Return:     {total_return * 5:>8.2f}%")
print(f"   Max Drawdown:     {max_dd * 5:>8.2f}%")
print(f"   Liquidation at:   -50% (typical isolated margin)")
print(f"   Your max loss:    {max_dd * 5:>8.2f}%")
print(f"   Safety margin:    {-50 - (max_dd * 5):>8.2f}%")
if max_dd * 5 < -50:
    print(f"   ❌ WOULD LIQUIDATE - Your account blown!")
else:
    print(f"   ✅ SAFE - Would survive worst drawdown")

print(f"\n{'='*70}")
print(f"INTRADAY VOLATILITY RISK (CRITICAL FOR LEVERAGE)")
print(f"{'='*70}\n")

# Daily volatility analysis
daily_vol = portfolio_returns.std() * 100
worst_days = portfolio_returns.nsmallest(10) * 100

print(f"Average Daily Move: ±{daily_vol:.2f}%")
print(f"\n10 Worst Single Days (could trigger liquidation with high leverage):")
print(f"{'Date':<15} {'Loss':<10} {'2x Impact':<12} {'3x Impact':<12} {'5x Impact':<12}")
print(f"{'-'*70}")

for date, loss in worst_days.items():
    impact_2x = loss * 2
    impact_3x = loss * 3
    impact_5x = loss * 5

    print(f"{str(date.date()):<15} {loss:>7.2f}% {impact_2x:>10.2f}% {impact_3x:>10.2f}% {impact_5x:>10.2f}%")

print(f"\n{'='*70}")
print(f"LIQUIDATION PROBABILITY ANALYSIS")
print(f"{'='*70}\n")

# Calculate probability of hitting liquidation threshold
for leverage in [2, 3, 5]:
    liquidation_threshold = -50 / leverage  # Threshold in terms of unleveraged loss

    # How many days would have triggered liquidation?
    liquidation_days = (portfolio_returns * leverage * 100 <= -50).sum()
    total_days = len(portfolio_returns)
    probability = (liquidation_days / total_days) * 100

    print(f"{leverage}x Leverage:")
    print(f"   Liquidation threshold: {liquidation_threshold:.2f}% daily loss (unleveraged)")
    print(f"   Days that would liquidate: {liquidation_days}/{total_days}")
    print(f"   Probability: {probability:.2f}%")

    if probability > 0:
        print(f"   ❌ UNSAFE - Already had {liquidation_days} liquidation events in backtest!")
    else:
        print(f"   ✅ SAFE - No single-day liquidations in historical data")
    print()

print(f"{'='*70}")
print(f"RECOMMENDATIONS")
print(f"{'='*70}\n")

# Calculate safe leverage
safe_leverage = abs(50 / max_dd)  # Leverage that keeps max DD at -50%

print(f"Based on historical max drawdown of {max_dd:.2f}%:\n")

print(f"❌ UNSAFE LEVERAGE LEVELS:")
if safe_leverage < 2:
    print(f"   2x leverage: Max DD = {max_dd * 2:.2f}% (LIQUIDATION RISK)")
if safe_leverage < 3:
    print(f"   3x leverage: Max DD = {max_dd * 3:.2f}% (LIQUIDATION RISK)")
if safe_leverage < 5:
    print(f"   5x leverage: Max DD = {max_dd * 5:.2f}% (LIQUIDATION RISK)")

print(f"\n✅ MAXIMUM SAFE LEVERAGE:")
print(f"   {safe_leverage:.1f}x leverage")
print(f"   This keeps max DD at ~-50% (liquidation threshold)")

print(f"\n🟢 CONSERVATIVE RECOMMENDATION:")
conservative_leverage = safe_leverage * 0.5  # 50% safety margin
print(f"   {conservative_leverage:.1f}x leverage")
print(f"   Provides 50% safety margin for unexpected volatility")

print(f"\n💡 PRACTICAL ADVICE:")
print(f"   • For crypto momentum strategies, leverage amplifies both gains AND losses")
print(f"   • Historical max DD was {max_dd:.2f}%, but crypto can go -50% in weeks")
print(f"   • Single-day -10% to -20% crashes happen (Black Swan events)")
print(f"   • Use cross margin (liquidation at -80-90%) instead of isolated (-50%)")
print(f"   • NEVER go above 2x leverage for crypto momentum strategies")
print(f"   • Consider NO leverage - {total_return:.2f}% return is already excellent!")

print(f"\n{'='*70}\n")
