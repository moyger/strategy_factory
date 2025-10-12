#!/usr/bin/env python3
"""
Example: ATR Breakout Strategy

This demonstrates the ATR Breakout strategy by Tomas Nesnidal.
Tests on various instruments and timeframes.

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from strategies.atr_breakout_strategy import ATRBreakoutStrategy, ATRBreakoutParams
from strategy_factory.analyzer import StrategyAnalyzer


def download_ohlc_data(symbol: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    """
    Download OHLC data from Yahoo Finance

    Args:
        symbol: Ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval (1d, 1h, 5m, etc.)

    Returns:
        DataFrame with OHLC data
    """
    print(f"📥 Downloading {symbol} data ({interval})...")
    data = yf.download(symbol, start=start_date, end=end_date, interval=interval, progress=False, auto_adjust=True)

    # Fix MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Ensure we have OHLC columns
    if 'Close' not in data.columns:
        raise ValueError(f"No data downloaded for {symbol}")

    # Remove any NaN rows
    data = data.dropna()

    print(f"✅ Downloaded {len(data)} bars")
    return data


def main():
    print("="*80)
    print("ATR BREAKOUT STRATEGY - EXAMPLE")
    print("="*80)

    # Configuration
    SYMBOL = "SPY"  # S&P 500 ETF
    START_DATE = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')  # 2 years
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 100000

    print(f"\n⚙️  Configuration:")
    print(f"   Symbol: {SYMBOL}")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")

    # Download data
    prices = download_ohlc_data(SYMBOL, START_DATE, END_DATE, interval="1d")

    # ==================== TEST 1: Default Parameters ====================
    print(f"\n{'='*80}")
    print("TEST 1: DEFAULT PARAMETERS")
    print(f"{'='*80}")

    params1 = ATRBreakoutParams(
        poi="prev_close",
        atr_period=40,
        k_multiplier=2.8,
        adx_period=25,
        adx_min=25.0,
        sma_period=100,
        atr_expansion_period=20,
        risk_per_trade=0.005,
        stop_r=1.5,
        target_r=3.0
    )

    strategy1 = ATRBreakoutStrategy(params1)
    portfolio1 = strategy1.backtest(prices, initial_capital=INITIAL_CAPITAL)
    strategy1.print_results(portfolio1, prices)

    # ==================== TEST 2: Aggressive Parameters ====================
    print(f"\n{'='*80}")
    print("TEST 2: AGGRESSIVE PARAMETERS (Lower k, tighter stops)")
    print(f"{'='*80}")

    params2 = ATRBreakoutParams(
        poi="prev_close",
        atr_period=20,           # Shorter ATR
        k_multiplier=2.0,        # Lower multiplier = more entries
        adx_period=14,
        adx_min=20.0,            # Lower ADX = more entries
        sma_period=50,           # Shorter SMA
        atr_expansion_period=None,  # No ATR expansion filter
        risk_per_trade=0.01,     # Higher risk (1%)
        stop_r=1.0,              # Tighter stop
        target_r=2.0             # Closer target
    )

    strategy2 = ATRBreakoutStrategy(params2)
    portfolio2 = strategy2.backtest(prices, initial_capital=INITIAL_CAPITAL)
    strategy2.print_results(portfolio2, prices)

    # ==================== TEST 3: Conservative Parameters ====================
    print(f"\n{'='*80}")
    print("TEST 3: CONSERVATIVE PARAMETERS (Higher k, wider stops)")
    print(f"{'='*80}")

    params3 = ATRBreakoutParams(
        poi="prev_close",
        atr_period=60,           # Longer ATR
        k_multiplier=3.5,        # Higher multiplier = fewer entries
        adx_period=25,
        adx_min=30.0,            # Higher ADX = only strong trends
        sma_period=200,          # Longer SMA
        atr_expansion_period=20,
        risk_per_trade=0.003,    # Lower risk (0.3%)
        stop_r=2.0,              # Wider stop
        target_r=4.0             # Further target
    )

    strategy3 = ATRBreakoutStrategy(params3)
    portfolio3 = strategy3.backtest(prices, initial_capital=INITIAL_CAPITAL)
    strategy3.print_results(portfolio3, prices)

    # ==================== TEST 4: No Filters (Pure Breakout) ====================
    print(f"\n{'='*80}")
    print("TEST 4: NO FILTERS (Pure ATR Breakout)")
    print(f"{'='*80}")

    params4 = ATRBreakoutParams(
        poi="prev_close",
        atr_period=40,
        k_multiplier=2.8,
        adx_period=25,
        adx_min=None,            # No ADX filter
        sma_period=None,         # No SMA filter
        atr_expansion_period=None,  # No ATR expansion filter
        risk_per_trade=0.005,
        stop_r=1.5,
        target_r=3.0
    )

    strategy4 = ATRBreakoutStrategy(params4)
    portfolio4 = strategy4.backtest(prices, initial_capital=INITIAL_CAPITAL)
    strategy4.print_results(portfolio4, prices)

    # ==================== COMPARISON ====================
    print(f"\n{'='*80}")
    print("STRATEGY COMPARISON")
    print(f"{'='*80}")

    results = []

    for i, (name, portfolio) in enumerate([
        ("Default", portfolio1),
        ("Aggressive", portfolio2),
        ("Conservative", portfolio3),
        ("No Filters", portfolio4)
    ], 1):
        final_value = portfolio.value().iloc[-1]
        total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100

        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
        except:
            sharpe = 0.0

        max_dd = portfolio.max_drawdown() * 100
        trades_count = portfolio.trades.count()

        try:
            win_rate = portfolio.trades.win_rate() * 100
        except:
            win_rate = 0.0

        results.append({
            'name': name,
            'return': total_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': trades_count,
            'win_rate': win_rate
        })

    print(f"\n{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<10} {'Trades':<10} {'Win Rate':<10}")
    print("-" * 80)

    for r in results:
        print(f"{r['name']:<20} {r['return']:>10.2f}%  {r['sharpe']:>8.2f}  {r['max_dd']:>8.2f}%  {r['trades']:>8}  {r['win_rate']:>8.1f}%")

    # Find best strategy
    best = max(results, key=lambda x: x['return'])
    print(f"\n🏆 BEST PERFORMER: {best['name']}")
    print(f"   Return: {best['return']:.2f}%")
    print(f"   Sharpe: {best['sharpe']:.2f}")

    # Generate QuantStats report for best strategy
    print(f"\n📊 Generating QuantStats report for best strategy...")

    # Get best portfolio
    best_portfolio = [portfolio1, portfolio2, portfolio3, portfolio4][results.index(best)]
    returns = best_portfolio.returns()

    analyzer = StrategyAnalyzer()
    report_path = analyzer.generate_full_report(
        returns,
        output_file=f'atr_breakout_{SYMBOL.lower()}_report.html',
        title=f'ATR Breakout Strategy ({best["name"]}) - {SYMBOL}',
        benchmark=None
    )

    print(f"✅ Report saved: {report_path}")

    print(f"\n{'='*80}")
    print("BACKTEST COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
