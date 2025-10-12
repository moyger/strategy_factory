# How to Run Strategies - Complete Guide

This guide shows you **5 different ways** to run trading strategies in the Strategy Factory system, from simplest to most advanced.

---

## Quick Start (30 seconds)

```bash
# Method 1: Use the universal runner (EASIEST!)
python run_strategy.py --strategy sma --fast 10 --slow 50

# Method 2: Run an example file
python examples/example_simple_sma.py

# Method 3: Run the complete workflow
python quick_start.py
```

---

## Table of Contents

1. [Method 1: Universal Strategy Runner](#method-1-universal-strategy-runner-easiest) ⭐ **RECOMMENDED FOR BEGINNERS**
2. [Method 2: Run Example Files](#method-2-run-example-files)
3. [Method 3: Run Quick Start Workflow](#method-3-run-quick-start-workflow)
4. [Method 4: Run Strategy Scripts Directly](#method-4-run-strategy-scripts-directly)
5. [Method 5: Create Custom Python Scripts](#method-5-create-custom-python-scripts)
6. [Advanced: Jupyter Notebooks](#advanced-jupyter-notebooks)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Method 1: Universal Strategy Runner (EASIEST) ⭐

The `run_strategy.py` script lets you run any strategy with simple command-line arguments.

### Basic Usage

```bash
# Simple strategies
python run_strategy.py --strategy sma --fast 10 --slow 50
python run_strategy.py --strategy rsi --period 14 --oversold 30 --overbought 70
python run_strategy.py --strategy breakout --window 20 --breakout-pct 2.0

# Advanced strategies
python run_strategy.py --strategy atr_trailing_stop
python run_strategy.py --strategy ftmo_challenge --challenge-size 50k
python run_strategy.py --strategy advanced --sizing-method kelly
```

### Generate Reports

Add `--report` to generate a detailed QuantStats HTML report:

```bash
python run_strategy.py --strategy atr_trailing_stop --report
python run_strategy.py --strategy ftmo_challenge --challenge-size 100k --report
```

### All Available Strategies

| Strategy | Command | Description |
|----------|---------|-------------|
| **SMA Crossover** | `--strategy sma` | Simple moving average crossover |
| **RSI Mean Reversion** | `--strategy rsi` | Buy oversold, sell overbought |
| **Breakout** | `--strategy breakout` | Trade price breakouts |
| **ATR Trailing Stop** | `--strategy atr_trailing_stop` | Dynamic ATR-based stops |
| **FTMO Challenge** | `--strategy ftmo_challenge` | FTMO-compliant strategy |
| **Advanced Template** | `--strategy advanced` | All features combined |

### Common Parameters

```bash
# Data and capital
--data data/crypto/BTCUSD_5m.csv  # Use different data file
--capital 50000                    # Starting capital (default: 10000)

# Risk management
--risk-percent 1.5                 # Risk per trade % (default: 1.0)
--atr-period 14                    # ATR calculation period
--atr-sl 2.0                       # Stop loss in ATR units
--atr-tp 4.0                       # Take profit in ATR units

# Position sizing
--sizing-method fixed_percent      # fixed_percent, kelly, or volatility
--kelly-fraction 0.5               # Kelly fraction (for kelly method)

# FTMO parameters
--challenge-size 50k               # 10k, 25k, 50k, 100k, 200k
--check-ftmo                       # Check FTMO compliance rules

# Filters
--no-session-filter                # Disable session filtering
--no-trend-filter                  # Disable trend filtering
--require-high-volatility          # Only trade high volatility

# Output
--report                           # Generate QuantStats HTML report
```

### Examples

```bash
# Conservative FTMO 50k strategy
python run_strategy.py --strategy ftmo_challenge \
    --challenge-size 50k \
    --risk-percent 0.5 \
    --atr-sl 3.0 \
    --atr-tp 6.0 \
    --report

# Aggressive Kelly sizing with high volatility filter
python run_strategy.py --strategy advanced \
    --sizing-method kelly \
    --kelly-fraction 0.5 \
    --require-high-volatility \
    --report

# Simple SMA test on different data
python run_strategy.py --strategy sma \
    --fast 20 \
    --slow 100 \
    --data data/crypto/ADAUSD_5m.csv
```

### Get Help

```bash
# See all available options
python run_strategy.py --help
```

---

## Method 2: Run Example Files

We provide ready-to-run example files in the `examples/` folder. These are perfect for learning!

### Available Examples

```bash
# 1. Simple SMA Crossover (BEGINNER)
python examples/example_simple_sma.py

# 2. ATR Trailing Stops (INTERMEDIATE)
python examples/example_with_atr_stops.py

# 3. Position Sizing Comparison (ADVANCED)
python examples/example_with_position_sizing.py

# 4. FTMO Challenge (ADVANCED)
python examples/example_ftmo_challenge.py

# 5. Create Your Own Strategy (TEMPLATE)
python examples/example_custom_strategy.py
```

### What Each Example Teaches

| Example | You'll Learn |
|---------|--------------|
| **example_simple_sma.py** | Basic strategy structure, signal generation, simple backtesting |
| **example_with_atr_stops.py** | ATR-based stops, trailing stops, position sizing, risk management |
| **example_with_position_sizing.py** | 3 sizing methods (Fixed%, Kelly, Volatility), comparing results |
| **example_ftmo_challenge.py** | FTMO rules, compliance checking, prop firm trading |
| **example_custom_strategy.py** | Create your own strategy from scratch, template to copy |

### Modify and Experiment

All examples are **well-commented** and **easy to modify**. Try changing:

- Strategy parameters (periods, thresholds, multipliers)
- Data files (test on different assets)
- Risk management settings
- Entry/exit conditions

---

## Method 3: Run Quick Start Workflow

The `quick_start.py` script demonstrates the **complete Strategy Factory workflow**:

```bash
python quick_start.py
```

This will:

1. ✅ Load BTCUSD 5-minute data
2. ✅ Generate 96 strategies (SMA, RSI, Breakout variations)
3. ✅ Test all strategies
4. ✅ Rank by Sharpe ratio
5. ✅ Validate best strategy out-of-sample
6. ✅ Generate performance report

**Output:**
- Top 10 strategies printed to console
- Validation results
- Performance metrics

**Good for:** Understanding the full workflow, mass strategy testing

---

## Method 4: Run Strategy Scripts Directly

Some strategies have built-in `if __name__ == "__main__"` blocks for direct execution.

### Strategies You Can Run Directly

```bash
# ATR Trailing Stop Strategy
python strategies/atr_trailing_stop_strategy.py

# FTMO Challenge Strategy
python strategies/ftmo_challenge_strategy.py

# Advanced Strategy Template
python strategies/advanced_strategy_template.py
```

### How It Works

These files contain example usage at the bottom:

```python
if __name__ == "__main__":
    # Load data
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    # ... setup ...

    # Create strategy
    strategy = ATRTrailingStopStrategy(...)

    # Run backtest
    portfolio = strategy.backtest(df)

    # Print results
    strategy.print_results(portfolio)
```

You can **modify these parameters directly** in the file before running.

---

## Method 5: Create Custom Python Scripts

The most flexible method - create your own script!

### Template

Create a file called `my_test.py`:

```python
import pandas as pd
import vectorbt as vbt
from strategies.sma_crossover import SMAStrategy

# 1. Load data
df = pd.read_csv('data/crypto/BTCUSD_5m.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

# 2. Create strategy
strategy = SMAStrategy(fast_period=10, slow_period=50)

# 3. Generate signals
df_signals = strategy.generate_signals(df)

# 4. Run backtest
entries = (df_signals['signal'] == 'BUY')
exits = (df_signals['signal'] == 'SELL')

portfolio = vbt.Portfolio.from_signals(
    close=df['close'].values,
    entries=entries,
    exits=exits,
    init_cash=10000,
    fees=0.001
)

# 5. Print results
print(f"Total Return: {portfolio.total_return() * 100:.2f}%")
print(f"Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
print(f"Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")
```

Then run:

```bash
python my_test.py
```

### Advanced Example with Risk Management

```python
import pandas as pd
import vectorbt as vbt
from strategies.atr_trailing_stop_strategy import ATRTrailingStopStrategy
from strategy_factory.analyzer import StrategyAnalyzer

# Load data
df = pd.read_csv('data/crypto/BTCUSD_5m.csv')
df.columns = df.columns.str.lower()
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')

# Create strategy with custom parameters
strategy = ATRTrailingStopStrategy(
    atr_period=14,
    atr_sl_multiplier=2.5,  # Wider stops
    atr_tp_multiplier=5.0,  # Higher targets
    risk_percent=1.0
)

# Run backtest
portfolio = strategy.backtest(df, initial_capital=50000)

# Generate full report
analyzer = StrategyAnalyzer()
returns = portfolio.returns()

# Get metrics
metrics = analyzer.get_key_metrics(returns)
analyzer.print_metrics(metrics)

# Generate HTML report
report_path = analyzer.generate_full_report(
    returns,
    output_file='my_strategy_report.html',
    title='My Custom Backtest'
)

print(f"\nReport: {report_path}")
```

---

## Advanced: Jupyter Notebooks

For **interactive development** and **visualization**, use Jupyter notebooks.

### Start Jupyter

```bash
jupyter notebook
```

Then open:

- `notebooks/01_strategy_generation.ipynb` - Mass strategy generation
- `notebooks/02_strategy_optimization.ipynb` - Parameter optimization

### Notebook Workflow

Notebooks let you:

- ✅ Run code cells one at a time
- ✅ See charts and visualizations inline
- ✅ Experiment with parameters interactively
- ✅ Save your work as you go

**Good for:** Research, experimentation, creating visualizations

---

## Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'vectorbt'`

**Solution:** Install dependencies

```bash
# If using virtual environment
venv/bin/pip install vectorbt quantstats deap

# Or regular pip
pip install vectorbt quantstats deap
```

### Problem: `FileNotFoundError: data/crypto/BTCUSD_5m.csv`

**Solution:** Check data file exists

```bash
# List available data
ls data/crypto/

# If missing, check if ADA or other data exists
python run_strategy.py --strategy sma --data data/crypto/ADAUSD_5m.csv
```

### Problem: Strategy shows 0 trades or inf Sharpe

**Possible causes:**

1. **Not enough data:** Use more bars (increase data size)
2. **Parameters too strict:** Relax entry conditions
3. **Look-ahead bias:** Make sure signals use `.shift(1)` to avoid future data

**Debug:**

```python
# Check if signals are generated
df_signals = strategy.generate_signals(df)
print((df_signals['signal'] == 'BUY').sum())  # Should be > 0
print((df_signals['signal'] == 'SELL').sum())

# Check signal timing
print(df_signals[df_signals['signal'].notna()][['close', 'signal']].head(10))
```

### Problem: `KeyError: 'close'`

**Solution:** Data columns must be lowercase

```python
# Fix column names
df.columns = df.columns.str.lower()

# Verify required columns exist
print(df.columns)  # Should have: open, high, low, close, volume
```

### Problem: Backtest too slow

**Solutions:**

```python
# 1. Use fewer bars
df = df.tail(50000)  # Last 50k bars only

# 2. Use resampling (5min → 15min)
df = df.resample('15min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# 3. Use vectorbt's fast mode (already default in our system)
```

---

## FAQ

### Q: Which method should I use as a beginner?

**A:** Start with **Method 1** (Universal Runner) or **Method 2** (Example Files).

```bash
# Easiest - just run this
python run_strategy.py --strategy sma

# Or run a commented example
python examples/example_simple_sma.py
```

### Q: How do I test my own strategy idea?

**A:** Use the custom strategy template:

```bash
# 1. Copy the template
cp examples/example_custom_strategy.py my_strategy.py

# 2. Edit the MyCustomStrategy class with your logic

# 3. Run it
python my_strategy.py
```

### Q: How do I generate a detailed report?

**A:** Add `--report` flag:

```bash
python run_strategy.py --strategy atr_trailing_stop --report
```

This creates an HTML file in `results/analysis_reports/` with:
- Performance metrics
- Equity curve charts
- Drawdown analysis
- Monthly returns heatmap
- Trade statistics

### Q: Can I test on different data files?

**A:** Yes! Use `--data` parameter:

```bash
python run_strategy.py --strategy sma --data data/crypto/ADAUSD_5m.csv
python run_strategy.py --strategy rsi --data data/crypto/XAUUSD_5m.csv
```

### Q: How do I optimize strategy parameters?

**A:** Use the optimizer module:

```python
from strategy_factory.optimizer import StrategyOptimizer
from strategies.sma_crossover import SMAStrategy

optimizer = StrategyOptimizer()

best_params, best_portfolio = optimizer.optimize_genetic(
    strategy_class=SMAStrategy,
    df=df,
    param_ranges={
        'fast_period': (5, 20),
        'slow_period': (30, 100)
    },
    population_size=50,
    generations=20
)

print(f"Best params: {best_params}")
print(f"Sharpe: {best_portfolio.sharpe_ratio(freq='5min'):.2f}")
```

### Q: How do I add ATR stops to my strategy?

**A:** Import risk management utilities:

```python
from strategy_factory.risk_management import RiskCalculator, PositionSizer

# In your generate_signals() method:
df['atr'] = RiskCalculator.calculate_atr(df, period=14)
df['stop_loss'] = df['close'] - df['atr'] * 2.0
df['take_profit'] = df['close'] + df['atr'] * 4.0

# Position sizing
df['position_size'] = PositionSizer.fixed_percent_risk(
    account_balance=10000,
    risk_percent=1.0,
    stop_distance=df['atr'] * 2.0
)

# In your backtest:
portfolio = vbt.Portfolio.from_signals(
    close=close,
    entries=entries,
    exits=exits,
    size=df['position_size'].values,
    sl_stop=df['stop_loss'].values,
    sl_trail=True,  # Enable trailing stops!
    tp_stop=df['take_profit'].values,
    high=high,
    low=low
)
```

See [ADVANCED_FEATURES_GUIDE.md](ADVANCED_FEATURES_GUIDE.md) for complete examples.

### Q: How do I test FTMO compliance?

**A:** Use the FTMO strategy:

```bash
# Quick test
python run_strategy.py --strategy ftmo_challenge --challenge-size 50k

# Detailed analysis
python examples/example_ftmo_challenge.py
```

Or add FTMO checking to any strategy:

```python
from strategy_factory.risk_management import FTMOChecker

ftmo_checker = FTMOChecker(challenge_size='50k')

# After backtest
equity_curve = portfolio.value()
trade_dates = portfolio.trades.records_readable['Entry Timestamp']

ftmo_results = ftmo_checker.check_all_rules(
    equity_curve=equity_curve,
    trade_dates=pd.to_datetime(trade_dates)
)

if ftmo_results['challenge_passed']:
    print("✅ PASSED FTMO Challenge!")
else:
    print(f"❌ FAILED: {ftmo_results['summary']}")
```

### Q: How do I compare multiple strategies?

**A:** Use the analyzer's comparison method:

```python
from strategy_factory.analyzer import StrategyAnalyzer
from strategies.sma_crossover import SMAStrategy
from strategies.rsi_strategy import RSIStrategy

analyzer = StrategyAnalyzer()

# Run multiple strategies
strategies = {
    'SMA_10_50': SMAStrategy(10, 50),
    'SMA_20_100': SMAStrategy(20, 100),
    'RSI_14': RSIStrategy(14, 30, 70)
}

results = {}
for name, strategy in strategies.items():
    df_signals = strategy.generate_signals(df)
    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000
    )

    results[name] = portfolio.returns()

# Compare
comparison_df = analyzer.compare_strategies(results)
print(comparison_df)
```

### Q: What's the difference between backtesting and live trading?

**A:**

| Backtesting (Development) | Live Trading (Production) |
|---------------------------|---------------------------|
| Uses historical data | Uses real-time data |
| Instant results | Real-time execution |
| /strategies folder | /deployment folder |
| Testing and development | Real money trading |
| `run_strategy.py` | `live_trader.py` |

**This guide covers backtesting only.** For live trading, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

---

## Next Steps

### After Running Your First Strategy

1. ✅ **Understand the results** - Look at return, Sharpe, drawdown, win rate
2. ✅ **Generate a report** - Add `--report` to see detailed analysis
3. ✅ **Modify parameters** - Change periods, thresholds, see what improves
4. ✅ **Try different data** - Test on other assets/timeframes
5. ✅ **Add risk management** - Implement stops, position sizing
6. ✅ **Optimize parameters** - Use genetic algorithm to find best settings
7. ✅ **Walk-forward test** - Validate on out-of-sample data
8. ✅ **Create your own strategy** - Start with `example_custom_strategy.py`

### Learn More

- **Advanced Features:** [ADVANCED_FEATURES_GUIDE.md](ADVANCED_FEATURES_GUIDE.md)
- **Quick Reference:** [ADVANCED_FEATURES_SUMMARY.md](ADVANCED_FEATURES_SUMMARY.md)
- **Getting Started:** [GETTING_STARTED.md](GETTING_STARTED.md)
- **Implementation Plan:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

### Need Help?

- Check example files in `/examples` - they're well-commented!
- Read strategy files in `/strategies` - they show best practices
- Review notebooks in `/notebooks` - interactive learning

---

## Summary: Which Method to Use When

| When You Want To... | Use This Method | Command |
|---------------------|-----------------|---------|
| **Quick test of any strategy** | Universal Runner | `python run_strategy.py --strategy sma` |
| **Learn by example** | Example Files | `python examples/example_simple_sma.py` |
| **See full workflow** | Quick Start | `python quick_start.py` |
| **Modify strategy directly** | Strategy Scripts | `python strategies/ftmo_challenge_strategy.py` |
| **Maximum flexibility** | Custom Scripts | `python my_custom_test.py` |
| **Interactive development** | Notebooks | `jupyter notebook` |
| **Mass testing** | Generator | Import and use `StrategyGenerator` |
| **Parameter optimization** | Optimizer | Import and use `StrategyOptimizer` |

---

**Ready to start?** Try this command now:

```bash
python run_strategy.py --strategy atr_trailing_stop --report
```

This will run a professional strategy with ATR stops and generate a beautiful report!

---

*Last updated: 2025*
*Strategy Factory - Professional Trading Strategy Development System*
