# Strategy Factory Integration - Proper Testing Workflow

**Date:** 2025-10-12

---

## Problem Statement

During crypto quarterly rebalancing research, standalone backtest scripts were created:
- `test_quarterly_rebalance_crypto.py`
- `test_universe_selection_criteria.py`
- `test_pure_selection_criteria.py`

**This violated the project architecture** by duplicating framework functionality instead of using the Strategy Factory framework.

---

## Solution: Proper Framework Integration

### ✅ What Was Added

**1. New StrategyGenerator Method**
- Location: [strategy_factory/generator.py](../strategy_factory/generator.py)
- Method: `generate_crypto_momentum_strategies()`
- Purpose: Test crypto strategies with different universe selection and rebalancing approaches

**Features:**
- Supports multiple universe types: `'fixed'`, `'roc_momentum'`, `'relative_strength'`
- Tests different rebalancing frequencies: `'quarterly'`, `'monthly'`, `'annual'`, `'none'`
- Varies portfolio size: number of positions
- Returns sorted results by Sharpe ratio
- Integrates with existing framework methods (`filter_strategies()`, etc.)

**2. Updated Strategy Docstring**
- Location: [strategies/05_institutional_crypto_perp.py](../strategies/05_institutional_crypto_perp.py)
- Added: Universe selection research findings
- Documents: Why fixed universe is used (not quarterly rebalancing)
- References: Analysis documents in `results/crypto/`

**3. Example Script**
- Location: [examples/example_crypto_strategy_generator.py](../examples/example_crypto_strategy_generator.py)
- Demonstrates: Proper use of StrategyGenerator
- Shows: How to compare fixed vs dynamic universe approaches
- Includes: Quality filtering and result saving

---

## The Correct Workflow

### Step 1: Use StrategyGenerator (Not Standalone Scripts)

```python
from strategy_factory.generator import StrategyGenerator

generator = StrategyGenerator(initial_capital=100000, commission=0.001)

# Test multiple parameter combinations
results = generator.generate_crypto_momentum_strategies(
    prices=crypto_prices,
    universe_type='fixed',
    roc_periods=[60, 90, 100],
    rebalance_freq=['quarterly', 'monthly'],
    num_positions=[5, 7],
    verbose=True
)

# Get top 10 configurations
print(results.head(10))
```

### Step 2: Filter by Quality Criteria

```python
# Apply quality filters
filtered = generator.filter_strategies(
    results=results,
    min_sharpe=1.0,
    max_drawdown=30.0,
    min_trades=20,
    min_win_rate=0.45
)
```

### Step 3: Validate with StrategyOptimizer

```python
from strategy_factory.optimizer import StrategyOptimizer

optimizer = StrategyOptimizer()

# Walk-forward validation
walk_forward_results = optimizer.walk_forward_validation(
    strategy_class=InstitutionalCryptoPerp,
    prices=crypto_prices,
    train_period='3Y',
    test_period='1Y'
)

# Monte Carlo simulation
monte_carlo_results = optimizer.monte_carlo_simulation(
    returns=strategy_returns,
    num_simulations=1000
)
```

### Step 4: Analyze with StrategyAnalyzer

```python
from strategy_factory.analyzer import StrategyAnalyzer

analyzer = StrategyAnalyzer()

# Generate full tearsheet
analyzer.generate_tearsheet(
    portfolio=portfolio,
    prices=crypto_prices,
    output_path='results/crypto/tearsheet.html'
)
```

---

## Architecture Comparison

### ❌ WRONG: Standalone Scripts

```
root/
├── test_quarterly_rebalance_crypto.py    # Duplicates framework
├── test_universe_selection_criteria.py   # Custom backtest logic
└── test_pure_selection_criteria.py       # Not reusable
```

**Problems:**
- Code duplication
- Not reusable
- Can't leverage framework features (walk-forward, Monte Carlo, filtering)
- Clutters root directory
- Hard to maintain

### ✅ CORRECT: Framework Integration

```
strategy_factory/
├── generator.py                                    # Add methods here
│   └── generate_crypto_momentum_strategies()      # ← NEW
├── optimizer.py                                    # Walk-forward, Monte Carlo
└── analyzer.py                                     # Performance analysis

examples/
└── example_crypto_strategy_generator.py           # Usage example

strategies/
└── 05_institutional_crypto_perp.py                # Updated docstring
```

**Benefits:**
- Reusable across projects
- Consistent API
- Leverages all framework features
- Clean architecture
- Easy to maintain

---

## When to Use Each Approach

### Use StrategyGenerator When:
✅ Testing multiple parameter combinations
✅ Comparing different strategy configurations
✅ Need sorting/filtering by performance metrics
✅ Want to leverage framework features

**Example:**
```python
# Test 12 different configurations
results = generator.generate_crypto_momentum_strategies(
    prices=crypto_prices,
    roc_periods=[60, 90, 100],           # 3 options
    rebalance_freq=['quarterly', 'monthly'],  # 2 options
    num_positions=[5, 7]                      # 2 options
)
# Returns DataFrame with all 12 results sorted by Sharpe
```

### Use Strategy Class Directly When:
✅ Testing a single specific configuration
✅ Need full strategy complexity (pyramiding, stops, regime filter)
✅ Integrating with live trading
✅ Custom analysis beyond framework capabilities

**Example:**
```python
from strategies.institutional_crypto_perp import InstitutionalCryptoPerp

strategy = InstitutionalCryptoPerp(
    max_positions=10,
    donchian_period=20,
    adx_threshold=25
)

portfolio = strategy.backtest(prices=crypto_prices)
strategy.print_results(portfolio, crypto_prices)
```

### Use Standalone Scripts When:
✅ Quick one-off analysis
✅ Research/exploration phase
✅ Results won't be reused
✅ BUT: Put in `examples/` folder, NOT root

**Example:**
```python
# examples/explore_volatility_squeeze.py
# Quick test of volatility squeeze indicator
# Results documented, script archived
```

---

## Research Findings Integration

The quarterly rebalancing research (Oct 2025) is now properly documented:

**1. Analysis Documents** (Keep)
- `results/crypto/QUARTERLY_REBALANCING_ANALYSIS.md`
- `results/crypto/UNIVERSE_SELECTION_CRITERIA_ANALYSIS.md`
- These are valuable permanent documentation

**2. Test Scripts** (Archive)
- `examples/test_quarterly_rebalance_crypto.py`
- `examples/test_universe_selection_criteria.py`
- `examples/test_pure_selection_criteria.py`
- Keep for reference, but recommend using StrategyGenerator for future tests

**3. Framework Integration** (Use Going Forward)
- `strategy_factory/generator.py` - `generate_crypto_momentum_strategies()`
- `examples/example_crypto_strategy_generator.py` - Proper usage example

**Key Finding Documented:**
Fixed universe outperforms quarterly rebalancing by 3-25× for crypto due to:
- BTC/ETH persistent dominance (not temporary like stock sectors)
- Winner-take-all network effects
- Multi-year momentum persistence
- Forced turnover with no edge

---

## Summary

✅ **What was done right:**
- Comprehensive research with 6 selection methods tested
- Detailed analysis documents created
- Clear conclusions reached

❌ **What was wrong:**
- Used standalone scripts instead of framework
- Duplicated backtest logic
- Not reusable

✅ **What was fixed:**
- Added `generate_crypto_momentum_strategies()` to StrategyGenerator
- Updated InstitutionalCryptoPerp docstring with findings
- Created proper example script showing framework usage

🎯 **Going forward:**
- Use StrategyGenerator for parameter testing
- Use StrategyOptimizer for validation
- Use StrategyAnalyzer for reporting
- Put research scripts in `examples/` (not root)
- Document findings in strategy docstrings

---

## References

**Framework Files:**
- [strategy_factory/generator.py:422](../strategy_factory/generator.py#L422) - New crypto method
- [strategies/05_institutional_crypto_perp.py:27](../strategies/05_institutional_crypto_perp.py#L27) - Updated docstring
- [examples/example_crypto_strategy_generator.py](../examples/example_crypto_strategy_generator.py) - Usage example

**Research Documentation:**
- [results/crypto/QUARTERLY_REBALANCING_ANALYSIS.md](../results/crypto/QUARTERLY_REBALANCING_ANALYSIS.md)
- [results/crypto/UNIVERSE_SELECTION_CRITERIA_ANALYSIS.md](../results/crypto/UNIVERSE_SELECTION_CRITERIA_ANALYSIS.md)

**Project Guidelines:**
- [CLAUDE.md](../CLAUDE.md) - File organization rules (lines 38-106)
