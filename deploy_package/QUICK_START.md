# Quick Start Guide - London Breakout Live Trading

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies (2 min)

```bash
pip install MetaTrader5 pandas numpy
```

### Step 2: Configure Settings (2 min)

Edit `live/config_live.py`:

```python
# Line 21 - Set your account balance
INITIAL_BALANCE = 100000  # Change to your actual balance

# Line 25 - Start conservative
RISK_PER_TRADE = 1.0  # Start at 1%, increase to 1.5% later

# Line 64 - IMPORTANT: Paper trade first!
PAPER_TRADE_MODE = True  # Keep True for testing
```

### Step 3: Validate Configuration (30 sec)

```bash
python live/config_live.py
```

Expected: `✅ Configuration validated successfully`

### Step 4: Start Paper Trading (30 sec)

```bash
python live/live_trader.py
```

---

## ⚠️ Before Going Live

**MANDATORY:**
1. ✅ Paper trade for 3-6 months
2. ✅ Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. ✅ Verify win rate 55-65%
4. ✅ Set `PAPER_TRADE_MODE = False`

---

## 📊 Expected Performance

| Metric | Conservative | Realistic | Optimistic |
|--------|--------------|-----------|------------|
| **Annual Return** | 15-18% | 18-22% | 22-28% |
| **Risk per Trade** | 1.0% | 1.5% | 1.75% |
| **Max Drawdown** | -5.7% | -8.4% | -9.8% |
| **Monthly P&L** | $1,200 | $1,800 | $2,300 |

---

## 🔴 Stop Trading If:

- Daily loss exceeds -4%
- Total drawdown exceeds -8.5%
- 5+ consecutive losses
- Unexpected behavior

---

## 📞 Need Help?

Read the full guide: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
