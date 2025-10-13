# Strategy Versions Quick Reference

## 🏆 HIGH-PERFORMING VERSIONS

### 1. **Original TQS (183.37%)** - PRODUCTION READY
- **Location:** `deployment/live_nick_radge_tqs_ibkr.py`
- **Config:** `deployment/config_tqs_ibkr.json`
- **Return:** +183.37% (2020-2025)
- **Sharpe:** 1.46
- **Max DD:** -24.33%
- **Status:** ✅ PRESERVED & BACKED UP
- **Features:**
  - Volatility targeting (20% annual)
  - Top 100 S&P 500 universe
  - Quarterly rebalancing
  - GLD bear protection
  - Max 25% position limit

### 2. **Hybrid 80/20 (108.91%)** - ML ENHANCED
- **Location:** `strategy_factory/hybrid_qualifier.py`
- **Return:** +108.91% (2020-2025)
- **Sharpe:** 1.28
- **Max DD:** -14.98%
- **Formula:** 80% TQS + 20% XGBoost
- **Features:**
  - ML predictions with 33 features
  - Sector momentum (9 ETFs)
  - Walk-forward training
  - Best ML-enhanced version

### 3. **Pure TQS (108.72%)** - ML TESTING BASELINE
- **Location:** `strategies/02_nick_radge_bss.py`
- **Return:** +108.72% (2020-2025)
- **Sharpe:** 1.26
- **Max DD:** -14.48%
- **Features:**
  - No volatility targeting
  - Fixed 50-stock universe
  - Simpler configuration
  - Used for ML comparisons

---

## 📊 PERFORMANCE COMPARISON

| Strategy | Return | Sharpe | Max DD | Universe | Vol Target |
|----------|--------|--------|--------|----------|------------|
| **Original TQS** | **+183.37%** | **1.46** | -24.33% | 100 stocks | ✅ 20% |
| Hybrid 80/20 | +108.91% | 1.28 | -14.98% | 51 stocks | ❌ |
| Pure TQS | +108.72% | 1.26 | -14.48% | 51 stocks | ❌ |
| XGBoost + Sectors | +58.79% | 1.11 | -10.81% | 51 stocks | ❌ |
| SPY Benchmark | +86.24% | 0.69 | N/A | - | - |

---

## 🎯 WHICH ONE TO USE?

### For Production Trading:
**→ Original TQS (183.37%)**
- Most proven performance
- Complete deployment guide
- IBKR integration ready
- Volatility targeting optimized

### For Research/ML Testing:
**→ Pure TQS (108.72%)**
- Clean baseline for comparisons
- Simpler configuration
- Fast testing iterations
- ML qualifier integration

### For ML Experimentation:
**→ Hybrid 80/20 (108.91%)**
- Best ML-enhanced version
- Sector features included
- Walk-forward validation
- Feature importance analysis

---

## 📁 FILE LOCATIONS

### Original TQS (183.37%)
```
deployment/
├── live_nick_radge_tqs_ibkr.py    ← Production script
├── config_tqs_ibkr.json           ← Configuration
├── DEPLOYMENT_GUIDE_TQS.md        ← Deployment guide
└── TQS_ORIGINAL_183_PERCENT.md    ← Preservation doc

backups/tqs_183_percent_20250113/  ← Backup folder
```

### ML Strategies
```
strategy_factory/
├── performance_qualifiers.py      ← TQS, BSS, ANM, etc.
├── ml_qualifiers.py               ← RandomForest
├── ml_xgboost.py                  ← XGBoost
└── hybrid_qualifier.py            ← TQS + XGBoost

strategies/
└── 02_nick_radge_bss.py           ← Core strategy engine
```

### Testing Scripts
```
examples/
├── compare_ml_methods.py          ← TQS vs RF vs XGBoost
├── test_xgboost_with_sectors.py  ← Sector features
└── test_hybrid_strategy.py        ← Hybrid weights
```

---

## ⚠️ IMPORTANT NOTES

1. **Original TQS files are PROTECTED**
   - DO NOT modify without backup
   - Backup exists in `backups/tqs_183_percent_20250113/`
   - Git commit: `4021115`

2. **Performance differences explained:**
   - 183% has volatility targeting (+~75% boost)
   - 183% uses larger stock universe (100 vs 50)
   - 183% has optimal risk management parameters

3. **ML added complexity with minimal gain:**
   - Hybrid beats Pure TQS by only +0.19%
   - Pure TQS is simpler and faster
   - Original TQS still outperforms all (+74.65% better)

---

**Last Updated:** 2025-01-13
**Status:** All versions preserved and documented
