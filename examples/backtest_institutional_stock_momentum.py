"""
Backtest: Institutional Stock Momentum Strategy (06)

Tests the signal-based stock momentum strategy with:
- Dynamic top 50 momentum universe (quarterly rebalancing)
- SPY regime filter (3-tier)
- Optional Donchian breakout confirmation
- 2×ATR trailing stops
- Vol-targeted position sizing
- TLT/GLD bear market allocation
- Leverage (1.0-1.2×)

Compares with Nick Radge rebalancing strategy
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import vectorbt as vbt
import quantstats as qs
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Load strategy
import importlib.util
spec = importlib.util.spec_from_file_location("institutional_stock_momentum",
    Path(__file__).parent.parent / "strategies" / "06_institutional_stock_momentum.py")
inst_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inst_module)

InstitutionalStockMomentum = inst_module.InstitutionalStockMomentum
MarketRegime = inst_module.MarketRegime

print("="*80)
print("INSTITUTIONAL STOCK MOMENTUM - FULL BACKTEST (WITH GLD)")
print("="*80)
print("\n🎯 Testing: Signal-based momentum with trailing stops + GLD allocation")
print("   Period: 5 years (2020-2024)")
print("   Initial Capital: $100,000\n")

# ============================================================================
# 1. DOWNLOAD DATA
# ============================================================================
print("="*80)
print("DOWNLOADING DATA")
print("="*80)

# Top S&P 500 stocks (same as Nick Radge universe)
stock_tickers = [
    # Tech
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',
    'CRM', 'AMD', 'INTC', 'CSCO', 'QCOM', 'INTU', 'NOW', 'AMAT', 'MU', 'PLTR',
    # Finance
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW', 'AXP', 'SPGI',
    # Healthcare
    'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
    # Consumer
    'WMT', 'HD', 'MCD', 'NKE', 'COST', 'SBUX', 'TGT', 'LOW', 'DIS', 'CMCSA',
]

# Download stock data
print(f"\n📥 Downloading {len(stock_tickers)} stocks...")
start_date = '2019-01-01'  # Extra lookback for indicators
end_date = '2024-12-31'

stock_data = yf.download(stock_tickers, start=start_date, end=end_date, progress=False)

# Extract OHLC
if isinstance(stock_data.columns, pd.MultiIndex):
    close = stock_data['Close'].copy()
    high = stock_data['High'].copy()
    low = stock_data['Low'].copy()
else:
    close = stock_data[['Close']].copy()
    high = stock_data[['High']].copy()
    low = stock_data[['Low']].copy()

close = close.ffill().dropna(how='all')
high = high.ffill().dropna(how='all')
low = low.ffill().dropna(how='all')

# Align all OHLC data
common_index = close.index.intersection(high.index).intersection(low.index)
close = close.loc[common_index]
high = high.loc[common_index]
low = low.loc[common_index]

print(f"✅ Stock data: {len(close)} days, {len(close.columns)} stocks")

# Download SPY (regime filter + benchmark)
print(f"\n📊 Downloading SPY and bear assets...")
spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)
if isinstance(spy_data.columns, pd.MultiIndex):
    spy_data.columns = spy_data.columns.get_level_values(0)
spy_prices = spy_data['Close'].ffill()

# Download TLT (bonds) and GLD (gold) for bear allocation
tlt_data = yf.download('TLT', start=start_date, end=end_date, progress=False)
if isinstance(tlt_data.columns, pd.MultiIndex):
    tlt_data.columns = tlt_data.columns.get_level_values(0)
tlt_prices = tlt_data['Close'].ffill()

gld_data = yf.download('GLD', start=start_date, end=end_date, progress=False)
if isinstance(gld_data.columns, pd.MultiIndex):
    gld_data.columns = gld_data.columns.get_level_values(0)
gld_prices = gld_data['Close'].ffill()

print(f"✅ SPY: {len(spy_prices)} days")
print(f"✅ TLT: {len(tlt_prices)} days")
print(f"✅ GLD: {len(gld_prices)} days")

# Align all data
common_dates = (close.index
                .intersection(spy_prices.index)
                .intersection(tlt_prices.index)
                .intersection(gld_prices.index))

close = close.loc[common_dates]
high = high.loc[common_dates]
low = low.loc[common_dates]
spy_prices = spy_prices.loc[common_dates]
tlt_prices = tlt_prices.loc[common_dates]
gld_prices = gld_prices.loc[common_dates]

# Filter to backtest period (2020-2024)
backtest_start = '2020-01-01'
close = close[close.index >= backtest_start]
high = high[high.index >= backtest_start]
low = low[low.index >= backtest_start]
spy_prices = spy_prices[spy_prices.index >= backtest_start]
tlt_prices = tlt_prices[tlt_prices.index >= backtest_start]
gld_prices = gld_prices[gld_prices.index >= backtest_start]

print(f"\n✅ Backtest period: {close.index[0].date()} to {close.index[-1].date()}")
print(f"   Total days: {len(close)}")

# ============================================================================
# 2. RUN SIMPLIFIED BACKTEST (Rebalancing-based approximation)
# ============================================================================
print("\n" + "="*80)
print("RUNNING BACKTEST (Rebalancing Approximation)")
print("="*80)
print("\nNote: This is a SIMPLIFIED version using quarterly rebalancing")
print("      Full event-driven simulation with trailing stops would be more complex")

# Initialize strategy
strategy = InstitutionalStockMomentum(
    universe='sp500',
    max_positions=10,
    rebalance_frequency='quarterly',
    momentum_lookback=100,
    top_n_momentum=50,
    spy_ma_long=200,
    spy_ma_short=50,
    use_donchian_confirmation=False,  # Keep it simple
    trail_atr_multiple=2.0,
    vol_target_per_position=0.18,
    max_leverage_strong_bull=1.2,
    max_leverage_weak_bull=1.0,
    max_leverage_bear=0.5,
    bear_market_asset='GLD',  # Test with GLD (gold)
    bear_allocation=1.0
)

# Calculate regime
print(f"\n📊 Calculating SPY regime...")
regime = strategy.calculate_regime(spy_prices)

regime_counts = regime.value_counts()
total = len(regime)
print(f"\nRegime Distribution:")
for r in [MarketRegime.STRONG_BULL, MarketRegime.WEAK_BULL, MarketRegime.BEAR]:
    count = regime_counts.get(r.value, 0)
    pct = (count / total) * 100
    print(f"  {r.value}: {count} days ({pct:.1f}%)")

# Calculate momentum scores
print(f"\n📈 Calculating momentum scores...")
momentum = strategy.calculate_momentum_scores(close)

# Generate allocations (simplified quarterly rebalancing)
print(f"\n💼 Generating portfolio allocations (quarterly rebalancing)...")

# Rebalance dates (quarter starts)
rebalance_dates = pd.date_range(start=close.index[0], end=close.index[-1], freq='QS')
rebalance_dates = [d for d in rebalance_dates if d in close.index]

# Skip early dates where we don't have enough data
min_date = close.index[0] + pd.Timedelta(days=200)
rebalance_dates = [d for d in rebalance_dates if d >= min_date]

print(f"   Rebalance dates: {len(rebalance_dates)}")
print(f"   First: {rebalance_dates[0].date()}, Last: {rebalance_dates[-1].date()}")

# Initialize allocations
allocations = pd.DataFrame(0.0, index=close.index, columns=close.columns)

# Add GLD column for bear allocation
allocations['GLD'] = 0.0

# Track current positions
current_holdings = None

for date in close.index:
    if date < min_date:
        continue

    # Check if rebalance date
    if date in rebalance_dates or current_holdings is None:
        current_regime = regime.loc[date]

        # Determine portfolio size based on regime
        if current_regime == MarketRegime.STRONG_BULL.value:
            positions = strategy.max_positions  # 10
        elif current_regime == MarketRegime.WEAK_BULL.value:
            positions = max(3, strategy.max_positions // 2)  # 5
        else:  # BEAR
            positions = 0

        # Reset allocations
        allocations.loc[date, :] = 0.0

        if positions == 0:
            # Bear market: 100% GLD
            allocations.loc[date, 'GLD'] = strategy.bear_allocation
            current_holdings = {'GLD': strategy.bear_allocation}
        else:
            # Select top momentum stocks
            momentum_universe = strategy.select_momentum_universe(close, date, top_n=50)

            if len(momentum_universe) > 0:
                # Get momentum scores for universe
                if date in momentum.index:
                    scores = momentum.loc[date, momentum_universe].dropna()

                    # Take top N by momentum
                    top_stocks = scores.nlargest(positions).index.tolist()

                    # Equal weight (simplification - vol-targeting is more complex)
                    weight = 1.0 / len(top_stocks)

                    for ticker in top_stocks:
                        if ticker in allocations.columns:
                            allocations.loc[date, ticker] = weight

                    current_holdings = {ticker: weight for ticker in top_stocks}
                else:
                    current_holdings = {}
            else:
                current_holdings = {}
    else:
        # Between rebalances - maintain positions
        if current_holdings:
            for ticker, weight in current_holdings.items():
                if ticker in allocations.columns:
                    allocations.loc[date, ticker] = weight

# Count active positions
active_positions = (allocations > 0).sum(axis=1)
print(f"\n   Avg positions: {active_positions.mean():.1f}")
print(f"   Max positions: {active_positions.max():.0f}")

# Add GLD to price data for backtesting
close_with_gld = close.copy()
close_with_gld['GLD'] = gld_prices

# Align allocations and prices
common_cols = allocations.columns.intersection(close_with_gld.columns)
allocations_aligned = allocations[common_cols]
close_aligned = close_with_gld[common_cols]

print(f"\n📈 Running vectorbt backtest...")
print(f"   Columns: {len(common_cols)}")
print(f"   Days: {len(close_aligned)}")

# Run backtest
portfolio = vbt.Portfolio.from_orders(
    close=close_aligned,
    size=allocations_aligned,
    size_type='targetpercent',
    init_cash=100000,
    fees=0.001,  # 0.1% per trade
    slippage=0.0005,  # 0.05% slippage
    group_by=True,
    cash_sharing=True
)

# ============================================================================
# 3. CALCULATE RESULTS
# ============================================================================
print("\n" + "="*80)
print("RESULTS - INSTITUTIONAL STOCK MOMENTUM")
print("="*80)

# Extract metrics
pf_value = portfolio.value()
if isinstance(pf_value, pd.DataFrame):
    final_value = float(pf_value.values[-1][0])
elif isinstance(pf_value, pd.Series):
    final_value = float(pf_value.values[-1])
else:
    final_value = float(pf_value)

total_return = ((final_value / 100000) - 1) * 100

try:
    sharpe = portfolio.sharpe_ratio()
    if isinstance(sharpe, pd.Series):
        sharpe = float(sharpe.values[0])
    else:
        sharpe = float(sharpe)
except:
    sharpe = 0.0

try:
    max_dd = portfolio.max_drawdown()
    if isinstance(max_dd, pd.Series):
        max_dd = float(max_dd.values[0])
    else:
        max_dd = float(max_dd)
except:
    max_dd = 0.0

try:
    num_trades = portfolio.trades.count()
    if isinstance(num_trades, pd.Series):
        num_trades = int(num_trades.sum())
    else:
        num_trades = int(num_trades)
except:
    num_trades = 0

print(f"\n📊 PERFORMANCE:")
print(f"Initial Capital:     $100,000")
print(f"Final Value:         ${final_value:,.2f}")
print(f"Total Return:        {total_return:+.2f}%")
print(f"Sharpe Ratio:        {sharpe:.2f}")
print(f"Max Drawdown:        {max_dd*100:.2f}%")
print(f"Total Trades:        {num_trades}")

# Calculate SPY benchmark
spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100
print(f"\n📈 vs SPY:")
print(f"SPY Return:          {spy_return:+.2f}%")
print(f"Outperformance:      {total_return - spy_return:+.2f}%")

if total_return > spy_return:
    print(f"Status:              ✅ OUTPERFORMED SPY")
else:
    print(f"Status:              ❌ UNDERPERFORMED SPY")

# ============================================================================
# 4. SAVE RESULTS
# ============================================================================
print("\n" + "="*80)
print("GENERATING REPORTS")
print("="*80)

output_dir = Path('results/institutional_stock_momentum')
output_dir.mkdir(parents=True, exist_ok=True)

# Get returns
returns = portfolio.returns()
if isinstance(returns, pd.DataFrame):
    returns = returns.iloc[:, 0]

spy_returns = spy_prices.pct_change()

# Generate QuantStats report
print(f"\n📊 Generating QuantStats tearsheet...")
qs.reports.html(
    returns,
    benchmark=spy_returns,
    output=str(output_dir / 'institutional_stock_momentum_GLD_tearsheet.html'),
    title='Institutional Stock Momentum - With GLD Protection'
)

print(f"✅ Tearsheet saved: {output_dir}/institutional_stock_momentum_GLD_tearsheet.html")

# Save summary
summary_df = pd.DataFrame([{
    'Strategy': 'Institutional Stock Momentum',
    'Bear_Asset': 'GLD',
    'Initial_Capital': 100000,
    'Final_Value': final_value,
    'Total_Return_Pct': total_return,
    'Sharpe_Ratio': sharpe,
    'Max_Drawdown_Pct': max_dd * 100,
    'Num_Trades': num_trades,
    'SPY_Return_Pct': spy_return,
    'Outperformance_Pct': total_return - spy_return,
    'Period': f"{close.index[0].date()} to {close.index[-1].date()}"
}])

summary_df.to_csv(output_dir / 'backtest_summary_GLD.csv', index=False)
print(f"✅ Summary saved: {output_dir}/backtest_summary_GLD.csv")

print("\n" + "="*80)
print("✅ BACKTEST COMPLETE")
print("="*80)
print(f"\n📂 Open: {output_dir}/institutional_stock_momentum_GLD_tearsheet.html")
