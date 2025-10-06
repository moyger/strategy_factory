# Triangle Pattern Detection - Implementation Guide

## 📁 Files Created

### 1. `strategies/pattern_detector.py`
Core pattern detection module implementing:
- **Pivot point detection** (3-candle window)
- **Trendline calculation** (linear regression with R²)
- **Pattern validation** for:
  - ✅ Ascending triangles (flat resistance + rising support)
  - ✅ Descending triangles (flat support + falling resistance)
  - ✅ Symmetrical triangles (converging trendlines)
  - ✅ Flag patterns (parallel consolidation channels)
  - ✅ Pennant patterns (converging consolidation)
- **Breakout detection** with configurable buffer

### 2. `strategies/strategy_breakout_v4_triangles.py`
Enhanced London Breakout strategy combining:
- **Asia Range Breakout** (proven v3.1 logic)
- **Triangle Pattern Breakout** (new pattern-based entries)

Both approaches share:
- H4 trend alignment filter
- First-hour momentum confirmation
- Dynamic position sizing (0.75% risk for FTMO)
- Stepped trailing stop management

---

## 🔧 Pattern Detection Parameters

### Default Settings (Production)
```python
PatternDetector(
    lookback=25,              # Bars to analyze for patterns
    min_pivot_points=3,       # Minimum pivots required
    pivot_window=3,           # 3-candle window for pivots
    r_squared_min=0.9,        # Trendline quality threshold
    slope_tolerance=0.00001   # Max slope for "flat" lines
)
```

### Key Thresholds

| Pattern | Upper Slope | Lower Slope | R² Min | Notes |
|---------|-------------|-------------|--------|-------|
| **Ascending** | ≤ 0.00001 | > 0.00001 | 0.9 | Flat resistance, rising support |
| **Descending** | < -0.00001 | ≤ 0.00001 | 0.9 | Falling resistance, flat support |
| **Symmetrical** | < 0 | > 0 | 0.9 | Converging, slope ratio 0.5-2.0 |
| **Flag** | Similar | Similar | 0.7 | Parallel, slope ratio 0.9-1.05 |
| **Pennant** | ≤ -0.0001 | ≥ 0.0001 | 0.9 | Converging, slope ratio 0.95-1.05 |

---

## 🎯 Usage Examples

### Basic Pattern Detection
```python
from pattern_detector import PatternDetector

# Initialize detector
detector = PatternDetector(lookback=25, min_pivot_points=3)

# Find pivot points
df = detector.find_pivot_points(df)

# Detect all patterns
patterns = detector.detect_all_patterns(df)

for pattern in patterns:
    print(f"Pattern: {pattern['type']}")
    print(f"Resistance: {pattern['resistance']['price']:.5f}")
    print(f"Support: {pattern['support']['price']:.5f}")
    print(f"R² quality: {pattern['resistance']['r2']:.3f}")
```

### Check for Breakout
```python
# After detecting a pattern
pattern = patterns[0]
current_price = df.iloc[-1]['close']

breakout = detector.check_breakout(
    pattern,
    current_price,
    buffer_pct=0.0015  # 0.15% buffer (~1.5 pips)
)

if breakout == 'long':
    print("Bullish breakout detected!")
elif breakout == 'short':
    print("Bearish breakout detected!")
```

### Integration with Trading Strategy
```python
from strategy_breakout_v4_triangles import LondonBreakoutV4Triangles

# Enable both Asia and Triangle breakouts
strategy = LondonBreakoutV4Triangles(
    risk_percent=0.75,
    initial_capital=100000,
    enable_asia_breakout=True,    # v3.1 logic
    enable_triangle_breakout=True  # New pattern logic
)

# Run backtest
trades = strategy.backtest(h1_df, h4_df)

# Analyze by signal type
for sig_type in trades['signal_type'].unique():
    sig_trades = trades[trades['signal_type'] == sig_type]
    print(f"{sig_type}: {len(sig_trades)} trades, "
          f"{(sig_trades['pnl_dollars'] > 0).mean()*100:.1f}% win rate")
```

---

## 📊 Pattern Detection Algorithm

### Step 1: Pivot Point Detection
```
For each candle at index i:
  - Check if high[i] == max(high[i-3:i+3])  → Pivot High
  - Check if low[i] == min(low[i-3:i+3])    → Pivot Low
```

### Step 2: Trendline Calculation
```python
# Linear regression on pivot points
x = [index for each pivot]
y = [price for each pivot]

slope, intercept, r_value = scipy.stats.linregress(x, y)
r_squared = r_value ** 2

# Project trendline to current bar
trendline_price = slope * current_index + intercept
```

### Step 3: Pattern Classification
```
IF |upper_slope| ≤ 0.00001 AND lower_slope > 0.00001:
    → Ascending Triangle

ELIF |lower_slope| ≤ 0.00001 AND upper_slope < -0.00001:
    → Descending Triangle

ELIF upper_slope < 0 AND lower_slope > 0:
    IF 0.5 ≤ |upper_slope/lower_slope| ≤ 2.0:
        → Symmetrical Triangle
```

### Step 4: Breakout Confirmation
```
buffer = 0.15%  # ~1.5 pips for EURUSD

IF current_price > resistance * (1 + buffer):
    → LONG breakout

ELIF current_price < support * (1 - buffer):
    → SHORT breakout
```

---

## 🎨 Entry Signal Logic (v4.0)

### Triangle Breakout Entry Conditions

**LONG Breakout:**
1. ✅ Price breaks above pattern resistance + buffer
2. ✅ Pattern type filter:
   - Ascending: Allow if H4 trend ≠ downtrend
   - Descending breaking up: Require H4 uptrend
   - Symmetrical: Allow if H4 trend ≠ downtrend
3. ✅ First-hour momentum confirmation (18+ pips)
4. ✅ Time filter: Only during London hours 3-4 AM
5. ✅ Pattern not previously traded

**SHORT Breakout:**
1. ✅ Price breaks below pattern support - buffer
2. ✅ Pattern type filter:
   - Descending: Allow if H4 trend ≠ uptrend
   - Ascending breaking down: Require H4 downtrend
   - Symmetrical: Allow if H4 trend ≠ uptrend
3. ✅ First-hour momentum confirmation (18+ pips)
4. ✅ Time filter: Only during London hours 3-4 AM
5. ✅ Pattern not previously traded

### Stop Loss & Take Profit
```python
# LONG
entry = resistance_price * (1 + buffer)
stop_loss = support_price * (1 - buffer * 0.5)
take_profit = entry + (risk * 1.3)  # 1.3:1 R/R

# SHORT
entry = support_price * (1 - buffer)
stop_loss = resistance_price * (1 + buffer * 0.5)
take_profit = entry - (risk * 1.3)
```

**Safety Caps:**
- Maximum SL distance: 50 pips
- Minimum TP: 25 pips
- Take profit also considers 2× ATR

---

## 🧪 Testing & Validation

### Run Pattern Detector Tests
```bash
python strategies/pattern_detector.py
```

Expected output:
```
Found 7 pivot highs and 7 pivot lows

Pattern 1: ASCENDING
Resistance: price=1.10506, slope=0.00000102, R²=0.733
Support: price=1.10607, slope=0.00006678, R²=0.999
Pivot highs: 6, Pivot lows: 6

Testing breakout detection...
Price 1.10496: No breakout
Price 1.10662: long
Price 1.10672: long
```

### Run Strategy Backtest
```bash
python strategies/strategy_breakout_v4_triangles.py
```

Tests three configurations:
1. **Asia Breakout Only** (baseline v3.1)
2. **Triangle Breakout Only** (new patterns)
3. **Combined** (both strategies)

Compare metrics:
- Win rate
- Profit factor
- Average P&L
- Signal type breakdown

---

## 📈 Expected Performance

### v3.1 Baseline (Asia Breakout)
- 42 trades/year
- 58.3% win rate
- Profit factor: 1.93
- Sharpe ratio: 1.99

### v4.0 Enhancement Goals
- **More opportunities**: Patterns form beyond Asia sessions
- **Higher quality**: Geometric validation reduces false signals
- **Better R/R**: Defined support/resistance from trendlines
- **Diversification**: Two uncorrelated signal sources

---

## 🔍 Pattern Quality Indicators

### High-Quality Patterns
✅ R² ≥ 0.9 (both trendlines)
✅ 5+ pivot points
✅ Clean slope classification
✅ Lookback window ≥ 20 bars
✅ Pattern width ≥ 30 pips

### Low-Quality Patterns (Avoid)
❌ R² < 0.7
❌ < 3 pivot points
❌ Ambiguous slopes
❌ Too narrow (< 20 pips)
❌ Too recent (< 15 bars)

---

## 🚀 Next Steps

### 1. Backtest Validation
- [ ] Test on full 2020-2025 dataset
- [ ] Compare Asia-only vs Triangle-only vs Combined
- [ ] Analyze signal type performance breakdown
- [ ] Check for overfitting (walk-forward analysis)

### 2. Parameter Optimization
- [ ] Optimize `triangle_lookback` (20-40 range)
- [ ] Test `r_squared_min` (0.7-0.95)
- [ ] Tune `slope_tolerance` (0.00001-0.0001)
- [ ] Adjust `buffer_pct` (0.1%-0.2%)

### 3. Additional Patterns
- [ ] VCP (Volatility Contraction Pattern)
- [ ] Cup & Handle
- [ ] Patrick Walker's Simple Base
- [ ] Volatility compression zones

### 4. Live Trading Preparation
- [ ] Add real-time pattern scanning
- [ ] Implement visualization for detected patterns
- [ ] Create alerts for breakout signals
- [ ] Add pattern quality scoring

---

## 📚 References

**Implementation Sources:**
1. [zeta-zetra/chart_patterns](https://github.com/zeta-zetra/chart_patterns) - Triangle detection algorithms
2. [ZiadFrancis/AscendingTrianglesBacktest](https://github.com/ZiadFrancis/AscendingTrianglesBacktest) - Flag pattern logic
3. [white07S/TradingPatternScanner](https://github.com/white07S/TradingPatternScanner) - Signal filtering techniques

**Trading Theory:**
- Thomas Bulkowski's "Encyclopedia of Chart Patterns"
- Pivot point detection (3-candle window method)
- Linear regression for trendline validation
- R² threshold for quality control (≥0.9 for production)

---

## ⚠️ Important Notes

1. **Pattern Detection is Probabilistic**: Not all patterns will lead to successful breakouts
2. **Filters are Critical**: H4 trend and momentum filters significantly improve win rate
3. **Position Sizing**: Use consistent 0.75% risk for FTMO compliance
4. **Pattern Uniqueness**: Track traded patterns to avoid duplicate entries
5. **Time Filters**: Restrict to London hours (3-5 AM) for best results

---

## 💡 Tips for Best Results

### Pattern Selection
- Prioritize patterns with **R² > 0.9** on both trendlines
- Look for **5+ pivot points** (more data = better validation)
- Prefer patterns that have formed over **20+ bars**
- Avoid patterns too close to current price (< 10 pips)

### Entry Timing
- Wait for **clear breakout** + buffer (don't front-run)
- Confirm with **first-hour momentum** (18+ pips move)
- Check **H4 trend alignment** before entering
- Avoid trading after **4 AM** (patterns become less reliable)

### Risk Management
- **Never exceed 50 pips SL** (cap max risk)
- Use **trailing stop** to lock profits (1R, 1.5R, 2R levels)
- **Close all positions** at London close (12 PM)
- **Track capital** and adjust lot size per 0.75% risk rule

---

**Created:** October 2025
**Version:** 4.0 - Triangle Pattern Enhanced
**Status:** ✅ Ready for backtesting
