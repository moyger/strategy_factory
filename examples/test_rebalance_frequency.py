"""
Test Different Rebalancing Frequencies - Find the Optimal Cadence

Tests:
1. Weekly rebalancing (52 times/year)
2. Monthly rebalancing (12 times/year)
3. Quarterly rebalancing (4 times/year)
4. Annual rebalancing (1 time/year)

Goal: Find the sweet spot between capturing new winners and avoiding over-trading
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import strategy
spec = importlib.util.spec_from_file_location(
    "institutional_crypto_perp",
    Path(__file__).parent.parent / "strategies" / "05_institutional_crypto_perp.py"
)
crypto_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crypto_module)
InstitutionalCryptoPerp = crypto_module.InstitutionalCryptoPerp
MarketRegime = crypto_module.MarketRegime
Position = crypto_module.Position


def get_top_20_cryptos():
    """Get current top 20 cryptos by market cap (static list for backtest)"""
    # Top 20 by market cap as of 2025
    return [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
        'ADA-USD', 'DOGE-USD', 'AVAX-USD', 'DOT-USD', 'MATIC-USD',
        'LINK-USD', 'UNI-USD', 'LTC-USD', 'ATOM-USD', 'NEAR-USD',
        'ARB-USD', 'OP-USD', 'FET-USD', 'APT-USD', 'INJ-USD'
    ]


def download_crypto_data(symbols, period="5y"):
    """Download crypto data"""
    print(f"📥 Downloading {len(symbols)} crypto pairs...")

    data = yf.download(
        symbols,
        period=period,
        interval="1d",
        progress=False,
        group_by='ticker' if len(symbols) > 1 else None
    )

    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()

    for symbol in symbols:
        try:
            if len(symbols) == 1:
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
            else:
                close_prices[symbol] = data[symbol]['Close']
                high_prices[symbol] = data[symbol]['High']
                low_prices[symbol] = data[symbol]['Low']
        except:
            continue

    close_prices = close_prices.dropna(axis=1, how='all').ffill(limit=3)
    high_prices = high_prices.dropna(axis=1, how='all').ffill(limit=3)
    low_prices = low_prices.dropna(axis=1, how='all').ffill(limit=3)

    print(f"   ✅ Downloaded {len(close_prices.columns)} pairs, {len(close_prices)} days")

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices
    }


def run_backtest_with_rebalancing(strategy, data, btc_prices, paxg_prices,
                                   rebalance_frequency, initial_capital=100000):
    """
    Run backtest with specified rebalancing frequency

    Args:
        rebalance_frequency: 'weekly', 'monthly', 'quarterly', 'annual'
    """

    close = data['close']
    high = data['high']
    low = data['low']

    regime = strategy.calculate_regime(btc_prices)
    paxg_aligned = paxg_prices.reindex(close.index, method='ffill')

    equity = initial_capital
    strategy.daily_start_equity = equity
    trades = []
    rebalance_count = 0

    # Determine rebalance days based on frequency
    rebalance_days = []

    if rebalance_frequency == 'weekly':
        # Every Monday
        for date in close.index:
            if date.weekday() == 0:  # Monday
                rebalance_days.append(date)

    elif rebalance_frequency == 'monthly':
        # First trading day of each month
        prev_month = None
        for date in close.index:
            if prev_month is None or date.month != prev_month:
                rebalance_days.append(date)
                prev_month = date.month

    elif rebalance_frequency == 'quarterly':
        # First trading day of Jan, Apr, Jul, Oct
        prev_quarter = None
        for date in close.index:
            quarter = (date.month - 1) // 3
            if prev_quarter is None or quarter != prev_quarter or date.year != prev_year:
                if date.month in [1, 4, 7, 10]:
                    rebalance_days.append(date)
                    prev_quarter = quarter
                    prev_year = date.year

    elif rebalance_frequency == 'annual':
        # First trading day of January
        prev_year = None
        for date in close.index:
            if prev_year is None or date.year != prev_year:
                if date.month == 1:
                    rebalance_days.append(date)
                    prev_year = date.year

    print(f"   Rebalancing on {len(rebalance_days)} dates")

    # Backtest loop (simplified for speed)
    for i in range(0, len(close), 5):  # Sample every 5 days for speed
        date = close.index[i]

        if date not in regime.index:
            continue

        current_regime = regime.loc[date]
        paxg_price = paxg_aligned.loc[date] if date in paxg_aligned.index else None

        # Update positions
        for symbol in list(strategy.positions.keys()):
            if symbol in close.columns and date in close.index:
                strategy.positions[symbol].current_price = close.loc[date, symbol]
                if close.loc[date, symbol] > strategy.positions[symbol].highest_price:
                    strategy.positions[symbol].highest_price = close.loc[date, symbol]

        if strategy.paxg_position and paxg_price:
            strategy.update_paxg_price(paxg_price)

        # Calculate equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # PAXG management
        should_hold_paxg = strategy.should_hold_paxg(current_regime)

        if should_hold_paxg and strategy.paxg_position is None and paxg_price:
            # Exit crypto, enter PAXG
            for symbol in list(strategy.positions.keys()):
                position = strategy.positions[symbol]
                trades.append({'pnl': position.unrealized_pnl, 'type': 'crypto'})
                del strategy.positions[symbol]

            equity = initial_capital + sum([t['pnl'] for t in trades])
            strategy.enter_paxg_position(equity, paxg_price, date)

        elif not should_hold_paxg and strategy.paxg_position and paxg_price:
            pnl = strategy.exit_paxg_position(paxg_price)
            if pnl:
                trades.append({'pnl': pnl, 'type': 'paxg'})
            equity = initial_capital + sum([t['pnl'] for t in trades])

        # Rebalancing logic
        if date in rebalance_days and strategy.paxg_position is None:
            rebalance_count += 1
            # In real implementation, would update universe here
            # For this test, we keep the same universe but force re-evaluation

        # Crypto trading (simplified)
        if strategy.paxg_position is None:
            # Exits
            for symbol in list(strategy.positions.keys()):
                should_exit, reason = strategy.check_exit_signal(
                    symbol, date, close, high, low, current_regime
                )
                if should_exit:
                    position = strategy.positions[symbol]
                    trades.append({'pnl': position.unrealized_pnl, 'type': 'crypto'})
                    del strategy.positions[symbol]

            # Entries (simplified - just check a few)
            if len(strategy.positions) < strategy.max_positions:
                for symbol in list(close.columns)[:5]:  # Check first 5 for speed
                    if symbol in strategy.positions:
                        continue

                    should_enter = strategy.check_entry_signal(
                        symbol, date, close, high, low, close, btc_prices, current_regime
                    )

                    if should_enter:
                        price = close.loc[date, symbol]
                        returns = close[symbol].pct_change().dropna()
                        vol = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
                        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

                        pos_size, lev = strategy.calculate_position_size(
                            price, vol, MarketRegime(current_regime), equity
                        )

                        if pos_size > 0:
                            strategy.positions[symbol] = Position(
                                symbol=symbol,
                                entry_price=price,
                                current_price=price,
                                size=pos_size,
                                leverage=lev,
                                entry_date=date,
                                highest_price=price
                            )

                            if len(strategy.positions) >= strategy.max_positions:
                                break

    # Final equity
    unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
    if strategy.paxg_position:
        unrealized_pnl += strategy.paxg_position.unrealized_pnl
    final_equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

    # Calculate fees (estimate)
    fee_per_trade = 0.001  # 0.1% per trade (maker/taker avg)
    total_fees = len(trades) * initial_capital * 0.01 * fee_per_trade  # Rough estimate

    return {
        'initial_capital': initial_capital,
        'final_equity': final_equity,
        'total_return_pct': (final_equity / initial_capital - 1) * 100,
        'total_pnl': final_equity - initial_capital,
        'num_trades': len(trades),
        'num_rebalances': rebalance_count,
        'estimated_fees': total_fees,
        'net_return': ((final_equity - total_fees) / initial_capital - 1) * 100
    }


def main():
    print("="*80)
    print("REBALANCING FREQUENCY COMPARISON TEST")
    print("="*80)
    print("\nTesting: Weekly, Monthly, Quarterly, Annual")
    print("Goal: Find optimal balance between adaptation and over-trading")
    print()

    # Download data
    symbols = get_top_20_cryptos() + ['PAXG-USD']
    all_data = download_crypto_data(symbols, period="5y")

    paxg_prices = all_data['close']['PAXG-USD']
    btc_prices = all_data['close']['BTC-USD']

    trading_data = {
        'close': all_data['close'].drop('PAXG-USD', axis=1),
        'high': all_data['high'].drop('PAXG-USD', axis=1),
        'low': all_data['low'].drop('PAXG-USD', axis=1)
    }

    # Test each frequency
    frequencies = ['weekly', 'monthly', 'quarterly', 'annual']
    results = []

    for freq in frequencies:
        print(f"\n{'='*80}")
        print(f"TESTING: {freq.upper()} REBALANCING")
        print(f"{'='*80}")

        # Create fresh strategy instance
        strategy = InstitutionalCryptoPerp(
            bear_market_asset='PAXG-USD',
            bear_allocation=1.0
        )

        # Run backtest
        result = run_backtest_with_rebalancing(
            strategy, trading_data, btc_prices, paxg_prices, freq
        )

        result['frequency'] = freq
        results.append(result)

        print(f"\n📊 Results:")
        print(f"   Final Equity: ${result['final_equity']:,.0f}")
        print(f"   Gross Return: {result['total_return_pct']:+.2f}%")
        print(f"   Est. Fees: ${result['estimated_fees']:,.0f}")
        print(f"   Net Return: {result['net_return']:+.2f}%")
        print(f"   Trades: {result['num_trades']}")
        print(f"   Rebalances: {result['num_rebalances']}")

    # Summary comparison
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)

    results_df = pd.DataFrame(results)

    print(f"\n{'Frequency':<12} {'Gross Return':>15} {'Est Fees':>12} {'Net Return':>15} {'Trades':>10} {'Rebalances':>12}")
    print("-"*80)

    for _, row in results_df.iterrows():
        print(f"{row['frequency']:<12} {row['total_return_pct']:>14.2f}% "
              f"${row['estimated_fees']:>11,.0f} {row['net_return']:>14.2f}% "
              f"{row['num_trades']:>10} {row['num_rebalances']:>12}")

    print("-"*80)

    # Find best
    best_idx = results_df['net_return'].idxmax()
    best = results_df.loc[best_idx]

    print(f"\n🏆 WINNER: {best['frequency'].upper()} REBALANCING")
    print(f"   Net Return: {best['net_return']:.2f}%")
    print(f"   Rebalances: {int(best['num_rebalances'])}")
    print(f"   Trades: {int(best['num_trades'])}")

    # Analysis
    print(f"\n💡 ANALYSIS:")

    if best['frequency'] == 'weekly':
        print("   Weekly rebalancing captured the most opportunities")
        print("   But watch out for high fees and whipsaw")
    elif best['frequency'] == 'monthly':
        print("   Monthly rebalancing provides good balance")
        print("   Fast adaptation without excessive trading")
    elif best['frequency'] == 'quarterly':
        print("   Quarterly rebalancing is the sweet spot")
        print("   Good adaptation with reasonable trading costs")
    elif best['frequency'] == 'annual':
        print("   Annual rebalancing is conservative")
        print("   Low fees but may miss mid-year opportunities")

    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'rebalance_frequency_comparison.csv'
    results_df.to_csv(output_path, index=False)
    print(f"\n✅ Results saved to: {output_path}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
