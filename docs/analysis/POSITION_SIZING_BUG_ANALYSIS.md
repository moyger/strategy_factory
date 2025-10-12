# Critical Bug Found: Position Sizing Compounding Error

## The Bug

**Location:** `strategies/institutional_crypto_perp_strategy.py`, line 349

```python
# BUGGY CODE:
max_notional = equity * max_leverage * allocation_per_position
```

## What Went Wrong

This line allows **leverage to compound with equity growth**, creating exponential, unrealistic returns.

### Example of the Bug

**Iteration 1 (Start):**
- Equity: $100,000
- Allocation: 10% per position
- Leverage: 1.5×
- Max notional: $100,000 × 1.5 × 0.10 = **$15,000**  ✅ Reasonable

**Iteration 100 (After some wins):**
- Equity: $1,000,000 (10× growth)
- Allocation: 10% per position
- Leverage: 1.5×
- Max notional: $1,000,000 × 1.5 × 0.10 = **$150,000**  ❌ Too large!

**Iteration 500 (Compounding effect):**
- Equity: $10,000,000 (100× growth)
- Max notional: $10,000,000 × 1.5 × 0.10 = **$1,500,000**  ❌❌❌ Insanely large!

### The Problem

The position size grows proportionally with equity, which means:
1. Bigger equity → Bigger positions
2. Bigger positions → Bigger wins
3. Bigger wins → Even bigger equity
4. **Infinite compounding loop**

This is why we saw:
- **+98,429% return** over 5 years ($100k → $98.5M)
- Final positions of **millions of dollars** each
- **Unrealistic leverage** applied to huge equity

---

## What Actually Happens in Real Trading

### Real Trader Behavior

**Option 1: Fixed Position Sizes**
- Start: $100k equity, $10k positions (10%)
- Later: $1M equity, still $10k-50k positions
- **Positions grow slowly or stay fixed**

**Option 2: Percentage-Based with Caps**
- Start: $100k equity, $10k positions (10%)
- Later: $1M equity, $50k positions (5%) ← Lower percentage
- **Reduced allocation % as account grows**

**Option 3: Kelly Criterion / Risk-Based**
- Position size based on edge/win rate
- Typically 1-5% risk per trade
- Never uses full leverage on full equity

### What Our Buggy Code Did

- Start: $100k equity, $15k positions (10% × 1.5 leverage)
- Later: $1M equity, $150k positions (10% × 1.5 leverage) ← Same %!
- Final: $98M equity, **$14.7M positions** (10% × 1.5 leverage) ← INSANE

**No real trader does this.** Position sizes don't scale linearly with unlimited growth.

---

## Realistic Test Results

When I fixed the position sizing to use **FIXED allocation** (10% of INITIAL $100k):

```
Processing 2021-10-16: $102,926  (+3%)
Processing 2022-11-20: $121,607  (+22%)
Processing 2023-12-25: $155,285  (+55%)
Processing 2025-01-28: $102,343  (+2%)
```

**Much more realistic growth pattern!**

---

## Impact on Results

### Original (Buggy) Results

| Configuration | Total Return | Final Equity |
|--------------|--------------|--------------|
| 10 pos, 1.5× lev | **+98,429%** | **$98,529,164** |
| 5 pos, 1.5× lev | +31,311% | $31,410,655 |

### Expected Realistic Results

| Configuration | Estimated Return | Estimated Final |
|--------------|------------------|-----------------|
| 10 pos, 1.5× lev | **~+200-500%** | **~$200k-$600k** |
| 5 pos, 1.5× lev | ~+150-400% | ~$150k-$500k** |

**The realistic results are 50-200× LOWER than the buggy results.**

---

## Why This Matters

### The "5 vs 10 positions" conclusion was WRONG

**What we thought:**
- 10 positions: +98,429% ✅ WINNER
- 5 positions: +31,311% ❌ LOSER
- Conclusion: Use 10 positions

**What really happened:**
- Both results are inflated by the bug
- We can't draw ANY conclusions from buggy data
- Need to re-run with fixed position sizing

---

## How to Fix

### Option 1: Fixed Dollar Amounts (Conservative)

```python
def calculate_position_size_fixed(price, initial_capital=100000):
    """
    Each position is fixed % of INITIAL capital
    Doesn't grow with equity
    """
    position_notional = initial_capital * 0.10  # Always $10k
    position_size = position_notional / price
    return position_size
```

**Pros:**
- Simple, realistic
- Prevents unlimited growth
- Matches how many traders operate

**Cons:**
- No compounding (slow growth)
- Same position size whether you have $100k or $1M

---

### Option 2: Percent of Equity with Hard Caps (Moderate)

```python
def calculate_position_size_capped(price, equity, initial_capital=100000):
    """
    Position is % of equity, but capped at 10× initial
    """
    base_notional = equity * 0.10
    max_notional = initial_capital * 0.10 * 10  # Cap at $100k per position
    position_notional = min(base_notional, max_notional)
    position_size = position_notional / price
    return position_size
```

**Pros:**
- Allows some compounding
- Caps prevent exponential growth
- Realistic growth curve

**Cons:**
- Still eventually hits cap
- More complex

---

### Option 3: Scaling Down Allocation % (Advanced)

```python
def calculate_position_size_scaled(price, equity, initial_capital=100000):
    """
    Allocation % decreases as equity grows
    """
    if equity <= initial_capital:
        allocation = 0.10  # 10% when small
    elif equity <= initial_capital * 10:
        allocation = 0.05  # 5% when medium
    else:
        allocation = 0.02  # 2% when large

    position_notional = equity * allocation
    position_size = position_notional / price
    return position_size
```

**Pros:**
- Mimics real trader behavior
- Natural risk management
- Still allows compounding but slower

**Cons:**
- Arbitrary brackets
- Complex logic

---

## Recommendation

### Use Option 2: Percent with Caps

**Why:**
1. Allows compounding (realistic for crypto)
2. Caps prevent explosion (realistic for risk management)
3. Balance between growth and safety

**Implementation:**

```python
def calculate_realistic_position_size(price, equity, initial_capital=100000,
                                     allocation_pct=0.10, max_multiplier=10):
    """
    Calculate position size with realistic constraints

    - Base: allocation_pct of current equity
    - Cap: max_multiplier × allocation_pct of initial capital
    """
    base_notional = equity * allocation_pct
    cap_notional = initial_capital * allocation_pct * max_multiplier
    final_notional = min(base_notional, cap_notional)

    position_size = final_notional / price
    return position_size
```

**Example:**
- Initial: $100k equity → $10k per position ✅
- After 5× growth: $500k equity → $50k per position ✅
- After 20× growth: $2M equity → $100k per position (capped) ✅
- **Never exceeds 10× initial position size**

---

## Next Steps

1. ✅ Identified the bug
2. ⏳ Fix the position sizing function
3. ⏳ Re-run 5-year backtest with realistic sizing
4. ⏳ Re-evaluate 5 vs 10 positions
5. ⏳ Re-evaluate all conclusions

**The previous +98,429% result is INVALID. Need to re-test everything.**

---

*Analysis by Strategy Factory | October 2025*
*Bug discovered through skeptical review of unrealistic returns*
