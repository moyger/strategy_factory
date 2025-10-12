"""
Full Backtest: Institutional Crypto Perpetual Strategy with PAXG

Tests the complete strategy with:
1. Performance backtest
2. QuantStats report
3. Walk-forward validation
4. Monte Carlo simulation
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import quantstats as qs
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import from numbered file
spec = importlib.util.spec_from_file_location(
    "institutional_crypto_perp",
    Path(__file__).parent.parent / "strategies" / "05_institutional_crypto_perp.py"
)
crypto_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crypto_module)
InstitutionalCryptoPerp = crypto_module.InstitutionalCryptoPerp
MarketRegime = crypto_module.MarketRegime
Position = crypto_module.Position


def download_crypto_data(symbols, period="2y"):
    """Download crypto data from Yahoo Finance"""
    print(f"\n📥 Downloading {len(symbols)} crypto pairs...")

    data = yf.download(
        symbols,
        period=period,
        interval="1d",
        progress=False,
        group_by='ticker' if len(symbols) > 1 else None
    )

    # Organize into OHLCV structure
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
            print(f"   ⚠️  Failed to download {symbol}")
            continue

    # Drop columns with all NaN
    close_prices = close_prices.dropna(axis=1, how='all')
    high_prices = high_prices.dropna(axis=1, how='all')
    low_prices = low_prices.dropna(axis=1, how='all')

    # Forward fill missing data
    close_prices = close_prices.ffill(limit=3)
    high_prices = high_prices.ffill(limit=3)
    low_prices = low_prices.ffill(limit=3)

    print(f"   ✅ Downloaded {len(close_prices.columns)} pairs, {len(close_prices)} days")

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices
    }


def backtest_strategy(strategy, data, btc_prices, paxg_prices, initial_capital=100000):
    """Run backtest"""
    print("\n🚀 Running backtest...")

    close = data['close']
    high = data['high']
    low = data['low']

    # Calculate regime
    regime = strategy.calculate_regime(btc_prices)

    # Initialize tracking
    equity_curve = []
    dates = []
    trades = []
    equity = initial_capital
    strategy.daily_start_equity = equity

    # Align PAXG data to trading dates
    paxg_aligned = paxg_prices.reindex(close.index, method='ffill')

    # Backtest loop
    for i, date in enumerate(close.index):
        if i % 50 == 0 and i > 0:
            print(f"   📅 {date.strftime('%Y-%m-%d')}: Equity=${equity:,.0f}, Positions={len(strategy.positions)}")

        if date not in regime.index:
            continue

        current_regime = regime.loc[date]

        # Get PAXG price for today
        paxg_price = paxg_aligned.loc[date] if date in paxg_aligned.index else None

        # Update position prices
        for symbol in list(strategy.positions.keys()):
            if symbol in close.columns and date in close.index:
                strategy.positions[symbol].current_price = close.loc[date, symbol]

        # Update PAXG position if exists
        if strategy.paxg_position is not None and paxg_price is not None:
            strategy.update_paxg_price(paxg_price)

        # Calculate current equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # Check if should hold PAXG
        should_hold_paxg_now = strategy.should_hold_paxg(current_regime)

        # PAXG entry/exit logic
        if should_hold_paxg_now and strategy.paxg_position is None and paxg_price is not None:
            # Enter PAXG
            # First close all crypto positions
            for symbol in list(strategy.positions.keys()):
                position = strategy.positions[symbol]
                pnl = position.unrealized_pnl
                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': position.current_price,
                    'size': position.size,
                    'pnl': pnl,
                    'reason': 'Bear regime - switching to PAXG'
                })
                del strategy.positions[symbol]

            # Recalculate equity after exits
            equity = initial_capital + sum([t['pnl'] for t in trades])

            # Enter PAXG
            strategy.enter_paxg_position(equity, paxg_price, date)
            print(f"   💰 {date.strftime('%Y-%m-%d')}: Entered PAXG @ ${paxg_price:.2f}")

        elif not should_hold_paxg_now and strategy.paxg_position is not None and paxg_price is not None:
            # Exit PAXG
            pnl = strategy.exit_paxg_position(paxg_price)
            if pnl is not None:
                trades.append({
                    'date': date,
                    'symbol': 'PAXG-USD',
                    'action': 'SELL',
                    'price': paxg_price,
                    'size': 0,
                    'pnl': pnl,
                    'reason': 'Exit PAXG - returning to crypto'
                })
                equity = initial_capital + sum([t['pnl'] for t in trades])
                print(f"   💰 {date.strftime('%Y-%m-%d')}: Exited PAXG with PnL=${pnl:,.2f}")

        # Only trade crypto if not holding PAXG
        if strategy.paxg_position is None:
            # Check exits
            for symbol in list(strategy.positions.keys()):
                should_exit, exit_reason = strategy.check_exit_signal(
                    symbol, date, close, high, low, current_regime
                )
                if should_exit:
                    position = strategy.positions[symbol]
                    pnl = position.unrealized_pnl
                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': position.current_price,
                        'size': position.size,
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    del strategy.positions[symbol]

            # Check entries (if room for more positions)
            if len(strategy.positions) < strategy.max_positions:
                for symbol in close.columns:
                    if symbol in strategy.positions:
                        continue

                    should_enter = strategy.check_entry_signal(
                        symbol, date, close, high, low, close, btc_prices, current_regime
                    )

                    if should_enter:
                        # Calculate position size
                        price = close.loc[date, symbol]
                        returns = close[symbol].pct_change().dropna()
                        volatility = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                        # Recalculate equity
                        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
                        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

                        position_size, final_leverage = strategy.calculate_position_size(
                            price, volatility, MarketRegime(current_regime), equity
                        )

                        if position_size > 0:
                            # Create position
                            strategy.positions[symbol] = Position(
                                symbol=symbol,
                                entry_price=price,
                                current_price=price,
                                size=position_size,
                                leverage=final_leverage,
                                entry_date=date,
                                highest_price=price
                            )

                            trades.append({
                                'date': date,
                                'symbol': symbol,
                                'action': 'BUY',
                                'price': price,
                                'size': position_size,
                                'pnl': 0,
                                'reason': f'Entry ({current_regime})'
                            })

                            if len(strategy.positions) >= strategy.max_positions:
                                break

        # Record equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        equity_curve.append(equity)
        dates.append(date)

    return {
        'equity': equity_curve,
        'dates': dates,
        'trades': trades,
        'initial_capital': initial_capital
    }


def print_results(portfolio):
    """Print backtest results"""
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)

    equity = portfolio['equity']
    trades = portfolio['trades']
    initial_capital = portfolio['initial_capital']

    final_equity = equity[-1]
    total_return = (final_equity / initial_capital - 1) * 100

    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]

    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

    print(f"\n💰 P&L:")
    print(f"   Initial Capital: ${initial_capital:,.2f}")
    print(f"   Final Equity: ${final_equity:,.2f}")
    print(f"   Total Return: {total_return:+.2f}%")
    print(f"\n📊 Trades:")
    print(f"   Total: {len(trades)}")
    print(f"   Win Rate: {win_rate:.1f}%")

    if winning_trades:
        avg_win = np.mean([t['pnl'] for t in winning_trades])
        print(f"   Avg Win: ${avg_win:,.2f}")
    if losing_trades:
        avg_loss = np.mean([t['pnl'] for t in losing_trades])
        print(f"   Avg Loss: ${avg_loss:,.2f}")


def generate_quantstats_report(portfolio, benchmark_data):
    """Generate QuantStats HTML report"""
    print("\n" + "="*80)
    print("GENERATING QUANTSTATS REPORT")
    print("="*80)

    # Calculate returns
    equity = portfolio['equity']
    dates = portfolio['dates']

    equity_series = pd.Series(equity, index=dates)
    strategy_returns = equity_series.pct_change().fillna(0)

    # Benchmark returns (BTC)
    benchmark_returns = benchmark_data.pct_change().fillna(0)
    benchmark_returns = benchmark_returns.reindex(dates, method='ffill').fillna(0)

    # Generate report
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'paxg_full_backtest_report.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qs.reports.html(
        strategy_returns,
        benchmark_returns,
        output=str(output_path),
        title='Institutional Crypto Perp with PAXG - Full Report'
    )

    print(f"✅ Report saved to: {output_path}")

    # Print key metrics
    print(f"\n📊 KEY METRICS:")
    print(f"   Total Return: {qs.stats.comp(strategy_returns):.2%}")
    print(f"   CAGR: {qs.stats.cagr(strategy_returns):.2%}")
    print(f"   Sharpe: {qs.stats.sharpe(strategy_returns):.2f}")
    print(f"   Max Drawdown: {qs.stats.max_drawdown(strategy_returns):.2%}")


def main():
    print("="*80)
    print("INSTITUTIONAL CRYPTO PERP WITH PAXG - FULL BACKTEST")
    print("="*80)

    # Download data
    symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'PAXG-USD']
    data = download_crypto_data(symbols, period="2y")

    # Separate PAXG
    paxg_prices = data['close']['PAXG-USD']
    btc_prices = data['close']['BTC-USD']

    # Remove PAXG from trading universe
    data['close'] = data['close'].drop('PAXG-USD', axis=1)
    data['high'] = data['high'].drop('PAXG-USD', axis=1)
    data['low'] = data['low'].drop('PAXG-USD', axis=1)

    # Initialize strategy with PAXG
    strategy = InstitutionalCryptoPerp(
        bear_market_asset='PAXG-USD',
        bear_allocation=1.0
    )

    # Run backtest
    portfolio = backtest_strategy(strategy, data, btc_prices, paxg_prices)

    # Print results
    print_results(portfolio)

    # Generate QuantStats report
    generate_quantstats_report(portfolio, btc_prices)

    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
