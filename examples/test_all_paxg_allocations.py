"""
Test ALL PAXG allocations: 0%, 25%, 50%, 75%, 100%

This script runs the institutional crypto perp strategy with different
bear market allocations to PAXG to find the optimal allocation.

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

# Import the hybrid backtest function
exec(open('examples/test_institutional_crypto_perp_hybrid.py').read().replace('if __name__', 'if False'))

from strategies.institutional_crypto_perp_strategy import InstitutionalCryptoPerp, MarketRegime


def run_allocation_test(allocation_pct):
    """Run backtest with specific PAXG allocation"""

    # Download data
    LOOKBACK_YEARS = 2
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365)).strftime('%Y-%m-%d')

    # Top 30 cryptos + PAXG
    TOP_30_PERPS = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
        'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
        'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'BCH-USD',
        'NEAR-USD', 'APT-USD', 'ARB-USD', 'OP-USD', 'FTM-USD',
        'AAVE-USD', 'MKR-USD', 'SNX-USD', 'RUNE-USD',
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'ICP-USD'
    ]

    all_symbols = TOP_30_PERPS + ['PAXG-USD']

    # Download data
    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()

    for symbol in all_symbols:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty:
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
        except:
            pass

    close_prices = close_prices.fillna(method='ffill', limit=3)
    high_prices = high_prices.fillna(method='ffill', limit=3)
    low_prices = low_prices.fillna(method='ffill', limit=3)

    # Separate PAXG
    paxg_prices = close_prices['PAXG-USD']
    crypto_data = {
        'close': close_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'high': high_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'low': low_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'volume': pd.DataFrame()
    }

    btc_prices = crypto_data['close']['BTC-USD']

    # Initialize strategy
    strategy = InstitutionalCryptoPerp(
        max_positions=10,
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
        max_leverage_bull=1.5,
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
        bear_allocation=allocation_pct
    )

    equity_curve = results['equity_curve']
    trades = results['trades']

    # Calculate metrics
    total_return = ((equity_curve.iloc[-1] / 100000) - 1) * 100
    years = len(equity_curve) / 252
    annualized_return = ((equity_curve.iloc[-1] / 100000) ** (1 / years) - 1) * 100

    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100
    max_drawdown = drawdown.min()

    daily_returns = equity_curve.pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 0 else 0

    # PAXG stats
    paxg_trades = trades[trades['symbol'] == 'PAXG']
    paxg_pnl = paxg_trades[paxg_trades['action'] == 'SELL']['pnl'].sum() if len(paxg_trades) > 0 else 0

    return {
        'allocation': allocation_pct,
        'final_equity': equity_curve.iloc[-1],
        'total_return': total_return,
        'annualized_return': annualized_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'paxg_pnl': paxg_pnl
    }


def main():
    print("="*60)
    print("🧪 TESTING ALL PAXG ALLOCATIONS")
    print("="*60)

    allocations = [0.0, 0.25, 0.50, 0.75, 1.00]
    results = []

    for alloc in allocations:
        print(f"\n📊 Testing {int(alloc*100)}% PAXG allocation during bear markets...")

        result = run_allocation_test(alloc)
        results.append(result)

        print(f"   ✅ Final equity: ${result['final_equity']:,.0f}")
        print(f"   📈 Total return: {result['total_return']:.2f}%")
        print(f"   📊 Sharpe ratio: {result['sharpe_ratio']:.2f}")
        print(f"   💰 PAXG P&L: ${result['paxg_pnl']:,.0f}")

    # Summary table
    print("\n" + "="*60)
    print("📊 SUMMARY: PAXG ALLOCATION COMPARISON")
    print("="*60)

    df = pd.DataFrame(results)

    print(f"\n{'Allocation':<12} {'Final $':<15} {'Total Return':<15} {'Annual Return':<15} {'Sharpe':<10} {'Max DD':<10} {'PAXG P&L':<12}")
    print("-" * 100)

    for _, row in df.iterrows():
        print(f"{int(row['allocation']*100):>3}% PAXG    ${row['final_equity']:>12,.0f}   {row['total_return']:>12.2f}%   {row['annualized_return']:>13.2f}%   {row['sharpe_ratio']:>8.2f}   {row['max_drawdown']:>8.2f}%   ${row['paxg_pnl']:>10,.0f}")

    # Find optimal
    best_idx = df['sharpe_ratio'].idxmax()
    best_alloc = df.loc[best_idx, 'allocation']

    print("\n" + "="*60)
    print(f"🏆 OPTIMAL ALLOCATION: {int(best_alloc*100)}% PAXG")
    print("="*60)
    print(f"   Final Equity: ${df.loc[best_idx, 'final_equity']:,.0f}")
    print(f"   Total Return: {df.loc[best_idx, 'total_return']:.2f}%")
    print(f"   Annualized: {df.loc[best_idx, 'annualized_return']:.2f}%")
    print(f"   Sharpe Ratio: {df.loc[best_idx, 'sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {df.loc[best_idx, 'max_drawdown']:.2f}%")
    print(f"   PAXG P&L: ${df.loc[best_idx, 'paxg_pnl']:,.0f}")

    # Save results
    results_dir = Path(__file__).parent.parent / 'results'
    df.to_csv(results_dir / 'paxg_allocation_comparison.csv', index=False)
    print(f"\n💾 Results saved to {results_dir}/paxg_allocation_comparison.csv")


if __name__ == '__main__':
    main()
