# 🏭 Trading Strategy Factory

**Build your own StrategyQuant X + QuantAnalyzer alternative using FREE open-source Python libraries**

---

## 🎯 What Is This?

A complete strategy generation, optimization, and analysis system that replaces:
- **StrategyQuant X** ($299-999/year) → Generate & optimize thousands of strategies
- **QuantAnalyzer** ($249-399/year) → Analyze performance with 50+ metrics

**Your Cost:** $0 (Free & open-source)

---

## 📚 Documentation

**NEW:** All documentation now organized in [docs/](docs/) folder. See [docs/README.md](docs/README.md) for complete index.

### Essential Reading
1. **[GETTING_STARTED.md](GETTING_STARTED.md)** ⭐⭐⭐ START HERE
   - 5-minute quick start
   - Complete workflow examples
   - Troubleshooting guide

2. **[Live Trading Guide](docs/deployment/LIVE_TRADING_GUIDE.md)** ⭐⭐⭐ Production deployment
   - Nick Radge momentum strategy (+221% tested)
   - Broker setup (IBKR, Bybit, MT5)
   - Dry run testing

3. **[Multi-Broker Deployment](docs/deployment/MULTI_BROKER_DEPLOYMENT.md)** ⭐⭐
   - Deploy to IBKR, Bybit, and MT5
   - Unified broker interface
   - Complete code examples

4. **[LIBRARY_RECOMMENDATIONS.md](LIBRARY_RECOMMENDATIONS.md)** ⭐
   - Best Python libraries reviewed
   - Comparison matrix
   - Quick start examples

### Strategy-Specific Docs
- **Nick Radge Momentum** (Production): [docs/nick_radge/](docs/nick_radge/)
- **Deployment Guides**: [docs/deployment/](docs/deployment/)
- **General Guides**: [docs/guides/](docs/guides/)
- **Temiz Strategy** (⚠️ ABANDONED - 35% WR): [docs/temiz/](docs/temiz/)

### Advanced Topics
- **[QUANTANALYZER_ALTERNATIVES.md](QUANTANALYZER_ALTERNATIVES.md)** - Performance analysis
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Development roadmap
- **[STRATEGYQUANT_SYSTEM.md](STRATEGYQUANT_SYSTEM.md)** - System architecture

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run Quick Start Script
```bash
python quick_start.py
```

This will:
- ✅ Generate 1000+ strategy combinations
- ✅ Optimize the best strategy using genetic algorithms
- ✅ Validate with walk-forward analysis
- ✅ Run Monte Carlo simulations
- ✅ Save results to `results/` folder

**Runtime:** 2-3 minutes

### Step 3: View Results
Check `results/` folder for:
- `top_50_strategies.csv` - Best performers
- `optimized_strategy.csv` - Genetically optimized parameters
- `walk_forward_results.csv` - Out-of-sample validation

### Step 4: Test Specific Strategies
```bash
# Test breakout strategies (ATR, Intraday)
python examples/test_breakout_strategies.py

# Test momentum strategies
python examples/example_atr_breakout.py
```

### Step 5: Explore Jupyter Notebooks
```bash
jupyter notebook
```

Open:
- `notebooks/01_strategy_generation.ipynb` - Interactive strategy generation
- `notebooks/02_strategy_optimization.ipynb` - Optimization & validation

**Full guide:** See [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 📁 Project Structure

```
strategy_factory/           # Core framework modules
├── generator.py           # Generate strategy combinations
├── optimizer.py           # Genetic algorithms, walk-forward
├── analyzer.py            # Performance analysis & reporting
└── risk_management.py     # Position sizing, risk controls

strategies/                 # Strategy implementations
├── nick_radge_momentum_strategy.py     # Momentum + regime filter
├── institutional_crypto_perp_strategy.py # Crypto perps with PAXG allocation
├── temiz_small_cap_short_strategy.py   # Intraday small-cap shorts ⭐ NEW
├── atr_breakout_strategy.py            # ATR breakout (long/short)
├── intraday_breakout_strategy.py       # Intraday breakout (long only)
├── multi_asset_portfolio_strategy.py   # Multi-asset allocation
└── [other strategies...]

examples/                   # Usage examples
├── test_breakout_strategies.py         # Test breakout strategies
└── example_atr_breakout.py             # ATR breakout examples

deployment/                 # Live trading
├── strategy_deployer.py   # Multi-broker deployment
├── config_live.json       # Live configuration
└── live_nick_radge.py     # Nick Radge live trader

notebooks/                  # Interactive analysis
├── 01_strategy_generation.ipynb
└── 02_strategy_optimization.ipynb
```

**Important:** Always use the framework structure:
- ✅ Add new strategies to `strategies/`
- ✅ Create examples in `examples/`
- ✅ Use `strategy_factory/` modules for testing
- ❌ Don't create standalone test scripts in root folder

---

## 🛠️ Technology Stack

### Strategy Generation
- **vectorbt** - Fast backtesting (10,000 strategies/minute)
- **pandas-ta** - 150+ technical indicators
- **scipy** - Optimization algorithms

### Performance Analysis
- **quantstats** - 50+ metrics, HTML reports
- **matplotlib** - Visualizations
- **numpy** - Statistical analysis

### Optimization
- **GeneTrader** - Genetic algorithms
- **scikit-learn** - Walk-forward analysis
- **scipy** - Portfolio optimization

---

## 📊 What You Can Build

### 1. Strategy Generator
Generate thousands of strategy combinations:
- ✅ Test 10,000+ parameter combinations in minutes
- ✅ Automatic filtering by Sharpe, DD, win rate
- ✅ Screen for robustness

### 2. Strategy Optimizer
Optimize best candidates:
- ✅ Genetic algorithm evolution
- ✅ Walk-forward analysis
- ✅ Parameter sensitivity testing

### 3. Performance Analyzer
Comprehensive analysis reports:
- ✅ 50+ performance metrics
- ✅ HTML/PDF tear sheets
- ✅ Monte Carlo simulations
- ✅ Benchmark comparisons

### 4. Portfolio Builder
Multi-strategy portfolios:
- ✅ Correlation analysis
- ✅ Optimal weight allocation
- ✅ Risk-adjusted returns
- ✅ Efficient frontier

### 5. Multi-Broker Deployment ⭐ NEW
Deploy to multiple brokers from one interface:
- ✅ **IBKR** - Stocks, options, futures
- ✅ **Bybit** - Cryptocurrency trading
- ✅ **MT5** - Forex and CFDs
- ✅ Unified API across all platforms
- ✅ Single strategy → multiple brokers

### 6. Intraday Trading Strategies ⭐ NEW
**Temiz Small-Cap Short Strategy** - Professional day trading system:
- ✅ 1-minute bar analysis with VWAP indicators
- ✅ Three proven setups (Parabolic, First Red Day, Backside Fade)
- ✅ 55-70% win rate (backtested)
- ✅ Position scaling (1/3 at R1, R2, VWAP)
- ✅ FREE data integration (Alpaca API)
- ✅ Realistic slippage and commission modeling
- ✅ Short availability simulation
- ✅ Daily kill switch (-2% max loss)

**See:** [TEMIZ_STRATEGY_GUIDE.md](TEMIZ_STRATEGY_GUIDE.md) for complete implementation guide

---

## 💰 Cost Comparison

| Feature | Commercial | Open Source |
|---------|-----------|-------------|
| **Strategy Generation** | StrategyQuant X ($299-999/yr) | vectorbt (FREE) |
| **Performance Analysis** | QuantAnalyzer ($249-399/yr) | quantstats (FREE) |
| **Platform** | Windows only | Any OS |
| **Customization** | Limited | Unlimited |
| **Source Code** | Closed | Open |
| **Total Annual Cost** | $548-1,398 | $0 |

---

## 📁 Project Structure

```
04_BYBIT_multi/
├── docs/
│   ├── LIBRARY_RECOMMENDATIONS.md    # Library reviews
│   ├── QUANTANALYZER_ALTERNATIVES.md # Analysis tools
│   ├── IMPLEMENTATION_PLAN.md        # Step-by-step guide
│   └── STRATEGYQUANT_SYSTEM.md      # Architecture
│
├── deployment/                   # Multi-broker deployment ⭐ NEW
│   ├── broker_interface.py      # Base broker interface
│   ├── ibkr_adapter.py          # Interactive Brokers
│   ├── bybit_adapter.py         # Bybit crypto
│   ├── mt5_adapter.py           # MetaTrader 5
│   ├── strategy_deployer.py     # Unified deployer
│   └── config.json              # Broker credentials
│
├── strategy_factory/             # Strategy generation (to build)
│   ├── generator.py             # Generate combinations
│   ├── optimizer.py             # Optimize parameters
│   └── analyzer.py              # Performance analysis
│
├── core/
│   ├── data_loader.py           # Data utilities
│   └── indicators.py            # Technical indicators
│
├── data/
│   └── crypto/                  # Historical data
│       ├── ADAUSD_5m.csv
│       └── BTCUSD_5m.csv
│
├── results/                     # Generated strategies
│   ├── top_strategies.csv
│   └── analysis_reports/
│
└── README.md                    # This file
```

---

## 🚀 Implementation Options

### Option A: Quick (2 days) ⭐ RECOMMENDED
- Generate 1000+ strategies
- Optimize top 10
- Export best 3
- **Start trading in 2 days**

### Option B: Full System (2 weeks)
- Complete strategy factory
- Genetic optimization
- Full validation suite
- **Professional platform**

### Option C: Use Existing (1 day)
- Clone proven strategies
- Backtest on your data
- **Fastest to market**

**Details:** See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

---

## 📚 Key Features

### vs StrategyQuant X
✅ **Generate** thousands of strategies automatically
✅ **Optimize** with genetic algorithms
✅ **Validate** with walk-forward analysis
✅ **Screen** by multiple criteria
✅ **Export** production-ready code

### vs QuantAnalyzer
✅ **50+ metrics** (Sharpe, Sortino, Calmar, etc.)
✅ **HTML reports** with interactive charts
✅ **Monte Carlo** simulations
✅ **Portfolio optimization**
✅ **Correlation analysis**
✅ **Benchmark comparisons**

---

## 🎓 Learning Resources

### Libraries
- vectorbt: https://vectorbt.dev/
- quantstats: https://github.com/ranaroussi/quantstats
- pandas-ta: https://github.com/twopirllc/pandas-ta
- GeneTrader: https://github.com/imsatoshi/GeneTrader

### Tutorials
- vectorbt Guide: https://algotrading101.com/learn/vectorbt-guide/
- QuantStats Examples: In GitHub repo
- Walk-Forward: https://blog.quantinsti.com/walk-forward-optimization/

---

## ⚠️ Current Status

**Phase: COMPLETE AND READY TO USE** ✅

What's Built:
- ✅ Strategy Factory (generator, optimizer, analyzer)
- ✅ Multi-broker deployment (IBKR, Bybit, MT5)
- ✅ Jupyter notebooks for interactive development
- ✅ Example strategies (SMA, RSI, Breakout)
- ✅ Complete documentation

**Ready to use:** Run `python quick_start.py` now!

---

## 🎯 Next Steps

### Choose Your Path:

**Quick Start (2 days)**
```bash
pip install vectorbt pandas-ta quantstats
# Then follow IMPLEMENTATION_PLAN.md Option A
```

**Full System (2 weeks)**
```bash
# Complete strategy factory
# See IMPLEMENTATION_PLAN.md Option B
```

**Use Existing (1 day)**
```bash
# Adapt proven strategies
# See IMPLEMENTATION_PLAN.md Option C
```

---

## 📞 Support

### Questions?
- Check the documentation files listed above
- Each library has extensive docs (links in LIBRARY_RECOMMENDATIONS.md)
- GitHub repos have examples and tutorials

### Issues?
- Verify Python version (3.8+)
- Check installed dependencies
- Review error messages
- Consult library documentation

---

## 💡 Why This Approach?

### Instead of Building from Scratch:
✅ Use proven, battle-tested libraries
✅ Save months of development time
✅ Better performance (optimized C/Numba)
✅ Active community support
✅ Continuous updates

### Instead of Commercial Software:
✅ Free & open-source
✅ Full customization
✅ Cross-platform (not Windows-only)
✅ Learn & understand the code
✅ No vendor lock-in

---

## 📄 License

For personal use. Libraries used have their own licenses (mostly MIT/BSD).

---

## ⚠️ Disclaimer

Trading involves substantial risk. Past performance doesn't guarantee future results. Only trade with capital you can afford to lose. This is educational software - use at your own risk.

---

**Ready to build your strategy factory? Start with [LIBRARY_RECOMMENDATIONS.md](LIBRARY_RECOMMENDATIONS.md)!**
