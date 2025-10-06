"""
Visualize Pattern Detection and Trades for One Month
Shows triangle patterns, entry/exit points, and trade outcomes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import numpy as np

from backtesting.backtest import Backtest
from strategies.strategy_breakout_v4_1_optimized import StrategyBreakoutV4_1
from core.data_loader import load_ohlc_data

def plot_month_with_trades(year=2025, month=1):
    """
    Plot one month showing:
    - Price action (candlesticks)
    - Triangle patterns detected
    - Trade entries (green arrow)
    - Trade exits (red arrow for loss, blue arrow for win)
    - Stop loss and take profit levels
    """

    print(f"\n{'='*80}")
    print(f"VISUALIZING TRADES - {year}/{month:02d}")
    print(f"{'='*80}\n")

    # Load data
    print("Loading data...")
    df_h1 = load_ohlc_data('EURUSD', 'H1', 'data/EURUSD_1H.csv')
    df_h4 = load_ohlc_data('EURUSD', 'H4', 'data/EURUSD_4H.csv')

    # Filter to specific month + buffer (for pattern detection lookback)
    month_start = pd.Timestamp(f'{year}-{month:02d}-01')
    month_end = month_start + pd.DateOffset(months=1)
    lookback_start = month_start - pd.DateOffset(days=10)  # Extra for pattern detection

    df_h1_month = df_h1[lookback_start:month_end].copy()
    df_h4_month = df_h4[lookback_start:month_end].copy()

    print(f"Data range: {df_h1_month.index[0]} to {df_h1_month.index[-1]}")
    print(f"Total bars: {len(df_h1_month)}")

    # Run backtest for this month
    strategy = StrategyBreakoutV4_1(
        risk_per_trade=0.01,
        enable_asia_breakout=True,
        enable_triangle_breakout=True,
        triangle_lookback=60,  # Use robust parameter
        triangle_r2_min=0.5,
        triangle_slope_tolerance=0.0003
    )

    bt = Backtest(
        strategy=strategy,
        df_h1=df_h1_month,
        df_h4=df_h4_month,
        initial_balance=100000,
        commission=0,
        slippage_pips=0.5
    )

    print("\nRunning backtest...")
    results = bt.run()
    trades_df = results['trades']

    # Filter trades to only those in the target month
    trades_in_month = trades_df[
        (trades_df['entry_time'] >= month_start) &
        (trades_df['entry_time'] < month_end)
    ].copy()

    print(f"\nTrades in {year}-{month:02d}: {len(trades_in_month)}")
    if len(trades_in_month) == 0:
        print("No trades in this month. Try a different month.")
        return

    # Show trade summary
    print("\nTrade Summary:")
    print(trades_in_month[['entry_time', 'pattern_type', 'direction', 'pnl', 'exit_reason']].to_string(index=False))

    # Create visualization
    fig, axes = plt.subplots(2, 1, figsize=(20, 12), height_ratios=[3, 1])
    ax_price = axes[0]
    ax_equity = axes[1]

    # Filter to display month only
    df_display = df_h1_month[month_start:month_end].copy()

    # Plot candlesticks
    plot_candlesticks(ax_price, df_display)

    # Plot patterns and trades
    for _, trade in trades_in_month.iterrows():
        plot_trade(ax_price, df_h1_month, trade)

    # Plot equity curve for the month
    plot_equity_curve(ax_equity, trades_in_month)

    # Formatting
    ax_price.set_title(f'EURUSD H1 - {year}/{month:02d} - Pattern Detection & Trades', fontsize=16, fontweight='bold')
    ax_price.set_ylabel('Price', fontsize=12)
    ax_price.legend(loc='upper left', fontsize=10)
    ax_price.grid(True, alpha=0.3)

    ax_equity.set_xlabel('Date', fontsize=12)
    ax_equity.set_ylabel('Cumulative P&L ($)', fontsize=12)
    ax_equity.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    output_file = f'output/trades_visualization_{year}_{month:02d}.png'
    Path('output').mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nChart saved to: {output_file}")
    plt.close()

    # Create second chart: Detailed view of each trade
    if len(trades_in_month) > 0:
        create_individual_trade_charts(df_h1_month, trades_in_month, year, month)

def plot_candlesticks(ax, df):
    """Plot candlestick chart"""
    # Convert datetime to numeric for plotting
    x = np.arange(len(df))

    # Plot candlestick bodies
    for i, (idx, row) in enumerate(df.iterrows()):
        color = 'green' if row['close'] >= row['open'] else 'red'
        # Body
        height = abs(row['close'] - row['open'])
        bottom = min(row['open'], row['close'])
        ax.add_patch(Rectangle((i-0.3, bottom), 0.6, height, facecolor=color, edgecolor=color, alpha=0.7))
        # Wick
        ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.5, alpha=0.7)

    # Set x-axis labels
    step = max(1, len(df) // 20)  # Show ~20 labels
    ax.set_xticks(x[::step])
    ax.set_xticklabels([df.index[i].strftime('%m/%d %H:%M') for i in range(0, len(df), step)], rotation=45, ha='right')
    ax.set_xlim(-1, len(df))

    return x

def plot_trade(ax, df_full, trade):
    """Plot individual trade with pattern and levels"""
    entry_time = trade['entry_time']
    exit_time = trade['exit_time']
    pattern_type = trade['pattern_type']
    direction = trade['direction']
    entry_price = trade['entry_price']
    sl = trade['stop_loss']
    tp = trade['take_profit']
    pnl = trade['pnl']
    exit_reason = trade['exit_reason']

    # Find indices in display dataframe
    df_display = df_full[df_full.index >= entry_time.replace(hour=0, minute=0)]
    if len(df_display) == 0:
        return

    entry_idx = df_display.index.get_loc(entry_time)
    if exit_time in df_display.index:
        exit_idx = df_display.index.get_loc(exit_time)
    else:
        exit_idx = len(df_display) - 1

    # Pattern color
    if 'asia' in pattern_type.lower():
        pattern_color = 'blue'
        pattern_label = 'Asia Breakout'
    else:
        pattern_color = 'purple'
        pattern_label = f'Triangle ({trade.get("triangle_type", "?")})'

    # Entry arrow
    entry_y = entry_price
    if direction == 'long':
        ax.annotate('', xy=(entry_idx, entry_y), xytext=(entry_idx, entry_y - 0.002),
                   arrowprops=dict(arrowstyle='->', color='green', lw=2))
    else:
        ax.annotate('', xy=(entry_idx, entry_y), xytext=(entry_idx, entry_y + 0.002),
                   arrowprops=dict(arrowstyle='->', color='green', lw=2))

    # Exit arrow (color based on outcome)
    exit_y = df_full.loc[exit_time, 'close']
    exit_color = 'darkgreen' if pnl > 0 else 'darkred'
    ax.plot(exit_idx, exit_y, 'o', color=exit_color, markersize=8, zorder=5)

    # Stop loss and take profit lines
    ax.hlines(sl, entry_idx, exit_idx, colors='red', linestyles='--', linewidth=1, alpha=0.6, label='SL' if entry_idx == 0 else '')
    ax.hlines(tp, entry_idx, exit_idx, colors='green', linestyles='--', linewidth=1, alpha=0.6, label='TP' if entry_idx == 0 else '')

    # Pattern highlight box
    ax.axvspan(entry_idx - 5, exit_idx, alpha=0.1, color=pattern_color)

    # Trade label
    label_y = max(entry_price, sl, tp) + 0.001
    pnl_sign = '+' if pnl >= 0 else ''
    ax.text(entry_idx, label_y, f'{pattern_label}\n{direction.upper()}\n{pnl_sign}${pnl:.0f}',
           fontsize=8, ha='left', va='bottom',
           bbox=dict(boxstyle='round,pad=0.3', facecolor=pattern_color, alpha=0.3))

def plot_equity_curve(ax, trades_df):
    """Plot cumulative P&L"""
    if len(trades_df) == 0:
        return

    trades_sorted = trades_df.sort_values('entry_time').copy()
    trades_sorted['cumulative_pnl'] = trades_sorted['pnl'].cumsum()

    # Plot equity curve
    ax.plot(trades_sorted['entry_time'], trades_sorted['cumulative_pnl'],
           'b-', linewidth=2, label='Cumulative P&L')
    ax.axhline(0, color='black', linewidth=0.5, linestyle='--', alpha=0.5)

    # Mark wins/losses
    wins = trades_sorted[trades_sorted['pnl'] > 0]
    losses = trades_sorted[trades_sorted['pnl'] <= 0]

    ax.scatter(wins['entry_time'], wins['cumulative_pnl'],
              color='green', s=50, marker='^', zorder=5, label='Win')
    ax.scatter(losses['entry_time'], losses['cumulative_pnl'],
              color='red', s=50, marker='v', zorder=5, label='Loss')

    # Stats box
    total_pnl = trades_sorted['pnl'].sum()
    win_rate = (trades_sorted['pnl'] > 0).sum() / len(trades_sorted) * 100
    stats_text = f'Trades: {len(trades_sorted)} | Win Rate: {win_rate:.1f}% | P&L: ${total_pnl:.0f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
           fontsize=11, va='top', ha='left',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))

    ax.legend(loc='upper right')

def create_individual_trade_charts(df_full, trades_df, year, month):
    """Create detailed chart for each trade"""
    print(f"\nCreating individual trade charts...")

    for idx, trade in trades_df.iterrows():
        fig, ax = plt.subplots(figsize=(16, 8))

        # Get data window around trade (pattern lookback + trade duration)
        entry_time = trade['entry_time']
        exit_time = trade['exit_time']
        lookback = 60  # bars before entry

        # Find the position in full dataframe
        entry_pos = df_full.index.get_loc(entry_time)
        start_pos = max(0, entry_pos - lookback)

        # Get exit position
        if exit_time in df_full.index:
            exit_pos = df_full.index.get_loc(exit_time)
        else:
            exit_pos = len(df_full) - 1

        end_pos = min(len(df_full) - 1, exit_pos + 10)

        df_window = df_full.iloc[start_pos:end_pos+1].copy()

        # Plot candlesticks
        plot_candlesticks(ax, df_window)

        # Adjust entry/exit indices for windowed data
        entry_idx_window = entry_pos - start_pos
        exit_idx_window = exit_pos - start_pos

        # Plot pattern if triangle
        if 'triangle' in trade['pattern_type'].lower() or 'flag' in trade['pattern_type'].lower() or 'pennant' in trade['pattern_type'].lower():
            plot_triangle_pattern(ax, df_window, entry_idx_window, trade)

        # Plot trade details
        entry_price = trade['entry_price']
        sl = trade['stop_loss']
        tp = trade['take_profit']
        pnl = trade['pnl']
        direction = trade['direction']

        # Entry marker
        ax.plot(entry_idx_window, entry_price, 'go', markersize=12, label='Entry', zorder=5)

        # Exit marker
        exit_price = df_window.iloc[exit_idx_window]['close']
        exit_color = 'darkgreen' if pnl > 0 else 'darkred'
        ax.plot(exit_idx_window, exit_price, 'o', color=exit_color, markersize=12, label='Exit', zorder=5)

        # SL/TP lines
        ax.hlines(sl, 0, len(df_window)-1, colors='red', linestyles='--', linewidth=2, alpha=0.7, label='Stop Loss')
        ax.hlines(tp, 0, len(df_window)-1, colors='green', linestyles='--', linewidth=2, alpha=0.7, label='Take Profit')

        # Trade info box
        info_text = f"""
        Pattern: {trade['pattern_type']}
        Direction: {direction.upper()}
        Entry: ${entry_price:.5f}
        Exit: ${exit_price:.5f}
        SL: ${sl:.5f} | TP: ${tp:.5f}
        P&L: ${pnl:.2f}
        Exit Reason: {trade['exit_reason']}
        """
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=10, va='top', ha='left', family='monospace',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))

        ax.set_title(f'Trade Detail - {entry_time.strftime("%Y-%m-%d %H:%M")} - {trade["pattern_type"]}',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        # Save
        output_file = f'output/trade_detail_{year}_{month:02d}_{idx+1}.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {output_file}")

def plot_triangle_pattern(ax, df_window, entry_idx, trade):
    """Plot triangle pattern lines if available"""
    # This is simplified - in reality you'd need to store pattern details
    # For now, just highlight the pattern formation area
    pattern_start = max(0, entry_idx - 40)
    ax.axvspan(pattern_start, entry_idx, alpha=0.15, color='purple', label='Pattern Formation')

if __name__ == '__main__':
    # Test with January 2025
    plot_month_with_trades(year=2025, month=1)

    # You can try other months if January has no trades
    # plot_month_with_trades(year=2025, month=2)
    # plot_month_with_trades(year=2025, month=3)
