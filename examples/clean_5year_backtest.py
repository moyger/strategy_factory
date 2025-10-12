"""
CLEAN 5-YEAR BACKTEST - NO BUGS

This is a complete rewrite with CAREFUL position sizing logic.

POSITION SIZING RULES (REALISTIC):
1. Each position = 10% of CURRENT equity (allows compounding)
2. BUT: Capped at 10× the initial position size (prevents explosion)
3. Leverage is 1× (NO leverage to start - keep it simple)
4. Example:
   - Start: $100k → $10k per position
   - At $500k: Min($50k, $100k cap) = $50k per position ✓
   - At $5M: Min($500k, $100k cap) = $100k per position (capped) ✓

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


def download_crypto_data(lookback_years=5):
    """Download crypto data with error handling"""

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=lookback_years*365 + 30)).strftime('%Y-%m-%d')

    print(f"\n📥 Downloading data from {start_date} to {end_date}")

    # Top 20 cryptos that have data since 2020
    symbols = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'DOGE-USD',
        'XRP-USD', 'DOT-USD', 'LINK-USD', 'LTC-USD', 'BCH-USD',
        'UNI-USD', 'ATOM-USD', 'SOL-USD', 'AVAX-USD', 'MATIC-USD',
        'SAND-USD', 'MANA-USD', 'AAVE-USD', 'RUNE-USD', 'SNX-USD',
        'PAXG-USD'  # Gold for bear periods
    ]

    close_df = pd.DataFrame()

    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start_date, end=end_date, progress=False)

            if not df.empty and len(df) > 250:  # Need at least 250 days
                close_df[symbol] = df['Close']
                print(f"   ✅ {symbol}: {len(df)} days")
            else:
                print(f"   ⚠️  {symbol}: Insufficient data")

        except Exception as e:
            print(f"   ❌ {symbol}: Failed - {e}")

    # Fill missing data
    close_df = close_df.fillna(method='ffill', limit=5)

    print(f"\n✅ Successfully downloaded {len(close_df.columns)} symbols")
    print(f"   Date range: {close_df.index[0].date()} to {close_df.index[-1].date()}")
    print(f"   Total days: {len(close_df)}")

    return close_df


def calculate_position_size(equity, initial_capital, allocation_pct=0.10, cap_multiplier=10):
    """
    Calculate position size with realistic constraints

    Args:
        equity: Current account equity
        initial_capital: Starting capital (e.g., $100,000)
        allocation_pct: Percentage of equity per position (default 10%)
        cap_multiplier: Maximum position as multiple of initial (default 10×)

    Returns:
        Position size in dollars
    """
    # Base size: allocation % of current equity (allows compounding)
    base_size = equity * allocation_pct

    # Cap: Can't exceed cap_multiplier × initial allocation
    max_size = initial_capital * allocation_pct * cap_multiplier

    # Take the minimum
    position_size = min(base_size, max_size)

    return position_size


def run_clean_backtest(close_prices, initial_capital=100000, max_positions=10,
                       bear_allocation=1.0, use_paxg=True):
    """
    Run clean backtest with careful position sizing

    Args:
        close_prices: DataFrame with close prices
        initial_capital: Starting capital
        max_positions: Maximum number of positions
        bear_allocation: % allocated to PAXG during bear (1.0 = 100%)
        use_paxg: Whether to use PAXG or sit in cash during bear

    Returns:
        Dictionary with results
    """

    print(f"\n{'='*80}")
    print(f"🚀 RUNNING CLEAN BACKTEST")
    print(f"{'='*80}")
    print(f"   Initial capital: ${initial_capital:,}")
    print(f"   Max positions: {max_positions}")
    print(f"   Bear allocation: {bear_allocation*100}% to {'PAXG' if use_paxg else 'cash'}")
    print(f"   Position sizing: 10% of equity, capped at 10× initial")

    # Separate PAXG
    paxg_prices = close_prices['PAXG-USD'].copy()
    crypto_prices = close_prices.drop(columns=['PAXG-USD'])

    # Calculate BTC regime (simple 200MA)
    btc_prices = crypto_prices['BTC-USD']
    btc_ma200 = btc_prices.rolling(window=200).mean()

    # Track everything
    equity = initial_capital
    cash = initial_capital
    positions = {}  # {symbol: {'shares': X, 'entry_price': Y, 'entry_date': Z}}
    paxg_shares = 0
    paxg_entry_price = 0

    trades = []
    equity_history = []
    date_history = []
    regime_history = []

    # Start after 200 days (need MA)
    start_idx = 200

    print(f"\n📊 Processing {len(close_prices) - start_idx} days...")

    for i in range(start_idx, len(close_prices)):
        date = close_prices.index[i]

        # Progress update every 200 days
        if (i - start_idx) % 200 == 0:
            print(f"   {date.strftime('%Y-%m-%d')}: Equity = ${equity:,.0f}, Positions = {len(positions)}")

        # Determine regime
        btc_current = btc_prices.iloc[i]
        btc_ma = btc_ma200.iloc[i]

        if pd.isna(btc_ma):
            continue

        is_bull = btc_current > btc_ma
        regime = 'BULL' if is_bull else 'BEAR'
        regime_history.append(regime)

        # Update position values
        for symbol in list(positions.keys()):
            if symbol in crypto_prices.columns:
                current_price = crypto_prices[symbol].iloc[i]
                if not pd.isna(current_price):
                    positions[symbol]['current_price'] = current_price

        # Calculate equity
        position_value = sum(
            pos['shares'] * pos.get('current_price', pos['entry_price'])
            for pos in positions.values()
        )

        paxg_value = 0
        if paxg_shares > 0:
            paxg_current_price = paxg_prices.iloc[i]
            if not pd.isna(paxg_current_price):
                paxg_value = paxg_shares * paxg_current_price

        equity = cash + position_value + paxg_value

        # Record
        equity_history.append(equity)
        date_history.append(date)

        # --- BEAR REGIME LOGIC ---
        if regime == 'BEAR':
            # Close all crypto positions
            for symbol in list(positions.keys()):
                pos = positions[symbol]
                current_price = pos.get('current_price', pos['entry_price'])

                # Sell
                proceeds = pos['shares'] * current_price
                cash += proceeds

                # Record trade
                pnl = proceeds - (pos['shares'] * pos['entry_price'])
                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': current_price,
                    'shares': pos['shares'],
                    'pnl': pnl,
                    'reason': 'Bear regime (BTC < 200MA)'
                })

                # Remove position
                del positions[symbol]

            # Allocate to PAXG if enabled and not already in PAXG
            if use_paxg and paxg_shares == 0 and bear_allocation > 0:
                paxg_current_price = paxg_prices.iloc[i]

                if not pd.isna(paxg_current_price):
                    # Allocate % of cash to PAXG
                    paxg_allocation = cash * bear_allocation
                    paxg_shares = paxg_allocation / paxg_current_price
                    paxg_entry_price = paxg_current_price
                    cash -= paxg_allocation

                    trades.append({
                        'date': date,
                        'symbol': 'PAXG',
                        'action': 'BUY',
                        'price': paxg_current_price,
                        'shares': paxg_shares,
                        'pnl': 0,
                        'reason': f'Bear allocation ({bear_allocation*100}%)'
                    })

        # --- EXIT PAXG WHEN LEAVING BEAR ---
        if regime == 'BULL' and paxg_shares > 0:
            paxg_current_price = paxg_prices.iloc[i]

            if not pd.isna(paxg_current_price):
                # Sell PAXG
                proceeds = paxg_shares * paxg_current_price
                cash += proceeds

                pnl = proceeds - (paxg_shares * paxg_entry_price)
                trades.append({
                    'date': date,
                    'symbol': 'PAXG',
                    'action': 'SELL',
                    'price': paxg_current_price,
                    'shares': paxg_shares,
                    'pnl': pnl,
                    'reason': 'Exit bear → Bull regime'
                })

                paxg_shares = 0
                paxg_entry_price = 0

        # --- BULL REGIME: TRADE CRYPTO ---
        if regime == 'BULL' and len(positions) < max_positions:
            # Entry signal: Price breaks above 50-day high
            for symbol in crypto_prices.columns:
                if symbol in positions:
                    continue

                if len(positions) >= max_positions:
                    break

                # Get price series for this symbol
                symbol_prices = crypto_prices[symbol].iloc[:i+1]

                if len(symbol_prices) < 51:  # Need 50 days history
                    continue

                current_price = symbol_prices.iloc[-1]

                if pd.isna(current_price):
                    continue

                # 50-day high (excluding today)
                high_50 = symbol_prices.iloc[-51:-1].max()

                # Entry: Break above 50-day high
                if current_price > high_50:
                    # Calculate position size
                    position_size_dollars = calculate_position_size(
                        equity=equity,
                        initial_capital=initial_capital,
                        allocation_pct=0.10,
                        cap_multiplier=10
                    )

                    # How many shares can we buy?
                    shares = position_size_dollars / current_price
                    cost = shares * current_price

                    # Only buy if we have cash
                    if cost <= cash:
                        cash -= cost

                        positions[symbol] = {
                            'shares': shares,
                            'entry_price': current_price,
                            'current_price': current_price,
                            'entry_date': date
                        }

                        trades.append({
                            'date': date,
                            'symbol': symbol,
                            'action': 'BUY',
                            'price': current_price,
                            'shares': shares,
                            'pnl': 0,
                            'reason': '50-day breakout'
                        })

        # --- EXIT LOGIC: 20-day low breakdown ---
        for symbol in list(positions.keys()):
            symbol_prices = crypto_prices[symbol].iloc[:i+1]

            if len(symbol_prices) < 21:
                continue

            current_price = symbol_prices.iloc[-1]

            if pd.isna(current_price):
                continue

            # 20-day low (excluding today)
            low_20 = symbol_prices.iloc[-21:-1].min()

            # Exit: Break below 20-day low
            if current_price < low_20:
                pos = positions[symbol]

                # Sell
                proceeds = pos['shares'] * current_price
                cash += proceeds

                pnl = proceeds - (pos['shares'] * pos['entry_price'])
                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': current_price,
                    'shares': pos['shares'],
                    'pnl': pnl,
                    'reason': '20-day low breakdown'
                })

                del positions[symbol]

    print(f"\n✅ Backtest complete!")
    print(f"   Final equity: ${equity:,.0f}")
    print(f"   Total trades: {len(trades)}")

    return {
        'equity_history': pd.Series(equity_history, index=date_history),
        'trades': pd.DataFrame(trades),
        'regime_history': pd.Series(regime_history, index=date_history),
        'final_equity': equity,
        'initial_capital': initial_capital
    }


def analyze_results(results):
    """Analyze and display results"""

    equity = results['equity_history']
    trades = results['trades']
    initial_capital = results['initial_capital']

    print(f"\n{'='*80}")
    print(f"📊 PERFORMANCE ANALYSIS")
    print(f"{'='*80}")

    # Returns
    total_return = ((equity.iloc[-1] / initial_capital) - 1) * 100
    years = len(equity) / 252
    annualized = ((equity.iloc[-1] / initial_capital) ** (1/years) - 1) * 100

    print(f"\n💰 Returns:")
    print(f"   Initial Capital: ${initial_capital:,}")
    print(f"   Final Equity: ${equity.iloc[-1]:,.0f}")
    print(f"   Total Return: {total_return:.1f}%")
    print(f"   Annualized: {annualized:.1f}%")
    print(f"   Period: {years:.2f} years")

    # Drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax * 100
    max_dd = drawdown.min()
    max_dd_date = drawdown.idxmin()

    print(f"\n📉 Risk:")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Max DD Date: {max_dd_date.strftime('%Y-%m-%d')}")

    # Sharpe
    daily_returns = equity.pct_change().dropna()
    if len(daily_returns) > 0 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        print(f"   Sharpe Ratio: {sharpe:.2f}")

    # Trades
    if len(trades) > 0:
        sell_trades = trades[trades['action'] == 'SELL']
        crypto_sells = sell_trades[sell_trades['symbol'] != 'PAXG']

        if len(crypto_sells) > 0:
            winners = crypto_sells[crypto_sells['pnl'] > 0]
            losers = crypto_sells[crypto_sells['pnl'] < 0]

            win_rate = len(winners) / len(crypto_sells) * 100
            avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
            avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0

            print(f"\n📈 Trading:")
            print(f"   Total Trades: {len(crypto_sells)}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Avg Win: ${avg_win:,.0f}")
            print(f"   Avg Loss: ${avg_loss:,.0f}")

            if len(winners) > 0 and len(losers) > 0:
                profit_factor = abs(winners['pnl'].sum() / losers['pnl'].sum())
                print(f"   Profit Factor: {profit_factor:.2f}")

        # PAXG contribution
        paxg_trades = sell_trades[sell_trades['symbol'] == 'PAXG']
        if len(paxg_trades) > 0:
            paxg_pnl = paxg_trades['pnl'].sum()
            total_profit = equity.iloc[-1] - initial_capital

            print(f"\n🟡 PAXG Contribution:")
            print(f"   PAXG P&L: ${paxg_pnl:,.0f}")
            print(f"   % of Total Profit: {paxg_pnl/total_profit*100:.1f}%")

        # Top performers
        top_performers = crypto_sells.groupby('symbol')['pnl'].sum().sort_values(ascending=False).head(10)

        if len(top_performers) > 0:
            print(f"\n🏆 Top 10 Performers:")
            for i, (symbol, pnl) in enumerate(top_performers.items(), 1):
                num_trades = len(crypto_sells[crypto_sells['symbol'] == symbol])
                print(f"   {i}. {symbol}: ${pnl:,.0f} ({num_trades} trades)")

    # Regime breakdown
    regime_counts = results['regime_history'].value_counts()
    total_days = len(results['regime_history'])

    print(f"\n🌍 Regime Distribution:")
    for regime, count in regime_counts.items():
        pct = count / total_days * 100
        print(f"   {regime}: {count} days ({pct:.1f}%)")

    print(f"\n{'='*80}")

    return {
        'total_return': total_return,
        'annualized': annualized,
        'max_dd': max_dd,
        'sharpe': sharpe if 'sharpe' in locals() else 0,
        'trades': len(crypto_sells) if 'crypto_sells' in locals() else 0,
        'win_rate': win_rate if 'win_rate' in locals() else 0
    }


def main():
    """Main execution"""

    print("="*80)
    print("🏛️  CLEAN 5-YEAR BACKTEST (BUG-FREE)")
    print("="*80)
    print("\nPosition sizing: 10% of equity, capped at 10× initial")
    print("Leverage: 1× (NO leverage)")
    print("Strategy: Simple 50-day breakout, 20-day exit")

    # Download data
    close_prices = download_crypto_data(lookback_years=5)

    # Run backtest
    results = run_clean_backtest(
        close_prices=close_prices,
        initial_capital=100000,
        max_positions=10,
        bear_allocation=1.0,  # 100% PAXG during bear
        use_paxg=True
    )

    # Analyze
    metrics = analyze_results(results)

    # Save results
    print(f"\n💾 Saving results...")
    results_dir = Path(__file__).parent.parent / 'results'
    results_dir.mkdir(exist_ok=True)

    results['equity_history'].to_csv(results_dir / 'clean_5year_equity.csv')
    results['trades'].to_csv(results_dir / 'clean_5year_trades.csv', index=False)

    print(f"   ✅ Saved to {results_dir}/")

    # Sanity checks
    print(f"\n{'='*80}")
    print(f"🧪 SANITY CHECKS")
    print(f"{'='*80}")

    final_equity = results['final_equity']
    total_return = metrics['total_return']

    if total_return > 10000:
        print(f"   ⚠️  WARNING: Return of {total_return:.0f}% seems unrealistic!")
        print(f"       This might indicate a bug.")
    elif total_return > 1000:
        print(f"   ⚠️  CAUTION: Return of {total_return:.0f}% is very high.")
        print(f"       Review position sizing carefully.")
    elif total_return < 0:
        print(f"   ⚠️  WARNING: Negative return ({total_return:.1f}%)")
        print(f"       Strategy may not work or has bugs.")
    else:
        print(f"   ✅ Return of {total_return:.1f}% seems reasonable for crypto")

    if metrics['max_dd'] < -80:
        print(f"   ⚠️  WARNING: Drawdown of {metrics['max_dd']:.1f}% is extreme!")
    elif metrics['max_dd'] < -50:
        print(f"   ⚠️  CAUTION: Drawdown of {metrics['max_dd']:.1f}% is high but realistic for crypto")
    else:
        print(f"   ✅ Drawdown of {metrics['max_dd']:.1f}% is reasonable")

    print(f"\n✨ Clean backtest complete!")

    return results, metrics


if __name__ == '__main__':
    results, metrics = main()
