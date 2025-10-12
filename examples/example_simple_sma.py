#!/usr/bin/env python3
"""
Example: Simple SMA Crossover Strategy

This is the simplest possible example - a basic moving average crossover.

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import vectorbt as vbt
from strategies.sma_crossover import SMAStrategy


def main():
    print("="*80)
    print("EXAMPLE: SIMPLE SMA CROSSOVER STRATEGY")
    print("="*80)

    # Step 1: Load data
    print("\n📂 Loading data...")
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use last 50k bars for speed
    df = df.tail(50000)

    print(f"✅ Loaded {len(df):,} bars")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    # Step 2: Create strategy
    print("\n📊 Creating SMA crossover strategy...")
    strategy = SMAStrategy(
        fast_period=10,  # Fast moving average
        slow_period=50   # Slow moving average
    )

    print(f"   Strategy: {strategy}")

    # Step 3: Generate signals
    print("\n🔍 Generating trading signals...")
    df_signals = strategy.generate_signals(df)

    buy_signals = (df_signals['signal'] == 'BUY').sum()
    sell_signals = (df_signals['signal'] == 'SELL').sum()

    print(f"   Buy signals: {buy_signals}")
    print(f"   Sell signals: {sell_signals}")

    # Step 4: Run backtest
    print("\n📈 Running backtest...")

    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001,      # 0.1% trading fee
        slippage=0.0005  # 0.05% slippage
    )

    # Step 5: Print results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    print(f"\n📈 Performance:")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
    print(f"   Final Equity: ${portfolio.value().iloc[-1]:,.2f}")
    print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
    print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")

    print(f"\n💼 Trades:")
    print(f"   Number of Trades: {portfolio.trades.count()}")

    if portfolio.trades.count() > 0:
        print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
        print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
        print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
        print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")
        print(f"   Best Trade: ${portfolio.trades.pnl.max():.2f}")
        print(f"   Worst Trade: ${portfolio.trades.pnl.min():.2f}")

    print("\n" + "="*80)
    print("✅ Example completed!")
    print("\nTry modifying the parameters:")
    print("   - Change fast_period and slow_period")
    print("   - Try different data files")
    print("   - Adjust fees and slippage")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
