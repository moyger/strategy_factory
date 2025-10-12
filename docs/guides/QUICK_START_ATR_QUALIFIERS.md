# Quick Start: ATR-Based Qualifiers for Nick Radge Strategy

## 🎯 TL;DR

**Breakout Strength Score (BSS)** improves Nick Radge momentum strategy by **+47%** (197% vs 134% total return) by using ATR-adjusted breakout distance instead of simple Rate of Change.

---

## What Was Done

Based on Tomas Nesnidal's "Breakout Trading Revolution," I implemented 5 ATR-based performance qualifiers to rank stocks for the Nick Radge momentum strategy:

1. **ATR-Normalized Momentum (ANM)** - Volatility-adjusted momentum
2. **Breakout Strength Score (BSS)** ⭐ **WINNER** - Distance from POI in ATR multiples
3. **Volatility Expansion Momentum (VEM)** - Momentum during volatility expansion
4. **Trend Quality Score (TQS)** - Trend strength with ADX confirmation
5. **Risk-Adjusted Momentum (RAM)** - Momentum penalized by drawdown
6. **Composite Score** - Weighted combination (failed)

---

## Results Summary

| Qualifier | Return | Sharpe | Max DD | vs SPY | vs ROC |
|-----------|--------|--------|--------|--------|--------|
| **🏆 BSS** | **196.8%** | **1.20** | **-26.8%** | **+92%** | **+47%** |
| ROC (baseline) | 133.9% | 0.89 | -31.3% | +29% | - |
| ANM | 115.0% | 1.05 | -19.7% | +10% | -14% |
| TQS | 108.4% | 1.04 | -21.9% | +4% | -19% |
| VEM | 101.4% | 0.78 | -30.8% | -3% | -24% |
| SPY B&H | 104.9% | - | - | - | -22% |

**See chart:** [results/qualifier_comparison.png](results/qualifier_comparison.png)

---

## How to Use

### Option 1: Test It Yourself

```bash
# Run comparison backtest
venv/bin/python examples/compare_qualifiers.py

# Generate chart
venv/bin/python examples/visualize_qualifier_results.py
```

### Option 2: Integrate BSS into Your Strategy

```python
from strategy_factory.performance_qualifiers import get_qualifier
from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy

# Create BSS qualifier
bss = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)

# Calculate scores
scores = bss.calculate(prices)

# Rank stocks at specific date
date = prices.index[-1]
ranked = scores.loc[date].sort_values(ascending=False)
top_7 = ranked.head(7)
```

### Option 3: Use Enhanced Strategy Class

```python
from strategies.nick_radge_enhanced import NickRadgeEnhanced

strategy = NickRadgeEnhanced(
    portfolio_size=7,
    qualifier_type='bss',  # ⭐ Change this!
    bear_market_asset='GLD'
)

portfolio = strategy.backtest(prices, spy_prices)
strategy.print_results(portfolio, prices)
```

---

## Files Created

### Framework
- `strategy_factory/performance_qualifiers.py` - All ATR qualifiers
- `strategies/nick_radge_enhanced.py` - Strategy with qualifier support

### Examples
- `examples/compare_qualifiers.py` - Full backtest comparison
- `examples/visualize_qualifier_results.py` - Chart generation

### Documentation
- `ATR_QUALIFIERS_ANALYSIS.md` - Full analysis report
- `QUICK_START_ATR_QUALIFIERS.md` - This file

### Results
- `results/qualifier_comparison.csv` - Performance data
- `results/qualifier_comparison.png` - Visual comparison

---

## Why BSS Works

**Formula:** `BSS = (Price - MA100) / (2.0 × ATR)`

**Key Insight:** BSS identifies stocks breaking out WITH CONVICTION:
- Price must be **2× ATR above the 100-day MA** to score high
- Normalizes across different volatility regimes
- Filters out weak momentum (noise)
- Captures expansion phase of trends (Nesnidal's principle)

**Example:**
- Stock A: +10% above MA, ATR = 2% → BSS = 5.0 ✅ STRONG
- Stock B: +10% above MA, ATR = 5% → BSS = 2.0 ✅ OK
- Stock C: +10% above MA, ATR = 10% → BSS = 1.0 ❌ WEAK

---

## Next Steps

### Immediate (Paper Trading)

1. Update `deployment/config_live.json`:
   ```json
   {
     "ranking_method": "bss",
     "bss_k_multiplier": 2.0,
     "dry_run": true
   }
   ```

2. Monitor for 1 month

3. Compare against ROC baseline

### Research (Optional)

1. **Optimize k-multiplier:** Test k = [1.5, 2.0, 2.5, 3.0]
2. **Test different universes:** 20 stocks vs 50 stocks vs 100 stocks
3. **Regime-specific qualifiers:** Use BSS in STRONG_BULL, ANM in WEAK_BULL
4. **Add filters:** Combine BSS > 2.0 with ADX > 30

---

## Key Takeaways

✅ **BSS beats ROC by +47%** (197% vs 134% total return)

✅ **ATR normalization works** - same principle applies to stocks as futures

✅ **Single strong signal beats composite** - don't dilute BSS with averaging

✅ **Volatility-adjusted = conviction** - high ROC + low ATR = sustainable trend

❌ **RAM failed** - over-penalized normal volatility

❌ **Composite failed** - conflicting signals cancel out

---

## Questions?

Read the full analysis: [ATR_QUALIFIERS_ANALYSIS.md](ATR_QUALIFIERS_ANALYSIS.md)

Or check Tomas Nesnidal's book: "The Breakout Trading Revolution"

---

*Generated: 2025-10-09*
*Test Period: 2020-2025 (5 years)*
*Universe: 50 S&P 500 stocks + GLD*
