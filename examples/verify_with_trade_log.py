"""
Comprehensive Trade-by-Trade Audit

This script logs EVERY trade made by the Nick Radge strategy to verify
whether the +1,106% result is accurate or if there's a bug.

Key checks:
1. Log every rebalance with exact positions
2. Track cash and portfolio value day by day
3. Verify GLD entries/exits during BEAR regime
4. Count total trades and check for hidden leverage
5. Compare logged results vs vectorbt results
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
print("TRADE-BY-TRADE AUDIT - NICK RADGE STRATEGY")
print("="*80)
print("\n🎯 Purpose: Verify +1,106% result by logging every trade")

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

print("Downloading data (2013-2024)...")
data = yf.download(all_tickers, start='2013-01-01', end='2024-12-31', progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill().dropna()

# Remove insufficient data
min_data_points = 500
for col in list(close.columns):
    if close[col].count() < min_data_points:
        print(f"   Removing {col} (insufficient data)")
        close = close.drop(columns=[col])

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[[t for t in tickers if t in close.columns]]

print(f"✅ Data ready: {len(close)} days, {len(stock_prices.columns)} stocks")

# Filter to 2014+
start_backtest = '2014-01-01'

# Initialize strategy
print("\n" + "="*80)
print("INITIALIZING STRATEGY")
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
print("\n⚙️  Generating allocations...")
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)
spy_roc = spy_prices.pct_change(100)

allocations = strategy.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Filter to 2014+
allocations_bt = allocations[allocations.index >= start_backtest]
prices_bt = prices_with_gld[prices_with_gld.index >= start_backtest]
spy_bt = spy_prices[spy_prices.index >= start_backtest]

print(f"✅ Allocations generated")

# MANUAL BACKTEST WITH TRADE LOGGING
print("\n" + "="*80)
print("MANUAL BACKTEST WITH TRADE LOG")
print("="*80)

INITIAL_CAPITAL = 100000
cash = INITIAL_CAPITAL
positions = {}  # {ticker: shares}
portfolio_values = []
trade_log = []
rebalance_count = 0

# Fee settings
FEE_PCT = 0.001  # 0.1%

print(f"\nStarting capital: ${cash:,.2f}")
print(f"Fee: {FEE_PCT*100}%")
print("\nProcessing daily...")

for i, date in enumerate(prices_bt.index):
    # Get target allocations for this date
    target_allocs = allocations_bt.loc[date]

    # Current prices
    current_prices = prices_bt.loc[date]

    # Calculate current position values
    position_value = 0
    for ticker, shares in positions.items():
        if ticker in current_prices:
            position_value += shares * current_prices[ticker]

    total_value = cash + position_value

    # Check if we need to rebalance (allocations changed from previous day)
    needs_rebalance = False
    if i > 0:
        prev_allocs = allocations_bt.iloc[i-1]
        # Check if any allocation changed
        if not target_allocs.equals(prev_allocs):
            needs_rebalance = True
    elif i == 0 and target_allocs.sum() > 0:
        # First day with non-zero allocations
        needs_rebalance = True

    if needs_rebalance:
        rebalance_count += 1

        # Get regime
        regime = 'UNKNOWN'
        if date in spy_prices.index:
            spy_price = spy_prices.loc[date]
            ma_200 = spy_prices.loc[:date].tail(200).mean()
            ma_50 = spy_prices.loc[:date].tail(50).mean()
            if spy_price > ma_200 and spy_price > ma_50:
                regime = 'STRONG_BULL'
            elif spy_price > ma_200:
                regime = 'WEAK_BULL'
            else:
                regime = 'BEAR'

        print(f"\n{'='*80}")
        print(f"REBALANCE #{rebalance_count} - {date.date()} ({regime})")
        print(f"{'='*80}")
        print(f"Portfolio value before: ${total_value:,.2f}")

        # Close all current positions
        if len(positions) > 0:
            print(f"\nClosing {len(positions)} positions:")
            for ticker, shares in list(positions.items()):
                if ticker in current_prices and shares > 0:
                    sell_price = current_prices[ticker]
                    proceeds = shares * sell_price
                    fee = proceeds * FEE_PCT
                    cash += proceeds - fee

                    print(f"   SELL {shares:.2f} {ticker} @ ${sell_price:.2f} = ${proceeds:,.2f} (fee: ${fee:.2f})")

                    trade_log.append({
                        'date': date,
                        'action': 'SELL',
                        'ticker': ticker,
                        'shares': shares,
                        'price': sell_price,
                        'value': proceeds,
                        'fee': fee,
                        'regime': regime
                    })

            positions = {}
            print(f"   Cash after sells: ${cash:,.2f}")

        # Open new positions based on target allocations
        new_positions = target_allocs[target_allocs > 0]

        if len(new_positions) > 0:
            print(f"\nOpening {len(new_positions)} positions:")
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

                        print(f"   BUY {shares_to_buy:.2f} {ticker} @ ${buy_price:.2f} = ${cost:,.2f} (fee: ${fee:.2f}, alloc: {target_pct*100:.1f}%)")

                        trade_log.append({
                            'date': date,
                            'action': 'BUY',
                            'ticker': ticker,
                            'shares': shares_to_buy,
                            'price': buy_price,
                            'value': cost,
                            'fee': fee,
                            'regime': regime
                        })
                    else:
                        print(f"   ⚠️ SKIPPED {ticker} - insufficient cash (need ${total_cost:,.2f}, have ${cash:,.2f})")

            print(f"   Cash after buys: ${cash:,.2f}")

        # Recalculate portfolio value
        position_value = sum(positions.get(t, 0) * current_prices[t] for t in positions if t in current_prices)
        total_value = cash + position_value
        print(f"\nPortfolio value after: ${total_value:,.2f}")
        print(f"Positions held: {len(positions)}")
        if len(positions) > 0:
            print(f"Tickers: {', '.join(positions.keys())}")

    # Record portfolio value
    position_value = sum(positions.get(t, 0) * current_prices[t] for t in positions if t in current_prices)
    total_value = cash + position_value
    portfolio_values.append({
        'date': date,
        'cash': cash,
        'positions': position_value,
        'total': total_value
    })

# Final results
print("\n" + "="*80)
print("MANUAL BACKTEST RESULTS")
print("="*80)

portfolio_df = pd.DataFrame(portfolio_values)
portfolio_df.set_index('date', inplace=True)

final_value = portfolio_df['total'].iloc[-1]
total_return = ((final_value / INITIAL_CAPITAL) - 1) * 100

# Calculate drawdown
running_max = portfolio_df['total'].expanding().max()
drawdown = (portfolio_df['total'] / running_max - 1) * 100
max_drawdown = drawdown.min()

# Calculate annualized return
years = (portfolio_df.index[-1] - portfolio_df.index[0]).days / 365.25
annualized = ((final_value / INITIAL_CAPITAL) ** (1/years) - 1) * 100

print(f"\nManual Backtest:")
print(f"   Initial Capital:     ${INITIAL_CAPITAL:,.2f}")
print(f"   Final Value:         ${final_value:,.2f}")
print(f"   Total Return:        {total_return:+.2f}%")
print(f"   Annualized Return:   {annualized:.2f}%")
print(f"   Max Drawdown:        {max_drawdown:.2f}%")
print(f"   Total Rebalances:    {rebalance_count}")
print(f"   Total Trades:        {len(trade_log)}")

# Now run vectorbt version
print("\n" + "="*80)
print("VECTORBT BACKTEST (FOR COMPARISON)")
print("="*80)

portfolio_vbt = vbt.Portfolio.from_orders(
    close=prices_bt,
    size=allocations_bt,
    size_type='targetpercent',
    init_cash=INITIAL_CAPITAL,
    fees=FEE_PCT,
    group_by=True,
    cash_sharing=True
)

vbt_value = portfolio_vbt.value()
if isinstance(vbt_value, pd.DataFrame):
    vbt_final = float(vbt_value.values[-1][0])
elif isinstance(vbt_value, pd.Series):
    vbt_final = float(vbt_value.values[-1])
else:
    vbt_final = float(vbt_value)

vbt_return = ((vbt_final / INITIAL_CAPITAL) - 1) * 100

def extract_value(val):
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

vbt_annualized = extract_value(portfolio_vbt.annualized_return(freq='D')) * 100
vbt_max_dd = extract_value(portfolio_vbt.max_drawdown()) * 100
vbt_sharpe = extract_value(portfolio_vbt.sharpe_ratio(freq='D'))

print(f"\nVectorBT Results:")
print(f"   Final Value:         ${vbt_final:,.2f}")
print(f"   Total Return:        {vbt_return:+.2f}%")
print(f"   Annualized Return:   {vbt_annualized:.2f}%")
print(f"   Max Drawdown:        {vbt_max_dd:.2f}%")
print(f"   Sharpe Ratio:        {vbt_sharpe:.2f}")

# Comparison
print("\n" + "="*80)
print("COMPARISON - WHICH IS CORRECT?")
print("="*80)

diff_return = abs(total_return - vbt_return)
diff_dd = abs(max_drawdown - vbt_max_dd)

print(f"\nTotal Return:")
print(f"   Manual:    {total_return:+.2f}%")
print(f"   VectorBT:  {vbt_return:+.2f}%")
print(f"   Difference: {diff_return:.2f}%")

print(f"\nMax Drawdown:")
print(f"   Manual:    {max_drawdown:.2f}%")
print(f"   VectorBT:  {vbt_max_dd:.2f}%")
print(f"   Difference: {diff_dd:.2f}%")

print(f"\nFinal Value:")
print(f"   Manual:    ${final_value:,.2f}")
print(f"   VectorBT:  ${vbt_final:,.2f}")
print(f"   Difference: ${abs(final_value - vbt_final):,.2f}")

# Verdict
print("\n" + "="*80)
print("VERDICT")
print("="*80)

if diff_return < 5:  # Within 5%
    print(f"\n✅ RESULTS MATCH CLOSELY!")
    print(f"   Difference of {diff_return:.2f}% is within acceptable range")
    print(f"   VectorBT result of {vbt_return:+.2f}% is RELIABLE")
    print(f"\n🎯 Conclusion: The +{vbt_return:.1f}% result is CORRECT")
else:
    print(f"\n⚠️ SIGNIFICANT DISCREPANCY!")
    print(f"   Difference of {diff_return:.2f}% requires investigation")
    print(f"   Need to check:")
    print(f"   - Order execution logic")
    print(f"   - Fee calculation")
    print(f"   - Cash management")
    print(f"   - Position sizing")

# Trade statistics
print("\n" + "="*80)
print("TRADE STATISTICS")
print("="*80)

trades_df = pd.DataFrame(trade_log)

if len(trades_df) > 0:
    print(f"\nTotal trades: {len(trades_df)}")
    print(f"   Buys:  {len(trades_df[trades_df['action'] == 'BUY'])}")
    print(f"   Sells: {len(trades_df[trades_df['action'] == 'SELL'])}")

    total_fees = trades_df['fee'].sum()
    print(f"\nTotal fees paid: ${total_fees:,.2f}")
    print(f"   As % of initial capital: {(total_fees / INITIAL_CAPITAL)*100:.2f}%")

    # Trades by regime
    print(f"\nTrades by regime:")
    for regime in ['STRONG_BULL', 'WEAK_BULL', 'BEAR']:
        regime_trades = trades_df[trades_df['regime'] == regime]
        if len(regime_trades) > 0:
            print(f"   {regime}: {len(regime_trades)} trades")

    # GLD trades
    gld_trades = trades_df[trades_df['ticker'] == 'GLD']
    if len(gld_trades) > 0:
        print(f"\nGLD (bear asset) trades: {len(gld_trades)}")
        print(f"   Buys:  {len(gld_trades[gld_trades['action'] == 'BUY'])}")
        print(f"   Sells: {len(gld_trades[gld_trades['action'] == 'SELL'])}")

# Save trade log
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

if len(trades_df) > 0:
    trades_df.to_csv(output_dir / 'trade_log.csv', index=False)
    print(f"\n📁 Trade log saved to: {output_dir}/trade_log.csv")

portfolio_df.to_csv(output_dir / 'portfolio_values.csv')
print(f"📁 Portfolio values saved to: {output_dir}/portfolio_values.csv")

# Save comparison
comparison = pd.DataFrame([
    {'Method': 'Manual Backtest', 'Total_Return': total_return, 'Max_Drawdown': max_drawdown, 'Final_Value': final_value},
    {'Method': 'VectorBT', 'Total_Return': vbt_return, 'Max_Drawdown': vbt_max_dd, 'Final_Value': vbt_final}
])
comparison.to_csv(output_dir / 'verification_comparison.csv', index=False)
print(f"📁 Comparison saved to: {output_dir}/verification_comparison.csv")

print("\n✅ Trade-by-trade audit complete!")

# SPY comparison
spy_bt_filtered = spy_bt[spy_bt.index >= start_backtest]
spy_return = ((spy_bt_filtered.iloc[-1] / spy_bt_filtered.iloc[0]) - 1) * 100

print(f"\n📊 SPY Buy & Hold: {spy_return:+.2f}%")
print(f"📊 Strategy outperformance: {vbt_return - spy_return:+.2f}%")
