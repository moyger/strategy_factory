# Documentation Index

All project documentation organized by topic.

## 📁 Directory Structure

```
docs/
├── temiz/              # Temiz small-cap short strategy (ABANDONED)
├── nick_radge/         # Nick Radge momentum strategy (PRODUCTION)
├── deployment/         # Live trading & broker setup
├── setup/              # Data sources & API setup
└── guides/             # General how-to guides
```

## 🎯 Quick Links by Topic

### Getting Started
- [Main README](../README.md) - Project overview
- [CLAUDE.md](../CLAUDE.md) - Instructions for Claude Code
- [How to Run Strategies](guides/HOW_TO_RUN_STRATEGIES.md)

### Live Trading (Production)
- **Nick Radge Momentum** - Primary strategy (+221% 2015-2024)
  - [Bear Market Trading](nick_radge/BEAR_MARKET_TRADING.md) - How regime filter works
  - [Bear Alternatives Report](nick_radge/BEAR_ALTERNATIVES_FINAL_REPORT.md) - Why we use GLD
  - [GLD Winner Report](nick_radge/GLD_WINNER_REPORT.md) - GLD vs alternatives
  - [Regime Comparison](nick_radge/REGIME_COMPARISON_CHART.md) - 3-tier regime system
  - [Bear Trading Test Results](nick_radge/BEAR_TRADING_TEST_RESULTS.md)
  - [Weak Bull Explanation](nick_radge/WEAK_BULL_EXPLANATION.md)

### Deployment & Brokers
- [Live Trading Guide](deployment/LIVE_TRADING_GUIDE.md) ⭐ Start here
- [Live Deployment Guide](deployment/LIVE_DEPLOYMENT_GUIDE.md)
- [Broker Setup Guide](deployment/BROKER_SETUP_GUIDE.md) - IBKR, Bybit, MT5
- [Multi-Broker Deployment](deployment/MULTI_BROKER_DEPLOYMENT.md) - Unified interface
- [Deployment Checklist](deployment/DEPLOYMENT_CHECKLIST.md) - Pre-launch checklist
- [Monitoring Guide](deployment/MONITORING_GUIDE.md) - Track live trades

### Data Sources & APIs
- [Alpaca Setup Guide](setup/ALPACA_SETUP_GUIDE.md) - FREE 1-min historical data

### General Guides
- [Advanced Features Guide](guides/ADVANCED_FEATURES_GUIDE.md)
- [Advanced Features Summary](guides/ADVANCED_FEATURES_SUMMARY.md)
- [How Capital Works](guides/HOW_CAPITAL_WORKS.md) - Position sizing
- [How Stock Selection Works](guides/HOW_STOCK_SELECTION_WORKS.md) - Momentum ranking
- [Portfolio Strategies Guide](guides/PORTFOLIO_STRATEGIES_GUIDE.md)
- [Quick Start ATR Qualifiers](guides/QUICK_START_ATR_QUALIFIERS.md)
- [Reports Guide](guides/REPORTS_GUIDE.md)

### Temiz Small-Cap Short Strategy (⚠️ ABANDONED - 35% WR, -0.57%)
- [Strategy Guide](temiz/TEMIZ_STRATEGY_GUIDE.md) - Complete strategy explanation
- [Confluence Filters Guide](temiz/CONFLUENCE_FILTERS_GUIDE.md) - Filter methodology
- [Backtest Results](temiz/TEMIZ_BACKTEST_RESULTS.md) - Daily data test (false positive)
- [1-Min Backtest Analysis](temiz/TEMIZ_1MIN_BACKTEST_ANALYSIS.md) - Real 1-min data test
- [Final Analysis](temiz/TEMIZ_FINAL_ANALYSIS.md) ⭐ Read this - Why it failed
- [Implementation Summary](temiz/TEMIZ_IMPLEMENTATION_SUMMARY.md) - Technical details
- [Quick Reference](temiz/TEMIZ_QUICK_REFERENCE.md) - Setup cheat sheet

**Why Temiz Failed:**
- 2021 test: -1.08% return, 33.3% win rate (9 trades on 7 days)
- 2024 test: -0.57% return, 35.7% win rate (28 trades on 55 days)
- Confluence filters: 0% win rate (filtered out ALL trades)
- **Conclusion:** Strategy doesn't work in real markets

---

## 🚦 Strategy Status

| Strategy | Status | Return | Sharpe | Max DD | Use Case |
|----------|--------|--------|--------|--------|----------|
| Nick Radge Momentum | ✅ PRODUCTION | +221% | 1.19 | -32% | Swing trading stocks |
| Institutional Crypto Perp | ✅ TESTED | +580% | 1.40 | -27% | Crypto perpetuals |
| Temiz Small-Cap Short | ❌ ABANDONED | -0.57% | N/A | N/A | Don't use |
| ATR Breakout (Long Only) | ⚠️ CONDITIONAL | +28% | 0.70 | -15% | Intraday futures only |
| ATR Breakout (Long/Short) | ❌ FAILED | -107% | N/A | -60% | Don't use |

---

## 📞 Need Help?

1. **Quick start:** Run `python quick_start.py` (2-3 min)
2. **Strategy selection:** Start with Nick Radge (proven +221%)
3. **Live trading:** Read [Live Trading Guide](deployment/LIVE_TRADING_GUIDE.md) first
4. **Deployment:** Always test in dry_run mode first
5. **Issues:** Check [CLAUDE.md](../CLAUDE.md) for troubleshooting

---

**Last updated:** October 2025
