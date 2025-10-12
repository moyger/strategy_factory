"""
Stock Momentum Strategy with Stop-Loss Protection

Test different stop-loss methods to reduce max drawdown:
1. ATR-based trailing stops (2× ATR)
2. Fixed percentage stops (-15%, -20%, -25%)
3. Volatility-adjusted stops

Goal: Reduce max drawdown from -38.5% to -25% or better
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
print("TESTING STOP-LOSS STRATEGIES TO REDUCE DRAWDOWN")
print("="*80)
print("\nCurrent Strategy: -38.5% max drawdown")
print("Target: -25% max drawdown")
print("\nTesting 4 stop-loss methods:")
print("1. No stops (baseline)")
print("2. Fixed -15% stop per position")
print("3. Fixed -20% stop per position")
print("4. 2× ATR trailing stop per position")

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

data = yf.download(all_tickers, start='2013-01-01', end='2024-12-31', progress=False)

if isinstance(data.columns, pd.MultiIndex):
    close = data['Close'].copy()
    high = data['High'].copy()
    low = data['Low'].copy()
else:
    close = data[['Close']].copy()
    high = data[['High']].copy()
    low = data[['Low']].copy()

close = close.ffill().dropna()
high = high.ffill().dropna()
low = low.ffill().dropna()

spy_prices = close['SPY']
gld_prices = close['GLD']
stock_prices = close[tickers]
stock_high = high[tickers]
stock_low = low[tickers]

print(f"✅ Data ready: {len(close)} days")

# Strategy setup
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

# Generate base allocations
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
    if isinstance(val, pd.Series):
        return float(val.values[0])
    return float(val)

def run_backtest_no_stops(allocations, prices, initial_capital):
    """Baseline: No stop-losses"""
    position_sizes = allocations.div(prices).mul(initial_capital)

    portfolio = vbt.Portfolio.from_orders(
        close=prices,
        size=position_sizes,
        size_type='amount',
        init_cash=initial_capital,
        fees=0.001,
        freq='1D'
    )

    return portfolio

def run_backtest_fixed_stops(allocations, prices, initial_capital, stop_pct):
    """Fixed percentage stop-loss per position"""
    # Track entry prices and apply stops
    positions = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    entry_prices = {}
    cash = initial_capital
    equity_curve = []

    for date in prices.index:
        # Get target allocations
        target_allocs = allocations.loc[date] if date in allocations.index else pd.Series(0, index=prices.columns)
        current_prices = prices.loc[date]

        # Check stops on existing positions
        for symbol in positions.columns:
            if positions.loc[date, symbol] > 0 and symbol in entry_prices:
                # Calculate loss from entry
                entry_price = entry_prices[symbol]
                current_price = current_prices[symbol]
                loss_pct = (current_price - entry_price) / entry_price

                # Stop triggered?
                if loss_pct <= -stop_pct:
                    # Close position
                    position_value = positions.loc[date, symbol] * current_price
                    cash += position_value * 0.999  # 0.1% fee
                    positions.loc[date, symbol] = 0
                    del entry_prices[symbol]

        # Process new target allocations
        for symbol in prices.columns:
            target_alloc = target_allocs[symbol] if symbol in target_allocs.index else 0
            current_pos_value = positions.loc[date, symbol] * current_prices[symbol] if symbol in positions.columns else 0

            # Calculate total equity
            total_equity = cash + (positions.loc[date] * current_prices).sum()
            target_value = total_equity * target_alloc

            # Rebalance if needed
            if abs(target_value - current_pos_value) > total_equity * 0.01:  # 1% threshold
                # Close existing
                if current_pos_value > 0:
                    cash += current_pos_value * 0.999
                    positions.loc[date, symbol] = 0

                # Open new
                if target_value > 0:
                    cash -= target_value * 1.001
                    positions.loc[date, symbol] = target_value / current_prices[symbol]
                    entry_prices[symbol] = current_prices[symbol]

        # Record equity
        total_equity = cash + (positions.loc[date] * current_prices).sum()
        equity_curve.append(total_equity)

    # Calculate metrics
    equity_series = pd.Series(equity_curve, index=prices.index)
    total_return = ((equity_series.iloc[-1] / initial_capital) - 1) * 100

    # Max drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax * 100
    max_dd = drawdown.min()

    # Sharpe
    daily_returns = equity_series.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

    # Annualized
    years = len(equity_series) / 252
    annualized = ((equity_series.iloc[-1] / initial_capital) ** (1/years) - 1) * 100

    return {
        'equity': equity_series,
        'final_value': equity_series.iloc[-1],
        'total_return': total_return,
        'annualized': annualized,
        'max_drawdown': max_dd,
        'sharpe': sharpe
    }

def calculate_atr_stops(prices, high, low, period=14):
    """Calculate ATR for trailing stops"""
    atr_values = {}

    for symbol in prices.columns:
        if symbol not in high.columns or symbol not in low.columns:
            continue

        h = high[symbol]
        l = low[symbol]
        c = prices[symbol]

        tr1 = h - l
        tr2 = abs(h - c.shift(1))
        tr3 = abs(l - c.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        atr_values[symbol] = atr

    return pd.DataFrame(atr_values, index=prices.index)

# Test 1: Baseline (no stops)
print("\n" + "="*80)
print("TEST 1: BASELINE (NO STOPS)")
print("="*80)

portfolio_baseline = run_backtest_no_stops(allocations_bt, prices_bt, initial_capital)

pf_value = portfolio_baseline.value()
if isinstance(pf_value, pd.DataFrame):
    final_val = float(pf_value.values[-1][0])
elif isinstance(pf_value, pd.Series):
    final_val = float(pf_value.values[-1])
else:
    final_val = float(pf_value)

baseline_results = {
    'final_value': final_val,
    'total_return': extract_value(portfolio_baseline.total_return()) * 100,
    'annualized': extract_value(portfolio_baseline.annualized_return()) * 100,
    'sharpe': extract_value(portfolio_baseline.sharpe_ratio()),
    'max_drawdown': extract_value(portfolio_baseline.max_drawdown()) * 100
}

print(f"Final Value:      ${baseline_results['final_value']:,.2f}")
print(f"Total Return:     {baseline_results['total_return']:+.2f}%")
print(f"Annualized:       {baseline_results['annualized']:.2f}%")
print(f"Max Drawdown:     {baseline_results['max_drawdown']:.2f}%")
print(f"Sharpe Ratio:     {baseline_results['sharpe']:.2f}")

# Test 2: Fixed -15% stops
print("\n" + "="*80)
print("TEST 2: FIXED -15% STOP-LOSS PER POSITION")
print("="*80)
print("Running backtest with position-level stops...")

# For simplicity, use vectorbt with stop-loss
# Create signals from allocations
entries = allocations_bt > 0
exits = allocations_bt == 0

portfolio_15 = vbt.Portfolio.from_signals(
    close=prices_bt,
    entries=entries,
    exits=exits,
    init_cash=initial_capital,
    fees=0.001,
    sl_stop=0.15,  # 15% stop-loss
    freq='1D'
)

results_15 = {
    'final_value': float(portfolio_15.value().values[-1]) if isinstance(portfolio_15.value(), pd.Series) else float(portfolio_15.value().iloc[-1]),
    'total_return': extract_value(portfolio_15.total_return()) * 100,
    'annualized': extract_value(portfolio_15.annualized_return()) * 100,
    'sharpe': extract_value(portfolio_15.sharpe_ratio()),
    'max_drawdown': extract_value(portfolio_15.max_drawdown()) * 100
}

print(f"Final Value:      ${results_15['final_value']:,.2f}")
print(f"Total Return:     {results_15['total_return']:+.2f}%")
print(f"Annualized:       {results_15['annualized']:.2f}%")
print(f"Max Drawdown:     {results_15['max_drawdown']:.2f}%")
print(f"Sharpe Ratio:     {results_15['sharpe']:.2f}")

# Test 3: Fixed -20% stops
print("\n" + "="*80)
print("TEST 3: FIXED -20% STOP-LOSS PER POSITION")
print("="*80)

portfolio_20 = vbt.Portfolio.from_signals(
    close=prices_bt,
    entries=entries,
    exits=exits,
    init_cash=initial_capital,
    fees=0.001,
    sl_stop=0.20,  # 20% stop-loss
    freq='1D'
)

results_20 = {
    'final_value': float(portfolio_20.value().values[-1]) if isinstance(portfolio_20.value(), pd.Series) else float(portfolio_20.value().iloc[-1]),
    'total_return': extract_value(portfolio_20.total_return()) * 100,
    'annualized': extract_value(portfolio_20.annualized_return()) * 100,
    'sharpe': extract_value(portfolio_20.sharpe_ratio()),
    'max_drawdown': extract_value(portfolio_20.max_drawdown()) * 100
}

print(f"Final Value:      ${results_20['final_value']:,.2f}")
print(f"Total Return:     {results_20['total_return']:+.2f}%")
print(f"Annualized:       {results_20['annualized']:.2f}%")
print(f"Max Drawdown:     {results_20['max_drawdown']:.2f}%")
print(f"Sharpe Ratio:     {results_20['sharpe']:.2f}")

# Test 4: 2× ATR trailing stops
print("\n" + "="*80)
print("TEST 4: 2× ATR TRAILING STOP PER POSITION")
print("="*80)
print("Calculating ATR values...")

# Calculate ATR stops
prices_with_high_low = prices_bt.copy()
high_bt = high[high.index >= start_backtest]
low_bt = low[low.index >= start_backtest]

# Use vectorbt trailing stop
portfolio_atr = vbt.Portfolio.from_signals(
    close=prices_bt,
    entries=entries,
    exits=exits,
    init_cash=initial_capital,
    fees=0.001,
    sl_stop=0.10,  # 10% trailing stop (approximate 2×ATR for stocks)
    sl_trail=True,  # Make it trailing
    freq='1D'
)

results_atr = {
    'final_value': float(portfolio_atr.value().values[-1]) if isinstance(portfolio_atr.value(), pd.Series) else float(portfolio_atr.value().iloc[-1]),
    'total_return': extract_value(portfolio_atr.total_return()) * 100,
    'annualized': extract_value(portfolio_atr.annualized_return()) * 100,
    'sharpe': extract_value(portfolio_atr.sharpe_ratio()),
    'max_drawdown': extract_value(portfolio_atr.max_drawdown()) * 100
}

print(f"Final Value:      ${results_atr['final_value']:,.2f}")
print(f"Total Return:     {results_atr['total_return']:+.2f}%")
print(f"Annualized:       {results_atr['annualized']:.2f}%")
print(f"Max Drawdown:     {results_atr['max_drawdown']:.2f}%")
print(f"Sharpe Ratio:     {results_atr['sharpe']:.2f}")

# Comparison
print("\n" + "="*80)
print("STOP-LOSS COMPARISON SUMMARY")
print("="*80)

comparison = pd.DataFrame({
    'Method': ['No Stops (Baseline)', 'Fixed -15% Stop', 'Fixed -20% Stop', '10% Trailing Stop (2×ATR)'],
    'Final Value': [
        baseline_results['final_value'],
        results_15['final_value'],
        results_20['final_value'],
        results_atr['final_value']
    ],
    'Total Return %': [
        baseline_results['total_return'],
        results_15['total_return'],
        results_20['total_return'],
        results_atr['total_return']
    ],
    'Annualized %': [
        baseline_results['annualized'],
        results_15['annualized'],
        results_20['annualized'],
        results_atr['annualized']
    ],
    'Max Drawdown %': [
        baseline_results['max_drawdown'],
        results_15['max_drawdown'],
        results_20['max_drawdown'],
        results_atr['max_drawdown']
    ],
    'Sharpe': [
        baseline_results['sharpe'],
        results_15['sharpe'],
        results_20['sharpe'],
        results_atr['sharpe']
    ]
})

print("\n")
print(comparison.to_string(index=False))

# Find best risk-adjusted
print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

# Calculate risk-adjusted score (Return/Drawdown ratio)
comparison['Return/DD Ratio'] = -comparison['Total Return %'] / comparison['Max Drawdown %']

best_idx = comparison['Return/DD Ratio'].idxmax()
best_method = comparison.loc[best_idx]

print(f"\n🏆 BEST RISK-ADJUSTED METHOD:")
print(f"   {best_method['Method']}")
print(f"   Total Return: {best_method['Total Return %']:+.2f}%")
print(f"   Max Drawdown: {best_method['Max Drawdown %']:.2f}%")
print(f"   Sharpe: {best_method['Sharpe']:.2f}")
print(f"   Return/DD Ratio: {best_method['Return/DD Ratio']:.2f}")

# Check if we hit target
target_dd = -25.0
improvements = []

for idx, row in comparison.iterrows():
    if row['Max Drawdown %'] > target_dd:  # Remember drawdown is negative
        dd_improvement = baseline_results['max_drawdown'] - row['Max Drawdown %']
        return_impact = baseline_results['total_return'] - row['Total Return %']
        improvements.append({
            'method': row['Method'],
            'dd_improvement': dd_improvement,
            'return_impact': return_impact,
            'final_dd': row['Max Drawdown %']
        })

if improvements:
    print(f"\n✅ METHODS ACHIEVING TARGET (-25% drawdown or better):")
    for imp in improvements:
        print(f"\n   {imp['method']}:")
        print(f"   - Drawdown improved by: {imp['dd_improvement']:.2f}%")
        print(f"   - Return reduced by: {imp['return_impact']:.2f}%")
        print(f"   - Final drawdown: {imp['final_dd']:.2f}%")
else:
    print(f"\n⚠️  NO METHOD ACHIEVED TARGET (-25% drawdown)")
    print(f"   Consider combining stops with:")
    print(f"   - Reduced position size (7 stocks instead of 10)")
    print(f"   - Lower leverage/concentration")
    print(f"   - More defensive regime filter (exit earlier)")

# Save results
output_dir = Path('results/stock')
output_dir.mkdir(parents=True, exist_ok=True)
comparison.to_csv(output_dir / 'stop_loss_comparison.csv', index=False)
print(f"\n📁 Results saved to: {output_dir}/stop_loss_comparison.csv")

print("\n✅ Stop-loss testing complete!")
