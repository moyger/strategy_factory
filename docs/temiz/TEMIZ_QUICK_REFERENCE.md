# Temiz Strategy - Quick Reference Card

## 🎯 Strategy At A Glance

**Type:** Intraday small-cap shorts (parabolic exhaustion)
**Timeframe:** 1-minute bars
**Win Rate:** 60-70% (with filters)
**Profit Factor:** 2.5-3.5
**Risk/Trade:** 0.5% of account
**Max Daily Loss:** -2% (kill switch)

---

## 📋 Three Setups (Priority Order)

### 1. Parabolic Exhaustion (70% WR) ⭐⭐⭐
```
Entry:
✓ VWAP Z-score >2.5
✓ Blow-off candle (wick >60%)
✓ Volume >5× average
✓ Price velocity >2%/min

Stop: 2% above high
Conviction: HIGH
```

### 2. First Red Day (60% WR) ⭐⭐
```
Entry:
✓ First red after 3+ greens
✓ VWAP Z-score >1.5
✓ RVOL >2.0
✓ After 9:45 AM

Stop: 3% above high
Conviction: MEDIUM
```

### 3. Backside Fade (55% WR) ⭐
```
Entry:
✓ Failed breakout
✓ Below VWAP
✓ RVOL >2.0
✓ After 11:00 AM

Stop: 2% above recent high
Conviction: LOW
```

---

## 🎲 Position Sizing

```python
# Fixed fractional (0.5% risk)
risk_amount = account_equity × 0.005
shares = risk_amount / (stop_loss - entry_price)

# Max position value = 10% of account
max_shares = (account_equity × 0.10) / entry_price
shares = min(shares, max_shares)
```

**Example:**
- Account: $100,000
- Risk: $500 (0.5%)
- Entry: $50, Stop: $52
- Risk/share: $2
- Shares: 500 / 2 = **250 shares**

---

## 📊 Exit Strategy (Scale Out)

```
Position: 300 shares

R2 (2× risk):   Sell 100 shares (1/3)
R1 (1× risk):   Sell 100 shares (1/3)
VWAP (runner):  Sell 100 shares (1/3)

Hard Stop: Entry stop loss (close all)
EOD Exit: 3:55 PM (close all remaining)
```

**Example:**
- Entry: $50, Stop: $52, Risk: $2
- R1: $48 (1× risk = $2 profit)
- R2: $46 (2× risk = $4 profit)
- VWAP: $45 (dynamic, trail to VWAP)

---

## ✅ Pre-Trade Checklist

**Stock Criteria:**
- [ ] Gap >5% from previous close
- [ ] Float <20M shares (ideal <10M)
- [ ] RVOL >2.0 (relative volume)
- [ ] No major news catalyst (check Alpaca news)
- [ ] History of pump-and-dump (6+ months chart)

**Technical Criteria:**
- [ ] Setup detected (Parabolic/First Red/Backside)
- [ ] VWAP Z-score meets threshold
- [ ] Volume climax present
- [ ] Time window appropriate (9:30-3:00 PM)

**Confluence Filters:**
- [ ] Composite score ≥50/100
- [ ] News check: No positive catalyst
- [ ] Historical: Repeat pumper (3+ prior spikes)
- [ ] Float rotation: >1× today

**Risk Checks:**
- [ ] Position count <3 (max concurrent)
- [ ] Daily loss <2% (kill switch)
- [ ] Short available (check HTB status)
- [ ] Slippage acceptable (<2%)

---

## 🚫 Never Trade If...

❌ **Stock has breaking news:**
- FDA approval, clinical trial
- Earnings beat, revenue growth
- Merger, acquisition, partnership
- Insider buying, analyst upgrade

❌ **Technical conditions poor:**
- RVOL <2.0 (thin volume)
- Float >50M (too liquid)
- No pump history (unknown behavior)
- First 15 minutes (too choppy)

❌ **Risk limits hit:**
- Daily loss -2% (kill switch)
- 3 positions already open
- Account equity <$25k (PDT rule)
- Short unavailable (HTB)

---

## 📈 Confluence Filter Scoring

**News Sentiment (40% weight):**
- 100 = No news (best)
- 50 = Neutral news
- 0 = Positive catalyst (avoid)

**Historical Analysis (40% weight):**
- 70-100 = Excellent (5+ prior spikes)
- 50-69 = Good (3-4 spikes)
- 0-49 = Poor (unknown)

**Float Rotation (20% weight):**
- 70-100 = Excellent (RVOL >5×, rotation >2×)
- 50-69 = Good (RVOL >3×, rotation >1×)
- 0-49 = Poor (RVOL <2×)

**Composite Score:**
```
70-100 → STRONG SHORT (full position, HIGH conviction)
50-69  → SHORT (reduce 50%, MEDIUM conviction)
30-49  → WEAK SHORT (reduce 75%, LOW conviction)
0-29   → AVOID (skip entirely)
```

---

## 💻 Quick Code Snippets

### Load Data
```python
from data.alpaca_data_loader import AlpacaDataLoader

loader = AlpacaDataLoader(api_key='...', secret_key='...', paper=True)
bars = loader.get_1min_bars('GME', '2021-01-28', '2021-01-28')
```

### Scan for Signals
```python
from indicators.intraday_indicators import calculate_all_indicators
from strategies.temiz_small_cap_short_strategy import TemizSmallCapShortStrategy

indicators = calculate_all_indicators(bars)
strategy = TemizSmallCapShortStrategy()
signals = strategy.scan_for_signals(bars, indicators)
```

### Check Quality
```python
from indicators.confluence_filters import ConfluenceFilters

filters = ConfluenceFilters(alpaca_api_key='...', alpaca_secret_key='...')
result = filters.get_composite_score(
    symbol='GME',
    current_volume=50_000_000,
    avg_volume_20d=10_000_000,
    float_shares=50_000_000
)

if result['composite_score'] >= 70:
    # STRONG SHORT - take trade
```

### Run Backtest
```python
from examples.backtest_temiz_strategy import TemizBacktester

backtester = TemizBacktester(initial_capital=100000)
results = backtester.backtest_single_day('GME', bars, strategy, verbose=True)
backtester.print_results()
```

---

## 🎯 Performance Targets

**Per Trade:**
- Average R: 0.8-1.2R
- Win rate: 60-70%
- Risk/reward: 1:2 (target 2R average winner)

**Daily:**
- Max trades: 3-5
- Max loss: -2% (kill switch)
- Target: +1-3% (realistic)

**Monthly:**
- Target return: 10-20%
- Max drawdown: <15%
- Win rate: 60-70%
- Profit factor: >2.5

**Annual:**
- Target return: 100-200%+ (highly variable)
- Max drawdown: <25%
- Sharpe ratio: 1.5-2.5

---

## 📱 Morning Routine (30 min)

**9:00 AM - Pre-Market Prep:**
1. Scan gap-up stocks (Finviz screener)
2. Filter: Gap >5%, float <20M, volume >500k
3. Check news on each (TradingView news tab)
4. Analyze daily chart (pump history?)
5. Create watchlist (10-20 tickers max)

**9:30 AM - Market Open:**
1. Watch watchlist for setup signals
2. Wait 15 minutes (avoid opening chop)
3. Run confluence filters on signals
4. Take only HIGH/MEDIUM conviction setups

**3:55 PM - Close:**
1. Close all remaining positions
2. Log results (setup type, R-multiple, exit reason)
3. Review day (what worked, what didn't)

---

## 🛠️ Tools & Resources

**Free Tools:**
- Alpaca Paper API (data + news): https://alpaca.markets
- TradingView (charting): https://tradingview.com
- Finviz (screener): https://finviz.com/screener.ashx
- yfinance (historical data): Via Python

**Paid Tools (Optional):**
- Alpaca Live ($9/mo): Real-time data
- Norgate ($29/mo): Survivorship-free data
- Trade-Ideas ($99+/mo): Scanner for runners
- Polygon.io ($29-99/mo): Professional data

**Broker:**
- Interactive Brokers (IBKR): Best for shorts (locate availability)
- Alpaca Live: Good for stocks (no shorting yet)

---

## 📊 Key Metrics to Track

**Trade-Level:**
- Setup type (Parabolic/First Red/Backside)
- Conviction (HIGH/MEDIUM/LOW)
- Filter score (0-100)
- Entry price, stop, targets
- R-multiple achieved
- Exit reason (R1/R2/VWAP/STOP/EOD)

**Daily:**
- Trades taken
- Win rate
- P&L ($, %)
- Max drawdown (intraday)
- Largest winner/loser

**Weekly/Monthly:**
- Total trades
- Win rate by setup type
- Average R by conviction level
- Profit factor
- Filter effectiveness (filtered vs unfiltered)

---

## 🚨 Common Mistakes

**Mistake 1:** Shorting too early (before exhaustion)
- **Fix:** Wait for blow-off candle + volume climax

**Mistake 2:** Ignoring news catalysts
- **Fix:** Always check Alpaca news (24hr lookback)

**Mistake 3:** Over-trading low-quality setups
- **Fix:** Only trade filter score ≥50, prefer ≥70

**Mistake 4:** Not respecting stops
- **Fix:** Hard stop at entry level, no second chances

**Mistake 5:** Holding overnight
- **Fix:** Close all by 3:55 PM ET, no exceptions

**Mistake 6:** Trading in first 15 minutes
- **Fix:** Wait until 9:45 AM (let opening range form)

**Mistake 7:** Shorting strong uptrends
- **Fix:** Check daily chart, need pump history

**Mistake 8:** Position sizing too large
- **Fix:** 0.5% risk per trade, max 10% position value

---

## 📞 Emergency Procedures

**Kill Switch Triggered (-2% daily loss):**
1. Close all positions immediately
2. Stop trading for the day
3. Review what went wrong
4. Resume next trading day

**Stuck in Losing Position:**
1. Check stop loss (2-3% from entry)
2. If hit, close immediately
3. Don't move stop or hope for recovery
4. Accept the loss, move on

**News Breaks While In Position:**
1. Check headline (positive or negative?)
2. If positive news: Close immediately (avoid squeeze)
3. If negative news: Hold for target (catalyst in your favor)

**Platform/Data Outage:**
1. Have IBKR/TradingView as backup
2. Close positions manually if needed
3. Don't enter new trades during outage

---

## 📚 Learn More

**Full Documentation:**
- Strategy Guide: `TEMIZ_STRATEGY_GUIDE.md`
- Filter Guide: `CONFLUENCE_FILTERS_GUIDE.md`
- Implementation Summary: `TEMIZ_IMPLEMENTATION_SUMMARY.md`

**Code Files:**
- Data: `data/alpaca_data_loader.py`
- Indicators: `indicators/intraday_indicators.py`
- Filters: `indicators/confluence_filters.py`
- Strategy: `strategies/temiz_small_cap_short_strategy.py`
- Backtest: `examples/backtest_temiz_strategy.py`

**External Resources:**
- Tomas Temiz Course: "Small Cap Rockets"
- Book: "How to Make Money Selling Stocks Short" (William O'Neil)
- Alpaca Docs: https://alpaca.markets/docs/

---

**Print this page and keep it on your desk during trading hours! 📋**
