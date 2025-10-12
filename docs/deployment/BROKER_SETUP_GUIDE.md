# Broker Setup Guide

## Overview

The strategy supports three brokers:
1. **IBKR (Interactive Brokers)** - Recommended for stocks
2. **Bybit** - Crypto/futures
3. **MT5 (MetaTrader 5)** - Forex/CFDs

**For this strategy (stocks + GLD), IBKR is recommended.**

---

## 🏦 IBKR (Interactive Brokers) Setup

### Step 1: Create Account

1. Go to [www.interactivebrokers.com](https://www.interactivebrokers.com)
2. Click "Open Account"
3. Choose account type:
   - **Paper Trading** (for testing) - FREE
   - **Live Trading** (real money) - Requires funding

**Recommended:** Start with Paper Trading!

---

### Step 2: Install TWS or IB Gateway

**Download:**
- **TWS (Trader Workstation)** - Full featured (recommended for beginners)
- **IB Gateway** - Lightweight, API only (recommended for production)

**Links:**
- TWS: [https://www.interactivebrokers.com/tws](https://www.interactivebrokers.com/tws)
- Gateway: [https://www.interactivebrokers.com/gateway](https://www.interactivebrokers.com/gateway)

**Installation:**
1. Download for your OS
2. Install with default settings
3. Login with your IBKR credentials

---

### Step 3: Enable API Access

**In TWS/Gateway:**

1. **Edit → Global Configuration → API → Settings**

2. **Enable:**
   - ✅ "Enable ActiveX and Socket Clients"
   - ✅ "Allow connections from localhost only"
   - ✅ "Read-Only API" (for testing)

3. **Set Ports:**
   - **Paper Trading:** 7497
   - **Live Trading:** 7496

4. **Master API Client ID:** Leave blank (or use 0)

5. **Trusted IPs:** Add `127.0.0.1`

6. **Click OK** and **Restart TWS/Gateway**

---

### Step 4: Configure Strategy

**Edit `deployment/config.json`:**

```json
{
  "ibkr": {
    "enabled": true,          // ← Enable IBKR
    "host": "127.0.0.1",      // Localhost
    "port": 7497,             // Paper: 7497, Live: 7496
    "client_id": 1            // Unique ID (use 1 if running one bot)
  }
}
```

**For Paper Trading:**
- Port: `7497`
- Account: Your paper account login

**For Live Trading:**
- Port: `7496`
- Account: Your live account login

---

### Step 5: Test Connection

**Run dry run:**

```bash
python deployment/live_nick_radge.py --broker ibkr
```

**Expected Output:**

```
✅ Connected to IBKR
📊 Account Info:
   Account: DU1234567 (Paper)
   Balance: $1,000,000
   Currency: USD
```

**If connection fails:**
- Check TWS/Gateway is running
- Verify API settings enabled
- Check port number (7497 for paper)
- Ensure firewall not blocking

---

## 📱 Bybit Setup

### Step 1: Create Account

1. Go to [www.bybit.com](https://www.bybit.com)
2. Sign up for account
3. Complete KYC verification

### Step 2: Create API Keys

1. **Account → API Management**
2. **Create API Key**
3. **Settings:**
   - Name: "Nick Radge Strategy"
   - Permissions: ✅ Trade, ✅ Read
   - IP Restriction: Optional (add your IP)

4. **Save:**
   - API Key
   - Secret Key

**⚠️ IMPORTANT:** Never share your secret key!

---

### Step 3: Configure Strategy

**Edit `deployment/config.json`:**

```json
{
  "bybit": {
    "enabled": true,
    "api_key": "YOUR_ACTUAL_API_KEY",
    "api_secret": "YOUR_ACTUAL_SECRET",
    "testnet": true             // Start with testnet!
  }
}
```

**For Testnet (Testing):**
- `testnet: true`
- Use testnet API keys from [testnet.bybit.com](https://testnet.bybit.com)

**For Live:**
- `testnet: false`
- Use mainnet API keys

---

### Step 4: Test Connection

```bash
python deployment/live_nick_radge.py --broker bybit
```

**Note:** Bybit is primarily crypto. For stock strategy, use IBKR instead.

---

## 📊 MT5 (MetaTrader 5) Setup

### Step 1: Install MT5

1. Download from [www.metatrader5.com](https://www.metatrader5.com)
2. Install MT5 platform
3. Connect to broker server

### Step 2: Enable Algo Trading

1. **Tools → Options → Expert Advisors**
2. **Enable:**
   - ✅ "Allow algorithmic trading"
   - ✅ "Allow DLL imports"

### Step 3: Get Login Credentials

From your MT5 broker:
- Login number
- Password
- Server name

---

### Step 4: Configure Strategy

**Edit `deployment/config.json`:**

```json
{
  "mt5": {
    "enabled": true,
    "login": 12345678,              // Your MT5 login
    "password": "your_password",
    "server": "YourBroker-Server"   // e.g., "ICMarkets-Demo"
  }
}
```

---

### Step 5: Test Connection

```bash
python deployment/live_nick_radge.py --broker mt5
```

**Note:** MT5 is for forex/CFDs. For stocks, use IBKR.

---

## 🔧 Troubleshooting

### IBKR Connection Issues

**Error:** "Failed to connect"

**Solutions:**
1. Ensure TWS/Gateway is running
2. Check API enabled in settings
3. Verify correct port (7497 paper, 7496 live)
4. Restart TWS/Gateway
5. Check firewall settings

**Error:** "API connection closed"

**Solutions:**
1. Check "Enable ActiveX and Socket Clients"
2. Add `127.0.0.1` to trusted IPs
3. Increase timeout in TWS settings

**Error:** "Already connected"

**Solutions:**
1. Close other API connections
2. Change `client_id` in config
3. Restart TWS/Gateway

---

### Bybit Connection Issues

**Error:** "Invalid API key"

**Solutions:**
1. Verify API key copied correctly
2. Check using testnet keys for testnet
3. Regenerate API keys if needed

**Error:** "IP not whitelisted"

**Solutions:**
1. Add your IP to whitelist in Bybit
2. Use API key without IP restriction

---

### MT5 Connection Issues

**Error:** "Invalid credentials"

**Solutions:**
1. Verify login/password correct
2. Check server name exact match
3. Ensure account not locked

**Error:** "Connection timeout"

**Solutions:**
1. Check MT5 platform running
2. Verify server reachable
3. Check internet connection

---

## ✅ Recommended Setup

**For This Strategy (Stocks + GLD):**

### Best Choice: IBKR

**Why:**
- ✅ Best stock execution
- ✅ Low commissions
- ✅ GLD easily tradeable
- ✅ Robust API
- ✅ Paper trading available

**Setup:**
1. Create IBKR Paper account (free)
2. Install TWS
3. Enable API (port 7497)
4. Test with dry run
5. Paper trade 1 month
6. Open live account
7. Switch to live (port 7496)

---

### Alternative: Bybit

**Use if:**
- Trading crypto versions
- Want crypto exposure
- Prefer Bybit platform

**Note:** May not support traditional stocks/GLD

---

### Alternative: MT5

**Use if:**
- Trading CFDs on stocks
- Prefer MT5 platform
- Broker supports stocks

**Note:** CFDs have different characteristics than stocks

---

## 📋 Pre-Deployment Checklist

### IBKR Checklist

- [ ] IBKR account created
- [ ] TWS/Gateway installed
- [ ] API access enabled
- [ ] Port configured (7497 paper / 7496 live)
- [ ] Trusted IPs set
- [ ] Paper account funded
- [ ] Connection tested successfully
- [ ] Can retrieve balance
- [ ] Can retrieve positions

### Config File Checklist

- [ ] `deployment/config.json` created
- [ ] Broker credentials correct
- [ ] `enabled: true` for chosen broker
- [ ] Port/settings correct
- [ ] Testnet/paper mode enabled (for testing)

### Test Run Checklist

- [ ] Dry run completed successfully
- [ ] Connection established
- [ ] Data downloaded
- [ ] Orders generated (dry run)
- [ ] No errors in logs

---

## 🚀 Next Steps

Once broker is configured:

1. ✅ Test dry run: `python deployment/live_nick_radge.py --broker ibkr`
2. ✅ Verify connection successful
3. ✅ Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
4. ✅ Start paper trading
5. ✅ Monitor for 1 month
6. ✅ Go live with small capital

---

**Questions?** Check [LIVE_DEPLOYMENT_GUIDE.md](LIVE_DEPLOYMENT_GUIDE.md) for full details.
