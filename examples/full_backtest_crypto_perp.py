"""
FULL BACKTEST: Institutional Crypto Perpetual Strategy with PAXG

This is a COMPLETE backtest including:
1. Performance backtest with crypto trading (Donchian, ADX, trailing stops, etc.)
2. PAXG bear market allocation
3. QuantStats report (MANDATORY)
4. Walk-forward validation (MANDATORY)
5. Monte Carlo simulation (MANDATORY)

Strategy: 05_institutional_crypto_perp.py
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

# Top crypto pairs by volume
CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD'
]


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
        except Exception as e:
            print(f"   ⚠️  Failed to download {symbol}: {e}")
            continue

    # Drop columns with all NaN
    close_prices = close_prices.dropna(axis=1, how='all')
    high_prices = high_prices.dropna(axis=1, how='all')
    low_prices = low_prices.dropna(axis=1, how='all')

    # Forward fill missing data (up to 3 days)
    close_prices = close_prices.ffill(limit=3)
    high_prices = high_prices.ffill(limit=3)
    low_prices = low_prices.ffill(limit=3)

    print(f"   ✅ Successfully downloaded {len(close_prices.columns)} pairs")
    print(f"   📊 Data points: {len(close_prices)} days")

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices
    }


def backtest_institutional_perp(strategy, data, btc_prices, paxg_prices, initial_capital=100000):
    """
    Run complete backtest with crypto trading + PAXG allocation
    """
    print("\n🚀 Running institutional crypto perp backtest...")

    close = data['close']
    high = data['high']
    low = data['low']

    # Calculate regime
    print("   📈 Calculating market regime...")
    regime = strategy.calculate_regime(btc_prices)

    # Initialize tracking
    equity_curve = []
    dates = []
    trades = []
    regime_history = []

    equity = initial_capital
    strategy.daily_start_equity = equity

    # Align PAXG data
    paxg_aligned = paxg_prices.reindex(close.index, method='ffill')

    # Track regime statistics
    regime_stats = {
        MarketRegime.BULL_RISK_ON.value: {'days': 0, 'pnl': 0, 'trades': 0},
        MarketRegime.NEUTRAL.value: {'days': 0, 'pnl': 0, 'trades': 0},
        MarketRegime.BEAR_RISK_OFF.value: {'days': 0, 'pnl': 0, 'trades': 0}
    }

    # Backtest loop
    total_days = len(close)
    for i, date in enumerate(close.index):
        if i % 100 == 0:
            paxg_status = "PAXG" if strategy.paxg_position else f"{len(strategy.positions)} crypto"
            print(f"   📅 {date.strftime('%Y-%m-%d')} ({i}/{total_days}): Equity=${equity:,.0f}, Positions={paxg_status}")

        if date not in regime.index:
            continue

        current_regime = regime.loc[date]
        regime_stats[current_regime]['days'] += 1
        regime_history.append(current_regime)

        # Reset daily start equity at beginning of each day
        if len(equity_curve) > 0 and dates[-1].date() != date.date():
            strategy.daily_start_equity = equity

        # Get PAXG price
        paxg_price = paxg_aligned.loc[date] if date in paxg_aligned.index else None

        # Update position prices
        for symbol in list(strategy.positions.keys()):
            if symbol in close.columns and date in close.index:
                current_price = close.loc[date, symbol]
                strategy.positions[symbol].current_price = current_price
                # Update highest price for trailing stop
                if current_price > strategy.positions[symbol].highest_price:
                    strategy.positions[symbol].highest_price = current_price

        # Update PAXG position
        if strategy.paxg_position is not None and paxg_price is not None:
            strategy.update_paxg_price(paxg_price)

        # Calculate current equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # Check if should hold PAXG
        should_hold_paxg_now = strategy.should_hold_paxg(current_regime)

        # PAXG ENTRY: Bear regime - exit all crypto, enter PAXG
        if should_hold_paxg_now and strategy.paxg_position is None and paxg_price is not None:
            # Close all crypto positions
            for symbol in list(strategy.positions.keys()):
                position = strategy.positions[symbol]
                pnl = position.unrealized_pnl

                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': position.current_price,
                    'pnl': pnl,
                    'reason': 'BEAR regime - switching to PAXG'
                })

                regime_stats[current_regime]['pnl'] += pnl
                regime_stats[current_regime]['trades'] += 1
                del strategy.positions[symbol]

            # Recalculate equity
            equity = initial_capital + sum([t['pnl'] for t in trades])

            # Enter PAXG
            strategy.enter_paxg_position(equity, paxg_price, date)

        # PAXG EXIT: Return to bull/neutral - exit PAXG, ready to trade crypto
        elif not should_hold_paxg_now and strategy.paxg_position is not None and paxg_price is not None:
            pnl = strategy.exit_paxg_position(paxg_price)
            if pnl is not None:
                trades.append({
                    'date': date,
                    'symbol': 'PAXG-USD',
                    'action': 'SELL',
                    'price': paxg_price,
                    'pnl': pnl,
                    'reason': 'Exiting PAXG - returning to crypto'
                })
                regime_stats[MarketRegime.BEAR_RISK_OFF.value]['pnl'] += pnl
                regime_stats[MarketRegime.BEAR_RISK_OFF.value]['trades'] += 1
                equity = initial_capital + sum([t['pnl'] for t in trades])

        # CRYPTO TRADING: Only if not holding PAXG
        if strategy.paxg_position is None:
            # Check risk limits
            breach, reason = strategy.check_risk_limits(date, equity)
            if breach:
                # Close all positions
                for symbol in list(strategy.positions.keys()):
                    position = strategy.positions[symbol]
                    pnl = position.unrealized_pnl

                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': position.current_price,
                        'pnl': pnl,
                        'reason': reason
                    })

                    regime_stats[current_regime]['pnl'] += pnl
                    regime_stats[current_regime]['trades'] += 1
                    del strategy.positions[symbol]

            # Check exits for existing positions
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
                        'pnl': pnl,
                        'reason': exit_reason
                    })

                    regime_stats[current_regime]['pnl'] += pnl
                    regime_stats[current_regime]['trades'] += 1
                    del strategy.positions[symbol]

            # Check entries (if room for more positions)
            if len(strategy.positions) < strategy.max_positions:
                for symbol in close.columns:
                    if symbol in strategy.positions:
                        continue

                    # Check entry signal
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

                        position_size, leverage = strategy.calculate_position_size(
                            price, volatility, MarketRegime(current_regime), equity
                        )

                        if position_size > 0:
                            # Create position
                            strategy.positions[symbol] = Position(
                                symbol=symbol,
                                entry_price=price,
                                current_price=price,
                                size=position_size,
                                leverage=leverage,
                                entry_date=date,
                                highest_price=price
                            )

                            trades.append({
                                'date': date,
                                'symbol': symbol,
                                'action': 'BUY',
                                'price': price,
                                'pnl': 0,
                                'reason': f'Entry ({current_regime})'
                            })

                            regime_stats[current_regime]['trades'] += 1

                            if len(strategy.positions) >= strategy.max_positions:
                                break

        # Record equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        equity_curve.append(equity)
        dates.append(date)

    # Close any remaining positions
    for symbol in list(strategy.positions.keys()):
        position = strategy.positions[symbol]
        pnl = position.unrealized_pnl
        trades.append({
            'date': dates[-1],
            'symbol': symbol,
            'action': 'SELL',
            'price': position.current_price,
            'pnl': pnl,
            'reason': 'End of backtest'
        })

    if strategy.paxg_position:
        pnl = strategy.paxg_position.unrealized_pnl
        trades.append({
            'date': dates[-1],
            'symbol': 'PAXG-USD',
            'action': 'SELL',
            'price': strategy.paxg_position.current_price,
            'pnl': pnl,
            'reason': 'End of backtest'
        })

    return {
        'equity': equity_curve,
        'dates': dates,
        'trades': trades,
        'regime_stats': regime_stats,
        'regime_history': regime_history,
        'initial_capital': initial_capital
    }


def print_results(portfolio):
    """Print backtest results"""
    print("\n" + "="*80)
    print("COMPONENT 1: PERFORMANCE BACKTEST RESULTS")
    print("="*80)

    equity = portfolio['equity']
    trades = [t for t in portfolio['trades'] if t['action'] == 'SELL']
    initial_capital = portfolio['initial_capital']
    regime_stats = portfolio['regime_stats']

    final_equity = equity[-1]
    total_return = (final_equity / initial_capital - 1) * 100

    # Trade statistics
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    crypto_trades = [t for t in trades if t['symbol'] != 'PAXG-USD']
    paxg_trades = [t for t in trades if t['symbol'] == 'PAXG-USD']

    win_rate = len(winning_trades) / len(trades) * 100 if trades else 0

    print(f"\n💰 P&L:")
    print(f"   Initial Capital: ${initial_capital:,.2f}")
    print(f"   Final Equity: ${final_equity:,.2f}")
    print(f"   Total Return: {total_return:+.2f}%")
    print(f"   Total P&L: ${final_equity - initial_capital:+,.2f}")

    print(f"\n📊 Trades:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Crypto Trades: {len(crypto_trades)}")
    print(f"   PAXG Trades: {len(paxg_trades)}")
    print(f"   Win Rate: {win_rate:.1f}%")

    if winning_trades:
        avg_win = np.mean([t['pnl'] for t in winning_trades])
        print(f"   Avg Win: ${avg_win:,.2f}")
    if losing_trades:
        avg_loss = np.mean([t['pnl'] for t in losing_trades])
        print(f"   Avg Loss: ${avg_loss:,.2f}")

    print(f"\n📈 Regime Performance:")
    for regime_name, stats in regime_stats.items():
        days = stats['days']
        pnl = stats['pnl']
        trades_count = stats['trades']
        print(f"   {regime_name:20s}: {days:4d} days, {trades_count:3d} trades, P&L=${pnl:+,.2f}")


def generate_quantstats_report(portfolio, benchmark_data):
    """COMPONENT 2: Generate QuantStats HTML report (MANDATORY)"""
    print("\n" + "="*80)
    print("COMPONENT 2: QUANTSTATS REPORT")
    print("="*80)

    # Calculate returns
    equity = portfolio['equity']
    dates = portfolio['dates']

    equity_series = pd.Series(equity, index=dates)
    strategy_returns = equity_series.pct_change().fillna(0)

    # Benchmark returns (BTC buy & hold)
    benchmark_returns = benchmark_data.pct_change().fillna(0)
    benchmark_returns = benchmark_returns.reindex(dates, method='ffill').fillna(0)

    # Generate report
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'institutional_perp_full_report.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating QuantStats report...")
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
    print(f"   Sharpe Ratio: {qs.stats.sharpe(strategy_returns):.2f}")
    print(f"   Max Drawdown: {qs.stats.max_drawdown(strategy_returns):.2%}")
    print(f"   Calmar Ratio: {qs.stats.calmar(strategy_returns):.2f}")

    return output_path


def run_walk_forward_validation(data, btc_prices, paxg_prices, n_folds=6):
    """COMPONENT 3: Walk-Forward Validation (MANDATORY)"""
    print("\n" + "="*80)
    print("COMPONENT 3: WALK-FORWARD VALIDATION")
    print("="*80)

    close = data['close']
    total_bars = len(close)
    fold_size = total_bars // n_folds

    results = []

    for fold in range(n_folds):
        start_idx = fold * fold_size
        end_idx = min((fold + 1) * fold_size, total_bars)

        # Split data
        fold_data = {
            'close': close.iloc[start_idx:end_idx],
            'high': data['high'].iloc[start_idx:end_idx],
            'low': data['low'].iloc[start_idx:end_idx]
        }
        btc_fold = btc_prices.iloc[start_idx:end_idx]
        paxg_fold = paxg_prices.iloc[start_idx:end_idx]

        if len(fold_data['close']) < 200:
            continue

        # Run strategy on fold
        strategy = InstitutionalCryptoPerp(
            bear_market_asset='PAXG-USD',
            bear_allocation=1.0
        )

        portfolio = backtest_institutional_perp(strategy, fold_data, btc_fold, paxg_fold, initial_capital=100000)

        # Calculate metrics
        equity = portfolio['equity']
        final_equity = equity[-1]
        total_return = (final_equity / 100000 - 1) * 100

        trades = [t for t in portfolio['trades'] if t['action'] == 'SELL']

        results.append({
            'fold': fold + 1,
            'start_date': fold_data['close'].index[0],
            'end_date': fold_data['close'].index[-1],
            'total_return': total_return,
            'final_equity': final_equity,
            'trades': len(trades)
        })

        print(f"\nFold {fold + 1}/{n_folds}: Return={total_return:+.2f}%, Trades={len(trades)}")

    # Summary
    results_df = pd.DataFrame(results)

    if len(results_df) == 0:
        print("\n❌ No valid folds - data too short")
        return results_df

    positive_folds = (results_df['total_return'] > 0).sum()
    consistency = (positive_folds / len(results_df)) * 100

    print(f"\n📈 WALK-FORWARD SUMMARY:")
    print(f"   Total Folds: {len(results_df)}")
    print(f"   Positive Folds: {positive_folds}/{len(results_df)} ({consistency:.1f}%)")
    print(f"   Average Return: {results_df['total_return'].mean():.2f}%")
    print(f"   Std Dev: {results_df['total_return'].std():.2f}%")
    print(f"   Best Fold: {results_df['total_return'].max():+.2f}%")
    print(f"   Worst Fold: {results_df['total_return'].min():+.2f}%")

    # Risk assessment
    if consistency >= 75 and results_df['total_return'].mean() > 10:
        print("   ✅ Risk Assessment: EXCELLENT - Strategy is robust")
    elif consistency >= 60 and results_df['total_return'].mean() > 5:
        print("   ⚠️  Risk Assessment: GOOD - Monitor closely")
    else:
        print("   ❌ Risk Assessment: POOR - Strategy may be unstable")

    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'institutional_perp_walkforward.csv'
    results_df.to_csv(output_path, index=False)
    print(f"\n✅ Walk-forward results saved to: {output_path}")

    return results_df


def run_monte_carlo_simulation(portfolio, n_simulations=1000):
    """COMPONENT 4: Monte Carlo Simulation (MANDATORY)"""
    print("\n" + "="*80)
    print("COMPONENT 4: MONTE CARLO SIMULATION")
    print("="*80)

    trades = [t for t in portfolio['trades'] if t['action'] == 'SELL']

    if len(trades) < 30:
        print(f"⚠️  Warning: Only {len(trades)} trades. Results may be unreliable.")

    # Extract returns
    returns = np.array([t['pnl'] for t in trades])

    print(f"\nTrade Statistics:")
    print(f"   Total Trades: {len(returns)}")
    print(f"   Winning Trades: {(returns > 0).sum()} ({(returns > 0).mean() * 100:.1f}%)")
    print(f"   Average Win: ${returns[returns > 0].mean():,.2f}")
    print(f"   Average Loss: ${returns[returns < 0].mean():,.2f}")

    # Run simulations
    print(f"\nRunning {n_simulations} Monte Carlo simulations...")
    initial_capital = portfolio['initial_capital']
    simulation_results = []

    for sim in range(n_simulations):
        sampled_returns = np.random.choice(returns, size=len(returns), replace=True)
        equity = initial_capital + np.cumsum(sampled_returns)
        final_equity = equity[-1]
        total_return = (final_equity / initial_capital - 1) * 100

        # Max drawdown
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        max_dd = drawdown.min()

        simulation_results.append({
            'final_equity': final_equity,
            'total_return': total_return,
            'max_drawdown': max_dd
        })

    sim_df = pd.DataFrame(simulation_results)

    print(f"\n🎲 MONTE CARLO RESULTS:")
    print(f"   Simulations: {n_simulations}")
    print(f"   Probability of Profit: {(sim_df['total_return'] > 0).mean() * 100:.1f}%")
    print(f"   Expected Return: {sim_df['total_return'].mean():.2f}%")
    print(f"   Median Return: {sim_df['total_return'].median():.2f}%")
    print(f"   5th Percentile: {sim_df['total_return'].quantile(0.05):.2f}%")
    print(f"   95th Percentile: {sim_df['total_return'].quantile(0.95):.2f}%")
    print(f"   Expected Max DD: {sim_df['max_drawdown'].mean():.2f}%")
    print(f"   Worst Case DD: {sim_df['max_drawdown'].min():.2f}%")

    prob_profit = (sim_df['total_return'] > 0).mean() * 100
    if prob_profit >= 80:
        print("   ✅ Risk Assessment: EXCELLENT")
    elif prob_profit >= 60:
        print("   ⚠️  Risk Assessment: MODERATE")
    else:
        print("   ❌ Risk Assessment: HIGH RISK")

    # Save results
    output_path = Path(__file__).parent.parent / 'results' / 'crypto' / 'institutional_perp_montecarlo.csv'
    sim_df.to_csv(output_path, index=False)
    print(f"\n✅ Monte Carlo results saved to: {output_path}")

    return sim_df


def main():
    print("="*80)
    print("FULL BACKTEST: INSTITUTIONAL CRYPTO PERP WITH PAXG (5-YEAR)")
    print("="*80)
    print("\n📋 This backtest includes ALL 4 MANDATORY components:")
    print("   1. Performance Backtest (crypto trading + PAXG)")
    print("   2. QuantStats Report")
    print("   3. Walk-Forward Validation")
    print("   4. Monte Carlo Simulation")
    print("\n" + "="*80)

    # Download data
    symbols = CRYPTO_UNIVERSE + ['PAXG-USD']
    all_data = download_crypto_data(symbols, period="5y")

    # Separate PAXG
    paxg_prices = all_data['close']['PAXG-USD']
    btc_prices = all_data['close']['BTC-USD']

    # Remove PAXG from trading universe
    trading_data = {
        'close': all_data['close'].drop('PAXG-USD', axis=1),
        'high': all_data['high'].drop('PAXG-USD', axis=1),
        'low': all_data['low'].drop('PAXG-USD', axis=1)
    }

    # Initialize strategy with PAXG
    strategy = InstitutionalCryptoPerp(
        bear_market_asset='PAXG-USD',
        bear_allocation=1.0
    )

    # COMPONENT 1: Performance Backtest
    portfolio = backtest_institutional_perp(strategy, trading_data, btc_prices, paxg_prices)
    print_results(portfolio)

    # COMPONENT 2: QuantStats Report
    report_path = generate_quantstats_report(portfolio, btc_prices)

    # COMPONENT 3: Walk-Forward Validation
    wf_results = run_walk_forward_validation(trading_data, btc_prices, paxg_prices, n_folds=6)

    # COMPONENT 4: Monte Carlo Simulation
    mc_results = run_monte_carlo_simulation(portfolio, n_simulations=1000)

    print("\n" + "="*80)
    print("✅ FULL BACKTEST COMPLETE")
    print("="*80)
    print(f"\n📁 Results saved to:")
    print(f"   - {report_path}")
    print(f"   - results/crypto/institutional_perp_walkforward.csv")
    print(f"   - results/crypto/institutional_perp_montecarlo.csv")
    print(f"\n🚀 Strategy is ready for deployment if all components show positive results.")


if __name__ == "__main__":
    main()
