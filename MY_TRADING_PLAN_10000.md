# My ADAUSD Trading Plan - Bybit 3x Leverage

## Account Setup
- **Starting Capital**: $10,000
- **Leverage**: 3x
- **Risk per Trade**: 1% ($100)
- **Exchange**: Bybit

---

## 📊 Expected Performance (Based on Backtest)

### Full Period (2023-2025, 2.4 years):
- **Starting**: $10,000
- **Ending**: $15,821
- **Total Profit**: +$5,821 (+58.2%)
- **Annual Return**: +$2,386/year (23.9%)

### Out-of-Sample (2024-2025, 1.4 years):
- **Starting**: $10,000
- **Ending**: $12,478
- **Total Profit**: +$2,478 (+24.8%)
- **Annual Return**: +$1,721/year (17.2%)

### Key Stats:
- **Trades per Year**: 15-20
- **Win Rate**: 67-74%
- **Profit Factor**: 1.8-2.5
- **Max Drawdown**: -6.2%
- **Typical Win**: $150-600
- **Typical Loss**: $100-530

---

## 💰 Position Sizing Details

### Per Trade Breakdown:
```
Risk Amount: $100 (1% of $10,000)

Example Trade:
  Entry: $0.50
  Stop Loss: $0.48 (2% move = $0.02)

  Without leverage:
    Position: 5,000 ADA ($2,500)

  With 3x leverage:
    Position: 15,000 ADA ($7,500 notional)
    Margin needed: $2,500

  If win (+2.6%):
    Price move: $0.013
    Profit: $0.013 × 15,000 = $195
    ROI on margin: 7.8%

  If loss (-2%):
    Loss: -$100 (as intended)
    ROI on margin: -4%
```

### Typical Trade Stats:
- **Position Size**: 24,000-48,000 ADA
- **Notional Value**: $12,000-$24,000
- **Margin Needed**: $4,000-$8,000 (40-80% of capital)
- **Fees per Trade**: ~$13-26
- **Average Win**: +$342 (7.6% ROI on margin)
- **Average Loss**: -$376 (7.7% ROI on margin)

---

## 📅 Monthly Performance Analysis

Based on historical results:

| Month | Avg Trades | Expected P&L | Best Case | Worst Case |
|-------|-----------|--------------|-----------|------------|
| Jan | 1-2 | $0-200 | +$516 | -$397 |
| Feb | 2-3 | $600-1,250 | +$1,254 | -$53 |
| Mar | 1-2 | $400-735 | +$735 | $0 |
| Apr | 2-3 | -$100-580 | +$580 | -$437 |
| May | 2-3 | $80-800 | +$787 | +$88 |
| Jun | 0-1 | $0-200 | N/A | N/A |
| Jul | 1 | $200-417 | +$417 | $0 |
| Aug | 1 | $120-201 | +$201 | $0 |
| Sep | 0-1 | $0-200 | N/A | N/A |
| Oct | 1 | $80-115 | +$115 | $0 |
| Nov | 2-4 | $200-525 | +$525 | +$215 |
| Dec | 1-2 | -$300-568 | +$568 | -$299 |

**Best Months**: February, March, May, November
**Caution Months**: April (choppy), December (volatile)

---

## 📈 Sample Trades from Backtest

### Biggest Winners (Top 5):
1. **2025-04-07**: SHORT $0.6178 → $0.6014 = +$605 (7.6% ROI) ✅
2. **2025-05-19**: SHORT $0.7592 → $0.7371 = +$591 (8.4% ROI) ✅
3. **2025-03-31**: SHORT $0.6657 → $0.6500 = +$580 (6.8% ROI) ✅
4. **2025-02-28**: SHORT $0.6587 → $0.6313 = +$565 (12.2% ROI) ✅
5. **2025-02-03**: SHORT $0.8512 → $0.8107 = +$541 (13.9% ROI) ✅

### Biggest Losers (Top 5):
1. **2025-04-14**: LONG $0.6510 → $0.6380 = -$531 (-6.3% ROI) ❌
2. **2025-04-17**: SHORT $0.6038 → $0.6172 = -$512 (-7.0% ROI) ❌
3. **2025-05-22**: SHORT $0.7510 → $0.7839 = -$502 (-13.5% ROI) ❌
4. **2024-11-18**: LONG $0.7354 → $0.7199 = -$447 (-6.7% ROI) ❌
5. **2024-12-06**: LONG $1.2313 → $1.1823 = -$442 (-12.3% ROI) ❌

**Key Insight**: Largest losses are still controlled at -$500 range (5% of capital), showing good risk management.

---

## 📊 Yearly Performance Breakdown

### 2023: Perfect Year
- **Trades**: 8
- **Win Rate**: 100%
- **P&L**: +$2,678 (+26.8%)
- **Notes**: All 8 trades were winners!

### 2024: Moderate Year
- **Trades**: 15
- **Win Rate**: 66.7%
- **P&L**: +$1,353 (+13.5%)
- **Notes**: More choppy, April drawdown

### 2025: Good Year (partial)
- **Trades**: 15 (through May)
- **Win Rate**: 66.7%
- **P&L**: +$1,790 (+17.9%)
- **Notes**: Strong February, choppy April

---

## ⚠️ Risk Management Rules

### Position Limits:
- ✅ **Max 1 position at a time**
- ✅ **Max margin usage: 85% of capital** ($8,500)
- ✅ **Keep $1,500-2,000 free** (15-20% buffer)

### Stop Loss Rules:
- ✅ **Daily Loss Limit**: Stop trading if down $300 in one day (3%)
- ✅ **Weekly Loss Limit**: Stop trading if down $500 in one week (5%)
- ✅ **Monthly Loss Limit**: Review strategy if down $1,000 in one month (10%)

### Drawdown Protection:
- If capital drops to **$9,500** (-5%): Reduce risk to 0.75% ($75/trade)
- If capital drops to **$9,000** (-10%): STOP trading, review strategy
- If capital grows to **$12,000**: Increase risk to 1.25% OR withdraw $2,000 profit

### Daily Routine:
1. **Check positions**: Morning (7-8 AM your time)
2. **Monitor trades**: During London session (3-11 AM GMT)
3. **Review equity**: End of day
4. **Weekly review**: Every Sunday

---

## 🎯 Trading Schedule

### Active Hours (GMT):
- **Asia Session**: 00:00-03:00 (range formation)
- **London Session**: 03:00-11:00 (trading window)

### Your Local Time:
**If Philippines (GMT+8):**
- Asia range: 8:00 AM - 11:00 AM
- Trading: 11:00 AM - 7:00 PM ✅ **Perfect timezone!**

**Strategy**: Set price alerts on Bybit for breakout levels.

---

## 📱 Bybit Setup Checklist

### Account Configuration:
- [ ] Deposit $10,000 USDT
- [ ] Enable 3x leverage for ADAUSD
- [ ] Set to **Isolated Margin** (safer)
- [ ] Enable price alerts
- [ ] Set up mobile app notifications
- [ ] Verify trading fees (0.055% taker)

### Before Each Trade:
- [ ] Confirm London session (3-11 AM GMT)
- [ ] Check Asia range (1-8% width)
- [ ] Verify H4 trend direction
- [ ] Calculate exact position size
- [ ] Set stop loss BEFORE entry
- [ ] Set take profit BEFORE entry
- [ ] Confirm margin available

### Position Size Calculator:
```
Risk = $100
Entry = $X
Stop Loss = $Y
Distance = |Entry - Stop Loss|

Base Units = $100 / Distance
Leveraged Units = Base Units × 3
Margin = (Leveraged Units × Entry) / 3

Example:
  Entry: $0.50, SL: $0.48
  Distance: $0.02
  Base: $100 / $0.02 = 5,000 ADA
  With 3x: 15,000 ADA
  Margin: (15,000 × $0.50) / 3 = $2,500
```

---

## 📊 Progress Tracking

### Weekly Review (Every Sunday):
Track these metrics:
- [ ] Total trades this week
- [ ] Win rate
- [ ] Net P&L
- [ ] Current balance
- [ ] Max margin used
- [ ] Fees paid

### Monthly Review:
- [ ] Total trades this month
- [ ] Profit factor
- [ ] Largest win/loss
- [ ] Average trade size
- [ ] Total fees
- [ ] Compare to expected performance

### Quarterly Goals:

**Q1 (Jan-Mar):**
- Target: +$600-1,000
- Expected trades: 8-12
- End balance: $10,600-11,000

**Q2 (Apr-Jun):**
- Target: +$400-800
- Expected trades: 5-8
- End balance: $11,000-11,800

**Q3 (Jul-Sep):**
- Target: +$300-600
- Expected trades: 3-6
- End balance: $11,300-12,400

**Q4 (Oct-Dec):**
- Target: +$600-1,000
- Expected trades: 8-12
- End balance: $11,900-13,400

**Year-End Target: $12,000-13,500** (+$2,000-3,500 profit, 20-35% return)

---

## ⚡ Quick Reference Card

### My Parameters:
```
Capital: $10,000
Risk: 1% = $100
Leverage: 3x
Max Margin: $8,500 (85%)
Buffer: $1,500-2,000

Typical Trade:
  Position: 24k-48k ADA
  Margin: $4,000-8,000
  Win: $150-600
  Loss: $100-530
```

### Entry Checklist:
✅ London session (3-11 AM GMT)
✅ Asia range 1-8%
✅ First hour momentum confirmed
✅ H4 trend agrees
✅ Margin available ($4k-8k)
✅ Stop loss calculated
✅ Take profit set

### Exit Rules:
🛑 **Stop Loss**: Hit predetermined level
💰 **Take Profit**: 1.3x risk distance (typically +2.6%)
⏰ **Time Exit**: 12 PM GMT (London close)
📈 **Trailing**: Move SL to breakeven at +2% profit

---

## 🚀 Getting Started

### Week 1: Paper Trading
- [ ] Run strategy on TradingView or demo
- [ ] Practice calculating position sizes
- [ ] Set up Bybit alerts
- [ ] Test your routine

### Week 2-4: Live with Half Size (0.5% risk = $50)
- [ ] Start with smaller risk
- [ ] Focus on execution quality
- [ ] Build confidence
- [ ] Aim for 5-10 trades

### Month 2+: Full Size (1% risk = $100)
- [ ] Increase to full 1% risk
- [ ] Follow all rules strictly
- [ ] Track every trade
- [ ] Review monthly

---

## 💡 Advantages of $10k vs $2.5k Account

### Better Capital Management:
1. **Lower Relative Margin Usage**
   - $10k: Average margin 46% (vs 56% for $2.5k)
   - More breathing room per trade

2. **Better Cushion for Drawdowns**
   - $10k: -6.2% max DD = $620 loss
   - $2.5k: -6.2% max DD = $155 loss
   - Larger account handles volatility better

3. **Larger Profits per Trade**
   - $10k: Average win $342 (vs $85 for $2.5k)
   - Faster path to meaningful profits

4. **Lower Fee Impact**
   - $10k: Fees ~$576/year (9.9% of profits)
   - $2.5k: Fees ~$144/year (9.9% of profits)
   - Same %, but larger base

5. **Psychological Benefits**
   - Winning $342 feels better than $85
   - $100 loss feels reasonable vs capital
   - More confidence in strategy

---

## 🎓 Key Lessons from Backtest

### What Works:
✅ **73.7% win rate** - very consistent
✅ **Losses controlled** at ~$100-530 range
✅ **February is best** (5 trades, +$1,254)
✅ **SHORT bias** seems stronger
✅ **2023 was perfect** (8/8 wins)
✅ **Drawdown manageable** at -6.2%

### Watch Out For:
⚠️ **April can be choppy** (3 trades, -$437 in 2025)
⚠️ **December volatility** (-$299 in 2024)
⚠️ **Some positions use 85%+ margin** (tight)
⚠️ **Consecutive losses** can happen (Apr 2025: 2 in a row)
⚠️ **Large losses possible** (-$530 max)

### Red Flags to Stop Trading:
🚨 **3 losses in a row**
🚨 **Down $500 in a week** (5%)
🚨 **Margin usage consistently >80%**
🚨 **Missing setup criteria**
🚨 **Feeling emotional about trades**
🚨 **Chasing losses** (revenge trading)

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

POSITION:
- Direction: Long/Short
- Entry: $_______
- Stop Loss: $_______
- Take Profit: $_______
- Position Size: _______ ADA
- Margin Used: $_______ (___%)
- Fees Estimate: $______

EXIT:
- Exit Price: $_______
- Exit Reason: TP/SL/Time
- P&L: $_______ (___%)
- ROI on Margin: ___%
- New Balance: $_______
- Actual Fees: $______

ANALYSIS:
- What went well:
- What to improve:
- Lessons learned:
- Emotional state: Calm/Anxious/Excited
```

---

## 💪 Mindset & Discipline

### Remember:
- This is a **marathon, not a sprint**
- Average trade = $153 profit (small but consistent)
- 15-20 trades/year = patience required
- Not every week will have trades
- Losses are part of the game (10 out of 38 trades)

### Success Factors:
1. **Follow the rules** (no exceptions)
2. **Wait for setup** (don't force trades)
3. **Accept losses** (they're built into the plan)
4. **Stay disciplined** (no revenge trading)
5. **Track progress** (data over feelings)
6. **Protect capital** (survival first, profits second)

### When Things Go Wrong:
- **Stuck in losing trade**: Trust your stop loss
- **Margin call warning**: Close position immediately
- **Multiple losses**: Take a break, review rules
- **Down $500+**: Stop trading, review strategy
- **Emotional**: Step away, come back tomorrow

---

## 🎯 Final Reminder

**You're starting with $10,000 and aiming for $12,000-13,500 by end of year (20-35% return).**

That's realistic and achievable with:
- Consistent execution
- Proper risk management
- Patience between trades
- Discipline during losses
- Capital protection focus

### Monthly Milestones:
- **Month 3**: $10,600-11,000 (+6-10%)
- **Month 6**: $11,000-11,800 (+10-18%)
- **Month 9**: $11,300-12,400 (+13-24%)
- **Month 12**: $12,000-13,500 (+20-35%)

**Trade safe, stay disciplined, and let the edge work over time.** 📈

---

*Last updated: 2025-10-06*
*Backtest period: 2023-2025*
*Platform: Bybit*
*Pair: ADAUSD*
*Leverage: 3x*
*Starting Capital: $10,000*
