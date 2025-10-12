"""
Test Nick Radge Crypto Strategy with BSS Qualifier

Compares:
1. Weekly rebalancing vs Monthly rebalancing
2. ROC vs BSS ranking for crypto
3. With/without BTC regime filter

Key differences from stock version:
- 30-day ROC (vs 100-day)
- 50-day MA (vs 100-day)
- BTC 100/50 MA regime (vs SPY 200/50)
- USDT bear asset (vs GLD)
- Weekly/Monthly rebalance (vs Quarterly)
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
START_DATE = '2019-01-01'  # Earlier start for more data
END_DATE = '2025-01-01'
INITIAL_CAPITAL = 10000
FEES = 0.001  # 0.1% (typical CEX fees)
SLIPPAGE = 0.001  # 0.1% (higher than stocks)

# Top cryptos that have long history (2019+)
# Focus on established coins with track record
CRYPTO_UNIVERSE = [
    # Top tier (must have - market leaders)
    'BTC-USD', 'ETH-USD',
    # Large caps with history
    'BNB-USD', 'XRP-USD', 'ADA-USD', 'LTC-USD', 'LINK-USD',
    'DOT-USD', 'UNI-USD', 'DOGE-USD', 'MATIC-USD',
    # DeFi blue chips
    'AAVE-USD', 'MKR-USD',
    # Others with track record
    'ATOM-USD', 'ETC-USD', 'XLM-USD', 'VET-USD', 'FIL-USD',
    # Bear asset
    'USDT-USD'
]

def download_crypto_data():
    """Download historical crypto data from Yahoo Finance"""
    print(f"📊 Downloading data for {len(CRYPTO_UNIVERSE)} cryptos...")
    print(f"📅 Period: {START_DATE} to {END_DATE}\n")

    data = yf.download(CRYPTO_UNIVERSE, start=START_DATE, end=END_DATE,
                       auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
    else:
        prices = data

    # Clean column names (remove -USD suffix for readability)
    prices.columns = [col.replace('-USD', '') for col in prices.columns]

    # Drop columns with too many NaN (coins that didn't exist yet)
    min_data_points = len(prices) * 0.5  # Require 50% data availability
    prices = prices.dropna(thresh=min_data_points, axis=1)

    # Forward fill missing data (crypto trades 24/7, some exchanges have gaps)
    prices = prices.ffill()

    # Drop rows with any remaining NaN
    prices = prices.dropna()

    if len(prices) == 0 or len(prices.columns) == 0:
        raise ValueError("Failed to download crypto data. Check network connection.")

    print(f"✅ Downloaded {len(prices.columns)} cryptos with sufficient data")
    print(f"✅ Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"✅ Total days: {len(prices)}")
    print(f"✅ Available cryptos: {', '.join(prices.columns)}\n")

    return prices

def run_crypto_strategy(prices, strategy_name, rebalance_freq, use_bss=False, use_regime_filter=True):
    """Run crypto strategy with specified configuration"""
    print(f"\n{'='*70}")
    print(f"🔄 Testing {strategy_name}")
    print(f"{'='*70}")

    # Extract BTC for regime filter
    if 'BTC' not in prices.columns:
        raise ValueError("BTC not in dataset - required for regime filter")

    btc_prices = prices['BTC']

    # Initialize strategy
    # RELAXED REGIME: Hold cryptos even in WEAK_BULL (crypto recovers fast)
    # Only go to USDT in severe BEAR (BTC < 100MA)
    strategy = NickRadgeCryptoStrategy(
        portfolio_size=5,  # Smaller portfolio for more concentrated bets
        roc_period=30,  # Crypto moves faster
        ma_period=50,
        rebalance_freq=rebalance_freq,
        use_regime_filter=use_regime_filter,  # Toggle regime filtering
        regime_ma_long=100,  # BTC regime
        regime_ma_short=50,
        strong_bull_positions=5,  # Full portfolio in strong bull
        weak_bull_positions=5,  # KEEP POSITIONS in weak bull (crypto-specific)
        bear_positions=0,      # Only exit in true bear (BTC < 100MA)
        bear_market_asset='USDT',
        bear_allocation=1.0
    )

    # Monkey-patch to use BSS if requested
    if use_bss:
        bss = get_qualifier('bss', poi_period=50, atr_period=14, k=2.0)  # Adjust POI to 50 for crypto

        def rank_cryptos_with_bss(self, prices, indicators, date, benchmark_roc=None):
            if date not in prices.index:
                return pd.DataFrame()

            # Calculate BSS scores
            available_prices = prices.loc[:date].iloc[-150:]  # Last 150 days
            bss_scores = bss.calculate(available_prices)
            latest_scores = bss_scores.loc[date]

            # Apply MA filter
            above_ma = indicators['above_ma'].loc[date]
            valid_cryptos = above_ma[above_ma == True].index
            if self.bear_market_asset:
                valid_cryptos = [c for c in valid_cryptos if c != self.bear_market_asset]

            # Filter BSS scores
            crypto_scores = latest_scores[latest_scores.index.isin(valid_cryptos)]
            crypto_scores = crypto_scores.replace([np.inf, -np.inf], np.nan).dropna()

            if len(crypto_scores) == 0:
                return pd.DataFrame()

            # Sort by BSS score
            ranked = crypto_scores.sort_values(ascending=False)

            return pd.DataFrame({
                'ticker': ranked.index,
                'roc': ranked.values  # Use 'roc' name for compatibility
            })

        strategy.rank_cryptos = lambda prices, indicators, date, benchmark_roc=None: \
            rank_cryptos_with_bss(strategy, prices, indicators, date, benchmark_roc)

    # Run backtest
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

    print(f"\n📊 {strategy_name} Results:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Total Trades: {trades}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Final Value: ${final_value:,.2f}")

    return {
        'Strategy': strategy_name,
        'Rebalance': rebalance_freq,
        'Ranking': 'BSS' if use_bss else 'ROC',
        'Regime Filter': 'Yes' if use_regime_filter else 'No',
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
    print("🔬 CRYPTO STRATEGY COMPARISON")
    print("="*70)
    print("Testing: Weekly vs Monthly | ROC vs BSS | Crypto Universe")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"Fees: {FEES*100}% | Slippage: {SLIPPAGE*100}%")
    print("="*70 + "\n")

    # Download data
    prices = download_crypto_data()

    # Test configurations: with and without regime filter
    # Format: (name, rebalance_freq, use_bss, use_regime_filter)
    configs = [
        # WITHOUT regime filter (always invested, ride or die)
        ('Monthly ROC (No Regime)', 'MS', False, False),
        ('Monthly BSS (No Regime)', 'MS', True, False),
        # WITH regime filter (go to USDT in bear markets)
        ('Monthly ROC (With Regime)', 'MS', False, True),
        ('Monthly BSS (With Regime)', 'MS', True, True),
    ]

    results = []
    for strategy_name, rebalance_freq, use_bss, use_regime_filter in configs:
        try:
            result = run_crypto_strategy(prices, strategy_name, rebalance_freq, use_bss, use_regime_filter)
            results.append(result)
        except Exception as e:
            print(f"\n⚠️  Error testing {strategy_name}: {e}")
            continue

    # Create comparison DataFrame
    if len(results) > 0:
        comparison_df = pd.DataFrame(results)
        comparison_df = comparison_df.sort_values('Total Return %', ascending=False)

        print("\n" + "="*70)
        print("📊 CRYPTO STRATEGY COMPARISON RESULTS")
        print("="*70 + "\n")
        print(comparison_df.to_string(index=False))

        # Save results
        output_file = Path(__file__).parent.parent / 'results' / 'crypto_strategy_comparison.csv'
        output_file.parent.mkdir(exist_ok=True)
        comparison_df.to_csv(output_file, index=False)
        print(f"\n✅ Results saved to: {output_file}")

        # Analysis
        print("\n" + "="*70)
        print("🔍 ANALYSIS")
        print("="*70 + "\n")

        winner = comparison_df.iloc[0]
        print(f"🏆 WINNER: {winner['Strategy']}")
        print(f"   Return: {winner['Total Return %']:.2f}%")
        print(f"   Sharpe: {winner['Sharpe Ratio']:.2f}")
        print(f"   Max DD: {winner['Max Drawdown %']:.2f}%")
        print(f"   Profit Factor: {winner['Profit Factor']:.2f}")

        # Compare regime vs no regime
        no_regime = comparison_df[comparison_df['Regime Filter'] == 'No']
        with_regime = comparison_df[comparison_df['Regime Filter'] == 'Yes']

        if len(no_regime) > 0 and len(with_regime) > 0:
            print(f"\n🛡️  Regime Filter Impact:")
            print(f"   Best NO regime:   {no_regime.iloc[0]['Total Return %']:>8.2f}% "
                  f"(DD: {no_regime.iloc[0]['Max Drawdown %']:>6.2f}%) - {no_regime.iloc[0]['Ranking']}")
            print(f"   Best WITH regime: {with_regime.iloc[0]['Total Return %']:>8.2f}% "
                  f"(DD: {with_regime.iloc[0]['Max Drawdown %']:>6.2f}%) - {with_regime.iloc[0]['Ranking']}")

        # Compare ROC vs BSS
        roc = comparison_df[comparison_df['Ranking'] == 'ROC']
        bss = comparison_df[comparison_df['Ranking'] == 'BSS']

        if len(roc) > 0 and len(bss) > 0:
            print(f"\n📊 ROC vs BSS (best of each):")
            print(f"   Best ROC: {roc.iloc[0]['Total Return %']:>8.2f}% (Regime: {roc.iloc[0]['Regime Filter']})")
            print(f"   Best BSS: {bss.iloc[0]['Total Return %']:>8.2f}% (Regime: {bss.iloc[0]['Regime Filter']})")

        print("\n" + "="*70)
        print("✅ CRYPTO STRATEGY TEST COMPLETE")
        print("="*70 + "\n")

        # Compare to stock baseline
        print("💡 Comparison to Stock Strategy (Quarterly BSS):")
        print("   Stock BSS: 134% return, 1.48 Sharpe, -14% DD")
        print(f"   Crypto {winner['Strategy']}: {winner['Total Return %']:.2f}% return, "
              f"{winner['Sharpe Ratio']:.2f} Sharpe, {winner['Max Drawdown %']:.2f}% DD")
        print("\n   Expected: Crypto has higher volatility and faster rebalancing needs")

if __name__ == '__main__':
    main()
