"""
Visualize Pattern Detection and Trades for One Month
Shows triangle patterns, entry/exit points, and trade outcomes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from core.data_loader import ForexDataLoader

def plot_month_with_trades(year=2025, month=1):
    """
    Plot one month showing:
    - Price action (candlesticks)
    - Trade entries (green arrow)
    - Trade exits (red arrow for loss, blue arrow for win)
    - Stop loss and take profit levels
    """

    print(f"\n{'='*80}")
    print(f"VISUALIZING TRADES - {year}/{month:02d}")
    print(f"{'='*80}\n")

    # Load data
    print("Loading data...")
    loader = ForexDataLoader(data_dir='data/forex')
    df_h1 = loader.load('EURUSD', 'H1')
    df_h4 = loader.load('EURUSD', 'H4')

    # Filter to specific month + buffer (for pattern detection lookback)
    month_start = pd.Timestamp(f'{year}-{month:02d}-01')
    month_end = month_start + pd.DateOffset(months=1)
    lookback_start = month_start - pd.DateOffset(days=20)  # Extra for pattern detection

    df_h1_month = df_h1[lookback_start:month_end].copy()
    df_h4_month = df_h4[lookback_start:month_end].copy()

    print(f"Data range: {df_h1_month.index[0]} to {df_h1_month.index[-1]}")
    print(f"Total bars: {len(df_h1_month)}")

    # Run backtest for this period
    strategy = LondonBreakoutV41Optimized(
        risk_percent=1.0,
        initial_capital=100000,
        enable_asia_breakout=True,
        enable_triangle_breakout=True
    )

    # Use robust parameters (lookback=60)
    strategy.triangle_lookback = 60
    strategy.triangle_r2_min = 0.5
    strategy.triangle_slope_tolerance = 0.0003
    strategy.triangle_time_end = 9

    strategy.pattern_detector = PatternDetector(
        lookback=60,
        min_pivot_points=3,
        r_squared_min=0.5,
        slope_tolerance=0.0003
    )

    print("\nRunning backtest...")
    trades_df = strategy.backtest(df_h1_month, df_h4_month)

    # Filter trades to only those in the target month
    trades_in_month = trades_df[
        (trades_df['entry_time'] >= month_start) &
        (trades_df['entry_time'] < month_end)
    ].copy()

    print(f"\nTrades in {year}-{month:02d}: {len(trades_in_month)}")

    if len(trades_in_month) == 0:
        print("No trades in this month. Trying next months...")
        # Try next few months
        for m in range(month + 1, month + 4):
            if m > 12:
                break
            print(f"\nTrying {year}-{m:02d}...")
            month_start_new = pd.Timestamp(f'{year}-{m:02d}-01')
            month_end_new = month_start_new + pd.DateOffset(months=1)
            trades_test = trades_df[
                (trades_df['entry_time'] >= month_start_new) &
                (trades_df['entry_time'] < month_end_new)
            ]
            if len(trades_test) > 0:
                print(f"Found {len(trades_test)} trades in {year}-{m:02d}!")
                month = m
                month_start = month_start_new
                month_end = month_end_new
                trades_in_month = trades_test
                break

    if len(trades_in_month) == 0:
        print("No trades found. Exiting.")
        return

    # Show trade summary
    print("\nTrade Summary:")
    for _, trade in trades_in_month.iterrows():
        print(f"  {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} | "
              f"{trade['signal_type']:20s} | {trade['type']:5s} | "
              f"P&L: ${trade['pnl_dollars']:7.0f} | {trade['exit_reason']}")

    # Create visualization
    fig, axes = plt.subplots(2, 1, figsize=(20, 12), height_ratios=[3, 1])
    ax_price = axes[0]
    ax_equity = axes[1]

    # Filter to display month only
    df_display = df_h1_month[month_start:month_end].copy()

    # Plot candlesticks
    x_coords = plot_candlesticks(ax_price, df_display)

    # Plot trades
    for _, trade in trades_in_month.iterrows():
        plot_trade(ax_price, df_display, df_h1_month, trade)

    # Plot equity curve for the month
    plot_equity_curve(ax_equity, trades_in_month)

    # Formatting
    ax_price.set_title(f'EURUSD H1 - {year}/{month:02d} - Pattern Detection & Trades (lookback=60)',
                      fontsize=16, fontweight='bold')
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

    # Also create individual trade details
    create_individual_trade_charts(df_h1_month, trades_in_month, year, month)

    print(f"\n✅ Visualization complete!")
    print(f"   Main chart: {output_file}")
    print(f"   Individual trades: output/trade_detail_{year}_{month:02d}_*.png")

def plot_candlesticks(ax, df):
    """Plot candlestick chart"""
    # Convert datetime to numeric for plotting
    x = np.arange(len(df))

    # Plot candlestick bodies
    for i, (idx, row) in enumerate(df.iterrows()):
        color = 'green' if row['close'] >= row['open'] else 'red'
        # Body
        height = abs(row['close'] - row['open'])
        if height < 0.00001:
            height = 0.00001  # Minimum height for visibility
        bottom = min(row['open'], row['close'])
        ax.add_patch(Rectangle((i-0.3, bottom), 0.6, height,
                               facecolor=color, edgecolor=color, alpha=0.7))
        # Wick
        ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.5, alpha=0.7)

    # Set x-axis labels
    step = max(1, len(df) // 20)  # Show ~20 labels
    ax.set_xticks(x[::step])
    ax.set_xticklabels([df.index[i].strftime('%m/%d %H:%M') for i in range(0, len(df), step)],
                       rotation=45, ha='right')
    ax.set_xlim(-1, len(df))

    return x

def plot_trade(ax, df_display, df_full, trade):
    """Plot individual trade with levels"""
    entry_time = trade['entry_time']
    exit_time = trade['exit_time']
    signal_type = trade['signal_type']
    direction = trade['type']  # 'long' or 'short'
    entry_price = trade['entry_price']
    sl = trade['sl']  # stop loss column name
    tp = trade['tp']  # take profit column name
    pnl = trade['pnl_dollars']
    exit_reason = trade['exit_reason']

    # Find indices in display dataframe
    if entry_time not in df_display.index:
        return

    entry_idx = df_display.index.get_loc(entry_time)

    if exit_time in df_display.index:
        exit_idx = df_display.index.get_loc(exit_time)
    else:
        exit_idx = len(df_display) - 1

    # Pattern color
    if 'asia' in signal_type.lower():
        pattern_color = 'blue'
        pattern_label = 'Asia Breakout'
    else:
        pattern_color = 'purple'
        triangle_type = signal_type.replace('triangle_', '').replace('_', ' ').title()
        pattern_label = f'{triangle_type}'

    # Entry arrow
    entry_y = entry_price
    if direction == 'long':
        ax.annotate('', xy=(entry_idx, entry_y), xytext=(entry_idx, entry_y - 0.0015),
                   arrowprops=dict(arrowstyle='->', color='green', lw=3))
    else:
        ax.annotate('', xy=(entry_idx, entry_y), xytext=(entry_idx, entry_y + 0.0015),
                   arrowprops=dict(arrowstyle='->', color='green', lw=3))

    # Exit marker
    exit_y = df_full.loc[exit_time, 'close'] if exit_time in df_full.index else entry_price
    exit_color = 'darkgreen' if pnl > 0 else 'darkred'
    ax.plot(exit_idx, exit_y, 'o', color=exit_color, markersize=10, zorder=5)

    # Stop loss and take profit lines
    ax.hlines(sl, entry_idx, exit_idx, colors='red', linestyles='--', linewidth=1.5, alpha=0.6)
    ax.hlines(tp, entry_idx, exit_idx, colors='green', linestyles='--', linewidth=1.5, alpha=0.6)

    # Pattern highlight box
    ax.axvspan(entry_idx - 2, exit_idx, alpha=0.1, color=pattern_color)

    # Trade label
    label_y = max(entry_price, sl, tp) + 0.0008
    pnl_sign = '+' if pnl >= 0 else ''
    ax.text(entry_idx, label_y, f'{pattern_label}\n{direction.upper()}\n{pnl_sign}${pnl:.0f}',
           fontsize=9, ha='left', va='bottom',
           bbox=dict(boxstyle='round,pad=0.3', facecolor=pattern_color, alpha=0.4))

def plot_equity_curve(ax, trades_df):
    """Plot cumulative P&L"""
    if len(trades_df) == 0:
        return

    trades_sorted = trades_df.sort_values('entry_time').copy()
    trades_sorted['cumulative_pnl'] = trades_sorted['pnl_dollars'].cumsum()

    # Plot equity curve
    ax.plot(trades_sorted['entry_time'], trades_sorted['cumulative_pnl'],
           'b-', linewidth=2, label='Cumulative P&L')
    ax.axhline(0, color='black', linewidth=0.5, linestyle='--', alpha=0.5)

    # Mark wins/losses
    wins = trades_sorted[trades_sorted['pnl_dollars'] > 0]
    losses = trades_sorted[trades_sorted['pnl_dollars'] <= 0]

    ax.scatter(wins['entry_time'], wins['cumulative_pnl'],
              color='green', s=50, marker='^', zorder=5, label='Win')
    ax.scatter(losses['entry_time'], losses['cumulative_pnl'],
              color='red', s=50, marker='v', zorder=5, label='Loss')

    # Stats box
    total_pnl = trades_sorted['pnl_dollars'].sum()
    win_rate = (trades_sorted['pnl_dollars'] > 0).sum() / len(trades_sorted) * 100
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

        # Plot trade details
        entry_price = trade['entry_price']
        sl = trade['sl']
        tp = trade['tp']
        pnl = trade['pnl_dollars']
        direction = trade['type']

        # Entry marker
        ax.plot(entry_idx_window, entry_price, 'go', markersize=12, label='Entry', zorder=5)

        # Exit marker
        exit_price = df_window.iloc[exit_idx_window]['close']
        exit_color = 'darkgreen' if pnl > 0 else 'darkred'
        ax.plot(exit_idx_window, exit_price, 'o', color=exit_color, markersize=12, label='Exit', zorder=5)

        # SL/TP lines
        ax.hlines(sl, 0, len(df_window)-1, colors='red', linestyles='--', linewidth=2, alpha=0.7, label='Stop Loss')
        ax.hlines(tp, 0, len(df_window)-1, colors='green', linestyles='--', linewidth=2, alpha=0.7, label='Take Profit')

        # Pattern formation area (if triangle)
        if 'triangle' in trade['signal_type'] or 'flag' in trade['signal_type'] or 'pennant' in trade['signal_type']:
            pattern_start = max(0, entry_idx_window - 40)
            ax.axvspan(pattern_start, entry_idx_window, alpha=0.15, color='purple', label='Pattern Formation')

        # Trade info box
        direction_label = trade['type']
        info_text = f"""Pattern: {trade['signal_type']}
Direction: {direction_label.upper()}
Entry: ${entry_price:.5f} @ {entry_time.strftime('%Y-%m-%d %H:%M')}
Exit: ${exit_price:.5f} @ {exit_time.strftime('%Y-%m-%d %H:%M')}
SL: ${trade['sl']:.5f} | TP: ${trade['tp']:.5f}
P&L: ${pnl:.2f}
Exit: {trade['exit_reason']}"""

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=10, va='top', ha='left', family='monospace',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))

        ax.set_title(f'Trade Detail - {entry_time.strftime("%Y-%m-%d %H:%M")} - {trade["signal_type"]}',
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_ylabel('Price')

        # Save
        output_file = f'output/trade_detail_{year}_{month:02d}_{idx+1}.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Saved: {output_file}")

if __name__ == '__main__':
    # Test with January 2025
    plot_month_with_trades(year=2025, month=1)
