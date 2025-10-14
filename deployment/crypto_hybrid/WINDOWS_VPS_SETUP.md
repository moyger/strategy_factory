# Windows VPS Setup Guide - Crypto Trading Bot

## Nick Radge Crypto Hybrid Strategy - Bybit Deployment on Windows VPS

### 🎯 Quick Summary

- **Strategy:** Nick Radge Crypto Hybrid (70/30 core/satellite)
- **Backtest:** 19,410% return (2020-2025), Sharpe 1.81
- **Position Stops:** 40% (optimal from testing)
- **Platform:** Windows Server 2016/2019/2022 or Windows 10/11
- **Broker:** Bybit (Official SDK or CCXT)

---

## 📋 Prerequisites

### 1. Windows VPS Requirements

**Minimum:**
- **OS:** Windows Server 2016+ or Windows 10/11
- **CPU:** 2 vCPU
- **RAM:** 4 GB
- **Storage:** 20 GB SSD
- **Network:** Stable internet (required 24/7)

**Recommended:**
- **CPU:** 4 vCPU
- **RAM:** 8 GB
- **Storage:** 40 GB SSD
- **Location:** Near Bybit servers (Singapore/Hong Kong for lower latency)

### 2. Software Requirements

- **Python:** 3.8, 3.9, 3.10, 3.11, or 3.12
- **Packages:** pybit (or ccxt), pandas, numpy, yfinance, vectorbt
- **Optional:** NSSM (for Windows service installation)

### 3. Connection Method Choice

📖 **See [BYBIT_ADAPTER_COMPARISON.md](BYBIT_ADAPTER_COMPARISON.md) for detailed comparison**

**Option A: Official Bybit SDK (pybit)** ⭐ Recommended
- Official from Bybit
- Best performance (~30-50% faster)
- Lighter weight (~2MB)
- Cutting-edge API features

**Option B: CCXT (Multi-Exchange)**
- Works with 100+ exchanges
- Easy to switch brokers
- Larger community support
- More generic approach

---

## 🚀 Installation Steps

### Step 1: Install Python on Windows VPS

1. **Download Python:**
   - Go to: https://www.python.org/downloads/
   - Download Python 3.11 or 3.12 (recommended)
   - Choose "Windows installer (64-bit)"

2. **Install Python:**
   - Run the installer
   - ✅ **IMPORTANT:** Check "Add Python to PATH"
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify Installation:**
   ```cmd
   python --version
   pip --version
   ```

### Step 2: Upload Strategy Files to VPS

**Option A: Direct Upload (RDP)**
1. Connect to VPS via Remote Desktop
2. Create folder: `C:\TradingBot`
3. Copy all files from `deployment/` folder to `C:\TradingBot`

**Option B: Git Clone**
```cmd
cd C:\
git clone https://github.com/YOUR_REPO/strategy_factory.git
cd strategy_factory\deployment
```

**Required Files:**
```
C:\TradingBot\
├── live_crypto_bybit.py          ← Main bot script
├── config_crypto_bybit.json      ← Configuration
├── bybit_adapter.py              ← CCXT connector (Option B)
├── bybit_adapter_official.py     ← Official SDK connector (Option A)
├── broker_interface.py           ← Base interface
├── setup_windows.bat             ← Setup script (choose adapter)
├── run_crypto_bot_windows.bat    ← Run script
└── install_windows_service.bat   ← Service installer
```

### Step 3: Run Setup Script

1. Open Command Prompt (cmd.exe)
2. Navigate to bot folder:
   ```cmd
   cd C:\TradingBot
   ```
3. Run setup:
   ```cmd
   setup_windows.bat
   ```

The setup script will prompt you to choose:
```
1. Official Bybit SDK (pybit) - RECOMMENDED
2. CCXT (Multi-exchange)
```

This will install all required Python packages:
- pybit or ccxt (Bybit connector)
- pandas (data analysis)
- numpy (calculations)
- yfinance (historical data)
- vectorbt (backtesting)

### Step 4: Configure the Bot

1. **Get Bybit API Keys:**
   - **Testnet:** https://testnet.bybit.com/
   - **Live:** https://www.bybit.com/ (only after testing!)

2. **Create API Key:**
   - Log in to Bybit
   - Go to: API Management → Create New Key
   - **Permissions:** Enable "Spot Trading" only
   - Save API Key and Secret

3. **Edit Configuration:**
   ```cmd
   notepad config_crypto_bybit.json
   ```

4. **Update Settings:**
   ```json
   {
       "testnet": true,              ← Keep as true for testing
       "dry_run": true,              ← Keep as true for testing
       "api_credentials": {
           "api_key": "YOUR_BYBIT_API_KEY",
           "api_secret": "YOUR_BYBIT_SECRET"
       },
       "trading_params": {
           "initial_capital": 10000  ← Set your capital (USDT)
       }
   }
   ```

5. **Save and close**

### Step 5: Test the Bot

```cmd
run_crypto_bot_windows.bat
```

**Expected Output:**
```
================================================================================
CRYPTO TRADING BOT - WINDOWS VPS
================================================================================

Python found: Python 3.11.x
Configuration file found: config_crypto_bybit.json

================================================================================
STARTING CRYPTO TRADING BOT
================================================================================

✅ Connected to Bybit (Testnet)
✅ DRY RUN MODE - No real trades
Strategy initialized successfully
...
```

**Press Ctrl+C to stop the bot**

---

## 🔧 Running as Windows Service

To run the bot 24/7 in the background:

### Option 1: Using Task Scheduler (Built-in)

1. **Open Task Scheduler:**
   - Press Win+R
   - Type: `taskschd.msc`
   - Press Enter

2. **Create Basic Task:**
   - Click "Create Basic Task"
   - Name: "Crypto Trading Bot"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: `C:\TradingBot\run_crypto_bot_windows.bat`

3. **Advanced Settings:**
   - Right-click task → Properties
   - Check: "Run whether user is logged on or not"
   - Check: "Run with highest privileges"
   - Configure for: Windows Server 2016+

### Option 2: Using NSSM (Recommended)

**NSSM** (Non-Sucking Service Manager) is the best way to run Python scripts as Windows services.

1. **Download NSSM:**
   - Go to: https://nssm.cc/download
   - Download: nssm-2.24.zip
   - Extract `nssm.exe` to `C:\TradingBot\`

2. **Install Service:**
   ```cmd
   cd C:\TradingBot
   install_windows_service.bat
   ```
   (Right-click → Run as Administrator)

3. **Start Service:**
   ```cmd
   sc start CryptoTradingBot
   ```

4. **Check Status:**
   ```cmd
   sc query CryptoTradingBot
   ```

5. **Manage via GUI:**
   - Press Win+R
   - Type: `services.msc`
   - Find: "Crypto Trading Bot"
   - Right-click → Start/Stop/Restart

---

## 📊 Monitoring on Windows

### View Logs

**Real-time (Command Prompt):**
```cmd
cd C:\TradingBot\logs
type crypto_bybit_live.log
```

**Continuous monitoring:**
```cmd
powershell Get-Content crypto_bybit_live.log -Wait -Tail 20
```

**Or use Notepad++:**
- Install: https://notepad-plus-plus.org/
- Open: `C:\TradingBot\logs\crypto_bybit_live.log`
- View → Monitoring (tail -f)

### Check Performance

```cmd
cd C:\TradingBot\logs
python -c "import pandas as pd; print(pd.read_csv('performance_crypto_bybit.csv').tail())"
```

### View Trades

```cmd
notepad logs\trades_crypto_bybit.csv
```

---

## 🛡️ Windows Firewall Configuration

The bot needs internet access. If Windows Firewall blocks Python:

1. **Open Windows Defender Firewall**
2. **Allow an app through firewall**
3. **Click "Change settings"**
4. **Click "Allow another app"**
5. **Browse to:** `C:\Python311\python.exe`
6. **Check both:** Private and Public networks
7. **Click OK**

---

## 🚨 Emergency Stop Procedures

### Method 1: Stop Running Script
- If running in Command Prompt: **Press Ctrl+C**

### Method 2: Kill Python Process
```cmd
taskkill /F /IM python.exe
```

### Method 3: Stop Windows Service
```cmd
sc stop CryptoTradingBot
```

Or via Services Manager:
- Press Win+R → `services.msc`
- Find "Crypto Trading Bot"
- Right-click → Stop

### Method 4: Enable Dry Run
1. Edit `config_crypto_bybit.json`
2. Set `"dry_run": true`
3. Restart bot

---

## 🔄 Auto-Restart on Crash

If bot crashes, auto-restart it:

### Using Task Scheduler:
1. Open Task Scheduler
2. Find your task → Properties
3. **Settings tab:**
   - Check: "If the task fails, restart every 5 minutes"
   - "Attempt to restart up to: 3 times"

### Using NSSM:
```cmd
nssm set CryptoTradingBot AppExit Default Restart
nssm set CryptoTradingBot AppRestartDelay 5000
```

---

## 📈 Performance Optimization for Windows VPS

### 1. Disable Windows Updates During Trading Hours

```cmd
sc config wuauserv start= demand
```

### 2. Set High Priority for Python

In Task Manager:
- Find python.exe
- Right-click → Set Priority → Above Normal

### 3. Disable Power Saving

```cmd
powercfg -change -standby-timeout-ac 0
powercfg -change -hibernate-timeout-ac 0
```

### 4. Keep VPS Time Synced

```cmd
w32tm /resync
```

---

## 🐛 Troubleshooting Windows-Specific Issues

### Error: "Python not found"

**Solution:**
```cmd
setx PATH "%PATH%;C:\Python311;C:\Python311\Scripts"
```
Then restart Command Prompt.

### Error: "pip not recognized"

**Solution:**
```cmd
python -m pip install --upgrade pip
```

### Error: "DLL load failed"

**Install Microsoft Visual C++ Redistributable:**
- Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
- Install and restart

### Error: "Permission denied"

**Run as Administrator:**
- Right-click → Run as Administrator

### Error: "Connection timeout"

**Check Windows Firewall:**
```cmd
netsh advfirewall show allprofiles
```

**Test connectivity:**
```cmd
ping api.bybit.com
```

---

## 🔒 Security Best Practices for Windows VPS

### 1. Enable Windows Firewall

```cmd
netsh advfirewall set allprofiles state on
```

### 2. Disable Unnecessary Services

```cmd
sc config "Remote Registry" start= disabled
```

### 3. Use Strong RDP Password

- Open: Computer Management → Local Users
- Change Administrator password (16+ characters)

### 4. Enable RDP Network Level Authentication

```cmd
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" /v UserAuthentication /t REG_DWORD /d 1 /f
```

### 5. Encrypt API Keys in Config

Consider using environment variables:

**Set environment variables:**
```cmd
setx BYBIT_API_KEY "your_api_key_here"
setx BYBIT_API_SECRET "your_secret_here"
```

**Update config:**
```json
{
    "api_credentials": {
        "api_key": "%BYBIT_API_KEY%",
        "api_secret": "%BYBIT_API_SECRET%"
    }
}
```

---

## 📊 Windows VPS Providers

### Recommended Providers:

**1. Vultr**
- Windows Server 2019
- Starting: $10/month (2 vCPU, 4GB RAM)
- Location: Singapore (low latency to Bybit)
- https://www.vultr.com/

**2. DigitalOcean**
- Windows Server 2022
- Starting: $12/month (2 vCPU, 4GB RAM)
- Location: Singapore
- https://www.digitalocean.com/

**3. Linode (Akamai)**
- Windows Server 2019
- Starting: $12/month (2 vCPU, 4GB RAM)
- Location: Singapore
- https://www.linode.com/

**4. AWS EC2**
- Windows Server 2022
- t3.small: ~$15/month
- Location: ap-southeast-1 (Singapore)
- https://aws.amazon.com/ec2/

### Cost Comparison:

| Provider | RAM | CPU | Storage | Price/mo | Singapore |
|----------|-----|-----|---------|----------|-----------|
| Vultr | 4GB | 2 | 80GB | $10 | ✅ |
| DigitalOcean | 4GB | 2 | 80GB | $12 | ✅ |
| Linode | 4GB | 2 | 80GB | $12 | ✅ |
| AWS | 2GB | 2 | 30GB | $15+ | ✅ |

---

## 📝 Deployment Checklist for Windows VPS

### Pre-Deployment:
- [ ] VPS provisioned (Windows Server 2016+)
- [ ] Python 3.8+ installed
- [ ] All files uploaded to `C:\TradingBot`
- [ ] Dependencies installed (`setup_windows.bat`)
- [ ] Bybit testnet API keys obtained
- [ ] Config file updated with API keys
- [ ] Config set to: `testnet: true`, `dry_run: true`

### Testing Phase (1-2 weeks):
- [ ] Bot runs without errors (`run_crypto_bot_windows.bat`)
- [ ] Logs show successful connection to Bybit
- [ ] Test data downloads correctly
- [ ] Rebalancing triggers on schedule
- [ ] Position stops work (if triggered)
- [ ] No crashes or exceptions in logs

### Service Setup:
- [ ] NSSM downloaded and placed in `C:\TradingBot`
- [ ] Windows service installed (as Administrator)
- [ ] Service set to auto-start
- [ ] Service tested (start/stop/restart)
- [ ] Logs confirm service runs correctly

### Pre-Live:
- [ ] Tested on testnet for 1-2 weeks minimum
- [ ] No errors in logs
- [ ] Config reviewed (capital, risk limits)
- [ ] Emergency stop procedure tested
- [ ] Firewall configured
- [ ] RDP password changed
- [ ] Backups configured

### Going Live:
- [ ] Update config: `testnet: false`, `dry_run: true` (test live data first)
- [ ] Test for 2-3 days
- [ ] Update config: `dry_run: false` (REAL MONEY!)
- [ ] Start with small capital (10-20% of target)
- [ ] Monitor daily for first week
- [ ] Set up alerts (Telegram optional)

---

## 🎯 Next Steps

1. **Read main guide:** [BYBIT_DEPLOYMENT_GUIDE.md](BYBIT_DEPLOYMENT_GUIDE.md)
2. **Set up Windows VPS** (follow this guide)
3. **Test on testnet** (1-2 weeks minimum)
4. **Monitor performance** (check logs daily)
5. **Go live with caution** (small capital first)

---

## 📞 Support & Resources

- **Main Deployment Guide:** BYBIT_DEPLOYMENT_GUIDE.md
- **Strategy Documentation:** CLAUDE.md
- **Backtest Results:** results/crypto/
- **GitHub Issues:** Report bugs/problems

---

## ⚠️ Important Notes

**DO NOT:**
- ❌ Skip testnet testing
- ❌ Go live without 1-2 weeks testing
- ❌ Risk more than you can afford to lose
- ❌ Disable position stops (40% is optimal)
- ❌ Run without monitoring for first week

**ALWAYS:**
- ✅ Start with testnet
- ✅ Start with dry_run
- ✅ Test thoroughly before live
- ✅ Monitor logs daily
- ✅ Have emergency stop ready

---

**Windows VPS setup is complete!** 🎉

Run `run_crypto_bot_windows.bat` to start testing on Bybit testnet.
