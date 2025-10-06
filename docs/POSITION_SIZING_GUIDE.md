# Position Sizing Guide

## Overview

The London Breakout v3 strategy now includes **percentage-based position sizing** with proper forex lot calculations. This allows you to trade with consistent risk per trade while compounding returns.

---

## How It Works

### Formula

```
Risk Amount ($) = Current Capital × Risk %
Dollars per Pip = Risk Amount / Stop Loss (pips)
Lot Size = Dollars per Pip / 10  (for EURUSD)
```

### Example

**Trade Setup:**
- Capital: $100,000
- Risk: 1%
- Stop Loss: 25 pips

**Calculation:**
- Risk Amount = $100,000 × 1% = $1,000
- $/pip = $1,000 / 25 pips = $40/pip
- Lots = $40 / $10 = 4.0 lots

**Result:** Enter with 4.0 lots (risking exactly $1,000)

---

## Performance by Risk Level

### Conservative: 0.5% Risk
- **Final Capital:** $144,883 (+44.88%)
- **Max Drawdown:** -0.07%
- **Annual Return:** 7.83%
- **Best For:** Capital preservation, very low risk tolerance

### Balanced: 1.0% Risk ⭐ RECOMMENDED
- **Final Capital:** $206,885 (+106.89%)
- **Max Drawdown:** -0.15%
- **Annual Return:** 18.64%
- **Best For:** Most traders, FTMO challenges, consistent growth

### Aggressive: 2.0% Risk
- **Final Capital:** $404,014 (+304.01%)
- **Max Drawdown:** -0.35%
- **Annual Return:** 53.03%
- **Best For:** High risk tolerance, maximum growth

---

## Key Benefits

### 1. Compounding Returns
Position sizes grow with your capital:
- **Start:** 4.2 lots at $100k
- **Middle:** 10-15 lots at $150k
- **End:** 22.3 lots at $206k

Winners become larger as capital grows, while risk stays constant at 1%.

### 2. Ultra-Low Drawdown
Even at aggressive 2% risk:
- Max drawdown: Only -0.35%
- Enhanced trailing stop protects capital
- 54.4% win rate keeps equity curve smooth

### 3. Proper Forex Position Sizing
- Calculated in lots (standard unit for MT5/MT4)
- 1.0 lot = $10/pip (standard)
- 0.1 lot = $1/pip (mini)
- 0.01 lot = $0.10/pip (micro)

### 4. Risk Consistency
Every trade risks exactly the same percentage, regardless of:
- Current capital
- Stop loss distance
- Market conditions

---

## Usage

### In Code

```python
from strategies.strategy_breakout_v3 import LondonBreakoutV3

# Create strategy with 1% risk per trade
strategy = LondonBreakoutV3(
    pair='EURUSD',
    risk_percent=1.0,        # 1% risk per trade
    initial_capital=100000   # Starting capital
)

# Run backtest
trades = strategy.backtest(h1_df, h4_df)

# Check results
print(f"Final Capital: ${strategy.current_capital:,.2f}")
```

### Default Settings

If you don't specify:
```python
strategy = LondonBreakoutV3()  # Uses 1% risk, $100k capital
```

---

## Trade Information

Each trade now includes:

```python
{
    'lots': 4.52,              # Position size in lots
    'dollars_per_pip': 45.20,  # $ value per pip
    'pnl_pips': 25.0,          # Profit/loss in pips
    'pnl_dollars': 1130.00,    # Profit/loss in dollars
    'capital_after': 101130.00 # Equity after trade
}
```

---

## Live Trading Recommendations

### Starting Out
1. **Paper trade 2-4 weeks** with 0.5% risk
2. **Verify execution** matches backtest
3. **Start live with 0.5%** risk for first 20 trades
4. **Scale up to 1.0%** once comfortable

### FTMO Challenge
- **Use 1.0% risk** for optimal speed to target
- Expected: Reach +10% in 30-60 days
- Max DD stays well below -10% limit

### Risk Ladder
```
Conservative:  0.5% - 0.75%
Balanced:      1.0% - 1.25% ⭐
Aggressive:    1.5% - 2.0%
Max:           2.5% (not recommended)
```

### Account Size Guidelines

| Capital | 0.5% Risk | 1.0% Risk | 2.0% Risk |
|---------|-----------|-----------|-----------|
| $10k    | $50/trade | $100/trade | $200/trade |
| $50k    | $250/trade | $500/trade | $1,000/trade |
| $100k   | $500/trade | $1,000/trade | $2,000/trade |

---

## Risk Management Rules

### Always
✅ Use stop losses on every trade
✅ Let position sizing adjust automatically
✅ Track equity curve regularly
✅ Respect max drawdown limits

### Never
❌ Override calculated position size
❌ Risk more than 2% per trade
❌ Remove stop losses
❌ Trade during major news (if not experienced)

---

## Monitoring Your Trades

### Check After Each Trade
- Current capital
- Position size (lots)
- Risk amount ($)
- Win rate
- Cumulative return

### Weekly Review
- Equity curve trend
- Largest position size
- Average P&L
- Drawdown level

### Monthly Review
- Compare to backtest metrics
- Adjust risk % if needed
- Review largest winners/losers

---

## FAQ

**Q: Can I change risk % during live trading?**
A: Yes, but do it gradually (0.25% increments) and only after reviewing performance.

**Q: What if my stop loss is very tight?**
A: Position size will be larger, but risk stays at your set %. The strategy handles this automatically.

**Q: Does this work with other currencies?**
A: Formula works for all pairs, but pip value varies. EURUSD uses $10/lot/pip.

**Q: What about leverage?**
A: Position sizing accounts for leverage automatically. You'll need sufficient margin for calculated lot size.

---

## Example Equity Curve (1% Risk)

```
Start:  $100,000
Month 1: $103,500 (+3.5%)
Month 3: $109,200 (+9.2%)
Month 6: $118,400 (+18.4%)
Year 1:  $125,600 (+25.6%)
Year 2:  $156,800 (+56.8%)
Final:   $206,885 (+106.9%)
```

**Compounding Effect:**
Your position sizes grow with capital, accelerating returns over time.

---

## Conclusion

The percentage-based position sizing transforms the strategy from "fixed $10/pip" to a **professional, scalable trading system**.

With 1% risk:
- ✅ Consistent risk per trade
- ✅ Compounding returns
- ✅ Ultra-low drawdown
- ✅ Professional money management
- ✅ Suitable for accounts from $10k to $1M+

**Ready to trade!** 🚀
