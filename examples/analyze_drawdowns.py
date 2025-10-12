"""
Analyze drawdowns in the institutional crypto perp strategy

This script identifies the largest drawdowns and their causes to find
ways to reduce them without overfitting.

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

# Import hybrid backtest
exec(open('examples/test_institutional_crypto_perp_hybrid.py').read().replace('if __name__', 'if False'))

from strategies.institutional_crypto_perp_strategy import InstitutionalCryptoPerp, MarketRegime


def analyze_drawdown_periods(equity_curve, regime_history, trades, top_n=5):
    """Identify and analyze the largest drawdown periods"""

    # Calculate drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax * 100

    # Find drawdown periods (start to recovery)
    in_drawdown = drawdown < -1.0  # More than -1% drawdown

    periods = []
    start = None

    for i, date in enumerate(drawdown.index):
        if in_drawdown.iloc[i] and start is None:
            start = i
        elif not in_drawdown.iloc[i] and start is not None:
            # Drawdown ended
            dd_period = drawdown.iloc[start:i+1]
            max_dd = dd_period.min()
            max_dd_date = dd_period.idxmin()

            periods.append({
                'start': drawdown.index[start],
                'end': date,
                'max_dd_date': max_dd_date,
                'max_dd': max_dd,
                'duration_days': (date - drawdown.index[start]).days,
                'start_equity': equity_curve.iloc[start],
                'bottom_equity': equity_curve.loc[max_dd_date],
                'end_equity': equity_curve.iloc[i]
            })

            start = None

    # Sort by max drawdown
    periods_df = pd.DataFrame(periods).sort_values('max_dd')

    print("="*80)
    print("📉 TOP DRAWDOWN PERIODS ANALYSIS")
    print("="*80)

    for i, period in periods_df.head(top_n).iterrows():
        print(f"\n🔴 Drawdown #{i+1}: {period['max_dd']:.2f}%")
        print(f"   Period: {period['start'].strftime('%Y-%m-%d')} → {period['end'].strftime('%Y-%m-%d')}")
        print(f"   Duration: {period['duration_days']} days")
        print(f"   Equity: ${period['start_equity']:,.0f} → ${period['bottom_equity']:,.0f} → ${period['end_equity']:,.0f}")
        print(f"   Max DD date: {period['max_dd_date'].strftime('%Y-%m-%d')}")

        # Analyze regime during this period
        period_regime = regime_history[period['start']:period['end']]
        regime_counts = period_regime.value_counts()

        print(f"\n   Regime distribution:")
        for regime, count in regime_counts.items():
            pct = count / len(period_regime) * 100
            print(f"      {regime}: {count} days ({pct:.1f}%)")

        # Analyze trades during this period
        period_trades = trades[
            (trades['date'] >= period['start']) &
            (trades['date'] <= period['end'])
        ]

        if len(period_trades) > 0:
            sell_trades = period_trades[period_trades['action'] == 'SELL']

            if len(sell_trades) > 0:
                total_pnl = sell_trades['pnl'].sum()
                losing_trades = sell_trades[sell_trades['pnl'] < 0]
                winning_trades = sell_trades[sell_trades['pnl'] > 0]

                print(f"\n   Trading activity:")
                print(f"      Total trades: {len(sell_trades)}")
                print(f"      Winning: {len(winning_trades)} (${winning_trades['pnl'].sum():,.0f})")
                print(f"      Losing: {len(losing_trades)} (${losing_trades['pnl'].sum():,.0f})")
                print(f"      Net P&L: ${total_pnl:,.0f}")

                # Largest losses
                if len(losing_trades) > 0:
                    worst_trades = losing_trades.nsmallest(3, 'pnl')
                    print(f"\n      Worst losses:")
                    for _, trade in worst_trades.iterrows():
                        print(f"         {trade['date'].strftime('%Y-%m-%d')} {trade['symbol']}: ${trade['pnl']:,.0f} ({trade['pnl_pct']:.1f}%) - {trade['reason']}")

        # Check if PAXG position during this period
        paxg_trades = period_trades[period_trades['symbol'] == 'PAXG']
        if len(paxg_trades) > 0:
            paxg_pnl = paxg_trades[paxg_trades['action'] == 'SELL']['pnl'].sum()
            print(f"\n   PAXG during drawdown: ${paxg_pnl:,.0f}")

    print("\n" + "="*80)

    return periods_df


def test_drawdown_reduction_strategies():
    """Test different approaches to reduce drawdown"""

    print("\n" + "="*80)
    print("🧪 TESTING DRAWDOWN REDUCTION STRATEGIES")
    print("="*80)

    # Download data
    LOOKBACK_YEARS = 2
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365)).strftime('%Y-%m-%d')

    TOP_30_PERPS = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
        'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
        'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'BCH-USD',
        'NEAR-USD', 'APT-USD', 'ARB-USD', 'OP-USD', 'FTM-USD',
        'AAVE-USD', 'MKR-USD', 'SNX-USD', 'RUNE-USD',
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'ICP-USD'
    ]

    all_symbols = TOP_30_PERPS + ['PAXG-USD']

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

    paxg_prices = close_prices['PAXG-USD']
    crypto_data = {
        'close': close_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'high': high_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'low': low_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'volume': pd.DataFrame()
    }
    btc_prices = crypto_data['close']['BTC-USD']

    # Test configurations
    configs = [
        {
            'name': 'BASELINE (100% PAXG)',
            'daily_loss_limit': 0.03,
            'trail_atr_multiple': 2.0,
            'max_leverage_bull': 1.5,
            'max_positions': 10
        },
        {
            'name': 'TIGHTER STOP (1.5×ATR)',
            'daily_loss_limit': 0.03,
            'trail_atr_multiple': 1.5,  # Tighter trailing stop
            'max_leverage_bull': 1.5,
            'max_positions': 10
        },
        {
            'name': 'STRICTER LOSS LIMIT (-2%)',
            'daily_loss_limit': 0.02,  # Stricter daily limit
            'trail_atr_multiple': 2.0,
            'max_leverage_bull': 1.5,
            'max_positions': 10
        },
        {
            'name': 'LOWER LEVERAGE (1.0×)',
            'daily_loss_limit': 0.03,
            'trail_atr_multiple': 2.0,
            'max_leverage_bull': 1.0,  # Lower leverage
            'max_positions': 10
        },
        {
            'name': 'FEWER POSITIONS (5 max)',
            'daily_loss_limit': 0.03,
            'trail_atr_multiple': 2.0,
            'max_leverage_bull': 1.5,
            'max_positions': 5  # More concentrated
        },
        {
            'name': 'COMBINED (1.5×ATR + -2% + 1.0× leverage)',
            'daily_loss_limit': 0.02,
            'trail_atr_multiple': 1.5,
            'max_leverage_bull': 1.0,
            'max_positions': 10
        }
    ]

    results = []

    for config in configs:
        print(f"\n📊 Testing: {config['name']}")

        strategy = InstitutionalCryptoPerp(
            max_positions=config['max_positions'],
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
            trail_atr_multiple=config['trail_atr_multiple'],
            breakdown_period=10,
            vol_target_per_position=0.20,
            portfolio_vol_target=0.50,
            max_leverage_bull=config['max_leverage_bull'],
            max_leverage_neutral=1.0,
            max_leverage_bear=0.5,
            daily_loss_limit=config['daily_loss_limit'],
            weekend_degross=False
        )

        backtest_results = backtest_hybrid_perp(
            strategy=strategy,
            data=crypto_data,
            btc_prices=btc_prices,
            paxg_prices=paxg_prices,
            initial_capital=100000,
            bear_allocation=1.0
        )

        equity_curve = backtest_results['equity_curve']

        # Calculate metrics
        total_return = ((equity_curve.iloc[-1] / 100000) - 1) * 100
        years = len(equity_curve) / 252
        annualized_return = ((equity_curve.iloc[-1] / 100000) ** (1 / years) - 1) * 100

        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax * 100
        max_drawdown = drawdown.min()

        daily_returns = equity_curve.pct_change().dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

        trades = backtest_results['trades']
        crypto_trades = trades[trades['symbol'] != 'PAXG']
        sell_trades = crypto_trades[crypto_trades['action'] == 'SELL']

        results.append({
            'config': config['name'],
            'total_return': total_return,
            'annualized': annualized_return,
            'sharpe': sharpe_ratio,
            'max_dd': max_drawdown,
            'final_equity': equity_curve.iloc[-1],
            'trades': len(sell_trades)
        })

        print(f"   Return: {total_return:.1f}% | Sharpe: {sharpe_ratio:.2f} | Max DD: {max_drawdown:.2f}% | Trades: {len(sell_trades)}")

    # Summary
    print("\n" + "="*80)
    print("📊 DRAWDOWN REDUCTION RESULTS")
    print("="*80)

    df = pd.DataFrame(results)

    print(f"\n{'Configuration':<40} {'Return':<12} {'Annual':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades'}")
    print("-" * 100)

    for _, row in df.iterrows():
        print(f"{row['config']:<40} {row['total_return']:>10.1f}%  {row['annualized']:>10.1f}%  {row['sharpe']:>8.2f}  {row['max_dd']:>10.2f}%  {row['trades']:>6.0f}")

    # Find best balance
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)

    # Best Sharpe
    best_sharpe_idx = df['sharpe'].idxmax()
    print(f"\n🏆 Best Risk-Adjusted (Sharpe): {df.loc[best_sharpe_idx, 'config']}")
    print(f"   Sharpe: {df.loc[best_sharpe_idx, 'sharpe']:.2f}")
    print(f"   Max DD: {df.loc[best_sharpe_idx, 'max_dd']:.2f}%")
    print(f"   Return: {df.loc[best_sharpe_idx, 'total_return']:.1f}%")

    # Lowest DD
    best_dd_idx = df['max_dd'].idxmax()  # Max because DD is negative
    print(f"\n🛡️  Lowest Drawdown: {df.loc[best_dd_idx, 'config']}")
    print(f"   Max DD: {df.loc[best_dd_idx, 'max_dd']:.2f}%")
    print(f"   Sharpe: {df.loc[best_dd_idx, 'sharpe']:.2f}")
    print(f"   Return: {df.loc[best_dd_idx, 'total_return']:.1f}%")

    return df


def main():
    """Main execution"""

    print("="*80)
    print("🔍 DRAWDOWN ANALYSIS - INSTITUTIONAL CRYPTO PERP STRATEGY")
    print("="*80)

    # First, run baseline to analyze drawdowns
    print("\n📊 Running baseline (100% PAXG) to analyze drawdowns...")

    LOOKBACK_YEARS = 2
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=LOOKBACK_YEARS*365)).strftime('%Y-%m-%d')

    TOP_30_PERPS = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD',
        'ADA-USD', 'DOGE-USD', 'MATIC-USD', 'DOT-USD', 'AVAX-USD',
        'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'BCH-USD',
        'NEAR-USD', 'APT-USD', 'ARB-USD', 'OP-USD', 'FTM-USD',
        'AAVE-USD', 'MKR-USD', 'SNX-USD', 'RUNE-USD',
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'ICP-USD'
    ]

    all_symbols = TOP_30_PERPS + ['PAXG-USD']

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

    paxg_prices = close_prices['PAXG-USD']
    crypto_data = {
        'close': close_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'high': high_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'low': low_prices.drop(columns=['PAXG-USD'], errors='ignore'),
        'volume': pd.DataFrame()
    }
    btc_prices = crypto_data['close']['BTC-USD']

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

    results = backtest_hybrid_perp(
        strategy=strategy,
        data=crypto_data,
        btc_prices=btc_prices,
        paxg_prices=paxg_prices,
        initial_capital=100000,
        bear_allocation=1.0
    )

    # Analyze drawdown periods
    drawdown_periods = analyze_drawdown_periods(
        results['equity_curve'],
        results['regime_history'],
        results['trades'],
        top_n=5
    )

    # Test drawdown reduction strategies
    test_results = test_drawdown_reduction_strategies()

    print("\n✨ Analysis complete!")


if __name__ == '__main__':
    main()
