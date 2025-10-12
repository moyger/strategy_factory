#!/usr/bin/env python3
"""
Test Adaptive Qualifier vs Pure ROC vs Pure BSS

Compares three approaches:
1. Pure ROC (always)
2. Pure BSS (always)
3. Adaptive (ROC in STRONG_BULL, BSS otherwise)

This shows if regime-based switching can capture the best of both worlds.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_momentum_strategy import download_sp500_stocks, download_spy
from strategies.nick_radge_adaptive_qualifier import NickRadgeAdaptiveQualifier
from examples.compare_qualifiers import test_qualifier_on_nick_radge


if __name__ == "__main__":
    print("="*100)
    print("ADAPTIVE QUALIFIER TEST: ROC vs BSS vs ADAPTIVE")
    print("="*100)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000
    NUM_STOCKS = 50

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Capital: ${INITIAL_CAPITAL:,}")
    print(f"\n   Strategies to test:")
    print(f"   1. Pure ROC (always use ROC)")
    print(f"   2. Pure BSS (always use BSS)")
    print(f"   3. Adaptive (ROC in STRONG_BULL, BSS in WEAK_BULL/BEAR)")

    # Download data
    print(f"\n{'='*100}")
    print("DOWNLOADING DATA")
    print("="*100)

    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)

    # Add GLD
    if 'GLD' not in prices.columns:
        print(f"\n⚠️  Adding GLD...")
        gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
        if isinstance(gld_data.columns, pd.MultiIndex):
            gld_data.columns = gld_data.columns.get_level_values(0)
        prices['GLD'] = gld_data['Close']
        prices = prices.dropna()
        print(f"✅ GLD added")

    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready: {len(prices)} days, {len(prices.columns)} stocks")

    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Test all three approaches
    print(f"\n{'='*100}")
    print("RUNNING BACKTESTS")
    print("="*100)

    results = []

    # 1. Pure ROC
    print(f"\n{'='*100}")
    print("1. PURE ROC (Always ROC)")
    print("="*100)
    roc_result = test_qualifier_on_nick_radge('roc', prices, spy_prices, INITIAL_CAPITAL)
    if roc_result:
        results.append(roc_result)

    # 2. Pure BSS
    print(f"\n{'='*100}")
    print("2. PURE BSS (Always BSS)")
    print("="*100)
    bss_result = test_qualifier_on_nick_radge('bss', prices, spy_prices, INITIAL_CAPITAL)
    if bss_result:
        results.append(bss_result)

    # 3. Adaptive
    print(f"\n{'='*100}")
    print("3. ADAPTIVE (ROC in STRONG_BULL, BSS otherwise)")
    print("="*100)

    strategy = NickRadgeAdaptiveQualifier(
        portfolio_size=7,
        strong_bull_qualifier='roc',
        weak_bull_qualifier='bss',
        bear_qualifier='bss',
        bear_market_asset='GLD',
        bear_allocation=1.0,
        use_regime_filter=True
    )

    portfolio = strategy.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.001,
        slippage=0.0005
    )

    # Extract metrics
    final_value = portfolio.value().iloc[-1]
    if isinstance(final_value, pd.Series):
        final_value = final_value.sum()

    init_cash = portfolio.init_cash
    if isinstance(init_cash, pd.Series):
        init_cash = init_cash.sum()

    total_return = ((final_value / init_cash) - 1) * 100

    try:
        sharpe = portfolio.sharpe_ratio(freq='D')
        if isinstance(sharpe, pd.Series):
            sharpe = sharpe.mean()
    except:
        sharpe = 0.0

    max_dd = portfolio.max_drawdown()
    if isinstance(max_dd, pd.Series):
        max_dd = max_dd.max()

    trades_count = portfolio.trades.count()
    if isinstance(trades_count, pd.Series):
        trades_count = trades_count.sum()

    try:
        win_rate = portfolio.trades.win_rate()
        if isinstance(win_rate, pd.Series):
            win_rate = win_rate.mean()
    except:
        win_rate = 0.0

    try:
        profit_factor = portfolio.trades.profit_factor()
        if isinstance(profit_factor, pd.Series):
            profit_factor = profit_factor.mean()
    except:
        profit_factor = 0.0

    days = (prices.index[-1] - prices.index[0]).days
    years = days / 365.25
    annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0

    print(f"\n✅ Results:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Annualized: {annualized_return:.2f}%")
    print(f"   Sharpe: {sharpe:.2f}")
    print(f"   Max DD: {max_dd*100:.2f}%")
    print(f"   Trades: {trades_count}")
    print(f"   Win Rate: {win_rate*100:.1f}%")

    results.append({
        'Qualifier': 'ADAPTIVE',
        'Total Return %': total_return,
        'Annualized %': annualized_return,
        'Sharpe Ratio': sharpe,
        'Max Drawdown %': max_dd * 100,
        'Trades': trades_count,
        'Win Rate %': win_rate * 100,
        'Profit Factor': profit_factor,
        'Final Value': final_value
    })

    # Create comparison
    comparison_df = pd.DataFrame(results)

    print(f"\n{'='*100}")
    print("FINAL COMPARISON")
    print("="*100)

    print("\n" + comparison_df.to_string(index=False))

    print(f"\n{'='*100}")
    print("WINNERS")
    print("="*100)

    best_return = comparison_df.loc[comparison_df['Total Return %'].idxmax()]
    best_sharpe = comparison_df.loc[comparison_df['Sharpe Ratio'].idxmax()]
    best_drawdown = comparison_df.loc[comparison_df['Max Drawdown %'].idxmin()]

    print(f"\n🏆 Best Return: {best_return['Qualifier']} ({best_return['Total Return %']:.2f}%)")
    print(f"🏆 Best Sharpe: {best_sharpe['Qualifier']} ({best_sharpe['Sharpe Ratio']:.2f})")
    print(f"🏆 Best Drawdown: {best_drawdown['Qualifier']} ({best_drawdown['Max Drawdown %']:.2f}%)")

    print(f"\n📊 SPY Buy-Hold: {spy_return:.2f}%")

    # Key insights
    print(f"\n{'='*100}")
    print("KEY INSIGHTS")
    print("="*100)

    adaptive_return = comparison_df[comparison_df['Qualifier'] == 'ADAPTIVE']['Total Return %'].values[0]
    roc_return = comparison_df[comparison_df['Qualifier'] == 'ROC']['Total Return %'].values[0]
    bss_return = comparison_df[comparison_df['Qualifier'] == 'BSS']['Total Return %'].values[0]

    print(f"\n💡 Adaptive vs Pure Strategies:")
    print(f"   Adaptive: {adaptive_return:.2f}%")
    print(f"   ROC Only: {roc_return:.2f}% (diff: {adaptive_return - roc_return:+.2f}%)")
    print(f"   BSS Only: {bss_return:.2f}% (diff: {adaptive_return - bss_return:+.2f}%)")

    if adaptive_return > roc_return and adaptive_return > bss_return:
        print(f"\n   ✅ ADAPTIVE WINS! Best of both worlds achieved.")
    elif adaptive_return > max(roc_return, bss_return):
        print(f"\n   ✅ ADAPTIVE beats the better single strategy")
    else:
        print(f"\n   ❌ ADAPTIVE doesn't beat best single strategy")
        if roc_return > bss_return:
            print(f"      Pure ROC is better (strong bull market period)")
        else:
            print(f"      Pure BSS is better (defensive period)")

    # Save results
    comparison_df.to_csv('results/adaptive_comparison.csv', index=False)
    print(f"\n💾 Saved: results/adaptive_comparison.csv")

    print(f"\n{'='*100}")
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
