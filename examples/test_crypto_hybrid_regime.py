"""
Test Hybrid Regime Strategy for Crypto

Instead of 100% USDT/PAXG during BEAR, keep some crypto exposure:
- STRONG_BULL: 5 cryptos (100%)
- WEAK_BULL: 5 cryptos (100%)
- BEAR: 3 cryptos (60%) + 2 PAXG (40%)

This could capture some upside during bear while having downside protection
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from strategies.nick_radge_crypto_strategy import NickRadgeCryptoStrategy
from strategy_factory.performance_qualifiers import get_qualifier
import warnings
warnings.filterwarnings('ignore')

# Configuration
START_DATE = '2019-01-01'
END_DATE = '2025-01-01'
INITIAL_CAPITAL = 10000
FEES = 0.001
SLIPPAGE = 0.001

CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'LTC-USD', 'LINK-USD',
    'DOT-USD', 'UNI-USD', 'DOGE-USD', 'MATIC-USD', 'AAVE-USD', 'MKR-USD',
    'ATOM-USD', 'ETC-USD', 'XLM-USD', 'VET-USD', 'FIL-USD',
    'PAXG-USD',  # Gold-backed stablecoin
    'USDT-USD'   # Regular stablecoin for comparison
]

def download_crypto_data():
    """Download crypto data"""
    print(f"📊 Downloading data for {len(CRYPTO_UNIVERSE)} cryptos...")

    data = yf.download(CRYPTO_UNIVERSE, start=START_DATE, end=END_DATE,
                       auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
    else:
        prices = data

    prices.columns = [col.replace('-USD', '') for col in prices.columns]
    prices = prices.dropna(thresh=len(prices) * 0.5, axis=1).ffill().dropna()

    print(f"✅ Got {len(prices.columns)} cryptos\n")
    return prices

def run_hybrid_strategy(prices, config_name, strong_bull_pos, weak_bull_pos, bear_pos, bear_asset, bear_allocation):
    """Run strategy with specified configuration"""
    print(f"\n{'='*70}")
    print(f"🔄 Testing {config_name}")
    print(f"{'='*70}")

    btc_prices = prices['BTC']

    strategy = NickRadgeCryptoStrategy(
        portfolio_size=5,
        roc_period=30,
        ma_period=50,
        rebalance_freq='MS',
        use_regime_filter=True,
        regime_ma_long=100,
        regime_ma_short=50,
        strong_bull_positions=strong_bull_pos,
        weak_bull_positions=weak_bull_pos,
        bear_positions=bear_pos,
        bear_market_asset=bear_asset,
        bear_allocation=bear_allocation
    )

    portfolio = strategy.backtest(
        prices=prices,
        btc_prices=btc_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=FEES,
        slippage=SLIPPAGE
    )

    # Extract metrics
    total_return = portfolio.total_return() * 100
    sharpe = portfolio.sharpe_ratio(freq='D')
    max_dd = portfolio.max_drawdown() * 100
    trades = portfolio.trades.count()

    stats = portfolio.stats()
    win_rate = stats['Win Rate [%]']
    profit_factor = stats['Profit Factor']
    final_value = portfolio.total_profit() + INITIAL_CAPITAL

    print(f"\n📊 {config_name} Results:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Total Trades: {trades}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Final Value: ${final_value:,.2f}")

    return {
        'Strategy': config_name,
        'Strong Bull': f"{strong_bull_pos} cryptos",
        'Weak Bull': f"{weak_bull_pos} cryptos",
        'Bear': f"{bear_pos} cryptos + {5-bear_pos if bear_pos < 5 else 0} {bear_asset}",
        'Total Return %': total_return,
        'Sharpe Ratio': sharpe,
        'Max Drawdown %': abs(max_dd),
        'Total Trades': trades,
        'Win Rate %': win_rate,
        'Profit Factor': profit_factor,
        'Final Value': final_value
    }

def main():
    print("\n" + "="*70)
    print("🔬 HYBRID REGIME STRATEGY COMPARISON")
    print("="*70)
    print("Testing different bear market allocations")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print("="*70 + "\n")

    prices = download_crypto_data()

    # Test configurations
    # Format: (name, strong_bull_pos, weak_bull_pos, bear_pos, bear_asset, bear_allocation)
    configs = [
        # Baseline: No regime filter
        ('No Regime Filter (Baseline)', 5, 5, 5, 'USDT', 0.0),

        # Original: 100% to stablecoin
        ('100% USDT in Bear', 5, 5, 0, 'USDT', 1.0),

        # Hybrid options with USDT
        ('80% Crypto + 20% USDT', 5, 5, 4, 'USDT', 0.2),
        ('60% Crypto + 40% USDT', 5, 5, 3, 'USDT', 0.4),
        ('40% Crypto + 60% USDT', 5, 5, 2, 'USDT', 0.6),
        ('20% Crypto + 80% USDT', 5, 5, 1, 'USDT', 0.8),

        # Hybrid options with PAXG (gold)
        ('100% PAXG in Bear', 5, 5, 0, 'PAXG', 1.0),
        ('60% Crypto + 40% PAXG', 5, 5, 3, 'PAXG', 0.4),
        ('50% Crypto + 50% PAXG', 5, 5, 3, 'PAXG', 0.5),  # Your suggestion: 3 crypto, 2 gold
        ('40% Crypto + 60% PAXG', 5, 5, 2, 'PAXG', 0.6),
    ]

    results = []
    for config_name, sb, wb, bp, ba, ball in configs:
        try:
            result = run_hybrid_strategy(prices, config_name, sb, wb, bp, ba, ball)
            results.append(result)
        except Exception as e:
            print(f"\n⚠️  Error testing {config_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Create comparison DataFrame
    if len(results) > 0:
        comparison_df = pd.DataFrame(results)
        comparison_df = comparison_df.sort_values('Total Return %', ascending=False)

        print("\n" + "="*70)
        print("📊 HYBRID REGIME STRATEGY RESULTS")
        print("="*70 + "\n")
        print(comparison_df.to_string(index=False))

        # Save results
        output_file = Path(__file__).parent.parent / 'results' / 'crypto_hybrid_regime_comparison.csv'
        output_file.parent.mkdir(exist_ok=True)
        comparison_df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")

        # Analysis
        print("\n" + "="*70)
        print("🔍 ANALYSIS")
        print("="*70 + "\n")

        winner = comparison_df.iloc[0]
        baseline = comparison_df[comparison_df['Strategy'] == 'No Regime Filter (Baseline)'].iloc[0]

        print(f"🏆 WINNER: {winner['Strategy']}")
        print(f"   Return: {winner['Total Return %']:.2f}%")
        print(f"   Sharpe: {winner['Sharpe Ratio']:.2f}")
        print(f"   Max DD: {winner['Max Drawdown %']:.2f}%")
        print(f"   Final Value: ${winner['Final Value']:,.2f}")

        print(f"\n📌 Baseline (No Regime Filter):")
        print(f"   Return: {baseline['Total Return %']:.2f}%")
        print(f"   Sharpe: {baseline['Sharpe Ratio']:.2f}")
        print(f"   Max DD: {baseline['Max Drawdown %']:.2f}%")
        print(f"   Final Value: ${baseline['Final Value']:,.2f}")

        if winner['Strategy'] != 'No Regime Filter (Baseline)':
            diff = winner['Total Return %'] - baseline['Total Return %']
            print(f"\n💡 {winner['Strategy']} vs Baseline: {diff:+.2f}%")
        else:
            print(f"\n✅ Baseline still optimal (no regime filter)")

        # Analyze hybrid options specifically
        hybrid_results = comparison_df[
            comparison_df['Strategy'].str.contains('Crypto \\+') &
            comparison_df['Strategy'].str.contains('PAXG')
        ]

        if len(hybrid_results) > 0:
            print(f"\n📈 Best Hybrid (3 Crypto + 2 PAXG) Result:")
            your_suggestion = comparison_df[comparison_df['Strategy'] == '60% Crypto + 40% PAXG']
            if len(your_suggestion) > 0:
                result = your_suggestion.iloc[0]
                print(f"   Strategy: {result['Strategy']}")
                print(f"   Return: {result['Total Return %']:.2f}%")
                print(f"   vs Baseline: {result['Total Return %'] - baseline['Total Return %']:+.2f}%")
                print(f"   vs 100% USDT: {result['Total Return %'] - comparison_df[comparison_df['Strategy']=='100% USDT in Bear'].iloc[0]['Total Return %']:+.2f}%")

        print("\n" + "="*70)
        print("✅ HYBRID REGIME TEST COMPLETE")
        print("="*70 + "\n")

if __name__ == '__main__':
    main()
