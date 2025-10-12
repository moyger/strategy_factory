"""
Simple Stock Momentum Backtest

Quick test of Nick Radge momentum strategy on S&P 500 stocks with:
- Top 10 momentum stocks (quarterly rebalancing)
- SPY regime filtering (200/50-day MAs)
- TLT/GLD bear market protection
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import vectorbt as vbt
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("INSTITUTIONAL STOCK MOMENTUM BACKTEST")
print("="*80)

# Download top 60 liquid S&P 500 stocks
print("\n📥 Downloading S&P 500 stock data...")
tickers = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
    'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
    'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
    'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
    'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T',
    'AMGN', 'IBM', 'BA', 'GE', 'CAT', 'SBUX', 'LOW', 'GS', 'ELV', 'SPGI'
]

# Add SPY + bear assets
all_tickers = tickers + ['SPY', 'TLT', 'GLD']

# Download data
start_date = '2014-01-01'  # Need extra data for ROC calculation
end_date = '2024-12-31'

print("   (This may take 1-2 minutes...)")
data = yf.download(all_tickers, start=start_date, end=end_date, progress=True, threads=True)

# Extract close prices
if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

# Fill forward and drop NaNs
close = close.ffill().dropna()

# Remove tickers with insufficient data
min_data_points = 500
for col in close.columns:
    if close[col].count() < min_data_points:
        print(f"   Removing {col} (insufficient data: {close[col].count()} days)")
        close = close.drop(columns=[col])

print(f"✅ Downloaded {len(close)} days for {len(close.columns)} symbols")
print(f"   Date range: {close.index[0].date()} to {close.index[-1].date()}")

# Separate SPY and bear assets
spy_prices = close['SPY']
tlt_prices = close['TLT']
gld_prices = close['GLD']
stock_prices = close[tickers]

# Test with TLT first
print("\n" + "="*80)
print("TESTING WITH TLT (20-YEAR BONDS) AS BEAR ASSET")
print("="*80)

initial_capital = 100000

# Initialize strategy
strategy = NickRadgeMomentumStrategy(
    portfolio_size=10,
    roc_period=100,
    rebalance_freq='QS',  # Quarterly
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=10,
    weak_bull_positions=5,
    bear_positions=0,
    bear_market_asset='TLT',
    bear_allocation=1.0
)

print(f"\nStrategy Configuration:")
print(f"- Portfolio Size: 10 stocks")
print(f"- Momentum Period: 100 days (ROC)")
print(f"- Rebalance: Quarterly")
print(f"- Regime Filter: SPY 200/50-day MAs")
print(f"- Bear Asset: TLT (100% allocation)")
print(f"- Strong Bull: 10 positions")
print(f"- Weak Bull: 5 positions")
print(f"- Bear: 0 positions (100% TLT)")

# Generate allocations
print(f"\n⚙️  Generating portfolio allocations...")

# Need to add TLT to prices for bear allocation
prices_with_bear = pd.concat([stock_prices, tlt_prices.to_frame()], axis=1)

# Calculate SPY ROC for relative strength
spy_roc = spy_prices.pct_change(100)

allocations = strategy.generate_allocations(
    prices=prices_with_bear,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

print(f"✅ Allocations generated")

# Run vectorbt backtest
print(f"\n📊 Running backtest...")

# Create position sizes (allocations * capital / price)
position_sizes = allocations.div(prices_with_bear).mul(initial_capital)

# Build portfolio
portfolio = vbt.Portfolio.from_orders(
    close=prices_with_bear,
    size=position_sizes,
    size_type='amount',
    init_cash=initial_capital,
    fees=0.001,  # 0.1% per trade
    freq='1D'
)

# Get results (handle Series returns)
def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

total_return = extract_value(portfolio.total_return()) * 100
annualized_return = extract_value(portfolio.annualized_return()) * 100
sharpe = extract_value(portfolio.sharpe_ratio())
max_drawdown = extract_value(portfolio.max_drawdown()) * 100
total_trades = portfolio.trades.count()

print("\n" + "="*80)
print("PERFORMANCE SUMMARY")
print("="*80)
portfolio_value = portfolio.value()
if isinstance(portfolio_value, pd.Series):
    final_value = float(portfolio_value.values[-1])
else:
    final_value = float(portfolio_value.iloc[-1].iloc[0] if hasattr(portfolio_value.iloc[-1], 'iloc') else portfolio_value.iloc[-1])
print(f"Initial Capital:     ${initial_capital:,.2f}")
print(f"Final Equity:        ${final_value:,.2f}")
print(f"Total Return:        {total_return:+.2f}%")
print(f"Annualized Return:   {annualized_return:.2f}%")
print(f"Max Drawdown:        {max_drawdown:.2f}%")
print(f"Sharpe Ratio:        {sharpe:.2f}")
print(f"Number of Trades:    {total_trades}")

# SPY benchmark
spy_start = spy_prices.iloc[0]
spy_end = spy_prices.iloc[-1]
spy_return = ((spy_end / spy_start) - 1) * 100

print("\n" + "="*80)
print("BENCHMARK COMPARISON")
print("="*80)
print(f"SPY Buy & Hold:      {spy_return:+.2f}%")
print(f"Strategy:            {total_return:+.2f}%")
print(f"Outperformance:      {total_return - spy_return:+.2f}%")

# Now test with GLD
print("\n\n" + "="*80)
print("TESTING WITH GLD (GOLD) AS BEAR ASSET")
print("="*80)

strategy_gld = NickRadgeMomentumStrategy(
    portfolio_size=10,
    roc_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=10,
    weak_bull_positions=5,
    bear_positions=0,
    bear_market_asset='GLD',
    bear_allocation=1.0
)

# Add GLD to prices
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)

print(f"\n⚙️  Generating portfolio allocations...")
allocations_gld = strategy_gld.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Run vectorbt backtest
print(f"\n📊 Running backtest...")
position_sizes_gld = allocations_gld.div(prices_with_gld).mul(initial_capital)

portfolio_gld = vbt.Portfolio.from_orders(
    close=prices_with_gld,
    size=position_sizes_gld,
    size_type='amount',
    init_cash=initial_capital,
    fees=0.001,
    freq='1D'
)

# Get results
total_return_gld = extract_value(portfolio_gld.total_return()) * 100
annualized_return_gld = extract_value(portfolio_gld.annualized_return()) * 100
sharpe_gld = extract_value(portfolio_gld.sharpe_ratio())
max_drawdown_gld = extract_value(portfolio_gld.max_drawdown()) * 100
total_trades_gld = portfolio_gld.trades.count()

print("\n" + "="*80)
print("PERFORMANCE SUMMARY (GLD)")
print("="*80)
portfolio_value_gld = portfolio_gld.value()
if isinstance(portfolio_value_gld, pd.Series):
    final_value_gld = float(portfolio_value_gld.values[-1])
else:
    final_value_gld = float(portfolio_value_gld.iloc[-1].iloc[0] if hasattr(portfolio_value_gld.iloc[-1], 'iloc') else portfolio_value_gld.iloc[-1])
print(f"Initial Capital:     ${initial_capital:,.2f}")
print(f"Final Equity:        ${final_value_gld:,.2f}")
print(f"Total Return:        {total_return_gld:+.2f}%")
print(f"Annualized Return:   {annualized_return_gld:.2f}%")
print(f"Max Drawdown:        {max_drawdown_gld:.2f}%")
print(f"Sharpe Ratio:        {sharpe_gld:.2f}")
print(f"Number of Trades:    {total_trades_gld}")

# Compare bear assets
print("\n\n" + "="*80)
print("BEAR ASSET COMPARISON")
print("="*80)
print(f"\nTLT (20-Year Bonds): {total_return:+.2f}%")
print(f"GLD (Gold ETF):      {total_return_gld:+.2f}%")

if total_return > total_return_gld:
    print(f"\n✅ WINNER: TLT (+{total_return - total_return_gld:.2f}% better)")
else:
    print(f"\n✅ WINNER: GLD (+{total_return_gld - total_return:.2f}% better)")

print("\n✅ Stock momentum backtest complete!")
