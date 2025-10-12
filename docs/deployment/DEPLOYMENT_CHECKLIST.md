# 🚀 Quick Deployment Checklist

## Pre-Flight Checks

### ✅ Configuration
- [ ] `deployment/config_live.json` exists
- [ ] `bear_market_asset` set to `"GLD"`
- [ ] `bear_allocation` set to `1.0`
- [ ] `dry_run` set to `true` (for testing)
- [ ] Stock universe configured (50 stocks)
- [ ] Rebalance time set (default: 09:35)

### ✅ Broker Setup
- [ ] Broker account active (IBKR/Bybit/MT5)
- [ ] API credentials configured
- [ ] Paper trading account ready
- [ ] Broker platform running (if IBKR)
- [ ] API enabled in broker settings

### ✅ System Ready
- [ ] Python 3.8+ installed
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Logs directory exists (`logs/`)

---

## Testing Phase

### Step 1: Dry Run Test (Required)
```bash
python deployment/live_nick_radge.py --broker ibkr
```

**Verify:**
- [ ] Connects to broker ✅
- [ ] Downloads market data (51 assets) ✅
- [ ] Calculates regime correctly ✅
- [ ] Ranks stocks ✅
- [ ] Generates allocations ✅
- [ ] Shows order preview (dry run) ✅
- [ ] No errors in logs ✅

**If ANY failures → STOP and fix before proceeding!**

---

### Step 2: Paper Trading (1 Month)

**Setup:**
- [ ] Keep `"dry_run": true` OR use paper account
- [ ] IBKR: Port 7497 (paper) | Bybit: `testnet: true`

**Daily monitoring:**
- [ ] Run script daily at 9:35 AM
- [ ] Check logs for errors
- [ ] Verify positions match strategy
- [ ] Track performance

**Success Criteria:**
- [ ] No errors for 1 month ✅
- [ ] Positions update correctly ✅
- [ ] Regime detection working ✅
- [ ] GLD allocated in BEAR (if occurred) ✅
- [ ] Performance reasonable ✅

---

## Go Live Phase

### Step 3: Live Deployment (Small Capital)

**⚠️ Only proceed if paper trading successful!**

**Configuration Changes:**
```json
{
  "dry_run": false,  // ← Change to false
  "ibkr": {
    "port": 7496    // ← Live port (was 7497)
  }
}
```

**Pre-launch:**
- [ ] Start with SMALL capital ($10k or less)
- [ ] Broker live account connected
- [ ] Emergency shutdown plan ready
- [ ] Monitoring setup

**First Live Run:**
```bash
python deployment/live_nick_radge.py --broker ibkr
```

**Watch First Trades:**
- [ ] Orders execute correctly ✅
- [ ] Fills at reasonable prices ✅
- [ ] Positions match allocation ✅
- [ ] Fees acceptable ✅
- [ ] GLD tradeable ✅

---

## Ongoing Monitoring

### Daily (First Month)
- [ ] Check logs: `tail -f logs/live_nick_radge.log`
- [ ] Verify positions in broker
- [ ] Monitor for errors
- [ ] Track performance

### Weekly
- [ ] Review performance vs backtest
- [ ] Check drawdown levels
- [ ] Verify execution quality

### Monthly
- [ ] Full performance review
- [ ] Compare metrics (return, Sharpe, DD)
- [ ] Adjust if needed

### Quarterly (Rebalance Days)
- [ ] **Monitor CLOSELY on Jan 1, Apr 1, Jul 1, Oct 1**
- [ ] Watch execution logs
- [ ] Verify all orders filled
- [ ] Confirm new positions match target

---

## Expected Performance

### Target Metrics (From Backtest)
- **Total Return:** ~221% over 5 years
- **Annualized:** ~23%
- **Sharpe Ratio:** ~1.19
- **Max Drawdown:** ~-32%
- **Win Rate:** ~63%

### Acceptable Live Variance
- Annual return: ±5% (18-28%)
- Sharpe: ±0.2 (0.99-1.39)
- Drawdown: ±5% (27-37%)

### Red Flags 🚨
- Annual return < 15%
- Sharpe < 0.7
- Drawdown > 40%
- Win rate < 50%

**If red flags persist for 3+ months → Review strategy!**

---

## Emergency Procedures

### If Something Goes Wrong:

**1. Stop the script:**
```bash
pkill -f live_nick_radge.py
```

**2. Switch back to dry run:**
Edit `config_live.json`: `"dry_run": true`

**3. Review logs:**
```bash
tail -100 logs/live_nick_radge.log | grep ERROR
```

**4. Close positions manually** (if needed):
- Use broker platform to flatten positions
- Wait until issue resolved

**5. Debug and fix:**
- Identify root cause
- Test fix in dry run
- Restart when confident

---

## Automation Setup

### Option 1: Cron (Mac/Linux)
```bash
crontab -e

# Add this line (runs daily at 9:35 AM ET)
35 9 * * 1-5 cd /path/to/strategy_factory && venv/bin/python deployment/live_nick_radge.py --broker ibkr >> logs/cron.log 2>&1
```

### Option 2: Task Scheduler (Windows)
- Open Task Scheduler
- Create Daily Task at 9:35 AM
- Run: `venv\Scripts\python.exe deployment\live_nick_radge.py --broker ibkr`

### Option 3: VPS (Cloud)
- Deploy to AWS/DigitalOcean
- Setup cron
- Monitor remotely

---

## Final Go/No-Go Checklist

Before switching `dry_run: false`:

- [ ] ✅ Dry run tested successfully
- [ ] ✅ Paper trading completed (1 month)
- [ ] ✅ All logs reviewed (no errors)
- [ ] ✅ Strategy understood
- [ ] ✅ Starting with small capital
- [ ] ✅ Monitoring plan in place
- [ ] ✅ Emergency shutdown known
- [ ] ✅ Risk tolerance acceptable
- [ ] ✅ Long-term commitment (3+ years)
- [ ] ✅ Comfortable with -32% drawdown risk

**All checked? You're READY! 🚀**

---

## Quick Reference

### Run Commands
```bash
# Dry run test
python deployment/live_nick_radge.py --broker ibkr

# Check logs
tail -f logs/live_nick_radge.log

# View last 100 lines
tail -100 logs/live_nick_radge.log

# Search for errors
grep ERROR logs/live_nick_radge.log

# Kill script
pkill -f live_nick_radge.py
```

### Key Files
- **Strategy Config:** `deployment/config_live.json`
- **Broker Config:** `deployment/config.json`
- **Live Script:** `deployment/live_nick_radge.py`
- **Logs:** `logs/live_nick_radge.log`

### Support Docs
- [LIVE_DEPLOYMENT_GUIDE.md](LIVE_DEPLOYMENT_GUIDE.md) - Full deployment guide
- [GLD_WINNER_REPORT.md](GLD_WINNER_REPORT.md) - Performance analysis
- [HOW_STOCK_SELECTION_WORKS.md](HOW_STOCK_SELECTION_WORKS.md) - Strategy explained

---

**Remember:** Start small, test thoroughly, monitor closely. Good luck! 🏆
