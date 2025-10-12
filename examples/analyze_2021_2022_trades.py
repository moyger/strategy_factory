"""
Analyze what happened during 2021-2022 bear market

Why did we lose money if PAXG was supposed to protect us?
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import strategy
spec = importlib.util.spec_from_file_location(
    "institutional_crypto_perp",
    Path(__file__).parent.parent / "strategies" / "05_institutional_crypto_perp.py"
)
crypto_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crypto_module)
InstitutionalCryptoPerp = crypto_module.InstitutionalCryptoPerp
MarketRegime = crypto_module.MarketRegime
Position = crypto_module.Position

CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD'
]


def download_data(symbols, start_date, end_date):
    """Download data for specific period"""
    print(f"\n📥 Downloading data from {start_date} to {end_date}...")

    data = yf.download(
        symbols,
        start=start_date,
        end=end_date,
        interval="1d",
        progress=False,
        group_by='ticker' if len(symbols) > 1 else None
    )

    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
            else:
                close_prices[symbol] = data[symbol]['Close']
                high_prices[symbol] = data[symbol]['High']
                low_prices[symbol] = data[symbol]['Low']
        except:
            continue

    close_prices = close_prices.dropna(axis=1, how='all').ffill(limit=3)
    high_prices = high_prices.dropna(axis=1, how='all').ffill(limit=3)
    low_prices = low_prices.dropna(axis=1, how='all').ffill(limit=3)

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices
    }


def analyze_bear_period():
    """Analyze 2021-2022 period in detail"""
    print("="*80)
    print("ANALYZING 2021-2022 BEAR MARKET PERIOD")
    print("="*80)

    # Download data including PAXG
    symbols = CRYPTO_UNIVERSE + ['PAXG-USD']
    all_data = download_data(symbols, start_date='2020-10-01', end_date='2023-01-01')

    paxg_prices = all_data['close']['PAXG-USD']
    btc_prices = all_data['close']['BTC-USD']

    trading_data = {
        'close': all_data['close'].drop('PAXG-USD', axis=1),
        'high': all_data['high'].drop('PAXG-USD', axis=1),
        'low': all_data['low'].drop('PAXG-USD', axis=1)
    }

    # Initialize strategy
    strategy = InstitutionalCryptoPerp(
        bear_market_asset='PAXG-USD',
        bear_allocation=1.0
    )

    # Calculate regime
    regime = strategy.calculate_regime(btc_prices)

    print("\n📊 REGIME ANALYSIS (2020-2023)")
    print("="*80)

    regime_counts = regime.value_counts()
    print("\nRegime Distribution:")
    for regime_name, count in regime_counts.items():
        pct = count / len(regime) * 100
        print(f"  {regime_name:20s}: {count:4d} days ({pct:5.1f}%)")

    # Check when BTC crossed 200MA
    print("\n📉 BTC vs 200MA Analysis:")
    print("="*80)

    btc_ma200 = btc_prices.rolling(200).mean()

    bear_transitions = []
    for i in range(1, len(btc_prices)):
        date = btc_prices.index[i]
        prev_date = btc_prices.index[i-1]

        if date not in regime.index or prev_date not in regime.index:
            continue

        curr_regime = regime.loc[date]
        prev_regime = regime.loc[prev_date]

        # Detect regime changes
        if curr_regime != prev_regime:
            btc_price = btc_prices.iloc[i]
            ma200 = btc_ma200.iloc[i] if not pd.isna(btc_ma200.iloc[i]) else 0

            bear_transitions.append({
                'date': date,
                'from': prev_regime,
                'to': curr_regime,
                'btc_price': btc_price,
                'ma200': ma200
            })

    print(f"\nFound {len(bear_transitions)} regime transitions")
    print("\nRegime Transitions:")
    print(f"{'Date':<12} {'From':<20} {'To':<20} {'BTC Price':>12} {'200MA':>12}")
    print("-"*90)

    for trans in bear_transitions[:20]:  # First 20 transitions
        print(f"{trans['date'].strftime('%Y-%m-%d'):<12} "
              f"{trans['from']:<20} {trans['to']:<20} "
              f"${trans['btc_price']:>11,.0f} ${trans['ma200']:>11,.0f}")

    # Analyze PAXG performance during bear periods
    print("\n💰 PAXG Performance Analysis:")
    print("="*80)

    # Get bear periods
    bear_dates = regime[regime == MarketRegime.BEAR_RISK_OFF.value].index

    if len(bear_dates) > 0:
        first_bear = bear_dates[0]
        last_bear = bear_dates[-1]

        print(f"\nBear regime periods: {first_bear.strftime('%Y-%m-%d')} to {last_bear.strftime('%Y-%m-%d')}")
        print(f"Total bear days: {len(bear_dates)}")

        # PAXG price during bear period
        paxg_bear_start = paxg_prices.loc[first_bear] if first_bear in paxg_prices.index else None
        paxg_bear_end = paxg_prices.loc[last_bear] if last_bear in paxg_prices.index else None

        if paxg_bear_start and paxg_bear_end:
            paxg_return = (paxg_bear_end / paxg_bear_start - 1) * 100
            print(f"\nPAXG Price:")
            print(f"  Start: ${paxg_bear_start:,.2f}")
            print(f"  End:   ${paxg_bear_end:,.2f}")
            print(f"  Return: {paxg_return:+.2f}%")

        # BTC price during same period
        btc_bear_start = btc_prices.loc[first_bear]
        btc_bear_end = btc_prices.loc[last_bear]
        btc_return = (btc_bear_end / btc_bear_start - 1) * 100

        print(f"\nBTC Price (for comparison):")
        print(f"  Start: ${btc_bear_start:,.0f}")
        print(f"  End:   ${btc_bear_end:,.0f}")
        print(f"  Return: {btc_return:+.2f}%")

    # Check specific problem periods
    print("\n🔍 DETAILED ANALYSIS: Why did we lose money?")
    print("="*80)

    # Check late 2020 - early 2021
    print("\nLate 2020 - Early 2021 (Initial losses):")
    period1 = regime['2020-10':'2021-02']
    print(f"  Regime distribution:")
    for regime_name, count in period1.value_counts().items():
        print(f"    {regime_name}: {count} days")

    # Check if we were in crypto during the top
    print("\n  BTC Price Action:")
    btc_period1 = btc_prices['2020-10':'2021-02']
    print(f"    Oct 2020: ${btc_period1.iloc[0]:,.0f}")
    print(f"    Feb 2021: ${btc_period1.iloc[-1]:,.0f}")
    print(f"    Return: {(btc_period1.iloc[-1] / btc_period1.iloc[0] - 1) * 100:+.2f}%")

    print("\n❗ HYPOTHESIS: We likely entered crypto positions during the mania")
    print("   and got stopped out when BTC crashed in Feb-Jun 2021")

    # Check mid 2021 crash
    print("\nMid 2021 (Crash period):")
    period2 = regime['2021-03':'2021-08']
    print(f"  Regime distribution:")
    for regime_name, count in period2.value_counts().items():
        print(f"    {regime_name}: {count} days")

    btc_period2 = btc_prices['2021-03':'2021-08']
    print(f"\n  BTC Price Action:")
    print(f"    Mar 2021: ${btc_period2.iloc[0]:,.0f}")
    print(f"    Aug 2021: ${btc_period2.iloc[-1]:,.0f}")
    print(f"    Return: {(btc_period2.iloc[-1] / btc_period2.iloc[0] - 1) * 100:+.2f}%")

    # Check 2022 bear market
    print("\n2022 (Full bear market):")
    period3 = regime['2022-01':'2022-12']
    print(f"  Regime distribution:")
    for regime_name, count in period3.value_counts().items():
        print(f"    {regime_name}: {count} days")

    btc_period3 = btc_prices['2022-01':'2022-12']
    print(f"\n  BTC Price Action:")
    print(f"    Jan 2022: ${btc_period3.iloc[0]:,.0f}")
    print(f"    Dec 2022: ${btc_period3.iloc[-1]:,.0f}")
    print(f"    Return: {(btc_period3.iloc[-1] / btc_period3.iloc[0] - 1) * 100:+.2f}%")


def main():
    analyze_bear_period()


if __name__ == "__main__":
    main()
