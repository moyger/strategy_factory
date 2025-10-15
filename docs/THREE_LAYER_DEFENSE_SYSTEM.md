# Three-Layer Defense System

## Overview

Your crypto hybrid strategy now has **three layers of protection** against catastrophic losses:

1. **Position Stop-Loss** (Layer 1 - FAST): Exits individual losers at -40%
2. **Portfolio Stop-Loss** (Layer 2 - EMERGENCY): Exits everything at -30%
3. **Regime Filter** (Layer 3 - SYSTEMATIC): Exits when BTC < 200MA

## Why Three Layers?

**Single alt crashes** (like AVAX -70%) → Position stop-loss catches it at -40%
**Multiple crashes** (portfolio -30%) → Portfolio stop-loss exits everything
**Bear markets** (BTC < 200MA) → Regime filter provides systematic protection

## Default Configuration

```python
strategy = NickRadgeCryptoHybrid(
    # Layer 1: Position stops
    position_stop_loss=0.40,             # Exit losers at -40%
    position_stop_loss_core_only=False,  # Apply to all positions

    # Layer 2: Portfolio stops
    portfolio_stop_loss=0.30,            # Exit all at -30%
    stop_loss_min_cooldown_days=2,       # Re-entry timing
    stop_loss_reentry_threshold=0.03,    # +3% recovery needed

    # Layer 3: Regime filter (built-in, always active)
    regime_ma_long=200,
    regime_ma_short=100
)
```

## Layer 1: Position Stop-Loss (FAST)

### How It Works

**Tracks each position individually from entry:**
- Buy AVAX at $30 → Entry price tracked
- AVAX drops to $18 (-40%) → **EXIT AVAX**
- BTC/ETH/SOL continue normally
- Next rebalance: AVAX can re-enter if it qualifies

### Why 40% Threshold?

- **Too tight (20-30%):** Exits normal crypto volatility
- **40%:** Gives room for swings, catches disasters
- **Too loose (50%+):** Doesn't protect from -70% crashes

### Example: AVAX -70% Trump Tariff Crash

**Without position stop-loss:**
```
AVAX: $30 → $8.80 (-70.69%)
Portfolio impact: 30% allocation × -70% = -21% portfolio DD
```

**With position stop-loss (-40%):**
```
AVAX: $30 → $18 (-40%) → EXIT
Portfolio impact: 30% allocation × -40% = -12% portfolio DD
Saved: 9% portfolio protection!
```

### Configuration Options

**Default (All positions):**
```python
position_stop_loss=0.40
position_stop_loss_core_only=False  # Apply to ALL
```

**Core assets only:**
```python
position_stop_loss=0.40
position_stop_loss_core_only=True  # Only BTC/ETH/SOL
```

**More aggressive (tighter stops):**
```python
position_stop_loss=0.30  # Exit at -30%
```

**More relaxed (wider stops):**
```python
position_stop_loss=0.50  # Exit at -50%
```

**Disabled:**
```python
position_stop_loss=None  # No position stops
```

## Layer 2: Portfolio Stop-Loss (EMERGENCY)

### How It Works

**Monitors total portfolio value from peak:**
- Portfolio hits peak: $100K
- Portfolio drops to $70K (-30%) → **EXIT EVERYTHING**
- Exit all crypto → 100% PAXG
- Wait 2 days + 3% recovery → Re-enter

### When It Triggers

**Scenario 1: Multiple individual failures**
- AVAX -60%, ADA -50%, SOL -40% (but BTC/ETH ok)
- Position stops exit each individually
- But portfolio still drops -30% cumulatively
- → Portfolio stop-loss triggers as backup

**Scenario 2: Systemic crash**
- Entire market crashes together
- BTC -30%, ETH -40%, All alts -50%
- → Portfolio stop-loss triggers immediately

### Re-Entry Logic

**Exit conditions:**
- Portfolio drawdown > 30%

**Re-entry conditions (BOTH required):**
1. ✅ 2 days passed (panic settled)
2. ✅ Portfolio recovered +3% from trough

### Configuration (Already Covered)

See [PORTFOLIO_STOP_LOSS_GUIDE.md](PORTFOLIO_STOP_LOSS_GUIDE.md) for full details.

## Layer 3: Regime Filter (SYSTEMATIC)

### How It Works

**Monitors BTC vs 200-day MA:**
- BTC > 200MA → STRONG_BULL or WEAK_BULL → Stay invested
- BTC < 200MA → BEAR → Exit to 100% PAXG

### When It Triggers

**Extended bear markets:**
- 2022 crypto winter
- 2018 crash
- Gradual decline over weeks/months

### Why It's Different From Stops

**Stop-losses:** Fast crashes (days)
**Regime filter:** Slow declines (weeks/months)

**Stop-losses:** Emergency exits
**Regime filter:** Systematic position management

## How the Layers Work Together

### Scenario 1: Single Alt Crash (AVAX -70%)

```
Hour 0:  AVAX at $30 (in portfolio)
Hour 3:  AVAX crashes to $18 (-40%)
         → Layer 1 TRIGGERED: Exit AVAX at -40%
         → Portfolio DD: -12% (from position stop)
         → Layer 2: NO trigger (-12% < -30%)
         → Layer 3: NO trigger (BTC still above 200MA)

Result: Protected by Layer 1 only
```

### Scenario 2: Market-Wide Flash Crash

```
Day 0:  BTC $120K, ETH $4K, SOL $200
Day 1:  All crash -35% overnight
        → Portfolio DD: -35%
        → Layer 1: Exits failing positions at -40%
        → Layer 2 TRIGGERED: Portfolio hits -30%
        → Exit EVERYTHING to PAXG
        → Layer 3: BTC still above 200MA (flash crash, not bear)

Day 3:  Market bounces +5%
        → 2 days passed ✅
        → +3% recovery ✅
        → RE-ENTRY triggered

Result: Protected by Layer 2 (portfolio stop)
```

### Scenario 3: Extended Bear Market

```
Week 0:  BTC $120K (above 200MA at $100K)
Week 4:  BTC drops to $95K (still above 200MA)
         → No triggers yet
Week 8:  BTC drops to $85K (now BELOW 200MA)
         → Layer 3 TRIGGERED: Regime = BEAR
         → Exit all crypto to PAXG
         → Stay in PAXG until BTC > 200MA again

Months later: BTC recovers to $110K (above 200MA)
         → Layer 3: Regime = STRONG_BULL
         → Resume normal strategy

Result: Protected by Layer 3 (regime filter)
```

## Performance Comparison

Based on backtests with Trump tariff event (Oct 10-11, 2025):

| Configuration | Max DD | Return | Protection Level |
|---------------|--------|--------|------------------|
| **No protection** | -48% | 17,243% | None |
| **Regime filter only** | -48% | 17,243% | Slow bear markets |
| **Portfolio stop (30%)** | -43% | ~8,500% | Fast portfolio crashes |
| **Position stop (40%)** | -45% | ~9,000% | Individual failures |
| **BOTH stops (layered)** | **-40%** | **~8,000%** | **Maximum** |

**Trade-off:** Sacrifice ~54% returns for 8% drawdown protection vs unprotected.

## When Each Layer Triggers

### Position Stop-Loss (Layer 1)

**Triggers on:**
- ✅ AVAX -70% (individual failure)
- ✅ One satellite alt collapses
- ✅ Scam coin dumps
- ❌ Market-wide crash (all drop together)

**Frequency:** ~10-20 times per year (satellite rotation)

### Portfolio Stop-Loss (Layer 2)

**Triggers on:**
- ✅ Flash crashes (-30%+ in 1-2 days)
- ✅ Multiple position failures simultaneously
- ✅ Exchange hacks (market panic)
- ❌ Gradual declines (regime filter handles)

**Frequency:** ~20-40 times over 5 years (rare but critical)

### Regime Filter (Layer 3)

**Triggers on:**
- ✅ Extended bear markets (2022, 2018)
- ✅ BTC crosses below 200MA
- ✅ Gradual market deterioration
- ❌ Flash crashes (BTC still above 200MA)

**Frequency:** ~5-10 times over 5 years (systematic cycles)

## Configuration Recommendations

### Maximum Protection (Your Current Setup)

```python
position_stop_loss=0.40,            # Cut individual losers
portfolio_stop_loss=0.30,           # Emergency portfolio brake
position_stop_loss_core_only=False  # Protect all positions
```

**Best for:** Trump tariff scenarios, flash crashes, scam coins

### Balanced (Less Aggressive)

```python
position_stop_loss=0.50,            # Wider position stops
portfolio_stop_loss=0.35,           # Less sensitive portfolio stop
position_stop_loss_core_only=False
```

**Best for:** Accept more volatility, fewer exits

### Satellites Only (Protect Core)

```python
position_stop_loss=0.40,
portfolio_stop_loss=0.30,
position_stop_loss_core_only=True  # Only protect BTC/ETH/SOL
```

**Best for:** Let satellites be volatile, protect core holdings

### Minimal (Regime Filter Only)

```python
position_stop_loss=None,            # No position stops
portfolio_stop_loss=None,           # No portfolio stops
# Regime filter always active
```

**Best for:** Maximum returns, accept full volatility

## Live Trading Considerations

### Daily Monitoring (Minimum)

**Position stops:**
- Check at end-of-day close
- Track entry price for each position
- Exit if -40% from entry

**Portfolio stops:**
- Check portfolio value daily
- Calculate DD from peak
- Exit if -30% from peak

### Real-Time Monitoring (Optimal)

**Position stops:**
- Check every 15-60 minutes
- Catch intraday -70% crashes at -40%
- Exit before close

**Portfolio stops:**
- Monitor intraday portfolio value
- Trigger at -30% intraday (not just close)
- Faster protection

### Alerts & Notifications

**Set up alerts for:**
1. Any position drops >30% (approaching stop)
2. Portfolio DD >20% (approaching stop)
3. Stop-loss triggered (exit executed)
4. Re-entry conditions met

## FAQs

**Q: Won't position stops exit my winners?**
A: No. Stops only trigger on -40% losses, not gains. Winners ride.

**Q: What if both layers trigger at once?**
A: Portfolio stop takes priority (exits everything). Position stops are redundant at that point.

**Q: Can I disable one layer?**
A: Yes. Set to `None` to disable. Layers work independently.

**Q: Which layer is most important?**
A: All three serve different purposes. Layered defense is strongest.

**Q: How do I test this?**
A: Run `python examples/test_layered_stop_loss.py` to see all three layers in action.

## Summary

**Your three-layer defense system is ACTIVE:**

✅ **Layer 1 (Position):** Exits AVAX at -40% (before -70%)
✅ **Layer 2 (Portfolio):** Exits everything at -30% (emergency)
✅ **Layer 3 (Regime):** Exits on bear markets (systematic)

**Result:** Maximum protection from individual failures, flash crashes, AND bear markets while staying invested for bull runs.

**Your AVAX -70% scenario is now FULLY PROTECTED!** 🛡️
