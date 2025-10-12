# Data Feed Options for Intraday Trading

**Last Updated:** October 10, 2025

This document compares data providers for intraday (1-minute bar) trading strategies like the Temiz day trading system.

---

## Requirements for Temiz Strategy

- ✅ **1-minute OHLCV bars** (to detect blow-off candles, volume spikes)
- ✅ **Real-time quotes** (<1 second latency for entries/exits)
- ✅ **Pre-market data** (4:00-9:30 AM for gap scanning)
- ✅ **Historical data** (at least 1 year for backtesting)
- ✅ **Small-cap coverage** (stocks <$20M float)

---

## Provider Comparison

| Provider | Monthly Cost | Latency | Historical | Pre-Market | Notes |
|----------|--------------|---------|------------|------------|-------|
| **FREE OPTIONS** | | | | | |
| Yahoo Finance | $0 | 15-min delay ❌ | Daily only ❌ | No ❌ | Current source - NOT suitable |
| Alpha Vantage | $0 | 5 req/min limit | 1-min (limited) | No | Too slow for real-time |
| Alpaca (Paper) | **$0** | Real-time ✅ | **5 years 1-min** ✅ | Yes ✅ | **BEST FREE** |
| | | | | | |
| **BROKER DATA** | | | | | |
| IBKR Market Data | **$10-20** | Real-time ✅ | 1-2 years | Yes ✅ | If already using IBKR |
| TD Ameritrade | $0 (if trading) | Real-time ✅ | Limited | Yes | Requires TD account |
| | | | | | |
| **BUDGET PREMIUM** | | | | | |
| Alpaca (Live) | **$9** | Real-time ✅ | 5 years 1-min ✅ | Yes ✅ | Best value |
| Twelve Data Basic | **$29** | 1-sec ✅ | 1 year 1-min | Yes ✅ | 800 calls/day limit |
| Polygon.io Starter | **$29** | 1-sec ✅ | 2 years 1-min | Yes ✅ | Good for backtesting |
| | | | | | |
| **PREMIUM** | | | | | |
| Polygon.io Developer | $99 | Real-time ✅ | 5 years | Yes ✅ | Professional grade |
| IEX Cloud | $79 | Real-time ✅ | 1 year | Yes ✅ | Exchange-direct |
| Polygon.io Advanced | $299 | Real-time ✅ | Unlimited | Yes ✅ | Institutional |

---

## Recommended Setup

### **For Backtesting (Current Focus)**
**Use: Alpaca Free Tier (Paper Account)**
- Cost: **$0**
- Data: 5 years of 1-minute historical bars
- Coverage: All US stocks
- API: Simple REST API + Python SDK

```python
from alpaca_trade_api import REST

api = REST(
    key_id='PAPER_KEY',
    secret_key='PAPER_SECRET',
    base_url='https://paper-api.alpaca.markets'
)

# Get historical 1-min bars (FREE)
bars = api.get_bars('AAPL', '1Min', start='2020-01-01', end='2024-12-31')
```

### **For Paper Trading**
**Use: Alpaca Free Tier**
- Real-time websocket quotes (FREE)
- Pre-market data included
- No rate limits

### **For Live Trading (Future)**
**Option A: IBKR Market Data** ($10-20/month)
- If already trading with IBKR
- Integrated with existing broker

**Option B: Alpaca Live Data** ($9/month)
- Cheapest premium option
- Can execute on any broker

---

## Cost Summary

| Phase | Solution | Monthly Cost |
|-------|----------|--------------|
| **Backtesting** (now) | Alpaca Paper | **$0** |
| **Paper Trading** | Alpaca Paper | **$0** |
| **Live Trading** | IBKR Market Data OR Alpaca Live | **$9-20** |

**Total Development Cost: $0** ✅

---

## Integration Example (Alpaca)

```python
# Install
pip install alpaca-trade-api

# Get 1-minute bars
from alpaca_trade_api import REST

api = REST('KEY', 'SECRET', 'https://paper-api.alpaca.markets')

# Historical bars (for backtesting)
bars = api.get_bars(
    'TSLA',
    '1Min',
    start='2024-01-01',
    end='2024-01-31'
).df

# Real-time streaming (for live trading)
from alpaca_trade_api.stream import Stream

stream = Stream('KEY', 'SECRET', base_url='paper')

@stream.on_bar('TSLA')
def on_bar(bar):
    print(f"Price: {bar.close}, Vol: {bar.volume}")

stream.subscribe_bars(['TSLA'])
stream.run()
```

---

## Decision Point (For Future Live Deployment)

**When ready to deploy live, choose based on:**

1. **Already using IBKR?** → Use IBKR Market Data ($10-20/mo)
2. **Want cheapest option?** → Use Alpaca Live ($9/mo)
3. **Need premium features?** → Use Polygon.io ($29-99/mo)

---

**Status:** Using Alpaca free tier for backtesting phase ✅
**Next Decision:** Live data provider (when deploying to production)
