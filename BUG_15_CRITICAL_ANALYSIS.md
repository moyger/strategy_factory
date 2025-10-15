# BUG 15: Critical VectorBT Price Error Analysis

**Status:** 🚨 **CRITICAL - BLOCKS DEPLOYMENT**
**Priority:** P0 (Showstopper)
**Discovered:** 2025-01-14
**Impact:** Strategy crashes on pure dynamic allocation, reported results unreliable

---

## THE BUG

### Error Message
```
ValueError: order.price must be finite and greater than 0
```

### When It Occurs
- Running "pure dynamic" test (100% satellite, 0% core)
- Strategy attempts to place order at NaN or ≤0 price
- VectorBT rejects invalid price

### Why It Slipped Through
- Original backtest used 70% core (BTC/ETH/SOL) with complete price history
- 30% satellite is small, so a few bad allocations got filtered
- **Pure dynamic (100% satellite) exposes the bug immediately**

---

## ROOT CAUSE

### The Timing Problem

**Sequence of events that creates the bug:**

```
Day T-1: Asset has valid price ($100)
  ↓
Indicators calculated using Day T-1 data
  ↓
Day T: Asset price is NaN (exchange downtime, delisting, etc.)
  ↓
select_satellite() ranks asset as "TOP 5" (using T-1 indicators)
  ↓
current_satellite = ['ASSET-A', 'ASSET-B', 'ASSET-C', ...]
  ↓
Allocation logic sets: allocations.loc[T, 'ASSET-A'] = 0.06
  ↓
VectorBT tries to execute: BUY ASSET-A at price NaN
  ↓
💥 CRASH: "price must be finite and greater than 0"
```

### The Code Flow

**Step 1: Satellite Selection** (lines 363-370)
```python
if should_rebalance_satellite:
    selected = self.select_satellite(satellite_prices, indicators, date)
    if len(selected) > 0:
        current_satellite = selected['ticker'].tolist()
        satellite_scores = dict(zip(selected['ticker'], selected['score']))
```

`select_satellite()` uses **lagged indicators** (lines 189-239):
```python
scores = indicators['scores'].loc[date]  # Already lagged by .shift(1)
above_ma = indicators['above_ma'].loc[date]
```

**Key issue:** Indicators are lagged (T-1 data), but current price (T) may be NaN.

**Step 2: Allocation** (lines 410-443)
```python
# FIX: Only allocate to satellites with valid prices (not NaN)
valid_satellites = [t for t in current_satellite
                  if t in prices.columns and not pd.isna(prices.at[date, t]) and prices.at[date, t] > 0]
```

**This SHOULD prevent NaN allocations**, but it happens AFTER selection.

**Step 3: The Gap**

Between steps 1 and 2, there's a gap:
- `current_satellite` contains assets selected on T-1 data
- `valid_satellites` filters for T data
- **BUT:** Non-rebalance days use `current_satellite` without re-filtering

**This is where the bug hides.**

---

## DETAILED TIMELINE ANALYSIS

### Scenario: Asset Gets Delisted

**2025-01-10 (Friday):**
- ASSET-A: $50 ✅
- TQS score: 0.85 (top 3)
- Quarterly rebalance → Selected for satellite
- `current_satellite = ['ASSET-A', 'ASSET-B', 'ASSET-C', 'ASSET-D', 'ASSET-E']`
- `allocations.loc['2025-01-10', 'ASSET-A'] = 0.06`
- VectorBT buys ASSET-A at $50 ✅

**2025-01-11 - 2025-01-12 (Weekend):**
- Exchange announces ASSET-A delisting effective Monday

**2025-01-13 (Monday):**
- ASSET-A: NaN ❌ (delisted)
- No rebalance scheduled (next is April)
- `pending_regime_change = False`
- `should_apply_allocation = False`
- **Code hits line 387-389:** `continue` (skip allocation)
- **VectorBT sees NaN in allocation matrix, holds existing position** ✅

So far so good. The `continue` prevents allocation.

**2025-01-14 (Tuesday):**
- ASSET-A: Still NaN
- BTC crosses 200MA → Regime change BEAR → STRONG_BULL
- `pending_regime_change = True`
- `should_apply_allocation = True`
- **Code executes allocation block (lines 430-455)**

```python
# Satellite: 30% momentum or equal weighted
valid_satellites = [t for t in current_satellite
                  if t in prices.columns and not pd.isna(prices.at[date, t]) and prices.at[date, t] > 0]
# valid_satellites = ['ASSET-B', 'ASSET-C', 'ASSET-D', 'ASSET-E']  (ASSET-A removed)

if self.use_momentum_weighting and valid_satellites and satellite_scores:
    total_score = sum(satellite_scores[t] for t in valid_satellites if t in satellite_scores)
    # total_score = satellite_scores['ASSET-B'] + satellite_scores['ASSET-C'] + ...
    # (ASSET-A not in valid_satellites, so not included)

    if total_score > 0:
        for ticker in valid_satellites:
            if ticker in satellite_scores:
                weight = (satellite_scores[ticker] / total_score) * self.satellite_allocation
                allocations.loc[date, ticker] = weight
```

**Wait, this looks fine! ASSET-A is filtered out.**

**So where's the bug?**

---

## THE ACTUAL BUG: INDICATOR CALCULATION

Let me trace back further to indicator calculation (lines 141-187):

```python
def calculate_indicators(self, prices: pd.DataFrame, btc_prices: Optional[pd.Series] = None):
    # For crypto: spy_prices=btc_prices, volumes=prices, sector_prices=None
    scores = self.qualifier.calculate(
        prices,
        spy_prices=btc_prices,
        volumes=prices,  # Use prices as volume proxy
        sector_prices=None
    ).shift(1)

    # Moving Average filter
    ma = prices.rolling(window=self.ma_period).mean().shift(1)
    above_ma = (prices.shift(1) > ma)
```

**Key line:**
```python
above_ma = (prices.shift(1) > ma)
```

**If `prices` contains NaN:**
- `prices.shift(1)` propagates NaN
- `NaN > ma` = NaN (not True/False!)
- `above_ma` contains NaN for that asset

**Then in `select_satellite()` (line 218):**
```python
valid_cryptos = above_ma[above_ma == True].index
```

**If `above_ma[ticker]` is NaN:**
- `NaN == True` → False
- Asset IS filtered out ✅

**So indicators are fine too!**

---

## WHERE IS THE ACTUAL BUG?

Let me check the allocation matrix creation more carefully...

**AH! Found it:** Lines 535-546

```python
# Find dates where allocations were actually set (non-zero rows)
row_sums = allocations.sum(axis=1)
actual_allocation_dates = row_sums[row_sums > 0].index.tolist()

# Create a copy with NaN for non-rebalance days
allocations_rebalance_only = pd.DataFrame(np.nan, index=allocations.index, columns=allocations.columns)

# Only copy allocations on days where we actually allocated
for date in actual_allocation_dates:
    allocations_rebalance_only.loc[date] = allocations.loc[date]
```

**The bug is NOT in setting allocations - it's in the PRICES DataFrame passed to VectorBT!**

Let me check the data cleaning (lines 646-710):

```python
# Step 1: Forward fill ONLY (no backfill!)
prices = prices.fillna(method='ffill')

# Step 2: Replace inf with NaN, then forward fill again
prices = prices.replace([np.inf, -np.inf], np.nan).fillna(method='ffill')

# Step 3: Drop columns that are COMPLETELY empty
completely_empty = prices.columns[prices.isna().all()].tolist()
# ... drops them

# Step 4: Check for columns with >50% NaN
nan_pct = prices.isna().sum() / len(prices)
too_sparse = nan_pct[nan_pct > 0.50].index.tolist()
# ... drops them (except core/bear assets)

# Step 5: Remaining NaNs
remaining_nans = prices.isna().sum().sum()
if remaining_nans > 0:
    print(f"   ℹ️  {remaining_nans} total NaN values (will not be used in calculations)")
    # Do NOT fill with zeros or backfill!
```

**FOUND IT!**

**Line 706:** "will not be used in calculations"

**But they ARE used by VectorBT!**

When `prices` has NaN and `allocations` has non-zero values for that date/asset:
- VectorBT tries to execute order at NaN price
- **CRASH**

---

## WHY IT HAPPENS IN PURE DYNAMIC

**Pure Dynamic = 100% satellite, 0% core**

This means:
- ALL allocations depend on satellite selection
- Satellites are selected from top 50 cryptos
- Many top 50 cryptos have partial histories (launched 2021-2022)
- When strategy tries to allocate to a crypto before it launched → NaN price
- **CRASH**

**70/30 Hybrid:**
- 70% is BTC/ETH/SOL (complete history)
- 30% satellite can have some NaNs, but 70% stabilizes it
- **Most NaN allocations get filtered, bug hidden**

---

## THE FIX

### Option 1: Filter Prices DataFrame (Recommended)

Before passing to VectorBT, drop any columns with remaining NaNs:

```python
# After all cleaning steps
if prices.isna().any().any():
    cols_with_nans = prices.columns[prices.isna().any()].tolist()
    print(f"   ⚠️  WARNING: {len(cols_with_nans)} columns still have NaN values")
    print(f"   These assets will be EXCLUDED from backtest (partial history)")

    # Only keep columns with complete data
    complete_cols = prices.columns[~prices.isna().any()].tolist()
    prices = prices[complete_cols]
    print(f"   ✅ Final: {len(prices.columns)} assets with complete data")
```

**Pros:**
- Simple, safe
- Prevents NaN price errors

**Cons:**
- Loses assets with partial histories (SOL, AVAX, etc.)
- Reduces satellite universe
- **Massive survivorship bias** (only assets that existed full period)

### Option 2: Align Allocations with Valid Prices (Better)

Only allocate to assets with valid prices on each day:

```python
# In generate_allocations(), before returning allocations_rebalance_only
for date in allocations_rebalance_only.index:
    for ticker in allocations_rebalance_only.columns:
        alloc = allocations_rebalance_only.at[date, ticker]

        # If allocation is non-NaN (rebalance day)
        if pd.notna(alloc) and alloc > 0:
            # Check if price is valid
            if ticker in prices.columns:
                price = prices.at[date, ticker]
                if pd.isna(price) or price <= 0:
                    # Clear allocation (can't trade at NaN price)
                    allocations_rebalance_only.at[date, ticker] = np.nan
```

**Pros:**
- Keeps assets with partial histories
- Only blocks trades when price is actually NaN
- More realistic (matches real trading)

**Cons:**
- Adds complexity
- May cause unintended cash holdings

### Option 3: Forward-Fill Until Valid (Dangerous)

Keep forward-filling prices until all NaNs are gone:

```python
prices = prices.fillna(method='ffill').fillna(method='bfill').fillna(0)
```

**Pros:**
- Simple

**Cons:**
- **Look-ahead bias** (backfill)
- **Invalid prices** (zero-fill)
- **WRONG - DO NOT USE**

---

## RECOMMENDED FIX

**Use Option 2 (Align Allocations with Valid Prices)**

Add this function:

```python
def _align_allocations_with_prices(self, allocations: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure allocations only reference assets with valid prices.
    Clears any allocations where price is NaN or ≤0.
    """
    aligned = allocations.copy()

    for date in aligned.index:
        for ticker in aligned.columns:
            alloc = aligned.at[date, ticker]

            # Only check on rebalance days (non-NaN allocations)
            if pd.notna(alloc) and alloc != 0:
                # Check if price is valid
                if ticker in prices.columns:
                    price = prices.at[date, ticker]
                    if pd.isna(price) or price <= 0:
                        # Clear allocation
                        aligned.at[date, ticker] = np.nan
                        print(f"   ⚠️  Cleared {ticker} allocation on {date} (price={price})")
                else:
                    # Ticker not in prices at all
                    aligned.at[date, ticker] = np.nan
                    print(f"   ⚠️  Cleared {ticker} allocation on {date} (not in prices)")

    return aligned
```

Call it before returning allocations:

```python
# At end of generate_allocations() (line 571)
return self._align_allocations_with_prices(allocations_rebalance_only, prices)
```

**This ensures VectorBT NEVER sees an allocation for an asset with NaN price.**

---

## IMPACT ON REPORTED RESULTS

### Did This Bug Affect the +9,825% Backtest?

**Probably not directly, but it creates doubt:**

1. The 70/30 hybrid didn't crash (bug hidden by core assets)
2. BUT: We don't know if some trades used invalid prices
3. VectorBT may have silently skipped bad trades (depends on version)
4. **Result: We can't trust the reported returns**

### Test to Verify

Run backtest with trade logging:

```python
# After backtest
trades = portfolio.trades.records
for trade in trades:
    date = prices.index[trade['exit_idx']]
    ticker = prices.columns[trade['col']]
    price = prices.at[date, ticker]

    if pd.isna(price) or price <= 0:
        print(f"❌ INVALID TRADE: {ticker} on {date} at price {price}")
```

If ANY trades have NaN prices → **entire backtest is invalid**.

---

## NEXT STEPS

1. **Implement Option 2 fix** (alignment function)
2. **Add trade validation** (check for NaN price trades)
3. **Re-run full backtest** with validation
4. **Compare results** (old vs new)
5. **Test pure dynamic** (should no longer crash)

**Only after fix + validation should we trust any results.**

---

## LESSONS LEARNED

### What Went Wrong

1. **Insufficient testing** - Only tested 70/30, not edge cases
2. **Complex logic** - Hard to reason about all paths
3. **Silent failures** - Bug didn't crash, just hid in lucky configuration
4. **No assertions** - Should have asserted: "No allocations for NaN prices"

### What Would Have Caught This

1. **Unit tests** - Test `generate_allocations()` with NaN prices
2. **Integration tests** - Test pure dynamic, pure fixed, 50/50, etc.
3. **Assertions** - Check allocation×price validity before VectorBT
4. **Trade logging** - Print every trade, catch NaN prices immediately

**This is a TEXTBOOK example of why strategies need comprehensive testing.**

---

**Analyst:** Claude (Bug Hunter Mode)
**Severity:** CRITICAL (P0)
**Status:** Open - Requires immediate fix
**Estimated Fix Time:** 2-4 hours (implement, test, validate)
