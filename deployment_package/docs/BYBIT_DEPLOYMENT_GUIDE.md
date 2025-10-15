# Bybit Live Deployment Guide

## Nick Radge Crypto Hybrid Strategy - Live Trading on Bybit

### Backtest Performance (2020-2025)
- **Total Return:** 19,410% (148% annualized)
- **Sharpe Ratio:** 1.81
- **Max Drawdown:** -48.35%
- **Position Stops:** 8 triggered (SOL -88%, AVAX -79%, ETH -63%, etc.)
- **Optimal Threshold:** 40% position stop-loss

---

## 🚀 Quick Start

### 1. Choose Connection Method

**Option A: Official Bybit SDK (Recommended)** ⭐
```bash
pip install pybit pandas numpy
```

**Option B: CCXT (Multi-Exchange)**
```bash
pip install ccxt pandas numpy
```

📖 **See [BYBIT_ADAPTER_COMPARISON.md](BYBIT_ADAPTER_COMPARISON.md) for detailed comparison**

### 2. Get Bybit API Keys

1. Go to [Bybit Testnet](https://testnet.bybit.com/) or [Bybit Live](https://www.bybit.com/)
2. Create account and enable API access
3. Generate API Key and Secret
4. **IMPORTANT:** Enable "Spot Trading" permissions

### 3. Configure

Edit `deployment/config_crypto_bybit.json`:

```json
{
    "broker": "bybit",
    "broker_adapter": "official",  // or "ccxt" for multi-exchange
    "testnet": true,  // Start with testnet!
    "api_credentials": {
        "api_key": "YOUR_BYBIT_API_KEY",
        "api_secret": "YOUR_BYBIT_API_SECRET"
    },
    "trading_params": {
        "initial_capital": 10000  // USDT
    },
    "execution": {
        "dry_run": true  // ALWAYS start with dry_run!
    }
}
```

**Adapter Options:**
- `"broker_adapter": "official"` - Use Official Bybit SDK (pybit) ⭐ Recommended
- `"broker_adapter": "ccxt"` - Use CCXT (multi-exchange support)

### 4. Test Connection

```bash
python deployment/live_crypto_bybit.py --config deployment/config_crypto_bybit.json
```

---

## 🛡️ Safety Checklist

### Before Going Live

- [ ] Tested on **testnet** for 1+ weeks
- [ ] Verified all logs (no errors)
- [ ] Confirmed rebalancing triggers correctly
- [ ] Tested position stop-loss triggers
- [ ] Set `initial_capital` to acceptable risk amount
- [ ] Reviewed `max_daily_loss_pct` (default: 10%)
- [ ] Confirmed `emergency_stop_loss` (default: 50%)
- [ ] Set up Telegram notifications (optional but recommended)
- [ ] Have kill switch ready (`Ctrl+C` or set `dry_run: true`)

### Deployment Stages

**Stage 1: Testnet Dry Run** ✅ START HERE
```json
{
    "testnet": true,
    "dry_run": true
}
```
- No real money
- No API calls
- Only logs what it would do

**Stage 2: Testnet Live**
```json
{
    "testnet": true,
    "dry_run": false
}
```
- Uses testnet tokens (fake money)
- Real API calls to testnet
- Full simulation

**Stage 3: Live Dry Run**
```json
{
    "testnet": false,
    "dry_run": true
}
```
- Connected to live Bybit
- Uses real market data
- No real trades

**Stage 4: Live Trading** ⚠️ REAL MONEY
```json
{
    "testnet": false,
    "dry_run": false
}
```
- **REAL MONEY AT RISK**
- Only after weeks of testing
- Start with small capital

---

## 📊 Strategy Overview

### Core/Satellite Approach

**70% Core (Fixed):**
- BTC (23.3%)
- ETH (23.3%)
- SOL (23.3%)
- NEVER rebalanced (only on regime change)

**30% Satellite (Dynamic):**
- Top 3 alts from universe (6% each)
- Quarterly rebalancing
- TQS momentum ranking

### Risk Management

**1. Regime Filter (3-Tier)**
- **STRONG_BULL** (BTC > 200MA & > 100MA): 100% invested
- **WEAK_BULL** (BTC > 200MA): 85% invested (reduce satellite)
- **BEAR** (BTC < 200MA): 100% cash (USDT)

**2. Position Stop-Loss (40%)**
- Individual position exits at -40% from entry
- Caught 8 catastrophic failures in backtest
- Improved returns by +273% vs no stops

**3. Emergency Stop (50%)**
- Portfolio-level circuit breaker
- Exits ALL positions at -50% from peak
- Sends critical alert and stops trading

**4. Daily Loss Limit (10%)**
- Prevents runaway losses
- Pauses trading for the day

---

## 🔧 Configuration Reference

### Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `core_allocation` | 0.70 | Fixed core allocation (70%) |
| `satellite_allocation` | 0.30 | Dynamic satellite (30%) |
| `satellite_size` | 3 | Number of satellites |
| `qualifier_type` | "tqs" | Momentum ranking method |
| `position_stop_loss` | 0.40 | Position stop threshold (40%) |
| `regime_ma_long` | 200 | Long-term MA for regime |
| `regime_ma_short` | 100 | Short-term MA for regime |
| `rebalance_freq` | "QS" | Quarterly rebalancing |

### Universe (Top 15 Cryptos)

```
BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, AVAX/USDT,
DOGE/USDT, DOT/USDT, MATIC/USDT, LINK/USDT, UNI/USDT,
ATOM/USDT, XRP/USDT, BNB/USDT, LTC/USDT, BCH/USDT
```

### Execution Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rebalance_time` | "09:00" | UTC time for daily check |
| `rebalance_days` | "daily" | Check frequency |
| `dry_run` | true | Simulate trades (no execution) |
| `log_level` | "INFO" | Logging verbosity |

### Risk Limits

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_daily_loss_pct` | 0.10 | Max 10% daily loss |
| `max_single_position_pct` | 0.25 | Max 25% per position |
| `max_leverage` | 1.0 | No leverage (spot only) |
| `emergency_stop_loss` | 0.50 | Circuit breaker at -50% |

---

## 📈 Monitoring

### Logs

All logs are saved to `deployment/logs/`:

- **`crypto_bybit_live.log`** - Main log file
- **`trades_crypto_bybit.csv`** - All trades executed
- **`positions_crypto_bybit.csv`** - Position history
- **`performance_crypto_bybit.csv`** - Daily performance

### Real-Time Monitoring

```bash
# Watch main log
tail -f deployment/logs/crypto_bybit_live.log

# Monitor trades
tail -f deployment/logs/trades_crypto_bybit.csv

# Check performance
python -c "import pandas as pd; print(pd.read_csv('deployment/logs/performance_crypto_bybit.csv').tail())"
```

### Telegram Notifications (Optional)

Enable in config:

```json
{
    "notifications": {
        "telegram_enabled": true,
        "telegram_bot_token": "YOUR_BOT_TOKEN",
        "telegram_chat_id": "YOUR_CHAT_ID",
        "notify_on_trade": true,
        "notify_on_error": true,
        "notify_on_stop_loss": true
    }
}
```

Get bot token from [@BotFather](https://t.me/botfather) on Telegram.

---

## 🚨 Emergency Procedures

### How to Stop Trading

**Method 1: Graceful Shutdown**
```bash
# Press Ctrl+C in terminal
# Bot will finish current operations and disconnect
```

**Method 2: Kill Process**
```bash
pkill -f live_crypto_bybit
```

**Method 3: Enable Dry Run**
```bash
# Edit config_crypto_bybit.json
{
    "execution": {
        "dry_run": true  // Set to true
    }
}
# Restart bot - it will stop placing real trades
```

### How to Close All Positions

**Via Bot:**
- Bot automatically closes all positions on emergency stop (-50% DD)

**Manually:**
```python
# In Python console
from deployment.bybit_adapter import BybitAdapter

broker = BybitAdapter(api_key='...', api_secret='...')
broker.connect()

positions = broker.get_positions()
for symbol, pos in positions.items():
    broker.place_order(symbol, 'sell', pos.quantity, 'market')
```

**Via Bybit Web:**
- Log in to Bybit → Derivatives → Positions → Close All

---

## 📊 Performance Expectations

### Historical Backtest (2020-2025)

| Metric | Value |
|--------|-------|
| Total Return | 19,410% |
| Annualized Return | 148.82% |
| Sharpe Ratio | 1.81 |
| Max Drawdown | -48.35% |
| Winning Trades | 63% |
| Position Stops | 8 triggered |

### Typical Behavior

**Good Days:**
- BTC +5% → Portfolio +3-7%
- Rebalancing once per quarter
- 0-1 position stops per year

**Bad Days:**
- BTC -5% → Portfolio -3-7%
- May trigger position stops (-40%)
- Regime filter exits to cash in BEAR

**Crypto Winter (2022-2023):**
- Strategy exited to cash (USDT) via regime filter
- Position stops caught 6 failures
- Avoided -70% to -88% individual crashes

---

## ❓ Troubleshooting

### Connection Errors

**Error:** `ccxt not installed`
```bash
pip install ccxt
```

**Error:** `Invalid API key`
- Check API key/secret in config
- Verify API permissions (enable "Spot Trading")
- Confirm testnet vs live keys match `testnet` setting

**Error:** `Insufficient balance`
- Check USDT balance on Bybit
- Reduce `initial_capital` in config

### Strategy Errors

**Error:** `No data for symbol X`
- Symbol may not be available on Bybit
- Check symbol format: Use "BTC/USDT" not "BTCUSD"
- Remove unavailable symbols from universe

**Error:** `Min order size not met`
- Increase `initial_capital`
- Reduce `satellite_size`
- Check `min_order_size_usdt` (default: $10)

### Position Stop Issues

**Stops not triggering:**
- Position stops track from ENTRY price, not peak
- Check `position_stop_loss` is set (default: 0.40)
- Verify strategy initialized correctly (check logs)

**Too many stops:**
- 40% threshold is optimal from backtest
- Don't reduce below 30% (causes -38% underperformance)
- Review logs to ensure stops are legitimate failures

---

## 🎯 Best Practices

### Testing Protocol

1. **Testnet Dry Run** (1 week minimum)
   - Verify bot starts without errors
   - Confirm data fetching works
   - Check allocation calculations

2. **Testnet Live** (2 weeks minimum)
   - Monitor actual trades on testnet
   - Verify order execution
   - Test stop-loss triggers

3. **Live Dry Run** (1 week minimum)
   - Connect to live Bybit
   - Use real market data
   - Confirm calculations match testnet

4. **Live with Small Capital** (1 month minimum)
   - Start with 10-20% of target capital
   - Monitor closely
   - Gradually increase if performing well

### Position Sizing

**Conservative:** Start with $1,000 - $5,000
- Good for testing
- Limited losses if issues arise
- Easy to monitor

**Moderate:** $10,000 - $50,000
- Recommended after 1+ month testing
- Meaningful returns
- Still manageable risk

**Aggressive:** $50,000+
- Only after 3+ months success
- Requires constant monitoring
- Consider professional risk management

### Monitoring Schedule

**Daily:**
- Check logs for errors
- Review open positions
- Verify stop-losses working

**Weekly:**
- Review performance metrics
- Compare to backtest expectations
- Check Telegram alerts

**Monthly:**
- Analyze trade log
- Calculate Sharpe ratio
- Assess vs benchmarks (BTC, ETH)

**Quarterly:**
- Full performance review
- Verify rebalancing occurred
- Adjust universe if needed

---

## 📚 Additional Resources

### Documentation
- [CLAUDE.md](../CLAUDE.md) - Project overview
- [Strategy File](../strategies/06_nick_radge_crypto_hybrid.py) - Full strategy code
- [Backtest Results](../results/crypto/stop_loss_threshold_comparison.csv) - Threshold testing

### Support
- GitHub Issues: Report bugs
- CLAUDE.md: Architecture and design decisions
- Code comments: Inline documentation

### Related Strategies
- Stock version: `deployment/live_nick_radge.py`
- IBKR deployment: `deployment/config_tqs_ibkr.json`

---

## ⚠️ Disclaimer

**THIS IS FOR EDUCATIONAL PURPOSES ONLY**

- Trading cryptocurrencies involves significant risk
- Past performance does not guarantee future results
- Backtest results may not reflect live trading
- You can lose all your capital
- Only invest what you can afford to lose
- Not financial advice - do your own research
- Author is not responsible for any losses

**USE AT YOUR OWN RISK**

---

## 📝 Change Log

### 2025-10-14 - Initial Deployment
- Created live deployment for Bybit
- Implemented 40% position stops (optimal from testing)
- Added emergency stop-loss (50%)
- Configured for Nick Radge Crypto Hybrid strategy
- Tested on 2020-2025 data: 19,410% return

---

**Questions?** Review CLAUDE.md or check inline code comments.

**Ready to deploy?** Start with testnet dry run!
