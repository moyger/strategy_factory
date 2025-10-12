"""
Test with REALISTIC position sizing (no compounding leverage bug)

This fixes the critical bug where leverage was compounding with equity growth.

PROPER POSITION SIZING:
- Allocate X% of equity per position
- Leverage is applied to INITIAL capital only, not compounded equity
- Or use FIXED dollar amounts per position (stops growing)

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

from strategies.institutional_crypto_perp_strategy import MarketRegime


def calculate_realistic_position_size(price: float, volatility: float,
                                     equity: float, initial_capital: float,
                                     max_leverage: float = 1.5,
                                     allocation_pct: float = 0.10,
                                     use_fixed_sizing: bool = False):
    """
    Calculate position size with REALISTIC constraints

    Two modes:
    1. Fixed sizing: Use % of INITIAL capital (stops compounding)
    2. Percent-of-equity: Use % of current equity (but cap at reasonable size)
    """

    if use_fixed_sizing:
        # Mode 1: Fixed sizing (% of INITIAL capital)
        # This prevents unlimited growth
        base_notional = initial_capital * allocation_pct
    else:
        # Mode 2: Percent of equity with growth cap
        # Allow growth but cap at 10× initial position size
        base_notional = equity * allocation_pct
        max_notional = initial_capital * allocation_pct * 10  # Cap at 10× initial
        base_notional = min(base_notional, max_notional)

    # Adjust for volatility
    vol_adjusted = max(0.3, min(volatility, 2.0))
    target_notional = base_notional * (0.5 / vol_adjusted)

    # Apply leverage cap (on the BASE, not compounded equity)
    max_with_leverage = base_notional * max_leverage
    final_notional = min(target_notional, max_with_leverage)

    # Position size
    position_size = final_notional / price
    actual_leverage = final_notional / base_notional  # Leverage relative to base

    return position_size, actual_leverage


def run_realistic_backtest(max_positions=10, bear_allocation=1.0,
                           leverage=1.5, use_fixed_sizing=False,
                           config_name=""):
    """Run backtest with REALISTIC position sizing"""

    print(f"\n{'='*80}")
    print(f"📊 TESTING: {config_name}")
    print(f"   Position sizing: {'FIXED (% of initial)' if use_fixed_sizing else 'PERCENT OF EQUITY (capped at 10×)'}")
    print(f"{'='*80}")

    # Download 5 years of data
    LOOKBACK_YEARS = 5
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365 + 30)).strftime('%Y-%m-%d')

    print(f"\n📅 Period: {start_date} → {end_date}")

    # Top cryptos
    TOP_CRYPTOS = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'DOGE-USD',
        'XRP-USD', 'DOT-USD', 'UNI-USD', 'LINK-USD', 'LTC-USD',
        'BCH-USD', 'ATOM-USD', 'SOL-USD', 'AVAX-USD', 'MATIC-USD',
        'SAND-USD', 'MANA-USD', 'AAVE-USD', 'RUNE-USD', 'SNX-USD'
    ]

    all_symbols = TOP_CRYPTOS + ['PAXG-USD']

    print(f"📥 Downloading {len(all_symbols)} symbols...")

    close_prices = pd.DataFrame()

    for symbol in all_symbols:
        try:
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty and len(data) > 250:
                close_prices[symbol] = data['Close']
                print(f"   ✅ {symbol} ({len(data)} days)")
        except:
            print(f"   ❌ {symbol} failed")

    close_prices = close_prices.fillna(method='ffill', limit=5)

    print(f"\n✅ Downloaded {len(close_prices.columns)} symbols")

    # Separate PAXG
    paxg_prices = close_prices['PAXG-USD']
    crypto_prices = close_prices.drop(columns=['PAXG-USD'])
    btc_prices = crypto_prices['BTC-USD']

    # Calculate BTC regime (simple 200MA)
    btc_ma200 = btc_prices.rolling(200).mean()
    regime = pd.Series('NEUTRAL', index=btc_prices.index)
    regime[btc_prices > btc_ma200] = 'BULL_RISK_ON'
    regime[btc_prices <= btc_ma200] = 'BEAR_RISK_OFF'

    print(f"\n⚙️  Running backtest...")
    print(f"   Max positions: {max_positions}")
    print(f"   Leverage: {leverage}×")
    print(f"   Bear allocation: {bear_allocation*100}% PAXG")

    # Backtest
    initial_capital = 100000
    equity = initial_capital
    positions = {}  # {symbol: {'size': X, 'entry_price': Y, 'entry_date': Z}}
    trades = []
    equity_curve = []

    paxg_position = 0
    paxg_entry_price = 0

    for i, date in enumerate(close_prices.index):
        if i < 200:  # Need 200 days for MA
            continue

        if i % 200 == 0:
            print(f"   Processing {date.strftime('%Y-%m-%d')} ({i}/{len(close_prices)} days, ${equity:,.0f})")

        current_regime = regime.loc[date]

        # Update position values
        for symbol in list(positions.keys()):
            if symbol in crypto_prices.columns:
                positions[symbol]['current_price'] = crypto_prices.loc[date, symbol]

        # Calculate equity
        unrealized_pnl = sum(
            (pos['current_price'] - pos['entry_price']) * pos['size']
            for pos in positions.values()
        )

        paxg_unrealized = 0
        if paxg_position > 0:
            paxg_current = paxg_prices.loc[date]
            paxg_unrealized = (paxg_current - paxg_entry_price) * paxg_position

        realized_pnl = sum(t.get('pnl', 0) for t in trades)
        equity = initial_capital + realized_pnl + unrealized_pnl + paxg_unrealized

        # BEAR regime: Close crypto, buy PAXG
        if current_regime == 'BEAR_RISK_OFF':
            # Close all crypto
            for symbol in list(positions.keys()):
                pos = positions[symbol]
                pnl = (pos['current_price'] - pos['entry_price']) * pos['size']
                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'pnl': pnl,
                    'reason': 'Bear regime'
                })
                del positions[symbol]

            # Buy PAXG if not already in
            if paxg_position == 0 and bear_allocation > 0:
                realized_pnl = sum(t.get('pnl', 0) for t in trades)
                current_equity = initial_capital + realized_pnl

                paxg_allocation = current_equity * bear_allocation
                paxg_entry_price = paxg_prices.loc[date]
                paxg_position = paxg_allocation / paxg_entry_price

                trades.append({
                    'date': date,
                    'symbol': 'PAXG',
                    'action': 'BUY',
                    'pnl': 0,
                    'reason': 'Bear allocation'
                })

        # Exit PAXG when leaving bear
        elif paxg_position > 0:
            paxg_current = paxg_prices.loc[date]
            paxg_pnl = (paxg_current - paxg_entry_price) * paxg_position

            trades.append({
                'date': date,
                'symbol': 'PAXG',
                'action': 'SELL',
                'pnl': paxg_pnl,
                'reason': 'Exit bear'
            })

            paxg_position = 0
            paxg_entry_price = 0

        # BULL regime: Trade crypto
        if current_regime == 'BULL_RISK_ON' and len(positions) < max_positions:
            # Simple entry: Buy anything above 50-day high
            for symbol in crypto_prices.columns:
                if symbol in positions or len(positions) >= max_positions:
                    continue

                prices_series = crypto_prices[symbol].dropna()
                if len(prices_series) < 50:
                    continue

                current_price = prices_series.loc[date]
                high_50 = prices_series.iloc[-51:-1].max()  # Previous 50 days

                # Entry: Break above 50-day high
                if current_price > high_50:
                    # Calculate volatility
                    returns = prices_series.pct_change().dropna()
                    vol = returns.iloc[-30:].std() * np.sqrt(365) if len(returns) >= 30 else 0.5

                    # Calculate position size (FIXED)
                    position_size, lev = calculate_realistic_position_size(
                        price=current_price,
                        volatility=vol,
                        equity=equity,
                        initial_capital=initial_capital,
                        max_leverage=leverage,
                        allocation_pct=0.10,
                        use_fixed_sizing=use_fixed_sizing
                    )

                    if position_size > 0:
                        positions[symbol] = {
                            'size': position_size,
                            'entry_price': current_price,
                            'current_price': current_price,
                            'entry_date': date
                        }

                        trades.append({
                            'date': date,
                            'symbol': symbol,
                            'action': 'BUY',
                            'pnl': 0,
                            'reason': 'Breakout'
                        })

        # Exit: Drop below 20-day low
        for symbol in list(positions.keys()):
            prices_series = crypto_prices[symbol].dropna()
            if len(prices_series) < 20:
                continue

            current_price = prices_series.loc[date]
            low_20 = prices_series.iloc[-21:-1].min()

            if current_price < low_20:
                pos = positions[symbol]
                pnl = (current_price - pos['entry_price']) * pos['size']

                trades.append({
                    'date': date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'pnl': pnl,
                    'reason': 'Stop loss (20-day low)'
                })

                del positions[symbol]

        equity_curve.append(equity)

    # Final calculations
    equity_series = pd.Series(equity_curve, index=close_prices.index[200:])

    total_return = ((equity_series.iloc[-1] / initial_capital) - 1) * 100
    years = len(equity_series) / 252
    annualized = ((equity_series.iloc[-1] / initial_capital) ** (1/years) - 1) * 100

    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax * 100
    max_dd = drawdown.min()

    daily_returns = equity_series.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    # Print results
    print(f"\n{'='*80}")
    print(f"📊 RESULTS: {config_name}")
    print(f"{'='*80}")
    print(f"\n💰 Performance:")
    print(f"   Final Equity: ${equity_series.iloc[-1]:,.0f}")
    print(f"   Total Return: {total_return:,.1f}%")
    print(f"   Annualized: {annualized:.1f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"\n📈 Trading:")
    print(f"   Total trades: {len([t for t in trades if t['action'] == 'SELL'])}")

    return {
        'config': config_name,
        'final_equity': equity_series.iloc[-1],
        'total_return': total_return,
        'annualized': annualized,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'use_fixed_sizing': use_fixed_sizing
    }


def main():
    """Test with different position sizing methods"""

    print("="*80)
    print("🧪 REALISTIC POSITION SIZING TEST")
    print("="*80)

    results = []

    # Test 1: FIXED sizing (% of initial capital - never grows)
    r1 = run_realistic_backtest(
        max_positions=10,
        bear_allocation=1.0,
        leverage=1.5,
        use_fixed_sizing=True,
        config_name="FIXED SIZING (10% of initial $100k = $10k per position)"
    )
    results.append(r1)

    # Test 2: Percent of equity (but capped at 10× initial)
    r2 = run_realistic_backtest(
        max_positions=10,
        bear_allocation=1.0,
        leverage=1.5,
        use_fixed_sizing=False,
        config_name="PERCENT OF EQUITY (10% of current, capped at 10× initial)"
    )
    results.append(r2)

    # Comparison
    print("\n" + "="*80)
    print("📊 COMPARISON")
    print("="*80)

    print(f"\n{'Method':<50} {'Final $':<15} {'Return':<12} {'Annual':<10} {'Sharpe':<10} {'Max DD'}")
    print("-" * 110)

    for r in results:
        print(f"{r['config']:<50} ${r['final_equity']:>12,.0f}   {r['total_return']:>9.1f}%   {r['annualized']:>8.1f}%   {r['sharpe']:>8.2f}   {r['max_dd']:>8.2f}%")

    print("\n" + "="*80)
    print("💡 ANALYSIS")
    print("="*80)
    print("\nThe FIXED sizing method is more realistic:")
    print("- Prevents unlimited position growth")
    print("- Matches how real traders operate")
    print("- Still allows compounding through MORE positions, not BIGGER positions")
    print("\nThe PERCENT method (even capped) can still grow too large over time")


if __name__ == '__main__':
    main()
