# Strategies Folder

## 🎯 Active Production Strategies

This folder contains **ONLY production-ready strategies**. All experimental and abandoned strategies have been cleaned up.

---

## ✅ Production Strategies

### **[02_nick_radge_bss.py](02_nick_radge_bss.py)** ⭐ PRIMARY STOCK STRATEGY
- **Status:** PRODUCTION (+183.37% with TQS, 2020-2025)
- **Description:** Enhanced Nick Radge momentum with flexible qualifiers
- **Class:** `NickRadgeEnhanced`
- **Market:** US stocks
- **Type:** Swing trading (quarterly rebalancing)

**Supported Qualifiers:**
- **TQS (Trend Quality Score)** ⭐ BEST (+183.37%, Sharpe 1.46)
- BSS (Breakout Strength Score)
- ANM (ATR-Normalized Momentum)
- VEM (Volatility Expansion Momentum)
- RAM (Risk-Adjusted Momentum)
- ROC (Rate of Change - original)
- **ml_rf** (RandomForest ML)
- **ml_xgb** (XGBoost ML)
- **hybrid** (TQS + XGBoost)

**Key Features:**
- 3-tier regime filter (Strong Bull/Weak Bull/Bear)
- GLD allocation during bear markets
- Momentum-weighted position sizing
- Volatility targeting (20% annual)
- Max 25% position concentration

**TQS Formula:**
```
TQS = (Price - MA100) / ATR × (ADX / 25)
```

**Performance (TQS variant):**
- Total Return: **+183.37%** (2020-2025)
- Annualized: **23.47%**
- Sharpe Ratio: **1.46**
- Max Drawdown: **-24.33%**
- Win Rate: **51.03%**
- vs SPY: **+64.66%** outperformance

**Deployment:**
- Production script: `deployment/live_nick_radge_tqs_ibkr.py`
- Configuration: `deployment/config_tqs_ibkr.json`
- Documentation: `deployment/DEPLOYMENT_GUIDE_TQS.md`
- Preservation: `deployment/TQS_ORIGINAL_183_PERCENT.md`

**Use Cases:**
- Long-term equity portfolio (primary production strategy)
- Volatility-adjusted momentum ranking
- ML-enhanced stock selection
- Research and backtesting framework

---

### **[05_institutional_crypto_perp.py](05_institutional_crypto_perp.py)** ⭐ PRIMARY CRYPTO STRATEGY
- **Status:** PRODUCTION (+580% tested, 2020-2024)
- **Description:** Institutional-grade crypto perpetuals trend-following with PAXG protection
- **Market:** BTC, ETH, SOL perpetual futures + PAXG (tokenized gold)
- **Type:** Position trading (daily rebalancing)

**Key Features:**
- Donchian breakout + ADX confirmation
- Regime filter (BTC 200MA + volatility)
- **100% PAXG allocation during bear markets** (+244% improvement)
- Volatility-based position sizing (0.5-2× leverage)
- 2× ATR trailing stops
- Pyramid adds (max 3)
- Daily loss limits (-3%)

**Performance (with PAXG):**
- Total Return: **+580%** (vs +336% without PAXG)
- Annualized: **93.8%**
- Sharpe: **1.29**
- Max Drawdown: **-36.7%**
- Profit Factor: **3.76**

**Use Cases:**
- Crypto perpetuals trading (Bybit, Binance)
- 24/7 automated trading
- Bear market protection with PAXG
- High leverage management

---

## 📊 Performance Comparison

| Strategy | Return | Sharpe | Max DD | Market | Status |
|----------|--------|--------|--------|--------|--------|
| **02 Nick Radge (TQS)** | **+183.37%** | **1.46** | **-24.33%** | US Stocks | ✅ PROD |
| **05 Crypto Perp (PAXG)** | **+580%** | **1.29** | **-36.7%** | Crypto | ✅ PROD |
| SPY Benchmark | +118.71% | 0.69 | N/A | US Stocks | - |

---

## 🎯 Which Strategy Should I Use?

| Goal | Strategy | File |
|------|----------|------|
| **US stock swing trading** | Nick Radge (TQS) | [02_nick_radge_bss.py](02_nick_radge_bss.py) |
| **ML-enhanced stocks** | Nick Radge (ml_xgb or hybrid) | [02_nick_radge_bss.py](02_nick_radge_bss.py) |
| **Crypto perpetuals** | Institutional Crypto Perp | [05_institutional_crypto_perp.py](05_institutional_crypto_perp.py) |
| **Research/testing** | Nick Radge (any qualifier) | [02_nick_radge_bss.py](02_nick_radge_bss.py) |

---

## 🚀 Quick Start

### Test Nick Radge TQS Strategy:
```python
from strategies.nick_radge_bss import NickRadgeEnhanced

strategy = NickRadgeEnhanced(
    portfolio_size=7,
    qualifier_type='tqs',  # Best performing
    ma_period=100,
    rebalance_freq='QS',
    use_momentum_weighting=True,
    use_regime_filter=True,
    bear_market_asset='GLD'
)

portfolio = strategy.backtest(prices, spy_prices, initial_capital=100000)
```

### Test Crypto Strategy:
```bash
python examples/test_crypto_perp.py
```

### Deploy to Production:
```bash
# Stock strategy (TQS)
python deployment/live_nick_radge_tqs_ibkr.py --mode paper

# Crypto strategy
python deployment/live_crypto_perp.py --mode paper
```

---

## 📂 Supporting Folders

### [_templates/](_templates/)
- `advanced_strategy_template.py` - Template for building new strategies
- Includes: Signal generation, backtesting, risk management, reporting

### [_simple_examples/](_simple_examples/)
- `sma_crossover.py` - Simple moving average crossover (teaching example)
- `rsi_strategy.py` - RSI overbought/oversold (teaching example)
- `breakout_strategy.py` - Basic breakout strategy (teaching example)

### [_archived/](_archived/)
- `ftmo_challenge_strategy.py` - FTMO prop firm challenge strategy (experimental)
- `atr_trailing_stop_strategy.py` - ATR trailing stop module (standalone)
- `momentum_backtest_standalone.py` - Early momentum tests (superseded)

---

## 🗑️ Removed Strategies (Cleaned Up)

The following strategies have been removed and backed up to `backups/removed_strategies_20250113/`:

- `01_nick_radge_momentum.py` - Superseded by 02 with TQS
- `03_nick_radge_adaptive.py` - Not production-ready
- `04_nick_radge_crypto.py` - Failed (regime filter doesn't work for crypto)
- `06_atr_breakout_longshort.py` - Failed on crypto (-107%)
- `07_atr_breakout_longonly.py` - Works but not optimal (+28%)
- `08_temiz_short_ABANDONED.py` - Failed (-0.57%, 35.7% WR)
- `09_multi_asset_portfolio.py` - Template/framework only

**Rationale:** Keep only production-ready strategies to reduce confusion and maintenance burden.

---

## 🛠️ Adding New Strategies

1. Copy template: `cp _templates/advanced_strategy_template.py 10_my_new_strategy.py`
2. Implement `generate_signals()` and `backtest()` methods
3. Test on historical data (min 1000+ bars)
4. Validate with walk-forward analysis and Monte Carlo
5. Add to this README with status and performance
6. Document in `docs/strategies/`

**Numbering Guide:**
- `02` - Nick Radge stock strategies
- `05` - Crypto strategies
- `10-19` - New crypto strategies
- `20-29` - Intraday/breakout strategies
- `30-39` - Experimental strategies
- `40+` - Your custom strategies

---

## 📖 Documentation

- **Strategy Factory Guide:** [README.md](../README.md)
- **TQS Deployment:** [deployment/DEPLOYMENT_GUIDE_TQS.md](../deployment/DEPLOYMENT_GUIDE_TQS.md)
- **TQS Preservation:** [deployment/TQS_ORIGINAL_183_PERCENT.md](../deployment/TQS_ORIGINAL_183_PERCENT.md)
- **Strategy Versions:** [STRATEGY_VERSIONS.md](../STRATEGY_VERSIONS.md)
- **ML Improvements:** [docs/ML_IMPROVEMENTS_SUMMARY.md](../docs/ML_IMPROVEMENTS_SUMMARY.md)

---

## 🔍 Strategy Selection Guide

### Choose Nick Radge (02) if:
- ✅ Trading US stocks
- ✅ Swing trading (quarterly rebalancing)
- ✅ Want proven 183% performance
- ✅ Need regime-based bear protection
- ✅ Want ML-enhanced options

### Choose Crypto Perp (05) if:
- ✅ Trading crypto perpetuals
- ✅ 24/7 automated trading
- ✅ Want 580% performance
- ✅ Need PAXG bear protection
- ✅ Comfortable with leverage

---

**Last updated:** 2025-01-13
**Active Strategies:** 2 (02, 05)
**Status:** Production Ready
**Backup:** `backups/removed_strategies_20250113/`
