#!/usr/bin/env python3
"""
Full Crypto Hybrid Strategy Backtest with Reports

Generates:
1. Performance metrics (Sharpe, max DD, win rate, etc.)
2. QuantStats HTML tearsheet
3. Equity curve plot
4. Drawdown analysis
5. Monthly/yearly returns heatmap

Author: Strategy Factory
Date: 2025-01-14
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import quantstats as qs
import matplotlib.pyplot as plt
from datetime import datetime
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import using importlib for more reliable loading
def load_strategy_module(filename, module_name):
    """Load strategy module using importlib"""
    filepath = Path(__file__).parent.parent / 'strategies' / filename
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load strategy module
crypto_hybrid_module = load_strategy_module('06_nick_radge_crypto_hybrid.py', 'nick_radge_crypto_hybrid')
NickRadgeCryptoHybrid = crypto_hybrid_module.NickRadgeCryptoHybrid

# Enable QuantStats output
qs.extend_pandas()

def download_crypto_data(tickers, start_date, end_date):
    """Download crypto data from Yahoo Finance"""
    print(f"\n📊 Downloading {len(tickers)} cryptocurrencies...")

    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
    else:
        prices = data[['Close']].copy()
        prices.columns = [tickers[0]]

    # Drop columns with too much missing data
    missing_pct = prices.isna().sum() / len(prices)
    valid_cols = missing_pct[missing_pct < 0.20].index.tolist()

    if len(valid_cols) < len(tickers):
        dropped = set(tickers) - set(valid_cols)
        print(f"   ⚠️  Dropping {len(dropped)} tickers with >20% missing data")

    prices = prices[valid_cols]
    print(f"   ✅ Downloaded {len(prices.columns)} tickers, {len(prices)} days")

    return prices

def main():
    print("="*80)
    print("CRYPTO HYBRID STRATEGY - FULL BACKTEST WITH REPORTS")
    print("="*80)

    # Configuration
    START_DATE = "2020-01-01"  # Start from beginning of 2020 (full year)
    END_DATE = "2025-10-12"     # Extend to October 12, 2025 (as requested)
    INITIAL_CAPITAL = 100000

    # Top 50 crypto universe
    top_50_cryptos = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
        'ADA-USD', 'AVAX-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD',
        'SHIB-USD', 'LTC-USD', 'UNI7083-USD', 'LINK-USD', 'ATOM-USD',
        'ETC-USD', 'XLM-USD', 'BCH-USD', 'NEAR-USD', 'ALGO-USD',
        'FIL-USD', 'VET-USD', 'ICP-USD', 'APT21794-USD', 'HBAR-USD',
        'ARB11841-USD', 'OP-USD', 'GRT6719-USD', 'STX4847-USD', 'RUNE-USD',
        'AAVE-USD', 'MKR-USD', 'INJ-USD', 'SNX-USD', 'FTM-USD',
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'EGLD-USD', 'XTZ-USD',
        'THETA-USD', 'EOS-USD', 'FLOW-USD', 'KCS-USD', 'ZEC-USD',
        'NEO-USD', 'DASH-USD', 'COMP-USD', 'SUSHI-USD', 'YFI-USD'
    ]

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Universe: Top 50 cryptocurrencies")

    # Download data
    crypto_prices = download_crypto_data(top_50_cryptos, START_DATE, END_DATE)

    # Download BTC for regime filter
    print(f"\n   Downloading BTC for regime filter...")
    btc_data = yf.download('BTC-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(btc_data.columns, pd.MultiIndex):
        btc_prices = btc_data['Close'].iloc[:, 0]
    else:
        btc_prices = btc_data['Close']

    # Download PAXG for bear protection
    print(f"   Downloading PAXG for bear protection...")
    paxg_data = yf.download('PAXG-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(paxg_data.columns, pd.MultiIndex):
        paxg_close = paxg_data['Close'].iloc[:, 0]
    else:
        paxg_close = paxg_data['Close']

    # Add PAXG to prices
    crypto_prices['PAXG-USD'] = paxg_close

    print(f"\n✅ Data ready: {len(crypto_prices.columns)} cryptos, {len(crypto_prices)} days")
    print(f"   Period: {crypto_prices.index[0].date()} to {crypto_prices.index[-1].date()}")

    # Initialize strategy
    print("\n" + "="*80)
    print("RUNNING HYBRID 70/30 TQS STRATEGY")
    print("="*80)

    strategy = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=5,
        qualifier_type='tqs',
        use_momentum_weighting=True,
        bear_asset='PAXG-USD'
    )

    # Run backtest with realistic costs
    # Fees: 0.002 = 0.2% (realistic for crypto exchanges)
    # Slippage: 0.002 = 0.2% (realistic for rebalancing altcoins)
    portfolio = strategy.backtest(
        crypto_prices,
        btc_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.002,  # 0.2% (was 0.1%)
        slippage=0.002,  # 0.2% (was 0.05%)
        log_trades=False  # Set to True for detailed trade log
    )

    # Print results
    strategy.print_results(portfolio, crypto_prices)

    # Generate reports
    print("\n" + "="*80)
    print("GENERATING COMPREHENSIVE REPORTS")
    print("="*80)

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'results' / 'crypto_hybrid' / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract returns
    portfolio_value = portfolio.value()
    if isinstance(portfolio_value, pd.DataFrame):
        portfolio_value = portfolio_value.iloc[:, 0]

    returns = portfolio_value.pct_change().fillna(0)

    # Download SPY for benchmark
    print("\n📊 Downloading SPY benchmark...")
    spy_data = yf.download('SPY', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(spy_data.columns, pd.MultiIndex):
        spy_prices = spy_data['Close'].iloc[:, 0]
    else:
        spy_prices = spy_data['Close']

    spy_returns = spy_prices.pct_change().fillna(0)

    # Align returns
    returns = returns.reindex(spy_returns.index).fillna(0)
    spy_returns = spy_returns.reindex(returns.index).fillna(0)

    # Generate QuantStats HTML report
    print("\n1️⃣  Generating QuantStats HTML tearsheet...")
    report_path = output_dir / 'quantstats_tearsheet.html'
    qs.reports.html(
        returns,
        spy_returns,
        output=str(report_path),
        title='Crypto Hybrid Strategy (70/30 TQS) - Full Tearsheet'
    )
    print(f"   ✅ Saved to: {report_path}")

    # Generate equity curve plot
    print("\n2️⃣  Generating equity curve plot...")
    fig, ax = plt.subplots(figsize=(14, 7))
    portfolio_value.plot(ax=ax, label='Hybrid 70/30 TQS', linewidth=2)
    ax.set_title('Crypto Hybrid Strategy - Equity Curve', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    equity_path = output_dir / 'equity_curve.png'
    plt.savefig(equity_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Saved to: {equity_path}")

    # Generate drawdown plot
    print("\n3️⃣  Generating drawdown analysis...")
    fig, ax = plt.subplots(figsize=(14, 7))
    drawdown = (portfolio_value / portfolio_value.cummax() - 1) * 100
    drawdown.plot(ax=ax, color='red', linewidth=2, label='Drawdown (%)')
    ax.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
    ax.set_title('Crypto Hybrid Strategy - Drawdown Analysis', fontsize=16, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    dd_path = output_dir / 'drawdown_analysis.png'
    plt.savefig(dd_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Saved to: {dd_path}")

    # Generate monthly returns heatmap
    print("\n4️⃣  Generating monthly returns heatmap...")
    fig = qs.plots.monthly_heatmap(returns, figsize=(12, 8))
    heatmap_path = output_dir / 'monthly_returns_heatmap.png'
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✅ Saved to: {heatmap_path}")

    # Save detailed metrics to CSV
    print("\n5️⃣  Generating detailed metrics CSV...")
    try:
        win_rate = strategy._safe_scalar(portfolio.trades.win_rate()) * 100
    except:
        win_rate = 0.0

    try:
        profit_factor = strategy._safe_scalar(portfolio.trades.profit_factor())
    except:
        profit_factor = 0.0

    metrics = {
        'Total Return': f"{strategy._safe_scalar(portfolio.total_return()) * 100:.2f}%",
        'Annualized Return': f"{strategy._safe_scalar(portfolio.annualized_return()) * 100:.2f}%",
        'Sharpe Ratio': f"{strategy._safe_scalar(portfolio.sharpe_ratio(freq='D')):.2f}",
        'Max Drawdown': f"{strategy._safe_scalar(portfolio.max_drawdown()) * 100:.2f}%",
        'Win Rate': f"{win_rate:.2f}%",
        'Profit Factor': f"{profit_factor:.2f}",
        'Total Trades': f"{len(portfolio.trades.records)}",
        'Start Date': crypto_prices.index[0].strftime('%Y-%m-%d'),
        'End Date': crypto_prices.index[-1].strftime('%Y-%m-%d'),
        'Initial Capital': f"${INITIAL_CAPITAL:,}",
        'Final Value': f"${strategy._safe_scalar(portfolio.value().iloc[-1]):,.2f}"
    }

    metrics_df = pd.DataFrame.from_dict(metrics, orient='index', columns=['Value'])
    metrics_path = output_dir / 'detailed_metrics.csv'
    metrics_df.to_csv(metrics_path)
    print(f"   ✅ Saved to: {metrics_path}")

    # Summary
    print("\n" + "="*80)
    print("✅ ALL REPORTS GENERATED SUCCESSFULLY")
    print("="*80)
    print(f"\n📁 Reports saved to: {output_dir}")
    print(f"\n📊 Files created:")
    print(f"   1. quantstats_tearsheet.html - Full QuantStats tearsheet (50+ metrics)")
    print(f"   2. equity_curve.png - Portfolio value over time")
    print(f"   3. drawdown_analysis.png - Drawdown visualization")
    print(f"   4. monthly_returns_heatmap.png - Monthly returns heatmap")
    print(f"   5. detailed_metrics.csv - All performance metrics")

    print(f"\n🌐 Open the HTML report:")
    print(f"   open {report_path}")

    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
