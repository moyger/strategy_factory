# BSS Qualifier Comparison - Full Test Results

**Test Period:** 2015-2024 (10 years)
**Universe:** 50-stock Nick Radge universe
**Strategy:** Nick Radge Enhanced with ATR-based qualifiers
**Initial Capital:** $100,000

---

## 📊 Results Summary

| Qualifier | Total Return | CAGR | Sharpe | Max DD | Trades | Win Rate | Profit Factor |
|-----------|-------------|------|--------|--------|--------|----------|---------------|
| **BSS** 🏆 | **+256.2%** | **29.0%** | **1.69** | **-16.2%** | 808 | **70.7%** | **10.3** |
| ROC | +198.2% | 24.5% | 1.25 | -32.0% | 1775 | 61.4% | 4.7 |
| VEM | +184.1% | 23.3% | 1.23 | -30.8% | 1776 | 61.3% | 4.9 |
| TQS | +157.6% | 20.9% | 1.46 | -17.5% | 1775 | 66.0% | 4.9 |
| ANM | +155.2% | 20.7% | 1.40 | -20.8% | 1811 | 62.6% | 3.8 |
| RAM | +68.6% | 11.0% | 0.67 | -27.0% | 264 | 40.9% | 3.3 |
| COMPOSITE | +54.0% | 9.0% | 0.96 | -18.1% | 244 | 50.8% | 9.1 |

---

## 🏆 WINNER: BSS (Breakout Strength Score)

**Why BSS Won:**

1. **Highest Total Return:** +256% vs +198% (ROC baseline) = **+58% improvement**
2. **Best Sharpe Ratio:** 1.69 vs 1.25 (ROC) = **35% better risk-adjusted returns**
3. **Lowest Drawdown:** -16.2% vs -32.0% (ROC) = **49% less downside risk**
4. **Highest Win Rate:** 70.7% vs 61.4% (ROC) = **+9.3% more winning trades**
5. **Best Profit Factor:** 10.3 vs 4.7 (ROC) = **Winners 10× larger than losers**

**Key Insight:** BSS achieved 54% fewer trades (808 vs 1775) but **higher quality** signals.

---

## 📈 Detailed Analysis by Qualifier

### 1️⃣ BSS (Breakout Strength Score) - 🏆 WINNER

**Formula:** `(Price - 100MA) / (k × ATR)`

**Performance:**
- Total Return: **+256.2%** ($100K → $356K)
- CAGR: **29.0%** per year
- Sharpe Ratio: **1.69** (excellent)
- Max Drawdown: **-16.2%** (lowest of all)
- Win Rate: **70.7%** (7 out of 10 trades win)
- Profit Factor: **10.3** (winners 10× losers)
- Trades: 808 (selective, high quality)

**Why It Works:**
- Volatility-adjusted momentum catches **strong breakouts** relative to normal volatility
- Filters out weak momentum in high-volatility stocks (avoids traps)
- Identifies stocks breaking out with **conviction** (multiple ATR above MA)
- Lower trade frequency = lower transaction costs = higher net returns

**Best For:**
- Breakout trading (momentum + volatility confirmation)
- Risk-conscious traders (lowest drawdown)
- Quality over quantity (fewer but better trades)

---

### 2️⃣ ROC (Rate of Change) - BASELINE

**Formula:** `(Price today - Price 100 days ago) / Price 100 days ago`

**Performance:**
- Total Return: **+198.2%** ($100K → $298K)
- CAGR: **24.5%** per year
- Sharpe Ratio: **1.25** (good)
- Max Drawdown: **-32.0%** (highest of tested)
- Win Rate: **61.4%**
- Profit Factor: **4.7**
- Trades: 1775 (high frequency)

**Why It's Used:**
- Nick Radge original method (proven track record)
- Simple, transparent, easy to calculate
- No volatility adjustment (pure momentum)
- High trade frequency (more opportunities)

**Drawback:**
- Doesn't account for volatility (treats all % moves equally)
- Higher drawdown (-32% vs BSS -16%)
- Lower Sharpe (1.25 vs BSS 1.69)

---

### 3️⃣ VEM (Volatility Expansion Momentum)

**Formula:** `Momentum × (ATR today / ATR avg)`

**Performance:**
- Total Return: **+184.1%**
- CAGR: **23.3%**
- Sharpe Ratio: **1.23**
- Max Drawdown: **-30.8%**
- Win Rate: **61.3%**
- Profit Factor: **4.9**

**Why It Works:**
- Favors stocks with **expanding volatility** (breakout confirmation)
- Catches early stages of strong trends
- Similar trade count to ROC (1776 trades)

**Best For:**
- Traders who want volatility expansion as confirmation
- Early breakout entries

---

### 4️⃣ TQS (Trend Quality Score)

**Formula:** `Momentum / (sum of abs(daily returns))`

**Performance:**
- Total Return: **+157.6%**
- CAGR: **20.9%**
- Sharpe Ratio: **1.46** (2nd best)
- Max Drawdown: **-17.5%** (2nd lowest)
- Win Rate: **66.0%** (2nd best)
- Profit Factor: **4.9**

**Why It Works:**
- Rewards **smooth trends**, penalizes **choppy moves**
- Quality over quantity focus
- Good Sharpe (1.46) and low drawdown (-17.5%)

**Best For:**
- Traders who prefer smooth, consistent trends
- Avoiding whipsaw-prone stocks

---

### 5️⃣ ANM (ATR-Normalized Momentum)

**Formula:** `(Price - Price[lookback]) / (ATR × sqrt(lookback))`

**Performance:**
- Total Return: **+155.2%**
- CAGR: **20.7%**
- Sharpe Ratio: **1.40** (3rd best)
- Max Drawdown: **-20.8%**
- Win Rate: **62.6%**
- Profit Factor: **3.8**

**Why It Works:**
- Risk-adjusted momentum (considers volatility path)
- Normalizes for different volatility regimes
- Highest trade count (1811)

**Best For:**
- Volatility regime normalization
- Comparing stocks with different ATR profiles

---

### 6️⃣ RAM (Risk-Adjusted Momentum)

**Formula:** `Momentum / Standard Deviation`

**Performance:**
- Total Return: **+68.6%** (lowest)
- CAGR: **11.0%**
- Sharpe Ratio: **0.67** (lowest)
- Max Drawdown: **-27.0%**
- Win Rate: **40.9%** (lowest)
- Profit Factor: **3.3**
- Trades: **264** (lowest - too selective)

**Why It Failed:**
- Too conservative (only 264 trades in 10 years)
- Penalizes **all** volatility (even healthy breakout volatility)
- Misses many profitable opportunities
- Low win rate (40.9% = most trades lose)

**Lesson:**
- Classic Sharpe-style ranking doesn't work for momentum strategies
- Momentum **requires** volatility - RAM filters out too many good trades

---

### 7️⃣ COMPOSITE (Weighted Average)

**Formula:** `Weighted combination of all 6 qualifiers`

**Performance:**
- Total Return: **+54.0%** (2nd lowest)
- CAGR: **9.0%**
- Sharpe Ratio: **0.96**
- Max Drawdown: **-18.1%** (good)
- Win Rate: **50.8%**
- Profit Factor: **9.1** (2nd best)
- Trades: **244** (too few)

**Why It Failed:**
- Too conservative (only 244 trades)
- Averaging dilutes the strengths of individual qualifiers
- RAM's poor performance dragged down the composite
- Low trade frequency = missed opportunities

**Lesson:**
- **Don't average qualifiers** - use the best one (BSS)
- Composite doesn't always outperform best individual

---

## 🎯 Recommendation

### **Use BSS for Production Trading**

**Reasons:**
1. ✅ **+58% higher returns** than baseline ROC (+256% vs +198%)
2. ✅ **49% less drawdown** (-16.2% vs -32.0%)
3. ✅ **35% better Sharpe ratio** (1.69 vs 1.25)
4. ✅ **70.7% win rate** (7 out of 10 trades profitable)
5. ✅ **10.3 profit factor** (average winner 10× average loser)

**Configuration:**
```json
{
  "qualifier_type": "bss",
  "portfolio_size": 7,
  "ma_period": 100,
  "rebalance_freq": "QS",
  "use_regime_filter": true,
  "bear_market_asset": "GLD"
}
```

---

## 📊 Performance Comparison Chart

```
Total Return (2015-2024):
BSS:       ████████████████████████████ +256%  🏆
ROC:       ████████████████████ +198%
VEM:       ██████████████████ +184%
TQS:       ███████████████ +158%
ANM:       ███████████████ +155%
RAM:       ██████ +69%
COMPOSITE: █████ +54%

Sharpe Ratio:
BSS:       ████████████████ 1.69  🏆
TQS:       ██████████████ 1.46
ANM:       █████████████ 1.40
ROC:       ███████████ 1.25
VEM:       ███████████ 1.23
COMPOSITE: █████████ 0.96
RAM:       ██████ 0.67

Win Rate:
BSS:       ██████████████ 70.7%  🏆
TQS:       █████████████ 66.0%
ANM:       ████████████ 62.6%
ROC:       ████████████ 61.4%
VEM:       ████████████ 61.3%
COMPOSITE: ██████████ 50.8%
RAM:       ████████ 40.9%

Max Drawdown (lower is better):
BSS:       -16.2%  🏆
TQS:       -17.5%
COMPOSITE: -18.1%
ANM:       -20.8%
RAM:       -27.0%
VEM:       -30.8%
ROC:       -32.0%
```

---

## 🚀 Next Steps

1. **Update live config** to use BSS qualifier
   ```bash
   Edit: deployment/config_live.json
   Change: "qualifier_type": "roc" → "qualifier_type": "bss"
   ```

2. **Test in dry run mode** for 1-2 weeks before going live

3. **Monitor key metrics:**
   - Win rate should stay >65%
   - Max drawdown should stay <-20%
   - Sharpe should stay >1.5

4. **Compare with ROC baseline** monthly

---

## 📖 Further Reading

- **BSS Formula Explained:** [docs/nick_radge/BSS_STRATEGY_EXPLAINED.md](../../docs/nick_radge/BSS_STRATEGY_EXPLAINED.md)
- **Strategy Implementation:** [strategies/02_nick_radge_enhanced_bss.py](../../strategies/02_nick_radge_enhanced_bss.py)
- **Live Trading Guide:** [docs/deployment/LIVE_TRADING_GUIDE.md](../../docs/deployment/LIVE_TRADING_GUIDE.md)

---

**Last Updated:** October 2025
**Test Data:** results/nick_radge/qualifier_comparison.csv
