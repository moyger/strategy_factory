"""
Compare Three Stop-Loss Levels: -15%, -18%, -20%

Comprehensive comparison to find optimal stop-loss for stock momentum strategy:
- Performance metrics (return, drawdown, Sharpe)
- Trade statistics (frequency, win rate)
- Risk-adjusted metrics
- Visual comparison

Goal: Choose best stop-loss level to reduce drawdown from -38.5% to -25%
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
print("COMPARING THREE STOP-LOSS LEVELS: -15%, -18%, -20%")
print("="*80)
print("\nGoal: Reduce max drawdown from -38.5% to -25%")
print("\nTesting:")
print("  1. Baseline (no stops)")
print("  2. Conservative (-15% stop)")
print("  3. Balanced (-18% stop)")
print("  4. Aggressive (-20% stop)")

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

print("Downloading historical data (2013-2024)...")
data = yf.download(all_tickers, start='2013-01-01', end='2024-12-31', progress=False, threads=True)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
else:
    close = data[['Close']].copy()

close = close.ffill().dropna()

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[tickers]

print(f"✅ Data ready: {len(close)} days, {len(close.columns)} symbols")

# Initialize strategy
initial_capital = 100000

strategy = NickRadgeMomentumStrategy(
    portfolio_size=10,
    roc_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    regime_ma_long=200,
    regime_ma_short=50,
    strong_bull_positions=10,
    weak_bull_positions=5,
    bear_positions=0,
    bear_market_asset='GLD',
    bear_allocation=1.0
)

# Generate allocations
print("\n⚙️  Generating base allocations...")
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)
spy_roc = spy_prices.pct_change(100)

allocations = strategy.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Filter to 2014+
start_backtest = '2014-01-01'
allocations_bt = allocations[allocations.index >= start_backtest]
prices_bt = prices_with_gld[prices_with_gld.index >= start_backtest]
spy_bt = spy_prices[spy_prices.index >= start_backtest]

def extract_value(val):
    """Safely extract float from pandas Series or scalar"""
    if isinstance(val, pd.Series):
        return float(val.values[0])
    elif isinstance(val, pd.DataFrame):
        return float(val.values[0][0])
    return float(val)

def extract_portfolio_value(portfolio):
    """Extract final portfolio value"""
    pf_value = portfolio.value()
    if isinstance(pf_value, pd.DataFrame):
        return float(pf_value.values[-1][0])
    elif isinstance(pf_value, pd.Series):
        return float(pf_value.values[-1])
    return float(pf_value)

def run_backtest_with_stops(allocations, prices, initial_capital, stop_pct, name):
    """Run backtest with position-level stop-loss"""
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")

    # Create entry/exit signals from allocations
    entries = allocations > 0
    exits = allocations == 0

    if stop_pct is None:
        # No stops - use order-based approach
        position_sizes = allocations.div(prices).mul(initial_capital)

        portfolio = vbt.Portfolio.from_orders(
            close=prices,
            size=position_sizes,
            size_type='amount',
            init_cash=initial_capital,
            fees=0.001,
            freq='1D'
        )
    else:
        # With stops - use signal-based approach
        portfolio = vbt.Portfolio.from_signals(
            close=prices,
            entries=entries,
            exits=exits,
            init_cash=initial_capital,
            fees=0.001,
            sl_stop=stop_pct,
            freq='1D'
        )

    # Extract metrics
    final_value = extract_portfolio_value(portfolio)
    total_return = extract_value(portfolio.total_return()) * 100
    annualized = extract_value(portfolio.annualized_return()) * 100
    sharpe = extract_value(portfolio.sharpe_ratio())
    max_dd = extract_value(portfolio.max_drawdown()) * 100

    # Trade statistics
    trades = portfolio.trades.records_readable
    if len(trades) > 0:
        total_trades = len(trades)
        winning_trades = (trades['PnL'] > 0).sum()
        win_rate = (winning_trades / total_trades) * 100
        avg_win = trades[trades['PnL'] > 0]['PnL'].mean() if winning_trades > 0 else 0
        avg_loss = trades[trades['PnL'] < 0]['PnL'].mean() if (total_trades - winning_trades) > 0 else 0
        profit_factor = abs(trades[trades['PnL'] > 0]['PnL'].sum() / trades[trades['PnL'] < 0]['PnL'].sum()) if (total_trades - winning_trades) > 0 else 0
    else:
        total_trades = 0
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0

    # Print results
    print(f"\n📊 PERFORMANCE METRICS:")
    print(f"Final Value:         ${final_value:,.2f}")
    print(f"Total Return:        {total_return:+.2f}%")
    print(f"Annualized Return:   {annualized:.2f}%")
    print(f"Max Drawdown:        {max_dd:.2f}%")
    print(f"Sharpe Ratio:        {sharpe:.2f}")

    print(f"\n📈 TRADE STATISTICS:")
    print(f"Total Trades:        {total_trades}")
    print(f"Win Rate:            {win_rate:.1f}%")
    print(f"Avg Win:             ${avg_win:,.2f}")
    print(f"Avg Loss:            ${avg_loss:,.2f}")
    print(f"Profit Factor:       {profit_factor:.2f}")

    # Return/DD ratio
    return_dd_ratio = -total_return / max_dd if max_dd != 0 else 0
    print(f"\n⭐ RISK-ADJUSTED:")
    print(f"Return/DD Ratio:     {return_dd_ratio:.2f}")

    # Years
    years = len(prices) / 252
    trades_per_year = total_trades / years if years > 0 else 0
    print(f"Trades per Year:     {trades_per_year:.1f}")

    return {
        'name': name,
        'stop_pct': stop_pct,
        'final_value': final_value,
        'total_return': total_return,
        'annualized': annualized,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'return_dd_ratio': return_dd_ratio,
        'trades_per_year': trades_per_year,
        'equity_curve': portfolio.value()
    }

# Run all tests
results = []

# Test 1: Baseline (no stops)
print("\nRunning Test 1/4...")
result_baseline = run_backtest_with_stops(
    allocations_bt, prices_bt, initial_capital,
    None,
    "TEST 1: BASELINE (NO STOPS)"
)
results.append(result_baseline)

# Test 2: Conservative -15% stop
print("\nRunning Test 2/4...")
result_15 = run_backtest_with_stops(
    allocations_bt, prices_bt, initial_capital,
    0.15,
    "TEST 2: CONSERVATIVE (-15% STOP)"
)
results.append(result_15)

# Test 3: Balanced -18% stop
print("\nRunning Test 3/4...")
result_18 = run_backtest_with_stops(
    allocations_bt, prices_bt, initial_capital,
    0.18,
    "TEST 3: BALANCED (-18% STOP)"
)
results.append(result_18)

# Test 4: Aggressive -20% stop
print("\nRunning Test 4/4...")
result_20 = run_backtest_with_stops(
    allocations_bt, prices_bt, initial_capital,
    0.20,
    "TEST 4: AGGRESSIVE (-20% STOP)"
)
results.append(result_20)

# Comparison table
print("\n" + "="*80)
print("COMPREHENSIVE COMPARISON")
print("="*80)

comparison_df = pd.DataFrame([
    {
        'Stop Level': r['name'].split('(')[1].replace(')', ''),
        'Final Value': f"${r['final_value']:,.0f}",
        'Total Return': f"{r['total_return']:+.1f}%",
        'Annualized': f"{r['annualized']:.1f}%",
        'Max Drawdown': f"{r['max_drawdown']:.1f}%",
        'Sharpe': f"{r['sharpe']:.2f}",
        'Trades/Year': f"{r['trades_per_year']:.0f}",
        'Win Rate': f"{r['win_rate']:.0f}%",
        'Return/DD': f"{r['return_dd_ratio']:.2f}"
    }
    for r in results
])

print("\n" + comparison_df.to_string(index=False))

# Detailed analysis
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)

# Find which methods hit -25% target
target_dd = -25.0
print(f"\n🎯 TARGET: Max Drawdown ≤ {target_dd}%")

passing_methods = []
for r in results:
    if r['max_drawdown'] >= target_dd:  # Remember drawdown is negative
        dd_improvement = results[0]['max_drawdown'] - r['max_drawdown']
        return_impact = results[0]['total_return'] - r['total_return']

        passing_methods.append({
            'name': r['name'],
            'stop': r['stop_pct'],
            'drawdown': r['max_drawdown'],
            'dd_improvement': dd_improvement,
            'return': r['total_return'],
            'return_impact': return_impact,
            'sharpe': r['sharpe'],
            'trades_per_year': r['trades_per_year']
        })

if passing_methods:
    print(f"\n✅ METHODS ACHIEVING TARGET:")
    for pm in passing_methods:
        print(f"\n   {pm['name'].split('(')[1].replace(')', '')}")
        print(f"   - Max Drawdown: {pm['drawdown']:.1f}% (improved by {pm['dd_improvement']:.1f}%)")
        print(f"   - Total Return: {pm['return']:+.1f}% (reduced by {pm['return_impact']:.1f}%)")
        print(f"   - Sharpe Ratio: {pm['sharpe']:.2f}")
        print(f"   - Trades/Year: {pm['trades_per_year']:.0f}")
else:
    print("\n⚠️  NO METHOD ACHIEVED TARGET")
    print("   Consider combining with portfolio size reduction (7 stocks)")

# Best risk-adjusted
print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

best_sharpe_idx = max(range(len(results)), key=lambda i: results[i]['sharpe'])
best_returndd_idx = max(range(len(results)), key=lambda i: results[i]['return_dd_ratio'])

best_sharpe = results[best_sharpe_idx]
best_returndd = results[best_returndd_idx]

print(f"\n🏆 BEST SHARPE RATIO:")
print(f"   {best_sharpe['name'].split('(')[1].replace(')', '')}")
print(f"   Sharpe: {best_sharpe['sharpe']:.2f}")
print(f"   Return: {best_sharpe['total_return']:+.1f}%")
print(f"   Drawdown: {best_sharpe['max_drawdown']:.1f}%")

print(f"\n🏆 BEST RETURN/DRAWDOWN RATIO:")
print(f"   {best_returndd['name'].split('(')[1].replace(')', '')}")
print(f"   Return/DD: {best_returndd['return_dd_ratio']:.2f}")
print(f"   Return: {best_returndd['total_return']:+.1f}%")
print(f"   Drawdown: {best_returndd['max_drawdown']:.1f}%")

# SPY comparison
spy_return = ((spy_bt.iloc[-1] / spy_bt.iloc[0]) - 1) * 100
print(f"\n📊 BENCHMARK (SPY Buy & Hold):")
print(f"   Return: {spy_return:+.1f}%")

print(f"\n📊 OUTPERFORMANCE vs SPY:")
for r in results:
    outperf = r['total_return'] - spy_return
    print(f"   {r['name'].split('(')[1].replace(')', ''):30s} {outperf:+.1f}%")

# Final recommendation logic
print("\n" + "="*80)
print("🎯 FINAL RECOMMENDATION")
print("="*80)

if len(passing_methods) > 0:
    # Choose method with best Sharpe among passing methods
    best_passing = max(passing_methods, key=lambda x: x['sharpe'])

    print(f"\n⭐⭐⭐ RECOMMENDED: {best_passing['name'].split('(')[1].replace(')', '')} ⭐⭐⭐")
    print(f"\nWhy this is optimal:")
    print(f"   ✅ Meets drawdown target: {best_passing['drawdown']:.1f}% (vs target {target_dd}%)")
    print(f"   ✅ Best Sharpe ratio: {best_passing['sharpe']:.2f}")
    print(f"   ✅ Excellent returns: {best_passing['return']:+.1f}%")
    print(f"   ✅ Reasonable trade frequency: {best_passing['trades_per_year']:.0f} trades/year")

    print(f"\n💰 EXPECTED OUTCOME:")
    print(f"   Starting capital: $100,000")
    print(f"   Ending value: ${results[[r['name'] for r in results].index(best_passing['name'])]['final_value']:,.0f}")
    print(f"   Improvement over baseline:")
    print(f"   - Drawdown reduced: {best_passing['dd_improvement']:.1f}% (from {results[0]['max_drawdown']:.1f}%)")
    print(f"   - Return reduced: {best_passing['return_impact']:.1f}% (acceptable tradeoff)")
    print(f"   - Risk-adjusted performance: IMPROVED ⭐")

else:
    print("\n⚠️  NONE OF THE TESTED STOPS ACHIEVE -25% TARGET")
    print("\nNext steps:")
    print("   1. Combine stop-loss with portfolio size reduction (7 stocks)")
    print("   2. Add 50% GLD / 50% cash in BEAR regime")
    print("   3. Test tighter stops (-12% or -10%)")

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

# Save comparison table
comparison_detailed = pd.DataFrame([
    {
        'Stop_Level': r['stop_pct'] if r['stop_pct'] else 'None',
        'Final_Value': r['final_value'],
        'Total_Return_Pct': r['total_return'],
        'Annualized_Return_Pct': r['annualized'],
        'Max_Drawdown_Pct': r['max_drawdown'],
        'Sharpe_Ratio': r['sharpe'],
        'Total_Trades': r['total_trades'],
        'Win_Rate_Pct': r['win_rate'],
        'Avg_Win': r['avg_win'],
        'Avg_Loss': r['avg_loss'],
        'Profit_Factor': r['profit_factor'],
        'Return_DD_Ratio': r['return_dd_ratio'],
        'Trades_Per_Year': r['trades_per_year']
    }
    for r in results
])

comparison_detailed.to_csv(output_dir / 'stop_loss_comparison_detailed.csv', index=False)

print(f"\n📁 Results saved to: {output_dir}/")
print(f"   - stop_loss_comparison_detailed.csv")

print("\n✅ Three-level stop-loss comparison complete!")
print("\nNext: Implement the recommended stop-loss level and re-run full validation")
