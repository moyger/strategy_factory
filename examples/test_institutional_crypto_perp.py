"""
Test Institutional Crypto Perpetual Futures Strategy

This script backtests the institutional-grade crypto perp strategy on the top 30
liquid perpetual futures pairs by volume.

The strategy features:
- Strict regime-gating (only aggressive in BULL_RISK_ON)
- Donchian breakout + ADX + RS filtering
- Pyramid adds at 0.75×ATR
- 2×ATR trailing stops
- Vol-targeted sizing (15-25% per position)
- Dynamic leverage (0.5-2× based on regime)
- Daily loss limits and weekend de-grossing

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
    'AAVE-USD', 'MKR-USD', 'GRT-USD', 'SNX-USD', 'RUNE-USD',
    'SAND-USD', 'MANA-USD', 'AXS-USD', 'IMX-USD', 'ICP-USD'
]


def download_crypto_data(symbols, start_date, end_date):
    """
    Download crypto data from Yahoo Finance

    Args:
        symbols: List of symbols (e.g., ['BTC-USD', 'ETH-USD'])
        start_date: Start date string
        end_date: End date string

    Returns:
        Dict with 'close', 'high', 'low', 'volume' DataFrames
    """
    print(f"\n📥 Downloading {len(symbols)} crypto pairs...")
    print(f"   Period: {start_date} to {end_date}")

    # Convert symbols to Yahoo Finance format
    yf_symbols = [s for s in symbols]

    # Download data
    data = yf.download(
        yf_symbols,
        start=start_date,
        end=end_date,
        progress=False,
        group_by='ticker'
    )

    # Organize into OHLCV structure
    close_prices = pd.DataFrame()
    high_prices = pd.DataFrame()
    low_prices = pd.DataFrame()
    volume = pd.DataFrame()

    for symbol in yf_symbols:
        try:
            if len(yf_symbols) == 1:
                close_prices[symbol] = data['Close']
                high_prices[symbol] = data['High']
                low_prices[symbol] = data['Low']
                volume[symbol] = data['Volume']
            else:
                close_prices[symbol] = data[symbol]['Close']
                high_prices[symbol] = data[symbol]['High']
                low_prices[symbol] = data[symbol]['Low']
                volume[symbol] = data[symbol]['Volume']
        except:
            print(f"   ⚠️  Failed to download {symbol}")
            continue

    # Drop columns with all NaN
    close_prices = close_prices.dropna(axis=1, how='all')
    high_prices = high_prices.dropna(axis=1, how='all')
    low_prices = low_prices.dropna(axis=1, how='all')
    volume = volume.dropna(axis=1, how='all')

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


def backtest_institutional_perp(strategy, data, btc_prices, initial_capital=100000):
    """
    Backtest the institutional crypto perp strategy

    Args:
        strategy: InstitutionalCryptoPerp instance
        data: Dict with 'close', 'high', 'low', 'volume' DataFrames
        btc_prices: BTC-USD price series
        initial_capital: Starting capital

    Returns:
        Dict with performance results
    """
    print("\n🚀 Running backtest...")

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

    equity = initial_capital
    strategy.daily_start_equity = equity

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
            print(f"   📅 Processing: {date.strftime('%Y-%m-%d')} ({i}/{total_days} days, {len(strategy.positions)} positions)")

        if date not in regime.index:
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

        # Calculate current equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # Check risk limits
        breach, reason = strategy.check_risk_limits(date, equity)
        if breach:
            # Close all positions
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

        # Check exits for existing positions
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

                # Update regime P&L
                regime_stats[current_regime]['pnl'] += pnl

                del strategy.positions[symbol]

        # Check pyramid adds for existing positions
        for symbol in list(strategy.positions.keys()):
            should_add = strategy.check_add_signal(symbol, date, close, high, low)

            if should_add:
                position = strategy.positions[symbol]

                # Calculate volatility
                returns = close[symbol].pct_change().dropna()
                volatility = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                # Calculate add size (same as original position)
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

        # Check entries for new positions
        if len(strategy.positions) < strategy.max_positions:
            # Get candidate symbols
            candidates = [s for s in close.columns if s not in strategy.positions]

            for symbol in candidates:
                # Check entry signal
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

                        # Stop if max positions reached
                        if len(strategy.positions) >= strategy.max_positions:
                            break

        # Record state
        equity_curve.append(equity)
        dates.append(date)
        regime_history.append(current_regime)
        position_history.append(len(strategy.positions))

    # Calculate final equity
    unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
    final_equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

    print(f"\n✅ Backtest complete!")
    print(f"   📊 Total trades: {len(trades)}")
    print(f"   💰 Final equity: ${final_equity:,.2f}")

    return {
        'equity_curve': pd.Series(equity_curve, index=dates),
        'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
        'regime_history': pd.Series(regime_history, index=dates),
        'position_history': pd.Series(position_history, index=dates),
        'regime_stats': regime_stats,
        'final_positions': strategy.positions
    }


def analyze_results(results, initial_capital):
    """Analyze and display backtest results"""
    print("\n" + "="*60)
    print("📊 PERFORMANCE SUMMARY")
    print("="*60)

    equity_curve = results['equity_curve']
    trades = results['trades']
    regime_stats = results['regime_stats']

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

    # Trade statistics
    if len(trades) > 0:
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] < 0]

        total_trades = len(trades[trades['action'].isin(['SELL'])])
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Avg Win: ${avg_win:,.2f}")
        print(f"   Avg Loss: ${avg_loss:,.2f}")
        print(f"   Profit Factor: {profit_factor:.2f}")

        # Pyramid statistics
        add_trades = trades[trades['action'].str.contains('ADD', na=False)]
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
    if len(trades) > 0:
        sell_trades = trades[trades['action'] == 'SELL'].copy()
        if len(sell_trades) > 0:
            symbol_performance = sell_trades.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean'])
            symbol_performance = symbol_performance.sort_values('sum', ascending=False)

            print(f"\n🏆 Top 10 Performers:")
            for i, (symbol, row) in enumerate(symbol_performance.head(10).iterrows(), 1):
                print(f"   {i}. {symbol}: ${row['sum']:,.2f} ({int(row['count'])} trades, ${row['mean']:,.2f} avg)")

    print("\n" + "="*60)


def main():
    """Main execution"""
    print("="*60)
    print("🏛️  INSTITUTIONAL CRYPTO PERPETUAL FUTURES STRATEGY")
    print("="*60)

    # Configuration
    LOOKBACK_YEARS = 2  # Use 2 years of data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365)).strftime('%Y-%m-%d')

    # Download data
    data = download_crypto_data(TOP_30_PERPS, start_date, end_date)

    # Get BTC prices for regime filter
    btc_prices = data['close']['BTC-USD']

    # Initialize strategy with CRYPTO-ADAPTED parameters
    print("\n⚙️  Initializing strategy...")
    strategy = InstitutionalCryptoPerp(
        max_positions=10,

        # Regime (RELAXED for crypto - vol 20-150 percentile)
        btc_ma_long=200,
        btc_ma_short=20,
        vol_lookback=30,
        vol_percentile_low=20,      # Lower threshold (was 30)
        vol_percentile_high=150,    # Higher threshold (was 120)

        # Entry (RELAXED - Donchian 20-day, ADX > 20, RS top half)
        donchian_period=20,
        adx_threshold=20,           # Lower for crypto (was 25)
        rs_quartile=0.50,           # Top half instead of top quartile (was 0.75)

        # Pyramid (3 adds at 0.75×ATR)
        add_atr_multiple=0.75,
        max_adds=3,

        # Exit (2×ATR trailing, 10-day breakdown)
        trail_atr_multiple=2.0,
        breakdown_period=10,

        # Sizing (20% vol target per position)
        vol_target_per_position=0.20,
        portfolio_vol_target=0.50,

        # Leverage (1.5× bull, 1× neutral, 0.5× bear - REDUCED for safety)
        max_leverage_bull=1.5,      # Reduced from 2.0
        max_leverage_neutral=1.0,
        max_leverage_bear=0.5,

        # Risk (-3% daily loss limit, NO weekend de-gross for 24/7 crypto)
        daily_loss_limit=0.03,
        weekend_degross=False       # Crypto trades 24/7
    )

    print("   ✅ Strategy initialized (CRYPTO-ADAPTED PARAMETERS)")
    print(f"      Max positions: {strategy.max_positions}")
    print(f"      ADX threshold: {strategy.adx_threshold} (lower for crypto)")
    print(f"      RS filter: Top {strategy.rs_quartile*100}% (relaxed)")
    print(f"      Vol target: {strategy.vol_target_per_position*100}% per position")
    print(f"      Max leverage: {strategy.max_leverage_bull}× (BULL) / {strategy.max_leverage_neutral}× (NEUTRAL) / {strategy.max_leverage_bear}× (BEAR)")
    print(f"      Weekend de-gross: {strategy.weekend_degross} (crypto trades 24/7)")

    # Run backtest
    results = backtest_institutional_perp(
        strategy=strategy,
        data=data,
        btc_prices=btc_prices,
        initial_capital=100000
    )

    # Analyze results
    analyze_results(results, initial_capital=100000)

    # Save results
    print("\n💾 Saving results...")

    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)

    # Save equity curve
    results['equity_curve'].to_csv(results_dir / 'institutional_perp_equity.csv')

    # Save trades
    if len(results['trades']) > 0:
        results['trades'].to_csv(results_dir / 'institutional_perp_trades.csv', index=False)

    print(f"   ✅ Results saved to {results_dir}/")

    print("\n✨ Done!")


if __name__ == '__main__':
    main()
