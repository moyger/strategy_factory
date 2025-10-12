# BSS Strategy Explained in Detail

## 🎯 What is BSS?

**BSS = Breakout Strength Score**

A **volatility-adjusted momentum ranking system** that measures how strongly a stock is breaking out relative to its normal volatility. It's based on Tomas Nesnidal's "Breakout Trading Revolution" principles, adapted for daily stock selection.

---

## 📐 The Formula

```
BSS = (Price - POI) / (k × ATR)

Where:
- Price = Current stock price
- POI = Point of Initiation (100-day Moving Average)
- k = ATR multiplier (2.0)
- ATR = Average True Range (14-day)
```

**In plain English:**
> "How many ATR units is the stock above its 100-day average?"

---

## 🧮 Step-by-Step Calculation

Let's calculate BSS for a real stock: **UNH (UnitedHealth)**

### Step 1: Get the Data
```
Date: October 8, 2025
Current Price: $369.92
100-day MA: $304.46
14-day ATR: $3.82
```

### Step 2: Calculate Distance from POI
```
Distance = Price - POI
Distance = $369.92 - $304.46
Distance = $65.46

Percentage: $65.46 / $304.46 = 21.5%
```
*Stock is 21.5% above its 100-day average*

### Step 3: Calculate ATR as Percentage
```
ATR% = ATR / Price
ATR% = $3.82 / $369.92
ATR% = 1.03%
```
*Stock's daily volatility is only 1.03% of its price*

### Step 4: Calculate BSS
```
BSS = Distance / (k × ATR)
BSS = $65.46 / (2.0 × $3.82)
BSS = $65.46 / $7.64
BSS = 8.57
```

**Result:** UNH has a BSS score of **8.57**

---

## 🔍 What Does BSS Score Mean?

### Interpreting Scores

| BSS Score | Meaning | Quality |
|-----------|---------|---------|
| **> 5.0** | Extremely strong breakout | ⭐⭐⭐⭐⭐ Excellent |
| **3.0 - 5.0** | Strong breakout | ⭐⭐⭐⭐ Very Good |
| **2.0 - 3.0** | Moderate breakout | ⭐⭐⭐ Good |
| **1.0 - 2.0** | Weak breakout | ⭐⭐ Fair |
| **< 1.0** | Very weak/no breakout | ⭐ Poor |

**BSS = 8.57 means:**
- Stock moved **8.57 ATR units** above its 100-day MA
- This is an **extremely strong, high-conviction breakout**
- Low volatility relative to the price gain = sustainable trend

---

## 💡 Why BSS Works: The Conviction Concept

### Example 1: High Conviction (High BSS)

**Stock A: AAPL**
```
Price: $258.06
MA100: $220.26
Distance: +17.2% above MA
ATR: $2.50 (0.97% of price)

BSS = ($258.06 - $220.26) / (2.0 × $2.50)
BSS = $37.80 / $5.00
BSS = 7.56 ⭐⭐⭐⭐⭐
```

**Why high conviction?**
- Stock moved +17.2% above average
- But ATR is only 0.97% (very stable)
- Move is **18× larger than daily volatility**
- **Interpretation:** Strong, steady uptrend with minimal noise

### Example 2: Low Conviction (Low BSS)

**Stock B: ORCL**
```
Price: $288.63
MA100: $235.22
Distance: +22.7% above MA (HIGHER than AAPL!)
ATR: $6.50 (2.25% of price)

BSS = ($288.63 - $235.22) / (2.0 × $6.50)
BSS = $53.41 / $13.00
BSS = 4.11 ⭐⭐⭐
```

**Why lower conviction despite bigger move?**
- Stock moved +22.7% above average (higher than AAPL)
- But ATR is 2.25% (2.3× more volatile than AAPL)
- Move is only **10× larger than daily volatility**
- **Interpretation:** Big move but choppy, erratic price action

**BSS Reveals:** AAPL (7.56) is a **stronger breakout** than ORCL (4.11) even though ORCL moved more in percentage terms!

---

## 🎓 The Core Philosophy: Volatility-Adjusted Selection

### Traditional ROC (Rate of Change)
```
ROC = (Price today - Price 100 days ago) / Price 100 days ago × 100

AAPL ROC = +17.2%
ORCL ROC = +22.7%

ROC Ranking: ORCL #1, AAPL #2
```

**Problem:** ROC ignores volatility
- ORCL has higher ROC but is choppy
- AAPL has lower ROC but is smooth
- **ROC picks the noisier stock**

### BSS (Breakout Strength Score)
```
BSS adjusts for volatility:

AAPL BSS = 7.56 (high conviction)
ORCL BSS = 4.11 (lower conviction)

BSS Ranking: AAPL #1, ORCL #2
```

**Advantage:** BSS picks stocks with **strong trends AND low noise**
- AAPL's move is more sustainable
- ORCL's move is more likely to whipsaw
- **BSS picks the smoother stock**

---

## 🧪 Real-World Example: Side-by-Side Comparison

### October 8, 2025 Selection

**Top 7 by ROC:**
| Rank | Ticker | ROC | ATR% | BSS | BSS Rank | Quality |
|------|--------|-----|------|-----|----------|---------|
| 1 | MU | 106.2% | 3.5% | 7.08 | 6 | High vol momentum |
| 2 | AMD | 104.9% | 3.2% | 6.37 | 7 | High vol momentum |
| 3 | **ORCL** | **81.5%** | **2.5%** | **3.52** | **23** ❌ | **Choppy!** |
| 4 | INTC | 73.7% | 3.0% | 5.95 | 8 | Erratic |
| 5 | GOOGL | 49.5% | 1.2% | 10.52 | 1 ✅ | Actually best! |
| 6 | AVGO | 49.1% | 1.1% | 9.31 | 2 ✅ | Actually #2! |
| 7 | PLTR | 43.3% | 2.1% | 4.06 | 16 | Volatile |

**ROC picked ORCL #3** - but BSS ranks it **#23** (rejected!)

**Top 7 by BSS:**
| Rank | Ticker | BSS | ATR% | ROC | ROC Rank | Advantage |
|------|--------|-----|------|-----|----------|-----------|
| 1 | GOOGL | 10.52 | 1.2% | 49.5% | 5 | Low volatility |
| 2 | AVGO | 9.31 | 1.1% | 49.1% | 6 | Steady trend |
| 3 | **UNH** | **8.58** | **1.0%** | **36.6%** | **9** ✅ | **Healthcare quality** |
| 4 | JNJ | 8.03 | 1.3% | 28.8% | 11 ✅ | Defensive winner |
| 5 | AAPL | 7.42 | 1.0% | 22.2% | 17 ✅ | Mega-cap stability |
| 6 | MU | 7.08 | 3.5% | 106.2% | 1 | High conviction |
| 7 | AMD | 6.37 | 3.2% | 104.9% | 2 | Semiconductor |

**BSS picked UNH, JNJ, AAPL** - ROC missed all three!

---

## 📊 How BSS is Used in the Nick Radge Strategy

### Full Selection Process

**Step 1: Filter Stocks**
```python
# Only consider stocks above 100-day MA
above_ma = price > MA(100)

# Valid universe (e.g., 36 stocks out of 50)
valid_stocks = stocks[above_ma == True]
```

**Step 2: Calculate BSS for Each Stock**
```python
for each stock in valid_stocks:
    POI = 100-day Moving Average
    ATR = 14-day Average True Range

    BSS = (Price - POI) / (2.0 × ATR)
```

**Step 3: Rank by BSS**
```python
ranked_stocks = sort(BSS, descending=True)

# Top 7 stocks
GOOGL: BSS = 10.52
AVGO:  BSS = 9.31
UNH:   BSS = 8.58
JNJ:   BSS = 8.03
AAPL:  BSS = 7.42
MU:    BSS = 7.08
AMD:   BSS = 6.37
```

**Step 4: Calculate Position Weights** (Momentum-weighted)
```python
# Weight by BSS score
total_bss = 10.52 + 9.31 + 8.58 + 8.03 + 7.42 + 7.08 + 6.37 = 57.31

GOOGL weight = 10.52 / 57.31 = 18.4%
AVGO weight  = 9.31 / 57.31 = 16.2%
UNH weight   = 8.58 / 57.31 = 15.0%
JNJ weight   = 8.03 / 57.31 = 14.0%
AAPL weight  = 7.42 / 57.31 = 12.9%
MU weight    = 7.08 / 57.31 = 12.4%
AMD weight   = 6.37 / 57.31 = 11.1%
```

**Step 5: Execute Trades** (Quarterly rebalance)
```
Buy/Rebalance to target weights
Hold for ~3 months (until next quarter)
Repeat
```

---

## 🎯 Key Components Explained

### 1. Point of Initiation (POI)

**What:** Reference price to measure from

**In our implementation:** 100-day Moving Average

**Why MA100?**
- Aligns with Nick Radge's trend filter
- Represents medium-term trend
- Stocks above MA100 = uptrend confirmed

**Alternatives Nesnidal uses:**
- Previous day's close (for intraday)
- Previous week's high (for swing trading)
- Previous quarter's high (for position trading)

### 2. Average True Range (ATR)

**What:** Measure of volatility

**Calculation (14-day ATR):**
```
True Range = MAX of:
  - (Today's High - Today's Low)
  - (Today's High - Yesterday's Close)
  - (Yesterday's Close - Today's Low)

ATR = Average of last 14 True Ranges
```

**Example:**
```
Stock price: $100
Daily ranges: $2, $3, $2.50, $3.20, $2.80...
ATR(14) = Average = $2.80

ATR% = $2.80 / $100 = 2.8%
```

**Why 14 days?**
- Standard period in technical analysis
- ~2-3 trading weeks
- Captures recent volatility without too much noise

### 3. The k Multiplier (k = 2.0)

**What:** ATR multiplier that sets the "conviction threshold"

**Formula component:** `(k × ATR)`

**Our setting:** k = 2.0

**What it means:**
```
BSS = Distance / (2.0 × ATR)

A BSS of 1.0 means:
  Stock moved exactly 2× ATR above MA100

A BSS of 5.0 means:
  Stock moved 10× ATR above MA100 (very strong!)
```

**Why k = 2.0?**
- Tomas Nesnidal's research: k = 1.5 to 3.5 for different markets
- 2.0 balances selectivity vs opportunity
- Lower k (1.5) = more trades, less selective
- Higher k (3.0) = fewer trades, very selective

**Optimization potential:**
- Test k = 1.5, 2.0, 2.5, 3.0
- May vary by market regime
- Current default (2.0) works well

---

## 🔬 The Science: Why ATR Normalization Works

### Problem with Raw Momentum

**Scenario:** Compare two stocks

**Stock A (Tech):**
```
Price: $200
100 days ago: $100
ROC = 100%
Daily volatility: 5% ($10/day swings)
```

**Stock B (Utility):**
```
Price: $110
100 days ago: $100
ROC = 10%
Daily volatility: 0.5% ($0.55/day swings)
```

**Traditional ROC ranking:**
1. Stock A (100%) - High momentum ✓
2. Stock B (10%) - Low momentum ✗

**But consider the context:**
- Stock A swings ±$10/day (5% volatility)
  - 100% gain over 100 days = 1% per day
  - Daily moves are **5× larger than trend**
  - Lots of noise, whipsaws

- Stock B swings ±$0.55/day (0.5% volatility)
  - 10% gain over 100 days = 0.1% per day
  - Daily moves are **5× smaller than needed**
  - But trend is VERY consistent

### BSS Analysis

**Stock A (Tech):**
```
ATR = $10 (5% of price)
Distance from MA100 = $100

BSS = $100 / (2.0 × $10)
BSS = $100 / $20
BSS = 5.0
```

**Stock B (Utility):**
```
ATR = $0.55 (0.5% of price)
Distance from MA100 = $10

BSS = $10 / (2.0 × $0.55)
BSS = $10 / $1.10
BSS = 9.09 ⭐⭐⭐⭐⭐
```

**BSS Ranking:**
1. **Stock B (9.09)** - High conviction! ✅
2. Stock A (5.0) - Moderate conviction

**BSS reveals:** Stock B has a **stronger breakout** despite lower absolute returns because:
- Move is large relative to its normal volatility (18× ATR)
- Trend is steady and sustainable
- Low noise = high conviction = likely to continue

---

## 📈 Performance Characteristics

### What BSS Optimizes For

✅ **Risk-Adjusted Returns** (not maximum returns)
✅ **Consistency** (not explosive moves)
✅ **Low volatility trends** (not high momentum)
✅ **Sustainable breakouts** (not speculative pumps)

### What You Get with BSS

**Advantages:**
- ✅ Lower drawdown (-16.25% vs ROC's -32.05%)
- ✅ Higher Sharpe ratio (1.69 vs 1.37)
- ✅ Better win rate (70.7% vs 61.4%)
- ✅ Smoother equity curve
- ✅ Less stress (fewer whipsaws)

**Trade-offs:**
- ❌ May miss explosive rallies (PLTR +39% in one quarter)
- ❌ Lower returns in pure bull markets (2024-2025)
- ❌ More "boring" stocks (UNH, JNJ vs TSLA, PLTR)
- ❌ Fewer trades (808 vs 1,775)

---

## 🎮 BSS in Action: Real Portfolio Example

### October 2025 Portfolio

**If you invested $10,000:**

| Stock | BSS | Weight | Allocation | Shares |
|-------|-----|--------|------------|--------|
| GOOGL | 10.52 | 18.4% | $1,840 | 7.5 |
| AVGO | 9.31 | 16.2% | $1,620 | 4.7 |
| UNH | 8.58 | 15.0% | $1,500 | 4.1 |
| JNJ | 8.03 | 14.0% | $1,400 | 7.4 |
| AAPL | 7.42 | 12.9% | $1,290 | 5.0 |
| MU | 7.08 | 12.4% | $1,240 | 6.3 |
| AMD | 6.37 | 11.1% | $1,110 | 4.7 |

**Portfolio characteristics:**
- Heavily weighted toward highest BSS (GOOGL 18.4%)
- Balanced across sectors (tech, healthcare, semiconductors)
- All stocks have BSS > 6.0 (strong conviction)
- Low-volatility leaders (GOOGL, UNH, JNJ) get more weight

**3-Month Forward Performance** (hypothetical):
- GOOGL: +5% = $92 gain
- AVGO: +8% = $130 gain
- UNH: +6% = $90 gain
- JNJ: +3% = $42 gain
- AAPL: +7% = $90 gain
- MU: +15% = $186 gain
- AMD: +12% = $133 gain

**Total: +$763 on $10,000 = +7.6% in 3 months**

---

## 🔄 Quarterly Rebalance Process

### Timeline

**Q1 - January 2, 2025:**
1. Calculate BSS for all 50 stocks
2. Rank by BSS score
3. Select top 7
4. Calculate weights
5. Rebalance portfolio
6. **Hold for 3 months**

**Q2 - April 1, 2025:**
1. Recalculate BSS (prices/MA/ATR all updated)
2. New top 7 may be different
3. Sell stocks that dropped out
4. Buy new stocks that ranked in
5. Adjust weights
6. **Hold for 3 months**

**Example changes:**
```
Q1 Top 7: PLTR, MCD, SBUX, LOW, ABBV, HD, META
Q2 Top 7: ABBV, AMGN, MCD, ABT, CSCO, PLTR, SPGI

Dropped out: SBUX, LOW, HD, META (4 stocks)
Added in: AMGN, ABT, CSCO, SPGI (4 stocks)
Held: PLTR, MCD, ABBV (3 stocks)
```

**Turnover:** 4/7 = 57% quarterly turnover

---

## 🎯 When BSS Wins vs Loses

### BSS Wins When:

✅ **Market Corrections** (2022: +23% vs ROC's -20%)
- Low volatility = avoided choppy stocks
- Defensive names (UNH, JNJ) held up
- High conviction = stayed in winners

✅ **Recovery Phases** (2023: +92% vs ROC's +63%)
- Caught quality breakouts early
- Avoided false starts
- Low ATR stocks led recovery

✅ **Volatile Markets** (Aug 2024: +12.8% vs ROC's -1.4%)
- ATR filter avoided whipsaws
- Selected stable momentum
- Conviction = held through volatility

### BSS Loses When:

❌ **Strong Bull Rallies** (2024: +30% vs ROC's +60%)
- Too conservative
- Missed explosive momentum stocks
- Avoided high-beta plays

❌ **Momentum Explosions** (Nov 2024: 0% vs ROC's +23%)
- ROC caught TSLA, PLTR, NVDA rallies
- BSS in cash or defensive names
- Selectivity = opportunity cost

---

## 💪 Strengths of BSS

1. **Volatility Awareness**
   - Adjusts for each stock's unique characteristics
   - Comparable across different volatility regimes

2. **Downside Protection**
   - -16.25% max drawdown (50% less than ROC)
   - Avoids choppy, whipsaw-prone stocks

3. **Quality Bias**
   - Naturally selects institutional-grade stocks
   - UNH, JNJ, AAPL vs PLTR, TSLA

4. **Consistency**
   - 70.7% win rate
   - Profit factor: 10.34
   - Smooth equity curve

5. **Tomas Nesnidal Validated**
   - Based on professional trader's research
   - Proven across multiple markets
   - "Holy Grail" indicator (ATR)

---

## ⚠️ Weaknesses of BSS

1. **Opportunity Cost**
   - Misses explosive rallies
   - Too conservative in strong bulls

2. **Lower Upside**
   - 256% vs potential 300%+ with aggressive approach
   - Defensive = gives up some gains

3. **Complexity**
   - Harder to explain than ROC
   - Requires ATR calculation
   - More parameters (POI, k, ATR period)

4. **Backtesting Bias**
   - Optimized for 2020-2025 period
   - May underperform in different regimes
   - Needs ongoing validation

---

## 🎓 Summary: BSS in One Page

### Formula
```
BSS = (Price - MA100) / (2.0 × ATR14)
```

### What It Measures
**"How many ATR units is the stock above its 100-day average?"**

### Core Insight
**High BSS = Strong price move with LOW volatility = High conviction breakout**

### Selection Criteria
- Filter: Stock > MA100 (uptrend confirmed)
- Calculate: BSS for each stock
- Rank: Select top 7 by BSS
- Weight: Allocate by BSS score (higher BSS = more weight)
- Rebalance: Quarterly

### Performance
- **256% return** over 5 years
- **1.69 Sharpe** (excellent risk-adjusted)
- **-16.25% max drawdown** (defensive)
- **70.7% win rate** (consistent)

### Best For
- Risk-averse investors
- Long-term wealth building
- Smooth equity curves
- Lower stress portfolios

### Compared to ROC
- Lower returns in bull markets
- Much better in corrections
- Overall: +29% better total return
- Key: Better compounding through lower drawdowns

---

## 📚 Further Reading

**In This Repository:**
- [ATR_QUALIFIERS_FINAL_RESULTS.md](ATR_QUALIFIERS_FINAL_RESULTS.md) - Full backtest results
- [BSS_STOCK_SELECTION_ANALYSIS.md](BSS_STOCK_SELECTION_ANALYSIS.md) - Which stocks qualify
- [strategy_factory/performance_qualifiers.py](strategy_factory/performance_qualifiers.py) - Implementation code

**External:**
- Tomas Nesnidal: "The Breakout Trading Revolution" (book)
- Nick Radge: "Unholy Grails" (momentum strategy framework)

---

*Last Updated: 2025-10-09*
*Author: Strategy Factory*
