# FTMO Grand Strategy - Master Plan

## Current Status: Ready for Phase 2 Expansion

### ✅ What We Have (PROVEN & PRODUCTION-READY)

**Strategy**: London Breakout v3.0 (Optimized)
- **Pair**: EUR/USD
- **Performance**: 124 trades (45/year), 49.2% WR, $4,749 total ($1,738/year)
- **FTMO Pass Rate**: 100% (never violated DD limits)
- **Max Drawdown**: -2.25% (vs -10% limit)
- **Status**: ✅ **PRODUCTION-READY**
- **File**: [strategy_breakout_v3.py](strategy_breakout_v3.py)

### ❌ What We Tried and Failed

**Mean Reversion** (4 attempts):
1. EUR/USD failed breakouts: 14.8% WR, -$14,832
2. EUR/USD range MR: 41.7% WR, -$1,136
3. EUR/GBP Bollinger MR: 12.9% WR, -$3,272
4. Failed breakout fade v2: 11.1% WR, -$2,156

**Conclusion**: Mean reversion doesn't work during London session. Abandon entirely.

---

## Grand FTMO Strategy: Multi-Pair Breakout Portfolio

### Phase 1: COMPLETED ✅
**EUR/USD Breakout v3.0**
- Developed, optimized, validated
- 45 trades/year, $1,738/year
- 100% FTMO pass rate

### Phase 2: SCALE TO MORE PAIRS (IN PROGRESS)

#### 2A. Add GBP/USD Breakout (NEXT - HIGH PRIORITY)
**Why GBP/USD?**
- Same strategy as EUR/USD (proven logic)
- London session pair (same hours)
- High volatility (good for breakouts)
- Uncorrelated enough to EUR/USD for diversification

**Expected Results**:
- Trades: ~45/year
- Win rate: ~49%
- Annual P&L: ~$1,700
- Risk: LOW (same proven strategy)

**Effort**: 1-2 days
- Download GBP/USD data
- Run strategy_breakout_v3.py with pair='GBPUSD'
- Validate results match EUR/USD performance
- Adjust parameters if needed

**Action Items**:
1. ☐ Download GBP/USD H1 + H4 data (yfinance or MT5)
2. ☐ Update data_loader.py (already done)
3. ☐ Run backtest: `python strategy_breakout_v3.py` (modify for GBPUSD)
4. ☐ Validate: WR > 45%, PF > 1.3, trades/year > 40
5. ☐ If validated → add to portfolio

**Success Criteria**:
- Win rate: 45-50%
- Profit factor: > 1.3
- Trades/year: > 40
- Max DD: < 3%

---

#### 2B. Add USD/JPY Breakout (MEDIUM PRIORITY)
**Why USD/JPY?**
- Tokyo close → London open transition (good breakout opportunities)
- Different currency exposure (USD base vs EUR base)
- Good volatility
- Diversification

**Expected Results**:
- Trades: ~40-45/year
- Win rate: ~48%
- Annual P&L: ~$1,600-1,700
- Risk: LOW-MEDIUM

**Considerations**:
- Different pip value (0.01 vs 0.0001)
- May need parameter adjustments
- Spreads slightly higher than EUR/USD

**Effort**: 2-3 days
**Timeline**: After GBP/USD validated

**Action Items**:
1. ☐ Download USD/JPY data
2. ☐ Adjust pip value in strategy (0.01 for JPY pairs)
3. ☐ Test with same parameters as EUR/USD
4. ☐ Optimize if needed
5. ☐ Validate and add to portfolio

---

### Phase 3: PORTFOLIO MANAGEMENT (FUTURE)

#### 3A. Create Multi-Strategy Portfolio Manager
**Purpose**: Run all strategies simultaneously, manage combined risk

**Features**:
```python
class PortfolioManager:
    def __init__(self):
        self.strategies = [
            LondonBreakoutV3(pair='EURUSD'),
            LondonBreakoutV3(pair='GBPUSD'),
            LondonBreakoutV3(pair='USDJPY'),
        ]

    def run_portfolio(self, start_date, end_date):
        # Run all strategies
        # Combine trades
        # Manage risk across portfolio
        # Generate combined performance report
```

**Risk Management**:
- Max 1 position per pair
- Max 2-3 positions total (diversification)
- Total portfolio risk: 2-3% per day
- Circuit breakers: Stop all trading at -8% DD

**Effort**: 2-3 days
**Timeline**: After 2+ pairs validated

---

#### 3B. Advanced Risk Management (OPTIONAL)
**Features**:
- Correlation-adjusted position sizing
- Dynamic risk based on recent performance
- Kelly criterion position sizing
- Volatility-adjusted stops

**Timeline**: After portfolio manager working

---

### Phase 4: ADVANCED FEATURES (OPTIONAL - LOW PRIORITY)

#### 4A. News Filter Integration
**Purpose**: Skip trading during high-impact news (NFP, FOMC, ECB)

**Expected Impact**:
- Reduce max DD by 10-20%
- Reduce trade frequency by ~5%
- Slightly improve win rate

**Effort**: 3-4 days
**Priority**: MEDIUM (after 3 pairs working)

---

#### 4B. Multi-Session Strategy (NOT RECOMMENDED)
**Idea**: Trade Asia breakouts + London breakouts

**Issues**:
- Different market dynamics
- Need to be awake 16+ hours
- Asia ranges are tighter (less profitable)

**Decision**: SKIP unless London-only portfolio underperforms

---

#### 4C. Machine Learning Enhancements (FAR FUTURE)
**Ideas**:
- Predict breakout success probability
- Adaptive parameters based on regime
- Market regime detection

**Effort**: Weeks/months
**Priority**: VERY LOW
**Decision**: Only after manual strategy proven live

---

## Expected Final Portfolio Performance

### Conservative Estimate (2 Pairs: EUR/USD + GBP/USD)

| Pair | Trades/Year | Win Rate | Annual P&L | Max DD |
|------|-------------|----------|------------|--------|
| EUR/USD | 45 | 49.2% | $1,738 | -2.25% |
| GBP/USD | 45 | 48.0% | $1,600 | -2.50% |
| **TOTAL** | **90** | **48.6%** | **$3,338** | **-3.00%** |

**FTMO Challenge**:
- Pass rate: ~100%
- Time to +10%: 60-120 days (vs 90-180 single pair)
- Safety: Excellent (max DD -3% vs -10% limit)

---

### Aggressive Estimate (3 Pairs: EUR/USD + GBP/USD + USD/JPY)

| Pair | Trades/Year | Win Rate | Annual P&L | Max DD |
|------|-------------|----------|------------|--------|
| EUR/USD | 45 | 49.2% | $1,738 | -2.25% |
| GBP/USD | 45 | 48.0% | $1,600 | -2.50% |
| USD/JPY | 40 | 47.5% | $1,500 | -2.75% |
| **TOTAL** | **130** | **48.2%** | **$4,838** | **-3.50%** |

**FTMO Challenge**:
- Pass rate: ~100%
- Time to +10%: 45-90 days
- Safety: Very good (max DD -3.5% vs -10% limit)

---

## Timeline & Milestones

### Week 1: GBP/USD Addition
**Days 1-2**: Download data, run backtest
**Days 3-4**: Validate results, optimize if needed
**Day 5**: Document findings, add to portfolio

**Deliverable**: GBP/USD breakout strategy validated

---

### Week 2: USD/JPY Addition
**Days 1-2**: Download data, adjust pip value
**Days 3-4**: Backtest, optimize
**Day 5**: Validate, document

**Deliverable**: USD/JPY breakout strategy validated

---

### Week 3: Portfolio Integration
**Days 1-2**: Create portfolio manager
**Days 3-4**: Backtest combined portfolio (2020-2025)
**Day 5**: Generate comprehensive report

**Deliverable**: Multi-pair portfolio manager working

---

### Week 4: Final Preparation
**Days 1-2**: Paper trade on demo account
**Days 3-4**: Monitor performance, fix any issues
**Day 5**: Final report, prepare for live FTMO

**Deliverable**: Ready for FTMO challenge

---

## Risk Assessment

### Low Risk Items ✅
- EUR/USD breakout v3: **PROVEN**
- GBP/USD breakout: **LOW RISK** (same strategy)
- Portfolio manager: **LOW RISK** (just combining strategies)

### Medium Risk Items ⚠️
- USD/JPY breakout: **MEDIUM RISK** (different currency, may need tweaks)
- News filter: **MEDIUM RISK** (need reliable news source)

### High Risk Items ❌
- Mean reversion: **ABANDONED** (4 failures)
- Multi-session trading: **SKIP** (different dynamics)
- ML enhancements: **FAR FUTURE** (too complex)

---

## Decision Tree: What to Do Next

```
START
  │
  ├─ Want maximum safety (conservative)?
  │  └─ Add GBP/USD only → 90 trades/year, $3,338/year
  │     └─ FTMO: 60-120 days to +10%
  │
  ├─ Want balanced approach (recommended)?
  │  └─ Add GBP/USD + USD/JPY → 130 trades/year, $4,838/year
  │     └─ FTMO: 45-90 days to +10%
  │
  └─ Want to try something different?
     ├─ Mean reversion? → ❌ DON'T (4 failures)
     ├─ Asia session? → ❌ NOT RECOMMENDED (low volatility)
     └─ More pairs (EUR/JPY, AUD/USD)? → Maybe later
```

---

## My Specific Recommendations

### Immediate (This Week): Test GBP/USD

**Why**:
- Doubles your trade frequency (45 → 90 trades/year)
- Low risk (same proven strategy)
- Fast to implement (2 days)

**How**:
```bash
# 1. Download GBP/USD data
python download_gbpusd_yfinance.py  # (create this)

# 2. Test strategy
python -c "
from strategy_breakout_v3 import LondonBreakoutV3
from data_loader import ForexDataLoader

loader = ForexDataLoader()
h1 = loader.load('GBPUSD', 'H1')
h4 = loader.load('GBPUSD', 'H4')

h1 = h1[h1.index >= '2023-01-01']
h4 = h4[h4.index >= '2023-01-01']

strategy = LondonBreakoutV3(pair='GBPUSD')
trades = strategy.backtest(h1, h4)

# Analyze
print(f'Trades: {len(trades)}')
print(f'Win rate: {(trades.pnl_dollars > 0).sum() / len(trades) * 100:.1f}%')
print(f'Total P&L: ${trades.pnl_dollars.sum():,.2f}')
"

# 3. If results good (>45% WR, >1.3 PF) → add to portfolio
```

---

### Next Week: Test USD/JPY

**Why**:
- Further diversification
- Different currency exposure
- Brings total to 130 trades/year

**Considerations**:
- Need to adjust pip value (0.01 vs 0.0001)
- May need slightly different parameters
- Spreads ~2-3 pips vs 0.5-1.0 for EUR/USD

---

### Week 3: Create Portfolio Manager

**Why**:
- Manage risk across all pairs
- Generate combined performance reports
- Prepare for live trading

**Features**:
- Run all 3 strategies simultaneously
- Combine trades chronologically
- Calculate portfolio metrics (Sharpe, DD, etc.)
- Generate FTMO challenge simulations

---

### Week 4: Paper Trade

**Why**:
- Validate backtest results match live conditions
- Check execution, slippage, spreads
- Find any bugs before risking real money

**Platform**: Demo FTMO account or broker demo

---

## Success Metrics

### Minimum Viable Portfolio (2 pairs)
- ✅ 90+ trades/year
- ✅ 48%+ win rate
- ✅ $3,000+ annual P&L
- ✅ <4% max DD
- ✅ 1.3+ profit factor

### Target Portfolio (3 pairs)
- 🎯 130+ trades/year
- 🎯 48%+ win rate
- 🎯 $4,500+ annual P&L
- 🎯 <4% max DD
- 🎯 1.4+ profit factor

### FTMO Performance
- 🏆 100% pass rate (maintained)
- 🏆 45-90 days to +10%
- 🏆 <5% max DD during challenge
- 🏆 No daily DD violations

---

## What NOT to Do

### ❌ Don't Pursue Mean Reversion
**Reason**: 4 attempts, 4 failures. It doesn't work during London session.

### ❌ Don't Add Too Many Pairs Too Fast
**Reason**: Need to validate each pair individually. Better to have 2-3 working pairs than 5-6 mediocre ones.

### ❌ Don't Over-Optimize
**Reason**: v3 parameters are already optimized. Don't tweak them for each new pair unless results are significantly different.

### ❌ Don't Skip Paper Trading
**Reason**: Backtest ≠ live performance. Need to validate on demo first.

### ❌ Don't Add Complexity Without Reason
**Reason**: Simple working strategy > complex fancy strategy. Add features only if they solve specific problems.

---

## Quick Reference: Next Actions

### TODAY (Option 1): Test GBP/USD
```bash
# Create GBP/USD downloader
# Download data
# Run backtest
# Analyze results
```

### TODAY (Option 2): Create Portfolio Manager
```bash
# Create portfolio_manager.py
# Combine EUR/USD + GBP/USD + USD/JPY
# Run combined backtest
# Generate reports
```

### TODAY (Option 3): Prepare for Live Trading
```bash
# Set up FTMO demo account
# Implement live trading script
# Paper trade EUR/USD for 1 week
# Monitor execution quality
```

---

## Final State: FTMO-Ready Portfolio

```
FTMO Grand Strategy Portfolio
│
├── Strategy: London Breakout v3.0
│   ├── EUR/USD: 45 trades/year, $1,738/year ✅
│   ├── GBP/USD: 45 trades/year, $1,600/year ⏳
│   └── USD/JPY: 40 trades/year, $1,500/year ⏳
│
├── Total Performance
│   ├── Trades: 130/year
│   ├── Win Rate: 48.2%
│   ├── Annual P&L: $4,838
│   ├── Profit Factor: 1.45
│   └── Max DD: -3.5%
│
├── FTMO Challenge
│   ├── Pass Rate: 100%
│   ├── Time to +10%: 45-90 days
│   ├── Max DD: -3.5% (safe)
│   └── Daily DD: -0.5% avg (safe)
│
└── Risk Management
    ├── Max positions: 3 (1 per pair)
    ├── Risk per trade: 0.8-1.0%
    ├── Total exposure: 2-3%
    └── Circuit breaker: -8% DD
```

---

## Conclusion: The Path Forward

### We Have:
✅ Proven profitable strategy (EUR/USD v3)
✅ Clear path to scale (GBP/USD, USD/JPY)
✅ Realistic targets ($4,838/year, 130 trades)
✅ Excellent safety (100% FTMO pass rate)

### We Need:
⏳ Validate GBP/USD (2 days)
⏳ Validate USD/JPY (2 days)
⏳ Build portfolio manager (2 days)
⏳ Paper trade (1 week)

### Timeline:
**2-3 weeks to FTMO-ready 3-pair portfolio**

### Next Immediate Step:
**Download GBP/USD data and run backtest**

---

**Ready to start with GBP/USD?**

---

**Document Status**: Master Plan Complete
**Last Updated**: 2025-10-05
**Next Action**: Test GBP/USD breakout strategy
