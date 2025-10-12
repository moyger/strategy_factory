# QuantStats Backtest Reports Guide

## Overview

Yes, the Strategy Factory generates **comprehensive QuantStats backtest reports**! QuantStats is a professional-grade Python library for portfolio analytics that creates institutional-quality tearsheets.

## What's Included

### 1. **HTML Reports** (QuantStats)
Full interactive HTML reports with:
- 📈 **Cumulative Returns Chart** - Performance over time
- 🔥 **Monthly Returns Heatmap** - Visual performance calendar
- 📉 **Drawdown Analysis** - Maximum and underwater periods
- 📊 **Rolling Statistics** - Sharpe, volatility, returns
- 🎯 **Distribution Charts** - Returns distribution and daily
- 📋 **Comprehensive Metrics** - 50+ performance indicators

### 2. **Trade History** (CSV)
Detailed trade-by-trade breakdown:
- Entry/Exit timestamps and prices
- Position sizes and fees
- Profit/Loss per trade
- Win/Loss analysis

### 3. **Comparison Reports**
Side-by-side strategy comparisons with all key metrics

## Generated Reports

After running `generate_reports.py`, you'll find:

```
results/analysis_reports/
├── best_strategy_breakout_report.html    (92 MB - Full QuantStats Report)
├── best_strategy_trades.csv              (Trade history)
└── top5_comparison.csv                   (Strategy comparison)
```

## Key Metrics in Reports

### Returns Metrics
- **Total Return**: 776.30% (7.76x your money!)
- **CAGR**: Compound Annual Growth Rate
- **Daily Mean**: Average daily return

### Risk-Adjusted Metrics
- **Sharpe Ratio**: 1.36 (excellent risk-adjusted return)
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return vs max drawdown
- **Omega Ratio**: Probability-weighted ratio

### Risk Metrics
- **Max Drawdown**: -41.05% (worst peak-to-trough decline)
- **Volatility**: Daily standard deviation
- **VaR (95%)**: Value at Risk at 95% confidence
- **CVaR (95%)**: Conditional Value at Risk

### Trade Statistics
- **Win Rate**: 70.6% (12 winners out of 17 trades)
- **Avg Win**: $7,469.43
- **Avg Loss**: -$2,400.64
- **Profit Factor**: Win/Loss ratio
- **Consecutive Wins**: Up to 14 in a row
- **Consecutive Losses**: Up to 14 in a row

## How to Generate Reports

### Quick Generation
```bash
python generate_reports.py
```

This will:
1. Load the best strategy from results
2. Run full backtest
3. Generate QuantStats HTML report
4. Export trade history
5. Compare top 5 strategies

### Custom Report Generation

```python
from strategy_factory.analyzer import StrategyAnalyzer
import vectorbt as vbt

# Create analyzer
analyzer = StrategyAnalyzer()

# Option 1: From portfolio object
portfolio = vbt.Portfolio.from_signals(...)
analyzer.analyze_portfolio(portfolio, output_file='my_strategy.html')

# Option 2: From returns series
returns = portfolio.returns()
analyzer.generate_full_report(returns, output_file='my_report.html')

# Get metrics dictionary
metrics = analyzer.get_key_metrics(returns)
analyzer.print_metrics(metrics)

# Export trades
trades = analyzer.export_trades(portfolio, 'trades.csv')
```

## Available Analyzer Features

### 1. Full HTML Report
```python
analyzer.generate_full_report(
    returns=returns,
    benchmark=benchmark_returns,  # Optional: compare to BTC buy-hold
    output_file='report.html',
    title='My Strategy'
)
```

### 2. Console Tearsheet
```python
# Print to console/notebook
analyzer.generate_tearsheet(returns, mode='full')  # or 'basic' or 'metrics'
```

### 3. Key Metrics
```python
metrics = analyzer.get_key_metrics(returns)
# Returns dict with 30+ metrics
```

### 4. Strategy Comparison
```python
strategies = {
    'Strategy A': returns_a,
    'Strategy B': returns_b,
    'Strategy C': returns_c
}
comparison = analyzer.compare_strategies(strategies)
```

### 5. Monte Carlo Simulation
```python
results = analyzer.monte_carlo_report(
    returns,
    n_simulations=1000,
    output_file='monte_carlo.html'
)
```

### 6. Rolling Metrics
```python
rolling_df = analyzer.rolling_metrics(
    returns,
    window=252,  # 1 year
    output_file='rolling.csv'
)
```

### 7. Drawdown Analysis
```python
drawdowns = analyzer.drawdown_analysis(returns)
# Returns DataFrame with all drawdown periods
```

## Best Strategy Results

**Strategy**: Breakout (Lookback=10, Breakout=2.0%)

| Metric | Value |
|--------|-------|
| **Total Return** | 776.30% |
| **Sharpe Ratio** | 1.36 |
| **Max Drawdown** | -41.05% |
| **Win Rate** | 70.6% |
| **Total Trades** | 17 |
| **Avg Win** | $7,469 |
| **Avg Loss** | -$2,401 |
| **Consecutive Wins** | Up to 14 |

## Viewing Reports

### HTML Reports
Open in any browser:
```bash
open results/analysis_reports/best_strategy_breakout_report.html
```

The HTML report includes:
- Interactive charts (can zoom, pan, hover)
- Downloadable images
- Printable format
- Mobile-responsive design

### Trade History
Open in Excel or any spreadsheet tool:
```bash
open results/analysis_reports/best_strategy_trades.csv
```

## Comparison with QuantAnalyzer

| Feature | QuantAnalyzer (Paid) | QuantStats (Free) |
|---------|---------------------|-------------------|
| **Price** | $499+ | Free & Open Source |
| **HTML Reports** | ✅ | ✅ |
| **Monthly Heatmaps** | ✅ | ✅ |
| **Drawdown Analysis** | ✅ | ✅ |
| **Risk Metrics** | ✅ | ✅ |
| **Interactive Charts** | ✅ | ✅ |
| **Trade Analysis** | ✅ | ✅ (via vectorbt) |
| **Monte Carlo** | ✅ | ✅ |
| **Custom Scripting** | ❌ | ✅ (Python) |
| **Integration** | NinjaTrader Only | Any Python Strategy |

**QuantStats is professional-grade and FREE!**

## Adding to Quick Start

Want reports generated automatically? Add to `quick_start.py`:

```python
# After step 4 (optimization)
if opt_result is not None:
    print("\n📊 Step 4.5: Generating QuantStats report...")

    # Re-run best strategy
    portfolio = optimizer.backtest_strategy(df, opt_result.best_params)

    # Generate report
    analyzer = StrategyAnalyzer()
    report_path = analyzer.generate_full_report(
        returns=portfolio.returns(),
        output_file='optimized_strategy_report.html',
        title='Optimized Strategy Performance'
    )

    print(f"✅ Report: {report_path}")
```

## Tips

1. **Large HTML files** - Reports can be 50-100MB due to embedded charts. This is normal.

2. **Frequency matters** - Make sure returns have correct frequency for accurate annualization:
   ```python
   returns.index.freq = '5min'  # for 5-minute data
   ```

3. **Benchmark comparison** - Add BTC buy-and-hold as benchmark:
   ```python
   btc_returns = df['close'].pct_change()
   analyzer.generate_full_report(returns, benchmark=btc_returns)
   ```

4. **Custom metrics** - QuantStats has 100+ metrics available:
   ```python
   import quantstats as qs
   qs.stats.kelly_criterion(returns)
   qs.stats.ulcer_index(returns)
   qs.stats.tail_ratio(returns)
   ```

## Resources

- **QuantStats Docs**: https://github.com/ranaroussi/quantstats
- **Analyzer Code**: `strategy_factory/analyzer.py`
- **Example Script**: `generate_reports.py`
- **Sample Report**: `results/analysis_reports/best_strategy_breakout_report.html`

---

**Generated**: October 2025
**Strategy Factory**: v1.0
