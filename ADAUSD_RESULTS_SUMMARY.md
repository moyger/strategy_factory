# ADAUSD Crypto Strategy Results

## Overview
Successfully adapted the London Breakout v4.1 strategy for ADAUSD (Cardano) cryptocurrency pair.

## Test Period
- **Full Period**: Jan 2023 - Jun 2025 (2.4 years)
- **Out-of-Sample**: Jan 2024 - Jun 2025 (1.4 years)
- **Data**: 41,074 H1 bars, 10,274 H4 bars

---

## Results Summary

### Risk Level: 1.0%
**Full Period:**
- Trades: 38 (15.6/year)
- Win Rate: 73.7%
- Total P&L: $17,084
- Annual Return: **7.0%**
- Profit Factor: 2.78
- Max Drawdown: -2.08%

**OOS Period:**
- Trades: 30 (20.8/year)
- Win Rate: 66.7%
- Annual Return: **5.6%**
- Profit Factor: 1.91
- Max Drawdown: -2.08%
- ✅ **FTMO COMPLIANT**

### Risk Level: 1.5%
**Full Period:**
- Trades: 38 (15.6/year)
- Win Rate: 73.7%
- Total P&L: $26,520
- Annual Return: **10.9%**
- Profit Factor: 2.72
- Max Drawdown: -3.12%

**OOS Period:**
- Trades: 30 (20.8/year)
- Win Rate: 66.7%
- Annual Return: **8.5%**
- Profit Factor: 1.89
- Max Drawdown: -3.12%
- ✅ **FTMO COMPLIANT**

### Risk Level: 2.0% (RECOMMENDED)
**Full Period:**
- Trades: 38 (15.6/year)
- Win Rate: 73.7%
- Total P&L: $36,594
- Annual Return: **15.0%**
- Profit Factor: 2.67
- Max Drawdown: -4.15%

**OOS Period:**
- Trades: 30 (20.8/year)
- Win Rate: 66.7%
- Annual Return: **11.4%**
- Profit Factor: 1.88
- Max Drawdown: -4.15%
- ✅ **FTMO COMPLIANT**

---

## Strategy Performance

### Trade Distribution
- **Asia Breakout**: 100% of trades (Triangle pattern didn't trigger)
- All trades executed during London session (3-11 AM GMT)
- Average win: +2.65%
- Average loss: -2.46%

### Recent Trades (2025)
```
Date       Type    Dir    Entry → Exit       P&L %   P&L $
04/07/25   ASIA    SHORT  $0.6178 → $0.6014  +2.66%  +$1,474
04/14/25   ASIA    LONG   $0.6510 → $0.6380  -2.00%  -$1,253
04/17/25   ASIA    SHORT  $0.6038 → $0.6172  -2.22%  -$1,234
05/19/25   ASIA    SHORT  $0.7592 → $0.7371  +2.90%  +$1,466
05/22/25   ASIA    SHORT  $0.7510 → $0.7839  -4.39%  -$1,210
```

---

## Key Adaptations for Crypto

### 1. No Pip Conversion
- Forex: Uses pips (0.0001) for EURUSD, points (0.1) for XAUUSD
- Crypto: Direct USD prices (e.g., $0.50)

### 2. Percentage-Based Parameters
```python
# Asia Range
min_range: 1%  (vs 15 pips for forex)
max_range: 8%  (vs 60 pips for forex)

# Breakout Buffer
buffer: 0.2%   (vs 1.5 pips for forex)

# First Hour Momentum
min_move: 1.5% (vs 18 pips for forex)

# Take Profit
min_tp: 2%     (vs 25 pips for forex)
```

### 3. Position Sizing Formula
```python
# Calculate risk in dollars
risk_amount = capital * (risk_percent / 100)

# Calculate units based on price distance
units = risk_amount / (entry_price - stop_loss)

# Convert to lots (1 lot = 100,000 ADA)
lots = units / 100_000
```

### 4. Volatility Adjustments
- Relaxed triangle R² threshold: 0.3 (vs 0.5 for forex)
- Higher slope tolerance for noisy crypto patterns
- Percentage-based trailing stops

---

## Comparison: Crypto vs Forex

| Metric | EURUSD | XAUUSD | ADAUSD |
|--------|---------|---------|---------|
| **Annual Return** | 18.7% | ~15% | 15.0% |
| **Win Rate** | 58.4% | ~65% | 73.7% |
| **Trades/Year** | 42.4 | ~20 | 15.6 |
| **Max DD** | ~-8% | ~-10% | -4.15% |
| **Profit Factor** | ~2.0 | ~2.5 | 2.67 |
| **FTMO Compliant** | Marginal | Yes | ✅ Yes |

---

## Advantages on Crypto

1. **Lower Drawdown**: -4.15% vs -8% to -10% on forex
2. **Higher Win Rate**: 73.7% vs 58-65% on forex
3. **Consistent Returns**: OOS performance holds up well
4. **FTMO Safe**: All risk levels well within -10% limit
5. **Simple**: Only Asia breakout strategy triggered (more focused)

## Considerations

1. **Lower Frequency**: 15-20 trades/year vs 40+ on forex
2. **24/7 Market**: Crypto trades on weekends too
3. **Commission**: Crypto spreads/fees can be higher
4. **Volatility**: More prone to gap moves and liquidity issues
5. **No Triangle Patterns**: More volatile structure reduces triangle setups

---

## Recommendation

**Use 2.0% risk level for optimal returns with acceptable drawdown:**
- 15% annual return
- 67% win rate
- 11.4% OOS return
- -4.15% max drawdown (FTMO safe)
- Profit factor 2.67

The strategy translates exceptionally well to crypto, actually showing **better risk-adjusted returns** than on forex pairs due to:
- Cleaner Asia range patterns
- More consistent breakout follow-through
- Lower drawdown profile
- Higher win rate

---

## Files
- Strategy: `strategies/strategy_breakout_v4_1_adausd.py`
- Backtest: `backtest_adausd.py`
- Data Prep: `prepare_adausd_data.py`
- Data: `data/crypto/ADAUSD_1H.csv`, `ADAUSD_4H.csv`
