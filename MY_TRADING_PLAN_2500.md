# My ADAUSD Trading Plan - Bybit 3x Leverage

## Account Setup
- **Starting Capital**: $2,500
- **Leverage**: 3x
- **Risk per Trade**: 1% ($25)
- **Exchange**: Bybit

---

## 📊 Expected Performance (Based on Backtest)

### Full Period (2023-2025, 2.4 years):
- **Starting**: $2,500
- **Ending**: $3,955
- **Total Profit**: +$1,455 (+58.2%)
- **Annual Return**: +$596/year (23.9%)

### Out-of-Sample (2024-2025, 1.4 years):
- **Starting**: $2,500
- **Ending**: $3,120
- **Total Profit**: +$620 (+24.8%)
- **Annual Return**: +$430/year (17.2%)

### Key Stats:
- **Trades per Year**: 15-20
- **Win Rate**: 67-74%
- **Profit Factor**: 1.8-2.5
- **Max Drawdown**: -6.2%
- **Typical Win**: $40-150
- **Typical Loss**: $20-130

---

## 💰 Position Sizing Details

### Per Trade Breakdown:
```
Risk Amount: $25 (1% of $2,500)

Example Trade:
  Entry: $0.50
  Stop Loss: $0.48 (2% move = $0.02)

  Without leverage:
    Position: 1,250 ADA ($625)

  With 3x leverage:
    Position: 3,750 ADA ($1,875 notional)
    Margin needed: $625

  If win (+2.6%):
    Price move: $0.013
    Profit: $0.013 × 3,750 = $48.75
    ROI on margin: 7.8%

  If loss (-2%):
    Loss: -$25 (as intended)
    ROI on margin: -4%
```

### Typical Trade Stats:
- **Position Size**: 6,000-12,000 ADA
- **Notional Value**: $3,000-$6,000
- **Margin Needed**: $1,000-$2,000 (40-80% of capital)
- **Fees per Trade**: ~$3-4
- **Average Win**: +$85 (7.6% ROI on margin)
- **Average Loss**: -$94 (7.7% ROI on margin)

---

## 📅 Monthly Expectations

Based on historical performance:

| Month | Avg Trades | Expected P&L |
|-------|-----------|--------------|
| Jan | 1-2 | $0-50 |
| Feb | 2-3 | $150-300 |
| Mar | 1-2 | $100-180 |
| Apr | 2-3 | $0-150 |
| May | 2-3 | $20-200 |
| Jun | 0-1 | $0-50 |
| Jul | 1 | $50-100 |
| Aug | 1 | $30-50 |
| Sep | 0-1 | $0-50 |
| Oct | 1 | $20-50 |
| Nov | 2-4 | $50-130 |
| Dec | 1-2 | -$75-150 |

**Note**: These are averages. Some months may have zero trades, others 4-5.

---

## 📈 Sample Trades from Backtest

### Best Trades:
1. **2025-04-07**: SHORT $0.6178 → $0.6014 = +$151 (+7.6% ROI) ✅
2. **2025-02-28**: SHORT $0.6587 → $0.6313 = +$141 (+12.2% ROI) ✅
3. **2025-03-31**: SHORT $0.6657 → $0.6500 = +$145 (+6.8% ROI) ✅
4. **2024-11-23**: LONG $0.9301 → $0.9966 = +$132 (+21.1% ROI) ✅
5. **2025-02-03**: SHORT $0.8512 → $0.8107 = +$135 (+13.9% ROI) ✅

### Worst Trades:
1. **2025-04-17**: SHORT $0.6038 → $0.6172 = -$128 (-7.0% ROI) ❌
2. **2025-04-14**: LONG $0.6510 → $0.6380 = -$133 (-6.3% ROI) ❌
3. **2025-05-22**: SHORT $0.7510 → $0.7839 = -$126 (-13.5% ROI) ❌
4. **2024-12-06**: LONG $1.2313 → $1.1823 = -$110 (-12.3% ROI) ❌

---

## ⚠️ Risk Management Rules

### Position Limits:
- ✅ **Max 1 position at a time**
- ✅ **Max margin usage: 85% of capital** ($2,125)
- ✅ **Keep $375-500 free** (15-20% buffer)

### Stop Loss Rules:
- ✅ **Daily Loss Limit**: Stop trading if down $75 in one day (3% of capital)
- ✅ **Weekly Loss Limit**: Stop trading if down $125 in one week (5%)
- ✅ **Monthly Loss Limit**: Review strategy if down $250 in one month (10%)

### Drawdown Protection:
- If capital drops to **$2,375** (-5%): Reduce risk to 0.75%
- If capital drops to **$2,250** (-10%): STOP trading, review strategy
- If capital grows to **$3,000**: Increase risk to 1.25% or withdraw profits

### Daily Routine:
1. **Check positions**: Morning (7-8 AM your time)
2. **Monitor trades**: During London session (3-11 AM GMT)
3. **Review equity**: End of day

---

## 🎯 Trading Schedule

### Active Hours (GMT):
- **Asia Session**: 00:00-03:00 (range formation)
- **London Session**: 03:00-11:00 (trading window)

### Your Local Time (adjust for your timezone):
If you're in **PST (GMT-8)**:
- Asia range: 4pm-7pm
- Trading: 7pm-3am (not ideal)

If you're in **EST (GMT-5)**:
- Asia range: 7pm-10pm
- Trading: 10pm-6am (not ideal)

If you're in **Philippines (GMT+8)**:
- Asia range: 8am-11am
- Trading: 11am-7pm ✅ **Perfect!**

**Strategy**: Set alerts on Bybit for breakout levels, don't need to watch constantly.

---

## 📱 Bybit Setup Checklist

### Account Configuration:
- [ ] Enable 3x leverage for ADAUSD
- [ ] Set to **Isolated Margin** (safer than cross)
- [ ] Enable price alerts
- [ ] Set up mobile app notifications

### Before Each Trade:
- [ ] Confirm London session (3-11 AM GMT)
- [ ] Check Asia range (1-8% width)
- [ ] Verify H4 trend direction
- [ ] Calculate exact position size
- [ ] Set stop loss BEFORE entry
- [ ] Set take profit BEFORE entry

### Position Size Calculator:
```
Risk = $25
Entry = $X
Stop Loss = $Y
Distance = |Entry - Stop Loss|

Base Units = $25 / Distance
Leveraged Units = Base Units × 3
Margin = (Leveraged Units × Entry) / 3

Example:
  Entry: $0.50, SL: $0.48
  Distance: $0.02
  Base: $25 / $0.02 = 1,250 ADA
  With 3x: 3,750 ADA
  Margin: (3,750 × $0.50) / 3 = $625
```

---

## 📊 Progress Tracking

### Weekly Review:
Track these metrics every Sunday:
- Total trades this week
- Win rate
- Net P&L
- Current balance
- Max margin used

### Monthly Review:
- Total trades this month
- Profit factor
- Largest win/loss
- Average trade size
- Fees paid

### Quarterly Goals:

**Q1 (Jan-Mar):**
- Target: +$150-250
- Expected trades: 8-12
- End balance: $2,650-750

**Q2 (Apr-Jun):**
- Target: +$100-200
- Expected trades: 5-8
- End balance: $2,750-950

**Q3 (Jul-Sep):**
- Target: +$75-150
- Expected trades: 3-6
- End balance: $2,825-1,100

**Q4 (Oct-Dec):**
- Target: +$150-250
- Expected trades: 8-12
- End balance: $2,975-1,350

**Year-End Target: $3,000-3,500** (+$500-1,000 profit, 20-40% return)

---

## ⚡ Quick Reference Card

### My Parameters:
```
Capital: $2,500
Risk: 1% = $25
Leverage: 3x
Max Margin: $2,125 (85%)
Buffer: $375-500

Typical Trade:
  Position: 6k-12k ADA
  Margin: $1,000-2,000
  Win: $40-150
  Loss: $20-130
```

### Entry Checklist:
✅ London session (3-11 AM GMT)
✅ Asia range 1-8%
✅ First hour momentum confirmed
✅ H4 trend agrees
✅ Margin available
✅ Stop loss calculated
✅ Take profit set

### Exit Rules:
🛑 Stop Loss: Hit predetermined level
💰 Take Profit: 1.3x risk distance
⏰ Time Exit: 12 PM GMT (London close)
📈 Trailing: Move SL to breakeven at +2% profit

---

## 🚀 Getting Started

### Week 1: Paper Trading
- Run strategy on TradingView or demo account
- Practice entering positions
- Get comfortable with timing
- Test your alert system

### Week 2-4: Live with Half Size
- Start with 0.5% risk ($12.50 per trade)
- Focus on execution quality
- Build confidence
- Aim for 5-10 trades

### Month 2+: Full Size
- Increase to 1% risk ($25)
- Follow all rules strictly
- Track every trade
- Review monthly

---

## 📞 Emergency Contacts / Resources

### If Things Go Wrong:
1. **Stuck in losing trade**: Trust your stop loss
2. **Margin call warning**: Close position immediately
3. **Multiple losses**: Take a break, review rules
4. **Tech issues**: Have Bybit mobile app as backup
5. **Emotional**: Step away, come back tomorrow

### Support Resources:
- Bybit Support: support@bybit.com
- Trading Journal: (keep in spreadsheet)
- Strategy File: `strategies/strategy_breakout_v4_1_adausd_bybit.py`
- Backtest: `backtest_adausd_bybit_2500.py`

---

## 🎓 Key Lessons from Backtest

### What Worked:
✅ 73.7% win rate - very consistent
✅ Losses are controlled (~$25-130)
✅ February is best month (5 trades, +$313)
✅ SHORT bias seems stronger (more wins)
✅ Drawdown stayed under 7%

### What to Watch:
⚠️ April can be choppy (3 trades, -$109 in 2025)
⚠️ December has one bad trade (liquidation-like)
⚠️ Some positions use 85%+ margin (tight)
⚠️ Fees add up ($144/year = 10% of profits)

### Red Flags to Stop Trading:
🚨 3 losses in a row
🚨 Down $125 in a week
🚨 Margin usage consistently >80%
🚨 Missing setup criteria
🚨 Feeling emotional about trades

---

## 💪 Mindset & Discipline

### Remember:
- This is a **marathon, not a sprint**
- Average trade = $38 profit (small but consistent)
- 15-20 trades/year = patience required
- Not every week will have trades
- Losses are part of the game

### Success Factors:
1. **Follow the rules** (no exceptions)
2. **Wait for setup** (don't force trades)
3. **Accept losses** (they're built into the plan)
4. **Stay disciplined** (no revenge trading)
5. **Track progress** (data over feelings)

---

## 📝 Trade Journal Template

```
Date: __________
Time: __________

SETUP:
- Asia Range: $______ to $______ (___%)
- First Hour Move: Yes/No
- H4 Trend: Up/Down/Neutral
- Entry Trigger: Asia Breakout / Triangle

TRADE:
- Direction: Long/Short
- Entry: $_______
- Stop Loss: $_______
- Take Profit: $_______
- Position Size: _______ ADA
- Margin Used: $_______ (___%)

EXIT:
- Exit Price: $_______
- Exit Reason: TP/SL/Time
- P&L: $_______ (___%)
- ROI on Margin: ___%
- New Balance: $_______

NOTES:
- What went well:
- What to improve:
- Lessons learned:
```

---

## 🎯 Final Reminder

**You're starting with $2,500 and aiming for $3,000-3,500 by end of year (20-40% return).**

That's realistic and achievable with:
- Consistent execution
- Proper risk management
- Patience between trades
- Discipline during losses

**Good luck! Trade safe, stay disciplined, and let the edge work over time.** 📈

---

*Last updated: 2025-10-06*
*Backtest period: 2023-2025*
*Platform: Bybit*
*Pair: ADAUSD*
*Leverage: 3x*
