"""
Backtest: London Breakout v4.1 on XAUUSD (Gold)
Test the strategy on Gold to see if the logic translates across instruments
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from strategies.strategy_breakout_v4_1_xauusd import LondonBreakoutV41XAUUSD

# Load XAUUSD data
print("Loading XAUUSD data...")
df_h1 = pd.read_csv('data/forex/XAUUSD/XAUUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h4 = pd.read_csv('data/forex/XAUUSD/XAUUSD_4H.csv', parse_dates=['Datetime'], index_col='Datetime')

print(f"H1 Data: {df_h1.index[0]} to {df_h1.index[-1]} ({len(df_h1)} bars)")
print(f"H4 Data: {df_h4.index[0]} to {df_h4.index[-1]} ({len(df_h4)} bars)")

# Use only recent data for faster testing
df_h1 = df_h1[df_h1.index >= '2022-01-01']
df_h4 = df_h4[df_h4.index >= '2022-01-01']

# Split into training and test periods
split_date = '2024-01-01'
train_h1 = df_h1[df_h1.index < split_date]
train_h4 = df_h4[df_h4.index < split_date]
test_h1 = df_h1[df_h1.index >= split_date]
test_h4 = df_h4[df_h4.index >= split_date]

print(f"\nTraining: {train_h1.index[0]} to {train_h1.index[-1]}")
print(f"Testing:  {test_h1.index[0]} to {test_h1.index[-1]}")

# Test multiple risk levels
risk_levels = [1.0, 1.5]

print("\n" + "="*80)
print("XAUUSD BACKTEST RESULTS - London Breakout v4.1")
print("="*80)

for risk in risk_levels:
    print(f"\n{'='*80}")
    print(f"RISK LEVEL: {risk}%")
    print(f"{'='*80}")

    # Full period backtest
    print("\n[FULL PERIOD: 2022-2025]")
    strategy_full = LondonBreakoutV41XAUUSD(
        pair='XAUUSD',
        risk_percent=risk,
        initial_capital=100000,
        enable_asia_breakout=True,
        enable_triangle_breakout=True
    )
    trades_full, equity_full = strategy_full.run(df_h1.copy(), df_h4.copy())

    if len(trades_full) > 0:
        wins = trades_full[trades_full['pnl'] > 0]
        losses = trades_full[trades_full['pnl'] <= 0]

        total_pnl = trades_full['pnl'].sum()
        win_rate = len(wins) / len(trades_full) * 100
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf')

        # Max drawdown
        equity_full['peak'] = equity_full['equity'].cummax()
        equity_full['drawdown'] = (equity_full['equity'] - equity_full['peak']) / equity_full['peak'] * 100
        max_dd = equity_full['drawdown'].min()

        # Annual return
        years = (df_h1.index[-1] - df_h1.index[0]).days / 365.25
        annual_pnl = total_pnl / years

        print(f"  Trades: {len(trades_full)}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total P&L: ${total_pnl:,.0f}")
        print(f"  Annual P&L: ${annual_pnl:,.0f}")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Avg Win: ${avg_win:,.0f} | Avg Loss: ${avg_loss:,.0f}")
        print(f"  Max Drawdown: {max_dd:.2f}%")

        # Strategy breakdown
        asia_trades = trades_full[trades_full['type'] == 'ASIA_BREAKOUT']
        triangle_trades = trades_full[trades_full['type'] == 'TRIANGLE_BREAKOUT']

        if len(asia_trades) > 0:
            asia_pnl = asia_trades['pnl'].sum()
            asia_wr = len(asia_trades[asia_trades['pnl'] > 0]) / len(asia_trades) * 100
            print(f"\n  Asia Breakout: {len(asia_trades)} trades | WR: {asia_wr:.1f}% | P&L: ${asia_pnl:,.0f} ({asia_pnl/total_pnl*100:.1f}%)")

        if len(triangle_trades) > 0:
            tri_pnl = triangle_trades['pnl'].sum()
            tri_wr = len(triangle_trades[triangle_trades['pnl'] > 0]) / len(triangle_trades) * 100
            print(f"  Triangle: {len(triangle_trades)} trades | WR: {tri_wr:.1f}% | P&L: ${tri_pnl:,.0f} ({tri_pnl/total_pnl*100:.1f}%)")
    else:
        print("  No trades generated")

    # Test period (OOS)
    print("\n[TEST PERIOD (OOS): 2024-2025]")
    strategy_test = LondonBreakoutV41XAUUSD(
        pair='XAUUSD',
        risk_percent=risk,
        initial_capital=100000,
        enable_asia_breakout=True,
        enable_triangle_breakout=True
    )
    trades_test, equity_test = strategy_test.run(test_h1.copy(), test_h4.copy())

    if len(trades_test) > 0:
        wins = trades_test[trades_test['pnl'] > 0]
        losses = trades_test[trades_test['pnl'] <= 0]

        total_pnl = trades_test['pnl'].sum()
        win_rate = len(wins) / len(trades_test) * 100
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else float('inf')

        # Max drawdown
        equity_test['peak'] = equity_test['equity'].cummax()
        equity_test['drawdown'] = (equity_test['equity'] - equity_test['peak']) / equity_test['peak'] * 100
        max_dd = equity_test['drawdown'].min()

        # Annual return
        years = (test_h1.index[-1] - test_h1.index[0]).days / 365.25
        annual_pnl = total_pnl / years

        print(f"  Trades: {len(trades_test)}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total P&L: ${total_pnl:,.0f}")
        print(f"  Annual P&L: ${annual_pnl:,.0f}")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Avg Win: ${avg_win:,.0f} | Avg Loss: ${avg_loss:,.0f}")
        print(f"  Max Drawdown: {max_dd:.2f}%")

        # FTMO check
        ftmo_compliant = max_dd >= -10.0
        ftmo_status = "✅ FTMO COMPLIANT" if ftmo_compliant else "❌ FTMO VIOLATION"
        print(f"\n  {ftmo_status}")
    else:
        print("  No trades generated")

print("\n" + "="*80)
print("BACKTEST COMPLETE")
print("="*80)
