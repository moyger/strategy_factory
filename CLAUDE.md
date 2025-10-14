# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Trading Strategy Factory** - a complete system for generating, optimizing, backtesting, and deploying quantitative trading strategies. It replaces commercial tools like StrategyQuant X ($299-999/year) and QuantAnalyzer ($249-399/year) using free open-source Python libraries.

**Core Purpose:** Generate thousands of strategy variations automatically, optimize them using genetic algorithms, validate with walk-forward analysis and Monte Carlo simulation, and deploy to multiple brokers (IBKR, Bybit, MT5).

## Commands

### Setup
```bash
# Install all dependencies
pip install -r requirements.txt

# Install live trading dependencies
pip install -r requirements_live.txt
```

### Running Strategies

```bash
# Quick start - Full automated workflow (2-3 min runtime)
python quick_start.py

# Test specific strategy types
python examples/test_breakout_strategies.py
python examples/example_atr_breakout.py

# Live trading (dry run mode by default)
python deployment/live_nick_radge.py

# Interactive analysis
jupyter notebook
# Then open: notebooks/01_strategy_generation.ipynb
```

### Testing Data
- Bitcoin 5-minute data: `data/crypto/BTCUSD_5m.csv`
- Stock universe defined in: `deployment/config_live.json`

## Architecture

### Three-Layer System Design

```
┌─────────────────────────────────────────────────┐
│  LAYER 1: Strategy Factory (Core Engine)       │
│  - strategy_factory/generator.py               │
│  - strategy_factory/optimizer.py               │
│  - strategy_factory/analyzer.py                │
│  - strategy_factory/risk_management.py         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 2: Strategy Implementations              │
│  - strategies/nick_radge_momentum_strategy.py   │
│  - strategies/atr_breakout_strategy.py          │
│  - strategies/intraday_breakout_strategy.py     │
│  - strategies/multi_asset_portfolio_strategy.py │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 3: Deployment (Live Trading)             │
│  - deployment/broker_interface.py               │
│  - deployment/ibkr_adapter.py                   │
│  - deployment/bybit_adapter.py                  │
│  - deployment/mt5_adapter.py                    │
│  - deployment/live_nick_radge.py                │
└─────────────────────────────────────────────────┘
```

### Key Design Patterns

**1. Unified Broker Interface**
- All brokers implement the same abstract interface (`broker_interface.py`)
- Order, Position, and Balance objects standardized across brokers
- Strategy signals (BUY/SELL/CLOSE) translated to broker-specific API calls

**2. Strategy Generator Pattern**
- `StrategyGenerator` tests parameter combinations using vectorized operations
- Generates 1000+ strategy variations in minutes (10,000 strategies/minute via vectorbt)
- Returns DataFrame sorted by Sharpe ratio with full metrics

**3. Genetic Optimization**
- `StrategyOptimizer` uses DEAP library for evolutionary optimization
- Supports walk-forward validation (rolling train/test windows)
- Monte Carlo simulation for confidence intervals

**4. Market Regime Filtering**
- 3-tier system: STRONG_BULL, WEAK_BULL, BEAR
- Based on SPY's 200-day and 50-day moving averages
- Dynamically adjusts portfolio size (7 → 3 → 0 positions) or switches to bear asset (GLD)

## Critical Implementation Details

### Nick Radge Momentum Strategy (Primary Production Strategy)

**Current Configuration** (`deployment/config_live.json`):
- **Portfolio Size:** 7 stocks from 50-stock universe
- **Momentum Ranking:** 100-day Rate of Change (ROC)
- **Regime Filter:** 3-tier based on SPY MAs (200/50-day)
- **Bear Market Asset:** GLD (Gold) with 100% allocation during BEAR regime
- **Rebalance:** Daily check at 09:35 AM (configurable via `rebalance_time`)
- **Dry Run:** Enabled by default (`"dry_run": true`)

**Why GLD?**
- Testing showed GLD 100% outperformed all alternatives:
  - GLD 100%: +228.56% (WINNER)
  - Cash: +177.61%
  - TLT: +109%
  - SH: +35-75%
  - SQQQ: -79% (catastrophic)

**Regime Logic:**
```python
if SPY > 200MA and SPY > 50MA:  # STRONG_BULL
    positions = 7
elif SPY > 200MA:  # WEAK_BULL
    positions = 3
else:  # BEAR
    positions = 0 (switch to GLD 100%)
```

### Breakout Strategies (Tomas Nesnidal)

**Two Implementations:**

1. **ATRBreakoutStrategy** (`strategies/atr_breakout_strategy.py`)
   - Original: Both long AND short positions
   - Uses POI (Point of Initiation) + k × ATR for entry
   - ADX filter: ADX >= threshold (trending markets)
   - Result on crypto: **Failed** (-55% to -107%) due to shorting bull market

2. **IntraDayBreakoutStrategy** (`strategies/intraday_breakout_strategy.py`)
   - Fixed: LONG ONLY
   - INVERTED ADX logic: ADX < threshold (consolidation breakouts)
   - Previous day's close as POI (for intraday trading)
   - Time window filters + end-of-day exits
   - Result on crypto: **+28-30%** (avoided short catastrophe)

**Important Finding:** These strategies are designed for **intraday futures** (YM emini Dow, 20-min bars), NOT 5-minute crypto. They work best with:
- Clear session structure (market open/close)
- Consolidation periods (overnight gaps)
- Mean reversion behavior

For crypto: Use Nick Radge Momentum instead.

## Data Flow

### Backtesting Workflow
```
1. Load data (yfinance, CSV, etc.)
   ↓
2. StrategyGenerator.generate_XXX_strategies()
   → Tests all parameter combinations
   → Returns DataFrame with metrics
   ↓
3. Filter by quality criteria
   → min_sharpe, max_drawdown, min_trades, min_win_rate
   ↓
4. StrategyOptimizer.optimize_XXX()
   → Genetic algorithm refinement
   → Walk-forward validation
   → Monte Carlo simulation
   ↓
5. Save results to results/ folder
   → top_50_strategies.csv
   → optimized_strategy.csv
   → walk_forward_results.csv
```

### Live Trading Workflow
```
1. Load config (deployment/config_live.json)
   ↓
2. Initialize broker adapter (IBKR/Bybit/MT5)
   ↓
3. Download market data (yfinance or broker API)
   ↓
4. Calculate strategy signals
   → NickRadgeMomentumStrategy.generate_allocations()
   → Returns target allocations for each ticker
   ↓
5. Calculate rebalancing orders
   → Compare current positions vs target
   → Generate buy/sell orders
   ↓
6. Execute orders (if not dry_run)
   → broker.place_order()
   ↓
7. Log results to deployment/logs/
```

## Risk Management: Position Stop-Loss System

**Nick Radge Crypto Hybrid Strategy (06_nick_radge_crypto_hybrid.py)** uses a **position-only stop-loss** system based on comprehensive backtest results (2020-2025).

### Configuration (DEFAULT)

```python
strategy = NickRadgeCryptoHybrid(
    portfolio_stop_loss=None,        # DISABLED (default)
    position_stop_loss=0.40,         # 40% stop on individual positions
    position_stop_loss_core_only=False  # Apply to ALL positions
)
```

### Why Position-Only Stops?

Backtest comparison over 2020-2025 (2,113 days including Trump tariff event):

| Configuration | Total Return | Max DD | Result |
|--------------|-------------|---------|---------|
| **Position-only (40%)** | **19,410%** | -48.35% | ✅ **OPTIMAL** |
| No stops | 19,137% | -48.44% | Baseline |
| Portfolio-only (30%) | 7,956% | -43.11% | -11,000% underperformance |
| Layered (both) | 8,156% | -43.11% | -11,000% underperformance |

**Key Finding:** Position stops actually **improved returns by +273%** vs baseline by cutting catastrophic losses early while letting winners run.

### Position Stops Caught (2020-2025)

8 catastrophic failures prevented:
- **SOL-USD:** -88.3% (stopped at -40%)
- **AVAX-USD:** -79.4%
- **DOT-USD:** -77.4%
- **ADA-USD:** -72.0% and -43.4% (twice)
- **ETH-USD:** -63.0%
- **BTC-USD:** -57.7%
- **DOGE-USD:** -42.8%

### Why Portfolio Stops Failed

Portfolio-level stops (30% from peak) caused:
- **43 trigger events** forcing 100% PAXG exits
- **328 days in cash** (15.5% of test period)
- **Missed major recoveries** after drawdowns
- **Excessive whipsawing** (-11,000% return cost)

**Conclusion:** Portfolio stops are too conservative for crypto's high volatility. Position stops provide better risk management by cutting individual losers without forcing full exits.

### Implementation Notes

- Position stops track entry price for EACH position
- Stop triggered when position drops >40% from entry
- Applies to both core (BTC/ETH/SOL) and satellite assets
- Independent of regime filter (runs in parallel)
- No cooldown or re-entry logic needed (position-specific)

## Important Configuration Files

**`deployment/config_live.json`** - Live trading configuration
- Strategy parameters (portfolio_size, roc_period, etc.)
- Stock universe (50 tickers)
- Regime filter settings
- Bear market asset (GLD)
- Dry run mode (ALWAYS start with `"dry_run": true`)

**`quick_start.py`** - Automated workflow script
- Loads BTCUSD 5min data by default
- Generates SMA, RSI, and Breakout strategies
- Runs full optimization pipeline
- Runtime: 2-3 minutes

## File Organization Rules

**CRITICAL:** Always follow this structure:

✅ **Correct:**
- New strategies → `strategies/NN_strategy_name.py` (numbered, e.g., `01_nick_radge_momentum.py`)
- Usage examples → `examples/example_your_strategy.py`
- Core framework → `strategy_factory/module.py`
- Live trading → `deployment/live_your_strategy.py`
- Documentation → `docs/category/GUIDE_NAME.md`
- Results → `results/strategy_name/`

❌ **Wrong:**
- **NEVER create standalone backtest scripts in root folder** (e.g., `test_strategy.py`, `backtest_XXX.py`)
- Hardcoded paths (use relative paths from project root)
- Standalone scripts that duplicate framework functionality
- Test scripts that don't use the strategy factory framework

**Why This Matters:**
- We have `strategy_factory/generator.py` and `strategy_factory/optimizer.py` for backtesting
- Strategies should have built-in `backtest()` methods
- Examples should go in `examples/` folder, not root
- Root folder is for core files only (README.md, CLAUDE.md, quick_start.py, requirements.txt)

**Strategy Numbering Convention:**
- `01-09` - Nick Radge momentum strategies (stocks)
- `10-19` - Crypto strategies
- `20-29` - ATR/Breakout strategies (intraday)
- `30-39` - Abandoned/experimental strategies
- `40-49` - Multi-asset portfolio strategies
- `50+` - Reserved for future strategies

**Example Pattern:**
```python
# In strategies/05_my_new_strategy.py
class MyNewStrategy:
    def __init__(self, params):
        self.params = params

    def generate_signals(self, prices):
        # Return entries/exits
        pass

    def backtest(self, prices, initial_capital=100000):
        # Use vectorbt (already part of framework)
        portfolio = vbt.Portfolio.from_signals(...)
        return portfolio

    def print_results(self, portfolio, prices):
        # Use strategy_factory.analyzer for consistent reporting
        from strategy_factory.analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()
        analyzer.print_performance(portfolio, prices)

# In examples/example_my_new_strategy.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies.my_new_strategy import MyNewStrategy

# Load data
df = pd.read_csv('data/crypto/BTCUSD_5m.csv')

# Test strategy using its built-in backtest method
strategy = MyNewStrategy(params)
portfolio = strategy.backtest(df)
strategy.print_results(portfolio, df)

# OR use strategy factory framework for bulk testing
from strategy_factory.generator import StrategyGenerator
generator = StrategyGenerator()
results = generator.generate_my_new_strategy_variations(df)
print(results.head(10))  # Top 10 parameter combinations
```

**If You Need to Test a Strategy:**
1. Check if strategy has built-in `backtest()` method → Use it
2. If testing multiple parameter combinations → Use `strategy_factory.generator`
3. If optimizing parameters → Use `strategy_factory.optimizer`
4. If validating robustness → Use walk-forward/Monte Carlo from framework
5. Put example in `examples/` folder, NOT root folder

## Dependencies and Library Choices

**Core Backtesting:**
- **vectorbt** - Fast vectorized backtesting (10,000 strategies/min)
- **pandas** - Data manipulation
- **numpy** - Numerical operations
- **quantstats** - Performance analysis (50+ metrics, HTML reports)

**Optimization:**
- **deap** - Genetic algorithms (used in StrategyOptimizer)
- **scipy** - Scientific computing

**Live Trading:**
- **ib_async** - Interactive Brokers (modern fork, use this NOT ib_insync)
- **ccxt** - Cryptocurrency exchanges (unified API for Bybit, Binance, etc.)
- **MetaTrader5** - MT5 API (Windows only)
- **yfinance** - Market data download

**Visualization:**
- **matplotlib** - Charts and plots
- **jupyter** - Interactive notebooks

## Common Pitfalls

1. **Overfitting:** Strategies optimized on in-sample data often fail out-of-sample
   - Always use walk-forward validation
   - Always run Monte Carlo simulation
   - Require min 100+ trades for statistical significance

2. **Look-Ahead Bias:** Using future data in calculations
   - All indicators must use `.shift(1)` for entry signals
   - Check that ROC, MA calculations don't peek ahead

3. **Survivorship Bias:** Testing only stocks that survived
   - Use point-in-time universes (not current S&P 500 for historical tests)
   - Nick Radge strategy uses a fixed 50-stock universe to mitigate this

4. **Data Issues:**
   - Yahoo Finance data has gaps/errors (use `df.dropna()`)
   - 5-minute crypto data is HUGE (27MB+, use last 6 months for testing)
   - Always check for MultiIndex columns from yfinance: `df.columns = df.columns.get_level_values(0)`

5. **Broker API Limitations:**
   - IBKR requires TWS/Gateway running on port 7496
   - MT5 Python API only works on Windows
   - Bybit has rate limits (check CCXT documentation)

## Strategy Factory Workflow Philosophy

The system is designed around **mass generation → filter → optimize → validate**:

1. **Generate thousands** of variations (brute force)
2. **Filter by quality** (Sharpe > 1.0, max DD < 20%, etc.)
3. **Optimize survivors** (genetic algorithms)
4. **Validate rigorously** (walk-forward + Monte Carlo)
5. **Deploy with confidence** (dry run first!)

This approach finds robust strategies that would be impossible to discover manually.

## Full Backtest Requirements

**CRITICAL:** When running a "full backtest" or "complete test", you MUST include ALL 4 components:

### 1. Performance Backtest ✅
- Run strategy on historical data (minimum 2+ years)
- Calculate all metrics (return, Sharpe, max DD, win rate, etc.)
- Save equity curve and trade log to `results/strategy_name/`

### 2. QuantStats Report ✅ (MANDATORY)
- Generate HTML tearsheet with 50+ metrics
- Include benchmark comparison (SPY)
- Drawdown analysis with underwater plot
- Rolling metrics (volatility, Sharpe, beta)
- Monthly/yearly returns heatmap
- Distribution plots
- Save to `results/strategy_name/quantstats_report.html`

```python
import quantstats as qs
qs.reports.html(
    strategy_returns,
    benchmark_returns,
    output='results/strategy_name/quantstats_report.html',
    title='Strategy Name - Full Report'
)
```

### 3. Walk-Forward Validation ✅ (MANDATORY)
- Test on rolling train/test windows
- Minimum 5+ folds (preferably 10+)
- Train period: ~3 years, Test period: 1 year
- Check consistency across time periods
- Save results to `results/strategy_name/walk_forward.csv`

**Purpose:** Ensures strategy works across different market conditions, not overfit to one period

### 4. Monte Carlo Simulation ✅ (MANDATORY)
- Resample trades with replacement (1000+ runs)
- Calculate confidence intervals (90% CI)
- Estimate probability of profit
- Identify worst-case scenarios
- Save results to `results/strategy_name/monte_carlo.csv`

**Purpose:** Quantifies uncertainty and tail risks

**If ANY of these 4 components are missing, the backtest is NOT complete.**

## Production Deployment Checklist

Before going live:

1. ✅ Test strategy on historical data (min 2+ years)
2. ✅ Walk-forward validation shows consistency
3. ✅ Monte Carlo shows >70% probability of profit
4. ✅ Tested in dry_run mode for 1+ weeks
5. ✅ Reviewed all logs (no errors/warnings)
6. ✅ Set position size limits (`max_position_size` in config)
7. ✅ Set up monitoring/alerts (Telegram bot recommended)
8. ✅ Document strategy parameters (version control config files)
9. ✅ Have kill switch ready (set `dry_run: true` to stop trading)

**Never skip dry_run mode on new strategies or configuration changes.**

## Performance Benchmarks

**Nick Radge Momentum + GLD (Production Strategy):**
- Total Return: +221.06% (2015-2024)
- Annualized: 23.47%
- Sharpe Ratio: 1.19
- Max Drawdown: -32.38%
- Win Rate: 63.0%
- Profit Factor: 4.50
- Outperformed SPY by +21.62%

**Key Success Factors:**
1. Momentum ranking (ROC) captures strongest trends
2. Regime filter (3-tier) protects in downturns
3. GLD allocation during BEAR regime (+50.96% improvement vs cash)
4. Quarterly rebalancing reduces transaction costs
5. Momentum weighting allocates more to winners

## When Adding New Strategies

1. Create strategy class in `strategies/`
2. Implement `generate_signals()` and `backtest()` methods
3. Add generator method to `strategy_factory/generator.py` if applicable
4. Create example in `examples/`
5. Test on historical data (min 1000+ bars)
6. Document parameters and expected use cases
7. Update this CLAUDE.md if strategy introduces new patterns

## Key Metrics to Track

- **Sharpe Ratio** - Risk-adjusted returns (aim for >1.5)
- **Max Drawdown** - Worst peak-to-trough decline (aim for <25%)
- **Profit Factor** - Gross wins / Gross losses (aim for >2.0)
- **Win Rate** - Percentage of winning trades (aim for >50%)
- **Trades per Year** - Liquidity (aim for >20 for significance)

Strategies with high Sharpe but few trades are likely overfit.
