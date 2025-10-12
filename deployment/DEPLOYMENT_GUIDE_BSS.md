# Live Trading Deployment Guide: Nick Radge BSS Strategy

## Overview

This guide shows you how to deploy the **Nick Radge Momentum Strategy with BSS** (Breakout Strength Score) for live trading on Interactive Brokers.

**Why BSS?** Backtesting showed +51% better returns than ROC (+217% vs +166%).

---

## Prerequisites

### 1. Software Requirements

```bash
# Install required libraries
pip install ib_insync yfinance pandas numpy
```

### 2. Interactive Brokers Setup

1. **Open IBKR Account** (if you don't have one)
   - Go to https://www.interactivebrokers.com/
   - Choose **Paper Trading** account first for testing

2. **Download TWS or IB Gateway**
   - TWS (Trader Workstation): Full featured, heavier
   - IB Gateway: Lightweight, API only (recommended)
   - Download: https://www.interactivebrokers.com/en/trading/tws.php

3. **Enable API Access**
   - Open TWS/Gateway
   - Go to: File → Global Configuration → API → Settings
   - Check "Enable ActiveX and Socket Clients"
   - Check "Read-Only API"
   - Set Socket port: **7496** (paper trading) or **7497** (live)
   - Trusted IPs: **127.0.0.1**
   - Click "OK" and restart TWS

4. **Login to TWS/Gateway**
   - Use your paper trading credentials
   - Keep it running while the script runs

---

## Configuration

### File: `deployment/live_nick_radge_bss_ibkr.py`

**Key Configuration Options:**

```python
class LiveTradingConfig:
    # IBKR Connection
    IBKR_PORT = 7496  # 7496 = Paper, 7497 = Live

    # Strategy Parameters
    PORTFOLIO_SIZE = 7
    POI_PERIOD = 100  # BSS: Point of Initiation (MA100)
    ATR_PERIOD = 14   # BSS: ATR lookback
    ATR_MULTIPLIER = 2.0  # BSS: Threshold

    # Regime Filter
    STRONG_BULL_POSITIONS = 7    # SPY > 200MA & 50MA
    WEAK_BULL_POSITIONS = 3      # SPY > 200MA only
    BEAR_MARKET_POSITIONS = 0    # SPY < 200MA → 100% GLD

    # Bear Market Protection
    BEAR_MARKET_ASSET = 'GLD'  # Gold ETF
    BEAR_ALLOCATION = 1.0  # 100%

    # Rebalance Schedule
    REBALANCE_MONTHS = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct
    REBALANCE_DAY = 1
    REBALANCE_HOUR = 10  # 10 AM ET

    # Safety
    DRY_RUN = True  # ALWAYS start with dry run!
```

---

## Deployment Steps

### Phase 1: Paper Trading (2-4 weeks recommended)

#### Step 1: Start TWS/Gateway

```bash
# Make sure TWS/Gateway is running on port 7496 (paper trading)
# Login with paper trading credentials
```

#### Step 2: Test Connection (Dry Run)

```bash
cd deployment
python live_nick_radge_bss_ibkr.py --test
```

**Expected Output:**
```
================================================================================
🚀 NICK RADGE MOMENTUM (BSS) - LIVE TRADING
================================================================================
Time: 2025-10-12 10:00:00
Mode: DRY RUN 🧪
Strategy: BSS (Breakout Strength Score)
Expected: +217% over 5 years (vs +166% for ROC)
✅ Connected to IBKR on port 7496

🧪 FORCED REBALANCE - Testing BSS quarterly rebalance logic
================================================================================
🔄 STARTING QUARTERLY REBALANCE (BSS STRATEGY)
================================================================================
📊 SPY Regime: STRONG_BULL (Price: $580.23, MA50: $570.45, MA200: $520.12)
📊 Regime: STRONG_BULL → Target positions: 7

📊 Calculating BSS for 100 stocks...
✅ Top 7 BSS stocks:
   1. NVDA - BSS: 4.32 (Price: $135.20, POI: $120.50)
   2. MSFT - BSS: 3.87 (Price: $420.15, POI: $390.22)
   3. AAPL - BSS: 3.45 (Price: $185.90, POI: $170.30)
   ...

💰 Account Value: $100,000.00
📊 Allocation per stock: $14,285.71 (7 stocks)

📋 TRADE PLAN:
--------------------------------------------------------------------------------
   🧪 DRY RUN: Would BUY 105 shares of NVDA
   🧪 DRY RUN: Would BUY 34 shares of MSFT
   🧪 DRY RUN: Would BUY 76 shares of AAPL
   ...

✅ Rebalance complete!
```

#### Step 3: Enable Actual Execution (Paper Trading)

Once dry run looks good:

1. Edit `live_nick_radge_bss_ibkr.py`:
   ```python
   DRY_RUN = False  # Enable real (paper) trading
   ```

2. Run again:
   ```bash
   python live_nick_radge_bss_ibkr.py --test
   ```

3. Check TWS/Gateway for actual orders

#### Step 4: Schedule Daily Runs (Paper Trading)

**Option A: Cron (Mac/Linux)**

```bash
# Edit crontab
crontab -e

# Add daily check at 10:30 AM ET
30 10 * * 1-5 cd /path/to/05_strategy_factory/deployment && python live_nick_radge_bss_ibkr.py

# Verify
crontab -l
```

**Option B: Task Scheduler (Windows)**

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 10:30 AM, Monday-Friday
4. Action: Start a program
   - Program: `python`
   - Arguments: `/path/to/deployment/live_nick_radge_bss_ibkr.py`
   - Start in: `/path/to/deployment/`

**Option C: Manual (Simplest for testing)**

Run manually every day at 10:30 AM ET:
```bash
python live_nick_radge_bss_ibkr.py
```

#### Step 5: Monitor Paper Trading (2-4 weeks)

**Daily Checklist:**
- [ ] Check `output/live_bss_trading.log` for errors
- [ ] Verify positions in TWS match expected
- [ ] Compare BSS rankings with previous day
- [ ] Monitor SPY regime (STRONG_BULL/WEAK_BULL/BEAR)
- [ ] Check quarterly rebalances executed correctly

**Expected Behavior:**
- **Daily:** Script checks regime, logs "no action needed" (most days)
- **Regime Change:** Immediate rebalance (BEAR → BULL or vice versa)
- **Quarterly (Jan 1, Apr 1, Jul 1, Oct 1):** Full rebalance
- **Bear Market:** 100% GLD allocation

---

### Phase 2: Live Trading (After successful paper trading)

#### Step 1: Switch to Live Account

**⚠️ CRITICAL: Only do this after 2-4 weeks of successful paper trading!**

1. Edit `live_nick_radge_bss_ibkr.py`:
   ```python
   IBKR_PORT = 7497  # Switch to LIVE trading port
   DRY_RUN = False   # Ensure this is False
   ```

2. Login to TWS/Gateway with **LIVE credentials**

3. Test with small capital first ($1,000-5,000)

#### Step 2: Initial Rebalance (Live)

```bash
# Force initial rebalance to establish positions
python live_nick_radge_bss_ibkr.py --test
```

Verify positions in TWS before confirming.

#### Step 3: Schedule Daily Runs (Live)

Same as paper trading (cron/Task Scheduler/manual).

#### Step 4: Monitor Live Trading

**Daily:**
- Check positions match expected
- Monitor logs for errors
- Verify trades executed at good prices

**Weekly:**
- Review performance vs benchmark (SPY)
- Check drawdown is within tolerance (-25% max)
- Verify BSS scores make sense

**Monthly:**
- Calculate return vs SPY
- Review quarterly rebalance execution
- Adjust capital if needed

**Quarterly:**
- Full strategy review
- Compare with backtest expectations
- Adjust parameters if severely off-track (rare)

---

## What the Script Does

### Daily Checks (Non-Rebalance Days)

```
1. Connect to IBKR
2. Download SPY data
3. Calculate regime (STRONG_BULL/WEAK_BULL/BEAR)
4. Compare with yesterday's regime
5. If regime changed → Rebalance immediately
6. If no change → Log "no action needed"
7. Disconnect
```

### Quarterly Rebalance (Jan 1, Apr 1, Jul 1, Oct 1)

```
1. Connect to IBKR
2. Calculate SPY regime
3. Determine target positions (7/3/0 based on regime)
4. If BEAR → Exit all stocks, buy GLD
5. If BULL → Calculate BSS for 100 stocks
6. Rank by BSS, select top 7 (or 3 in WEAK_BULL)
7. Get current positions from IBKR
8. Calculate delta (target - current)
9. Execute exit trades (positions not in top 7)
10. Execute entry trades (new positions)
11. Execute adjust trades (resize existing)
12. Log final positions
13. Disconnect
```

### Regime Recovery (BEAR → BULL)

```
1. Detect regime change from BEAR to BULL
2. Immediately rebalance (don't wait for quarterly)
3. Exit GLD position
4. Enter top 7 BSS stocks
5. Log "regime recovery"
```

---

## Expected Performance

### Backtest Results (2020-2024)

| Metric | BSS Strategy | SPY Benchmark |
|--------|--------------|---------------|
| **Total Return** | **+217.14%** | +95.30% |
| **Annualized** | ~25.2% | ~14.4% |
| **Max Drawdown** | **-21.52%** | -33.7% |
| **Win Rate** | **71.6%** | N/A |
| **Profit Factor** | **4.14** | N/A |
| **Outperformance** | **+121.85%** | Baseline |

### Live Trading Expectations

**Year 1 (Realistic):**
- Target: +15-20% (conservative estimate)
- Max Drawdown: -25% (expect higher than backtest)
- Trades: ~80-100 per year (quarterly rebalancing)

**Year 2-5 (If successful):**
- Target: +20-25% annually
- Max Drawdown: -20-30%
- Consistency: 3/5 years should beat SPY

**Red Flags (Stop trading if):**
- Drawdown > -35% (more than backtest suggests)
- Underperforming SPY by -20% for 2 years
- Multiple execution errors or failed trades
- Regime filter not working (always in wrong regime)

---

## Troubleshooting

### Issue 1: Connection Failed

```
❌ Failed to connect to IBKR: ConnectionRefusedError
```

**Fix:**
- Ensure TWS/Gateway is running
- Check port number (7496 paper, 7497 live)
- Verify API is enabled in TWS settings
- Check firewall settings

### Issue 2: No Price Data

```
⚠️ Skipping NVDA - no price data
```

**Fix:**
- Yahoo Finance might be down (temporary)
- Check internet connection
- Try again in 5-10 minutes
- If persistent, switch to IBKR data:
  ```python
  USE_IBKR_DATA = True  # Requires market data subscription
  ```

### Issue 3: Order Timeout

```
⚠️ Order timeout: AAPL
```

**Fix:**
- Market might be closed
- Check if stock is tradeable (halted?)
- Increase timeout in code:
  ```python
  timeout = 60  # Increase from 30 to 60 seconds
  ```

### Issue 4: Wrong Number of Positions

```
Total holdings: 5 (target 7)
```

**Fix:**
- Some stocks failed sizing filters
- Check logs for "Skipping {ticker} - position too small"
- Reduce `MIN_POSITION_VALUE` if account is small:
  ```python
  MIN_POSITION_VALUE = 50  # Lower threshold
  ```

### Issue 5: Not Rebalancing on Schedule

```
📊 Daily monitoring - checking regime
✅ Daily check complete - no action needed
```

**But it's Jan 1 (rebalance day):**
- Check `REBALANCE_HOUR` setting (default 10 AM)
- Run before 10 AM → Won't rebalance yet
- Force rebalance: `python live_nick_radge_bss_ibkr.py --test`

---

## Advanced: Parameter Tuning

### DO NOT tune parameters based on short-term results!

Only adjust if:
1. Live trading for 1+ year
2. Significantly underperforming backtest (-20%+)
3. Clear structural change in markets

### Safer Adjustments:

**Reduce risk (if drawdown too high):**
```python
STRONG_BULL_POSITIONS = 5  # Reduce from 7
WEAK_BULL_POSITIONS = 2    # Reduce from 3
```

**Increase BSS threshold (select only strongest breakouts):**
```python
# In calculate_bss_metrics() add filter:
if metrics['BSS'] < 2.5:  # Was no explicit filter
    continue
```

**More conservative regime (easier to go to cash):**
```python
# Modify get_spy_regime():
if latest['Close'] > latest['MA200'] and latest['Close'] > latest['MA50'] * 1.02:  # 2% buffer
    regime = 'STRONG_BULL'
```

---

## Security & Safety

### Financial Safety

1. **Start small:** $1,000-5,000 for first 3 months
2. **Test paper first:** 2-4 weeks minimum
3. **Monitor daily:** First month, check every day
4. **Set stop:** If account drops -35%, stop trading
5. **Diversify:** Don't put all capital in one strategy

### API Security

1. **API keys:** IBKR doesn't use API keys (username/password only)
2. **Read-only API:** Enable in TWS settings
3. **Trusted IPs:** Only allow 127.0.0.1 (localhost)
4. **Firewall:** Only allow localhost connections
5. **No remote access:** Don't expose TWS to internet

### Code Security

1. **No hardcoded passwords:** Always enter manually or use secure storage
2. **Log files:** Store in `output/` folder (add to `.gitignore`)
3. **Backup:** Keep logs for audit trail
4. **Version control:** Git commit before any changes

---

## Monitoring Checklist

### Daily (5 minutes)

- [ ] Check `output/live_bss_trading.log` for errors
- [ ] Verify script ran successfully
- [ ] Check if any regime changes occurred

### Weekly (15 minutes)

- [ ] Review positions in TWS
- [ ] Calculate week's return
- [ ] Compare with SPY return
- [ ] Check for any missed rebalances

### Monthly (30 minutes)

- [ ] Calculate monthly return
- [ ] Update performance spreadsheet
- [ ] Review BSS scores for current holdings
- [ ] Check regime distribution (time in each regime)

### Quarterly (1 hour)

- [ ] Full rebalance day - monitor execution
- [ ] Verify all trades executed correctly
- [ ] Calculate quarterly return vs SPY
- [ ] Review strategy performance vs backtest
- [ ] Adjust capital allocation if needed

---

## Contact & Support

### Interactive Brokers

- **Phone:** 1-877-442-2757
- **Website:** https://www.interactivebrokers.com/
- **API Docs:** https://interactivebrokers.github.io/

### Strategy Support

- **GitHub Issues:** Report bugs at repo issues page
- **Documentation:** See `CLAUDE.md` for strategy details
- **Backtests:** See `results/nick_radge_qualifiers/` for performance

---

## Disclaimer

**This is NOT financial advice.**

- Past performance does not guarantee future results
- Backtest results may not reflect live trading
- You can lose money trading stocks
- Only trade with capital you can afford to lose
- Consult a financial advisor before trading
- Test thoroughly on paper account first
- Monitor daily and be prepared to stop if needed

**Use at your own risk!**
