# Live Trading Guide - Nick Radge Momentum Strategy

Complete guide to running the Nick Radge Momentum Strategy live with real money.

## 🚀 Quick Start

### 1. Test in Dry Run Mode (Recommended First Step)

```bash
# Run a single check without placing real orders
python deployment/live_nick_radge.py --check-once

# Run continuously in dry-run mode
python deployment/live_nick_radge.py --broker ibkr
```

This will:
- Download market data
- Calculate positions
- Show what orders WOULD be placed
- NOT execute any real trades

### 2. Configure Your Broker

Edit `deployment/config.json`:

```json
{
  "ibkr": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 7496,
    "client_id": 1
  }
}
```

### 3. Configure Strategy Parameters

Edit `deployment/config_live.json` (auto-created on first run):

```json
{
  "strategy_name": "Nick Radge Momentum",
  "portfolio_size": 7,
  "roc_period": 100,
  "ma_period": 100,
  "strong_bull_positions": 7,
  "weak_bull_positions": 3,
  "bear_positions": 0,
  "stock_universe": ["AAPL", "MSFT", "GOOGL", ...],
  "max_position_size": 0.2,
  "dry_run": true
}
```

### 4. Run Live Trading

**⚠️ IMPORTANT: Set `"dry_run": false` in config_live.json to place real orders!**

```bash
# Run with Interactive Brokers
python deployment/live_nick_radge.py --broker ibkr --capital 10000

# Run with Bybit (crypto)
python deployment/live_nick_radge.py --broker bybit --capital 5000

# Run with MT5 (forex/CFDs)
python deployment/live_nick_radge.py --broker mt5 --capital 10000
```

---

## 📋 Detailed Setup Instructions

### Step 1: Broker Setup

#### Option A: Interactive Brokers (IBKR)

1. **Download TWS or IB Gateway**
   - Download from: https://www.interactivebrokers.com/
   - Install and log in with your credentials

2. **Enable API Access**
   - Go to File → Global Configuration → API → Settings
   - Enable "ActiveX and Socket Clients"
   - Set Socket Port to 7496 (paper) or 7497 (live)
   - Uncheck "Read-Only API"

3. **Configure in config.json**
   ```json
   {
     "ibkr": {
       "enabled": true,
       "host": "127.0.0.1",
       "port": 7496,  // 7496 for paper, 7497 for live
       "client_id": 1
     }
   }
   ```

#### Option B: Bybit (Crypto)

1. **Create API Keys**
   - Log in to Bybit
   - Go to Account → API Management
   - Create new API key with trading permissions

2. **Configure in config.json**
   ```json
   {
     "bybit": {
       "enabled": true,
       "api_key": "YOUR_API_KEY",
       "api_secret": "YOUR_API_SECRET",
       "testnet": true  // Set to false for real trading
     }
   }
   ```

#### Option C: MetaTrader 5 (Forex/CFDs)

1. **Open MT5 Account**
   - Download MT5 from your broker
   - Log in with your credentials

2. **Configure in config.json**
   ```json
   {
     "mt5": {
       "enabled": true,
       "login": 12345678,
       "password": "YOUR_PASSWORD",
       "server": "YourBroker-Server"
     }
   }
   ```

---

### Step 2: Strategy Configuration

The `config_live.json` file controls all strategy parameters:

```json
{
  "strategy_name": "Nick Radge Momentum",

  // Portfolio Construction
  "portfolio_size": 7,              // Hold top 7 stocks
  "roc_period": 100,                // 100-day momentum lookback
  "ma_period": 100,                 // 100-day moving average

  // Regime-Based Position Sizing
  "strong_bull_positions": 7,       // Hold 7 stocks in strong bull market
  "weak_bull_positions": 3,         // Hold 3 stocks in weak bull market
  "bear_positions": 0,              // Go to cash in bear market

  // Stock Universe (S&P 500 stocks)
  "stock_universe": [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    // ... add up to 50+ stocks for best results
  ],

  // Risk Management
  "max_position_size": 0.2,         // Max 20% per position
  "lookback_days": 200,             // Historical data for indicators

  // Execution
  "rebalance_time": "09:35",        // Rebalance at 9:35 AM ET
  "check_interval_minutes": 60,     // Check every hour

  // Safety
  "dry_run": true                   // MUST set to false for real trading
}
```

---

### Step 3: Testing Before Going Live

#### Test 1: Single Check (No Orders)

```bash
python deployment/live_nick_radge.py --check-once
```

**What it does:**
- Downloads market data
- Calculates momentum rankings
- Shows target positions
- Displays what orders would be placed
- Does NOT execute anything

**Expected output:**
```
📊 Current Market Regime: STRONG_BULL
🔄 Rebalancing: Quarterly rebalance
📊 Calculating target allocations...
   Target positions: 7
      NVDA: 18.50%
      AAPL: 16.20%
      ...
🔄 Calculating rebalance orders...
   📈 BUY NVDA: 45 shares ($8,100.00)
   📈 BUY AAPL: 92 shares ($7,200.00)
   ...
   ⚠️  DRY RUN MODE - Orders not sent to broker
```

#### Test 2: Continuous Dry Run

```bash
python deployment/live_nick_radge.py --broker ibkr
```

**What it does:**
- Runs continuously
- Checks every hour
- Logs all activity to `logs/live_nick_radge.log`
- Still in dry-run mode (safe)

**Let it run for a few hours/days to verify:**
- Data downloads correctly
- Positions calculate correctly
- No errors in logs

---

### Step 4: Go Live (Real Money)

#### ⚠️ Pre-Flight Checklist

Before setting `dry_run: false`, verify:

- [ ] Broker connection works
- [ ] Account has sufficient funds
- [ ] Stock universe is correctly configured
- [ ] Position sizes are reasonable
- [ ] Tested in dry-run mode for 24+ hours
- [ ] Understand the strategy risks
- [ ] Have stop-loss plan
- [ ] Know how to manually close positions

#### Enable Live Trading

1. Edit `deployment/config_live.json`:
   ```json
   {
     "dry_run": false  // ⚠️ This enables real trading!
   }
   ```

2. Start with small capital:
   ```bash
   python deployment/live_nick_radge.py --broker ibkr --capital 5000
   ```

3. Monitor the logs:
   ```bash
   tail -f logs/live_nick_radge.log
   ```

---

## 🔧 Advanced Configuration

### Custom Stock Universe

Edit `config_live.json` to trade different stocks:

```json
{
  "stock_universe": [
    // Tech sector focus
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "AMD", "INTC", "QCOM", "ORCL", "ADBE", "CRM", "AVGO",

    // Or specific industry
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK",

    // Or mega-caps only
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "BRK.B", "UNH", "JNJ", "V", "WMT", "XOM", "JPM"
  ]
}
```

### Adjust Risk Parameters

**Conservative (Lower Risk):**
```json
{
  "portfolio_size": 10,           // More diversification
  "max_position_size": 0.15,      // Max 15% per position
  "strong_bull_positions": 5,     // Hold fewer stocks
  "weak_bull_positions": 2,
  "bear_positions": 0
}
```

**Aggressive (Higher Risk):**
```json
{
  "portfolio_size": 5,            // Concentrated positions
  "max_position_size": 0.25,      // Max 25% per position
  "strong_bull_positions": 7,
  "weak_bull_positions": 5,
  "bear_positions": 1            // Stay partially invested in bear
}
```

---

## 📊 Strategy Logic

### When Does It Trade?

1. **Quarterly Rebalancing**
   - January 1, April 1, July 1, October 1
   - Or first trading day of quarter

2. **Regime Recovery**
   - Immediately when market regime changes from BEAR → BULL
   - This is the secret sauce - captures early recoveries

3. **Position Exits**
   - When stock drops out of top 7 momentum rankings
   - When bear market detected (goes to cash)

### Market Regime Detection

Based on SPY (S&P 500 ETF):

- **STRONG_BULL**: SPY > 200-day MA → Hold 7 positions
- **WEAK_BULL**: 50-day MA < SPY < 200-day MA → Hold 3 positions
- **BEAR**: SPY < 50-day MA → Go to cash (0 positions)
- **UNKNOWN**: Insufficient data → Go to cash

### Position Sizing

**Momentum Weighting** (default):
- Stronger momentum stocks get larger allocations
- Example: If NVDA has 2x the momentum of AAPL, it gets 2x the allocation

**Equal Weight** (alternative):
- All 7 positions get equal weight (14.3% each)
- Simpler but potentially lower returns

---

## 🚨 Risk Management

### Built-in Safety Features

1. **Maximum Position Size**
   - Default: 20% max per stock
   - Prevents over-concentration

2. **Regime-Based Sizing**
   - Automatically reduces positions in weak markets
   - Goes to cash in bear markets

3. **Diversification**
   - Minimum 5-7 positions (when invested)
   - Across multiple sectors

4. **Relative Strength Filter**
   - Only buys stocks outperforming SPY
   - Avoids weak stocks

### Manual Risk Controls

**Set Stop-Loss Levels:**
```python
# In config_live.json, add:
{
  "max_portfolio_drawdown": 0.25,  // Exit all if down 25%
  "max_position_loss": 0.15        // Close position if down 15%
}
```

**Monitor Daily:**
- Check `logs/live_nick_radge.log`
- Review positions in broker platform
- Track performance vs SPY

**Emergency Stop:**
```bash
# Press Ctrl+C to stop the script
# Or manually close all positions in broker
```

---

## 📈 Monitoring & Maintenance

### Daily Tasks

1. **Check Logs**
   ```bash
   tail -n 50 logs/live_nick_radge.log
   ```

2. **Verify Positions**
   - Compare script positions vs broker positions
   - Ensure orders executed correctly

3. **Monitor Performance**
   - Track daily P&L
   - Compare to SPY benchmark

### Weekly Tasks

1. **Review Rebalances**
   - Check if quarterly rebalance executed
   - Verify regime recovery triggers

2. **Update Stock Universe**
   - Remove delisted stocks
   - Add new high-momentum stocks

### Monthly Tasks

1. **Performance Review**
   - Generate QuantStats report
   - Compare to backtest expectations
   - Adjust parameters if needed

2. **Broker Reconciliation**
   - Match positions
   - Verify commissions
   - Check for errors

---

## 🐛 Troubleshooting

### Connection Issues

**Problem:** "Failed to connect to broker"

**Solutions:**
- Check TWS/Gateway is running
- Verify port number (7496 vs 7497)
- Check firewall settings
- Restart broker platform

### Data Issues

**Problem:** "Could not download market data"

**Solutions:**
- Check internet connection
- Verify ticker symbols are correct
- Try using different data source
- Check if market is open

### Order Execution Issues

**Problem:** "Failed to place order"

**Solutions:**
- Check account has sufficient funds
- Verify trading permissions
- Check if stock is tradeable
- Review broker error messages

### Performance Issues

**Problem:** "Strategy underperforming backtest"

**Possible causes:**
- Slippage higher than expected
- Commissions eating into returns
- Different market regime
- Data quality issues

**Solutions:**
- Review execution prices
- Adjust commission/slippage estimates
- Compare regime to backtest period
- Verify data accuracy

---

## 💡 Tips for Success

### 1. Start Small
- Begin with paper trading
- Use minimum capital ($5,000-$10,000)
- Scale up gradually

### 2. Be Patient
- Strategy rebalances quarterly
- May stay in cash during bear markets
- Don't override the system

### 3. Trust the Process
- Regime recovery is powerful
- Going to cash preserves capital
- Momentum works over time

### 4. Monitor But Don't Micromanage
- Check daily, don't trade daily
- Let quarterly rebalances work
- Trust the regime filter

### 5. Keep Records
- Save all log files
- Track every trade
- Document changes to config

---

## 📞 Support & Resources

### Log Files
- `logs/live_nick_radge.log` - Full trading log
- `logs/` - All strategy logs

### Configuration Files
- `deployment/config.json` - Broker settings
- `deployment/config_live.json` - Strategy settings

### Documentation
- `README.md` - Project overview
- `examples/example_nick_radge_momentum.py` - Backtest example
- `strategies/nick_radge_momentum_strategy.py` - Strategy code

### Backtest Before Trading
```bash
python examples/example_nick_radge_momentum.py
```

Review the QuantStats report to understand expected performance before going live!

---

## ⚖️ Legal Disclaimer

This software is provided for educational and research purposes only. Trading stocks involves substantial risk of loss. Past performance does not guarantee future results. You are solely responsible for your trading decisions and outcomes. The authors and contributors are not liable for any losses incurred through use of this software.

**Always:**
- Understand the risks
- Only trade capital you can afford to lose
- Seek professional financial advice if needed
- Test thoroughly before going live

---

## 🎯 Expected Performance

Based on 5-year backtest (2020-2025):

- **Total Return:** 170%+
- **Sharpe Ratio:** 0.9+
- **Max Drawdown:** ~31%
- **Win Rate:** ~63%
- **Outperformance vs SPY:** +25-40%

**Key Features:**
- Quarterly rebalancing reduces trading costs
- Regime recovery captures market rebounds
- Cash positions during bear markets preserve capital
- Momentum weighting improves returns

**Remember:** Live results WILL differ from backtest due to:
- Execution slippage
- Commission costs
- Data timing differences
- Market regime changes
- Psychological factors

Good luck and trade safely! 🚀
