# Live Deployment Guide - Nick Radge + GLD Strategy

## 🎯 Strategy Overview

**Strategy Name:** Nick Radge Momentum + GLD 100%

**Proven Performance (2020-2025):**
- Total Return: +221.06%
- Annualized Return: 23.47%
- Sharpe Ratio: 1.19
- Win Rate: 63.0%
- Max Drawdown: -32.38%
- **Beat SPY by +21.62%**

**How It Works:**
- **STRONG_BULL (56% of time):** Hold 7 top momentum stocks
- **WEAK_BULL (5% of time):** Hold 3 top momentum stocks
- **BEAR (26% of time):** Hold 100% GLD (Gold ETF)
- **Rebalance:** Quarterly (Jan 1, Apr 1, Jul 1, Oct 1)
- **Regime Recovery:** Auto re-enter stocks when BEAR → BULL

---

## 📋 Pre-Deployment Checklist

### ✅ 1. System Requirements

- [ ] Python 3.8+ installed
- [ ] Virtual environment setup (`venv` folder exists)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Broker account active (IBKR, Bybit, or MT5)
- [ ] API credentials configured
- [ ] Minimum capital available ($10,000+ recommended)

### ✅ 2. Configuration Files

**Check these files exist:**
- [ ] `deployment/config_live.json` (strategy config)
- [ ] `deployment/config.json` (broker config)
- [ ] `deployment/live_nick_radge.py` (live trading script)

### ✅ 3. Strategy Configuration

**Verify `deployment/config_live.json` has:**

```json
{
  "strategy_name": "Nick Radge Momentum + GLD",
  "portfolio_size": 7,
  "roc_period": 100,
  "ma_period": 100,
  "strong_bull_positions": 7,
  "weak_bull_positions": 3,
  "bear_positions": 0,
  "bear_market_asset": "GLD",        // ← CRITICAL: Must be "GLD"
  "bear_allocation": 1.0,             // ← CRITICAL: Must be 1.0
  "stock_universe": [...],            // Your 50 stocks
  "lookback_days": 200,
  "max_position_size": 0.2,
  "rebalance_time": "09:35",         // After market open
  "check_interval_minutes": 60,
  "dry_run": true                    // ← Start with true!
}
```

### ✅ 4. Broker Configuration

**Setup `deployment/config.json`:**

```json
{
  "ibkr": {
    "host": "127.0.0.1",
    "port": 7497,              // Paper trading: 7497, Live: 7496
    "client_id": 1,
    "account": "YOUR_ACCOUNT_ID"
  },
  "bybit": {
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_SECRET",
    "testnet": true            // Start with testnet!
  },
  "mt5": {
    "login": "YOUR_LOGIN",
    "password": "YOUR_PASSWORD",
    "server": "YOUR_SERVER"
  }
}
```

**⚠️ IMPORTANT:** Start with paper/testnet accounts!

---

## 🚀 Deployment Steps

### Step 1: Dry Run Test (REQUIRED)

**Purpose:** Test the strategy without real money.

```bash
# Make sure dry_run: true in config_live.json
python deployment/live_nick_radge.py --broker ibkr

# Or specify broker
python deployment/live_nick_radge.py --broker bybit
python deployment/live_nick_radge.py --broker mt5
```

**What to verify:**
- ✅ Script connects to broker
- ✅ Downloads market data (50 stocks + GLD + SPY)
- ✅ Calculates regime correctly
- ✅ Ranks stocks by momentum
- ✅ Calculates target allocations
- ✅ Generates orders (but doesn't submit in dry run)
- ✅ Logs all actions

**Expected Output:**

```
✅ Connected to ibkr
📥 Downloading market data...
   Downloading 51 stocks...
   Adding bear market asset: GLD
   ✅ Downloaded 51 stocks

📊 Calculating target allocations...
   Current regime: STRONG_BULL
   Portfolio size: 7 positions

   Ranked 45 stocks, selected top 7

💼 Target Allocations:
   NVDA: 18.50%
   AAPL: 16.20%
   MSFT: 15.80%
   GOOGL: 14.30%
   AMZN: 12.40%
   META: 11.90%
   TSLA: 10.90%

📈 Placing orders (DRY RUN):
   BUY 12 shares NVDA @ $450.23
   BUY 45 shares AAPL @ $185.67
   ...

✅ Dry run complete - no real orders placed
```

**If any errors occur, STOP and fix them before proceeding!**

---

### Step 2: Paper Trading Test (1 Month)

**Purpose:** Test with fake money in real market conditions.

**Setup:**
1. Keep `dry_run: true` OR
2. Use paper trading account:
   - IBKR: Port 7497
   - Bybit: `"testnet": true`

**Run for 1 month:**

```bash
# Run daily (or use cron/scheduler)
python deployment/live_nick_radge.py --broker ibkr
```

**Monitor:**
- Check logs daily: `logs/live_nick_radge.log`
- Verify positions match strategy
- Track performance vs backtest expectations
- Look for any errors or anomalies

**Success Criteria (After 1 Month):**
- ✅ No errors in logs
- ✅ Positions updated correctly on rebalance days
- ✅ Regime detection working
- ✅ GLD allocated during BEAR (if BEAR occurred)
- ✅ Performance reasonable (not exactly matching backtest, but close)

---

### Step 3: Go Live (Small Capital)

**⚠️ CRITICAL: Only proceed if paper trading was successful!**

**Setup:**
1. Update `config_live.json`:
   ```json
   {
     "dry_run": false  // ← Change to false
   }
   ```

2. Update broker to live account:
   ```json
   {
     "ibkr": {
       "port": 7496,  // ← Live port
       ...
     }
   }
   ```

3. **Start with SMALL capital** (e.g., $10,000 or less)

**First Live Run:**

```bash
python deployment/live_nick_radge.py --broker ibkr
```

**⚠️ WATCH CLOSELY:**
- Monitor first few trades
- Verify orders execute correctly
- Check fills, prices, commissions
- Ensure GLD can be traded (some brokers may restrict)

---

### Step 4: Scale Up (After 1-3 Months)

**Once comfortable:**
- Increase capital gradually
- Monitor performance vs backtest
- Adjust if needed

**Expected Performance:**
- Annualized Return: ~20-25%
- Sharpe Ratio: ~1.0-1.2
- Max Drawdown: ~25-35%

**⚠️ If performance significantly deviates, investigate!**

---

## 🤖 Automation Options

### Option 1: Manual Daily Execution

**Pros:** Full control
**Cons:** Must run manually

```bash
# Run once per day at 9:35 AM (after market open)
python deployment/live_nick_radge.py --broker ibkr
```

---

### Option 2: Cron Job (Linux/Mac)

**Setup:**

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9:35 AM ET)
35 9 * * 1-5 cd /path/to/strategy_factory && venv/bin/python deployment/live_nick_radge.py --broker ibkr >> logs/cron.log 2>&1
```

---

### Option 3: Task Scheduler (Windows)

**Setup:**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 9:35 AM
4. Action: Start Program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `deployment\live_nick_radge.py --broker ibkr`
   - Start in: `C:\path\to\strategy_factory`

---

### Option 4: Cloud Deployment (VPS)

**Recommended for 24/7 operation**

**Providers:**
- AWS EC2
- DigitalOcean
- Vultr
- Linode

**Setup:**
1. Create Linux VPS
2. Clone repository
3. Install dependencies
4. Setup cron job
5. Monitor remotely

**Cost:** ~$5-20/month

---

## 📊 Monitoring & Maintenance

### Daily Checks

**Every trading day:**
- [ ] Check logs for errors: `tail -f logs/live_nick_radge.log`
- [ ] Verify positions in broker dashboard
- [ ] Check regime classification (logged)
- [ ] Monitor capital utilization

**What to look for:**
- ✅ "✅ Connected to broker"
- ✅ "📊 Calculating target allocations"
- ✅ "💼 Target Allocations: ..."
- ✅ "📈 Placing orders..."
- ⚠️ Any ERROR messages

---

### Weekly Checks

**Every week:**
- [ ] Review performance vs backtest
- [ ] Check drawdown levels
- [ ] Verify all positions executing correctly
- [ ] Review GLD allocation (if in BEAR regime)

**Performance Metrics:**
- Weekly return vs SPY
- Running Sharpe ratio
- Current drawdown

---

### Monthly Checks

**Every month:**
- [ ] Full performance review
- [ ] Compare to backtest expectations
- [ ] Rebalance verification (if quarter-end)
- [ ] Review strategy parameters (any adjustments needed?)

**Questions to ask:**
- Is performance within expected range?
- Are costs (fees/slippage) reasonable?
- Is regime detection accurate?
- Should any parameters be adjusted?

---

### Quarterly Events

**On rebalance days (Jan 1, Apr 1, Jul 1, Oct 1):**

**CRITICAL - Monitor closely!**

**Morning (before 9:35 AM):**
- [ ] Ensure script will run
- [ ] Check broker connection
- [ ] Verify sufficient buying power

**After execution (9:35 AM - 10:00 AM):**
- [ ] Watch for execution logs
- [ ] Verify orders filled
- [ ] Check new positions
- [ ] Monitor for errors

**End of day:**
- [ ] Confirm portfolio matches target
- [ ] Review execution quality (prices, fills)
- [ ] Document any issues

---

## 🚨 Safety Features Built-In

### Automatic Safeguards

1. **Dry Run Mode**
   - Default: `"dry_run": true`
   - No real orders until you explicitly set to `false`

2. **Max Position Size**
   - Config: `"max_position_size": 0.2`
   - No single position > 20% of capital

3. **Regime Recovery**
   - Automatically exits GLD when BEAR → BULL
   - Prevents being stuck in cash/gold

4. **Balance Check**
   - Auto-retrieves capital from broker
   - No manual capital specification needed

5. **Logging**
   - All actions logged to `logs/live_nick_radge.log`
   - Easy debugging and audit trail

---

## ⚠️ Risk Management

### Position Sizing

**Default allocation:**
- STRONG_BULL: 7 stocks (momentum-weighted)
- WEAK_BULL: 3 stocks (momentum-weighted)
- BEAR: 100% GLD

**Max per position:** 20% (configurable)

**Typical allocation:**
- Top stock: 15-20%
- 2nd-3rd stocks: 12-15%
- 4th-7th stocks: 8-12%

---

### Stop Losses

**Built-in protection:**
- Quarterly rebalancing naturally cuts losing positions
- Stocks that fall out of top 7 are sold
- No explicit stop losses (momentum-based exits)

**Optional enhancement:**
- Add manual stop at -40% portfolio drawdown
- Pause strategy if consecutive losing quarters

---

### Emergency Shutdown

**If things go wrong:**

```bash
# 1. Kill running script
pkill -f live_nick_radge.py

# 2. Set dry_run back to true
# Edit config_live.json: "dry_run": true

# 3. Manually close positions in broker if needed

# 4. Review logs
tail -100 logs/live_nick_radge.log

# 5. Fix issue before restarting
```

---

## 📈 Expected Performance

### Based on 5-Year Backtest

**Annual Returns:**
- Expected: 20-25%
- Best year: ~60%
- Worst year: -20%

**Risk:**
- Max Drawdown: 25-35%
- Volatility: ~24%
- Sharpe Ratio: 1.0-1.2

**Win Rate:**
- ~60-65% positive months
- ~53-54% positive months overall

---

### Live vs Backtest Differences

**Why live may differ:**

1. **Slippage** - Real fills vs mid prices
2. **Fees** - Actual commissions
3. **Market impact** - Your orders affect prices (if large)
4. **Data differences** - Yahoo Finance vs live broker data
5. **Execution timing** - 9:35 AM vs perfect backtest timing

**Acceptable variance:**
- ±5% annual return is normal
- ±0.1-0.2 Sharpe ratio is normal
- Slightly lower returns expected (fees/slippage)

**Red flags:**
- >10% underperformance annually
- Sharpe ratio <0.7
- Win rate <50%

---

## 🔧 Troubleshooting

### Common Issues

**Issue:** "Failed to connect to broker"
- **Fix:** Check broker platform is running (IBKR TWS/Gateway)
- **Fix:** Verify port number (7497 paper, 7496 live)
- **Fix:** Check API settings enabled in broker

**Issue:** "GLD not found in universe"
- **Fix:** Ensure `"bear_market_asset": "GLD"` in config
- **Fix:** Verify GLD is tradeable on your broker
- **Fix:** Check ticker symbol (some brokers use different symbols)

**Issue:** "No stocks passed filters"
- **Fix:** Check market regime (may be BEAR = no stock positions)
- **Fix:** Review ROC/MA filters (may be too strict)
- **Fix:** Verify data download successful

**Issue:** "Insufficient buying power"
- **Fix:** Check account balance
- **Fix:** Close existing positions if needed
- **Fix:** Reduce `max_position_size` in config

**Issue:** "Orders not executing"
- **Fix:** Check `"dry_run": false` in config
- **Fix:** Verify broker connection
- **Fix:** Check market hours (9:30 AM - 4:00 PM ET)
- **Fix:** Review order logs for rejection reasons

---

## 📝 Logging & Debugging

### Log Files

**Location:** `logs/live_nick_radge.log`

**What's logged:**
- Broker connections
- Data downloads
- Regime calculations
- Stock rankings
- Target allocations
- Order placements
- Execution confirmations
- Errors

**View logs:**

```bash
# Real-time monitoring
tail -f logs/live_nick_radge.log

# Last 100 lines
tail -100 logs/live_nick_radge.log

# Search for errors
grep ERROR logs/live_nick_radge.log

# Search for specific date
grep "2025-10-09" logs/live_nick_radge.log
```

---

## 🎓 Best Practices

### DO:
✅ Start with dry run
✅ Test with paper trading first
✅ Start with small capital
✅ Monitor daily for first month
✅ Keep logs for audit trail
✅ Review performance monthly
✅ Have emergency shutdown plan
✅ Understand the strategy fully

### DON'T:
❌ Skip dry run testing
❌ Go live with large capital immediately
❌ Ignore errors in logs
❌ Override strategy manually (unless emergency)
❌ Change parameters frequently
❌ Panic on short-term losses
❌ Deploy without understanding risk

---

## 📞 Support & Resources

### Documentation
- [BEAR_MARKET_TRADING.md](BEAR_MARKET_TRADING.md) - Bear market strategy guide
- [GLD_WINNER_REPORT.md](GLD_WINNER_REPORT.md) - GLD test results
- [HOW_STOCK_SELECTION_WORKS.md](HOW_STOCK_SELECTION_WORKS.md) - Stock selection explained
- [WEAK_BULL_EXPLANATION.md](WEAK_BULL_EXPLANATION.md) - Regime system explained

### Files
- `deployment/config_live.json` - Strategy configuration
- `deployment/config.json` - Broker configuration
- `deployment/live_nick_radge.py` - Live trading script
- `logs/live_nick_radge.log` - Execution logs

### Community
- GitHub Issues: Report bugs or ask questions
- Pull Requests: Contribute improvements

---

## ✅ Final Deployment Checklist

Before going live:

- [ ] Completed dry run successfully
- [ ] Tested 1 month paper trading
- [ ] Reviewed all logs (no errors)
- [ ] Understand the strategy
- [ ] Set `"dry_run": false`
- [ ] Started with small capital
- [ ] Have monitoring plan
- [ ] Know how to emergency shutdown
- [ ] Comfortable with expected risks
- [ ] Ready to commit long-term (3+ years)

**If all checked, you're ready to deploy!** 🚀

---

## 🎯 Next Steps

1. **Test in dry run:** `python deployment/live_nick_radge.py --broker ibkr`
2. **Review this guide** completely
3. **Paper trade for 1 month**
4. **Go live with small capital**
5. **Monitor and scale up**

**Good luck! The backtest shows +221% returns over 5 years. Time to make it real!** 🏆

---

*Remember: Past performance doesn't guarantee future results. Trade responsibly and within your risk tolerance.*
