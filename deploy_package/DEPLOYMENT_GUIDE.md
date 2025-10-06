# Live Deployment Guide
## London Breakout v4.1 - FTMO Trading System

**Last Updated:** October 6, 2025
**Version:** 4.1 (FTMO Compliant)

---

## ⚠️ CRITICAL WARNING

**DO NOT deploy this system live without:**
1. ✅ Completing 3-6 months of paper trading
2. ✅ Understanding every parameter
3. ✅ Having emergency procedures in place
4. ✅ Accepting that you can lose money

**This system has been backtested but NOT live-tested. Past performance does NOT guarantee future results.**

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Installation & Setup](#installation--setup)
3. [Configuration](#configuration)
4. [Paper Trading Phase](#paper-trading-phase)
5. [Going Live](#going-live)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Emergency Procedures](#emergency-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### ☐ 1. System Requirements

- [ ] Windows 10/11 or Windows VPS
- [ ] MetaTrader 5 installed and configured
- [ ] Python 3.9+ installed
- [ ] Stable internet connection (VPS recommended)
- [ ] MetaTrader5 Python package installed (`pip install MetaTrader5`)

### ☐ 2. Account Preparation

- [ ] FTMO/Prop firm account approved and funded
- [ ] Account credentials available
- [ ] MT5 login working correctly
- [ ] Initial balance recorded: $__________

### ☐ 3. Knowledge Requirements

- [ ] Read and understood [FINAL_BACKTEST_REPORT.md](FINAL_BACKTEST_REPORT.md)
- [ ] Read and understood [HONEST_ASSESSMENT.md](HONEST_ASSESSMENT.md)
- [ ] Reviewed backtest results and expectations
- [ ] Understand risk: Can handle -9.78% drawdown psychologically
- [ ] Understand FTMO rules (max -10% loss, max -5% daily loss)

### ☐ 4. Risk Acceptance

- [ ] Comfortable with 1.5% risk per trade
- [ ] Prepared for potential losing months (like July 2025: -$3,378)
- [ ] Can wake up at 3 AM London time consistently
- [ ] Have contingency plan if strategy stops working
- [ ] Realistic expectations: $15-22k/year, NOT $128k

---

## Installation & Setup

### Step 1: Install Dependencies

```bash
# Navigate to project directory
cd /Users/karlomarceloestrada/Documents/@Projects/02_MT5_triangle

# Install required packages
pip install MetaTrader5 pandas numpy

# Verify installation
python -c "import MetaTrader5 as mt5; print('MT5 version:', mt5.__version__)"
```

### Step 2: Configure MT5

1. Open MetaTrader 5
2. Go to Tools → Options → Expert Advisors
3. Enable:
   - ✅ Allow automated trading
   - ✅ Allow DLL imports
   - ✅ Allow WebRequests
4. Click OK

### Step 3: Test MT5 Connection

```bash
python -c "
import MetaTrader5 as mt5

if not mt5.initialize():
    print('Failed to initialize MT5')
else:
    print('✅ MT5 initialized successfully')
    account = mt5.account_info()
    print(f'Account: {account.login}')
    print(f'Balance: ${account.balance:,.2f}')
    mt5.shutdown()
"
```

### Step 4: Create Directories

```bash
mkdir -p live/logs
mkdir -p live/data
```

---

## Configuration

### Edit `live/config_live.py`

**CRITICAL SETTINGS TO REVIEW:**

```python
# 1. RISK SETTINGS
RISK_PER_TRADE = 1.5  # Start conservative at 1.0%, increase to 1.5% after success

# 2. SAFETY SETTINGS
SAFETY_STOP_AT_DD_PCT = 8.5  # Stop before hitting -10% FTMO limit
SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.0  # Stop before hitting -5% daily limit

# 3. PAPER TRADING MODE (IMPORTANT!)
PAPER_TRADE_MODE = True  # MUST be True initially!

# 4. ACCOUNT SETTINGS
INITIAL_BALANCE = 100000  # Your actual account balance
ACCOUNT_TYPE = 'FTMO'

# 5. STRATEGY TOGGLES
STRATEGY_PARAMS = {
    'enable_asia_breakout': True,
    'enable_triangle_breakout': True,  # Set False for simpler Asia-only
    # ... other params (DO NOT CHANGE optimized values)
}
```

### Validate Configuration

```bash
python live/config_live.py
```

Expected output:
```
================================================================================
LIVE TRADING CONFIGURATION VALIDATION
================================================================================

Account Type: FTMO
Risk Per Trade: 1.5%
Paper Trade Mode: True
Asia Breakout: True
Triangle Patterns: True

Validating...
✅ Configuration validated successfully
```

---

## Paper Trading Phase

**MANDATORY: 3-6 months minimum**

### Week 1-2: System Familiarization

**Goal:** Get comfortable with the system

- [ ] Run system in paper mode
- [ ] Observe how it detects patterns
- [ ] Check logs daily
- [ ] Verify trades make sense
- [ ] No changes to parameters!

**Daily Routine:**
```bash
# Start trader
python live/live_trader.py

# Check logs (in another terminal)
tail -f live/logs/trading.log

# Stop trader: Press Ctrl+C
```

### Month 1-3: Performance Validation

**Goal:** Verify strategy performs as expected

**Track these metrics:**
- [ ] Win rate: Target 55-65%
- [ ] Monthly P&L: Target $1,000-$2,000
- [ ] Max drawdown: Should stay under -5%
- [ ] Daily loss: Should never exceed -3%

**Create tracking spreadsheet:**

| Date | Trades | Wins | Losses | P&L | DD % | Notes |
|------|--------|------|--------|-----|------|-------|
| Oct 6 | 2 | 1 | 1 | $450 | -0.2% | Asia breakouts |
| ... | ... | ... | ... | ... | ... | ... |

**Acceptance Criteria (ALL must pass):**
- ✅ Win rate: 55-65%
- ✅ Average monthly P&L: $800-$2,000
- ✅ Max DD: <8%
- ✅ No daily loss >4%
- ✅ Psychologically comfortable with losses
- ✅ Can maintain 3 AM wake-up schedule

**Rejection Criteria (any = STOP):**
- ❌ Win rate <50% for 2+ months
- ❌ Monthly P&L negative for 2+ months
- ❌ Drawdown >10% at any point
- ❌ Cannot handle emotional stress
- ❌ Cannot maintain trading schedule

---

## Going Live

### Pre-Live Final Checklist

**DO NOT go live unless ALL are checked:**

- [ ] Paper traded successfully for 3-6 months
- [ ] All acceptance criteria met
- [ ] Understand every parameter
- [ ] Read emergency procedures below
- [ ] VPS setup (recommended for 24/7 operation)
- [ ] Telegram/email alerts configured (optional but recommended)
- [ ] Backup plan if system fails
- [ ] Can afford to lose entire account (worst case)

### Going Live Steps

#### Step 1: Final Configuration Review

```python
# live/config_live.py

# CHANGE THIS:
PAPER_TRADE_MODE = False  # ⚠️ GOING LIVE!

# VERIFY THESE:
RISK_PER_TRADE = 1.0  # Start conservative, increase later
INITIAL_BALANCE = 100000  # Your actual FTMO balance
ACCOUNT_TYPE = 'FTMO'

# VERIFY SAFETY STOPS:
SAFETY_STOP_AT_DD_PCT = 8.5
SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.0
MAX_CONSECUTIVE_LOSSES = 5
```

#### Step 2: Start with Reduced Risk

**First 2 weeks live:**
- Risk: 1.0% (half normal)
- Monitor every trade
- Verify execution quality
- Check slippage

#### Step 3: Gradual Scale-Up

**If first 2 weeks successful:**
- Week 3-4: Increase to 1.25%
- Week 5-8: Increase to 1.5%
- Month 3+: Consider 1.75% if comfortable

#### Step 4: Launch

```bash
# Start in screen/tmux (for VPS) or as Windows service
python live/live_trader.py

# Monitor logs
tail -f live/logs/trading.log
```

---

## Monitoring & Maintenance

### Daily Routine (10 minutes)

**Every Morning (before 3 AM GMT):**
1. Check system is running
2. Review yesterday's trades
3. Check account balance
4. Verify no errors in logs

**Every Evening:**
1. Review day's trades
2. Update tracking spreadsheet
3. Check for alerts
4. Verify FTMO compliance

### Weekly Review (30 minutes)

**Every Sunday:**
- [ ] Calculate week's P&L
- [ ] Review win rate
- [ ] Check drawdown
- [ ] Compare to expectations
- [ ] Review any errors/issues
- [ ] Plan for next week

### Monthly Review (1-2 hours)

**End of month:**
- [ ] Generate performance report
- [ ] Compare to backtest expectations
- [ ] Review all trades
- [ ] Check parameter stability
- [ ] Decide: continue, adjust, or stop

**Monthly Review Template:**

```
Month: _______
Trades: ___
Win Rate: ___%
P&L: $_____
Max DD: ___%

vs Expected:
- Win Rate: 55-65% → Actual: ___%
- P&L: $1,000-2,000 → Actual: $_____
- Max DD: <8% → Actual: ___%

Continue? YES / NO / ADJUST
Notes: ___________________________
```

---

## Emergency Procedures

### 🚨 EMERGENCY STOP SCENARIOS

**Stop trading immediately if:**

1. **FTMO Violation Imminent**
   - Total DD approaching -9.5%
   - Daily loss approaching -4.5%
   - Action: STOP SYSTEM, close positions

2. **Unexpected Behavior**
   - Trades at wrong times
   - Wrong position sizes
   - Random errors
   - Action: STOP SYSTEM, investigate

3. **Technical Issues**
   - MT5 disconnection
   - VPS failure
   - Repeated order errors
   - Action: STOP SYSTEM, fix issue

4. **Personal Reasons**
   - Can't monitor
   - Health issues
   - Travel without VPS access
   - Action: STOP SYSTEM before leaving

### Emergency Stop Procedure

**Method 1: Keyboard Interrupt**
```bash
# Press Ctrl+C in terminal
```

**Method 2: Emergency Kill**
```bash
# Find process
ps aux | grep live_trader

# Kill it
kill -9 <PID>
```

**Method 3: MT5 Manual Stop**
1. Open MT5
2. Go to Tools → Options → Expert Advisors
3. Uncheck "Allow automated trading"
4. Manually close any open positions

### Post-Emergency Actions

1. [ ] Document what happened
2. [ ] Review logs for cause
3. [ ] Check account status
4. [ ] Close any open positions
5. [ ] Determine if safe to resume
6. [ ] Fix underlying issue
7. [ ] Test fix in paper mode
8. [ ] Resume only when confident

---

## Troubleshooting

### Common Issues

#### 1. "MT5 initialization failed"

**Cause:** MT5 not running or wrong settings

**Fix:**
```bash
# Check MT5 is running
# Check Tools → Options → Expert Advisors → Allow automated trading
# Restart MT5
# Try again
```

#### 2. "No trades being taken"

**Possible causes:**
- Not trading hours (3-11 AM GMT)
- Not trading day (weekdays only)
- Safety stop triggered
- PAPER_TRADE_MODE=True and no simulation logic

**Check:**
```python
# In live_trader.py logs
# Look for: "Trading disabled: <reason>"
```

#### 3. "Daily loss limit triggered early"

**Cause:** Account already had losses before system started

**Fix:**
- Restart system at start of new day
- Or adjust `DAILY_START_BALANCE` in safety manager

#### 4. "Positions not closing"

**Cause:** Exit logic not yet implemented (TODO in code)

**Temporary fix:**
- Manually close positions in MT5
- Monitor carefully until exit logic completed

---

## System Architecture

### File Structure

```
02_MT5_triangle/
├── live/
│   ├── config_live.py          # Configuration (edit this!)
│   ├── live_trader.py           # Main trading system
│   ├── logs/
│   │   └── trading.log          # System logs
│   └── data/
│       ├── trading_history.db   # Trade database
│       └── trading_state.json   # System state
├── strategies/
│   ├── strategy_breakout_v4_1_optimized.py  # Strategy logic
│   └── pattern_detector.py                   # Pattern detection
└── DEPLOYMENT_GUIDE.md          # This file
```

### Key Components

1. **FTMOSafetyManager**: Enforces FTMO rules
2. **LiveTrader**: Main trading loop
3. **Strategy**: Signal generation
4. **Config**: All adjustable parameters

---

## Risk Disclosure

**READ THIS CAREFULLY:**

1. **No Guarantees:** Past backtest performance (19.6% annual return) does NOT guarantee future results.

2. **Can Lose Money:** You can lose your entire FTMO account. The -9.78% max DD is based on historical data and could be exceeded.

3. **FTMO Rules:** One violation = account terminated. This system has safety stops but they may not always work.

4. **Technical Risk:** Software bugs, internet outages, MT5 issues can cause losses.

5. **Market Risk:** Strategy may stop working if market conditions change.

6. **Psychological Risk:** Watching losses can cause emotional decisions that override the system.

**By using this system, you accept full responsibility for all trading results.**

---

## Support & Resources

### Documentation
- [FINAL_BACKTEST_REPORT.md](FINAL_BACKTEST_REPORT.md) - Full backtest analysis
- [HONEST_ASSESSMENT.md](HONEST_ASSESSMENT.md) - Realistic expectations
- [BACKTEST_QUALITY_AUDIT.md](BACKTEST_QUALITY_AUDIT.md) - Quality analysis

### Configuration Files
- [live/config_live.py](live/config_live.py) - Main configuration

### Logs
- `live/logs/trading.log` - System logs
- `live/logs/paper_trades.csv` - Paper trading results

---

## Final Checklist Before Going Live

### Mandatory Steps (ALL must be YES)

- [ ] Paper traded for 3-6 months: YES / NO
- [ ] Win rate 55-65%: YES / NO
- [ ] Monthly P&L $800-2,000: YES / NO
- [ ] Max DD <8%: YES / NO
- [ ] Understand all parameters: YES / NO
- [ ] Read emergency procedures: YES / NO
- [ ] Can afford to lose account: YES / NO
- [ ] VPS setup (if using): YES / NO / N/A
- [ ] PAPER_TRADE_MODE = False: YES / NO
- [ ] RISK_PER_TRADE = 1.0% (starting): YES / NO

**If ANY answer is NO, do NOT go live yet.**

---

## Contact & Updates

**Project Location:**
`/Users/karlomarceloestrada/Documents/@Projects/02_MT5_triangle`

**Last Updated:** October 6, 2025
**Strategy Version:** 4.1
**Deployment Guide Version:** 1.0

---

**Good luck, trade safely, and remember: Preservation of capital is more important than profits.**

---

*This deployment guide is provided as-is. The author assumes no liability for trading losses. Trading involves substantial risk of loss.*
