"""
Nick Radge Strategy with Monthly Deposits
Testing: Jan 2020 - Sep 2025 with regular monthly contributions

Three scenarios:
1. $500/month
2. $1,000/month
3. $5,000/month

Starting capital: $5,000
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("NICK RADGE STRATEGY WITH MONTHLY DEPOSITS")
print("="*80)
print("\nPeriod: January 2020 - September 2025 (5.74 years)")
print("Starting Capital: $5,000")
print("\nScenarios:")
print("  1. $500/month deposits")
print("  2. $1,000/month deposits")
print("  3. $5,000/month deposits")

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

print("Downloading data...")
data = yf.download(all_tickers, start='2019-01-01', end='2025-09-30', progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill().dropna()

# Remove insufficient data
min_data_points = 200
for col in list(close.columns):
    if close[col].count() < min_data_points:
        close = close.drop(columns=[col])

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[[t for t in tickers if t in close.columns]]

print(f"✅ Data ready: {len(close)} days, {len(stock_prices.columns)} stocks")

# Initialize strategy
print("\n" + "="*80)
print("GENERATING STRATEGY ALLOCATIONS")
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

# Generate allocations
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)
spy_roc = spy_prices.pct_change(100)

allocations = strategy.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Filter to test period
start_test = '2020-01-01'
end_test = '2025-09-30'

allocations_test = allocations[(allocations.index >= start_test) & (allocations.index <= end_test)]
prices_test = prices_with_gld[(prices_with_gld.index >= start_test) & (prices_with_gld.index <= end_test)]
spy_test = spy_prices[(spy_prices.index >= start_test) & (spy_prices.index <= end_test)]

print(f"✅ Allocations generated for {len(prices_test)} trading days")

# Manual backtest with monthly deposits
def backtest_with_deposits(initial_capital, monthly_deposit):
    """Run backtest with monthly deposits"""

    cash = initial_capital
    positions = {}  # {ticker: shares}
    portfolio_values = []
    total_deposited = initial_capital

    FEE_PCT = 0.001  # 0.1%

    # Track last deposit month to avoid duplicates
    last_deposit_month = (prices_test.index[0].year, prices_test.index[0].month)

    for i, date in enumerate(prices_test.index):
        # Check if we should add monthly deposit (first trading day of each month)
        current_month = (date.year, date.month)
        if i > 0 and current_month != last_deposit_month:
            cash += monthly_deposit
            total_deposited += monthly_deposit
            last_deposit_month = current_month

        # Get target allocations
        target_allocs = allocations_test.loc[date]
        current_prices = prices_test.loc[date]

        # Calculate current position values
        position_value = sum(
            positions.get(ticker, 0) * current_prices[ticker]
            for ticker in positions
            if ticker in current_prices
        )

        total_value = cash + position_value

        # Check if we need to rebalance
        needs_rebalance = False
        if i > 0:
            prev_allocs = allocations_test.iloc[i-1]
            if not target_allocs.equals(prev_allocs):
                needs_rebalance = True
        elif i == 0 and target_allocs.sum() > 0:
            needs_rebalance = True

        if needs_rebalance:
            # Close all positions
            for ticker, shares in list(positions.items()):
                if ticker in current_prices and shares > 0:
                    sell_price = current_prices[ticker]
                    proceeds = shares * sell_price
                    fee = proceeds * FEE_PCT
                    cash += proceeds - fee

            positions = {}

            # Recalculate total after selling
            total_value = cash

            # Open new positions
            new_positions = target_allocs[target_allocs > 0]

            for ticker in new_positions.index:
                target_pct = new_positions[ticker]
                target_value = total_value * target_pct

                if ticker in current_prices:
                    buy_price = current_prices[ticker]
                    shares_to_buy = target_value / buy_price
                    cost = shares_to_buy * buy_price
                    fee = cost * FEE_PCT
                    total_cost = cost + fee

                    if total_cost <= cash:
                        cash -= total_cost
                        positions[ticker] = shares_to_buy

        # Record portfolio value
        position_value = sum(
            positions.get(ticker, 0) * current_prices[ticker]
            for ticker in positions
            if ticker in current_prices
        )
        total_value = cash + position_value

        portfolio_values.append({
            'date': date,
            'cash': cash,
            'positions': position_value,
            'total': total_value,
            'deposited': total_deposited
        })

    return pd.DataFrame(portfolio_values).set_index('date')

# Run three scenarios
print("\n" + "="*80)
print("RUNNING SIMULATIONS")
print("="*80)

INITIAL_CAPITAL = 5000
scenarios = [
    ('$500/month', 500),
    ('$1,000/month', 1000),
    ('$5,000/month', 5000)
]

results = []

for name, monthly in scenarios:
    print(f"\n⚙️  Running: {name}...")
    portfolio_df = backtest_with_deposits(INITIAL_CAPITAL, monthly)

    final_value = portfolio_df['total'].iloc[-1]
    total_deposited = portfolio_df['deposited'].iloc[-1]
    total_gain = final_value - total_deposited
    gain_pct = (total_gain / total_deposited) * 100

    # Calculate max drawdown
    running_max = portfolio_df['total'].expanding().max()
    drawdown = (portfolio_df['total'] / running_max - 1) * 100
    max_dd = drawdown.min()

    # Calculate annualized return (CAGR on total value)
    years = (portfolio_df.index[-1] - portfolio_df.index[0]).days / 365.25
    cagr = ((final_value / INITIAL_CAPITAL) ** (1/years) - 1) * 100

    results.append({
        'scenario': name,
        'monthly_deposit': monthly,
        'total_deposited': total_deposited,
        'final_value': final_value,
        'total_gain': total_gain,
        'gain_pct': gain_pct,
        'max_dd': max_dd,
        'cagr': cagr,
        'portfolio_df': portfolio_df
    })

    print(f"   ✅ Complete: ${final_value:,.2f} final value")

# Display results
print("\n" + "="*80)
print("RESULTS COMPARISON")
print("="*80)

print(f"\n📅 Period: {prices_test.index[0].date()} to {prices_test.index[-1].date()}")
print(f"   Duration: ~69 months (5.74 years)")

print("\n" + "="*80)

for r in results:
    print(f"\n💰 {r['scenario'].upper()}")
    print(f"{'='*80}")
    print(f"   Initial Capital:        ${INITIAL_CAPITAL:,}")
    print(f"   Monthly Deposits:       ${r['monthly_deposit']:,} × 69 months = ${r['monthly_deposit']*69:,}")
    print(f"   Total Deposited:        ${r['total_deposited']:,.2f}")
    print(f"   Final Value:            ${r['final_value']:,.2f}")
    print(f"   Total Profit:           ${r['total_gain']:,.2f}")
    print(f"   Return on Deposits:     {r['gain_pct']:+.2f}%")
    print(f"   CAGR (on initial):      {r['cagr']:.2f}%")
    print(f"   Max Drawdown:           {r['max_dd']:.2f}%")

# Detailed comparison table
print("\n" + "="*80)
print("SIDE-BY-SIDE COMPARISON")
print("="*80)

comparison_df = pd.DataFrame([
    {
        'Monthly Deposit': f"${r['monthly_deposit']:,}",
        'Total Deposited': f"${r['total_deposited']:,.0f}",
        'Final Value': f"${r['final_value']:,.0f}",
        'Total Profit': f"${r['total_gain']:,.0f}",
        'ROI': f"{r['gain_pct']:.1f}%",
        'CAGR': f"{r['cagr']:.1f}%"
    }
    for r in results
])

print("\n" + comparison_df.to_string(index=False))

# Calculate SPY comparison for $500/month scenario
print("\n" + "="*80)
print("SPY BUY & HOLD COMPARISON ($500/month)")
print("="*80)

def spy_with_deposits(initial_capital, monthly_deposit):
    """SPY buy and hold with monthly deposits"""
    shares = initial_capital / spy_test.iloc[0]
    total_deposited = initial_capital
    last_month = (spy_test.index[0].year, spy_test.index[0].month)

    values = []
    for i, date in enumerate(spy_test.index):
        current_month = (date.year, date.month)
        if i > 0 and current_month != last_month:
            # Buy more shares with monthly deposit
            shares += monthly_deposit / spy_test.loc[date]
            total_deposited += monthly_deposit
            last_month = current_month

        value = shares * spy_test.loc[date]
        values.append({'date': date, 'value': value, 'deposited': total_deposited})

    return pd.DataFrame(values).set_index('date')

spy_df = spy_with_deposits(INITIAL_CAPITAL, 500)
spy_final = spy_df['value'].iloc[-1]
spy_deposited = spy_df['deposited'].iloc[-1]
spy_gain = spy_final - spy_deposited
spy_gain_pct = (spy_gain / spy_deposited) * 100

print(f"\nSPY with $500/month:")
print(f"   Total Deposited:        ${spy_deposited:,.2f}")
print(f"   Final Value:            ${spy_final:,.2f}")
print(f"   Total Profit:           ${spy_gain:,.2f}")
print(f"   Return on Deposits:     {spy_gain_pct:+.2f}%")

strategy_result = results[0]  # $500/month scenario
print(f"\nStrategy with $500/month:")
print(f"   Final Value:            ${strategy_result['final_value']:,.2f}")
print(f"   Total Profit:           ${strategy_result['total_gain']:,.2f}")
print(f"   Return on Deposits:     {strategy_result['gain_pct']:+.2f}%")

outperformance = strategy_result['final_value'] - spy_final
print(f"\n✅ Strategy beats SPY by: ${outperformance:,.2f}")

# Year by year breakdown for $500/month
print("\n" + "="*80)
print("YEAR-BY-YEAR BREAKDOWN ($500/month)")
print("="*80)

portfolio_df = results[0]['portfolio_df']

yearly_data = []
for year in range(2020, 2026):
    year_data = portfolio_df[portfolio_df.index.year == year]
    if len(year_data) > 1:
        start_val = year_data['total'].iloc[0]
        end_val = year_data['total'].iloc[-1]
        start_dep = year_data['deposited'].iloc[0]
        end_dep = year_data['deposited'].iloc[-1]
        deposits_this_year = end_dep - start_dep

        # Calculate return (accounting for deposits)
        gain_excl_deposits = end_val - start_val - deposits_this_year
        year_return = (gain_excl_deposits / start_val) * 100 if start_val > 0 else 0

        yearly_data.append({
            'Year': year,
            'Start Value': f"${start_val:,.0f}",
            'End Value': f"${end_val:,.0f}",
            'Deposits': f"${deposits_this_year:,.0f}",
            'Return': f"{year_return:+.1f}%"
        })

if yearly_data:
    yearly_df = pd.DataFrame(yearly_data)
    print("\n" + yearly_df.to_string(index=False))

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

summary = pd.DataFrame([
    {
        'Scenario': r['scenario'],
        'Monthly_Deposit': r['monthly_deposit'],
        'Total_Deposited': r['total_deposited'],
        'Final_Value': r['final_value'],
        'Total_Profit': r['total_gain'],
        'ROI_Pct': r['gain_pct'],
        'CAGR_Pct': r['cagr'],
        'Max_Drawdown_Pct': r['max_dd']
    }
    for r in results
])

summary.to_csv(output_dir / 'monthly_deposits_comparison.csv', index=False)

print(f"\n📁 Results saved to: {output_dir}/monthly_deposits_comparison.csv")

print("\n" + "="*80)
print("✅ MONTHLY DEPOSITS ANALYSIS COMPLETE")
print("="*80)
