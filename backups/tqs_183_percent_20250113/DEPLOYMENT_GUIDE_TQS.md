# Nick Radge TQS Strategy - IBKR Deployment Guide

**Strategy:** Nick Radge Momentum with TQS (Trend Quality Score)
**Expected Performance:** +183% over 5 years (Sharpe 1.46)
**Status:** Ready for paper trading

---

## Why TQS?

**TQS (Trend Quality Score)** is the best-performing qualifier for the Nick Radge momentum strategy:

```
TQS = (Price - MA100) / ATR × (ADX / 25)
```

**Performance Comparison (2020-2025):**

| Metric | TQS | BSS | Winner |
|--------|-----|-----|--------|
| Total Return | +183.37% | +167.50% | **TQS (+15.87%)** |
| Sharpe Ratio | 1.46 | 1.33 | **TQS (+10%)** |
| Max Drawdown | -24.33% | -26.72% | **TQS (-2.39%)** |
| Win Rate | 51.03% | 51.14% | Tie |

**Why TQS Wins:**
- Combines breakout strength + trend quality (ADX filter)
- Filters out choppy/sideways markets (low ADX)
- Better risk-adjusted returns (higher Sharpe)
- Lower drawdown = smoother equity curve

---

## Prerequisites

### 1. Software Requirements

```bash
# Install Python dependencies
pip install ib_insync yfinance pandas numpy vectorbt

# Verify installation
python -c "import ib_insync; print('ib_insync OK')"
python -c "import vectorbt; print('vectorbt OK')"
```

### 2. IBKR Account Setup

1. **Open IBKR Account:**
   - Go to [interactivebrokers.com](https://www.interactivebrokers.com)
   - Open a paper trading account (free)
   - Enable API access in account settings

2. **Download TWS or IB Gateway:**
   - TWS (Trader Workstation): Full GUI
   - IB Gateway: Lightweight, headless
   - Download: [IBKR Software](https://www.interactivebrokers.com/en/index.php?f=16040)

3. **Configure API Settings:**
   - Open TWS/Gateway
   - Go to: **File → Global Configuration → API → Settings**
   - Enable "Enable ActiveX and Socket Clients"
   - Enable "Read-Only API"
   - Socket Port: **7496** (paper) or **7497** (live)
   - Trusted IPs: **127.0.0.1**
   - Click "OK" and restart TWS/Gateway

### 3. Test Connection

```bash
# Start TWS/Gateway first (port 7496 for paper trading)

# Test connection
python -c "
from ib_insync import IB
ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)
print('✅ IBKR Connected!')
print(f'Account Value: \$\{ib.accountValues()[0].value}')
ib.disconnect()
"
```

If this works, you're ready to proceed!

---

## Deployment Phases

### Phase 1: Paper Trading (4 weeks)

**Goal:** Verify execution logic without risking real capital

**Configuration:**
```json
{
  "dry_run": true,
  "ibkr_port": 7496  // Paper trading port
}
```

**Steps:**

1. **Start TWS/Gateway on port 7496 (paper trading)**

2. **Test forced rebalance:**
   ```bash
   cd deployment
   python live_nick_radge_tqs_ibkr.py --force-rebalance
   ```

3. **Expected Output:**
   ```
   🚀 NICK RADGE MOMENTUM (TQS) - LIVE TRADING
   Time: 2025-10-13 10:00:00
   Mode: DRY RUN 🧪
   Strategy: TQS (Trend Quality Score)
   Expected: +183% over 5 years (Sharpe 1.46)

   ✅ Connected to IBKR on port 7496
   📊 SPY Regime: STRONG_BULL (Price: $550.23, MA50: $545.12, MA200: $520.45)
   📊 Regime: STRONG_BULL → Target positions: 7

   📊 Calculating target allocations using TQS strategy...
   ✅ Target allocations (7 positions):
      NVDA: 17.5%
      MSFT: 16.2%
      AAPL: 15.8%
      ...

   📋 TRADE PLAN:
   ────────────────────────────────────────────────
      BUY: NVDA (50 shares)
      BUY: MSFT (40 shares)
      ...

   🧪 DRY RUN: Would BUY 50 shares of NVDA
   🧪 DRY RUN: Would BUY 40 shares of MSFT
   ...

   ✅ Rebalance complete!
   ```

4. **Review Logs:**
   ```bash
   tail -f output/live_tqs_trading.log
   ```

5. **Validate:**
   - ✅ Connects to IBKR successfully
   - ✅ Calculates regime correctly (STRONG_BULL/WEAK_BULL/BEAR)
   - ✅ Generates 7 positions in STRONG_BULL regime
   - ✅ Switches to GLD during BEAR regime
   - ✅ No errors in log file

**Paper Trading Checklist (4 weeks):**

- [ ] Week 1: Test forced rebalance, verify allocations
- [ ] Week 2: Test regime changes (manually edit SPY data if needed)
- [ ] Week 3: Test GLD switching (simulate BEAR market)
- [ ] Week 4: Run daily monitoring, ensure no errors

---

### Phase 2: Small Capital Testing (12 weeks)

**Goal:** Validate real-world execution with minimal risk

**Configuration:**
```json
{
  "dry_run": false,
  "ibkr_port": 7496,  // Still paper trading!
  "capital": "$5,000-$10,000"
}
```

**Steps:**

1. **Set dry_run = false in script:**
   ```python
   # In live_nick_radge_tqs_ibkr.py, line 105
   DRY_RUN = False  # Enable real orders (on paper account)
   ```

2. **Run quarterly rebalance:**
   ```bash
   python live_nick_radge_tqs_ibkr.py --force-rebalance
   ```

3. **Monitor execution:**
   - Check IBKR TWS for filled orders
   - Verify positions match target allocations
   - Check slippage (should be < 0.1%)

4. **Set up cron job (daily monitoring):**
   ```bash
   # Add to crontab (run daily at 10:30 AM)
   30 10 * * * cd /path/to/strategy_factory/deployment && python live_nick_radge_tqs_ibkr.py >> output/live_tqs_cron.log 2>&1
   ```

**12-Week Validation:**

| Week | Action | Expected Result |
|------|--------|----------------|
| 1-4 | Let initial allocation run | Verify positions match target |
| 5-8 | Monitor daily regime checks | No false regime switches |
| 9-12 | Wait for quarterly rebalance | Smooth rebalancing execution |

**Success Criteria:**
- ✅ All orders filled successfully (0% failed orders)
- ✅ Slippage < 0.5% per trade
- ✅ No execution errors in logs
- ✅ Positions match target allocations within 5%
- ✅ GLD switching works correctly (if BEAR regime occurs)

---

### Phase 3: Full Deployment (Live Trading)

**Goal:** Scale to full capital on live IBKR account

**Configuration:**
```json
{
  "dry_run": false,
  "ibkr_port": 7497,  // LIVE TRADING PORT!
  "capital": "Full account balance"
}
```

**⚠️  CRITICAL: Only proceed if Phase 2 was 100% successful**

**Steps:**

1. **Switch to live TWS/Gateway (port 7497):**
   ```python
   # In live_nick_radge_tqs_ibkr.py, line 67
   IBKR_PORT = 7497  # LIVE TRADING
   ```

2. **Final safety checks:**
   - [ ] Reviewed all 12 weeks of paper trading logs
   - [ ] Zero execution errors
   - [ ] GLD switching tested successfully
   - [ ] Regime detection working correctly
   - [ ] Comfortable with expected drawdown (-25% to -30%)

3. **Deploy to live account:**
   ```bash
   # DOUBLE CHECK: dry_run = False, port = 7497
   python live_nick_radge_tqs_ibkr.py --force-rebalance
   ```

4. **Monitor closely for first month:**
   - Daily: Check execution errors
   - Weekly: Compare actual vs expected performance
   - Monthly: Verify volatility targeting is working

---

## Daily Operations

### Automated Monitoring (Cron Job)

```bash
# Run daily at 10:30 AM ET (after market open)
30 10 * * 1-5 cd /path/to/strategy_factory/deployment && python live_nick_radge_tqs_ibkr.py >> output/live_tqs_cron.log 2>&1
```

**What it does:**
- Checks SPY regime daily
- Detects regime changes (BULL ↔ BEAR)
- Executes immediate rebalance if regime changes
- Logs all activity to `output/live_tqs_trading.log`

### Manual Rebalancing

```bash
# Force quarterly rebalance (Jan 1, Apr 1, Jul 1, Oct 1)
python live_nick_radge_tqs_ibkr.py --force-rebalance
```

---

## Risk Management

### Position Limits

- **Max Position Size:** 25% (concentration limit)
- **Portfolio Size:** 7 stocks (STRONG_BULL), 3 stocks (WEAK_BULL), 0 stocks (BEAR)
- **Volatility Target:** 20% annual (dynamic scaling)

### Kill Switches

**Automatic Stop Conditions:**
- Drawdown exceeds 40%
- 3 consecutive quarterly losses
- Annual return < -25%
- Execution errors > 5% of trades

**Manual Kill Switch:**
```python
# In live_nick_radge_tqs_ibkr.py, line 105
DRY_RUN = True  # Stop all trading immediately
```

---

## Expected Performance

### Backtest Results (2020-2025)

- **Total Return:** +183.37%
- **Annualized:** 23.47%
- **Sharpe Ratio:** 1.46
- **Max Drawdown:** -24.33%
- **Win Rate:** 51.03%
- **Outperformance vs SPY:** +64.66%

### Live Trading Expectations

Accounting for slippage and real-world execution:

- **Annualized Return:** 20-25%
- **Sharpe Ratio:** 1.3-1.5
- **Max Drawdown:** -25% to -30%

**Note:** Expect underperformance vs backtest by ~10-15% due to:
- Slippage (~0.1-0.3% per trade)
- Market impact (especially for large positions)
- Regime detection lag (1 day)

---

## Monitoring Checklist

### Daily
- [ ] Check for execution errors in `output/live_tqs_trading.log`
- [ ] Verify GLD allocation during BEAR regime
- [ ] Check regime changes (BULL ↔ BEAR)

### Weekly
- [ ] Review performance vs SPY
- [ ] Verify volatility targeting is working (portfolio vol ~20%)
- [ ] Check position sizes (no single position > 25%)

### Monthly
- [ ] Check if within expected volatility bounds (15-25%)
- [ ] Review slippage (should be < 0.5% per trade)
- [ ] Compare actual vs expected returns

### Quarterly
- [ ] Full rebalancing execution review
- [ ] Compare actual vs expected returns
- [ ] Verify TQS rankings are reasonable
- [ ] Review kill switch triggers (none should be hit)

---

## Troubleshooting

### Error: "Connection refused" (IBKR)

**Solution:**
1. Ensure TWS/Gateway is running
2. Check port (7496 for paper, 7497 for live)
3. Verify API settings enabled
4. Check firewall (allow port 7496/7497)

### Error: "Failed to download price data"

**Solution:**
1. Check internet connection
2. Verify Yahoo Finance is accessible
3. Try different tickers (some may be delisted)

### Error: "No target allocations"

**Causes:**
- All stocks failed MA100 filter
- All stocks have TQS < SPY TQS
- BEAR regime (should switch to GLD)

**Solution:**
- Check SPY regime
- Verify price data downloaded correctly
- Review logs for specific filtering reasons

### Warning: "Slippage > 1%"

**Solution:**
- Use limit orders instead of market orders
- Trade during market hours (avoid opens/closes)
- Reduce position sizes (especially for illiquid stocks)

---

## Advanced Features

### Volatility Targeting

The strategy dynamically scales portfolio exposure to target 20% annual volatility:

```python
# 20-day realized vol estimate
realized_vol = portfolio_returns.rolling(20).std() * sqrt(252)

# Vol scalar (clipped to [0.0, 2.0])
vol_scalar = (0.20 / realized_vol).clip(0.0, 2.0)

# Apply to allocations
allocations = base_allocations * vol_scalar
```

**Benefits:**
- Reduces exposure during high volatility (2020 crash)
- Increases exposure during low volatility (2021 bull run)
- Smoother equity curve

### Concentration Limits

Prevents over-concentration in single positions:

```python
max_position_size = 0.25  # 25% max per position

allocations = allocations.clip(upper=max_position_size)
```

**Why 25%?**
- 7 positions → ideal is 14.3% each
- 25% max allows momentum weighting while preventing blow-ups
- Tested in backtest (optimal for TQS)

---

## FAQ

### Q: Why quarterly rebalancing instead of monthly?

**A:** Lower transaction costs, less overfitting. Backtests showed quarterly was optimal.

### Q: Why GLD during BEAR markets?

**A:** Testing showed GLD 100% outperformed all alternatives:
- GLD 100%: +228.56% (WINNER)
- Cash: +177.61%
- TLT: +109%
- SH: +35-75%
- SQQQ: -79% (catastrophic)

### Q: What if SPY regime flips daily (whipsaw)?

**A:** The script detects regime changes daily and rebalances immediately. However, whipsaws are rare (regime uses 200-day and 50-day MAs).

### Q: Can I use this on other brokers (Alpaca, Schwab)?

**A:** Yes, but you'll need to adapt the broker interface. The strategy logic is broker-agnostic.

### Q: What if I have < $10,000?

**A:** Use fewer positions (3-5 instead of 7) or fractional shares (if broker supports).

---

## Support

**Issues:** https://github.com/moyger/strategy_factory/issues
**Documentation:** [CLAUDE.md](../CLAUDE.md)
**Email:** [Your email here]

---

## Disclaimer

**Past performance does not guarantee future results.**

This strategy is provided for educational purposes only. Trading involves risk of loss. Always test thoroughly on paper accounts before deploying real capital.

The authors are not responsible for any losses incurred from using this strategy.

**USE AT YOUR OWN RISK.**

---

## Version History

- **v1.0** (2025-10-13): Initial release with TQS qualifier
- Backtest: +183.37% (2020-2025), Sharpe 1.46
- VectorBT integration complete
- All look-ahead biases eliminated

---

**Happy Trading! 🚀**
