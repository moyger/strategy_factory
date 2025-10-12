"""
Test Institutional Stock Momentum Strategy

Backtests the stock version adapted from crypto strategy with:
- Top 50 S&P 500 momentum stocks (quarterly rebalancing)
- SPY regime filtering (200/50-day MAs)
- TLT/GLD bear market protection
- Full validation suite
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from strategies.nick_radge_momentum import NickRadgeMomentumStrategy
import warnings
warnings.filterwarnings('ignore')

def download_sp500_tickers():
    """Get S&P 500 tickers"""
    # Use a subset for initial testing (top liquid stocks)
    sp500_subset = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
        'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
        'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
        'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T',
        'AMGN', 'IBM', 'BA', 'GE', 'CAT', 'SBUX', 'LOW', 'GS', 'ELV', 'SPGI'
    ]
    return sp500_subset

def download_data(tickers, start_date, end_date):
    """Download historical data for all tickers + SPY + bear assets"""
    print(f"Downloading data for {len(tickers)} stocks...")

    # Add SPY (regime) and bear assets (TLT, GLD)
    all_tickers = tickers + ['SPY', 'TLT', 'GLD']

    # Download
    data = yf.download(all_tickers, start=start_date, end=end_date, progress=False)

    # Handle MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        close = data['Close']
        high = data['High']
        low = data['Low']
    else:
        close = data[['Close']]
        high = data[['High']]
        low = data[['Low']]

    # Fill forward then drop remaining NaNs
    close = close.fillna(method='ffill').dropna()
    high = high.fillna(method='ffill').dropna()
    low = low.fillna(method='ffill').dropna()

    return close, high, low

def run_stock_momentum_backtest(bear_asset='TLT'):
    """
    Run full backtest using Nick Radge strategy (already has regime + bear asset features)

    Args:
        bear_asset: 'TLT' (bonds) or 'GLD' (gold)
    """
    print("="*80)
    print(f"INSTITUTIONAL STOCK MOMENTUM BACKTEST (Bear Asset: {bear_asset})")
    print("="*80)

    # Parameters
    start_date = '2015-01-01'
    end_date = '2024-12-31'
    initial_capital = 100000

    # Download S&P 500 subset
    tickers = download_sp500_tickers()

    # Download data
    close, high, low = download_data(tickers, start_date, end_date)

    print(f"\nData loaded: {len(close)} days, {len(close.columns)} symbols")
    print(f"Date range: {close.index[0].date()} to {close.index[-1].date()}")

    # Use Nick Radge strategy (already has regime filtering and bear asset allocation)
    print(f"\nInitializing Nick Radge Momentum Strategy...")
    print(f"- Portfolio Size: 10 stocks")
    print(f"- Momentum Period: 100 days (ROC)")
    print(f"- Regime Filter: SPY 200/50-day MAs")
    print(f"- Bear Asset: {bear_asset} (100% allocation)")
    print(f"- Rebalance: Quarterly")

    strategy = NickRadgeMomentumStrategy(
        portfolio_size=10,
        roc_period=100,
        rebalance_frequency='quarterly',
        use_regime_filter=True,
        bear_market_asset=bear_asset,
        bear_allocation=1.0,
        portfolio_weighting='momentum'  # Allocate more to stronger momentum
    )

    # Run backtest
    print("\nRunning backtest...")
    results = strategy.backtest(close, initial_capital=initial_capital)

    # Extract equity curve
    equity = results['equity']

    # Calculate metrics
    total_return = ((equity.iloc[-1] / equity.iloc[0]) - 1) * 100

    # Annualized return
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    annualized_return = ((equity.iloc[-1] / equity.iloc[0]) ** (1/years) - 1) * 100

    # Max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax * 100
    max_drawdown = drawdown.min()

    # Sharpe ratio (daily returns)
    daily_returns = equity.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

    # Win rate (from trades)
    trades = results.get('trades', [])
    if trades:
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / len(trades)) * 100
    else:
        win_rate = 0

    # Print results
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    print(f"Initial Capital:     ${initial_capital:,.2f}")
    print(f"Final Equity:        ${equity.iloc[-1]:,.2f}")
    print(f"Total Return:        {total_return:+.2f}%")
    print(f"Annualized Return:   {annualized_return:.2f}%")
    print(f"Max Drawdown:        {max_drawdown:.2f}%")
    print(f"Sharpe Ratio:        {sharpe:.2f}")
    print(f"Number of Trades:    {len(trades)}")
    if trades:
        print(f"Win Rate:            {win_rate:.1f}%")

    # Regime breakdown
    if 'regime_stats' in results:
        print("\n" + "="*80)
        print("REGIME BREAKDOWN")
        print("="*80)
        for regime, stats in results['regime_stats'].items():
            print(f"\n{regime}:")
            print(f"  Days: {stats.get('days', 0)}")
            print(f"  Return: {stats.get('return', 0):+.2f}%")

    # Bear asset performance
    if 'bear_asset_trades' in results and results['bear_asset_trades']:
        print("\n" + "="*80)
        print(f"{bear_asset} PERFORMANCE (Bear Markets)")
        print("="*80)
        bear_trades = results['bear_asset_trades']
        bear_pnl = sum(t.get('pnl', 0) for t in bear_trades)
        print(f"Number of {bear_asset} positions: {len(bear_trades)}")
        print(f"Total {bear_asset} P&L: ${bear_pnl:,.2f}")

    # Buy and hold comparison (SPY)
    spy_return = ((close['SPY'].iloc[-1] / close['SPY'].iloc[0]) - 1) * 100
    print("\n" + "="*80)
    print("BENCHMARK COMPARISON")
    print("="*80)
    print(f"SPY Buy & Hold:      {spy_return:+.2f}%")
    print(f"Strategy:            {total_return:+.2f}%")
    print(f"Outperformance:      {total_return - spy_return:+.2f}%")

    return results, equity

def compare_bear_assets():
    """Compare TLT vs GLD as bear market asset"""
    print("\n" + "="*80)
    print("COMPARING BEAR MARKET ASSETS: TLT vs GLD")
    print("="*80)

    results_tlt, equity_tlt = run_stock_momentum_backtest(bear_asset='TLT')
    print("\n" + "-"*80 + "\n")
    results_gld, equity_gld = run_stock_momentum_backtest(bear_asset='GLD')

    # Compare
    print("\n" + "="*80)
    print("BEAR ASSET COMPARISON")
    print("="*80)

    tlt_return = ((equity_tlt.iloc[-1] / equity_tlt.iloc[0]) - 1) * 100
    gld_return = ((equity_gld.iloc[-1] / equity_gld.iloc[0]) - 1) * 100

    print(f"\nTLT (20-Year Bonds): {tlt_return:+.2f}%")
    print(f"GLD (Gold ETF):      {gld_return:+.2f}%")

    if tlt_return > gld_return:
        print(f"\n✅ WINNER: TLT (+{tlt_return - gld_return:.2f}% better)")
    else:
        print(f"\n✅ WINNER: GLD (+{gld_return - tlt_return:.2f}% better)")

if __name__ == '__main__':
    # Run single backtest first (TLT as default)
    print("Starting backtest with TLT (bonds) as bear asset...")
    results, equity = run_stock_momentum_backtest(bear_asset='TLT')

    # Optionally compare both bear assets
    print("\n\nWould you like to compare TLT vs GLD? (This will take twice as long)")
    # For now, just run TLT version
    # Uncomment below to run comparison:
    # compare_bear_assets()

    print("\n✅ Backtest complete!")
