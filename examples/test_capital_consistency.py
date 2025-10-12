"""
Test if strategy returns are consistent across different starting capitals

The percentage return should be the SAME whether we start with $10K or $100K!
If it's different, there's a bug in the position sizing or capital allocation.
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

CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD'
]


def download_data(symbols, period="5y"):
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

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices
    }


def run_quick_backtest(strategy, data, btc_prices, paxg_prices, initial_capital):
    """Simplified backtest to test capital consistency"""

    close = data['close']
    high = data['high']
    low = data['low']

    regime = strategy.calculate_regime(btc_prices)
    paxg_aligned = paxg_prices.reindex(close.index, method='ffill')

    equity = initial_capital
    strategy.daily_start_equity = equity
    trades = []

    # Sample every 10 days for speed
    sample_indices = range(0, len(close), 10)

    for idx in sample_indices:
        date = close.index[idx]

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
                trades.append({'pnl': position.unrealized_pnl})
                del strategy.positions[symbol]

            equity = initial_capital + sum([t['pnl'] for t in trades])
            strategy.enter_paxg_position(equity, paxg_price, date)

        elif not should_hold_paxg and strategy.paxg_position and paxg_price:
            # Exit PAXG
            pnl = strategy.exit_paxg_position(paxg_price)
            if pnl:
                trades.append({'pnl': pnl})
            equity = initial_capital + sum([t['pnl'] for t in trades])

        # Crypto trading
        if strategy.paxg_position is None:
            # Exits
            for symbol in list(strategy.positions.keys()):
                should_exit, reason = strategy.check_exit_signal(
                    symbol, date, close, high, low, current_regime
                )
                if should_exit:
                    position = strategy.positions[symbol]
                    trades.append({'pnl': position.unrealized_pnl})
                    del strategy.positions[symbol]

            # Entries
            if len(strategy.positions) < strategy.max_positions:
                for symbol in close.columns:
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

    return {
        'initial_capital': initial_capital,
        'final_equity': final_equity,
        'total_return_pct': (final_equity / initial_capital - 1) * 100,
        'total_pnl': final_equity - initial_capital,
        'num_trades': len(trades)
    }


def main():
    print("="*80)
    print("TESTING CAPITAL CONSISTENCY")
    print("="*80)
    print("\nThe percentage return should be IDENTICAL regardless of starting capital!")
    print()

    # Download data
    symbols = CRYPTO_UNIVERSE + ['PAXG-USD']
    all_data = download_data(symbols, period="5y")

    paxg_prices = all_data['close']['PAXG-USD']
    btc_prices = all_data['close']['BTC-USD']

    trading_data = {
        'close': all_data['close'].drop('PAXG-USD', axis=1),
        'high': all_data['high'].drop('PAXG-USD', axis=1),
        'low': all_data['low'].drop('PAXG-USD', axis=1)
    }

    # Test with different capital amounts
    test_capitals = [10000, 50000, 100000, 500000, 1000000]

    print("\n" + "="*80)
    print("TESTING WITH DIFFERENT STARTING CAPITALS")
    print("="*80)
    print(f"\n{'Initial Capital':>20} {'Final Equity':>20} {'Total Return':>15} {'P&L':>20}")
    print("-"*80)

    results = []

    for capital in test_capitals:
        # Create fresh strategy instance
        strategy = InstitutionalCryptoPerp(
            bear_market_asset='PAXG-USD',
            bear_allocation=1.0
        )

        # Run backtest
        result = run_quick_backtest(strategy, trading_data, btc_prices, paxg_prices, capital)
        results.append(result)

        print(f"${result['initial_capital']:>19,} ${result['final_equity']:>19,.0f} "
              f"{result['total_return_pct']:>14.2f}% ${result['total_pnl']:>19,.0f}")

    print("-"*80)

    # Check consistency
    returns = [r['total_return_pct'] for r in results]
    return_std = np.std(returns)
    return_mean = np.mean(returns)

    print(f"\n📊 CONSISTENCY CHECK:")
    print(f"   Average Return: {return_mean:.2f}%")
    print(f"   Std Deviation: {return_std:.4f}%")

    if return_std < 0.01:
        print(f"   ✅ EXCELLENT - Returns are consistent!")
    elif return_std < 1.0:
        print(f"   ✅ GOOD - Returns are mostly consistent (minor rounding differences)")
    else:
        print(f"   ❌ PROBLEM - Returns vary significantly!")
        print(f"   🐛 This indicates a BUG in position sizing or capital allocation!")
        print(f"\n   Possible causes:")
        print(f"   - Position size calculation uses fixed dollar amounts instead of percentages")
        print(f"   - Leverage calculation doesn't scale with capital")
        print(f"   - Min/max position size constraints are dollar-based not %-based")

    # Show the actual previous $10K test you mentioned
    print("\n" + "="*80)
    print("INVESTIGATING YOUR $10K → $98K RESULT")
    print("="*80)
    print(f"\nYou mentioned: $10,000 → $98,000+ (500%+ return)")
    print(f"Our test shows: $10,000 → ${results[0]['final_equity']:,.0f} ({results[0]['total_return_pct']:.2f}% return)")
    print(f"\nDifference: ${98000 - results[0]['final_equity']:,.0f}")

    if results[0]['total_return_pct'] < 500:
        print(f"\n❗ Our test shows LOWER returns than you reported!")
        print(f"\nPossible explanations:")
        print(f"1. Different test period (maybe you tested 2023-2025 bull market only?)")
        print(f"2. Different strategy parameters (higher leverage, more positions?)")
        print(f"3. Bug in our current backtest (missing trades, incorrect exits?)")
        print(f"4. Your test included leveraged gains that we're not capturing")
        print(f"\n💡 Recommendation: Check if your previous test was on a shorter, bullish period")


if __name__ == "__main__":
    main()
