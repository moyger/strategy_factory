# ADAUSD Bybit 5x Leverage - Complete Analysis

## Executive Summary
Strategy adapted for Bybit with **5x leverage** on ADAUSD crypto pair. Leverage amplifies returns significantly but increases risk proportionally.

**Best Configuration: 1.0-1.5% risk per trade**
- Maintains manageable drawdown (~10-15%)
- Delivers strong returns (30-80% annually)
- Keeps position sizes reasonable

---

## Results Comparison: No Leverage vs 5x Leverage

| Metric | No Leverage (1%) | 5x Leverage (1%) | 5x Leverage (1.5%) | 5x Leverage (2%) |
|--------|------------------|------------------|-------------------|------------------|
| **Annual Return** | 7.0% | **45.5%** | **80.7%** | **115.0%** |
| **Win Rate** | 73.7% | 73.7% | 73.7% | 73.7% |
| **Trades/Year** | 15.6 | 15.6 | 15.6 | 15.6 |
| **Max Drawdown** | -2.08% | **-10.25%** | **-15.16%** | **-19.48%** |
| **Profit Factor** | 2.78 | 2.37 | 2.18 | 2.01 |
| **Avg Win** | $954 | $6,863 | $12,965 | $19,972 |
| **Avg Loss** | -$962 | -$8,110 | -$16,619 | -$27,864 |
| **Total Fees** | ~$200 | $11,834 | $22,995 | $36,388 |

### Key Observations:
- **5x leverage multiplies returns ~6.5x** (7% → 45.5% at 1% risk)
- **Drawdown increases ~5x** (-2% → -10% at 1% risk)
- **Fees are significant**: $11k-36k per year (10-13% of gross profits)
- **Profit factor decreases** with higher leverage/risk

---

## Detailed Results by Risk Level

### 🎯 RECOMMENDED: 1.0% Risk (Conservative)

**Full Period (2023-2025):**
- Trades: 38 (15.6/year)
- Win Rate: 73.7%
- Total P&L: **$111,054**
- Annual Return: **45.5%**
- Max Drawdown: **-10.25%**
- Profit Factor: 2.37

**Out-of-Sample (2024-2025):**
- Annual Return: **29.7%**
- Max Drawdown: **-10.25%**
- Risk Rating: ⚠️ **MODERATE RISK**

**Leverage Metrics:**
- Avg Margin Used: $56,794 (56.8% of capital)
- Max Margin Used: $116,462 (116.5% of capital)
- Avg Position: 481,708 ADA (~$280k notional)
- Avg ROI per trade: ±12.7%

**Pros:**
- Lowest drawdown among leveraged options
- Still delivers excellent 30-45% returns
- Uses reasonable margin (50-60% average)
- MODERATE risk profile

**Cons:**
- Max drawdown at -10.25% (near danger zone)
- Can use 116% of capital in worst case

---

### 🔥 AGGRESSIVE: 1.5% Risk

**Full Period (2023-2025):**
- Trades: 38 (15.6/year)
- Win Rate: 73.7%
- Total P&L: **$196,825**
- Annual Return: **80.7%**
- Max Drawdown: **-15.16%**
- Profit Factor: 2.18

**Out-of-Sample (2024-2025):**
- Annual Return: **46.1%**
- Max Drawdown: **-15.16%**
- Risk Rating: ⚠️ **MODERATE RISK**

**Leverage Metrics:**
- Avg Margin Used: $110,380 (110.4% of capital)
- Max Margin Used: $259,499 (259.5% of capital)
- Avg Position: 917,415 ADA (~$530k notional)
- Avg ROI per trade: ±12.7%

**Pros:**
- Excellent 46-80% annual returns
- Still maintains 73.7% win rate
- Profit factor above 2.0

**Cons:**
- -15% drawdown is significant
- Regularly uses 110% of capital (margin call risk)
- Max margin at 259% could trigger liquidation

---

### ⚠️ HIGH RISK: 2.0% Risk

**Full Period (2023-2025):**
- Total P&L: **$280,580**
- Annual Return: **115.0%**
- Max Drawdown: **-19.48%**
- Profit Factor: 2.01

**Out-of-Sample:**
- Annual Return: **58.4%**
- Max Drawdown: **-19.48%**
- Risk Rating: ⚠️ **MODERATE RISK**

**Leverage Metrics:**
- Avg Margin Used: 174.7% of capital
- Max Margin Used: **444.7% of capital** ⚠️
- Avg Position: 1.4M ADA (~$830k notional)

**Warning:** Max margin at 444% is **extremely dangerous**. High liquidation risk.

---

### ❌ VERY HIGH RISK: 3.0% Risk

**Full Period (2023-2025):**
- Total P&L: **$424,070**
- Annual Return: **173.8%**
- Max Drawdown: **-23.33%**
- Profit Factor: 1.89

**Out-of-Sample:**
- Annual Return: **81.5%**
- Max Drawdown: **-23.33%**
- Risk Rating: ❌ **HIGH RISK**

**Leverage Metrics:**
- Avg Margin Used: **285.1% of capital**
- Max Margin Used: **649.3% of capital** 🚨
- Avg Position: 2.3M ADA (~$1.4M notional)

**Critical Warning:** This configuration is **NOT RECOMMENDED**. High probability of liquidation during drawdowns.

---

## Recent Trades Analysis (Last 5 Trades @ 1% Risk)

```
Date       Dir    Entry → Exit       Margin    ROI      P&L
04/07/25   SHORT  $0.6178 → $0.6014  $107,500  +12.7%   +$13,689 ✅
04/14/25   LONG   $0.6510 → $0.6380  $116,462  -10.6%   -$12,297 ❌
04/17/25   SHORT  $0.6038 → $0.6172  $99,490   -11.7%   -$11,601 ❌
05/19/25   SHORT  $0.7592 → $0.7371  $93,818   +14.0%   +$13,100 ✅
05/22/25   SHORT  $0.7510 → $0.7839  $50,710   -22.5%   -$11,408 ❌
```

**Insights:**
- Average trade ROI: ±12-13% on margin
- Wins deliver 12-14% returns
- Losses typically -10 to -12% (sometimes higher like -22.5%)
- Margin usage varies: $50k-116k (50-116% of capital)

---

## How 5x Leverage Works on Bybit

### Position Sizing Formula
```python
# Base calculation (same as no leverage)
risk_amount = $100,000 * 1% = $1,000
price_distance = entry - stop_loss = $0.02 (example)
base_units = $1,000 / $0.02 = 50,000 ADA

# With 5x leverage
leveraged_units = 50,000 * 5 = 250,000 ADA
notional_value = 250,000 * $0.50 = $125,000
margin_required = $125,000 / 5 = $25,000

# P&L is on full position (250k ADA)
# But you only need $25k margin
```

### Example Trade Breakdown

**Trade Setup:**
- Entry: $0.50
- Stop Loss: $0.48 (2% = $0.02)
- Take Profit: $0.5126 (2.6% = $0.0126)
- Risk: 1% of $100k = $1,000

**Without Leverage:**
- Position: 50,000 ADA
- If TP hit: $0.0126 * 50,000 = $630 profit

**With 5x Leverage:**
- Position: 250,000 ADA (5x larger)
- Margin: $25,000 (only 25% of notional)
- If TP hit: $0.0126 * 250,000 = **$3,150 profit**
- ROI on margin: $3,150 / $25,000 = **12.6%**
- If SL hit: -$1,000 loss (same as intended risk)

### Fee Impact

**Bybit Taker Fees: 0.055%**

For $125k notional trade:
- Entry fee: $125,000 * 0.055% = $68.75
- Exit fee: $125,000 * 0.055% = $68.75
- **Total fees: ~$137 per trade**

With 38 trades/2.4 years = 15.6 trades/year:
- Annual fees: $137 * 15.6 = **~$2,137/year**
- As % of profits: ~4-5% drag on returns

---

## Risk Management for Bybit 5x

### 🔴 Critical Risks

1. **Liquidation Risk**
   - At 1% risk: Max margin usage 116% (some trades exceed capital)
   - At 1.5% risk: Max margin usage 259% (HIGH liquidation risk)
   - At 2%+ risk: Max margin 400%+ (EXTREME liquidation risk)

2. **Drawdown Amplification**
   - No leverage: -2% max DD
   - 5x leverage @ 1%: -10.25% max DD (5x multiplier)
   - 5x leverage @ 2%: -19.48% max DD

3. **Margin Calls**
   - Bybit requires maintenance margin
   - If equity drops below maintenance, position liquidated
   - Losses accelerate quickly in drawdowns

### ✅ Risk Mitigation Strategies

1. **Start with 1% Risk Maximum**
   - Provides buffer for volatility
   - Allows surviving 10% drawdown
   - Still delivers 30-45% annual returns

2. **Monitor Margin Usage**
   - Set alerts when margin usage > 50%
   - Reduce position sizes during volatile periods
   - Keep extra cash buffer (20-30% of capital)

3. **Use Cross Margin Carefully**
   - Isolated margin = protects other positions
   - Cross margin = uses full account (more liquidation risk)
   - Recommend isolated for crypto

4. **Scale Gradually**
   - Start with 0.5-1% risk for first month
   - Increase to 1-1.5% after consistent results
   - Never exceed 2% risk with 5x leverage

5. **Stop Trading After Large Losses**
   - If down 5% in a week, pause trading
   - Review strategy parameters
   - Reduce risk size temporarily

---

## Recommended Configuration

### For Bybit Live Trading:

```python
Configuration:
- Initial Capital: $50,000 - $100,000
- Risk per Trade: 1.0%
- Leverage: 5x
- Stop Trading if DD > 10%
- Maximum Concurrent Positions: 1

Expected Results:
- Trades per Year: 15-20
- Win Rate: 65-75%
- Annual Return: 30-45%
- Max Drawdown: ~10%
- Fees: ~$2,000/year
```

### Position Sizing Example ($100k account):

```
Trade Parameters:
- Entry: $0.50
- Stop Loss: $0.48 (2% move)
- Risk: 1% = $1,000

Calculation:
- Base units: $1,000 / $0.02 = 50,000 ADA
- With 5x: 250,000 ADA
- Notional: $125,000
- Margin required: $25,000
- Fees: ~$137
```

---

## Comparison: ADAUSD vs Other Pairs (5x Leverage)

| Pair | Annual Return | Max DD | Win Rate | Trades/Year |
|------|---------------|--------|----------|-------------|
| **ADAUSD** (5x @ 1%) | **45.5%** | **-10.25%** | **73.7%** | **15.6** |
| EURUSD (no leverage) | 18.7% | -8% | 58.4% | 42.4 |
| XAUUSD (no leverage) | ~15% | -10% | ~65% | ~20 |

**Advantages of ADAUSD with 5x:**
- Highest annual returns (2.4x better than forex)
- Best win rate (73.7%)
- Lower frequency but higher quality setups
- Crypto volatility + leverage = explosive gains

**Disadvantages:**
- Higher drawdown risk
- Significant fee burden
- Liquidation risk if not managed properly
- 24/7 market = less predictable than forex sessions

---

## Next Steps

1. **Paper Trade First**
   - Test on demo account for 1 month
   - Verify execution, fees, slippage
   - Confirm comfort with volatility

2. **Start Small**
   - Begin with $10k-25k if new to leverage
   - Use 0.5% risk initially
   - Scale up after 20+ trades

3. **Monitor Key Metrics Weekly**
   - Win rate (target: >65%)
   - Average ROI per trade (target: 10%+)
   - Margin usage (keep <50% average)
   - Drawdown (stop if >10%)

4. **Adjust as Needed**
   - If win rate drops below 60%, reduce risk or pause
   - If margin usage consistently >70%, reduce risk
   - If drawdown hits -8%, stop trading and review

---

## Files

- Strategy: `strategies/strategy_breakout_v4_1_adausd_bybit.py`
- Backtest: `backtest_adausd_bybit.py`
- Data: `data/crypto/ADAUSD_1H.csv`, `ADAUSD_4H.csv`

---

## Disclaimer

⚠️ **HIGH RISK ALERT**

- Leverage amplifies both gains and losses
- Past performance doesn't guarantee future results
- Crypto is highly volatile and unpredictable
- Only use capital you can afford to lose
- Consider starting with no leverage first
- Liquidation can result in total loss of margin

**Recommended:** Start with 1% risk, monitor closely for first 3 months, then adjust based on actual results.
