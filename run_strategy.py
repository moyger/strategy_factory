#!/usr/bin/env python3
"""
London Breakout v3 - Main Entry Point

Quick start:
    python run_strategy.py              # Run backtest
    python run_strategy.py --report     # Generate full report
"""
import sys
from pathlib import Path

# Add subdirectories to path
sys.path.insert(0, str(Path(__file__).parent / 'core'))
sys.path.insert(0, str(Path(__file__).parent / 'strategies'))
sys.path.insert(0, str(Path(__file__).parent / 'backtests'))

from strategies.strategy_breakout_v3 import LondonBreakoutV3
from core.data_loader import ForexDataLoader
from backtests.backtest_report import BacktestReporter
import pandas as pd


def run_backtest():
    """Run the London Breakout v3 strategy backtest"""
    print("=" * 80)
    print("LONDON BREAKOUT v3.0 - ENHANCED TRAILING STOP")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    # Filter to 2020+
    h1_df = h1_df[h1_df.index >= '2020-01-01']
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print(f"\nTesting period: {h1_df.index.min()} to {h1_df.index.max()}")
    print(f"H1 bars: {len(h1_df):,}")
    print(f"H4 bars: {len(h4_df):,}\n")

    # Run backtest
    strategy = LondonBreakoutV3()
    trades = strategy.backtest(h1_df, h4_df)

    if len(trades) == 0:
        print("❌ No trades generated")
        return None, None

    # Print results
    print(f"Total trades: {len(trades)}")
    wins = trades[trades['pnl_dollars'] > 0]
    losses = trades[trades['pnl_dollars'] <= 0]

    print(f"\nPerformance:")
    print(f"  Wins: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"  Losses: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")
    print(f"  Total P&L: ${trades['pnl_dollars'].sum():,.2f}")
    print(f"  Avg P&L: ${trades['pnl_dollars'].mean():.2f}")

    if len(wins) > 0 and len(losses) > 0:
        profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())
        print(f"  Profit Factor: {profit_factor:.2f}")

    # Annualized
    days = (h1_df.index.max() - h1_df.index.min()).days
    years = days / 365.25
    print(f"\nAnnualized:")
    print(f"  Trades/Year: {len(trades)/years:.1f}")
    print(f"  P&L/Year: ${trades['pnl_dollars'].sum()/years:,.2f}")

    print("\n" + "=" * 80)

    return trades, h1_df


def generate_report(trades, h1_df):
    """Generate full backtest report"""
    print("\nGenerating comprehensive report...")

    # Create equity curve
    equity_curve = []
    equity = 100000

    for idx, trade in trades.iterrows():
        equity += trade['pnl_dollars']
        equity_curve.append({
            'timestamp': trade['exit_time'],
            'equity': equity
        })

    equity_df = pd.DataFrame(equity_curve)

    # Generate report
    reporter = BacktestReporter(
        trades_df=trades,
        equity_curve_df=equity_df,
        initial_equity=100000
    )

    reporter.generate_full_report()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='London Breakout v3 Strategy')
    parser.add_argument('--report', action='store_true',
                       help='Generate full HTML report with charts')
    args = parser.parse_args()

    # Run backtest
    trades, h1_df = run_backtest()

    # Generate report if requested
    if trades is not None and args.report:
        generate_report(trades, h1_df)
        print("\n✅ Open output/london_breakout/tearsheet.html to view full report")
