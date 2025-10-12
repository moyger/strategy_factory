# Strategies Folder

All trading strategies organized by numbering system and status.

## 📁 Organization System

**Numbering Convention:**
- Simple sequential numbering: `01`, `02`, `03`, `04`, `05`, etc.
- No gaps - just add the next number when creating a new strategy
- Suffix `_ABANDONED` for failed strategies (e.g., `08_temiz_short_ABANDONED.py`)

---

## ✅ Production Strategies (Ready for Live Trading)

### Nick Radge Strategies (01-04)

**[01_nick_radge_momentum.py](01_nick_radge_momentum.py)** ⭐ PRIMARY
- **Status:** PRODUCTION (+221% tested, 2015-2024)
- **Description:** Original Nick Radge momentum strategy with ROC ranking
- **Market:** US stocks (50-stock universe)
- **Type:** Swing trading (quarterly rebalancing)
- **Features:**
  - 100-day ROC momentum ranking
  - 3-tier regime filter (Strong Bull/Weak Bull/Bear)
  - GLD allocation during bear markets
  - Momentum-weighted position sizing
- **Use case:** Long-term equity portfolio (primary production strategy)

**[02_nick_radge_bss.py](02_nick_radge_bss.py)** ⚡ ENHANCED
- **Status:** Tested (multiple qualifiers validated)
- **Description:** Enhanced Nick Radge with ATR-based qualifiers (BSS, ANM, VEM, etc.)
- **Market:** US stocks
- **Type:** Swing trading
- **Features:**
  - 7 ranking methods: ROC, BSS, ANM, VEM, TQS, RAM, Composite
  - BSS (Breakout Strength Score) = (Price - POI) / (k × ATR)
  - All original Nick Radge features
- **Use case:** When you want volatility-adjusted momentum ranking

**[03_nick_radge_adaptive.py](03_nick_radge_adaptive.py)**
- **Status:** Tested (adaptive position sizing)
- **Description:** Nick Radge with dynamic portfolio size based on market conditions
- **Features:**
  - Adaptive position count (5-10 positions)
  - Momentum-weighted allocation
  - Regime-aware adjustments
- **Use case:** Adaptive portfolio management

**[04_nick_radge_crypto.py](04_nick_radge_crypto.py)**
- **Status:** Failed (regime filter doesn't work for crypto)
- **Description:** Nick Radge adapted for cryptocurrencies
- **Issue:** SPY-based regime filter inappropriate for crypto markets
- **Use case:** ❌ Don't use - see #10 instead

---

### Crypto Strategies (05)

**[05_institutional_crypto_perp.py](05_institutional_crypto_perp.py)** ⭐ CRYPTO PRIMARY
- **Status:** PRODUCTION (+580% tested, 2020-2024)
- **Description:** Institutional-grade crypto perpetuals trend-following with PAXG bear market protection
- **Market:** BTC, ETH, SOL perpetual futures + PAXG (tokenized gold)
- **Type:** Position trading (daily rebalancing)
- **Features:**
  - Donchian breakout + ADX confirmation
  - Regime filter (BTC 200MA + volatility)
  - **100% PAXG allocation during bear markets** (+244% improvement)
  - Volatility-based position sizing (0.5-2× leverage)
  - 2× ATR trailing stops
  - Pyramid adds (max 3)
  - Daily loss limits (-3%)
- **Performance (with PAXG):**
  - Return: **+580%** (vs +336% without PAXG)
  - Annualized: **93.8%**
  - Sharpe: **1.29**
  - Max DD: -36.7%
- **Use case:** Crypto perpetuals trading with bear market protection (Bybit, Binance)

---

### ATR Breakout Strategies (06-07)

**[06_atr_breakout_longshort.py](06_atr_breakout_longshort.py)** ⚠️ CONDITIONAL
- **Status:** FAILED on crypto (-107%), works on futures
- **Description:** Tomas Nesnidal ATR breakout (BOTH long AND short)
- **Market:** Intraday futures (YM emini Dow, 20-min bars)
- **Type:** Day trading
- **Features:**
  - POI (Point of Initiation) + k × ATR entries
  - ADX >= threshold (trending markets)
  - Both long and short positions
- **Issue:** Shorts catastrophic in bull crypto markets
- **Use case:** ✅ Intraday futures ONLY, ❌ NOT for crypto

**[07_atr_breakout_longonly.py](07_atr_breakout_longonly.py)** ⚠️ CONDITIONAL
- **Status:** Works (+28-30% on crypto), but not optimal
- **Description:** ATR breakout LONG ONLY (fixed version)
- **Market:** Intraday (5-min crypto bars)
- **Type:** Day trading
- **Features:**
  - INVERTED ADX logic: ADX < threshold (consolidation breakouts)
  - Previous day's close as POI
  - Time window filters + EOD exits
- **Result:** +28-30% on crypto (avoided short disaster)
- **Use case:** ✅ Intraday breakouts (long bias markets), but #10 is better for crypto

---

## ⚠️ Experimental/Abandoned (08)

**[08_temiz_short_ABANDONED.py](08_temiz_short_ABANDONED.py)** ❌ ABANDONED
- **Status:** FAILED (-0.57%, 35.7% WR on 55 days of 2024 testing)
- **Description:** Temiz small-cap short strategy (parabolic exhaustion)
- **Market:** Small-cap stocks (GME, AMC, DJT, RGTI, etc.)
- **Type:** Day trading (1-minute bars, short-only)
- **Why failed:**
  - 2021 test: -1.08% return, 33.3% win rate
  - 2024 test: -0.57% return, 35.7% win rate
  - Confluence filters: Blocked ALL trades (too strict)
- **Lesson learned:** Daily data backtests are MISLEADING for intraday strategies (+17% false positive)
- **Use case:** ❌ Don't use

---

## 🧩 Multi-Asset Strategies (09)

**[09_multi_asset_portfolio.py](09_multi_asset_portfolio.py)**
- **Status:** Template/Framework
- **Description:** Multi-asset portfolio with dynamic allocation
- **Markets:** Stocks, bonds, commodities, crypto
- **Type:** Strategic allocation
- **Use case:** Portfolio-level strategy framework

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
- `momentum_backtest_standalone.py` - Early momentum tests (superseded by #01)

---

## 🎯 Which Strategy Should I Use?

| Goal | Strategy | File |
|------|----------|------|
| **US stock swing trading** | Nick Radge Momentum | [01_nick_radge_momentum.py](01_nick_radge_momentum.py) |
| **Volatility-adjusted ranking** | Nick Radge Enhanced (BSS) | [02_nick_radge_enhanced_bss.py](02_nick_radge_enhanced_bss.py) |
| **Crypto perpetuals** | Institutional Crypto Perp | [05_institutional_crypto_perp.py](05_institutional_crypto_perp.py) |
| **Intraday futures** | ATR Breakout (Long/Short) | [06_atr_breakout_longshort.py](06_atr_breakout_longshort.py) |
| **Learn basics** | Simple examples | [_simple_examples/](_simple_examples/) |
| **Build new strategy** | Template | [_templates/advanced_strategy_template.py](_templates/advanced_strategy_template.py) |

---

## 📊 Performance Summary

| Strategy | Status | Return | Sharpe | Max DD | Win Rate | Markets |
|----------|--------|--------|--------|--------|----------|---------|
| 01 Nick Radge Momentum | ✅ PROD | +221% | 1.19 | -32% | 63% | US Stocks |
| 02 Nick Radge Enhanced (BSS) | ✅ Tested | Varies | ~1.0+ | <-30% | ~60% | US Stocks |
| 10 Institutional Crypto Perp | ✅ PROD | +580% | 1.40 | -27% | 58% | Crypto |
| 20 ATR Breakout (L/S) | ⚠️ Futures only | N/A | N/A | N/A | N/A | Futures |
| 21 ATR Breakout (Long) | ⚠️ Works | +28% | 0.70 | -15% | ~50% | Intraday |
| 30 Temiz Short | ❌ FAIL | -0.57% | N/A | N/A | 36% | Stocks |

---

## 🚀 Quick Start

**Test Nick Radge strategy:**
```bash
python examples/test_nick_radge.py
```

**Test crypto perp strategy:**
```bash
python examples/test_crypto_perp.py
```

**Run full workflow (all strategies):**
```bash
python quick_start.py
```

---

## 📖 Documentation

- Strategy details: [docs/strategies/](../docs/strategies/)
- Nick Radge guide: [docs/nick_radge/](../docs/nick_radge/)
- Crypto guide: [docs/crypto/](../docs/crypto/)
- Deployment: [docs/deployment/](../docs/deployment/)

---

## 🛠️ Adding New Strategies

1. Copy template: `cp _templates/advanced_strategy_template.py 50_my_new_strategy.py`
2. Implement `generate_signals()` and `backtest()` methods
3. Test on historical data (min 1000+ bars)
4. Add to this README with numbering convention
5. Document in `docs/strategies/`

**Numbering Guide:**
- Nick Radge variants: `01-09`
- Crypto strategies: `10-19`
- Intraday/breakout: `20-29`
- Experimental: `30-39`
- Multi-asset: `40-49`
- Your custom: `50+`

---

**Last updated:** October 2025
