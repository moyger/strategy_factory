"""
Compare Nick Radge Qualifiers: ROC vs BSS (and others)

Tests all performance qualifiers from strategy_factory:
1. ROC (Rate of Change) - Original Nick Radge
2. BSS (Breakout Strength Score) - Tomas Nesnidal inspired
3. ANM (ATR-Normalized Momentum)
4. VEM (Volatility Expansion Momentum)
5. TQS (Trend Quality Score)
6. RAM (Risk-Adjusted Momentum)
7. Composite (Weighted combination)

Period: 2020-2024 (same as previous tests)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import quantstats as qs
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import Nick Radge Enhanced strategy
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy

# Import enhanced strategy with importlib
import importlib.util
spec = importlib.util.spec_from_file_location("nick_radge_bss",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py")
bss_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bss_module)
NickRadgeEnhanced = bss_module.NickRadgeEnhanced

print("="*80)
print("NICK RADGE QUALIFIERS COMPARISON")
print("="*80)
print("\n🎯 Testing: ROC vs BSS vs Other Qualifiers")
print("   Period: 2020-2024 (5 years)")
print("   Initial Capital: $100,000\n")

# ============================================================================
# 1. DOWNLOAD DATA
# ============================================================================
print("="*80)
print("DOWNLOADING DATA")
print("="*80)

# Same universe as previous tests
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

print(f"\n📥 Downloading {len(stock_tickers)} stocks + SPY + GLD...")
start_date = '2019-01-01'  # Extra lookback
end_date = '2024-12-31'

# Download stocks
stock_data = yf.download(stock_tickers, start=start_date, end=end_date, progress=False)
if isinstance(stock_data.columns, pd.MultiIndex):
    prices = stock_data['Close'].copy()
else:
    prices = stock_data[['Close']].copy()
prices = prices.ffill().dropna(how='all')

# Download SPY
spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)
if isinstance(spy_data.columns, pd.MultiIndex):
    spy_data.columns = spy_data.columns.get_level_values(0)
spy_prices = spy_data['Close'].ffill()

# Download GLD
gld_data = yf.download('GLD', start=start_date, end=end_date, progress=False)
if isinstance(gld_data.columns, pd.MultiIndex):
    gld_data.columns = gld_data.columns.get_level_values(0)
gld_prices = gld_data['Close'].ffill()

# Add GLD to universe
prices['GLD'] = gld_prices

# Align all data
common_dates = prices.index.intersection(spy_prices.index)
prices = prices.loc[common_dates]
spy_prices = spy_prices.loc[common_dates]

# Filter to backtest period
backtest_start = '2020-01-01'
prices = prices[prices.index >= backtest_start]
spy_prices = spy_prices[spy_prices.index >= backtest_start]

print(f"✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")
print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")

# ============================================================================
# 2. TEST EACH QUALIFIER
# ============================================================================

qualifiers_to_test = [
    ('roc', 'ROC (Original Nick Radge)', {}),
    ('bss', 'Breakout Strength Score', {'poi_period': 100, 'atr_period': 14, 'k': 2.0}),
    ('anm', 'ATR-Normalized Momentum', {'momentum_period': 100, 'atr_period': 14}),
    ('vem', 'Volatility Expansion Momentum', {'roc_period': 100, 'atr_period': 14}),
]

results = []

for qualifier_type, qualifier_name, params in qualifiers_to_test:
    print("\n" + "="*80)
    print(f"TESTING: {qualifier_name} ({qualifier_type.upper()})")
    print("="*80)

    if qualifier_type == 'roc':
        # Use original Nick Radge strategy
        strategy = NickRadgeMomentumStrategy(
            portfolio_size=7,
            roc_period=100,
            ma_period=100,
            rebalance_freq='QS',
            use_momentum_weighting=True,
            use_regime_filter=True,
            use_relative_strength=True,
            strong_bull_positions=7,
            weak_bull_positions=3,
            bear_positions=0,
            bear_market_asset='GLD',
            bear_allocation=1.0
        )

        portfolio = strategy.backtest(
            prices=prices,
            spy_prices=spy_prices,
            initial_capital=100000,
            fees=0.001,
            slippage=0.0005
        )
    else:
        # Use enhanced strategy with specific qualifier
        strategy = NickRadgeEnhanced(
            portfolio_size=7,
            qualifier_type=qualifier_type,
            ma_period=100,
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
            bear_allocation=1.0,
            qualifier_params=params
        )

        portfolio = strategy.backtest(
            prices=prices,
            spy_prices=spy_prices,
            initial_capital=100000,
            fees=0.001,
            slippage=0.0005
        )

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

    try:
        win_rate = portfolio.trades.win_rate()
        if isinstance(win_rate, pd.Series):
            win_rate = float(win_rate.mean())
        else:
            win_rate = float(win_rate)
    except:
        win_rate = 0.0

    try:
        profit_factor = portfolio.trades.profit_factor()
        if isinstance(profit_factor, pd.Series):
            profit_factor = float(profit_factor.mean())
        else:
            profit_factor = float(profit_factor)
    except:
        profit_factor = 0.0

    # Calculate SPY return
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    print(f"\n📊 RESULTS:")
    print(f"Total Return:        {total_return:+.2f}%")
    print(f"Sharpe Ratio:        {sharpe:.2f}")
    print(f"Max Drawdown:        {max_dd*100:.2f}%")
    print(f"Total Trades:        {num_trades}")
    print(f"Win Rate:            {win_rate*100:.1f}%")
    print(f"Profit Factor:       {profit_factor:.2f}")
    print(f"vs SPY ({spy_return:.1f}%):  {total_return - spy_return:+.2f}%")

    results.append({
        'Qualifier': qualifier_name,
        'Code': qualifier_type.upper(),
        'Total_Return_Pct': total_return,
        'Sharpe_Ratio': sharpe,
        'Max_Drawdown_Pct': max_dd * 100,
        'Num_Trades': num_trades,
        'Win_Rate_Pct': win_rate * 100,
        'Profit_Factor': profit_factor,
        'vs_SPY_Pct': total_return - spy_return,
        'Final_Value': final_value
    })

# ============================================================================
# 3. COMPARISON TABLE
# ============================================================================
print("\n" + "="*80)
print("COMPREHENSIVE COMPARISON")
print("="*80)

results_df = pd.DataFrame(results)
results_df = results_df.sort_values('Total_Return_Pct', ascending=False)

print("\n")
print(results_df[['Qualifier', 'Code', 'Total_Return_Pct', 'Sharpe_Ratio',
                  'Max_Drawdown_Pct', 'vs_SPY_Pct']].to_string(index=False))

# ============================================================================
# 4. DETAILED ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("DETAILED ANALYSIS")
print("="*80)

# Find best performer
best = results_df.iloc[0]
worst = results_df.iloc[-1]

print(f"\n🏆 BEST PERFORMER: {best['Qualifier']} ({best['Code']})")
print(f"   Total Return: {best['Total_Return_Pct']:+.2f}%")
print(f"   Sharpe Ratio: {best['Sharpe_Ratio']:.2f}")
print(f"   Max Drawdown: {best['Max_Drawdown_Pct']:.2f}%")
print(f"   Win Rate: {best['Win_Rate_Pct']:.1f}%")
print(f"   Profit Factor: {best['Profit_Factor']:.2f}")

print(f"\n❌ WORST PERFORMER: {worst['Qualifier']} ({worst['Code']})")
print(f"   Total Return: {worst['Total_Return_Pct']:+.2f}%")
print(f"   Performance Gap: {best['Total_Return_Pct'] - worst['Total_Return_Pct']:.2f}%")

# Risk-adjusted winner
best_sharpe = results_df.loc[results_df['Sharpe_Ratio'].idxmax()]
print(f"\n⚖️  BEST RISK-ADJUSTED: {best_sharpe['Qualifier']} ({best_sharpe['Code']})")
print(f"   Sharpe Ratio: {best_sharpe['Sharpe_Ratio']:.2f}")
print(f"   Total Return: {best_sharpe['Total_Return_Pct']:+.2f}%")

# SPY comparison
spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100
print(f"\n📈 vs SPY BENCHMARK:")
print(f"   SPY Return: {spy_return:+.2f}%")

beat_spy = results_df[results_df['vs_SPY_Pct'] > 0]
print(f"   Strategies that beat SPY: {len(beat_spy)}/{len(results_df)}")

if len(beat_spy) > 0:
    best_vs_spy = beat_spy.loc[beat_spy['vs_SPY_Pct'].idxmax()]
    print(f"   Best outperformance: {best_vs_spy['Qualifier']} (+{best_vs_spy['vs_SPY_Pct']:.2f}%)")

# ============================================================================
# 5. SAVE RESULTS
# ============================================================================
print("\n" + "="*80)
print("SAVING RESULTS")
print("="*80)

output_dir = Path('results/nick_radge_qualifiers')
output_dir.mkdir(parents=True, exist_ok=True)

results_df.to_csv(output_dir / 'qualifiers_comparison.csv', index=False)
print(f"✅ Results saved: {output_dir}/qualifiers_comparison.csv")

# Create summary report
with open(output_dir / 'QUALIFIERS_SUMMARY.md', 'w') as f:
    f.write("# Nick Radge Qualifiers Comparison\n\n")
    f.write(f"**Test Period:** {prices.index[0].date()} to {prices.index[-1].date()}\n")
    f.write(f"**Initial Capital:** $100,000\n")
    f.write(f"**SPY Return:** {spy_return:+.2f}%\n\n")

    f.write("## Performance Ranking\n\n")
    f.write("| Rank | Qualifier | Return | Sharpe | Max DD | vs SPY |\n")
    f.write("|------|-----------|--------|--------|--------|--------|\n")

    for i, row in enumerate(results_df.itertuples(), 1):
        f.write(f"| {i} | {row.Qualifier} ({row.Code}) | ")
        f.write(f"{row.Total_Return_Pct:+.1f}% | ")
        f.write(f"{row.Sharpe_Ratio:.2f} | ")
        f.write(f"{row.Max_Drawdown_Pct:.1f}% | ")
        f.write(f"{row.vs_SPY_Pct:+.1f}% |\n")

    f.write(f"\n## Winner\n\n")
    f.write(f"**{best['Qualifier']}** ({best['Code']}) is the best performer:\n")
    f.write(f"- Total Return: {best['Total_Return_Pct']:+.2f}%\n")
    f.write(f"- Sharpe Ratio: {best['Sharpe_Ratio']:.2f}\n")
    f.write(f"- Max Drawdown: {best['Max_Drawdown_Pct']:.2f}%\n")
    f.write(f"- Outperformance vs SPY: {best['vs_SPY_Pct']:+.2f}%\n")

    f.write(f"\n## Qualifier Descriptions\n\n")
    f.write("### ROC (Rate of Change)\n")
    f.write("- **Original Nick Radge method**\n")
    f.write("- Formula: (Price - Price[100 days ago]) / Price[100 days ago]\n")
    f.write("- Measures pure momentum\n\n")

    f.write("### BSS (Breakout Strength Score)\n")
    f.write("- **Tomas Nesnidal inspired**\n")
    f.write("- Formula: (Price - POI) / (k × ATR)\n")
    f.write("- Measures breakout conviction (distance from 100-day MA in ATR units)\n")
    f.write("- BSS > 2.0 = strong breakout\n\n")

    f.write("### ANM (ATR-Normalized Momentum)\n")
    f.write("- Formula: Momentum / ATR%\n")
    f.write("- Adjusts momentum for volatility\n")
    f.write("- High ANM = strong move with controlled volatility\n\n")

    f.write("### VEM (Volatility Expansion Momentum)\n")
    f.write("- Formula: ROC × (Current ATR / Avg ATR)\n")
    f.write("- Combines momentum with volatility expansion\n")
    f.write("- High VEM = strong momentum + increasing volatility (breakout conditions)\n\n")

print(f"✅ Summary saved: {output_dir}/QUALIFIERS_SUMMARY.md")

print("\n" + "="*80)
print("✅ COMPARISON COMPLETE")
print("="*80)
print(f"\n🏆 Winner: {best['Qualifier']} ({best['Code']})")
print(f"   Return: {best['Total_Return_Pct']:+.2f}%")
print(f"   Sharpe: {best['Sharpe_Ratio']:.2f}")
print(f"   vs SPY: {best['vs_SPY_Pct']:+.2f}%")
