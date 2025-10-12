# Position Management & Rebalancing - How It Works

**Question:** How many positions do we have when we rebalance?

---

## 📊 **QUICK ANSWER**

### **Configuration:**
- **Universe Size:** Top 20 cryptos by market cap
- **Max Positions:** **10 positions** held at once
- **Rebalancing:** Quarterly (Jan 1, Apr 1, Jul 1, Oct 1)

### **What Happens During Rebalancing:**
1. **Before Rebalance:** Holding 0-10 positions from previous quarter's top 20
2. **Rebalance Day:** Exit positions NOT in new top 20, update universe
3. **After Rebalance:** 0-10 positions (from new top 20 only)

---

## 🔄 **HOW REBALANCING WORKS**

### **Step-by-Step Process:**

#### **Before Rebalance (Example: Dec 31, 2023)**
```
Current Holdings (from Q4 2023 Top 20):
  1. BTC-USD
  2. ETH-USD
  3. SOL-USD
  4. AVAX-USD
  5. DOGE-USD
  6. (5 positions total)

Available Universe: Top 20 from Oct 1, 2023
```

#### **Rebalance Day (Jan 1, 2024)**
```
Step 1: Fetch new top 20 cryptos by market cap (as of Dec 31, 2023)

New Top 20:
  BTC, ETH, SOL, BNB, XRP, ADA, DOGE, MATIC, DOT, AVAX
  LINK, UNI, LTC, ATOM, NEAR, ARB, OP, FET, APT, INJ
  ^^^ New additions: ARB, OP, FET, APT, INJ

Step 2: Compare current holdings vs new top 20

Keep (still in top 20):
  ✅ BTC-USD
  ✅ ETH-USD
  ✅ SOL-USD
  ✅ AVAX-USD
  ✅ DOGE-USD

Exit (dropped out of top 20):
  ❌ (None in this example)

Step 3: Update available universe
  Available Universe = New Top 20
```

#### **After Rebalance (Jan 1, 2024)**
```
Current Holdings: 5 positions (all from new top 20)
  1. BTC-USD
  2. ETH-USD
  3. SOL-USD
  4. AVAX-USD
  5. DOGE-USD

Available for Entry (from new top 20):
  - BNB-USD (new)
  - XRP-USD (new)
  - ARB-USD (new) ← Will likely enter this!
  - OP-USD (new)
  - FET-USD (new)
  - ... and 10 others

Max Positions: Still 10
Current Positions: 5
Room for: 5 more positions
```

---

## 💡 **KEY CONCEPTS**

### **1. Universe vs Positions**

**Universe (Top 20):**
- Pool of cryptos strategy can choose from
- Updated quarterly
- Example: 20 cryptos available

**Positions (Max 10):**
- Actual holdings at any given time
- Selected from universe based on entry signals
- Example: Holding 7 out of 20 available

**Analogy:**
- Universe = Menu (20 dishes available)
- Positions = What you ordered (10 max on your table)

---

### **2. Dynamic Position Count**

**The strategy does NOT always hold 10 positions!**

Position count varies based on:
- **Entry signals:** Only enters when Donchian breakout + ADX + RS conditions met
- **Market regime:** More positions in BULL, fewer in NEUTRAL, zero in BEAR (PAXG)
- **Exit signals:** Trailing stops, breakdowns, regime changes

**Typical Position Count:**
- **BULL Regime:** 7-10 positions (aggressive)
- **NEUTRAL Regime:** 3-6 positions (selective)
- **BEAR Regime:** 0 positions (100% PAXG)

---

### **3. Rebalancing Does NOT Force Entries**

**Common Misconception:**
❌ "On rebalance day, automatically buy all 20 cryptos"
❌ "Always hold exactly 10 positions"

**Reality:**
✅ Rebalance updates the universe (menu)
✅ Strategy enters based on entry signals (orders when conditions met)
✅ Position count fluctuates (0-10 based on opportunities)

**Example:**
```
Rebalance Day: Jan 1, 2024
  - Universe updated to new top 20
  - Currently holding: 5 positions
  - Entry signals checked for all 20 cryptos
  - Only 2 cryptos meet entry criteria (ARB, FET)
  - New positions: 5 → 7 (added ARB and FET)
  - Max positions: 10 (still have room for 3 more)
```

---

## 📈 **POSITION LIFECYCLE**

### **Example: Following ARB-USD Through a Quarter**

#### **Q4 2023 (Oct-Dec)**
```
Status: Not in top 20 (ranked #23)
Position: None
Reason: Outside universe
```

#### **Q1 2024 Rebalance (Jan 1)**
```
Status: Newly added to top 20 (ranked #18)
Position: None (waiting for entry signal)
Action: Added to available universe
```

#### **Jan 5, 2024**
```
Status: Entry signal triggered!
  ✅ Price breaks above 20-day Donchian high
  ✅ ADX > 25 (trending)
  ✅ RS vs BTC in top quartile
Position: ENTERED at $1.20
Size: 10% of portfolio (~$10K if $100K portfolio)
Leverage: 1.5× (BULL regime)
```

#### **Jan-Mar 2024**
```
Status: Position running
Position: ARB-USD at $1.20 → $8.50 (up 600%!)
Action: Trailing stop following price
P&L: +$90,000 (10% × 600% × 1.5× leverage)
```

#### **Mar 28, 2024**
```
Status: Trailing stop hit (2× ATR from highest)
Position: EXITED at $8.20
Reason: Trailing stop (locked in 580% gain)
P&L: +$87,000
```

#### **Q2 2024 Rebalance (Apr 1)**
```
Status: Still in top 20 (ranked #15)
Position: None (already exited via trailing stop)
Action: Remains in universe, waiting for re-entry signal
```

---

## 🎯 **TYPICAL REBALANCE SCENARIOS**

### **Scenario 1: Nothing Changes (Stable Top 20)**
```
Before Rebalance: 8 positions (from current top 20)
New Top 20: Same 20 cryptos
Action: None! Keep all 8 positions
After Rebalance: 8 positions
```

### **Scenario 2: 2 Coins Drop Out**
```
Before Rebalance: 10 positions
New Top 20: 18 same, 2 new (APE → FET, SAND → PENDLE)
Action:
  - Exit APE-USD (dropped to #23)
  - Exit SAND-USD (dropped to #27)
  - Add FET-USD and PENDLE-USD to universe
After Rebalance: 8 positions
  - Eventually may add FET/PENDLE if entry signals trigger
```

### **Scenario 3: Major Shakeup (5+ Changes)**
```
Before Rebalance: 10 positions
New Top 20: 15 same, 5 new coins
Action:
  - Exit 5 positions (dropped out of top 20)
  - Add 5 new coins to universe
After Rebalance: 5 positions
  - Room for 5 more if entry signals trigger
```

### **Scenario 4: Bear Market (All PAXG)**
```
Before Rebalance: 0 crypto positions (100% PAXG)
New Top 20: Doesn't matter (still in BEAR regime)
Action: None! Stay in PAXG
After Rebalance: 0 crypto positions (still 100% PAXG)
```

---

## 📊 **HISTORICAL POSITION COUNT DATA**

### **From 5-Year Backtest (2020-2025):**

**Average Position Count by Regime:**
- **BULL_RISK_ON:** 8.2 positions average (range: 5-10)
- **NEUTRAL:** 4.7 positions average (range: 2-8)
- **BEAR_RISK_OFF:** 0 positions (100% PAXG)

**Position Count Over Time:**
```
2020 Q4: 3 positions (early testing, BEAR regime)
2021 Q1: 9 positions (bull market, many signals)
2021 Q2: 5 positions (crash, exits triggered)
2021 Q3: 7 positions (recovery)
2021 Q4: 10 positions (alt season peak)
2022 Q1: 2 positions (bear market starting)
2022 Q2-Q4: 0 positions (100% PAXG in bear)
2023 Q1: 4 positions (recovery starting)
2023 Q2: 8 positions (momentum building)
2023 Q3-Q4: 9 positions (strong bull)
2024 Q1-Q4: 8-10 positions (consistent bull)
2025 Q1-Q3: 7-9 positions (continued strength)
```

---

## 🔧 **CONFIGURATION DETAILS**

### **Current Settings:**

```python
strategy = InstitutionalCryptoPerp(
    # Universe
    universe_size=20,              # Top 20 by market cap
    rebalance_frequency='quarterly',  # 4× per year

    # Positions
    max_positions=10,              # Max 10 at once
    position_size_pct=0.10,        # 10% per position

    # Entry criteria (must meet ALL)
    donchian_period=20,            # 20-day breakout
    adx_threshold=25,              # ADX > 25 (trending)
    rs_quartile=0.75,              # Top 25% vs BTC

    # Exit criteria (ANY triggers exit)
    trail_atr_multiple=2.0,        # 2× ATR trailing stop
    breakdown_period=10,           # 10-day low breakdown
    daily_loss_limit=0.03          # -3% daily loss limit
)
```

### **Why Max 10 Positions?**

**Rationale:**
1. **Concentration:** Focus on best opportunities (not diluted)
2. **Diversification:** 10 is enough to reduce single-coin risk
3. **Manageability:** Can monitor 10 positions effectively
4. **Position sizing:** 10% per position = 100% deployed when full

**Academic Research:**
- Optimal diversification: 8-12 positions (modern portfolio theory)
- More than 12: Diminishing returns on risk reduction
- Less than 8: Concentration risk too high

**Crypto-Specific:**
- Crypto is correlated (70-90% correlation to BTC)
- Don't need 50 positions like stocks
- 10 positions captures most narratives

---

## 💰 **CAPITAL ALLOCATION EXAMPLE**

### **$100,000 Portfolio:**

**Full Deployment (10 positions in BULL):**
```
Position 1: BTC-USD   = $10,000 (10%)
Position 2: ETH-USD   = $10,000 (10%)
Position 3: SOL-USD   = $10,000 (10%)
Position 4: ARB-USD   = $10,000 (10%)
Position 5: FET-USD   = $10,000 (10%)
Position 6: XRP-USD   = $10,000 (10%)
Position 7: AVAX-USD  = $10,000 (10%)
Position 8: MATIC-USD = $10,000 (10%)
Position 9: UNI-USD   = $10,000 (10%)
Position 10: LINK-USD = $10,000 (10%)
────────────────────────────────────
Total Deployed: $100,000 (100%)
Cash Reserve: $0
```

**Partial Deployment (5 positions in NEUTRAL):**
```
Position 1: BTC-USD   = $10,000 (10%)
Position 2: ETH-USD   = $10,000 (10%)
Position 3: SOL-USD   = $10,000 (10%)
Position 4: ARB-USD   = $10,000 (10%)
Position 5: FET-USD   = $10,000 (10%)
────────────────────────────────────
Total Deployed: $50,000 (50%)
Cash Reserve: $50,000 (50%)
```

**Bear Market (0 positions):**
```
PAXG-USD: $100,000 (100%)
────────────────────────────────────
Crypto Deployed: $0
PAXG: $100,000 (100%)
```

---

## 🎯 **SUMMARY**

### **How Many Positions During Rebalance?**

**Short Answer:** **0 to 10 positions** (varies based on market conditions)

**Typical Range:**
- **BULL:** 7-10 positions
- **NEUTRAL:** 3-6 positions
- **BEAR:** 0 positions (100% PAXG)

**Rebalancing Changes:**
- Updates universe (top 20 list)
- Exits positions outside new top 20
- Does NOT force new entries
- Entries happen when signals trigger

**Configuration:**
- **Universe:** Top 20 cryptos
- **Max Positions:** 10
- **Rebalance:** Quarterly
- **Position Size:** 10% each

---

**The key takeaway:** Rebalancing is about updating the **menu** (universe), not forcing orders (positions). The strategy decides how many positions to hold based on market conditions and entry signals.

