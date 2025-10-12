# Live Trading Deployment

This folder contains production-ready live trading implementations for Interactive Brokers (IBKR).

## Quick Start

```bash
# 1. Test pre-deployment checks
python -c "
import sys; from pathlib import Path; import importlib.util
spec = importlib.util.spec_from_file_location('nick_radge_tqs', Path('strategies/02_nick_radge_bss.py'))
tqs_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tqs_module)
print('✅ All imports working!')
"

# 2. Install IBKR TWS/Gateway (port 7496 for paper trading)

# 3. Test deployment (dry run, no IBKR connection needed)
cd deployment
python live_nick_radge_tqs_ibkr.py --test
```

## Available Strategies

### 1. Nick Radge TQS (RECOMMENDED) ⭐
**File:** `live_nick_radge_tqs_ibkr.py`
**Config:** `config_tqs_ibkr.json`
**Guide:** [DEPLOYMENT_GUIDE_TQS.md](DEPLOYMENT_GUIDE_TQS.md)

**Performance (2020-2025):**
- Total Return: +183.37%
- Sharpe Ratio: 1.46
- Max Drawdown: -24.33%

**Why TQS?**
- Best risk-adjusted returns (Sharpe 1.46 vs BSS 1.33)
- Lower drawdown (-24.33% vs -26.72%)
- Combines breakout strength + trend quality (ADX)

**Features:**
- Quarterly rebalancing (Jan/Apr/Jul/Oct)
- 3-tier regime filter (STRONG_BULL/WEAK_BULL/BEAR)
- GLD protection during bear markets
- Volatility targeting (20% annual)
- Concentration limits (max 25% per position)

### 2. Nick Radge BSS (Alternative)
**File:** `live_nick_radge_bss_ibkr.py`
**Config:** `config_stock_momentum_gld.json`
**Guide:** [DEPLOYMENT_GUIDE_BSS.md](DEPLOYMENT_GUIDE_BSS.md)

**Performance (2020-2025):**
- Total Return: +167.50%
- Sharpe Ratio: 1.33
- Max Drawdown: -26.72%

**Use BSS if:**
- You prefer simpler breakout logic (no ADX)
- You want to avoid ADX calculation overhead

### 3. Nick Radge Original (Deprecated)
**File:** `live_nick_radge.py`

Uses ROC (Rate of Change) ranking. Deprecated in favor of TQS/BSS qualifiers.

## File Structure

```
deployment/
├── README.md (this file)
├── live_nick_radge_tqs_ibkr.py    # TQS strategy (RECOMMENDED)
├── live_nick_radge_bss_ibkr.py    # BSS strategy (alternative)
├── live_nick_radge.py             # Original ROC (deprecated)
├── config_tqs_ibkr.json           # TQS configuration
├── config_stock_momentum_gld.json # BSS configuration
├── DEPLOYMENT_GUIDE_TQS.md        # Complete TQS deployment guide
└── DEPLOYMENT_GUIDE_BSS.md        # Complete BSS deployment guide
```

## Deployment Workflow

### Phase 1: Paper Trading (4 weeks)
```bash
# Test on IBKR paper account (port 7496)
python live_nick_radge_tqs_ibkr.py --force-rebalance
```

**Checklist:**
- [ ] Connects to IBKR successfully
- [ ] Calculates regime correctly
- [ ] Generates proper allocations
- [ ] Switches to GLD during BEAR regime
- [ ] No errors in logs

### Phase 2: Small Capital (12 weeks)
```bash
# Set dry_run = False (line 105)
python live_nick_radge_tqs_ibkr.py --force-rebalance
```

**Checklist:**
- [ ] All orders filled successfully
- [ ] Slippage < 0.5% per trade
- [ ] Positions match target allocations
- [ ] No execution errors

### Phase 3: Full Deployment
```bash
# Switch to live port (7497)
# Set IBKR_PORT = 7497 (line 67)
python live_nick_radge_tqs_ibkr.py --force-rebalance
```

**Checklist:**
- [ ] 12 weeks of successful paper trading
- [ ] Zero execution errors
- [ ] Comfortable with expected drawdown (-25% to -30%)

## Daily Operations

### Automated Monitoring (Cron)
```bash
# Run daily at 10:30 AM ET
30 10 * * 1-5 cd /path/to/strategy_factory/deployment && python live_nick_radge_tqs_ibkr.py >> output/live_tqs_cron.log 2>&1
```

### Manual Rebalance
```bash
python live_nick_radge_tqs_ibkr.py --force-rebalance
```

## Configuration

### TQS Strategy Parameters
```json
{
  "qualifier_type": "tqs",
  "portfolio_size": 7,
  "ma_period": 100,
  "atr_period": 14,
  "adx_period": 14,
  "max_position_size": 0.25,
  "target_volatility": 0.20,
  "dry_run": true
}
```

### Regime Settings
```json
{
  "regime_ma_long": 200,
  "regime_ma_short": 50,
  "strong_bull_positions": 7,
  "weak_bull_positions": 3,
  "bear_positions": 0,
  "bear_market_asset": "GLD"
}
```

## Safety Features

### Built-in Safeguards
- **Dry Run Mode:** All trades logged, none executed (default)
- **Concentration Limits:** Max 25% per position
- **Volatility Targeting:** Dynamic scaling to 20% annual vol
- **Regime Detection:** Automatic risk reduction in weak/bear markets
- **Min Position Size:** Don't trade < $100 positions

### Kill Switches
1. **Manual:** Set `DRY_RUN = True` in script
2. **Automatic:** Triggered by:
   - Drawdown > 40%
   - 3 consecutive quarterly losses
   - Annual return < -25%
   - Execution errors > 5%

## Expected Performance

### Backtest (2020-2025)
- **Total Return:** +183.37%
- **Annualized:** 23.47%
- **Sharpe Ratio:** 1.46
- **Max Drawdown:** -24.33%
- **Win Rate:** 51.03%
- **Outperformance vs SPY:** +64.66%

### Live Trading (Realistic)
Accounting for slippage and real-world execution:
- **Annualized Return:** 20-25%
- **Sharpe Ratio:** 1.3-1.5
- **Max Drawdown:** -25% to -30%

**Note:** Expect 10-15% underperformance vs backtest due to:
- Slippage (~0.1-0.3% per trade)
- Market impact
- Regime detection lag

## Monitoring

### Daily Checks
- [ ] Check for execution errors in `output/live_tqs_trading.log`
- [ ] Verify GLD allocation during BEAR regime
- [ ] Check regime changes (BULL ↔ BEAR)

### Weekly Checks
- [ ] Review performance vs SPY
- [ ] Verify volatility targeting (~20%)
- [ ] Check position sizes (no single position > 25%)

### Quarterly Checks
- [ ] Full rebalancing execution review
- [ ] Compare actual vs expected returns
- [ ] Verify TQS rankings are reasonable
- [ ] Review kill switch triggers (none should be hit)

## Troubleshooting

### "Connection refused" (IBKR)
1. Ensure TWS/Gateway is running
2. Check port (7496 for paper, 7497 for live)
3. Verify API settings enabled
4. Check firewall

### "Failed to download price data"
1. Check internet connection
2. Verify Yahoo Finance is accessible
3. Try different tickers

### "No target allocations"
- Check SPY regime
- Verify price data downloaded correctly
- Review logs for filtering reasons

## Support

**Issues:** https://github.com/moyger/strategy_factory/issues
**Documentation:** [CLAUDE.md](../CLAUDE.md)

## Disclaimer

**Past performance does not guarantee future results.**

This strategy is provided for educational purposes only. Trading involves risk of loss. Always test thoroughly on paper accounts before deploying real capital.

**USE AT YOUR OWN RISK.**

---

## Version History

- **v1.0** (2025-10-13): Initial TQS deployment release
  - Backtest: +183.37% (2020-2025), Sharpe 1.46
  - VectorBT integration complete
  - All look-ahead biases eliminated
  - Production-ready with safety features

---

**Happy Trading! 🚀**
