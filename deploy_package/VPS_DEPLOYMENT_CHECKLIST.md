# VPS Deployment Checklist

## 📦 Files to Upload to Windows VPS

### ✅ Required Files (Must Upload)

```
02_MT5_triangle/
│
├── live/                           ⭐ CRITICAL - Main trading system
│   ├── config_live.py              ← Your configuration
│   ├── live_trader.py              ← Trading engine
│   └── test_config.py              ← Configuration tester
│
├── strategies/                     ⭐ CRITICAL - Strategy logic
│   ├── strategy_breakout_v4_1_optimized.py
│   ├── pattern_detector.py
│   └── __init__.py (if exists)
│
├── core/                           ⭐ CRITICAL - Core utilities
│   ├── session_manager.py
│   ├── indicators.py
│   ├── data_loader.py
│   └── __init__.py (if exists)
│
├── DEPLOYMENT_GUIDE.md             📚 Reference documentation
├── QUICK_START.md                  📚 Quick reference
└── requirements.txt                📦 Dependencies (create this)
```

### ❌ Files NOT Needed on VPS

```
❌ data/                    # Historical data (not needed for live trading)
❌ backtests/               # Backtest results
❌ output/                  # Charts and reports
❌ *.md (except guides)     # Markdown reports
❌ .git/                    # Git repository
❌ __pycache__/             # Python cache
❌ *.pyc                    # Compiled Python
```

---

## 📋 Step-by-Step VPS Setup

### Step 1: Prepare Files on Mac

Create a clean deployment folder:

```bash
cd /Users/karlomarceloestrada/Documents/@Projects/02_MT5_triangle

# Create deployment package
mkdir -p deploy_package
mkdir -p deploy_package/live
mkdir -p deploy_package/strategies
mkdir -p deploy_package/core

# Copy required files
cp live/config_live.py deploy_package/live/
cp live/live_trader.py deploy_package/live/
cp live/test_config.py deploy_package/live/

cp strategies/strategy_breakout_v4_1_optimized.py deploy_package/strategies/
cp strategies/pattern_detector.py deploy_package/strategies/

cp core/session_manager.py deploy_package/core/
cp core/indicators.py deploy_package/core/
cp core/data_loader.py deploy_package/core/

cp DEPLOYMENT_GUIDE.md deploy_package/
cp QUICK_START.md deploy_package/

# Create requirements.txt
cat > deploy_package/requirements.txt << 'EOF'
MetaTrader5>=5.0.0
pandas>=1.3.0
numpy>=1.21.0
EOF

echo "✅ Deployment package created in deploy_package/"
ls -la deploy_package/
```

### Step 2: Create ZIP Archive

```bash
cd deploy_package
zip -r ../london_breakout_vps.zip .
cd ..

echo "✅ Created london_breakout_vps.zip"
ls -lh london_breakout_vps.zip
```

### Step 3: Upload to VPS

**Option A: Using SFTP/SCP**
```bash
# Replace with your VPS details
scp london_breakout_vps.zip username@your-vps-ip:/path/to/destination/
```

**Option B: Using Remote Desktop**
1. Connect to Windows VPS via Remote Desktop
2. Copy `london_breakout_vps.zip` via shared clipboard
3. Or download from cloud storage (Dropbox/Google Drive)

**Option C: Using Git (if you have private repo)**
```bash
# On VPS
git clone https://github.com/yourusername/your-private-repo.git
```

---

## 🖥️ VPS Installation Steps

### On Your Windows VPS

#### 1. Install Python
```powershell
# Download Python 3.11+ from python.org
# Or use chocolatey:
choco install python311

# Verify
python --version
```

#### 2. Extract Files
```powershell
# Extract ZIP
Expand-Archive -Path london_breakout_vps.zip -DestinationPath C:\Trading\

cd C:\Trading
```

#### 3. Install Dependencies
```powershell
# Install packages
pip install -r requirements.txt

# Verify MT5 installation
python -c "import MetaTrader5 as mt5; print('MT5 version:', mt5.__version__)"
```

#### 4. Install MetaTrader 5
```powershell
# Download MT5 from your broker
# Install to default location (usually C:\Program Files\MetaTrader 5)
```

#### 5. Test Configuration
```powershell
python live/test_config.py
```

Expected output:
```
✅ Configuration validated successfully
```

#### 6. Create Folders
```powershell
mkdir live\logs
mkdir live\data
```

#### 7. Start Paper Trading
```powershell
python live/live_trader.py
```

---

## 📝 Minimal File Structure on VPS

After setup, your VPS should have:

```
C:\Trading\
│
├── live\
│   ├── config_live.py       ← Edit this before running
│   ├── live_trader.py        ← Main program
│   ├── test_config.py        ← Test first
│   ├── logs\                 ← Created automatically
│   └── data\                 ← Created automatically
│
├── strategies\
│   ├── strategy_breakout_v4_1_optimized.py
│   └── pattern_detector.py
│
├── core\
│   ├── session_manager.py
│   ├── indicators.py
│   └── data_loader.py
│
├── requirements.txt
├── DEPLOYMENT_GUIDE.md
└── QUICK_START.md
```

---

## ⚙️ VPS Configuration Checklist

### Before Starting Live Trader

- [ ] **Python installed** (3.9+)
- [ ] **Dependencies installed** (`pip install -r requirements.txt`)
- [ ] **MT5 installed** and configured
- [ ] **MT5 logged in** to your FTMO account
- [ ] **MT5 AutoTrading enabled** (Tools → Options → Expert Advisors)
- [ ] **Configuration edited** (`live/config_live.py`)
  - [ ] Set `INITIAL_BALANCE` to your actual balance
  - [ ] Keep `PAPER_TRADE_MODE = True` initially
  - [ ] Verify risk settings
- [ ] **Configuration validated** (`python live/test_config.py`)
- [ ] **Folders created** (`live/logs`, `live/data`)
- [ ] **Firewall allows** Python/MT5
- [ ] **VPS won't auto-shutdown** or sleep

### Security

- [ ] Use strong VPS password
- [ ] Enable VPS firewall
- [ ] Only allow RDP from your IP
- [ ] Don't expose unnecessary ports
- [ ] Keep Windows updated
- [ ] Use antivirus

---

## 🔧 Useful VPS Commands

### Check if Trader is Running
```powershell
# List Python processes
tasklist | findstr python

# Check logs
Get-Content live\logs\trading.log -Tail 50 -Wait
```

### Stop Trader
```powershell
# Press Ctrl+C in terminal

# Or force kill
taskkill /F /IM python.exe
```

### Run as Background Service (Advanced)

**Option 1: Using Task Scheduler**
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start program → `python.exe`
5. Arguments: `C:\Trading\live\live_trader.py`

**Option 2: Using NSSM (Non-Sucking Service Manager)**
```powershell
# Install NSSM
choco install nssm

# Create service
nssm install LondonBreakout "C:\Python311\python.exe" "C:\Trading\live\live_trader.py"

# Start service
nssm start LondonBreakout

# Check status
nssm status LondonBreakout
```

---

## 📊 File Sizes (Approximate)

```
live/config_live.py              ~15 KB
live/live_trader.py              ~18 KB
live/test_config.py              ~5 KB
strategies/*.py                  ~30 KB total
core/*.py                        ~20 KB total
requirements.txt                 ~1 KB
Documentation                    ~50 KB

Total (without logs/data):       ~140 KB
ZIP archive:                     ~40 KB

Very lightweight! 🎯
```

---

## 🎯 Quick Copy-Paste Commands

### Create Deployment Package
```bash
cd /Users/karlomarceloestrada/Documents/@Projects/02_MT5_triangle

mkdir -p deploy_package/{live,strategies,core}

cp live/{config_live.py,live_trader.py,test_config.py} deploy_package/live/
cp strategies/{strategy_breakout_v4_1_optimized.py,pattern_detector.py} deploy_package/strategies/
cp core/{session_manager.py,indicators.py,data_loader.py} deploy_package/core/
cp {DEPLOYMENT_GUIDE.md,QUICK_START.md} deploy_package/

echo "MetaTrader5>=5.0.0
pandas>=1.3.0
numpy>=1.21.0" > deploy_package/requirements.txt

cd deploy_package && zip -r ../london_breakout_vps.zip . && cd ..

echo "✅ Package created: london_breakout_vps.zip ($(du -h london_breakout_vps.zip | cut -f1))"
```

---

## ✅ Final Checklist Before Upload

- [ ] All required files in `deploy_package/`
- [ ] Reviewed `config_live.py` settings
- [ ] Created `requirements.txt`
- [ ] Zipped package created
- [ ] VPS provider selected and paid
- [ ] VPS credentials available
- [ ] Ready to upload and configure

---

## 🚨 Important Notes

### Do NOT Upload:
- ❌ Your historical data files (100+ MB, not needed)
- ❌ Backtest results and charts
- ❌ Git history
- ❌ Virtual environments

### Security:
- ⚠️ `config_live.py` will contain your FTMO credentials eventually
- ⚠️ Keep VPS access secure
- ⚠️ Use strong passwords
- ⚠️ Enable 2FA where possible

### Maintenance:
- 📅 Check VPS daily (first few weeks)
- 📅 Review logs weekly
- 📅 Update Python packages monthly
- 📅 Keep Windows updated

---

**Total Upload Size: ~40-50 KB (very small!)**

You're deploying a lightweight, efficient system! 🚀
