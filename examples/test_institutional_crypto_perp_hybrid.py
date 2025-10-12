"""
Test Institutional Crypto Perpetual Futures Strategy - HYBRID VERSION

This version allocates 50% to PAXG (gold stablecoin) during BEAR_RISK_OFF periods
instead of sitting 100% in cash.

The idea: During the 42% of time when BTC is below 200MA (bear market),
we want some exposure to a defensive asset that tends to hold value.

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

from strategies.institutional_crypto_perp_strategy import (
    InstitutionalCryptoPerp, MarketRegime, Position, RiskMetrics
)


# Top 30 crypto perpetual pairs by volume (Bybit/Binance listing)
TOP_30_PERPS = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
    'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'BCH-USD',
    'NEAR-USD', 'APT-USD', 'ARB-USD', 'OP-USD', 'FTM-USD',
    'AAVE-USD', 'MKR-USD', 'SNX-USD', 'RUNE-USD',
    'SAND-USD', 'MANA-USD', 'AXS-USD', 'ICP-USD'
]

# Add PAXG for bear market allocation
PAXG_SYMBOL = 'PAXG-USD'


def download_crypto_data(symbols, start_date, end_date):
    """Download crypto data from Yahoo Finance"""
    print(f"\n📥 Downloading {len(symbols)} crypto pairs...")
    print(f"   Period: {start_date} to {end_date}")

    # Download each symbol individually
    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()
    volume = pd.DataFrame()

    for symbol in symbols:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty:
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
                volume[symbol] = data['Volume']
        except Exception as e:
            print(f"   ⚠️  Failed to download {symbol}: {e}")

    # Forward fill missing data (up to 3 days)
    close_prices = close_prices.fillna(method='ffill', limit=3)
    high_prices = high_prices.fillna(method='ffill', limit=3)
    low_prices = low_prices.fillna(method='ffill', limit=3)
    volume = volume.fillna(0)

    print(f"   ✅ Successfully downloaded {len(close_prices.columns)} pairs")
    print(f"   📊 Data points: {len(close_prices)} days")

    return {
        'close': close_prices,
        'high': high_prices,
        'low': low_prices,
        'volume': volume
    }


def backtest_hybrid_perp(strategy, data, btc_prices, paxg_prices, initial_capital=100000, bear_allocation=0.5):
    """
    Backtest with hybrid bear market allocation

    During BEAR_RISK_OFF:
    - Close all crypto positions
    - Allocate bear_allocation % to PAXG
    - Keep (1 - bear_allocation) % in cash
    """
    print("\n🚀 Running HYBRID backtest...")
    print(f"   💰 Bear market allocation: {bear_allocation*100}% to PAXG")

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
    position_history = []
    paxg_allocation_history = []

    equity = initial_capital
    strategy.daily_start_equity = equity
    paxg_position = 0  # Track PAXG holdings
    paxg_entry_price = 0

    # Track regime statistics
    regime_stats = {
        MarketRegime.BULL_RISK_ON.value: {'days': 0, 'pnl': 0},
        MarketRegime.NEUTRAL.value: {'days': 0, 'pnl': 0},
        MarketRegime.BEAR_RISK_OFF.value: {'days': 0, 'pnl': 0}
    }

    # Backtest loop
    total_days = len(close)
    for i, date in enumerate(close.index):
        if i % 100 == 0:
            print(f"   📅 Processing: {date.strftime('%Y-%m-%d')} ({i}/{total_days} days, {len(strategy.positions)} crypto + {paxg_position:.0f} PAXG)")

        if date not in regime.index or date not in paxg_prices.index:
            continue

        current_regime = regime.loc[date]
        regime_stats[current_regime]['days'] += 1

        # Reset daily start equity at beginning of each day
        if len(equity_curve) > 0 and dates[-1].date() != date.date():
            strategy.daily_start_equity = equity

        # Update position prices
        for symbol in list(strategy.positions.keys()):
            if symbol in close.columns and date in close.index:
                strategy.positions[symbol].current_price = close.loc[date, symbol]

        # Update PAXG position value
        paxg_value = 0
        paxg_pnl = 0
        if paxg_position > 0:
            current_paxg_price = paxg_prices.loc[date]
            paxg_value = paxg_position * current_paxg_price
            paxg_pnl = (current_paxg_price - paxg_entry_price) * paxg_position

        # Calculate current equity
        crypto_unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        realized_pnl = sum([t['pnl'] for t in trades])
        equity = initial_capital + realized_pnl + crypto_unrealized_pnl + paxg_pnl

        # HYBRID BEAR LOGIC: Allocate to PAXG during bear markets
        if current_regime == MarketRegime.BEAR_RISK_OFF.value:
            # Close all crypto positions if in bear
            for symbol in list(strategy.positions.keys()):
                position = strategy.positions[symbol]
                pnl = position.unrealized_pnl
                pnl_pct = position.pnl_pct

                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': position.current_price,
                    'size': position.size,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': 'Regime = BEAR_RISK_OFF'
                })

                regime_stats[current_regime]['pnl'] += pnl
                del strategy.positions[symbol]

            # Allocate to PAXG if not already allocated
            if paxg_position == 0:
                # Recalculate equity after closing positions
                realized_pnl = sum([t['pnl'] for t in trades])
                equity = initial_capital + realized_pnl

                paxg_allocation_amount = equity * bear_allocation
                current_paxg_price = paxg_prices.loc[date]
                paxg_position = paxg_allocation_amount / current_paxg_price
                paxg_entry_price = current_paxg_price

                trades.append({
                    'date': date,
                    'symbol': 'PAXG',
                    'action': 'BUY',
                    'price': current_paxg_price,
                    'size': paxg_position,
                    'pnl': 0,
                    'pnl_pct': 0,
                    'reason': f'Bear allocation ({bear_allocation*100}%)'
                })

        # Exit PAXG when leaving bear regime
        elif paxg_position > 0:
            current_paxg_price = paxg_prices.loc[date]
            paxg_pnl = (current_paxg_price - paxg_entry_price) * paxg_position
            paxg_pnl_pct = ((current_paxg_price / paxg_entry_price) - 1) * 100

            trades.append({
                'date': date,
                'symbol': 'PAXG',
                'action': 'SELL',
                'price': current_paxg_price,
                'size': paxg_position,
                'pnl': paxg_pnl,
                'pnl_pct': paxg_pnl_pct,
                'reason': f'Exit bear regime → {current_regime}'
            })

            # Add PAXG P&L to previous regime (where we exited from)
            prev_regime = MarketRegime.BEAR_RISK_OFF.value
            regime_stats[prev_regime]['pnl'] += paxg_pnl

            paxg_position = 0
            paxg_entry_price = 0

        # Check risk limits (only for crypto positions, not PAXG)
        if len(strategy.positions) > 0:
            breach, reason = strategy.check_risk_limits(date, equity)
            if breach:
                # Close all crypto positions
                for symbol in list(strategy.positions.keys()):
                    position = strategy.positions[symbol]
                    pnl = position.unrealized_pnl
                    pnl_pct = position.pnl_pct

                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': position.current_price,
                        'size': position.size,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': reason
                    })

                    del strategy.positions[symbol]

        # Check exits for existing crypto positions
        for symbol in list(strategy.positions.keys()):
            should_exit, exit_reason = strategy.check_exit_signal(
                symbol, date, close, high, low, current_regime
            )

            if should_exit:
                position = strategy.positions[symbol]
                pnl = position.unrealized_pnl
                pnl_pct = position.pnl_pct

                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': position.current_price,
                    'size': position.size,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': exit_reason
                })

                regime_stats[current_regime]['pnl'] += pnl
                del strategy.positions[symbol]

        # Check pyramid adds (only in non-bear regimes)
        if current_regime != MarketRegime.BEAR_RISK_OFF.value:
            for symbol in list(strategy.positions.keys()):
                should_add = strategy.check_add_signal(symbol, date, close, high, low)

                if should_add:
                    position = strategy.positions[symbol]

                    # Calculate volatility
                    returns = close[symbol].pct_change().dropna()
                    volatility = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                    # Calculate add size
                    add_size, add_leverage = strategy.calculate_position_size(
                        position.current_price, volatility,
                        MarketRegime(current_regime), equity
                    )

                    # Add to position
                    position.adds += 1
                    position.last_add_price = position.current_price
                    position.size += add_size

                    trades.append({
                        'date': date,
                        'symbol': symbol,
                        'action': f'ADD #{position.adds}',
                        'price': position.current_price,
                        'size': add_size,
                        'pnl': 0,
                        'pnl_pct': 0,
                        'reason': f'Pyramid add #{position.adds}'
                    })

        # Check entries for new positions (only in BULL regime)
        if current_regime == MarketRegime.BULL_RISK_ON.value and len(strategy.positions) < strategy.max_positions:
            candidates = [s for s in close.columns if s not in strategy.positions and s != 'PAXG-USD']

            for symbol in candidates:
                has_signal = strategy.check_entry_signal(
                    symbol, date, close, high, low, close, btc_prices, current_regime
                )

                if has_signal:
                    # Calculate volatility
                    returns = close[symbol].pct_change().dropna()
                    volatility = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                    # Calculate position size
                    entry_price = close.loc[date, symbol]
                    position_size, leverage = strategy.calculate_position_size(
                        entry_price, volatility, MarketRegime(current_regime), equity
                    )

                    if position_size > 0:
                        # Open position
                        strategy.positions[symbol] = Position(
                            symbol=symbol,
                            entry_price=entry_price,
                            current_price=entry_price,
                            size=position_size,
                            leverage=leverage,
                            adds=0,
                            highest_price=entry_price,
                            entry_date=date,
                            last_add_price=entry_price
                        )

                        trades.append({
                            'date': date,
                            'symbol': symbol,
                            'action': 'BUY',
                            'price': entry_price,
                            'size': position_size,
                            'pnl': 0,
                            'pnl_pct': 0,
                            'reason': 'Entry signal'
                        })

                        if len(strategy.positions) >= strategy.max_positions:
                            break

        # Record state
        equity_curve.append(equity)
        dates.append(date)
        regime_history.append(current_regime)
        position_history.append(len(strategy.positions))
        paxg_allocation_history.append(paxg_value / equity if equity > 0 else 0)

    # Calculate final equity
    crypto_unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
    paxg_unrealized_pnl = 0
    if paxg_position > 0:
        final_paxg_price = paxg_prices.iloc[-1]
        paxg_unrealized_pnl = (final_paxg_price - paxg_entry_price) * paxg_position

    final_equity = initial_capital + sum([t['pnl'] for t in trades]) + crypto_unrealized_pnl + paxg_unrealized_pnl

    print(f"\n✅ Backtest complete!")
    print(f"   📊 Total trades: {len(trades)}")
    print(f"   💰 Final equity: ${final_equity:,.2f}")

    return {
        'equity_curve': pd.Series(equity_curve, index=dates),
        'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
        'regime_history': pd.Series(regime_history, index=dates),
        'position_history': pd.Series(position_history, index=dates),
        'paxg_allocation_history': pd.Series(paxg_allocation_history, index=dates),
        'regime_stats': regime_stats,
        'final_positions': strategy.positions
    }


def analyze_results(results, initial_capital, bear_allocation):
    """Analyze and display backtest results"""
    print("\n" + "="*60)
    print("📊 HYBRID STRATEGY PERFORMANCE SUMMARY")
    print(f"   (50% PAXG allocation during bear markets)")
    print("="*60)

    equity_curve = results['equity_curve']
    trades = results['trades']
    regime_stats = results['regime_stats']
    paxg_allocation = results['paxg_allocation_history']

    # Overall metrics
    total_return = ((equity_curve.iloc[-1] / initial_capital) - 1) * 100
    years = len(equity_curve) / 252
    annualized_return = ((equity_curve.iloc[-1] / initial_capital) ** (1 / years) - 1) * 100

    # Drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100
    max_drawdown = drawdown.min()

    # Sharpe ratio
    daily_returns = equity_curve.pct_change().dropna()
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if len(daily_returns) > 0 else 0

    print(f"\n💰 Returns:")
    print(f"   Total Return: {total_return:,.2f}%")
    print(f"   Annualized: {annualized_return:,.2f}%")
    print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")

    # PAXG statistics
    paxg_trades = trades[trades['symbol'] == 'PAXG']
    if len(paxg_trades) > 0:
        paxg_buys = paxg_trades[paxg_trades['action'] == 'BUY']
        paxg_sells = paxg_trades[paxg_trades['action'] == 'SELL']
        paxg_total_pnl = paxg_sells['pnl'].sum() if len(paxg_sells) > 0 else 0

        avg_paxg_allocation = paxg_allocation.mean() * 100
        max_paxg_allocation = paxg_allocation.max() * 100
        days_in_paxg = (paxg_allocation > 0).sum()

        print(f"\n🟡 PAXG (Gold) Statistics:")
        print(f"   Total P&L from PAXG: ${paxg_total_pnl:,.2f}")
        print(f"   Days in PAXG: {days_in_paxg}")
        print(f"   Avg allocation: {avg_paxg_allocation:.1f}%")
        print(f"   Max allocation: {max_paxg_allocation:.1f}%")

    # Crypto trade statistics
    crypto_trades = trades[trades['symbol'] != 'PAXG']
    if len(crypto_trades) > 0:
        winning_trades = crypto_trades[crypto_trades['pnl'] > 0]
        losing_trades = crypto_trades[crypto_trades['pnl'] < 0]

        total_trades = len(crypto_trades[crypto_trades['action'].isin(['SELL'])])
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        print(f"\n📈 Crypto Trade Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Avg Win: ${avg_win:,.2f}")
        print(f"   Avg Loss: ${avg_loss:,.2f}")
        print(f"   Profit Factor: {profit_factor:.2f}")

        # Pyramid statistics
        add_trades = crypto_trades[crypto_trades['action'].str.contains('ADD', na=False)]
        print(f"   Pyramid Adds: {len(add_trades)}")

    # Regime breakdown
    print(f"\n🌍 Regime Breakdown:")
    for regime, stats in regime_stats.items():
        days = stats['days']
        pnl = stats['pnl']
        pct_time = days / len(equity_curve) * 100 if len(equity_curve) > 0 else 0

        print(f"   {regime}:")
        print(f"      Days: {days} ({pct_time:.1f}%)")
        print(f"      P&L: ${pnl:,.2f}")

    # Top performers
    if len(crypto_trades) > 0:
        sell_trades = crypto_trades[crypto_trades['action'] == 'SELL'].copy()
        if len(sell_trades) > 0:
            symbol_performance = sell_trades.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean'])
            symbol_performance = symbol_performance.sort_values('sum', ascending=False)

            print(f"\n🏆 Top 10 Crypto Performers:")
            for i, (symbol, row) in enumerate(symbol_performance.head(10).iterrows(), 1):
                print(f"   {i}. {symbol}: ${row['sum']:,.2f} ({int(row['count'])} trades, ${row['mean']:,.2f} avg)")

    print("\n" + "="*60)


def main():
    """Main execution"""
    print("="*60)
    print("🏛️  INSTITUTIONAL CRYPTO PERP - HYBRID STRATEGY")
    print("   (50% PAXG allocation during bear markets)")
    print("="*60)

    # Configuration
    LOOKBACK_YEARS = 2
    BEAR_ALLOCATION = 0.50  # 50% to PAXG during bear

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365)).strftime('%Y-%m-%d')

    # Download data (including PAXG)
    all_symbols = TOP_30_PERPS + [PAXG_SYMBOL]
    data = download_crypto_data(all_symbols, start_date, end_date)

    # Separate PAXG from crypto data
    paxg_prices = data['close'][PAXG_SYMBOL]

    # Remove PAXG from crypto data
    crypto_data = {
        'close': data['close'].drop(columns=[PAXG_SYMBOL], errors='ignore'),
        'high': data['high'].drop(columns=[PAXG_SYMBOL], errors='ignore'),
        'low': data['low'].drop(columns=[PAXG_SYMBOL], errors='ignore'),
        'volume': data['volume'].drop(columns=[PAXG_SYMBOL], errors='ignore')
    }

    # Get BTC prices for regime filter
    btc_prices = crypto_data['close']['BTC-USD']

    # Initialize strategy
    print("\n⚙️  Initializing strategy...")
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

    print("   ✅ Strategy initialized (HYBRID MODE)")
    print(f"      Bear allocation: {BEAR_ALLOCATION*100}% to PAXG")

    # Run backtest
    results = backtest_hybrid_perp(
        strategy=strategy,
        data=crypto_data,
        btc_prices=btc_prices,
        paxg_prices=paxg_prices,
        initial_capital=100000,
        bear_allocation=BEAR_ALLOCATION
    )

    # Analyze results
    analyze_results(results, initial_capital=100000, bear_allocation=BEAR_ALLOCATION)

    # Save results
    print("\n💾 Saving results...")
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)

    results['equity_curve'].to_csv(results_dir / 'institutional_perp_hybrid_equity.csv')
    if len(results['trades']) > 0:
        results['trades'].to_csv(results_dir / 'institutional_perp_hybrid_trades.csv', index=False)

    print(f"   ✅ Results saved to {results_dir}/")
    print("\n✨ Done!")


if __name__ == '__main__':
    main()
