#!/usr/bin/env python3
"""
Position Stop-Loss Threshold Comparison Test

Tests 4 different position stop-loss thresholds to find optimal balance:
- 20% (aggressive - may whipsaw)
- 30% (tighter - PROPOSED)
- 40% (current default - BASELINE)
- 50% (looser - allows more loss)

Period: 2020-2025 (includes Trump tariff event Oct 10-11, 2025)

Historical context:
- Average individual crypto drawdown: -65.5%
- Range: -42.8% (DOGE) to -88.3% (SOL)
- Altcoins crash harder: -72.3% avg vs BTC/ETH -60.4% avg
- Crypto winter 2023: 6 of 8 catastrophic failures

Author: Strategy Factory
Date: 2025-10-14
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import module with numeric prefix
spec = importlib.util.spec_from_file_location(
    "nick_radge_crypto_hybrid",
    Path(__file__).parent.parent / "strategies" / "06_nick_radge_crypto_hybrid.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeCryptoHybrid = module.NickRadgeCryptoHybrid


def run_backtest_with_threshold(prices, btc_prices, threshold, threshold_name):
    """Run backtest with specific position stop-loss threshold"""

    print(f"\n{'='*80}")
    print(f"TEST: {threshold_name} ({threshold*100:.0f}% POSITION STOP-LOSS)")
    print(f"{'='*80}")

    # Initialize strategy with this threshold
    strategy = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=3,  # Match layered backtest
        qualifier_type='tqs',  # Match layered backtest
        use_momentum_weighting=True,
        bear_asset='PAXG-USD',
        portfolio_stop_loss=None,  # Disabled
        position_stop_loss=threshold,
        position_stop_loss_core_only=False
    )

    # Run backtest using strategy's built-in method
    portfolio = strategy.backtest(
        prices,
        btc_prices,
        initial_capital=100000,
        fees=0.002,
        slippage=0.002,
        log_trades=False
    )

    # Calculate metrics
    total_return = portfolio.total_return() * 100
    max_dd = portfolio.max_drawdown() * 100
    sharpe = portfolio.sharpe_ratio()
    final_value = portfolio.final_value()

    # Calculate annualized return
    days = len(prices)
    years = days / 365.25
    annualized = ((final_value / 100000) ** (1 / years) - 1) * 100

    print(f"\n📊 Results:")
    print(f"   Total Return: {total_return:,.2f}%")
    print(f"   Annualized Return: {annualized:.2f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Final Value: ${final_value:,.2f}")

    return {
        'threshold': threshold_name,
        'threshold_pct': threshold * 100,
        'total_return': total_return,
        'annualized': annualized,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'final_value': final_value
    }


def main():
    """Main execution"""

    print("="*80)
    print("POSITION STOP-LOSS THRESHOLD COMPARISON TEST")
    print("="*80)
    print("\n⚙️  Configuration:")
    print("   Period: 2020-01-01 to 2025-10-14 (~5.8 years)")
    print("   Initial Capital: $100,000")
    print("   Universe: 9 cryptos (BTC, ETH, SOL, ADA, AVAX, DOGE, DOT, MATIC, PAXG)")
    print("   Includes: Trump tariff event (Oct 10-11, 2025)")
    print("\n📚 Historical Context (from previous backtest):")
    print("   Average individual crypto drawdown: -65.5%")
    print("   Range: -42.8% (DOGE) to -88.3% (SOL)")
    print("   Altcoins crash harder: -72.3% avg vs BTC/ETH -60.4% avg")
    print("   Crypto winter 2023: 6 of 8 catastrophic failures")

    # Download data
    START_DATE = "2020-01-01"
    END_DATE = "2025-10-14"

    test_cryptos = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD',
        'AVAX-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD', 'PAXG-USD'
    ]

    print(f"\n📊 Downloading data...")
    crypto_prices_raw = yf.download(
        test_cryptos,
        start=START_DATE,
        end=END_DATE,
        progress=False
    )

    if isinstance(crypto_prices_raw.columns, pd.MultiIndex):
        prices = crypto_prices_raw['Close']
    else:
        prices = crypto_prices_raw

    # Download BTC separately to ensure we have it for regime filter
    btc_data = yf.download('BTC-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(btc_data.columns, pd.MultiIndex):
        btc_prices = btc_data['Close'].iloc[:, 0]
    else:
        btc_prices = btc_data['Close']

    print(f"   ✅ Downloaded {len(prices.columns)} cryptos, {len(prices)} days")
    print(f"   ⚠️  Note: Some cryptos have partial history (will not trade until data exists)")

    # Test configurations
    thresholds = [
        (0.20, "20% STOP (Aggressive)"),
        (0.30, "30% STOP (Proposed)"),
        (0.40, "40% STOP (Current Default)"),
        (0.50, "50% STOP (Looser)")
    ]

    results = []

    for threshold, name in thresholds:
        result = run_backtest_with_threshold(prices, btc_prices, threshold, name)
        results.append(result)

    # Comparison table
    print("\n" + "="*80)
    print("📊 THRESHOLD COMPARISON SUMMARY")
    print("="*80)

    df = pd.DataFrame(results)

    print(f"\n{'Threshold':<25} {'Total Return':<15} {'Annual':<12} {'Sharpe':<10} {'Max DD':<12}")
    print("-" * 90)

    for _, row in df.iterrows():
        print(f"{row['threshold']:<25} {row['total_return']:>12.2f}%  {row['annualized']:>9.2f}%  {row['sharpe']:>8.2f}  {row['max_dd']:>10.2f}%")

    # Analysis
    print("\n" + "="*80)
    print("💡 ANALYSIS")
    print("="*80)

    # Best return
    best_return_idx = df['total_return'].idxmax()
    print(f"\n🏆 Best Total Return: {df.loc[best_return_idx, 'threshold']}")
    print(f"   Return: {df.loc[best_return_idx, 'total_return']:.2f}%")
    print(f"   Sharpe: {df.loc[best_return_idx, 'sharpe']:.2f}")

    # Best Sharpe
    best_sharpe_idx = df['sharpe'].idxmax()
    print(f"\n📈 Best Risk-Adjusted (Sharpe): {df.loc[best_sharpe_idx, 'threshold']}")
    print(f"   Sharpe: {df.loc[best_sharpe_idx, 'sharpe']:.2f}")
    print(f"   Return: {df.loc[best_sharpe_idx, 'total_return']:.2f}%")
    print(f"   Max DD: {df.loc[best_sharpe_idx, 'max_dd']:.2f}%")

    # Lowest DD
    best_dd_idx = df['max_dd'].idxmax()  # Max because DD is negative
    print(f"\n🛡️  Lowest Drawdown: {df.loc[best_dd_idx, 'threshold']}")
    print(f"   Max DD: {df.loc[best_dd_idx, 'max_dd']:.2f}%")
    print(f"   Return: {df.loc[best_dd_idx, 'total_return']:.2f}%")

    # Return impact analysis
    baseline_idx = df[df['threshold_pct'] == 40.0].index[0]
    baseline_return = df.loc[baseline_idx, 'total_return']

    print(f"\n📊 Return Impact vs 40% Baseline:")
    for idx, row in df.iterrows():
        if row['threshold_pct'] != 40.0:
            diff = row['total_return'] - baseline_return
            pct_diff = (diff / baseline_return) * 100 if baseline_return != 0 else 0
            symbol = "✅" if diff >= 0 else "⚠️"
            print(f"   {symbol} {row['threshold']}: {diff:+.2f}% ({pct_diff:+.1f}%)")

    # Recommendation
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION")
    print("="*80)

    # Find threshold within 5% of best return but with better Sharpe
    top_return = df['total_return'].max()
    candidates = df[df['total_return'] >= top_return * 0.95]

    if len(candidates) > 1:
        best_candidate_idx = candidates['sharpe'].idxmax()
        recommended = df.loc[best_candidate_idx]
    else:
        recommended = df.loc[best_return_idx]

    print(f"\n✨ Recommended Threshold: {recommended['threshold']}")
    print(f"\n   Total Return: {recommended['total_return']:.2f}%")
    print(f"   Annualized: {recommended['annualized']:.2f}%")
    print(f"   Sharpe Ratio: {recommended['sharpe']:.2f}")
    print(f"   Max Drawdown: {recommended['max_dd']:.2f}%")
    print(f"   Final Value: ${recommended['final_value']:,.2f}")

    print("\n   Rationale:")
    if recommended['threshold_pct'] == 20.0:
        print("   - Most aggressive protection")
        print("   - Cuts losses earliest")
        print("   - May whipsaw in normal volatility")
    elif recommended['threshold_pct'] == 30.0:
        print("   - Tighter protection than current")
        print("   - Catches catastrophic failures earlier")
        print("   - Good balance vs whipsaw risk")
    elif recommended['threshold_pct'] == 40.0:
        print("   - Current default performs well")
        print("   - Proven in historical backtest")
        print("   - Caught 8 catastrophic failures")
    else:
        print("   - More room for recoveries")
        print("   - Reduces whipsaw risk")
        print("   - May allow larger losses")

    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'stop_loss_threshold_comparison.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n💾 Results saved to: {output_path}")

    print("\n" + "="*80)
    print("✅ THRESHOLD COMPARISON TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
