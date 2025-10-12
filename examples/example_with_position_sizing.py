#!/usr/bin/env python3
"""
Example: Advanced Position Sizing Methods

This example demonstrates 3 different position sizing methods:
1. Fixed Percent Risk - Risk same % of account on each trade
2. Kelly Criterion - Optimal sizing based on edge
3. Volatility-based - Maintain constant portfolio volatility

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from strategies.advanced_strategy_template import AdvancedStrategyTemplate


def run_strategy_with_sizing(sizing_method: str, df: pd.DataFrame):
    """Run strategy with specific position sizing method"""

    print(f"\n{'='*80}")
    print(f"POSITION SIZING METHOD: {sizing_method.upper()}")
    print(f"{'='*80}")

    # Create strategy
    strategy = AdvancedStrategyTemplate(
        sizing_method=sizing_method,
        risk_per_trade=1.0,      # For fixed percent method
        kelly_fraction=0.5,       # For Kelly method (use 50% of optimal)
        atr_period=14,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=4.0,
        session_filter=False,
        require_high_volatility=False,
        check_ftmo_rules=False
    )

    print(f"\n📊 Strategy: {strategy}")

    # Run backtest
    print(f"\n📈 Running backtest...")
    results = strategy.backtest(df, initial_capital=10000)

    # Print results
    portfolio = results['portfolio']

    print(f"\n📊 Results:")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
    print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
    print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")
    print(f"   Num Trades: {portfolio.trades.count()}")

    if portfolio.trades.count() > 0:
        print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
        print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")

    return results


def main():
    print("="*80)
    print("EXAMPLE: COMPARING POSITION SIZING METHODS")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use last 30k bars for speed
    df = df.tail(30000)

    print(f"✅ Loaded {len(df):,} bars")

    # Test all 3 sizing methods
    print("\n" + "="*80)
    print("TESTING ALL POSITION SIZING METHODS")
    print("="*80)

    methods = ['fixed_percent', 'kelly', 'volatility']
    results_summary = {}

    for method in methods:
        results = run_strategy_with_sizing(method, df)
        portfolio = results['portfolio']

        results_summary[method] = {
            'return': portfolio.total_return() * 100,
            'sharpe': portfolio.sharpe_ratio(freq='5min'),
            'max_dd': portfolio.max_drawdown() * 100,
            'trades': portfolio.trades.count()
        }

    # Compare results
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)

    print(f"\n{'Method':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades':<10}")
    print("-" * 80)

    for method, metrics in results_summary.items():
        print(f"{method:<20} {metrics['return']:>10.2f}%  {metrics['sharpe']:>8.2f}  {metrics['max_dd']:>10.2f}%  {metrics['trades']:>8}")

    # Explanation
    print("\n" + "="*80)
    print("POSITION SIZING METHODS EXPLAINED")
    print("="*80)

    print("""
1. FIXED PERCENT RISK:
   - Risk same % of account on each trade (e.g., 1%)
   - Simple and consistent
   - Good for beginners
   - Best when: You want predictable risk per trade

2. KELLY CRITERION:
   - Optimal sizing based on win rate and avg win/loss
   - Maximizes long-term growth
   - Can be aggressive (use fraction like 0.5)
   - Best when: You have proven edge and want optimal growth

3. VOLATILITY-BASED:
   - Adjusts size to maintain constant portfolio volatility
   - Reduces size in volatile periods, increases in calm periods
   - More sophisticated risk management
   - Best when: You want smooth equity curve regardless of market conditions

WHICH TO USE?
- Starting out? Use Fixed Percent (1-2% risk)
- Have proven strategy? Use Kelly (0.5 fraction for safety)
- Want smooth returns? Use Volatility-based
    """)

    print("\n✅ Example completed!")
    print("\nNext steps:")
    print("   1. Try different data periods to see how sizing adapts")
    print("   2. Adjust risk_percent and kelly_fraction parameters")
    print("   3. Combine with session/volatility filters")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
