# How Capital Works in Live Trading

## ✅ Short Answer

**You don't need to specify capital!** The strategy automatically uses your **current broker account balance** for position sizing.

## 📊 How It Works

### 1. **Capital is Retrieved Dynamically**

Every time the strategy rebalances, it:

```python
# Gets your CURRENT account balance from the broker
balance = broker.get_balance()

# Calculates target positions based on CURRENT balance
for ticker, weight in allocations.items():
    target_value = balance * weight
    target_shares = target_value / current_price
```

### 2. **Balance Updates Automatically**

Your account balance changes constantly due to:
- ✅ **Profits** - Winning trades increase balance
- ❌ **Losses** - Losing trades decrease balance
- 💰 **Deposits** - Adding funds increases balance
- 💸 **Withdrawals** - Removing funds decreases balance

The strategy **adapts automatically** to your current balance!

### 3. **Example Scenario**

**Day 1:**
- Account balance: $10,000
- Target: 7 positions × 14.3% each
- Each position: ~$1,430

**Day 30 (after profits):**
- Account balance: $12,000 (gained $2,000!)
- Target: 7 positions × 14.3% each
- Each position: ~$1,716 (automatically larger!)

**Day 60 (after losses):**
- Account balance: $9,000 (lost $1,000)
- Target: 7 positions × 14.3% each
- Each position: ~$1,286 (automatically smaller!)

**You never have to update anything manually!**

---

## 🔧 Running the Strategy

### Old Way (Wrong ❌):
```bash
# Don't do this - capital parameter was removed!
python deployment/live_nick_radge.py --capital 10000
```

### New Way (Correct ✅):
```bash
# Capital is auto-detected from broker
python deployment/live_nick_radge.py --broker ibkr
```

The script will:
1. Connect to your broker
2. Get current account balance
3. Use that balance for position sizing
4. Update balance on every rebalance

---

## 📈 Position Sizing Logic

### How Allocations Are Calculated

The strategy uses **momentum-weighted allocations**:

```python
# Example: Current balance = $10,000, 7 positions

Stock Rankings by Momentum (ROC):
1. NVDA:  ROC = 45%  →  Weight = 45/200 = 22.5%  →  $2,250
2. AAPL:  ROC = 35%  →  Weight = 35/200 = 17.5%  →  $1,750
3. MSFT:  ROC = 30%  →  Weight = 30/200 = 15.0%  →  $1,500
4. GOOGL: ROC = 25%  →  Weight = 25/200 = 12.5%  →  $1,250
5. AMZN:  ROC = 25%  →  Weight = 25/200 = 12.5%  →  $1,250
6. META:  ROC = 20%  →  Weight = 20/200 = 10.0%  →  $1,000
7. TSLA:  ROC = 20%  →  Weight = 20/200 = 10.0%  →  $1,000
                       ─────────────────────────────
                       Total = 200%  = 100%    $10,000
```

**Key Points:**
- Stronger momentum stocks get larger allocations
- All positions sum to 100% of balance
- Balance is retrieved fresh each time

### Maximum Position Size Limit

To prevent over-concentration:

```python
# In config_live.json
{
  "max_position_size": 0.2  // Max 20% per position
}
```

Even if NVDA has very high momentum, it can't exceed 20% of your balance.

---

## 💡 Why This Is Better

### Old Approach (Fixed Capital):
❌ Have to manually update capital after profits/losses
❌ Position sizes don't scale with account growth
❌ Risk of using stale balance data
❌ Extra configuration parameter to manage

### New Approach (Dynamic Capital):
✅ **Automatically adapts** to current balance
✅ **Positions scale** with account growth
✅ **Always accurate** - uses real-time balance
✅ **Simpler** - one less parameter
✅ **Safer** - can't over-leverage accidentally

---

## 🔍 Monitoring Your Balance

### Check Balance Anytime

The strategy logs your balance on every check:

```
2025-10-09 09:35:00 - INFO - 💰 Account Balance: $12,543.87
2025-10-09 09:35:00 - INFO - 📊 Calculating target allocations...
2025-10-09 09:35:00 - INFO -    Target positions: 7
2025-10-09 09:35:00 - INFO -       NVDA: 22.50% ($2,822.37)
2025-10-09 09:35:00 - INFO -       AAPL: 17.50% ($2,195.18)
...
```

### View in Broker Platform

You can always check your exact balance in:
- **IBKR**: Account → Account Window
- **Bybit**: Assets → Wallet
- **MT5**: Terminal → Trade tab

---

## 🚨 Important Notes

### 1. **Balance vs. Equity**

The strategy uses **total account balance**, which typically includes:
- Cash available for trading
- Current position values
- Unrealized P&L

### 2. **Cash Reserve**

If you want to keep some cash on the sidelines:

```json
// In config_live.json
{
  "cash_reserve_pct": 0.1  // Keep 10% in cash (future feature)
}
```

Currently, the strategy uses 100% of available balance when fully invested.

### 3. **Adding/Withdrawing Funds**

**Adding Funds:**
- Deposit money to your broker account
- Next rebalance will automatically use new balance
- Positions will be sized larger

**Withdrawing Funds:**
- Withdraw money from broker account
- Next rebalance will automatically use new balance
- Positions will be sized smaller

**No manual intervention needed!**

### 4. **Multi-Currency Accounts**

If your broker account has multiple currencies:
- Balance is typically returned in base currency (USD, EUR, etc.)
- Make sure all stocks trade in the same currency
- Or configure multi-currency handling in broker adapter

---

## 🎯 Best Practices

### 1. **Start Small**
```python
# Your broker account: $5,000 - $10,000 initially
# Let it grow naturally
# Don't add/remove funds frequently
```

### 2. **Let It Compound**
```python
# Month 1: $10,000 → $10,500 (+5%)
# Month 2: $10,500 → $11,025 (+5%)  # Compounding!
# Month 3: $11,025 → $11,576 (+5%)  # Compounding!
```

### 3. **Monitor Performance**
```python
# Track your balance over time
# Compare to SPY benchmark
# Review quarterly rebalances
```

### 4. **Don't Micro-Adjust**
```python
# ❌ Don't withdraw profits frequently
# ❌ Don't add small amounts constantly
# ✅ Let the strategy compound
# ✅ Make changes quarterly if needed
```

---

## ❓ FAQ

**Q: What if I add $5,000 to my account mid-month?**
A: The strategy will see the new balance on the next rebalance (quarterly) and automatically size positions larger.

**Q: Can I specify a maximum account size to use?**
A: Yes, you can modify the code to cap the balance used:
```python
balance = min(broker.get_balance(), MAX_CAPITAL)
```

**Q: What if my balance goes below a minimum threshold?**
A: You can add a safety check:
```python
if balance < MIN_CAPITAL:
    logger.error("Balance too low, stopping strategy")
    return
```

**Q: Does this work with margin accounts?**
A: Yes, but be careful! The strategy will see your margin-enhanced buying power as available balance. Consider adding a leverage limit.

**Q: How often is the balance checked?**
A: Every time the strategy runs (hourly during market hours), but positions are only adjusted quarterly or on regime recovery.

---

## 📝 Summary

✅ **Capital is automatic** - retrieved from broker
✅ **Adapts to growth** - positions scale with profits
✅ **No manual updates** - always uses current balance
✅ **Safer** - can't over-leverage accidentally
✅ **Simpler** - one less thing to configure

**Just connect your broker and let it run!** 🚀
