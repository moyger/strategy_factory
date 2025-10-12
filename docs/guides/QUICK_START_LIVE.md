# Quick Start - Live Trading

## ✅ What You Have

The Nick Radge Momentum Strategy is **fully ready for live trading**!

**Files Created:**
- `deployment/live_nick_radge.py` - Live trading script
- `deployment/config_live.json` - Strategy configuration (auto-created)
- `LIVE_TRADING_GUIDE.md` - Complete guide

## 🚀 3 Steps to Go Live

### Step 1: Install Broker Library (Choose One)

**For Interactive Brokers:**
```bash
pip install ib_async
```

**For Bybit (Crypto):**
```bash
pip install ccxt
```

**For MT5 (Forex):**
```bash
pip install MetaTrader5  # Windows only
```

### Step 2: Configure Broker

Edit `deployment/config.json`:

```json
{
  "ibkr": {
    "enabled": true,  // ← Set to true
    "host": "127.0.0.1",
    "port": 7496,     // 7496 = paper trading, 7497 = real money
    "client_id": 1
  }
}
```

### Step 3: Run Live Trading

```bash
# DRY RUN (recommended first - no real orders)
python deployment/live_nick_radge.py --check-once

# LIVE TRADING (real money!)
# Edit deployment/config_live.json and set "dry_run": false
python deployment/live_nick_radge.py --broker ibkr # Capital auto-detected from broker
```

## 📊 What The Strategy Does

**Automatically:**
1. Downloads daily stock data for 50 S&P 500 stocks
2. Calculates 100-day momentum for each stock
3. Detects market regime (STRONG_BULL / WEAK_BULL / BEAR)
4. Selects top 7 highest momentum stocks
5. Rebalances quarterly (Jan, Apr, Jul, Oct)
6. Re-enters immediately on regime recovery (BEAR → BULL)
7. Goes to cash in bear markets

**Performance (Backtest):**
- 171% total return over 5 years
- 0.93 Sharpe ratio
- +29% outperformance vs SPY
- ~63% win rate

## ⚠️ Safety Features

**Built-in:**
- Maximum 20% per position
- Only trades stocks above 100-day MA
- Only trades stocks outperforming SPY
- Automatic cash position in bear markets

**Default Settings:**
- `dry_run: true` - No real orders until you change this!
- Hourly checks - Not over-trading
- Full logging to `logs/live_nick_radge.log`

## 📝 Configuration

Edit `deployment/config_live.json`:

```json
{
  "portfolio_size": 7,              // Number of stocks to hold
  "roc_period": 100,                // Momentum lookback (days)
  "max_position_size": 0.2,         // Max 20% per stock
  "dry_run": true,                  // ← MUST set to false for real trading

  "stock_universe": [
    "AAPL", "MSFT", "GOOGL", ...    // Customize your universe
  ]
}
```

## 🔍 Monitoring

**Check logs:**
```bash
tail -f logs/live_nick_radge.log
```

**Run one-time check:**
```bash
python deployment/live_nick_radge.py --check-once
```

This shows what the strategy would do WITHOUT executing any orders.

## 📚 Full Documentation

See `LIVE_TRADING_GUIDE.md` for:
- Complete broker setup instructions
- Risk management guidelines
- Troubleshooting
- Performance expectations
- Legal disclaimers

## ⚡ Example Workflow

```bash
# 1. Test once (no broker needed)
python deployment/live_nick_radge.py --check-once

# 2. Install broker library
pip install ib_async

# 3. Start broker platform (TWS or IB Gateway)

# 4. Configure broker
# Edit deployment/config.json → set ibkr.enabled = true

# 5. Test with broker connected (still dry-run)
python deployment/live_nick_radge.py --check-once

# 6. Review what it would do
cat logs/live_nick_radge.log

# 7. When ready for real trading:
# Edit deployment/config_live.json → set dry_run = false

# 8. Go live!
python deployment/live_nick_radge.py --broker ibkr # Capital auto-detected from broker
```

## 🎯 Expected Behavior

**On First Run:**
- Creates config files
- Downloads 200 days of stock data
- Calculates current market regime
- Shows target positions
- In dry-run: Shows orders but doesn't execute

**Ongoing:**
- Checks market every hour
- Rebalances quarterly
- Captures regime recoveries
- Logs all activity
- Prints account summary

## 💡 Pro Tips

1. **Start Small**: Use $5,000-10,000 initially
2. **Watch For Quarterly Rebalances**: Jan 1, Apr 1, Jul 1, Oct 1
3. **Trust The Process**: Strategy goes to cash in bear markets - this is correct!
4. **Be Patient**: Quarterly rebalancing means low activity
5. **Monitor Logs**: Check daily, don't micromanage

## ⚖️ Disclaimer

**IMPORTANT:** This software is for educational purposes. Trading involves substantial risk. Only trade with capital you can afford to lose. Past performance doesn't guarantee future results. You are solely responsible for your trading decisions.

**Always test thoroughly in paper trading before using real money!**

---

Ready to learn more? Read `LIVE_TRADING_GUIDE.md` for the complete guide! 📖
