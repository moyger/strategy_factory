"""
Full Nick Radge Strategy + Dynamic Replacement Stops

Integrating dynamic replacement stops into the FULL strategy that achieved +1,103%

This uses:
- ✅ Full momentum weighting
- ✅ Relative strength filters
- ✅ Proper GLD allocation in BEAR regime
- ✅ Regime recovery logic
- ✅ PLUS: Dynamic replacement when stops are hit

Goal: Preserve +1,103% returns while reducing -38.5% drawdown to -25-30%
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
print("FULL STRATEGY + DYNAMIC REPLACEMENT STOPS")
print("="*80)
print("\n🎯 Goal: Preserve +1,103% returns, reduce -38.5% drawdown")
print("\nIntegrating dynamic replacement into the FULL Nick Radge strategy")
print("\nTesting:")
print("  1. Baseline (full strategy, no stops) - Known: +1,103%")
print("  2. Full strategy + Dynamic -15% stops")
print("  3. Full strategy + Dynamic -18% stops")
print("  4. Full strategy + Dynamic -20% stops")

# Download data
print("\n" + "="*80)
print("STEP 1: DOWNLOADING DATA")
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

# Remove tickers with insufficient data
min_data_points = 500
for col in close.columns:
    if close[col].count() < min_data_points:
        print(f"   Removing {col} (insufficient data)")
        close = close.drop(columns=[col])
        if col in tickers:
            tickers.remove(col)

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[[t for t in tickers if t in close.columns]]

print(f"✅ Data ready: {len(close)} days, {len(stock_prices.columns)} stocks")

# Initialize strategy
initial_capital = 100000
start_backtest = '2014-01-01'

print("\n" + "="*80)
print("STEP 2: BASELINE - FULL STRATEGY (NO STOPS)")
print("="*80)

# Use the FULL Nick Radge strategy
strategy_baseline = NickRadgeMomentumStrategy(
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

# Generate allocations
print("Generating allocations...")
prices_with_gld = pd.concat([stock_prices, gld_prices.to_frame()], axis=1)
spy_roc = spy_prices.pct_change(100)

allocations_baseline = strategy_baseline.generate_allocations(
    prices=prices_with_gld,
    spy_prices=spy_prices,
    benchmark_roc=spy_roc,
    enable_regime_recovery=True
)

# Filter to 2014+
allocations_bt = allocations_baseline[allocations_baseline.index >= start_backtest]
prices_bt = prices_with_gld[prices_with_gld.index >= start_backtest]
spy_bt = spy_prices[spy_prices.index >= start_backtest]

print(f"✅ Allocations generated for {len(allocations_bt)} days")

# Now implement dynamic replacement MANUALLY on top of these allocations
def backtest_with_dynamic_stops(allocations, prices, spy_prices, initial_capital, stop_pct, name):
    """
    Take the strategy allocations and apply dynamic replacement stops

    Key: When a position hits stop, replace with next best stock from current momentum rankings
    """
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")

    cash = initial_capital
    positions = {}  # {symbol: {'shares': X, 'entry_price': Y, 'entry_date': Z, 'target_alloc': W}}
    equity_curve = []
    trades = []
    stop_count = 0
    replacement_count = 0

    # Calculate regime
    spy_ma_200 = spy_prices.rolling(200).mean()
    spy_ma_50 = spy_prices.rolling(50).mean()
    regime = pd.Series('UNKNOWN', index=spy_prices.index)
    regime[(spy_prices > spy_ma_200) & (spy_prices > spy_ma_50)] = 'STRONG_BULL'
    regime[(spy_prices > spy_ma_200) & (spy_prices <= spy_ma_50)] = 'WEAK_BULL'
    regime[spy_prices <= spy_ma_200] = 'BEAR'

    # Calculate momentum scores for replacement logic
    stock_cols = [col for col in prices.columns if col not in ['GLD', 'SPY']]
    stock_prices_only = prices[stock_cols]
    momentum_scores = stock_prices_only.pct_change(100)

    # Track rebalance dates
    rebalance_dates = pd.date_range(start=prices.index[0], end=prices.index[-1], freq='QS')
    rebalance_dates = [d for d in rebalance_dates if d in prices.index]

    for date in prices.index:
        current_prices = prices.loc[date]
        current_regime = regime.loc[date] if date in regime.index else 'UNKNOWN'
        current_allocations = allocations.loc[date] if date in allocations.index else pd.Series(0, index=prices.columns)

        # BEAR REGIME: Follow strategy's GLD allocation
        if current_regime == 'BEAR' or (date in allocations.index and allocations.loc[date, 'GLD'] > 0.5):
            # Close all stock positions
            if len(positions) > 0:
                for symbol, pos in list(positions.items()):
                    if symbol != 'GLD' and symbol in current_prices.index:
                        exit_price = current_prices[symbol]
                        exit_value = pos['shares'] * exit_price
                        pnl = exit_value - (pos['shares'] * pos['entry_price'])

                        cash += exit_value * 0.999

                        trades.append({
                            'exit_date': date,
                            'symbol': symbol,
                            'pnl': pnl,
                            'reason': 'BEAR_REGIME'
                        })

                        del positions[symbol]

            # Hold GLD (simplified - track as part of equity)
            total_equity = cash
            if 'GLD' in current_prices.index:
                gld_alloc = current_allocations.get('GLD', 1.0)
                gld_value = total_equity * gld_alloc
                total_equity = cash + gld_value

            equity_curve.append(total_equity)
            continue

        # DAILY STOP-LOSS CHECKS (only if stop_pct is set)
        if stop_pct:
            stopped_symbols = []
            for symbol, pos in list(positions.items()):
                if symbol == 'GLD' or symbol not in current_prices.index:
                    continue

                entry_price = pos['entry_price']
                current_price = current_prices[symbol]

                if pd.isna(current_price):
                    continue

                loss_pct = (current_price - entry_price) / entry_price

                # STOP TRIGGERED
                if loss_pct <= -stop_pct:
                    exit_value = pos['shares'] * current_price
                    pnl = exit_value - (pos['shares'] * entry_price)

                    cash += exit_value * 0.999

                    trades.append({
                        'exit_date': date,
                        'symbol': symbol,
                        'pnl': pnl,
                        'reason': 'STOP_LOSS'
                    })

                    stopped_symbols.append((symbol, pos['target_alloc']))
                    stop_count += 1
                    del positions[symbol]

            # DYNAMIC REPLACEMENT
            if stopped_symbols and date in momentum_scores.index:
                current_momentum = momentum_scores.loc[date].dropna().sort_values(ascending=False)

                # Filter out current positions
                held_symbols = [s for s in positions.keys() if s != 'GLD']
                available = current_momentum[~current_momentum.index.isin(held_symbols)]

                # Replace each stopped position
                for stopped_symbol, target_alloc in stopped_symbols:
                    if len(available) > 0 and cash > 0:
                        replacement_symbol = available.index[0]
                        replacement_price = current_prices[replacement_symbol]

                        if not pd.isna(replacement_price) and replacement_price > 0:
                            # Use the stopped position's target allocation
                            total_equity = cash + sum(
                                p['shares'] * current_prices[s]
                                for s, p in positions.items()
                                if s in current_prices.index and not pd.isna(current_prices[s])
                            )

                            target_value = total_equity * target_alloc
                            shares = target_value / replacement_price
                            cost = shares * replacement_price * 1.001

                            if cost <= cash:
                                positions[replacement_symbol] = {
                                    'shares': shares,
                                    'entry_price': replacement_price,
                                    'entry_date': date,
                                    'target_alloc': target_alloc
                                }
                                cash -= cost
                                replacement_count += 1

                                # Remove from available
                                available = available.drop(replacement_symbol)

        # QUARTERLY REBALANCING (follow strategy allocations exactly)
        if date in rebalance_dates:
            # Close all positions
            for symbol, pos in list(positions.items()):
                if symbol in current_prices.index and not pd.isna(current_prices[symbol]):
                    exit_price = current_prices[symbol]
                    exit_value = pos['shares'] * exit_price
                    pnl = exit_value - (pos['shares'] * pos['entry_price'])

                    cash += exit_value * 0.999

                    trades.append({
                        'exit_date': date,
                        'symbol': symbol,
                        'pnl': pnl,
                        'reason': 'QUARTERLY_REBALANCE'
                    })

            positions = {}

            # Enter positions based on strategy allocations
            if date in allocations.index:
                target_allocations = allocations.loc[date]

                # Calculate total equity
                total_equity = cash

                for symbol in target_allocations.index:
                    alloc = target_allocations[symbol]

                    if alloc > 0.01 and symbol != 'GLD':  # >1% allocation, not GLD
                        if symbol in current_prices.index and not pd.isna(current_prices[symbol]):
                            entry_price = current_prices[symbol]
                            target_value = total_equity * alloc

                            if entry_price > 0 and target_value > 0:
                                shares = target_value / entry_price
                                cost = shares * entry_price * 1.001

                                if cost <= cash:
                                    positions[symbol] = {
                                        'shares': shares,
                                        'entry_price': entry_price,
                                        'entry_date': date,
                                        'target_alloc': alloc
                                    }
                                    cash -= cost

        # Calculate equity
        position_value = sum(
            pos['shares'] * current_prices[symbol]
            for symbol, pos in positions.items()
            if symbol in current_prices.index and not pd.isna(current_prices[symbol])
        )
        total_equity = cash + position_value
        equity_curve.append(total_equity)

    # Calculate metrics
    equity_series = pd.Series(equity_curve, index=prices.index)

    total_return = ((equity_series.iloc[-1] / initial_capital) - 1) * 100
    years = len(equity_series) / 252
    annualized = ((equity_series.iloc[-1] / initial_capital) ** (1/years) - 1) * 100

    # Drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax * 100
    max_dd = drawdown.min()

    # Sharpe
    daily_returns = equity_series.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

    # Trade stats
    trades_df = pd.DataFrame(trades)
    win_rate = 0
    if len(trades_df) > 0:
        trades_with_pnl = trades_df[trades_df['pnl'].notna()]
        if len(trades_with_pnl) > 0:
            winning = (trades_with_pnl['pnl'] > 0).sum()
            win_rate = (winning / len(trades_with_pnl)) * 100

    print(f"\n📊 PERFORMANCE:")
    print(f"Final Value:         ${equity_series.iloc[-1]:,.2f}")
    print(f"Total Return:        {total_return:+.2f}%")
    print(f"Annualized Return:   {annualized:.2f}%")
    print(f"Max Drawdown:        {max_dd:.2f}%")
    print(f"Sharpe Ratio:        {sharpe:.2f}")
    print(f"Total Trades:        {len(trades_df)}")
    print(f"Win Rate:            {win_rate:.1f}%")

    if stop_pct:
        print(f"\n🔄 DYNAMIC REPLACEMENT:")
        print(f"Stops Triggered:     {stop_count}")
        print(f"Replacements Made:   {replacement_count}")

    return {
        'name': name,
        'equity_series': equity_series,
        'final_value': equity_series.iloc[-1],
        'total_return': total_return,
        'annualized': annualized,
        'max_drawdown': max_dd,
        'sharpe': sharpe,
        'total_trades': len(trades_df),
        'win_rate': win_rate,
        'stop_count': stop_count if stop_pct else 0,
        'replacement_count': replacement_count if stop_pct else 0
    }

# Run tests
results = []

# Test 1: Baseline
result_baseline = backtest_with_dynamic_stops(
    allocations_bt, prices_bt, spy_bt, initial_capital, None,
    "BASELINE - Full Strategy (No Stops)"
)
results.append(result_baseline)

# Test 2: -15% dynamic stops
print("\n" + "="*80)
print("STEP 3: FULL STRATEGY + DYNAMIC -15% STOPS")
print("="*80)

result_15 = backtest_with_dynamic_stops(
    allocations_bt, prices_bt, spy_bt, initial_capital, 0.15,
    "Full Strategy + Dynamic -15% Stops"
)
results.append(result_15)

# Test 3: -18% dynamic stops
print("\n" + "="*80)
print("STEP 4: FULL STRATEGY + DYNAMIC -18% STOPS")
print("="*80)

result_18 = backtest_with_dynamic_stops(
    allocations_bt, prices_bt, spy_bt, initial_capital, 0.18,
    "Full Strategy + Dynamic -18% Stops"
)
results.append(result_18)

# Test 4: -20% dynamic stops
print("\n" + "="*80)
print("STEP 5: FULL STRATEGY + DYNAMIC -20% STOPS")
print("="*80)

result_20 = backtest_with_dynamic_stops(
    allocations_bt, prices_bt, spy_bt, initial_capital, 0.20,
    "Full Strategy + Dynamic -20% Stops"
)
results.append(result_20)

# Final comparison
print("\n" + "="*80)
print("COMPREHENSIVE COMPARISON")
print("="*80)

comparison = pd.DataFrame([
    {
        'Method': r['name'],
        'Final Value': f"${r['final_value']:,.0f}",
        'Total Return': f"{r['total_return']:+.1f}%",
        'Annualized': f"{r['annualized']:.1f}%",
        'Max Drawdown': f"{r['max_drawdown']:.1f}%",
        'Sharpe': f"{r['sharpe']:.2f}",
        'Trades': r['total_trades'],
        'Stops': r.get('stop_count', 0),
        'Replacements': r.get('replacement_count', 0)
    }
    for r in results
])

print("\n" + comparison.to_string(index=False))

# Analysis
print("\n" + "="*80)
print("ANALYSIS")
print("="*80)

spy_return = ((spy_bt.iloc[-1] / spy_bt.iloc[0]) - 1) * 100
print(f"\n📊 SPY Buy & Hold: {spy_return:+.1f}%")

print(f"\n📊 OUTPERFORMANCE vs SPY:")
for r in results:
    outperf = r['total_return'] - spy_return
    print(f"   {r['name']:45s} {outperf:+.1f}%")

# Drawdown target
target_dd = -25.0
print(f"\n🎯 DRAWDOWN TARGET: {target_dd}%")

passing = [r for r in results if r['max_drawdown'] >= target_dd]

if passing:
    print(f"\n✅ METHODS ACHIEVING TARGET:")
    for r in passing:
        dd_improvement = results[0]['max_drawdown'] - r['max_drawdown']
        return_impact = results[0]['total_return'] - r['total_return']
        print(f"\n   {r['name']}")
        print(f"   - Drawdown: {r['max_drawdown']:.1f}% (improved by {dd_improvement:.1f}%)")
        print(f"   - Return: {r['total_return']:+.1f}% (reduced by {return_impact:.1f}%)")
        print(f"   - Sharpe: {r['sharpe']:.2f}")
else:
    print("\n⚠️  Target not achieved. Try combining with 7 stocks.")

# Best risk-adjusted
best = max(results, key=lambda x: x['sharpe'])

print(f"\n🏆 BEST RISK-ADJUSTED: {best['name']}")
print(f"   Sharpe: {best['sharpe']:.2f}")
print(f"   Return: {best['total_return']:+.1f}%")
print(f"   Drawdown: {best['max_drawdown']:.1f}%")

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)

summary = pd.DataFrame([
    {
        'Method': r['name'],
        'Final_Value': r['final_value'],
        'Total_Return_Pct': r['total_return'],
        'Annualized_Pct': r['annualized'],
        'Max_Drawdown_Pct': r['max_drawdown'],
        'Sharpe_Ratio': r['sharpe'],
        'Total_Trades': r['total_trades'],
        'Stops_Triggered': r.get('stop_count', 0),
        'Replacements_Made': r.get('replacement_count', 0)
    }
    for r in results
])

summary.to_csv(output_dir / 'full_strategy_dynamic_stops.csv', index=False)

print(f"\n📁 Results saved to: {output_dir}/full_strategy_dynamic_stops.csv")

print("\n✅ Full strategy + dynamic stops testing complete!")
