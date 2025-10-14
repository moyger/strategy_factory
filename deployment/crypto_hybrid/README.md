# Nick Radge Crypto Hybrid - Bybit Deployment

**Complete deployment package for the Nick Radge Crypto Hybrid strategy on Bybit**

---

## Strategy Overview

- **Type:** 70/30 Core/Satellite Hybrid
- **Core (70%):** BTC/ETH/SOL (fixed allocation)
- **Satellite (30%):** Top 3 altcoins (dynamic, quarterly rebalance)
- **Position Stops:** 40% (optimal from backtesting)
- **Regime Filter:** BTC 200MA/100MA (exits to cash in bear markets)

### Backtest Performance (2020-2025)

- **Total Return:** 19,410%
- **Annualized:** 148%
- **Sharpe Ratio:** 1.81
- **Max Drawdown:** -48.35%
- **Position Stops Triggered:** 8 (prevented -70% to -88% crashes)

### Validation

✅ **Walk-Forward:** 75% consistency (3/4 windows profitable)
✅ **Monte Carlo:** 100% profit probability (1,000 simulations)
✅ **Position Stops:** Caught 8 real failures (SOL -88%, AVAX -79%, etc.)

---

## Quick Start (3 Steps)

### 1. Install Dependencies

```bash
setup_windows.bat
```

Choose:
- **Option 1:** Official Bybit SDK (pybit) - Recommended ⭐
- **Option 2:** CCXT (multi-exchange)

### 2. Configure API Keys

Edit `config_crypto_bybit.json`:

```json
{
    "broker_adapter": "official",
    "testnet": true,
    "dry_run": true,
    "api_credentials": {
        "api_key": "YOUR_BYBIT_API_KEY",
        "api_secret": "YOUR_BYBIT_SECRET"
    }
}
```

Get testnet API keys: https://testnet.bybit.com/

### 3. Run Bot

```bash
run_crypto_bot_windows.bat
```

---

## Files in This Folder

### Core Files
- `live_crypto_bybit.py` - Main trading bot (24KB)
- `config_crypto_bybit.json` - Configuration file
- `bybit_adapter.py` - CCXT adapter
- `bybit_adapter_official.py` - Official pybit adapter

### Windows Scripts
- `setup_windows.bat` - Dependency installer
- `run_crypto_bot_windows.bat` - Bot launcher
- `install_windows_service.bat` - Windows service installer

### Documentation
- [BYBIT_DEPLOYMENT_GUIDE.md](BYBIT_DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [WINDOWS_VPS_SETUP.md](WINDOWS_VPS_SETUP.md) - Detailed Windows VPS setup
- [WINDOWS_QUICK_START.txt](WINDOWS_QUICK_START.txt) - Quick reference (copy/paste commands)
- [BYBIT_ADAPTER_COMPARISON.md](BYBIT_ADAPTER_COMPARISON.md) - pybit vs CCXT comparison

---

## Connection Methods

### Official Bybit SDK (pybit) ⭐ Recommended

**Pros:**
- 30-50% faster than CCXT
- Official from Bybit (always up-to-date)
- Lighter weight (~2MB)
- Best API coverage

**Installation:**
```bash
pip install pybit
```

**Config:**
```json
{"broker_adapter": "official"}
```

### CCXT (Multi-Exchange)

**Pros:**
- Works with 100+ exchanges
- Easy to switch brokers
- Large community support

**Installation:**
```bash
pip install ccxt
```

**Config:**
```json
{"broker_adapter": "ccxt"}
```

See [BYBIT_ADAPTER_COMPARISON.md](BYBIT_ADAPTER_COMPARISON.md) for detailed comparison.

---

## Deployment Workflow

### Phase 1: Testnet Testing (1-2 weeks)

```json
{
    "testnet": true,
    "dry_run": true
}
```

✅ Run bot daily
✅ Check logs for errors
✅ Verify rebalancing works
✅ Test position stops (if triggered)

### Phase 2: Live Data Testing (2-3 days)

```json
{
    "testnet": false,
    "dry_run": true
}
```

✅ Verify live data downloads
✅ Check order generation
✅ Review logs

### Phase 3: Production (Real Money)

```json
{
    "testnet": false,
    "dry_run": false
}
```

⚠️ **Start with 10-20% of target capital**
⚠️ **Monitor DAILY for first week**

---

## Running as Windows Service (24/7)

For production deployment:

1. Download NSSM: https://nssm.cc/download
2. Extract `nssm.exe` to this folder
3. Run as Administrator:
   ```cmd
   install_windows_service.bat
   ```
4. Start service:
   ```cmd
   sc start CryptoTradingBot
   ```

Manage via GUI:
- `Win+R` → `services.msc`
- Find "Crypto Trading Bot"
- Right-click → Start/Stop/Restart

---

## Monitoring

### View Logs

**Real-time:**
```cmd
powershell Get-Content logs\crypto_bybit_live.log -Wait -Tail 20
```

**Or use Notepad:**
```cmd
notepad logs\crypto_bybit_live.log
```

### View Trades

```cmd
notepad logs\trades_crypto_bybit.csv
```

### View Performance

```cmd
cd logs
python -c "import pandas as pd; print(pd.read_csv('performance_crypto_bybit.csv').tail())"
```

---

## Emergency Stop

### If running in Command Prompt:
Press `Ctrl+C`

### If running as service:
```cmd
sc stop CryptoTradingBot
```

Or via GUI:
- `Win+R` → `services.msc`
- Stop "Crypto Trading Bot"

### Disable trading without stopping:
Edit `config_crypto_bybit.json`:
```json
{"dry_run": true}
```
Restart bot.

---

## Strategy Files

### Core Strategy
- `../../strategies/06_nick_radge_crypto_hybrid.py`

### Test Files
- `../../examples/test_crypto_hybrid_strategy.py`
- `../../examples/full_crypto_hybrid_backtest.py`
- `../../examples/full_validation_suite.py`

### Results
- `../../results/crypto_hybrid/validation/`
- `../../results/crypto_hybrid/reports/`

---

## Configuration Options

### Key Settings

```json
{
    "broker": "bybit",
    "broker_adapter": "official",      // "official" or "ccxt"
    "testnet": true,                   // true = testnet, false = live

    "api_credentials": {
        "api_key": "YOUR_KEY",
        "api_secret": "YOUR_SECRET"
    },

    "strategy_params": {
        "core_allocation": 0.70,       // 70% to BTC/ETH/SOL
        "satellite_allocation": 0.30,   // 30% to top 3 altcoins
        "core_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        "satellite_size": 3,
        "qualifier_type": "tqs_ml_hybrid",
        "position_stop_loss": 0.40,    // 40% position stop (optimal)
        "portfolio_stop_loss": null     // Disabled (costs -11,000% returns)
    },

    "trading_params": {
        "initial_capital": 10000,      // USDT
        "emergency_stop_loss": 0.50,   // 50% circuit breaker
        "min_order_size_usdt": 10
    },

    "execution": {
        "dry_run": true,               // ALWAYS start with true!
        "rebalance_days": "daily",
        "rebalance_time": "09:35",
        "log_level": "INFO"
    }
}
```

---

## Troubleshooting

### Error: "Python not found"
```cmd
python --version
```
If error → Reinstall Python, check "Add to PATH"

### Error: "pybit not installed"
```cmd
pip install pybit
```
Or switch to CCXT in config:
```json
{"broker_adapter": "ccxt"}
```

### Error: "Connection failed"
- Check Windows Firewall
- Allow `python.exe` through firewall
- Test: `ping api.bybit.com`

### Bot crashes
- Check `logs/crypto_bybit_live.log`
- Look for error messages
- Verify API keys are correct

---

## VPS Providers

**Recommended for low latency to Bybit:**

| Provider | RAM | CPU | Price/mo | Singapore |
|----------|-----|-----|----------|-----------|
| **Vultr** | 4GB | 2 | $10 | ✅ |
| **DigitalOcean** | 4GB | 2 | $12 | ✅ |
| **Linode** | 4GB | 2 | $12 | ✅ |

---

## Important Reminders

### ✅ DO:
- Start with testnet
- Start with dry_run
- Test for 1-2 weeks minimum
- Start with small capital (10-20%)
- Monitor daily first week
- Have emergency stop ready

### ❌ DON'T:
- Skip testnet testing
- Go live without dry run testing
- Risk money you can't afford to lose
- Disable position stops (40% is optimal)
- Run without monitoring first week

---

## Support

- **GitHub Issues:** Report bugs/problems
- **Strategy Documentation:** `../../docs/CRYPTO_HYBRID_STRATEGY.md`
- **Backtest Results:** `../../results/crypto_hybrid/`

---

## Version

- **Strategy Version:** 06 (Nick Radge Crypto Hybrid)
- **Last Updated:** 2025-10-14
- **Status:** Production Ready ✅

---

**Ready to deploy?** Follow the 3-step Quick Start above! 🚀
