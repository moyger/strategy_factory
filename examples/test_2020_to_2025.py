"""
Nick Radge Strategy Test - 2020 to 2025
Testing the exact period requested: January 1, 2020 to September 2025

This includes:
- COVID crash (March 2020)
- Recovery bull run (2020-2021)
- Bear market (2022)
- Recovery (2023-2024)
- Recent market (2025 YTD)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import vectorbt as vbt
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("NICK RADGE STRATEGY: 2020-2025 TEST")
print("="*80)
print("\nTest Period: January 1, 2020 to September 30, 2025")
print("\nThis period includes:")
print("  - COVID crash (March 2020)")
print("  - Bull run recovery (2020-2021)")
print("  - Bear market (2022)")
print("  - Recovery (2023-2024)")
print("  - 2025 YTD")

# Download data
print("\n" + "="*80)
print("DOWNLOADING DATA")
print("="*80)

tickers = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
    'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
    'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
    'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
    'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T',
    'AMGN', 'IBM', 'BA', 'GE', 'CAT', 'SBUX', 'LOW', 'GS', 'ELV', 'SPGI'
]

all_tickers = tickers + ['SPY', 'GLD']

# Download from 2019 to allow for 200-day MA calculation
print("Downloading data (2019-2025 to allow for indicators)...")
data = yf.download(all_tickers, start='2019-01-01', end='2025-09-30', progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill().dropna()

# Remove insufficient data
min_data_points = 200  # Need at least 200 days for MA
for col in list(close.columns):
    if close[col].count() < min_data_points:
        print(f"   Removing {col} (insufficient data)")
        close = close.drop(columns=[col])

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[[t for t in tickers if t in close.columns]]

print(f"✅ Data ready: {len(close)} days, {len(stock_prices.columns)} stocks")

# Filter to test period
start_test = '2020-01-01'
end_test = '2025-09-30'

print(f"\n📅 Filtering to test period: {start_test} to {end_test}")

# Helper function
def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

# Initialize strategy
print("\n" + "="*80)
print("RUNNING BACKTEST")
print("="*80)

strategy = NickRadgeMomentumStrategy(
    portfolio_size=7,
    roc_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=7,
    weak_bull_positions=3,
    bear_positions=0,
    bear_market_asset='GLD',
    bear_allocation=1.0
)

print(f"\n⚙️  Configuration:")
print(f"   Portfolio: 7 stocks (momentum-weighted)")
print(f"   Rebalance: Quarterly")
print(f"   Regime filter: 3-tier (STRONG_BULL/WEAK_BULL/BEAR)")
print(f"   Bear asset: 100% GLD")
print(f"   ROC period: 100 days")

# Generate allocations
print("\n⚙️  Generating allocations...")
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)
spy_roc = spy_prices.pct_change(100)

allocations = strategy.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Filter to test period
allocations_test = allocations[(allocations.index >= start_test) & (allocations.index <= end_test)]
prices_test = prices_with_gld[(prices_with_gld.index >= start_test) & (prices_with_gld.index <= end_test)]
spy_test = spy_prices[(spy_prices.index >= start_test) & (spy_prices.index <= end_test)]

print(f"✅ Test period data: {len(prices_test)} trading days")

# Run vectorbt backtest
print("\n📊 Running backtest...")

INITIAL_CAPITAL = 5000

portfolio = vbt.Portfolio.from_orders(
    close=prices_test,
    size=allocations_test,
    size_type='targetpercent',
    init_cash=INITIAL_CAPITAL,
    fees=0.001,
    group_by=True,
    cash_sharing=True,
    freq='D'
)

# Extract metrics
pf_value = portfolio.value()
if isinstance(pf_value, pd.DataFrame):
    final_value = float(pf_value.values[-1][0])
elif isinstance(pf_value, pd.Series):
    final_value = float(pf_value.values[-1])
else:
    final_value = float(pf_value)

total_return = extract_value(portfolio.total_return()) * 100
annualized = extract_value(portfolio.annualized_return(freq='D')) * 100
sharpe = extract_value(portfolio.sharpe_ratio(freq='D'))
max_dd = extract_value(portfolio.max_drawdown()) * 100

# Calculate years
years = (prices_test.index[-1] - prices_test.index[0]).days / 365.25

# SPY comparison
spy_return = ((spy_test.iloc[-1] / spy_test.iloc[0]) - 1) * 100
spy_annualized = ((spy_test.iloc[-1] / spy_test.iloc[0]) ** (1/years) - 1) * 100

# Results
print("\n" + "="*80)
print("RESULTS - 2020 TO 2025")
print("="*80)

print(f"\n📅 Period: {prices_test.index[0].date()} to {prices_test.index[-1].date()}")
print(f"   Duration: {years:.2f} years ({len(prices_test)} trading days)")

print(f"\n💰 Strategy Performance:")
print(f"   Initial Capital:     ${INITIAL_CAPITAL:,}")
print(f"   Final Value:         ${final_value:,.2f}")
print(f"   Total Return:        {total_return:+.2f}%")
print(f"   Annualized Return:   {annualized:.2f}%")
print(f"   Max Drawdown:        {max_dd:.2f}%")
print(f"   Sharpe Ratio:        {sharpe:.2f}")

print(f"\n📊 SPY Buy & Hold:")
print(f"   Total Return:        {spy_return:+.2f}%")
print(f"   Annualized Return:   {spy_annualized:.2f}%")
print(f"   Outperformance:      {total_return - spy_return:+.2f}%")

if total_return > spy_return:
    print(f"\n✅ Strategy OUTPERFORMED SPY by {total_return - spy_return:.2f}%")
else:
    print(f"\n⚠️ Strategy UNDERPERFORMED SPY by {abs(total_return - spy_return):.2f}%")

# Detailed breakdown by year
print("\n" + "="*80)
print("YEAR-BY-YEAR BREAKDOWN")
print("="*80)

pf_values = portfolio.value()
if isinstance(pf_values, pd.DataFrame):
    pf_values = pf_values.iloc[:, 0]

yearly_returns = []
for year in range(2020, 2026):
    year_data = pf_values[pf_values.index.year == year]
    if len(year_data) > 1:
        year_return = ((year_data.iloc[-1] / year_data.iloc[0]) - 1) * 100

        # SPY for same period
        spy_year = spy_test[spy_test.index.year == year]
        if len(spy_year) > 1:
            spy_year_return = ((spy_year.iloc[-1] / spy_year.iloc[0]) - 1) * 100
        else:
            spy_year_return = 0

        yearly_returns.append({
            'Year': year,
            'Strategy': f"{year_return:+.2f}%",
            'SPY': f"{spy_year_return:+.2f}%",
            'Outperformance': f"{year_return - spy_year_return:+.2f}%"
        })

if yearly_returns:
    df = pd.DataFrame(yearly_returns)
    print("\n" + df.to_string(index=False))

# Key events
print("\n" + "="*80)
print("KEY EVENTS IN TEST PERIOD")
print("="*80)

print("\n📉 COVID Crash (Feb-Mar 2020):")
covid_period = pf_values[(pf_values.index >= '2020-02-01') & (pf_values.index <= '2020-04-01')]
if len(covid_period) > 1:
    covid_dd = ((covid_period.min() / covid_period.iloc[0]) - 1) * 100
    print(f"   Strategy drawdown: {covid_dd:.2f}%")

    spy_covid = spy_test[(spy_test.index >= '2020-02-01') & (spy_test.index <= '2020-04-01')]
    if len(spy_covid) > 1:
        spy_covid_dd = ((spy_covid.min() / spy_covid.iloc[0]) - 1) * 100
        print(f"   SPY drawdown: {spy_covid_dd:.2f}%")

print("\n📈 2020 Recovery (Apr-Dec 2020):")
recovery_period = pf_values[(pf_values.index >= '2020-04-01') & (pf_values.index <= '2020-12-31')]
if len(recovery_period) > 1:
    recovery_return = ((recovery_period.iloc[-1] / recovery_period.iloc[0]) - 1) * 100
    print(f"   Strategy return: {recovery_return:+.2f}%")

print("\n🐻 2022 Bear Market:")
bear_period = pf_values[(pf_values.index >= '2022-01-01') & (pf_values.index <= '2022-12-31')]
if len(bear_period) > 1:
    bear_return = ((bear_period.iloc[-1] / bear_period.iloc[0]) - 1) * 100
    bear_dd = ((bear_period.min() / bear_period.iloc[0]) - 1) * 100
    print(f"   Strategy return: {bear_return:+.2f}%")
    print(f"   Max drawdown: {bear_dd:.2f}%")

print("\n📈 2023-2024 Recovery:")
recent_period = pf_values[(pf_values.index >= '2023-01-01') & (pf_values.index <= '2024-12-31')]
if len(recent_period) > 1:
    recent_return = ((recent_period.iloc[-1] / recent_period.iloc[0]) - 1) * 100
    print(f"   Strategy return: {recent_return:+.2f}%")

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

summary = pd.DataFrame([{
    'Test_Period': f"{start_test} to {end_test}",
    'Years': round(years, 2),
    'Initial_Capital': INITIAL_CAPITAL,
    'Final_Value': final_value,
    'Total_Return_Pct': total_return,
    'Annualized_Pct': annualized,
    'Max_Drawdown_Pct': max_dd,
    'Sharpe_Ratio': sharpe,
    'SPY_Return_Pct': spy_return,
    'SPY_Annualized_Pct': spy_annualized,
    'Outperformance_Pct': total_return - spy_return
}])

summary.to_csv(output_dir / 'backtest_2020_2025.csv', index=False)
print(f"\n📁 Results saved to: {output_dir}/backtest_2020_2025.csv")

print("\n" + "="*80)
print("✅ 2020-2025 BACKTEST COMPLETE")
print("="*80)
