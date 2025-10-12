"""
Test Institutional Crypto Perp Strategy - 5 YEAR BACKTEST

This tests the strategy on 5 years of data (2020-2025) to validate:
- Performance across full crypto cycle (2021 bull, 2022 bear, 2023-2025 recovery)
- Robustness of the "5 positions max" optimization
- 100% PAXG bear allocation effectiveness

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import hybrid backtest
exec(open('examples/test_institutional_crypto_perp_hybrid.py').read().replace('if __name__', 'if False'))

from strategies.institutional_crypto_perp_strategy import InstitutionalCryptoPerp, MarketRegime


def run_5year_backtest(max_positions=10, bear_allocation=1.0, leverage=1.5, config_name=""):
    """Run 5-year backtest with specified configuration"""

    print(f"\n{'='*80}")
    print(f"📊 TESTING: {config_name}")
    print(f"{'='*80}")

    # 5 year lookback
    LOOKBACK_YEARS = 5
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365 + 30)).strftime('%Y-%m-%d')

    print(f"\n📅 Period: {start_date} → {end_date} ({LOOKBACK_YEARS} years)")

    # Top cryptos (some may not have existed in 2020)
    TOP_CRYPTOS = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'DOGE-USD',
        'XRP-USD', 'DOT-USD', 'UNI-USD', 'LINK-USD', 'LTC-USD',
        'BCH-USD', 'ATOM-USD', 'AAVE-USD', 'AVAX-USD', 'MATIC-USD',
        'SOL-USD', 'FTM-USD', 'SAND-USD', 'MANA-USD', 'AXS-USD',
        'NEAR-USD', 'RUNE-USD', 'SNX-USD', 'MKR-USD', 'ICP-USD',
        'ARB-USD', 'OP-USD', 'APT-USD'
    ]

    all_symbols = TOP_CRYPTOS + ['PAXG-USD']

    print(f"📥 Downloading {len(all_symbols)} symbols...")

    # Download data
    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()

    for symbol in all_symbols:
        try:
            print(f"   Downloading {symbol}...", end='')
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty and len(data) > 250:  # At least 250 days of data
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
                print(f" ✅ ({len(data)} days)")
            else:
                print(f" ⚠️  Skipped (insufficient data)")
        except Exception as e:
            print(f" ❌ Failed: {e}")

    # Forward fill
    close_prices = close_prices.fillna(method='ffill', limit=5)
    high_prices = high_prices.fillna(method='ffill', limit=5)
    low_prices = low_prices.fillna(method='ffill', limit=5)

    print(f"\n✅ Downloaded {len(close_prices.columns)} symbols with {len(close_prices)} days of data")

    # Separate PAXG
    if 'PAXG-USD' not in close_prices.columns:
        print("\n❌ ERROR: PAXG-USD not available")
        return None

    paxg_prices = close_prices['PAXG-USD']
    crypto_data = {
        'close': close_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'high': high_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'low': low_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'volume': pd.DataFrame()
    }

    if 'BTC-USD' not in crypto_data['close'].columns:
        print("\n❌ ERROR: BTC-USD not available")
        return None

    btc_prices = crypto_data['close']['BTC-USD']

    # Initialize strategy
    print(f"\n⚙️  Initializing strategy...")
    print(f"   Max positions: {max_positions}")
    print(f"   Max leverage (bull): {leverage}×")
    print(f"   Bear allocation: {bear_allocation*100}% PAXG")

    strategy = InstitutionalCryptoPerp(
        max_positions=max_positions,
        btc_ma_long=200,
        btc_ma_short=20,
        vol_lookback=30,
        vol_percentile_low=20,
        vol_percentile_high=150,
        donchian_period=20,
        adx_threshold=20,
        rs_quartile=0.50,
        add_atr_multiple=0.75,
        max_adds=3,
        trail_atr_multiple=2.0,
        breakdown_period=10,
        vol_target_per_position=0.20,
        portfolio_vol_target=0.50,
        max_leverage_bull=leverage,
        max_leverage_neutral=1.0,
        max_leverage_bear=0.5,
        daily_loss_limit=0.03,
        weekend_degross=False
    )

    # Run backtest
    results = backtest_hybrid_perp(
        strategy=strategy,
        data=crypto_data,
        btc_prices=btc_prices,
        paxg_prices=paxg_prices,
        initial_capital=100000,
        bear_allocation=bear_allocation
    )

    # Calculate metrics
    equity_curve = results['equity_curve']
    trades = results['trades']
    regime_history = results['regime_history']

    total_return = ((equity_curve.iloc[-1] / 100000) - 1) * 100
    years = len(equity_curve) / 252
    annualized_return = ((equity_curve.iloc[-1] / 100000) ** (1 / years) - 1) * 100

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100
    max_drawdown = drawdown.min()

    daily_returns = equity_curve.pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    # PAXG stats
    paxg_trades = trades[trades['symbol'] == 'PAXG']
    paxg_pnl = paxg_trades[paxg_trades['action'] == 'SELL']['pnl'].sum() if len(paxg_trades) > 0 else 0

    # Crypto stats
    crypto_trades = trades[trades['symbol'] != 'PAXG']
    sell_trades = crypto_trades[crypto_trades['action'] == 'SELL']

    # Regime stats
    regime_counts = regime_history.value_counts()

    # Print results
    print(f"\n{'='*80}")
    print(f"📊 RESULTS: {config_name}")
    print(f"{'='*80}")

    print(f"\n💰 Performance:")
    print(f"   Initial Capital: $100,000")
    print(f"   Final Equity: ${equity_curve.iloc[-1]:,.0f}")
    print(f"   Total Return: {total_return:,.1f}%")
    print(f"   Annualized Return: {annualized_return:.1f}%")
    print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")

    print(f"\n🌍 Regime Distribution:")
    for regime, count in regime_counts.items():
        pct = count / len(regime_history) * 100
        print(f"   {regime}: {count} days ({pct:.1f}%)")

    print(f"\n📈 Trading Stats:")
    print(f"   Total trades: {len(sell_trades)}")
    print(f"   Avg trades/year: {len(sell_trades) / years:.0f}")

    if len(sell_trades) > 0:
        winning = sell_trades[sell_trades['pnl'] > 0]
        losing = sell_trades[sell_trades['pnl'] < 0]

        win_rate = len(winning) / len(sell_trades) * 100
        avg_win = winning['pnl'].mean() if len(winning) > 0 else 0
        avg_loss = losing['pnl'].mean() if len(losing) > 0 else 0

        print(f"   Win rate: {win_rate:.1f}%")
        print(f"   Avg win: ${avg_win:,.0f}")
        print(f"   Avg loss: ${avg_loss:,.0f}")

    print(f"\n🟡 PAXG Contribution:")
    print(f"   Total P&L from PAXG: ${paxg_pnl:,.0f}")
    print(f"   % of total profit: {paxg_pnl / (equity_curve.iloc[-1] - 100000) * 100:.1f}%")

    # Top performers
    if len(sell_trades) > 0:
        top_performers = sell_trades.groupby('symbol')['pnl'].sum().sort_values(ascending=False).head(10)

        print(f"\n🏆 Top 10 Performers:")
        for i, (symbol, pnl) in enumerate(top_performers.items(), 1):
            print(f"   {i}. {symbol}: ${pnl:,.0f}")

    return {
        'config': config_name,
        'final_equity': equity_curve.iloc[-1],
        'total_return': total_return,
        'annualized': annualized_return,
        'sharpe': sharpe_ratio,
        'max_dd': max_drawdown,
        'trades': len(sell_trades),
        'paxg_pnl': paxg_pnl,
        'equity_curve': equity_curve,
        'regime_history': regime_history
    }


def main():
    """Main execution"""

    print("="*80)
    print("🏛️  INSTITUTIONAL CRYPTO PERP - 5 YEAR BACKTEST")
    print("="*80)

    # Test configurations
    configs = [
        {
            'name': 'BASELINE (10 pos, 1.5× lev, 100% PAXG)',
            'max_positions': 10,
            'leverage': 1.5,
            'bear_allocation': 1.0
        },
        {
            'name': 'OPTIMIZED (5 pos, 1.5× lev, 100% PAXG)',
            'max_positions': 5,
            'leverage': 1.5,
            'bear_allocation': 1.0
        },
        {
            'name': 'CONSERVATIVE (5 pos, 1.0× lev, 100% PAXG)',
            'max_positions': 5,
            'leverage': 1.0,
            'bear_allocation': 1.0
        }
    ]

    results = []

    for config in configs:
        result = run_5year_backtest(
            max_positions=config['max_positions'],
            bear_allocation=config['bear_allocation'],
            leverage=config['leverage'],
            config_name=config['name']
        )

        if result:
            results.append(result)

    # Comparison
    if len(results) > 1:
        print("\n" + "="*80)
        print("📊 COMPARISON - 5 YEAR RESULTS")
        print("="*80)

        print(f"\n{'Configuration':<45} {'Final $':<15} {'Return':<12} {'Annual':<10} {'Sharpe':<10} {'Max DD':<10} {'Trades'}")
        print("-" * 115)

        for r in results:
            print(f"{r['config']:<45} ${r['final_equity']:>12,.0f}   {r['total_return']:>9.1f}%   {r['annualized']:>8.1f}%   {r['sharpe']:>8.2f}   {r['max_dd']:>8.2f}%   {r['trades']:>6.0f}")

        # Best by metric
        print("\n" + "="*80)
        print("🏆 WINNERS BY METRIC")
        print("="*80)

        df = pd.DataFrame(results)

        best_return_idx = df['total_return'].idxmax()
        best_sharpe_idx = df['sharpe'].idxmax()
        best_dd_idx = df['max_dd'].idxmax()  # Highest (least negative)

        print(f"\n💰 Highest Return: {df.loc[best_return_idx, 'config']}")
        print(f"   Return: {df.loc[best_return_idx, 'total_return']:.1f}%")

        print(f"\n📊 Best Sharpe: {df.loc[best_sharpe_idx, 'config']}")
        print(f"   Sharpe: {df.loc[best_sharpe_idx, 'sharpe']:.2f}")

        print(f"\n🛡️  Lowest Drawdown: {df.loc[best_dd_idx, 'config']}")
        print(f"   Max DD: {df.loc[best_dd_idx, 'max_dd']:.2f}%")

    # Save results
    if len(results) > 0:
        print("\n💾 Saving results...")
        results_dir = Path(__file__).parent.parent / 'results'
        results_dir.mkdir(exist_ok=True)

        # Save equity curves
        for r in results:
            filename = r['config'].replace(' ', '_').replace('(', '').replace(')', '').replace(',', '').lower()
            r['equity_curve'].to_csv(results_dir / f'5year_{filename}_equity.csv')

        print(f"   ✅ Saved to {results_dir}/")

    print("\n✨ 5-year backtest complete!")


if __name__ == '__main__':
    main()
