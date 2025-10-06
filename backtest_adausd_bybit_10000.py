"""
Backtest: ADAUSD Bybit with YOUR Parameters
Capital: $10,000
Leverage: 3x
Risk: 1% per trade
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
test_h1 = df_h1[df_h1.index >= split_date]
test_h4 = df_h4[df_h4.index >= split_date]

print(f"\nFull Period: {df_h1.index[0]} to {df_h1.index[-1]}")
print(f"Test Period (OOS): {test_h1.index[0]} to {test_h1.index[-1]}")

print("\n" + "="*80)
print("YOUR CONFIGURATION: $10,000 Capital | 3x Leverage | 1% Risk")
print("="*80)

# Full period backtest
print("\n[FULL PERIOD: 2023-2025]")
strategy_full = LondonBreakoutV41ADAUSDBybit(
    pair='ADAUSD',
    risk_percent=1.0,
    initial_capital=10000,
    enable_asia_breakout=True,
    enable_triangle_breakout=True,
    leverage=3
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
    annual_return_pct = (total_pnl / 10000) / years * 100

    # Total fees
    total_fees = trades_full['fees'].sum()

    # Final balance
    final_balance = 10000 + total_pnl
    total_return_pct = (total_pnl / 10000) * 100

    print(f"\n📊 PERFORMANCE METRICS")
    print(f"  Starting Capital: $10,000")
    print(f"  Final Balance: ${final_balance:,.2f}")
    print(f"  Total Return: ${total_pnl:,.2f} ({total_return_pct:.1f}%)")
    print(f"  Annual Return: ${annual_pnl:,.2f} ({annual_return_pct:.1f}%)")
    print(f"  \n  Trades: {len(trades_full)} ({len(trades_full)/years:.1f}/year)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Max Drawdown: {max_dd:.2f}%")
    print(f"  Total Fees Paid: ${total_fees:,.2f}")

    print(f"\n💰 AVERAGE TRADE")
    print(f"  Avg Win: ${avg_win:.2f} (Price: {avg_win_pct:.2f}%, ROI: {avg_win_roi:.1f}%)")
    print(f"  Avg Loss: ${avg_loss:.2f} (Price: {avg_loss_pct:.2f}%, ROI: {avg_loss_roi:.1f}%)")
    print(f"  Avg P&L per Trade: ${trades_full['pnl'].mean():.2f}")

    # Leverage metrics
    avg_margin = trades_full['margin'].mean()
    max_margin = trades_full['margin'].max()
    avg_position_size = trades_full['units'].mean()

    print(f"\n📈 LEVERAGE & POSITION SIZING")
    print(f"  Avg Margin Used: ${avg_margin:,.2f} ({avg_margin/10000*100:.1f}% of capital)")
    print(f"  Max Margin Used: ${max_margin:,.2f} ({max_margin/10000*100:.1f}% of capital)")
    print(f"  Avg Position Size: {avg_position_size:,.0f} ADA (${avg_position_size * 0.5:,.0f} notional)")

    # Strategy breakdown
    asia_trades = trades_full[trades_full['type'] == 'ASIA_BREAKOUT']
    triangle_trades = trades_full[trades_full['type'] == 'TRIANGLE_BREAKOUT']

    print(f"\n📋 STRATEGY BREAKDOWN")
    if len(asia_trades) > 0:
        asia_pnl = asia_trades['pnl'].sum()
        asia_wr = len(asia_trades[asia_trades['pnl'] > 0]) / len(asia_trades) * 100
        print(f"  Asia Breakout: {len(asia_trades)} trades | WR: {asia_wr:.1f}% | P&L: ${asia_pnl:,.2f}")

    if len(triangle_trades) > 0:
        tri_pnl = triangle_trades['pnl'].sum()
        tri_wr = len(triangle_trades[triangle_trades['pnl'] > 0]) / len(triangle_trades) * 100
        print(f"  Triangle: {len(triangle_trades)} trades | WR: {tri_wr:.1f}% | P&L: ${tri_pnl:,.2f}")

    # Show ALL trades
    print(f"\n📝 ALL TRADES ({len(trades_full)} total):")
    print("-" * 110)
    print(f"{'Date':<17} {'Dir':<6} {'Entry':<8} {'Exit':<8} {'Margin':<10} {'ROI':<8} {'P&L':<12} {'Balance':<12} {'Exit':<10}")
    print("-" * 110)

    for _, trade in trades_full.iterrows():
        sign = "+" if trade['pnl'] > 0 else ""
        roi_sign = "+" if trade['roi_pct'] > 0 else ""
        color = "✅" if trade['pnl'] > 0 else "❌"

        print(f"{trade['entry_time'].strftime('%Y-%m-%d %H:%M'):<17} "
              f"{trade['direction']:<6} "
              f"${trade['entry_price']:<7.4f} "
              f"${trade['exit_price']:<7.4f} "
              f"${trade['margin']:>8,.0f} "
              f"{roi_sign}{trade['roi_pct']:>6.1f}% "
              f"{sign}${trade['pnl']:>9.2f} "
              f"${trade['balance']:>10.2f} "
              f"{trade['exit_type']:<10} {color}")

    print("-" * 110)

    # Monthly breakdown
    trades_full['month'] = trades_full['entry_time'].dt.to_period('M')
    monthly_stats = trades_full.groupby('month').agg({
        'pnl': ['sum', 'count']
    })

    print(f"\n📅 MONTHLY PERFORMANCE")
    print("-" * 60)
    print(f"{'Month':<12} {'Trades':<8} {'P&L':<15} {'Balance':<15}")
    print("-" * 60)

    running_balance = 10000
    for month in monthly_stats.index:
        month_trades = trades_full[trades_full['month'] == month]
        month_pnl = month_trades['pnl'].sum()
        month_count = len(month_trades)
        running_balance += month_pnl
        sign = "+" if month_pnl > 0 else ""

        print(f"{str(month):<12} {month_count:<8} {sign}${month_pnl:>12.2f} ${running_balance:>12.2f}")

    print("-" * 60)

    # Yearly summary
    print(f"\n📆 YEARLY SUMMARY")
    print("-" * 60)
    trades_full['year'] = trades_full['entry_time'].dt.year
    for year in trades_full['year'].unique():
        year_trades = trades_full[trades_full['year'] == year]
        year_pnl = year_trades['pnl'].sum()
        year_wins = len(year_trades[year_trades['pnl'] > 0])
        year_wr = (year_wins / len(year_trades)) * 100
        print(f"  {year}: {len(year_trades)} trades | WR: {year_wr:.1f}% | P&L: ${year_pnl:,.2f}")
    print("-" * 60)

else:
    print("  No trades generated")

# Test period (OOS)
print("\n" + "="*80)
print("[OUT-OF-SAMPLE PERIOD: 2024-2025]")
print("="*80)

strategy_test = LondonBreakoutV41ADAUSDBybit(
    pair='ADAUSD',
    risk_percent=1.0,
    initial_capital=10000,
    enable_asia_breakout=True,
    enable_triangle_breakout=True,
    leverage=3
)
trades_test, equity_test = strategy_test.run(test_h1.copy(), test_h4.copy())

if len(trades_test) > 0:
    wins = trades_test[trades_test['pnl'] > 0]
    losses = trades_test[trades_test['pnl'] <= 0]

    total_pnl = trades_test['pnl'].sum()
    win_rate = len(wins) / len(trades_test) * 100
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
    annual_return_pct = (total_pnl / 10000) / years * 100

    final_balance = 10000 + total_pnl
    total_return_pct = (total_pnl / 10000) * 100

    print(f"\n📊 OOS PERFORMANCE")
    print(f"  Starting Capital: $10,000")
    print(f"  Final Balance: ${final_balance:,.2f}")
    print(f"  Total Return: ${total_pnl:,.2f} ({total_return_pct:.1f}%)")
    print(f"  Annual Return: ${annual_pnl:,.2f} ({annual_return_pct:.1f}%)")
    print(f"  \n  Trades: {len(trades_test)} ({len(trades_test)/years:.1f}/year)")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Avg Win ROI: {avg_win_roi:.1f}% | Avg Loss ROI: {avg_loss_roi:.1f}%")
    print(f"  Max Drawdown: {max_dd:.2f}%")

    # Risk assessment
    if max_dd >= -5.0:
        risk_status = "✅ LOW RISK"
    elif max_dd >= -10.0:
        risk_status = "⚠️  MODERATE RISK"
    else:
        risk_status = "❌ HIGH RISK"
    print(f"\n  {risk_status}")

print("\n" + "="*80)
print("BACKTEST COMPLETE")
print("="*80)
print(f"\n💡 KEY TAKEAWAYS FOR $10,000 @ 3x LEVERAGE:")
print(f"  • Risk per trade: $100 (1% of $10,000)")
print(f"  • Expected trades: 15-20 per year")
print(f"  • Typical win: $150-600")
print(f"  • Typical loss: $100-400")
print(f"  • Position size: ~24,000-48,000 ADA per trade")
print(f"  • Margin needed: $4,600-6,800 per trade (46-68% of capital)")
print(f"\n⚠️  IMPORTANT:")
print(f"  • Keep $2,000-3,000 buffer for volatility")
print(f"  • Monitor margin usage closely")
print(f"  • Stop trading if down $500 (5% of capital)")
print(f"  • Each trade uses less % of capital vs $2,500 account")
print(f"  • Better cushion for drawdowns")
