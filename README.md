# London Breakout v3 - Enhanced Trailing Stop Strategy

🎯 **54.4% Win Rate** | 📈 **Sharpe 2.65** | 💰 **$1,978/year** | 📉 **Max DD -1.69%**

Professional London Session Breakout strategy with advanced stepped trailing stop logic.

---

## 🚀 Quick Start

```bash
# Run backtest
python run_strategy.py

# Generate full report with charts
python run_strategy.py --report

# View interactive report
open output/london_breakout/tearsheet.html
```

---

## 📊 Performance Highlights (2020-2025)

| Metric | Value |
|--------|-------|
| **Win Rate** | 54.4% |
| **Sharpe Ratio** | 2.65 |
| **Sortino Ratio** | 4.60 |
| **Calmar Ratio** | 5.51 |
| **Max Drawdown** | -1.69% |
| **CAGR** | 9.33% |
| **Profit Factor** | 1.50 |
| **Annual P&L** | $1,978 |
| **Trades/Year** | 52 |

---

## 🎯 Strategy Overview

### London Session Breakout
Trades breakouts from the Asian session range when London opens (3-4 AM EST).

**Entry Logic:**
1. ✅ Asia range 15-60 pips
2. ✅ H4 trend alignment (no counter-trend)
3. ✅ First hour momentum (≥15 pips bullish/bearish candle)
4. ✅ Breakout buffer (2 pips beyond Asia high/low)
5. ✅ Timing (only 3-4 AM entries)

**Exit Logic:**
- **Take Profit**: 1.3× risk OR 2× ATR (min 25 pips)
- **Enhanced Stepped Trailing Stop** ⭐ NEW:
  - At 1.0R: Move to breakeven + 2 pips
  - At 1.5R: Lock in 0.75R profit
  - At 2.0R: Lock in 1.5R profit
  - At 2.5R+: Trail at 0.5R distance
- **Time Exit**: Close at London close (12 PM)

---

## 📁 Project Structure

```
.
├── run_strategy.py          # Main entry point
├── requirements.txt
│
├── strategies/              # Trading strategies
│   ├── strategy_breakout_v3.py        ⭐ Main strategy
│   ├── strategy_breakout_v3_usdjpy.py
│   └── strategy_optimizer.py
│
├── core/                    # Core modules
│   ├── data_loader.py       # Data loading
│   ├── indicators.py        # Technical indicators
│   └── session_manager.py   # Session detection
│
├── backtests/              # Backtesting tools
│   ├── backtest_report.py   # Report generator
│   ├── monte_carlo_backtest.py
│   └── backtest_balanced_portfolio.py
│
├── utils/                  # Utilities
│   ├── ftmo_risk_manager.py
│   ├── ftmo_challenge_simulator.py
│   ├── portfolio_manager.py
│   └── multi_strategy_portfolio.py
│
├── data/                   # Market data
│   └── forex/
│
├── output/                 # Generated reports
│   └── london_breakout/
│       ├── tearsheet.html   # Interactive report
│       ├── equity_curve.png
│       ├── monthly_returns.png
│       └── rolling_metrics.png
│
└── docs/                   # Documentation
    ├── QUICK_START.md
    ├── STRATEGY_V3_FINAL_REPORT.md
    └── FTMO_STRATEGY_SUMMARY.md
```

---

## 🔑 Key Innovation: Stepped Trailing Stop

The **v3 enhancement** is a sophisticated trailing stop that protects profits progressively:

### Traditional Approach (v2)
- Move to breakeven at 50% to target
- Win rate: 49.2%, Profit: $1,738/year

### Enhanced Stepped Trail (v3)
- **1.0R**: Breakeven + 2 pips
- **1.5R**: Lock 75% profit
- **2.0R**: Lock 150% profit
- **2.5R+**: Dynamic trail at 0.5R distance

### Results
- **Win rate: 54.4%** (+5.2% improvement!)
- **Profit: $1,978/year** (+14% increase)
- **77% exits via SL** but averaging only **-$17.82** (many are profitable)

The trailing stop converts borderline trades into wins while letting runners exceed the initial 1.3R target.

---

## 📈 Exit Reason Analysis

| Exit | Count | % | Avg P&L |
|------|-------|---|---------|
| **SL** | 230 | 77% | **-$17.82** ⭐ |
| **TP** | 63 | 21% | $244.23 |
| **Time** | 5 | 2% | $11.00 |

**Key Insight**: 77% SL exits with only -$17.82 average means the trailing stop is **locking in profits** even on "stopped out" trades.

---

## 🛡️ Risk Management

- **Stop Loss**: 60% of Asia range (max 40 pips)
- **Position Size**: $10/pip (1 standard lot)
- **Max Drawdown**: -1.69% (excellent control)
- **Daily Risk**: Very low volatility
- **Commission**: $5 per trade
- **Slippage**: 0.5 pips

---

## 🔧 Installation

```bash
# Clone repository
git clone <repo-url>
cd 02_MT5_statarb

# Install dependencies
pip install -r requirements.txt

# Run backtest
python run_strategy.py
```

---

## 📚 Documentation

- [QUICK_START.md](docs/QUICK_START.md) - Getting started guide
- [STRATEGY_V3_FINAL_REPORT.md](docs/STRATEGY_V3_FINAL_REPORT.md) - Detailed analysis
- [FTMO_STRATEGY_SUMMARY.md](docs/FTMO_STRATEGY_SUMMARY.md) - FTMO integration

---

## 🎓 For Live Trading

### Prerequisites
1. EUR/USD H1 data feed
2. MetaTrader 5 or compatible broker
3. VPS for reliable execution

### Recommended Steps
1. **Paper trade 2-4 weeks** - Validate execution
2. **Monitor live signals** - Compare with backtest
3. **Start with 0.5R risk** - Conservative entry
4. **Scale up gradually** - After 20+ successful trades
5. **Trust the process** - Strong historical performance

---

## ⚠️ Disclaimer

This system is for educational purposes. Past performance does not guarantee future results. Trading involves substantial risk of loss. Always test thoroughly on demo before live trading.

---

## 📞 Support

- **Issues**: Report bugs via GitHub
- **Documentation**: See `docs/` folder
- **Code**: Fully commented Python files

---

**Version**: 3.0 (Enhanced Trailing Stop)
**Backtest Period**: 2020-2025
**Status**: ✅ Production-Ready
