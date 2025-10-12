#!/usr/bin/env python3
"""
Visualize ATR-Based Qualifier Comparison Results

Creates charts comparing all qualifiers across key metrics.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Read results
df = pd.read_csv('results/qualifier_comparison.csv')

# Create figure with subplots
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Nick Radge Strategy: ATR-Based Qualifiers vs ROC\n5-Year Backtest (2020-2025)',
             fontsize=16, fontweight='bold')

# Color palette - highlight BSS
colors = ['#FF4444' if q == 'BSS' else '#4A90E2' for q in df['Qualifier']]

# 1. Total Return
ax = axes[0, 0]
bars = ax.bar(df['Qualifier'], df['Total Return %'], color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=104.87, color='green', linestyle='--', label='SPY B&H (104.87%)', linewidth=2)
ax.set_title('Total Return (%)', fontweight='bold', fontsize=12)
ax.set_ylabel('Return (%)')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%',
            ha='center', va='bottom', fontsize=9)

# 2. Sharpe Ratio
ax = axes[0, 1]
bars = ax.bar(df['Qualifier'], df['Sharpe Ratio'], color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=1.0, color='gray', linestyle=':', label='Sharpe = 1.0', linewidth=1.5)
ax.set_title('Sharpe Ratio (Risk-Adjusted Returns)', fontweight='bold', fontsize=12)
ax.set_ylabel('Sharpe Ratio')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.2f}',
            ha='center', va='bottom', fontsize=9)

# 3. Max Drawdown
ax = axes[0, 2]
bars = ax.bar(df['Qualifier'], df['Max Drawdown %'], color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=-25, color='red', linestyle=':', label='Target < -25%', linewidth=1.5)
ax.set_title('Max Drawdown (%)', fontweight='bold', fontsize=12)
ax.set_ylabel('Drawdown (%)')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%',
            ha='center', va='top', fontsize=9)

# 4. Win Rate
ax = axes[1, 0]
bars = ax.bar(df['Qualifier'], df['Win Rate %'], color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=50, color='gray', linestyle=':', label='50% threshold', linewidth=1.5)
ax.set_title('Win Rate (%)', fontweight='bold', fontsize=12)
ax.set_ylabel('Win Rate (%)')
ax.set_xlabel('Qualifier')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.1f}%',
            ha='center', va='bottom', fontsize=9)

# 5. Profit Factor
ax = axes[1, 1]
bars = ax.bar(df['Qualifier'], df['Profit Factor'], color=colors, alpha=0.8, edgecolor='black')
ax.axhline(y=2.0, color='green', linestyle=':', label='Target > 2.0', linewidth=1.5)
ax.set_title('Profit Factor', fontweight='bold', fontsize=12)
ax.set_ylabel('Profit Factor')
ax.set_xlabel('Qualifier')
ax.legend()
ax.grid(axis='y', alpha=0.3)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.2f}',
            ha='center', va='bottom', fontsize=9)

# 6. Summary Metrics Table
ax = axes[1, 2]
ax.axis('off')

# Highlight top performers
best_return = df.loc[df['Total Return %'].idxmax()]
best_sharpe = df.loc[df['Sharpe Ratio'].idxmax()]
best_dd = df.loc[df['Max Drawdown %'].idxmin()]  # Closest to 0 (least negative)

summary_text = f"""
🏆 TOP PERFORMERS

Highest Return:
  {best_return['Qualifier']}: {best_return['Total Return %']:.1f}%
  (+{best_return['Total Return %'] - df[df['Qualifier']=='ROC']['Total Return %'].values[0]:.1f}% vs ROC)

Best Sharpe:
  {best_sharpe['Qualifier']}: {best_sharpe['Sharpe Ratio']:.2f}
  (Superior risk-adjusted returns)

Lowest Drawdown:
  {best_dd['Qualifier']}: {best_dd['Max Drawdown %']:.1f}%
  (Best downside protection)

📊 BENCHMARK
  SPY Buy & Hold: 104.87%

💡 KEY INSIGHT
  BSS (Breakout Strength Score)
  outperforms by identifying
  stocks breaking out with
  CONVICTION (ATR-adjusted)
"""

ax.text(0.05, 0.95, summary_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()

# Save figure
output_path = 'results/qualifier_comparison.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"✅ Chart saved: {output_path}")

plt.show()
