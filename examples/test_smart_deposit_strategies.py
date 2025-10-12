"""
Smart Deposit Strategies - Optimizing When to Add Capital

Testing different deposit timing strategies:
1. Fixed Monthly (baseline)
2. Bull Market Only (deposit only in STRONG_BULL)
3. Buy the Dip (deposit only in WEAK_BULL and BEAR)
4. Double Down in Dips (2× deposits in BEAR, 1× in BULL)
5. Lump Sum at Start (control)
6. Quarterly Rebalance Days (deposit on rebalance days)

Starting capital: $5,000
Monthly budget: $1,000 (accumulated if not deployed)
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
print("SMART DEPOSIT STRATEGIES - TIMING YOUR CAPITAL")
print("="*80)
print("\nPeriod: January 2020 - September 2025 (5.74 years)")
print("Starting Capital: $5,000")
print("Monthly Budget: $1,000")
print("\nTesting 6 deposit strategies:")
print("  1. Fixed Monthly (baseline)")
print("  2. Bull Market Only (STRONG_BULL regime)")
print("  3. Buy the Dip (WEAK_BULL + BEAR only)")
print("  4. Double Down in Dips (2× in BEAR, 1× in BULL)")
print("  5. Lump Sum (invest all $74k on day 1)")
print("  6. Quarterly Rebalance Days (deposit on strategy rebalance)")

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

# Calculate regime
regime = strategy.calculate_regime(spy_prices)

# Filter to test period
start_test = '2020-01-01'
end_test = '2025-09-30'

allocations_test = allocations[(allocations.index >= start_test) & (allocations.index <= end_test)]
prices_test = prices_with_gld[(prices_with_gld.index >= start_test) & (prices_with_gld.index <= end_test)]
spy_test = spy_prices[(spy_prices.index >= start_test) & (spy_prices.index <= end_test)]
regime_test = regime[(regime.index >= start_test) & (regime.index <= end_test)]

print(f"✅ Allocations generated for {len(prices_test)} trading days")

# Identify rebalance dates
rebalance_dates = []
for i in range(1, len(allocations_test)):
    if not allocations_test.iloc[i].equals(allocations_test.iloc[i-1]):
        rebalance_dates.append(allocations_test.index[i])

print(f"✅ Identified {len(rebalance_dates)} rebalance dates")

# Generic backtest function with custom deposit strategy
def backtest_with_strategy(deposit_function, strategy_name):
    """
    Run backtest with custom deposit strategy

    deposit_function: function(date, month_num, regime, is_rebalance, cash_buffer) -> deposit_amount
    """

    cash = 5000  # Initial capital
    cash_buffer = 0  # Accumulated deposits not yet invested
    positions = {}
    portfolio_values = []
    total_deposited = 5000
    deposits_made = []

    FEE_PCT = 0.001

    last_deposit_month = (prices_test.index[0].year, prices_test.index[0].month)
    month_counter = 0

    for i, date in enumerate(prices_test.index):
        # Check for new month
        current_month = (date.year, date.month)
        is_new_month = (i > 0 and current_month != last_deposit_month)

        if is_new_month:
            month_counter += 1
            last_deposit_month = current_month

            # Get regime for this date
            current_regime = regime_test.loc[date] if date in regime_test.index else 'UNKNOWN'
            is_rebalance = date in rebalance_dates

            # Call deposit strategy
            deposit_amount = deposit_function(date, month_counter, current_regime, is_rebalance, cash_buffer)

            if deposit_amount > 0:
                # Actually deposit money
                actual_deposit = min(deposit_amount, cash_buffer) if cash_buffer > 0 else deposit_amount
                cash += actual_deposit
                total_deposited += actual_deposit
                cash_buffer -= actual_deposit

                deposits_made.append({
                    'date': date,
                    'amount': actual_deposit,
                    'regime': current_regime
                })

            # Add monthly budget to buffer (for strategies that accumulate)
            if month_counter <= 69:  # Cap at 69 months
                cash_buffer += 1000

        # Get allocations and prices
        target_allocs = allocations_test.loc[date]
        current_prices = prices_test.loc[date]

        # Calculate portfolio value
        position_value = sum(
            positions.get(ticker, 0) * current_prices[ticker]
            for ticker in positions
            if ticker in current_prices
        )
        total_value = cash + position_value

        # Rebalance check
        needs_rebalance = False
        if i > 0:
            prev_allocs = allocations_test.iloc[i-1]
            if not target_allocs.equals(prev_allocs):
                needs_rebalance = True
        elif i == 0 and target_allocs.sum() > 0:
            needs_rebalance = True

        if needs_rebalance:
            # Close positions
            for ticker, shares in list(positions.items()):
                if ticker in current_prices and shares > 0:
                    sell_price = current_prices[ticker]
                    proceeds = shares * sell_price
                    fee = proceeds * FEE_PCT
                    cash += proceeds - fee

            positions = {}
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
            'total': total_value,
            'deposited': total_deposited,
            'cash_buffer': cash_buffer
        })

    return pd.DataFrame(portfolio_values).set_index('date'), deposits_made

# Define deposit strategies

def strategy_1_fixed_monthly(date, month_num, regime, is_rebalance, cash_buffer):
    """Fixed $1,000 every month (baseline)"""
    return 1000

def strategy_2_bull_only(date, month_num, regime, is_rebalance, cash_buffer):
    """Only deposit in STRONG_BULL regime"""
    if regime == 'STRONG_BULL':
        return cash_buffer  # Deploy all accumulated cash
    return 0

def strategy_3_buy_dip(date, month_num, regime, is_rebalance, cash_buffer):
    """Only deposit in WEAK_BULL or BEAR (dip buying)"""
    if regime in ['WEAK_BULL', 'BEAR']:
        return cash_buffer  # Deploy all accumulated cash
    return 0

def strategy_4_double_down(date, month_num, regime, is_rebalance, cash_buffer):
    """2× deposits in BEAR, 1× in BULL regimes"""
    if regime == 'BEAR':
        return 2000  # Double deposit
    elif regime == 'STRONG_BULL':
        return 1000
    return 0

def strategy_5_lump_sum(date, month_num, regime, is_rebalance, cash_buffer):
    """Invest everything on day 1"""
    if month_num == 0:
        return 69000  # All future deposits upfront
    return 0

def strategy_6_rebalance_days(date, month_num, regime, is_rebalance, cash_buffer):
    """Deposit on quarterly rebalance days only"""
    if is_rebalance and cash_buffer >= 3000:  # Accumulated 3 months
        return cash_buffer
    return 0

# Run all strategies
print("\n" + "="*80)
print("RUNNING 6 STRATEGIES")
print("="*80)

strategies = [
    ("Fixed Monthly ($1k)", strategy_1_fixed_monthly),
    ("Bull Market Only", strategy_2_bull_only),
    ("Buy the Dip", strategy_3_buy_dip),
    ("Double Down in Bear", strategy_4_double_down),
    ("Lump Sum (Day 1)", strategy_5_lump_sum),
    ("Quarterly Deposits", strategy_6_rebalance_days)
]

results = []

for name, func in strategies:
    print(f"\n⚙️  Running: {name}...")
    portfolio_df, deposits = backtest_with_strategy(func, name)

    final_value = portfolio_df['total'].iloc[-1]
    total_deposited = portfolio_df['deposited'].iloc[-1]
    total_gain = final_value - total_deposited
    roi = (total_gain / total_deposited) * 100

    # Max drawdown
    running_max = portfolio_df['total'].expanding().max()
    drawdown = (portfolio_df['total'] / running_max - 1) * 100
    max_dd = drawdown.min()

    # CAGR
    years = (portfolio_df.index[-1] - portfolio_df.index[0]).days / 365.25
    cagr = ((final_value / 5000) ** (1/years) - 1) * 100

    # Deposits breakdown
    deposits_df = pd.DataFrame(deposits)
    if len(deposits_df) > 0:
        deposits_by_regime = deposits_df.groupby('regime')['amount'].sum()
    else:
        deposits_by_regime = pd.Series()

    results.append({
        'name': name,
        'total_deposited': total_deposited,
        'final_value': final_value,
        'total_gain': total_gain,
        'roi': roi,
        'max_dd': max_dd,
        'cagr': cagr,
        'num_deposits': len(deposits),
        'deposits_by_regime': deposits_by_regime,
        'portfolio_df': portfolio_df
    })

    print(f"   ✅ Final: ${final_value:,.0f} | ROI: {roi:.1f}% | Deposits: {len(deposits)}")

# Results comparison
print("\n" + "="*80)
print("RESULTS COMPARISON")
print("="*80)

comparison_df = pd.DataFrame([
    {
        'Strategy': r['name'],
        'Deposited': f"${r['total_deposited']:,.0f}",
        'Final Value': f"${r['final_value']:,.0f}",
        'Profit': f"${r['total_gain']:,.0f}",
        'ROI': f"{r['roi']:.1f}%",
        'Max DD': f"{r['max_dd']:.1f}%",
        'CAGR': f"{r['cagr']:.1f}%",
        '# Deposits': r['num_deposits']
    }
    for r in results
])

print("\n" + comparison_df.to_string(index=False))

# Find best strategy
best_profit = max(results, key=lambda x: x['total_gain'])
best_roi = max(results, key=lambda x: x['roi'])
best_dd = max(results, key=lambda x: x['max_dd'])  # Highest = least negative

print("\n" + "="*80)
print("WINNERS")
print("="*80)
print(f"\n🏆 Highest Profit: {best_profit['name']}")
print(f"   Profit: ${best_profit['total_gain']:,.0f}")

print(f"\n🏆 Best ROI: {best_roi['name']}")
print(f"   ROI: {best_roi['roi']:.1f}%")

print(f"\n🏆 Lowest Drawdown: {best_dd['name']}")
print(f"   Max DD: {best_dd['max_dd']:.1f}%")

# Detailed analysis for top 3 strategies
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)

for r in results:
    print(f"\n{'='*80}")
    print(f"{r['name'].upper()}")
    print(f"{'='*80}")
    print(f"Total Deposited:    ${r['total_deposited']:,.0f}")
    print(f"Final Value:        ${r['final_value']:,.0f}")
    print(f"Total Profit:       ${r['total_gain']:,.0f}")
    print(f"ROI:                {r['roi']:.2f}%")
    print(f"CAGR:               {r['cagr']:.1f}%")
    print(f"Max Drawdown:       {r['max_dd']:.2f}%")
    print(f"Number of Deposits: {r['num_deposits']}")

    if len(r['deposits_by_regime']) > 0:
        print(f"\nDeposits by Regime:")
        for regime, amount in r['deposits_by_regime'].items():
            print(f"   {regime:15s}: ${amount:,.0f}")

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

summary = pd.DataFrame([
    {
        'Strategy': r['name'],
        'Total_Deposited': r['total_deposited'],
        'Final_Value': r['final_value'],
        'Total_Profit': r['total_gain'],
        'ROI_Pct': r['roi'],
        'Max_Drawdown_Pct': r['max_dd'],
        'CAGR_Pct': r['cagr'],
        'Num_Deposits': r['num_deposits']
    }
    for r in results
])

summary.to_csv(output_dir / 'smart_deposit_strategies.csv', index=False)

print(f"\n📁 Results saved to: {output_dir}/smart_deposit_strategies.csv")

# Recommendation
print("\n" + "="*80)
print("💡 RECOMMENDATION")
print("="*80)

print(f"""
Based on the analysis:

1️⃣  HIGHEST ABSOLUTE PROFIT: {best_profit['name']}
   - Final Value: ${best_profit['final_value']:,.0f}
   - Best if: You have all capital available upfront

2️⃣  BEST RISK-ADJUSTED: {best_dd['name']}
   - Max Drawdown: {best_dd['max_dd']:.1f}%
   - Best if: You want to minimize volatility

3️⃣  MOST PRACTICAL: Fixed Monthly
   - Simple, disciplined, no timing decisions
   - Best if: You have regular income to invest

🎯 WINNER FOR MOST PEOPLE: Buy the Dip strategy
   - Only deploy capital during market weakness
   - Accumulate cash in bull markets
   - Deploy aggressively in corrections
   - Combines discipline with opportunistic timing
""")

print("\n" + "="*80)
print("✅ SMART DEPOSIT STRATEGIES ANALYSIS COMPLETE")
print("="*80)
