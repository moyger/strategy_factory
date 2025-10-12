"""
Debug why institutional strategy isn't entering trades
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from strategies.institutional_crypto_perp_strategy import (
    InstitutionalCryptoPerp, MarketRegime
)


# Test with just a few cryptos
TEST_CRYPTOS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD']


def main():
    print("🔍 Debugging institutional strategy entry signals\n")

    # Download 2 years of data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

    print(f"📥 Downloading data ({start_date} to {end_date})...")

    close = pd.DataFrame()
    high = pd.DataFrame()
    low = pd.DataFrame()

    # Download each symbol individually
    for symbol in TEST_CRYPTOS:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty:
                close[symbol] = data['Close']
                high[symbol] = data['High']
                low[symbol] = data['Low']
        except Exception as e:
            print(f"   ⚠️  Failed: {symbol} - {e}")

    close = close.fillna(method='ffill')
    high = high.fillna(method='ffill')
    low = low.fillna(method='ffill')

    print(f"   ✅ Downloaded {len(close.columns)} pairs, {len(close)} days\n")

    # Initialize strategy
    strategy = InstitutionalCryptoPerp()

    # Get BTC prices
    btc_prices = close['BTC-USD']

    # Calculate regime
    print("📈 Calculating regime...")
    regime = strategy.calculate_regime(btc_prices)

    regime_counts = regime.value_counts()
    print(f"   BULL_RISK_ON: {regime_counts.get(MarketRegime.BULL_RISK_ON.value, 0)} days ({regime_counts.get(MarketRegime.BULL_RISK_ON.value, 0)/len(regime)*100:.1f}%)")
    print(f"   NEUTRAL: {regime_counts.get(MarketRegime.NEUTRAL.value, 0)} days ({regime_counts.get(MarketRegime.NEUTRAL.value, 0)/len(regime)*100:.1f}%)")
    print(f"   BEAR_RISK_OFF: {regime_counts.get(MarketRegime.BEAR_RISK_OFF.value, 0)} days ({regime_counts.get(MarketRegime.BEAR_RISK_OFF.value, 0)/len(regime)*100:.1f}%)\n")

    # Find BULL_RISK_ON periods
    bull_periods = regime[regime == MarketRegime.BULL_RISK_ON.value]

    if len(bull_periods) == 0:
        print("❌ NO BULL_RISK_ON PERIODS FOUND!")
        print("   The regime filter is too restrictive.\n")
        return

    print(f"✅ Found {len(bull_periods)} BULL_RISK_ON days\n")

    # Check conditions on a specific BULL day
    test_date = bull_periods.index[len(bull_periods)//2]  # Middle of bull period
    print(f"📅 Testing conditions on {test_date.strftime('%Y-%m-%d')} (BULL_RISK_ON):\n")

    # Calculate indicators
    donchian_high, _ = strategy.calculate_donchian(high)
    adx = strategy.calculate_adx(high, low, close)
    rs = strategy.calculate_relative_strength(close, btc_prices)

    for symbol in close.columns:
        if test_date not in close.index:
            continue

        print(f"   {symbol}:")

        # 1. Donchian breakout
        current_price = close.loc[test_date, symbol]
        donchian_level = donchian_high.shift(1).loc[test_date, symbol]
        breakout = current_price > donchian_level if not pd.isna(donchian_level) else False

        print(f"      Price: ${current_price:,.2f}")
        print(f"      Donchian 20-day high: ${donchian_level:,.2f}")
        print(f"      Breakout: {'✅ YES' if breakout else '❌ NO'}")

        # 2. ADX
        current_adx = adx.loc[test_date, symbol] if test_date in adx.index else np.nan
        adx_ok = current_adx >= strategy.adx_threshold if not pd.isna(current_adx) else False

        print(f"      ADX: {current_adx:.1f} (need >{strategy.adx_threshold})")
        print(f"      ADX OK: {'✅ YES' if adx_ok else '❌ NO'}")

        # 3. Relative strength
        rs_scores = rs.loc[test_date].dropna() if test_date in rs.index else pd.Series()
        if len(rs_scores) > 0 and symbol in rs_scores.index:
            rs_threshold = rs_scores.quantile(strategy.rs_quartile)
            rs_qualified = rs_scores[symbol] >= rs_threshold

            print(f"      RS vs BTC: {rs_scores[symbol]:.2f} (threshold: {rs_threshold:.2f})")
            print(f"      RS OK: {'✅ YES' if rs_qualified else '❌ NO'}")
        else:
            print(f"      RS: ⚠️ N/A")

        print()

    # Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSIS:")
    print("="*60)

    # Check if ANY day would qualify
    entry_signals = 0

    for date in bull_periods.index[:100]:  # Check first 100 bull days
        for symbol in close.columns:
            has_signal = strategy.check_entry_signal(
                symbol, date, close, high, low, close, btc_prices,
                MarketRegime.BULL_RISK_ON.value
            )
            if has_signal:
                entry_signals += 1

    print(f"\n✅ Found {entry_signals} entry signals in first 100 BULL days")

    if entry_signals == 0:
        print("\n❌ PROBLEM IDENTIFIED:")
        print("   The entry conditions are TOO RESTRICTIVE.")
        print("   Likely issues:")
        print("   1. ADX threshold (25) too high for crypto")
        print("   2. RS quartile (0.75) excludes most coins")
        print("   3. All 3 conditions rarely align simultaneously")
        print("\n💡 SOLUTION:")
        print("   Lower ADX threshold to 20")
        print("   Lower RS quartile to 0.50 (top half)")
        print("   Or make regime filter less strict")


if __name__ == '__main__':
    main()
