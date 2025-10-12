"""
Analyze Crypto Strategy P&L by Month and Year

Generates detailed monthly and yearly P&L breakdown from the 5-year backtest.
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

# Top crypto pairs
CRYPTO_UNIVERSE = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
    'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD'
]


def download_crypto_data(symbols, period="5y"):
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


def backtest_with_daily_tracking(strategy, data, btc_prices, paxg_prices, initial_capital=100000):
    """Run backtest with daily equity tracking"""
    print("\n🚀 Running backtest with daily P&L tracking...")

    close = data['close']
    high = data['high']
    low = data['low']

    # Calculate regime
    regime = strategy.calculate_regime(btc_prices)

    # Initialize tracking
    daily_equity = []
    daily_dates = []
    daily_pnl = []
    trades = []

    equity = initial_capital
    strategy.daily_start_equity = equity
    prev_equity = equity

    # Align PAXG data
    paxg_aligned = paxg_prices.reindex(close.index, method='ffill')

    # Backtest loop
    total_days = len(close)
    for i, date in enumerate(close.index):
        if i % 365 == 0:
            print(f"   📅 {date.strftime('%Y-%m-%d')}: Equity=${equity:,.0f}")

        if date not in regime.index:
            continue

        current_regime = regime.loc[date]

        if len(daily_equity) > 0 and daily_dates[-1].date() != date.date():
            strategy.daily_start_equity = equity

        paxg_price = paxg_aligned.loc[date] if date in paxg_aligned.index else None

        # Update position prices
        for symbol in list(strategy.positions.keys()):
            if symbol in close.columns and date in close.index:
                current_price = close.loc[date, symbol]
                strategy.positions[symbol].current_price = current_price
                if current_price > strategy.positions[symbol].highest_price:
                    strategy.positions[symbol].highest_price = current_price

        if strategy.paxg_position is not None and paxg_price is not None:
            strategy.update_paxg_price(paxg_price)

        # Calculate equity
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # PAXG logic
        should_hold_paxg_now = strategy.should_hold_paxg(current_regime)

        if should_hold_paxg_now and strategy.paxg_position is None and paxg_price is not None:
            # Close all crypto
            for symbol in list(strategy.positions.keys()):
                position = strategy.positions[symbol]
                pnl = position.unrealized_pnl
                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': position.current_price,
                    'pnl': pnl,
                    'reason': 'BEAR - switch to PAXG'
                })
                del strategy.positions[symbol]

            equity = initial_capital + sum([t['pnl'] for t in trades])
            strategy.enter_paxg_position(equity, paxg_price, date)

        elif not should_hold_paxg_now and strategy.paxg_position is not None and paxg_price is not None:
            pnl = strategy.exit_paxg_position(paxg_price)
            if pnl is not None:
                trades.append({
                    'date': date,
                    'symbol': 'PAXG-USD',
                    'action': 'SELL',
                    'price': paxg_price,
                    'pnl': pnl,
                    'reason': 'Exit PAXG'
                })
                equity = initial_capital + sum([t['pnl'] for t in trades])

        # Crypto trading (only if not holding PAXG)
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
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    del strategy.positions[symbol]

            # Check entries
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
                        volatility = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
                        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

                        position_size, leverage = strategy.calculate_position_size(
                            price, volatility, MarketRegime(current_regime), equity
                        )

                        if position_size > 0:
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

                            if len(strategy.positions) >= strategy.max_positions:
                                break

        # Final equity calculation
        unrealized_pnl = sum(p.unrealized_pnl for p in strategy.positions.values())
        if strategy.paxg_position:
            unrealized_pnl += strategy.paxg_position.unrealized_pnl
        equity = initial_capital + sum([t['pnl'] for t in trades]) + unrealized_pnl

        # Track daily P&L
        day_pnl = equity - prev_equity
        daily_equity.append(equity)
        daily_dates.append(date)
        daily_pnl.append(day_pnl)
        prev_equity = equity

    return {
        'daily_equity': daily_equity,
        'daily_dates': daily_dates,
        'daily_pnl': daily_pnl,
        'trades': trades,
        'initial_capital': initial_capital
    }


def generate_pnl_summaries(portfolio):
    """Generate monthly and yearly P&L summaries"""
    print("\n" + "="*80)
    print("MONTHLY & YEARLY P&L ANALYSIS")
    print("="*80)

    # Create DataFrame
    df = pd.DataFrame({
        'date': portfolio['daily_dates'],
        'equity': portfolio['daily_equity'],
        'daily_pnl': portfolio['daily_pnl']
    })

    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['year_month'] = df['date'].dt.to_period('M')

    # Monthly summary
    monthly = df.groupby('year_month').agg({
        'daily_pnl': 'sum',
        'equity': 'last'
    }).reset_index()

    monthly['return_pct'] = (monthly['equity'].pct_change() * 100).fillna(0)
    monthly['cumulative_pnl'] = monthly['daily_pnl'].cumsum()

    # Yearly summary
    yearly = df.groupby('year').agg({
        'daily_pnl': 'sum',
        'equity': 'last'
    }).reset_index()

    yearly['return_pct'] = yearly['daily_pnl'] / portfolio['initial_capital'] * 100

    return monthly, yearly, df


def print_monthly_summary(monthly):
    """Print monthly P&L table"""
    print("\n📅 MONTHLY P&L SUMMARY")
    print("="*80)
    print(f"{'Month':<12} {'P&L':>12} {'Return %':>10} {'Equity':>15} {'Cumulative':>15}")
    print("-"*80)

    for _, row in monthly.iterrows():
        month_str = str(row['year_month'])
        pnl = row['daily_pnl']
        ret = row['return_pct']
        equity = row['equity']
        cum_pnl = row['cumulative_pnl']

        pnl_color = "+" if pnl >= 0 else ""
        ret_color = "+" if ret >= 0 else ""

        print(f"{month_str:<12} ${pnl:>11,.2f} {ret_color}{ret:>9.2f}% ${equity:>13,.0f} ${cum_pnl:>13,.0f}")

    # Summary stats
    print("-"*80)
    positive_months = (monthly['daily_pnl'] > 0).sum()
    total_months = len(monthly)
    win_rate = positive_months / total_months * 100

    print(f"\n📊 Monthly Statistics:")
    print(f"   Total Months: {total_months}")
    print(f"   Positive Months: {positive_months} ({win_rate:.1f}%)")
    print(f"   Average Monthly P&L: ${monthly['daily_pnl'].mean():,.2f}")
    print(f"   Average Monthly Return: {monthly['return_pct'].mean():.2f}%")
    print(f"   Best Month: ${monthly['daily_pnl'].max():,.2f} ({monthly['return_pct'].max():.2f}%)")
    print(f"   Worst Month: ${monthly['daily_pnl'].min():,.2f} ({monthly['return_pct'].min():.2f}%)")
    print(f"   Std Dev: ${monthly['daily_pnl'].std():,.2f}")


def print_yearly_summary(yearly):
    """Print yearly P&L table"""
    print("\n" + "="*80)
    print("📆 YEARLY P&L SUMMARY")
    print("="*80)
    print(f"{'Year':<8} {'P&L':>15} {'Return %':>12} {'Final Equity':>18}")
    print("-"*80)

    for _, row in yearly.iterrows():
        year = int(row['year'])
        pnl = row['daily_pnl']
        ret = row['return_pct']
        equity = row['equity']

        pnl_color = "+" if pnl >= 0 else ""
        ret_color = "+" if ret >= 0 else ""

        print(f"{year:<8} ${pnl:>14,.2f} {ret_color}{ret:>11.2f}% ${equity:>16,.0f}")

    print("-"*80)

    # Summary stats
    positive_years = (yearly['daily_pnl'] > 0).sum()
    total_years = len(yearly)

    print(f"\n📊 Yearly Statistics:")
    print(f"   Total Years: {total_years}")
    print(f"   Positive Years: {positive_years}/{total_years}")
    print(f"   Average Yearly P&L: ${yearly['daily_pnl'].mean():,.2f}")
    print(f"   Average Yearly Return: {yearly['return_pct'].mean():.2f}%")
    print(f"   Best Year: ${yearly['daily_pnl'].max():,.2f} ({yearly['return_pct'].max():.2f}%)")
    print(f"   Worst Year: ${yearly['daily_pnl'].min():,.2f} ({yearly['return_pct'].min():.2f}%)")


def main():
    print("="*80)
    print("CRYPTO STRATEGY P&L ANALYSIS (5-YEAR)")
    print("="*80)

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

    # Initialize strategy
    strategy = InstitutionalCryptoPerp(
        bear_market_asset='PAXG-USD',
        bear_allocation=1.0
    )

    # Run backtest with daily tracking
    portfolio = backtest_with_daily_tracking(strategy, trading_data, btc_prices, paxg_prices)

    # Generate summaries
    monthly, yearly, daily_df = generate_pnl_summaries(portfolio)

    # Print results
    print_monthly_summary(monthly)
    print_yearly_summary(yearly)

    # Save to CSV
    output_dir = Path(__file__).parent.parent / 'results' / 'crypto'
    output_dir.mkdir(parents=True, exist_ok=True)

    monthly_path = output_dir / 'monthly_pnl.csv'
    yearly_path = output_dir / 'yearly_pnl.csv'
    daily_path = output_dir / 'daily_pnl.csv'

    monthly.to_csv(monthly_path, index=False)
    yearly.to_csv(yearly_path, index=False)
    daily_df.to_csv(daily_path, index=False)

    print(f"\n" + "="*80)
    print("✅ P&L ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📁 Files saved:")
    print(f"   - {monthly_path}")
    print(f"   - {yearly_path}")
    print(f"   - {daily_path}")


if __name__ == "__main__":
    main()
