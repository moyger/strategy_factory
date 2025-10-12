# How Stock Selection Works - Nick Radge Momentum Strategy

Complete explanation of how the strategy selects the top 7 stocks from the universe.

---

## 📊 Quick Summary

The strategy uses **4 filters** to find the strongest momentum stocks:

1. **Trend Filter** - Stock must be above its 100-day moving average
2. **Momentum Filter** - Stock must have positive ROC (Rate of Change)
3. **Relative Strength Filter** - Stock must be outperforming SPY
4. **Ranking** - Select top 7 by momentum strength

---

## 🔍 Step-by-Step Process

### **Step 0: Start with Universe**

```python
Stock Universe: 50 S&P 500 stocks
AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, AMD, INTC, ORCL, ...
```

### **Step 1: Calculate Momentum (ROC)**

**ROC = Rate of Change over 100 days**

```python
# Formula
ROC = ((Price_Today - Price_100_days_ago) / Price_100_days_ago) * 100

# Example:
NVDA: Price today = $500, Price 100 days ago = $350
ROC = ((500 - 350) / 350) * 100 = 42.86%

AAPL: Price today = $180, Price 100 days ago = $150
ROC = ((180 - 150) / 150) * 100 = 20.00%

INTC: Price today = $30, Price 100 days ago = $35
ROC = ((30 - 35) / 35) * 100 = -14.29%
```

**After Step 1:**
```
Stock    Price    100-day ROC
─────────────────────────────
NVDA     $500     +42.86%  ✅
ORCL     $140     +35.00%  ✅
PLTR     $28      +30.50%  ✅
AAPL     $180     +20.00%  ✅
MSFT     $420     +15.00%  ✅
GOOGL    $150     +12.00%  ✅
AMZN     $180     +8.00%   ✅
META     $520     +5.00%   ✅
TSLA     $250     +2.00%   ✅
AMD      $140     -5.00%   ❌
INTC     $30      -14.29%  ❌
```

---

### **Step 2: Filter - Above 100-day Moving Average**

**The Trend Filter**

```python
# Calculate 100-day MA for each stock
MA_100 = prices.rolling(window=100).mean()

# Only keep stocks where:
current_price > MA_100
```

**Why?** This ensures we only buy stocks in **uptrends**, not falling knives.

**Example:**
```
Stock    Price    MA(100)   Above MA?
────────────────────────────────────
NVDA     $500     $450      ✅ YES ($500 > $450)
AAPL     $180     $170      ✅ YES
MSFT     $420     $400      ✅ YES
INTC     $30      $35       ❌ NO  ($30 < $35) - REJECTED!
AMD      $140     $145      ❌ NO  ($140 < $145) - REJECTED!
```

**After Step 2:**
```
Remaining: Stocks with positive momentum AND above MA
NVDA, ORCL, PLTR, AAPL, MSFT, GOOGL, AMZN, META, TSLA
```

---

### **Step 3: Filter - Relative Strength vs SPY**

**The Benchmark Filter**

```python
# Calculate SPY's ROC
SPY_ROC = ((SPY_today - SPY_100days_ago) / SPY_100days_ago) * 100

# Only keep stocks where:
stock_ROC > SPY_ROC
```

**Why?** We only want stocks that are **beating the market**, not laggards.

**Example:**
```
SPY ROC = +10% (market benchmark)

Stock    ROC      vs SPY    Pass?
────────────────────────────────────
NVDA     +42.86%  +32.86%   ✅ Outperforming
ORCL     +35.00%  +25.00%   ✅ Outperforming
PLTR     +30.50%  +20.50%   ✅ Outperforming
AAPL     +20.00%  +10.00%   ✅ Outperforming
MSFT     +15.00%  +5.00%    ✅ Outperforming
GOOGL    +12.00%  +2.00%    ✅ Outperforming
AMZN     +8.00%   -2.00%    ❌ Underperforming - REJECTED!
META     +5.00%   -5.00%    ❌ Underperforming - REJECTED!
TSLA     +2.00%   -8.00%    ❌ Underperforming - REJECTED!
```

**After Step 3:**
```
Remaining: Stocks outperforming SPY
NVDA, ORCL, PLTR, AAPL, MSFT, GOOGL (6 stocks)
```

---

### **Step 4: Rank by Momentum & Select Top 7**

**The Final Ranking**

```python
# Sort remaining stocks by ROC (descending)
ranked = stocks.sort_values('roc', ascending=False)

# Select top 7 (or however many passed filters)
top_7 = ranked.head(7)
```

**Example:**
```
Rank  Stock    ROC      Selected?
─────────────────────────────────
 1    NVDA     +42.86%  ✅ YES
 2    ORCL     +35.00%  ✅ YES
 3    PLTR     +30.50%  ✅ YES
 4    AAPL     +20.00%  ✅ YES
 5    MSFT     +15.00%  ✅ YES
 6    GOOGL    +12.00%  ✅ YES
 7    WMT      +11.50%  ✅ YES (assuming WMT passed all filters)
─────────────────────────────────
 8    HD       +10.00%  ❌ NO (only top 7)
 9    JPM      +9.50%   ❌ NO
10    UNH      +8.75%   ❌ NO
```

**Final Portfolio: Top 7 Stocks**
```
NVDA, ORCL, PLTR, AAPL, MSFT, GOOGL, WMT
```

---

## 💰 Position Sizing - Momentum Weighting

After selecting the top 7, the strategy allocates capital **proportional to momentum strength**.

### **Formula:**

```python
# Each stock's weight = its ROC / Total ROC of all 7 stocks
weight = stock_ROC / sum_of_all_7_ROCs
```

### **Example Calculation:**

**Selected Stocks & Their ROC:**
```
Stock    ROC
─────────────────
NVDA     +42.86%
ORCL     +35.00%
PLTR     +30.50%
AAPL     +20.00%
MSFT     +15.00%
GOOGL    +12.00%
WMT      +11.50%
─────────────────
TOTAL    166.86%
```

**Calculate Weights:**
```
Stock    ROC      Weight Calculation           Weight    $10k Account
─────────────────────────────────────────────────────────────────────
NVDA     42.86%   42.86 / 166.86 = 0.2569     25.69%    $2,569
ORCL     35.00%   35.00 / 166.86 = 0.2098     20.98%    $2,098
PLTR     30.50%   30.50 / 166.86 = 0.1828     18.28%    $1,828
AAPL     20.00%   20.00 / 166.86 = 0.1199     11.99%    $1,199
MSFT     15.00%   15.00 / 166.86 = 0.0899      8.99%    $899
GOOGL    12.00%   12.00 / 166.86 = 0.0719      7.19%    $719
WMT      11.50%   11.50 / 166.86 = 0.0689      6.89%    $689
─────────────────────────────────────────────────────────────────────
TOTAL    166.86%  1.0000                      100.00%   $10,000
```

**Result:**
- **NVDA gets 25.69%** (strongest momentum → largest position)
- **WMT gets 6.89%** (weakest momentum → smallest position)
- **All 7 sum to 100%** of account balance

---

## 🐻 Market Regime Adjustment

The number of positions changes based on **market regime**:

### **Regime Detection:**

```python
# Based on SPY price vs moving averages
if SPY_price > MA_200:
    regime = "STRONG_BULL"  → Hold 7 positions
elif SPY_price > MA_50:
    regime = "WEAK_BULL"    → Hold 3 positions
else:
    regime = "BEAR"         → Hold 0 positions (cash)
```

### **Example - Different Regimes:**

**STRONG_BULL Market:**
```
Top 7 stocks selected:
NVDA, ORCL, PLTR, AAPL, MSFT, GOOGL, WMT
```

**WEAK_BULL Market:**
```
Top 3 stocks selected (highest momentum only):
NVDA, ORCL, PLTR
(More defensive, fewer positions)
```

**BEAR Market:**
```
0 stocks selected - 100% CASH
(Preserves capital during downturn)
```

---

## 📅 When Does Selection Happen?

### **Quarterly Rebalancing**

Selection runs every **quarter start**:
- **January 1** (Q1)
- **April 1** (Q2)
- **July 1** (Q3)
- **October 1** (Q4)

### **Regime Recovery**

Selection also triggers when market regime changes from **BEAR → BULL**:

```
Day 1: BEAR market → Portfolio = 100% cash
Day 2: Regime changes to STRONG_BULL
     → Immediate rebalance
     → Select top 7 stocks
     → Enter positions (don't wait for next quarter!)
```

**This is the secret sauce** - captures early recoveries!

---

## 🔄 Full Example - Quarterly Rebalance

Let's walk through a complete quarterly rebalance on **October 1, 2025**:

### **Step 1: Download Data**
```python
# Download 50 S&P 500 stocks
# Get last 200 days of price data
# Download SPY for comparison
```

### **Step 2: Calculate Indicators**
```python
For each of 50 stocks:
  - Calculate 100-day ROC
  - Calculate 100-day MA
  - Get current price

For SPY:
  - Calculate 100-day ROC = +10%
  - Calculate 50-day MA and 200-day MA
```

### **Step 3: Determine Regime**
```python
SPY price = $580
SPY MA_200 = $550
SPY MA_50 = $565

SPY > MA_200? YES → STRONG_BULL
Target positions: 7
```

### **Step 4: Filter Stocks**

**Starting Universe: 50 stocks**

**Filter 1 - Positive ROC:**
```
50 stocks → 30 stocks have positive ROC
```

**Filter 2 - Above MA:**
```
30 stocks → 22 stocks are above their 100-day MA
```

**Filter 3 - Outperforming SPY (>10% ROC):**
```
22 stocks → 15 stocks beat SPY's 10% ROC
```

### **Step 5: Rank Top 15**
```
Rank  Stock    ROC
────────────────────────
 1    MU       +45.50%  ← Selected
 2    NVDA     +42.86%  ← Selected
 3    ORCL     +38.20%  ← Selected
 4    PLTR     +35.75%  ← Selected
 5    AVGO     +32.10%  ← Selected
 6    AMD      +28.50%  ← Selected
 7    TSLA     +25.00%  ← Selected
────────────────────────
 8    AAPL     +22.00%  (Not selected)
 9    MSFT     +20.50%
10    GOOGL    +18.75%
11    AMZN     +17.20%
12    META     +15.80%
13    WMT      +14.50%
14    HD       +13.25%
15    JPM      +12.00%
```

### **Step 6: Calculate Allocations**
```
Total ROC of top 7 = 247.91%

Stock    ROC      Weight    $10k Account
──────────────────────────────────────
MU       45.50%   18.35%    $1,835
NVDA     42.86%   17.29%    $1,729
ORCL     38.20%   15.41%    $1,541
PLTR     35.75%   14.42%    $1,442
AVGO     32.10%   12.95%    $1,295
AMD      28.50%   11.50%    $1,150
TSLA     25.00%   10.08%    $1,008
──────────────────────────────────────
TOTAL    247.91%  100.00%   $10,000
```

### **Step 7: Generate Orders**

**Current positions (from last quarter):**
```
AAPL: 50 shares @ $180 = $9,000
MSFT: 2 shares @ $420 = $840
Cash: $160
Total: $10,000
```

**New target positions:**
```
MU:   61 shares @ $30 = $1,830
NVDA: 3 shares @ $580 = $1,740
ORCL: 11 shares @ $140 = $1,540
PLTR: 51 shares @ $28 = $1,428
AVGO: 1 share @ $1200 = $1,200
AMD:  8 shares @ $145 = $1,160
TSLA: 4 shares @ $250 = $1,000
```

**Orders to execute:**
```
SELL 50 AAPL   (close old position)
SELL 2 MSFT    (close old position)
BUY 61 MU      (new position)
BUY 3 NVDA     (new position)
BUY 11 ORCL    (new position)
BUY 51 PLTR    (new position)
BUY 1 AVGO     (new position)
BUY 8 AMD      (new position)
BUY 4 TSLA     (new position)
```

### **Step 8: Execute & Log**
```
2025-10-01 09:35:00 - Rebalancing: Quarterly rebalance
2025-10-01 09:35:10 - SELL 50 AAPL - Order ID: 12345
2025-10-01 09:35:11 - SELL 2 MSFT - Order ID: 12346
2025-10-01 09:35:12 - BUY 61 MU - Order ID: 12347
2025-10-01 09:35:13 - BUY 3 NVDA - Order ID: 12348
...
2025-10-01 09:35:20 - Rebalance complete
```

---

## 🎯 Key Insights

### **Why This Works:**

1. **Momentum Persistence**
   - Stocks with strong momentum tend to continue
   - Buying winners, avoiding losers

2. **Trend Following**
   - Only buy stocks in uptrends (above MA)
   - Avoid catching falling knives

3. **Relative Strength**
   - Only buy market leaders
   - Stocks beating SPY are strongest

4. **Regime Awareness**
   - Fewer positions in weak markets
   - Cash in bear markets
   - Preserves capital

5. **Momentum Weighting**
   - Strongest stocks get largest allocations
   - Better than equal weight

### **Common Scenarios:**

**Scenario 1: Bull Market**
```
50 stocks → 40 pass filters → Select top 7
Portfolio: Fully invested, high momentum stocks
```

**Scenario 2: Choppy Market**
```
50 stocks → 15 pass filters → Select top 7
Portfolio: Selective, only strong stocks
```

**Scenario 3: Bear Market**
```
SPY < MA_50 → BEAR regime
Portfolio: 100% cash (regardless of individual stocks)
```

**Scenario 4: Very Few Pass Filters**
```
50 stocks → Only 4 pass all filters
Portfolio: Hold only 4 stocks (not forced to reach 7)
```

---

## 📊 Visual Summary

```
┌─────────────────────────────────────────────────────┐
│         STOCK SELECTION FLOWCHART                   │
└─────────────────────────────────────────────────────┘

Start: 50 S&P 500 Stocks
         │
         ▼
    Calculate ROC (100-day momentum)
         │
         ▼
    Filter 1: Above 100-day MA?
         │ (Trend Filter)
         ▼
    Filter 2: Positive ROC?
         │ (Momentum Filter)
         ▼
    Filter 3: ROC > SPY ROC?
         │ (Relative Strength Filter)
         ▼
    Rank by ROC (Descending)
         │
         ▼
    Market Regime Check
    ┌───┴───┐
    │       │
STRONG   WEAK      BEAR
 BULL    BULL
  │       │         │
  ▼       ▼         ▼
Top 7   Top 3    0 Stocks
         │         │
         ▼         ▼
    Momentum Weight Each Stock
         │
         ▼
    Final Portfolio
```

---

## 🔍 Debugging - How to See the Process

Want to see the selection in action? Add this logging:

```python
def rank_stocks_by_momentum(self, prices, spy_prices):
    """Rank stocks by momentum with detailed logging"""

    print("\n" + "="*60)
    print("STOCK SELECTION PROCESS")
    print("="*60)

    # Calculate indicators
    roc = prices.pct_change(self.roc_period) * 100
    ma = prices.rolling(window=self.ma_period).mean()
    spy_roc = spy_prices.pct_change(self.roc_period).iloc[-1] * 100

    print(f"\nSPY Momentum (benchmark): {spy_roc:.2f}%")
    print(f"Starting universe: {len(prices.columns)} stocks")

    # Track filtering
    passed_filters = []

    for ticker in prices.columns:
        ticker_roc = roc.iloc[-1][ticker]
        ticker_ma = ma.iloc[-1][ticker]
        ticker_price = prices.iloc[-1][ticker]

        # Check filters
        if pd.isna(ticker_roc) or pd.isna(ticker_ma):
            print(f"  ❌ {ticker}: Insufficient data")
            continue

        if ticker_price <= ticker_ma:
            print(f"  ❌ {ticker}: Below MA (${ticker_price:.2f} < ${ticker_ma:.2f})")
            continue

        if ticker_roc <= spy_roc:
            print(f"  ❌ {ticker}: Weak vs SPY ({ticker_roc:.2f}% < {spy_roc:.2f}%)")
            continue

        # Passed all filters!
        print(f"  ✅ {ticker}: ROC {ticker_roc:+.2f}% (Above MA, Beats SPY)")
        passed_filters.append({'ticker': ticker, 'roc': ticker_roc})

    print(f"\nPassed all filters: {len(passed_filters)} stocks")

    # Rank and return
    df = pd.DataFrame(passed_filters)
    df = df.sort_values('roc', ascending=False)

    print(f"\nTop 10 by momentum:")
    for i, row in df.head(10).iterrows():
        print(f"  {i+1}. {row['ticker']}: {row['roc']:+.2f}%")

    return df
```

This will show you exactly which stocks pass each filter and why!

---

## 📚 Further Reading

- **Momentum Investing**: "Unholy Grails" by Nick Radge
- **Market Regimes**: Understanding bull/bear cycles
- **Relative Strength**: William O'Neil's CANSLIM method
- **Trend Following**: "Following the Trend" by Andreas Clenow

The strategy combines these proven concepts into one systematic approach! 🚀
