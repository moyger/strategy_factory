#!/usr/bin/env python3
"""
Example: Strategy with ATR-based Trailing Stops

This example shows how to use ATR (Average True Range) for dynamic stops
and take profit levels that adapt to market volatility.

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from strategies.atr_trailing_stop_strategy import ATRTrailingStopStrategy


def main():
    print("="*80)
    print("EXAMPLE: STRATEGY WITH ATR TRAILING STOPS")
    print("="*80)

    # Step 1: Load data
    print("\n📂 Loading data...")
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use last 50k bars
    df = df.tail(50000)

    print(f"✅ Loaded {len(df):,} bars")

    # Step 2: Create strategy with ATR-based risk management
    print("\n📊 Creating ATR trailing stop strategy...")
    strategy = ATRTrailingStopStrategy(
        atr_period=14,           # ATR calculation period
        atr_sl_multiplier=2.0,   # Stop loss = 2x ATR
        atr_tp_multiplier=4.0,   # Take profit = 4x ATR (2:1 R/R)
        risk_percent=1.0         # Risk 1% per trade
    )

    print(f"   Strategy: {strategy}")
    print(f"\n   Key Features:")
    print(f"   ✓ Dynamic stops based on volatility (ATR)")
    print(f"   ✓ Trailing stops to protect profits")
    print(f"   ✓ Position sizing based on risk percent")
    print(f"   ✓ 2:1 reward/risk ratio")

    # Step 3: Run backtest
    print("\n📈 Running backtest...")
    portfolio = strategy.backtest(df, initial_capital=10000)

    # Step 4: Print results
    strategy.print_results(portfolio)

    # Optional: Generate QuantStats report
    print("\n💡 Want a detailed report? Run:")
    print(f"   python run_strategy.py --strategy atr_trailing_stop --report")

    print("\n" + "="*80)
    print("✅ Example completed!")
    print("\nKey Takeaways:")
    print("   - ATR adapts to market volatility automatically")
    print("   - Trailing stops protect profits in trending markets")
    print("   - Risk % keeps position sizing consistent")
    print("   - 2:1 R/R means you only need 33%+ win rate to profit")
    print("\nTry adjusting:")
    print("   - atr_sl_multiplier (tighter/wider stops)")
    print("   - atr_tp_multiplier (adjust risk/reward)")
    print("   - risk_percent (more/less aggressive)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
