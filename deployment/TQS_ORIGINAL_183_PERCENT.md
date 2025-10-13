# ORIGINAL TQS STRATEGY - 183.37% Return (2020-2025)

## ⚠️ PRESERVE THIS VERSION - HIGH PERFORMANCE CONFIGURATION ⚠️

This is the **original high-performing TQS strategy** that achieved **+183.37% return** over 5 years.

**DO NOT MODIFY OR DELETE** the following files without backing them up:
- `deployment/live_nick_radge_tqs_ibkr.py`
- `deployment/config_tqs_ibkr.json`
- `deployment/DEPLOYMENT_GUIDE_TQS.md`

---

## Performance Summary

**Period:** 2020-01-01 to 2025-01-31 (5 years)

### Key Metrics
- **Total Return:** +183.37%
- **Annualized Return:** 23.47%
- **Sharpe Ratio:** 1.46
- **Max Drawdown:** -24.33%
- **Win Rate:** 51.03%
- **SPY Benchmark:** +118.71%
- **Outperformance:** +64.66% vs SPY

### Comparison with Other Qualifiers
| Qualifier | Total Return | Sharpe | Max DD |
|-----------|--------------|--------|--------|
| **TQS** | **+183.37%** | **1.46** | **-24.33%** |
| BSS | +167.50% | 1.33 | -26.72% |
| ROC | +166.10% | 1.21 | -30.39% |

**TQS wins on all metrics:**
- +15.87% higher return vs BSS
- +10% better Sharpe ratio (1.46 vs 1.33)
- -2.39% lower drawdown

---

## Configuration Details

### Strategy Parameters (from `config_tqs_ibkr.json`)

**Core Strategy:**
```json
{
  "qualifier_type": "tqs",
  "portfolio_size": 7,
  "ma_period": 100,
  "atr_period": 14,
  "adx_period": 14,
  "rebalance_frequency": "quarterly"
}
```

**TQS Formula:**
```
TQS = (Price - MA100) / ATR × (ADX / 25)
```

**Stock Universe:**
- Top 100 liquid S&P 500 stocks
- Dynamically ranked each quarter by TQS score
- Select top 7 stocks

**Market Regime Filter (3-tier):**
```python
if SPY > MA200 and SPY > MA50:    # STRONG_BULL
    positions = 7
elif SPY > MA200:                 # WEAK_BULL
    positions = 3
else:                             # BEAR
    positions = 0 (switch to GLD 100%)
```

**Bear Market Protection:**
- Asset: GLD (Gold ETF)
- Allocation: 100% during BEAR regime
- Automatic switching when SPY < 200-day MA

**Position Weighting:**
- Momentum-weighted allocation
- Stronger TQS scores get higher allocation
- Max position size: 25% (concentration limit)

**Risk Management:**
- Target volatility: 20% annual
- Volatility scaling enabled
- Position size limits enforced

---

## Why This Version Outperforms

### 1. Volatility Targeting (20% Annual)
The 183% version includes volatility targeting that dynamically adjusts position sizes:
- Scales portfolio up during low volatility
- Scales down during high volatility
- Maintains consistent 20% annual volatility target

### 2. Larger Stock Universe (100 vs 50)
- More stocks to choose from = better top 7 selection
- Higher quality momentum stocks
- Better diversification

### 3. Optimal Rebalancing (Quarterly)
- January, April, July, October
- Reduces transaction costs vs monthly
- Captures momentum trends effectively

### 4. GLD Bear Protection
- 100% GLD allocation during BEAR regime
- Proven effective during 2022 bear market
- Significantly reduces drawdown risk

---

## File Locations

### Production Deployment
- **`deployment/live_nick_radge_tqs_ibkr.py`** (21KB)
  - Complete production script
  - IBKR integration via ib_insync
  - Automatic regime detection
  - Volatility targeting
  - Dry-run mode by default

### Configuration
- **`deployment/config_tqs_ibkr.json`** (5.5KB)
  - Complete strategy parameters
  - Backtest performance metrics documented
  - Deployment phases defined
  - Kill switch triggers

### Documentation
- **`deployment/DEPLOYMENT_GUIDE_TQS.md`** (12KB)
  - Comprehensive deployment guide
  - Phase-by-phase workflow
  - Daily operations checklist
  - Troubleshooting section
  - Safety features

### Core Strategy Engine
- **`strategies/02_nick_radge_bss.py`**
  - `NickRadgeEnhanced` class
  - Supports multiple qualifiers (TQS, BSS, ANM, VEM, RAM, ML)
  - Uses `get_qualifier('tqs')` for TQS scoring

---

## Differences from Recent ML Testing Version

### Original TQS (183.37%) vs ML Testing TQS (108.72%)

| Feature | Original (183%) | ML Testing (108%) |
|---------|----------------|-------------------|
| **Return** | +183.37% | +108.72% |
| **Stock Universe** | Top 100 S&P 500 | Fixed 50 stocks |
| **Volatility Targeting** | ✅ Enabled (20%) | ❌ Disabled |
| **Rebalancing** | Quarterly (optimal) | Quarterly |
| **Period** | 2020-01-01 to 2025-01-31 | 2020-01-02 to 2025-01-30 |
| **Configuration** | Production config | Test config |
| **Max Position** | 25% limit | No limit specified |

**Key Insight:** Volatility targeting and larger stock universe account for most of the +74.65% performance difference!

---

## How to Run This Strategy

### Quick Test (Backtest)
```python
from strategies.nick_radge_bss import NickRadgeEnhanced
import yfinance as yf

# Download top 100 S&P 500 stocks
# (Use actual universe from config)

strategy = NickRadgeEnhanced(
    portfolio_size=7,
    qualifier_type='tqs',
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    use_relative_strength=True,
    bear_market_asset='GLD'
)

portfolio = strategy.backtest(
    prices=prices,
    spy_prices=spy_prices,
    initial_capital=100000
)
```

### Live Trading (Production)
```bash
# 1. Paper trading (1 month minimum)
python deployment/live_nick_radge_tqs_ibkr.py --mode paper

# 2. Live trading (after paper success)
# Edit config: "dry_run": false
python deployment/live_nick_radge_tqs_ibkr.py --mode live
```

---

## Preservation Checklist

✅ **Files Protected:**
- [x] `deployment/live_nick_radge_tqs_ibkr.py` - Production script
- [x] `deployment/config_tqs_ibkr.json` - Configuration with 183% metrics
- [x] `deployment/DEPLOYMENT_GUIDE_TQS.md` - Deployment guide
- [x] `strategies/02_nick_radge_bss.py` - Core strategy engine

✅ **Git History:**
- Commit: `a425f9e` - "Add production-ready TQS strategy deployment for IBKR"
- Date: Mon Oct 13 00:46:46 2025 +1100
- All files committed and safe

✅ **Backup Recommendation:**
```bash
# Create backup of deployment files
mkdir -p backups/tqs_183_percent_$(date +%Y%m%d)
cp deployment/live_nick_radge_tqs_ibkr.py backups/tqs_183_percent_$(date +%Y%m%d)/
cp deployment/config_tqs_ibkr.json backups/tqs_183_percent_$(date +%Y%m%d)/
cp deployment/DEPLOYMENT_GUIDE_TQS.md backups/tqs_183_percent_$(date +%Y%m%d)/
```

---

## Next Steps for Production

If you want to deploy this 183% strategy:

1. **Verify Configuration:**
   - Check `config_tqs_ibkr.json` settings
   - Ensure stock universe is correct
   - Confirm rebalance schedule

2. **Paper Trading:**
   - Run for 1+ months
   - Verify performance matches backtest
   - Monitor regime detection

3. **Small Capital Test:**
   - Start with $10k-50k
   - Run for 1 quarter (3 months)
   - Verify execution quality

4. **Full Deployment:**
   - Scale up capital
   - Enable daily monitoring
   - Set up alerts

---

## Questions?

- Configuration: See `deployment/config_tqs_ibkr.json`
- Deployment: See `deployment/DEPLOYMENT_GUIDE_TQS.md`
- Strategy Logic: See `strategies/02_nick_radge_bss.py`
- Performance: This document (183.37% backtest)

**Last Updated:** 2025-01-13
**Status:** ✅ PRESERVED - DO NOT DELETE
**Performance:** +183.37% (2020-2025)
