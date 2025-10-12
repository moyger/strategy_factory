#!/usr/bin/env python3
"""
Example: FTMO Challenge Strategy

This example shows how to create a strategy that complies with FTMO prop firm rules:
- Maximum daily loss: 5%
- Maximum total loss: 10%
- Minimum trading days: 4
- Profit target: 10%

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from strategies.ftmo_challenge_strategy import FTMOChallengeStrategy


def main():
    print("="*80)
    print("EXAMPLE: FTMO CHALLENGE STRATEGY")
    print("="*80)

    # Load data
    print("\n📂 Loading data...")
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use last 50k bars
    df = df.tail(50000)

    print(f"✅ Loaded {len(df):,} bars")

    # Test different challenge sizes
    print("\n" + "="*80)
    print("TESTING DIFFERENT FTMO CHALLENGE SIZES")
    print("="*80)

    challenge_sizes = ['10k', '50k', '100k']

    for size in challenge_sizes:
        print(f"\n{'='*80}")
        print(f"FTMO {size.upper()} CHALLENGE")
        print(f"{'='*80}")

        # Create strategy
        strategy = FTMOChallengeStrategy(
            challenge_size=size,
            risk_per_trade=1.0,      # Conservative 1% risk
            atr_period=14,
            atr_sl_multiplier=2.0,   # Conservative stops
            atr_tp_multiplier=4.0,   # 2:1 reward/risk
            session_filter=False,    # Disable for 24/7 crypto
            require_trend=True       # Only trade with trend
        )

        print(f"\n📊 Strategy: {strategy}")
        print(f"   Starting Balance: ${strategy.specs['balance']:,}")
        print(f"   Daily Loss Limit: ${strategy.specs['daily_loss_limit']:,}")
        print(f"   Max Total Loss: ${strategy.specs['max_loss_limit']:,}")
        print(f"   Profit Target: ${strategy.specs['profit_target']:,}")

        # Run backtest
        print(f"\n📈 Running backtest...")
        results = strategy.backtest(df)

        # Print summary
        portfolio = results['portfolio']
        ftmo_check = results['ftmo_check']

        print(f"\n📊 Quick Results:")
        print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
        print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")
        print(f"   Num Trades: {portfolio.trades.count()}")

        if ftmo_check['challenge_passed']:
            print(f"\n   ✅ PASSED - {ftmo_check['summary']}")
        else:
            print(f"\n   ❌ FAILED - {ftmo_check['summary']}")

    # Show detailed results for 50k challenge
    print("\n" + "="*80)
    print("DETAILED ANALYSIS: 50K CHALLENGE")
    print("="*80)

    strategy = FTMOChallengeStrategy(
        challenge_size='50k',
        risk_per_trade=1.0,
        atr_period=14,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=4.0,
        session_filter=False,
        require_trend=True
    )

    results = strategy.backtest(df)
    strategy.print_results(results)

    # Explanation
    print("\n" + "="*80)
    print("FTMO RULES EXPLAINED")
    print("="*80)

    print("""
FTMO challenges have strict rules you must follow:

1. DAILY LOSS LIMIT (5% of starting balance):
   - If you lose 5% in a single day, you fail immediately
   - Strategy uses 1% risk per trade to avoid this
   - Conservative stops prevent catastrophic losses

2. MAX TOTAL LOSS (10% of starting balance):
   - Your equity can never drop 10% below starting
   - This is the "stop-out" level
   - Strategy manages position sizes to stay within this

3. PROFIT TARGET (10% of starting balance):
   - You must make 10% to pass the challenge
   - Strategy aims for 2:1 R/R to reach target efficiently
   - Need good win rate to achieve this consistently

4. MINIMUM TRADING DAYS (4 days):
   - You must trade on at least 4 different calendar days
   - Cannot rush and finish in 1-2 days
   - Strategy naturally spreads trades over time

STRATEGY FEATURES FOR FTMO:
✓ 1% risk per trade (conservative)
✓ ATR-based stops (adaptive to volatility)
✓ 2:1 reward/risk ratio
✓ Trend filter (only trade with momentum)
✓ Session filter (optional, for Forex)
✓ Automatic FTMO rule checking

TIPS FOR PASSING:
- Start with 1% risk, don't get greedy
- Use 2:1 or better R/R ratio
- Don't overtrade - quality over quantity
- Protect your profits with trailing stops
- Monitor daily P&L carefully
    """)

    print("\n✅ Example completed!")
    print("\nNext steps:")
    print("   1. Try different challenge sizes (10k, 25k, 50k, 100k, 200k)")
    print("   2. Adjust risk_per_trade (0.5-1.0% recommended)")
    print("   3. Test on different market conditions")
    print("   4. Enable session filters for Forex trading")
    print("\nRun with report:")
    print("   python run_strategy.py --strategy ftmo_challenge --challenge-size 50k --report")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
