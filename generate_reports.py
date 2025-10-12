#!/usr/bin/env python3
"""
Generate QuantStats Reports for Best Strategies

This script:
1. Loads the best strategy from results
2. Runs backtest to get returns
3. Generates comprehensive QuantStats HTML report
4. Creates tear sheet and metrics
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from strategy_factory.generator import StrategyGenerator
from strategy_factory.analyzer import StrategyAnalyzer
import ast

print("=" * 80)
print("QUANTSTATS REPORT GENERATOR")
print("=" * 80)

# ==========================================
# 1. LOAD DATA
# ==========================================
print("\n📊 Step 1: Loading market data...")

df = pd.read_csv('data/crypto/BTCUSD_5m.csv')
df.columns = df.columns.str.lower()

if 'date' in df.columns:
    df = df.rename(columns={'date': 'timestamp'})

df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

print(f"✅ Loaded {len(df):,} bars")
print(f"   Period: {df.index[0]} to {df.index[-1]}")

# ==========================================
# 2. LOAD BEST STRATEGY
# ==========================================
print("\n🏆 Step 2: Loading best strategy...")

results = pd.read_csv('results/top_50_strategies.csv')
best_strategy = results.iloc[0]

params = ast.literal_eval(best_strategy['params'])
print(f"\nBest Strategy: {params['type']}")
print(f"  Parameters: {params}")
print(f"  Sharpe Ratio: {best_strategy['sharpe_ratio']:.2f}")
print(f"  Total Return: {best_strategy['total_return']:.2f}%")
print(f"  Win Rate: {best_strategy['win_rate']*100:.1f}%")

# ==========================================
# 3. RUN BACKTEST
# ==========================================
print("\n🔄 Step 3: Running backtest...")

generator = StrategyGenerator(initial_capital=10000, commission=0.001)

# Re-run the best strategy to get portfolio object
if params['type'] == 'Breakout':
    import vectorbt as vbt
    import pandas as pd

    high = df['high'].values
    low = df['low'].values
    close = df['close'].values

    lookback = params['lookback']
    breakout_pct = params['breakout_pct']

    # Calculate signals
    rolling_high = pd.Series(high).rolling(lookback).max()
    rolling_low = pd.Series(low).rolling(lookback).min()

    upper_band = rolling_high * (1 + breakout_pct / 100)
    lower_band = rolling_low * (1 - breakout_pct / 100)

    entries = pd.Series(close) > upper_band.shift(1)
    exits = pd.Series(close) < lower_band.shift(1)

    portfolio = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001
    )

    print(f"✅ Backtest complete")
    print(f"   Total Trades: {portfolio.trades.count()}")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")

# ==========================================
# 4. GENERATE QUANTSTATS REPORTS
# ==========================================
print("\n📈 Step 4: Generating QuantStats reports...")

analyzer = StrategyAnalyzer(output_dir='results/analysis_reports')

# Get returns with proper frequency
returns = portfolio.returns()

# Add datetime index if not present
if not isinstance(returns.index, pd.DatetimeIndex):
    returns.index = df.index

print(f"   Returns shape: {returns.shape}")
print(f"   Returns range: {returns.index[0]} to {returns.index[-1]}")

# Generate full HTML report
report_path = analyzer.generate_full_report(
    returns=returns,
    output_file=f'best_strategy_{params["type"].lower()}_report.html',
    title=f'Best {params["type"]} Strategy - QuantStats Report'
)

print(f"\n✅ Report generated: {report_path}")

# Generate metrics
print("\n📊 Calculating key metrics...")
metrics = analyzer.get_key_metrics(returns)
analyzer.print_metrics(metrics)

# Export trades
print("\n💾 Exporting trade history...")
trades_df = analyzer.export_trades(portfolio, output_file='best_strategy_trades.csv')

print(f"\n📋 Trade Summary:")
print(f"   Total Trades: {len(trades_df)}")
if len(trades_df) > 0:
    winning_trades = trades_df[trades_df['PnL'] > 0]
    print(f"   Winning Trades: {len(winning_trades)} ({len(winning_trades)/len(trades_df)*100:.1f}%)")
    print(f"   Average Win: ${trades_df[trades_df['PnL'] > 0]['PnL'].mean():.2f}")
    print(f"   Average Loss: ${trades_df[trades_df['PnL'] < 0]['PnL'].mean():.2f}")

# Drawdown analysis
print("\n📉 Analyzing drawdowns...")
drawdowns = analyzer.drawdown_analysis(returns)

if len(drawdowns) > 0:
    print(f"\n🔴 Top 5 Worst Drawdowns:")
    for i, dd in drawdowns.head(5).iterrows():
        print(f"   {i+1}. {dd['max_drawdown']:.2f}% over {dd['duration']} periods")

# ==========================================
# 5. COMPARE TOP 5 STRATEGIES
# ==========================================
print("\n🏅 Step 5: Comparing top 5 strategies...")

strategies_returns = {}

for idx, row in results.head(5).iterrows():
    params = ast.literal_eval(row['params'])

    if params['type'] == 'Breakout':
        lookback = params['lookback']
        breakout_pct = params['breakout_pct']

        rolling_high = pd.Series(df['high'].values).rolling(lookback).max()
        rolling_low = pd.Series(df['low'].values).rolling(lookback).min()

        upper_band = rolling_high * (1 + breakout_pct / 100)
        lower_band = rolling_low * (1 - breakout_pct / 100)

        entries = pd.Series(df['close'].values) > upper_band.shift(1)
        exits = pd.Series(df['close'].values) < lower_band.shift(1)

        pf = vbt.Portfolio.from_signals(
            close=df['close'].values,
            entries=entries,
            exits=exits,
            init_cash=10000,
            fees=0.001
        )

        rets = pf.returns()
        rets.index = df.index

        strategy_name = f"{params['type']} (L={lookback}, B={breakout_pct}%)"
        strategies_returns[strategy_name] = rets

comparison_df = analyzer.compare_strategies(
    strategies_returns,
    output_file='top5_comparison.csv'
)

print("\n📊 Comparison Results:")
print(comparison_df[['total_return', 'sharpe', 'max_drawdown', 'win_rate']].to_string())

# ==========================================
# 6. SUMMARY
# ==========================================
print("\n" + "=" * 80)
print("✅ REPORT GENERATION COMPLETE!")
print("=" * 80)

print(f"\n📁 Files Generated:")
print(f"   - results/analysis_reports/best_strategy_{params['type'].lower()}_report.html")
print(f"   - results/analysis_reports/best_strategy_trades.csv")
print(f"   - results/analysis_reports/top5_comparison.csv")

print(f"\n🌐 Open the HTML report in your browser to view:")
print(f"   - Cumulative returns chart")
print(f"   - Monthly returns heatmap")
print(f"   - Drawdown periods")
print(f"   - Rolling metrics")
print(f"   - Distribution of returns")
print(f"   - And much more!")

print("\n" + "=" * 80)
