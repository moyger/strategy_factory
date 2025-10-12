"""
Test Rebalancing Frequency for Nick Radge + BSS Strategy

Compares weekly, monthly, and quarterly rebalancing to determine optimal frequency.
Transaction costs are critical - more frequent rebalancing = more trades = higher costs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy
from strategy_factory.performance_qualifiers import get_qualifier
import warnings
warnings.filterwarnings('ignore')

# Configuration
START_DATE = '2020-01-01'
END_DATE = '2025-01-01'
INITIAL_CAPITAL = 10000
FEES = 0.001  # 0.1%
SLIPPAGE = 0.0005  # 0.05%

# Top 50 S&P 500 stocks
TOP_50_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
    'CRM', 'AMD', 'INTC', 'CSCO', 'QCOM', 'INTU', 'NOW', 'AMAT', 'MU', 'PLTR',
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW', 'AXP', 'SPGI',
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
    'WMT', 'HD', 'MCD', 'NKE', 'COST', 'SBUX', 'TGT', 'LOW', 'DIS', 'CMCSA'
]

def download_sp500_stocks():
    """Download historical data for top 50 stocks + GLD + SPY"""
    print(f"📊 Downloading data for {len(TOP_50_TICKERS)} stocks + GLD + SPY...")
    print(f"📅 Period: {START_DATE} to {END_DATE}\n")

    all_tickers = TOP_50_TICKERS + ['GLD', 'SPY']
    data = yf.download(all_tickers, start=START_DATE, end=END_DATE,
                       auto_adjust=True, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
    else:
        prices = data

    prices = prices.dropna()

    if len(prices) == 0 or len(prices.columns) == 0:
        raise ValueError("Failed to download price data. Check network connection.")

    print(f"✅ Downloaded {len(prices.columns)} tickers")
    print(f"✅ Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"✅ Total trading days: {len(prices)}\n")

    return prices

def run_bss_with_frequency(prices, freq_code, freq_name):
    """Run BSS strategy with specified rebalancing frequency"""
    print(f"\n{'='*70}")
    print(f"🔄 Testing {freq_name} Rebalancing (freq='{freq_code}')")
    print(f"{'='*70}")

    # Create BSS qualifier
    bss = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)

    # Initialize strategy with BSS and specified rebalance frequency
    strategy = NickRadgeMomentumStrategy(
        portfolio_size=7,
        roc_period=100,
        ma_period=100,
        rebalance_freq=freq_code,  # KEY PARAMETER - set in __init__
        strong_bull_positions=7,
        weak_bull_positions=3,
        bear_positions=0,
        bear_market_asset='GLD',
        bear_allocation=1.0
    )

    # Monkey-patch to use BSS instead of ROC
    def rank_stocks_with_bss(self, prices, indicators, date, benchmark_roc=None):
        if date not in prices.index:
            return pd.DataFrame()

        # Calculate BSS scores
        available_prices = prices.loc[:date].iloc[-250:]
        bss_scores = bss.calculate(available_prices)
        latest_scores = bss_scores.loc[date]

        # Filter out GLD and SPY
        stock_prices = prices.drop(columns=['GLD', 'SPY'], errors='ignore')
        stock_scores = latest_scores[stock_prices.columns]
        stock_scores = stock_scores.replace([np.inf, -np.inf], np.nan).dropna()

        # Also apply MA filter like original
        above_ma = indicators['above_ma'].loc[date]
        valid_stocks = above_ma[above_ma == True].index
        if self.bear_market_asset:
            valid_stocks = [s for s in valid_stocks if s != self.bear_market_asset]

        # Filter BSS scores to only stocks above MA
        stock_scores = stock_scores[stock_scores.index.isin(valid_stocks)]

        if len(stock_scores) == 0:
            return pd.DataFrame()

        # Sort by BSS score (descending)
        ranked = stock_scores.sort_values(ascending=False)

        # Return DataFrame with same structure as original (ticker, roc)
        # Use 'roc' column name for compatibility with momentum weighting
        return pd.DataFrame({
            'ticker': ranked.index,
            'roc': ranked.values  # Using 'roc' column name for compatibility
        })

    strategy.rank_stocks = lambda prices, indicators, date, benchmark_roc=None: rank_stocks_with_bss(strategy, prices, indicators, date, benchmark_roc)

    # Run backtest
    portfolio = strategy.backtest(
        prices=prices,
        initial_capital=INITIAL_CAPITAL,
        fees=FEES,
        slippage=SLIPPAGE
    )

    # Extract metrics (specify freq='D' for daily data)
    total_return = portfolio.total_return() * 100
    sharpe = portfolio.sharpe_ratio(freq='D')
    max_dd = portfolio.max_drawdown() * 100
    trades = portfolio.trades.count()

    stats = portfolio.stats()
    win_rate = stats['Win Rate [%]']
    profit_factor = stats['Profit Factor']
    final_value = portfolio.total_profit() + INITIAL_CAPITAL

    print(f"\n📊 {freq_name} Results:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Sharpe Ratio: {sharpe:.2f}")
    print(f"   Max Drawdown: {max_dd:.2f}%")
    print(f"   Total Trades: {trades}")
    print(f"   Win Rate: {win_rate:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Final Value: ${final_value:,.2f}")

    return {
        'Frequency': freq_name,
        'Code': freq_code,
        'Total Return %': total_return,
        'Sharpe Ratio': sharpe,
        'Max Drawdown %': abs(max_dd),
        'Total Trades': trades,
        'Win Rate %': win_rate,
        'Profit Factor': profit_factor,
        'Final Value': final_value
    }

def main():
    print("\n" + "="*70)
    print("🔬 REBALANCING FREQUENCY COMPARISON")
    print("="*70)
    print("Strategy: Nick Radge Momentum + BSS Qualifier")
    print("Universe: Top 50 S&P 500 stocks")
    print("Portfolio Size: 7 stocks")
    print("Bear Asset: GLD (100% allocation)")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"Fees: {FEES*100}% | Slippage: {SLIPPAGE*100}%")
    print("="*70 + "\n")

    # Download data
    prices = download_sp500_stocks()

    # Test configurations
    frequencies = [
        ('W-FRI', 'Weekly'),      # Weekly on Fridays
        ('MS', 'Monthly'),        # Monthly start
        ('QS', 'Quarterly')       # Quarterly start (baseline)
    ]

    results = []
    for freq_code, freq_name in frequencies:
        result = run_bss_with_frequency(prices, freq_code, freq_name)
        results.append(result)

    # Create comparison DataFrame
    comparison_df = pd.DataFrame(results)
    comparison_df = comparison_df.sort_values('Total Return %', ascending=False)

    print("\n" + "="*70)
    print("📊 REBALANCING FREQUENCY COMPARISON RESULTS")
    print("="*70 + "\n")
    print(comparison_df.to_string(index=False))

    # Save results
    output_file = Path(__file__).parent.parent / 'results' / 'rebalancing_frequency_comparison.csv'
    output_file.parent.mkdir(exist_ok=True)
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✅ Results saved to: {output_file}")

    # Analysis
    print("\n" + "="*70)
    print("🔍 ANALYSIS")
    print("="*70 + "\n")

    winner = comparison_df.iloc[0]
    baseline = comparison_df[comparison_df['Frequency'] == 'Quarterly'].iloc[0]

    print(f"🏆 WINNER: {winner['Frequency']} Rebalancing")
    print(f"   Return: {winner['Total Return %']:.2f}%")
    print(f"   Sharpe: {winner['Sharpe Ratio']:.2f}")
    print(f"   Max DD: {winner['Max Drawdown %']:.2f}%")
    print(f"   Trades: {winner['Total Trades']}")

    print(f"\n📌 Baseline (Quarterly):")
    print(f"   Return: {baseline['Total Return %']:.2f}%")
    print(f"   Sharpe: {baseline['Sharpe Ratio']:.2f}")
    print(f"   Max DD: {baseline['Max Drawdown %']:.2f}%")
    print(f"   Trades: {baseline['Total Trades']}")

    if winner['Frequency'] != 'Quarterly':
        diff = winner['Total Return %'] - baseline['Total Return %']
        trade_diff = winner['Total Trades'] - baseline['Total Trades']
        print(f"\n💡 {winner['Frequency']} beats Quarterly by {diff:+.2f}%")
        print(f"   Trade difference: {trade_diff:+.0f} trades")
        print(f"   Transaction cost impact: ~${abs(trade_diff) * INITIAL_CAPITAL * (FEES + SLIPPAGE):,.2f}")
    else:
        print(f"\n✅ Quarterly remains optimal (Nick Radge's original design)")

    # Trade frequency impact
    print(f"\n📈 Trade Frequency Impact:")
    for _, row in comparison_df.iterrows():
        avg_trades_per_year = row['Total Trades'] / 5  # 5 years of data
        print(f"   {row['Frequency']:12s}: {row['Total Trades']:4.0f} total trades "
              f"(~{avg_trades_per_year:.0f}/year)")

    print("\n" + "="*70)
    print("✅ REBALANCING FREQUENCY TEST COMPLETE")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
