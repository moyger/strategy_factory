# Strategy Monitoring Guide

## 📊 Daily Monitoring

### Morning Routine (Before Market Open)

**Time: 9:00 AM - 9:30 AM ET**

1. **Check System Status**
   ```bash
   # Verify script will run (if automated)
   crontab -l | grep live_nick_radge

   # Check last run status
   tail -20 logs/live_nick_radge.log
   ```

2. **Verify Broker Connection**
   - IBKR: Ensure TWS/Gateway running
   - Check API enabled
   - Confirm account accessible

3. **Review Market Conditions**
   - Check SPY price vs MA (regime indicator)
   - Note any major news/events
   - Check market hours (regular vs holiday)

---

### After Execution (9:35 AM - 10:00 AM)

**Monitor execution:**

```bash
# Watch logs in real-time
tail -f logs/live_nick_radge.log
```

**Verify:**
- ✅ Script executed successfully
- ✅ Market data downloaded
- ✅ Regime calculated
- ✅ Allocations computed
- ✅ Orders placed (if rebalance day)
- ✅ No errors

**Check broker platform:**
- Verify positions match expected
- Check order fills
- Review execution prices
- Confirm GLD position (if BEAR regime)

---

### End of Day (4:00 PM - 5:00 PM)

**Review:**

```bash
# Check full day logs
grep "$(date +%Y-%m-%d)" logs/live_nick_radge.log
```

**Metrics to track:**
- Daily P&L
- Current positions
- Cash balance
- Total portfolio value

**Document:**
- Any errors encountered
- Unusual market activity
- Strategy actions taken

---

## 📅 Weekly Monitoring

### Every Monday Morning

**Performance Review:**

1. **Calculate Weekly Metrics**
   ```python
   # Run this script
   python scripts/calculate_weekly_performance.py
   ```

2. **Compare vs Benchmarks**
   - Strategy return vs SPY
   - Strategy return vs GLD
   - Running Sharpe ratio

3. **Check Drawdown**
   - Current drawdown from peak
   - Max drawdown to date
   - Recovery status

4. **Review Logs**
   ```bash
   # Count errors in last week
   grep ERROR logs/live_nick_radge.log | grep "$(date -d '7 days ago' +%Y-%m)" | wc -l
   ```

**Health Check:**
- ✅ No critical errors
- ✅ All positions executing
- ✅ Performance within expected range
- ✅ Drawdown under control

---

## 📈 Monthly Monitoring

### First of Each Month

**Full Performance Review:**

1. **Generate Monthly Report**
   - Total return (month)
   - Best/worst day
   - Win rate
   - Sharpe ratio
   - Max drawdown

2. **Compare to Backtest**

   | Metric | Backtest | Live | Variance |
   |--------|----------|------|----------|
   | Monthly Return | 1.95% | ? | ? |
   | Win Rate | 63% | ? | ? |
   | Sharpe | 1.19 | ? | ? |
   | Max DD | -32.38% | ? | ? |

3. **Analyze Trades**
   - Total trades executed
   - Average win/loss
   - Profit factor
   - Commission costs

4. **Review Strategy Performance**
   - Regime distribution (BULL/BEAR/WEAK)
   - Stock selection accuracy
   - GLD allocation effectiveness
   - Rebalance quality

**Action Items:**
- Document any anomalies
- Adjust if significant deviation
- Update risk parameters if needed

---

## 🔄 Quarterly Monitoring

### Rebalance Day (Jan 1, Apr 1, Jul 1, Oct 1)

**⚠️ CRITICAL - HIGH ALERT DAY**

### Pre-Market (8:00 AM - 9:30 AM)

**Preparation:**
- [ ] Verify script will run
- [ ] Check broker connection
- [ ] Ensure sufficient buying power
- [ ] Review current positions
- [ ] Check for any restrictions (wash sales, etc.)

**Calculate Expected Changes:**
- What stocks likely to exit portfolio?
- What new stocks likely to enter?
- Will regime change (BULL ↔ BEAR)?
- GLD allocation expected?

---

### During Execution (9:35 AM - 10:30 AM)

**⚠️ ACTIVELY MONITOR**

```bash
# Watch execution in real-time
tail -f logs/live_nick_radge.log
```

**Monitor:**
- [ ] Data download successful
- [ ] Regime calculated correctly
- [ ] Rankings look reasonable
- [ ] Allocations computed
- [ ] Orders generated
- [ ] Orders submitted
- [ ] Orders filling

**In Broker Platform:**
- Watch order fills
- Check execution prices
- Verify quantities
- Monitor slippage

**If Issues Arise:**
1. Pause auto-execution
2. Investigate immediately
3. Manual intervention if needed
4. Document issue thoroughly

---

### Post-Execution (10:30 AM - 4:00 PM)

**Verification:**
- [ ] All orders filled
- [ ] Final positions match target allocations
- [ ] No pending orders
- [ ] Portfolio fully invested (or in GLD if BEAR)
- [ ] Cash balance appropriate

**Analysis:**
- Old positions closed
- New positions opened
- GLD allocation (if BEAR)
- Execution quality (prices vs VWAP)
- Commission costs

**Document:**
- Full rebalance details
- Any manual interventions
- Execution quality metrics
- Issues encountered

---

## 📊 Key Metrics Dashboard

### Daily Metrics

| Metric | Track | Alert If |
|--------|-------|----------|
| P&L | Daily $ change | Loss > -2% |
| Positions | # of holdings | ≠ expected |
| Cash | Available balance | < 5% of total |
| Errors | Log errors | Any critical |

### Weekly Metrics

| Metric | Track | Alert If |
|--------|-------|----------|
| Weekly Return | % change | < -5% |
| vs SPY | Relative performance | Underperform > 3% |
| Drawdown | From peak | > -20% |
| Sharpe | Rolling 30-day | < 0.5 |

### Monthly Metrics

| Metric | Track | Alert If |
|--------|-------|----------|
| Monthly Return | % change | < -10% |
| Win Rate | % positive days | < 45% |
| Profit Factor | Wins/Losses | < 1.5 |
| Max DD | Peak to trough | > -35% |

### Quarterly Metrics

| Metric | Track | Alert If |
|--------|-------|----------|
| Quarterly Return | % change | < -15% |
| Rebalance Quality | Execution | Poor fills |
| Regime Accuracy | BULL/BEAR calls | Whipsaws |
| Costs | Commissions/slippage | > 1% of capital |

---

## 🚨 Alert Thresholds

### Level 1: Watch Closely 🟡

**Triggered when:**
- Daily loss > -2%
- Weekly loss > -5%
- Drawdown > -20%
- Sharpe < 0.7

**Action:**
- Increase monitoring frequency
- Review strategy logic
- Check for data issues
- Document observations

---

### Level 2: Investigate 🟠

**Triggered when:**
- Daily loss > -5%
- Weekly loss > -10%
- Monthly loss > -15%
- Drawdown > -30%
- Sharpe < 0.5
- Win rate < 45%

**Action:**
- Deep dive analysis
- Compare to backtest
- Check for bugs/errors
- Consider parameter adjustment
- Review recent trades

---

### Level 3: Emergency 🔴

**Triggered when:**
- Daily loss > -10%
- Drawdown > -40%
- 3 consecutive losing months
- Sharpe < 0.3
- Critical system errors

**Action:**
1. **PAUSE STRATEGY IMMEDIATELY**
   ```bash
   pkill -f live_nick_radge.py
   ```

2. **Set dry_run: true**
   ```json
   { "dry_run": true }
   ```

3. **Review Thoroughly**
   - Full system check
   - Data integrity verification
   - Logic validation
   - Risk assessment

4. **Manual Position Review**
   - Consider flattening positions
   - Move to cash if needed
   - Wait for resolution

5. **Root Cause Analysis**
   - Identify failure point
   - Document lessons learned
   - Implement fixes
   - Test extensively

6. **Restart Only When Confident**

---

## 📝 Logging Best Practices

### What to Log

**Automatic (in code):**
- Script start/end times
- Broker connections
- Data downloads
- Regime calculations
- Stock rankings
- Allocations
- Orders
- Fills
- Errors

**Manual (daily notes):**
- Market conditions
- Observations
- Decisions made
- Issues encountered
- Performance notes

---

### Log Analysis

**Daily:**
```bash
# Today's activity
grep "$(date +%Y-%m-%d)" logs/live_nick_radge.log

# Count errors
grep ERROR logs/live_nick_radge.log | grep "$(date +%Y-%m-%d)" | wc -l

# Check regime
grep "Current regime" logs/live_nick_radge.log | tail -1
```

**Weekly:**
```bash
# Last 7 days errors
grep ERROR logs/live_nick_radge.log | tail -100

# Performance summary
grep "Total Return" logs/live_nick_radge.log | tail -7
```

**Monthly:**
```bash
# Archive old logs
mv logs/live_nick_radge.log logs/live_nick_radge_$(date +%Y%m).log

# Analysis
grep "Final Value" logs/live_nick_radge_*.log
```

---

## 📊 Performance Tracking Spreadsheet

### Create Google Sheet / Excel

**Columns:**
- Date
- Portfolio Value
- Daily P&L ($)
- Daily P&L (%)
- SPY Close
- GLD Close
- Current Regime
- Positions Held
- Notes

**Weekly Summary:**
- Week Ending
- Weekly Return
- SPY Return
- GLD Return
- Outperformance
- Drawdown
- Sharpe (30d)

**Monthly Summary:**
- Month
- Monthly Return
- Best Day
- Worst Day
- Win Rate
- # Trades
- Fees Paid

---

## 🔔 Notification Setup

### Email Alerts (Optional)

**Setup email notifications for:**
- Daily execution complete
- Errors encountered
- Drawdown alerts (> -20%, -30%, -40%)
- Rebalance notifications
- Emergency situations

**Python email script:**
```python
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'strategy@yourdomain.com'
    msg['To'] = 'you@email.com'

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login('your_email', 'your_password')
    s.send_message(msg)
    s.quit()
```

---

### SMS Alerts (Optional)

**Use Twilio for critical alerts:**
```python
from twilio.rest import Client

def send_sms(message):
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        body=message,
        from_='+1234567890',
        to='+0987654321'
    )
```

**When to SMS:**
- Emergency alerts (Level 3)
- Rebalance execution complete
- Critical errors
- Drawdown > -30%

---

## ✅ Monthly Checklist

### First of Each Month

- [ ] Review previous month performance
- [ ] Update tracking spreadsheet
- [ ] Calculate key metrics
- [ ] Compare to backtest expectations
- [ ] Review all logs for errors
- [ ] Check system health
- [ ] Update documentation
- [ ] Archive old logs
- [ ] Plan for upcoming quarter (if applicable)

---

## 🎯 Success Metrics

### After 1 Month
- [ ] No critical errors
- [ ] Performance within ±10% of backtest
- [ ] All rebalances executed smoothly
- [ ] Comfortable with monitoring routine

### After 3 Months
- [ ] Consistent execution
- [ ] Performance tracking backtest trend
- [ ] Automated monitoring working
- [ ] Confident in strategy

### After 6 Months
- [ ] Strong track record
- [ ] Performance meeting expectations
- [ ] Issues identified and resolved
- [ ] Ready to scale up capital

---

## 📚 Resources

### Monitoring Tools
- **Logs:** `logs/live_nick_radge.log`
- **Broker:** Platform dashboard
- **Tracking:** Spreadsheet/Google Sheets
- **Reports:** QuantStats HTML reports

### Support Documentation
- [LIVE_DEPLOYMENT_GUIDE.md](LIVE_DEPLOYMENT_GUIDE.md)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- [BROKER_SETUP_GUIDE.md](BROKER_SETUP_GUIDE.md)
- [GLD_WINNER_REPORT.md](GLD_WINNER_REPORT.md)

---

**Remember: Consistent monitoring is key to long-term success. Stay vigilant but don't over-react to short-term fluctuations.** 📊
