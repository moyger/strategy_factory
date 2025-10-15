# Nick Radge Crypto Hybrid - Minimal Deployment Package

This is a **standalone deployment package** for running the Nick Radge Crypto Hybrid strategy on Bybit (Windows VPS).

**Total size: ~100KB** (vs 50MB+ if you clone the full repo)

---

## What's Included

This package contains ONLY the essential files needed to run the crypto bot:

```
deployment_package/
├── README.md (this file)
├── broker_interface.py          # Base broker interface
├── 06_nick_radge_crypto_hybrid.py  # Strategy logic
├── live_crypto_bybit.py         # Main trading bot
├── config_crypto_bybit.json     # Configuration file
├── bybit_adapter.py             # CCXT adapter (multi-exchange)
├── bybit_adapter_official.py    # Official Bybit SDK adapter (recommended)
├── setup_windows.bat            # Windows setup script
├── run_crypto_bot_windows.bat   # Run bot manually
├── install_windows_service.bat  # Install as Windows service
└── docs/
    ├── BYBIT_DEPLOYMENT_GUIDE.md
    ├── WINDOWS_VPS_SETUP.md
    ├── WINDOWS_QUICK_START.txt
    └── BYBIT_ADAPTER_COMPARISON.md
```

---

## Strategy Overview

**Performance (2020-2025 Backtest):**
- Total Return: **19,410%**
- Annualized: **148%**
- Sharpe Ratio: **1.81**
- Max Drawdown: **-48.35%**

**How It Works:**
- **70/30 Core/Satellite Allocation**
  - Core (70%): BTC, ETH, SOL (fixed)
  - Satellite (30%): Top 3 from 25-crypto universe
- **Quarterly Rebalancing** (Jan/Apr/Jul/Oct)
- **Position Stop-Loss: 40%** (optimal from testing)
- **Regime Filter:** BTC 200MA/100MA
- **Market Type:** SPOT trading only (no leverage, no liquidation risk)

**Minimum Capital:** $2,400 (recommended for 6 positions × $400 avg)

---

## Quick Start (Windows VPS)

### 1. Install Python 3.10+

Download from [python.org](https://www.python.org/downloads/)

During installation, check "Add Python to PATH"

### 2. Install Dependencies

```bash
pip install pandas numpy yfinance ta-lib ccxt pybit
```

### 3. Configure Bybit API

Edit `config_crypto_bybit.json`:

```json
{
    "api_credentials": {
        "api_key": "YOUR_BYBIT_API_KEY",
        "api_secret": "YOUR_BYBIT_API_SECRET"
    },

    "testnet": true,

    "execution": {
        "dry_run": true
    }
}
```

**IMPORTANT:**
- Start with `"testnet": true` and `"dry_run": true`
- Use SPOT wallet API keys (not futures wallet)
- Enable API trading permissions in Bybit account

### 4. Test Run (Dry Run Mode)

```bash
python live_crypto_bybit.py
```

Check logs in `deployment/logs/crypto_bybit_live.log`

### 5. Go Live (After Testing)

Once you've tested for 1-2 weeks:

1. Set `"testnet": false` in config
2. Set `"dry_run": false` in config
3. Run: `python live_crypto_bybit.py`

---

## Running as Windows Service

For 24/7 operation, install as a Windows service:

```bash
# Run as administrator
install_windows_service.bat
```

This uses NSSM (Non-Sucking Service Manager) to run the bot automatically on Windows startup.

**Service Management:**
- Start: `net start CryptoTradingBot`
- Stop: `net stop CryptoTradingBot`
- Status: `sc query CryptoTradingBot`

---

## Configuration Guide

### Key Parameters

**Strategy Parameters:**
```json
"strategy_params": {
    "core_allocation": 0.70,
    "satellite_allocation": 0.30,
    "core_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    "satellite_size": 3,
    "position_stop_loss": 0.40,
    "portfolio_stop_loss": null
}
```

**Trading Parameters:**
```json
"trading_params": {
    "market_type": "spot",
    "max_position_size": 0.25,
    "min_order_size_usdt": 10,
    "slippage_pct": 0.002,
    "fees_pct": 0.001,
    "emergency_stop_loss": 0.50
}
```

**Execution Settings:**
```json
"execution": {
    "rebalance_time": "09:00",
    "rebalance_days": "daily",
    "dry_run": true,
    "log_level": "INFO"
}
```

### Broker Adapter Options

**Option 1: Official Bybit SDK (Recommended)**
```json
"broker_adapter": "official"
```
- Uses `pybit` library (official Bybit SDK)
- Best for dedicated Bybit deployment
- More stable, better documentation

**Option 2: CCXT (Multi-Exchange)**
```json
"broker_adapter": "ccxt"
```
- Uses CCXT library
- Useful if you plan to support multiple exchanges later
- More generic interface

See `docs/BYBIT_ADAPTER_COMPARISON.md` for detailed comparison.

---

## Capital Management

**How Balance Works:**
- Bot uses **real-time balance** from Bybit API via `broker.get_balance()`
- No need to set `initial_capital` in config
- Deposits/withdrawals are instantly reflected
- Bot automatically adjusts position sizes based on current balance

**Minimum Capital Recommendations:**
- **$2,400**: 6 positions × $400 avg (recommended)
- **$1,200**: Minimum viable (6 positions × $200 avg)
- **$4,800+**: Optimal for diversification

---

## Monitoring & Logs

**Log Files:**
- Trading log: `deployment/logs/crypto_bybit_live.log`
- Trade history: `deployment/logs/trades_crypto_bybit.csv`
- Position log: `deployment/logs/positions_crypto_bybit.csv`
- Performance log: `deployment/logs/performance_crypto_bybit.csv`

**Daily Checks:**
- Check for execution errors in trading log
- Verify positions match target allocations
- Check position stop-loss triggers

**Quarterly Checks:**
- Full rebalancing execution review
- Compare actual vs expected returns
- Verify satellite selection is reasonable

---

## Safety Features

**Built-in Safeguards:**
- **Dry Run Mode:** All trades logged, none executed (default)
- **Position Stops:** 40% stop-loss on individual positions
- **Emergency Stop:** 50% portfolio stop-loss (circuit breaker)
- **Concentration Limits:** Max 25% per position
- **Min Order Size:** $10 minimum (avoids dust trades)

**SPOT Trading Advantages:**
- No liquidation risk
- No funding fees (~$260/year saved with $2,400 capital)
- Matches 19,410% backtest (which used spot prices)
- Perfect for small accounts

---

## Troubleshooting

### "Connection refused" (Bybit)
1. Check internet connection
2. Verify API keys are correct
3. Check API key permissions (trading enabled)
4. Verify using SPOT wallet keys (not futures)

### "Failed to download price data"
1. Check internet connection
2. Try testnet first
3. Check if yfinance is accessible

### "Insufficient balance"
1. Check Bybit SPOT wallet balance (not futures)
2. Ensure balance > min_order_size_usdt × 6 positions
3. Check if funds are in correct wallet

### "No target allocations"
- Check BTC regime (may be BEAR market)
- Verify price data downloaded correctly
- Review logs for filtering reasons

---

## Comparison to Full Repo

**This Package (100KB):**
- Only crypto strategy files
- No stock strategies (01-05)
- No examples, tests, or notebooks
- No backtest results
- Clean, minimal deployment

**Full Repo (50MB+):**
- All strategies (stocks + crypto)
- Examples and tests
- Jupyter notebooks
- Historical backtest results
- Documentation and guides

**When to Use Full Repo:**
- If you want to backtest or modify the strategy
- If you want to test other strategies (TQS, BSS, etc.)
- If you want to understand the framework

**When to Use This Package:**
- For production deployment only
- For VPS with limited disk space
- For clean, minimal installations

---

## Support & Documentation

**Full Documentation:** See `docs/` folder for:
- Complete Bybit deployment guide
- Windows VPS setup instructions
- Adapter comparison guide
- Quick start guide

**GitHub Issues:** https://github.com/moyger/strategy_factory/issues

**Main Project Docs:** https://github.com/moyger/strategy_factory

---

## Disclaimer

**Past performance does not guarantee future results.**

This strategy is provided for educational purposes only. Trading involves risk of loss. Always test thoroughly on testnet and paper accounts before deploying real capital.

**USE AT YOUR OWN RISK.**

---

## Version History

- **v1.0** (2025-10-15): Initial minimal deployment package
  - Backtest: 19,410% (2020-2025), Sharpe 1.81
  - SPOT trading only (no leverage)
  - 40% position stops (optimal)
  - 25 crypto universe (expanded from 15)
  - Windows VPS ready

---

**Happy Trading!**
