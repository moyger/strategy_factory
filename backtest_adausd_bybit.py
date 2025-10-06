"""
Backtest: London Breakout v4.1 on ADAUSD for Bybit with 5x Leverage
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from strategies.strategy_breakout_v4_1_adausd_bybit import LondonBreakoutV41ADAUSDBybit

# Load ADAUSD data
print("Loading ADAUSD data...")
df_h1 = pd.read_csv('data/crypto/ADAUSD_1H.csv', parse_dates=['Datetime'], index_col='Datetime')
df_h4 = pd.read_csv('data/crypto/ADAUSD_4H.csv', parse_dates=['Datetime'], index_col='Datetime')

print(f"H1 Data: {df_h1.index[0]} to {df_h1.index[-1]} ({len(df_h1)} bars)")
print(f"H4 Data: {df_h4.index[0]} to {df_h4.index[-1]} ({len(df_h4)} bars)")

# Use recent data for testing
df_h1 = df_h1[df_h1.index >= '2023-01-01']
df_h4 = df_h4[df_h4.index >= '2023-01-01']

# Split into training and test periods
split_date = '2024-01-01'
train_h1 = df_h1[df_h1.index < split_date]
train_h4 = df_h4[df_h4.index < split_date]
test_h1 = df_h1[df_h1.index >= split_date]
test_h4 = df_h4[df_h4.index >= split_date]

print(f"\nTraining: {train_h1.index[0]} to {train_h1.index[-1]}")
print(f"Testing:  {test_h1.index[0]} to {test_h1.index[-1]}")

# Test multiple risk levels with 5x leverage
risk_levels = [1.0, 1.5, 2.0, 3.0]

print("\n" + "="*80)
print("ADAUSD BYBIT BACKTEST - 5x Leverage")
print("="*80)

for risk in risk_levels:
    print(f"\n{'='*80}")
    print(f"RISK LEVEL: {risk}% per trade | LEVERAGE: 5x")
    print(f"{'='*80}")

    # Full period backtest
    print("\n[FULL PERIOD: 2023-2025]")
    strategy_full = LondonBreakoutV41ADAUSDBybit(
        pair='ADAUSD',
        risk_percent=risk,
        initial_capital=100000,
        enable_asia_breakout=True,
        enable_triangle_breakout=True,
        leverage=5
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

        # Average % change and ROI
        avg_win_pct = wins['pct_change'].mean() if len(wins) > 0 else 0
        avg_loss_pct = losses['pct_change'].mean() if len(losses) > 0 else 0
        avg_win_roi = wins['roi_pct'].mean() if len(wins) > 0 else 0
        avg_loss_roi = losses['roi_pct'].mean() if len(losses) > 0 else 0

        # Max drawdown
        equity_full['peak'] = equity_full['equity'].cummax()
        equity_full['drawdown'] = (equity_full['equity'] - equity_full['peak']) / equity_full['peak'] * 100
        max_dd = equity_full['drawdown'].min()

        # Annual return
        years = (df_h1.index[-1] - df_h1.index[0]).days / 365.25
        annual_pnl = total_pnl / years
        annual_return_pct = (total_pnl / 100000) / years * 100

        # Total fees
        total_fees = trades_full['fees'].sum()

        print(f"  Trades: {len(trades_full)}")
        print(f"  Trades/Year: {len(trades_full)/years:.1f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total P&L: ${total_pnl:,.0f}")
        print(f"  Total Fees: ${total_fees:,.0f}")
        print(f"  Net P&L: ${total_pnl:,.0f}")
        print(f"  Annual Return: ${annual_pnl:,.0f} ({annual_return_pct:.1f}%)")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Avg Win: ${avg_win:,.0f} (Price: {avg_win_pct:.2f}%, ROI: {avg_win_roi:.1f}%)")
        print(f"  Avg Loss: ${avg_loss:,.0f} (Price: {avg_loss_pct:.2f}%, ROI: {avg_loss_roi:.1f}%)")
        print(f"  Max Drawdown: {max_dd:.2f}%")

        # Leverage metrics
        avg_margin = trades_full['margin'].mean()
        max_margin = trades_full['margin'].max()
        avg_position_size = trades_full['units'].mean()

        print(f"\n  Leverage Metrics:")
        print(f"    Avg Margin Used: ${avg_margin:,.0f} ({avg_margin/100000*100:.1f}% of capital)")
        print(f"    Max Margin Used: ${max_margin:,.0f} ({max_margin/100000*100:.1f}% of capital)")
        print(f"    Avg Position Size: {avg_position_size:,.0f} ADA")

        # Strategy breakdown
        asia_trades = trades_full[trades_full['type'] == 'ASIA_BREAKOUT']
        triangle_trades = trades_full[trades_full['type'] == 'TRIANGLE_BREAKOUT']

        if len(asia_trades) > 0:
            asia_pnl = asia_trades['pnl'].sum()
            asia_wr = len(asia_trades[asia_trades['pnl'] > 0]) / len(asia_trades) * 100
            print(f"\n  Asia Breakout: {len(asia_trades)} trades | WR: {asia_wr:.1f}% | P&L: ${asia_pnl:,.0f}")

        if len(triangle_trades) > 0:
            tri_pnl = triangle_trades['pnl'].sum()
            tri_wr = len(triangle_trades[triangle_trades['pnl'] > 0]) / len(triangle_trades) * 100
            print(f"  Triangle: {len(triangle_trades)} trades | WR: {tri_wr:.1f}% | P&L: ${tri_pnl:,.0f}")

        # Show recent trades
        print("\n  Recent trades (last 5):")
        for _, trade in trades_full.tail(5).iterrows():
            sign = "+" if trade['pnl'] > 0 else ""
            print(f"    {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} | {trade['direction']:5} | "
                  f"${trade['entry_price']:.4f} → ${trade['exit_price']:.4f} | "
                  f"Margin: ${trade['margin']:,.0f} | "
                  f"ROI: {sign}{trade['roi_pct']:.1f}% | P&L: {sign}${trade['pnl']:,.0f}")
    else:
        print("  No trades generated")

    # Test period (OOS)
    print("\n[TEST PERIOD (OOS): 2024-2025]")
    strategy_test = LondonBreakoutV41ADAUSDBybit(
        pair='ADAUSD',
        risk_percent=risk,
        initial_capital=100000,
        enable_asia_breakout=True,
        enable_triangle_breakout=True,
        leverage=5
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

        avg_win_roi = wins['roi_pct'].mean() if len(wins) > 0 else 0
        avg_loss_roi = losses['roi_pct'].mean() if len(losses) > 0 else 0

        # Max drawdown
        equity_test['peak'] = equity_test['equity'].cummax()
        equity_test['drawdown'] = (equity_test['equity'] - equity_test['peak']) / equity_test['peak'] * 100
        max_dd = equity_test['drawdown'].min()

        # Annual return
        years = (test_h1.index[-1] - test_h1.index[0]).days / 365.25
        annual_pnl = total_pnl / years
        annual_return_pct = (total_pnl / 100000) / years * 100

        total_fees = trades_test['fees'].sum()

        print(f"  Trades: {len(trades_test)}")
        print(f"  Trades/Year: {len(trades_test)/years:.1f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total P&L: ${total_pnl:,.0f}")
        print(f"  Total Fees: ${total_fees:,.0f}")
        print(f"  Annual Return: ${annual_pnl:,.0f} ({annual_return_pct:.1f}%)")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Avg Win ROI: {avg_win_roi:.1f}% | Avg Loss ROI: {avg_loss_roi:.1f}%")
        print(f"  Max Drawdown: {max_dd:.2f}%")

        # Risk assessment
        if max_dd >= -10.0:
            risk_status = "✅ LOW RISK"
        elif max_dd >= -20.0:
            risk_status = "⚠️  MODERATE RISK"
        else:
            risk_status = "❌ HIGH RISK"
        print(f"\n  {risk_status}")
    else:
        print("  No trades generated")

print("\n" + "="*80)
print("BYBIT 5x LEVERAGE BACKTEST COMPLETE")
print("="*80)
print("\nKey Features:")
print("- 5x leverage amplifies both gains and losses")
print("- Position size = Base size * 5")
print("- Margin required = Position value / 5")
print("- Fees: 0.055% taker fee on entry and exit")
print("- ROI shown is return on margin (not total capital)")
print("\nRecommendation: Start with 1-1.5% risk to maintain safety")
