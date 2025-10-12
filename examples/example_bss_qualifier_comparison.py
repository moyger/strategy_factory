#!/usr/bin/env python3
"""
BSS Qualifier Comparison - Proper Framework Usage

Tests Nick Radge Enhanced strategy with all 7 qualifier types:
1. ROC (Rate of Change - baseline)
2. BSS (Breakout Strength Score)
3. ANM (ATR-Normalized Momentum)
4. VEM (Volatility Expansion Momentum)
5. TQS (Trend Quality Score)
6. RAM (Risk-Adjusted Momentum)
7. Composite (weighted combination)

Uses the strategy's built-in backtest() method (following framework design).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import from renamed strategy file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "nick_radge_enhanced",
    "strategies/02_nick_radge_enhanced_bss.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeEnhanced = module.NickRadgeEnhanced

# Test universe (Nick Radge 50-stock universe)
UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'WMT',
    'MA', 'UNH', 'HD', 'PG', 'DIS', 'BAC', 'ADBE', 'NFLX', 'CRM', 'CSCO',
    'PEP', 'TMO', 'COST', 'AVGO', 'ABT', 'LLY', 'ACN', 'NKE', 'MCD', 'ORCL',
    'DHR', 'TXN', 'QCOM', 'UNP', 'PM', 'NEE', 'HON', 'RTX', 'UPS', 'LOW',
    'IBM', 'INTU', 'AMD', 'AMAT', 'CVX', 'CAT', 'SBUX', 'GS', 'AXP', 'BLK'
]

print("=" * 80)
print("NICK RADGE ENHANCED - BSS QUALIFIER COMPARISON")
print("=" * 80)
print()
print("📊 Testing 7 qualifier types on 50-stock universe (2015-2024)")
print("⏱️  Expected runtime: 5-10 minutes (7 backtests × ~1 min each)")
print()

# Download data
print("📥 Downloading historical data...")
start_date = '2015-01-01'
end_date = '2024-12-31'

try:
    data = yf.download(UNIVERSE + ['SPY', 'GLD'], start=start_date, end=end_date, progress=False)

    # Handle MultiIndex columns from yfinance
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    prices = data['Adj Close'][UNIVERSE] if 'Adj Close' in data else data[UNIVERSE]
    prices = prices.dropna(how='all')

    spy = data['Adj Close']['SPY'] if 'Adj Close' in data else data['SPY']
    spy = spy.dropna()

    gld = data['Adj Close']['GLD'] if 'Adj Close' in data else data['GLD']
    gld = gld.dropna()

except Exception as e:
    print(f"❌ Error downloading data: {e}")
    print("Retrying with alternative method...")

    # Alternative: Download one by one
    all_tickers = UNIVERSE + ['SPY', 'GLD']
    dfs = []
    for ticker in all_tickers:
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)['Adj Close']
            df.name = ticker
            dfs.append(df)
        except:
            print(f"  ⚠️  Skipped {ticker}")

    combined = pd.concat(dfs, axis=1)
    prices = combined[UNIVERSE].dropna(how='all')
    spy = combined['SPY'].dropna()
    gld = combined['GLD'].dropna()

print(f"✅ Downloaded {len(UNIVERSE)} stocks + SPY + GLD")
print(f"   Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
print(f"   Total bars: {len(prices)}")
print()

# Test configurations
qualifiers = ['roc', 'bss', 'anm', 'vem', 'tqs', 'ram', 'composite']
results = []

print("🔬 Running backtests...")
print("-" * 80)

for i, qualifier in enumerate(qualifiers, 1):
    print(f"\n[{i}/7] Testing {qualifier.upper()}...")

    try:
        # Initialize strategy with built-in backtest method
        strategy = NickRadgeEnhanced(
            portfolio_size=7,
            qualifier_type=qualifier,
            ma_period=100,
            rebalance_freq='QS',  # Quarterly
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

        # Run backtest using strategy's built-in method
        portfolio = strategy.backtest(
            prices=prices,
            spy_prices=spy,
            gld_prices=gld,
            initial_capital=100000
        )

        # Extract metrics
        total_return = portfolio.total_return() * 100
        cagr = portfolio.annualized_return() * 100
        sharpe = portfolio.sharpe_ratio()
        max_dd = portfolio.max_drawdown() * 100

        # Win rate calculation
        trades = portfolio.trades.records
        if len(trades) > 0:
            winning_trades = sum(trades['pnl'] > 0)
            win_rate = (winning_trades / len(trades)) * 100
        else:
            win_rate = 0

        num_trades = len(trades)

        results.append({
            'Qualifier': qualifier.upper(),
            'Total Return': f"{total_return:.2f}%",
            'CAGR': f"{cagr:.2f}%",
            'Sharpe': f"{sharpe:.2f}",
            'Max DD': f"{max_dd:.2f}%",
            'Win Rate': f"{win_rate:.1f}%",
            'Trades': num_trades
        })

        print(f"   ✓ Return: {total_return:+.2f}% | Sharpe: {sharpe:.2f} | Max DD: {max_dd:.2f}% | Trades: {num_trades}")

    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        results.append({
            'Qualifier': qualifier.upper(),
            'Total Return': 'ERROR',
            'CAGR': 'ERROR',
            'Sharpe': 'ERROR',
            'Max DD': 'ERROR',
            'Win Rate': 'ERROR',
            'Trades': 0
        })

print()
print("-" * 80)
print()

# Display results
df_results = pd.DataFrame(results)
print("📈 FINAL RESULTS - QUALIFIER COMPARISON")
print("=" * 80)
print(df_results.to_string(index=False))
print()

# Determine winner
valid_results = [r for r in results if r['Total Return'] != 'ERROR']
if len(valid_results) > 0:
    returns = [float(r['Total Return'].replace('%', '')) for r in valid_results]
    best_idx = returns.index(max(returns))
    winner = valid_results[best_idx]

    print("🏆 WINNER (by Total Return)")
    print("-" * 80)
    print(f"Best Qualifier: {winner['Qualifier']}")
    print(f"Total Return: {winner['Total Return']}")
    print(f"CAGR: {winner['CAGR']}")
    print(f"Sharpe Ratio: {winner['Sharpe']}")
    print(f"Max Drawdown: {winner['Max DD']}")
    print(f"Win Rate: {winner['Win Rate']}")
    print(f"Total Trades: {winner['Trades']}")
    print()

    # Sharpe winner
    sharpes = [float(r['Sharpe']) for r in valid_results if r['Sharpe'] != 'ERROR']
    if len(sharpes) > 0:
        sharpe_best_idx = sharpes.index(max(sharpes))
        sharpe_winner = valid_results[sharpe_best_idx]

        if sharpe_winner['Qualifier'] != winner['Qualifier']:
            print("🎯 BEST RISK-ADJUSTED (by Sharpe Ratio)")
            print("-" * 80)
            print(f"Best Qualifier: {sharpe_winner['Qualifier']}")
            print(f"Sharpe Ratio: {sharpe_winner['Sharpe']}")
            print(f"Total Return: {sharpe_winner['Total Return']}")
            print(f"Max Drawdown: {sharpe_winner['Max DD']}")
            print()

# Save results
output_file = 'results/nick_radge/bss_qualifier_comparison.csv'
df_results.to_csv(output_file, index=False)
print(f"💾 Results saved to: {output_file}")

print()
print("=" * 80)
print("✅ TEST COMPLETE")
print("=" * 80)
print()

# Key insights
print("💡 KEY INSIGHTS - What Each Qualifier Measures")
print("-" * 80)
print()
print("1️⃣  ROC (Rate of Change) - BASELINE")
print("   Formula: (Price today - Price 100 days ago) / Price 100 days ago")
print("   → Simple momentum, Nick Radge original method")
print("   → Good for trending markets")
print()
print("2️⃣  BSS (Breakout Strength Score)")
print("   Formula: (Price - 100MA) / (k × ATR)")
print("   → Volatility-adjusted breakout strength")
print("   → Measures 'how many ATR units above the MA'")
print("   → Best for identifying strong breakouts relative to normal volatility")
print()
print("3️⃣  ANM (ATR-Normalized Momentum)")
print("   Formula: (Price - Price[lookback]) / (ATR × sqrt(lookback))")
print("   → Risk-adjusted momentum considering volatility path")
print("   → Normalizes for different volatility regimes")
print()
print("4️⃣  VEM (Volatility Expansion Momentum)")
print("   Formula: Momentum × (ATR today / ATR avg)")
print("   → Favors stocks with expanding volatility")
print("   → Breakout confirmation via volatility increase")
print()
print("5️⃣  TQS (Trend Quality Score)")
print("   Formula: Momentum / (sum of abs(daily returns))")
print("   → Rewards smooth trends, penalizes choppy moves")
print("   → Quality over quantity")
print()
print("6️⃣  RAM (Risk-Adjusted Momentum)")
print("   Formula: Momentum / Standard Deviation")
print("   → Classic Sharpe-like ratio for ranking")
print("   → Risk-adjusted return focus")
print()
print("7️⃣  COMPOSITE")
print("   Formula: Weighted average of all 6 qualifiers")
print("   → Diversified ranking approach")
print("   → Combines strengths of all methods")
print()
print("-" * 80)
print()
print("📖 For detailed BSS explanation, see:")
print("   docs/nick_radge/BSS_STRATEGY_EXPLAINED.md")
print()
print("🚀 To use the best qualifier in production:")
print("   Edit deployment/config_live.json → 'qualifier_type': 'bss'")
print()
