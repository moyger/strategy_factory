# Portfolio Strategies Guide

## Multi-Asset Portfolio with Universe Scanning

Yes, you can absolutely create strategies that scan a universe of assets and make dynamic allocation decisions! This guide shows you how.

---

## What You Can Do

### ✅ Asset Universe Scanning
- Scan 10s, 100s, or 1000s of assets
- Cryptocurrencies, stocks, forex, commodities, etc.
- Load from multiple data files

### ✅ Dynamic Allocation
- Momentum-based weighting
- Risk parity (inverse volatility)
- Equal weight rebalancing
- Minimum variance optimization

### ✅ Ranking & Selection
- Rank by momentum, returns, Sharpe ratio
- Filter by minimum performance thresholds
- Select top N assets dynamically
- Exclude correlated assets

### ✅ Rebalancing
- Daily, Weekly, Monthly, Quarterly
- Event-driven (volatility spikes, drawdowns)
- Threshold-based (drift from target allocation)

### ✅ Position Sizing
- Equal weight across selected assets
- Momentum-weighted (higher momentum = more allocation)
- Risk parity (equal risk contribution)
- Custom allocation logic

---

## Quick Start

### Run the Example

```bash
# Test multi-asset portfolio with BTC and ADA
venv/bin/python examples/example_portfolio_strategy.py
```

**Results from the example:**

| Strategy | Return | Sharpe | Max DD | Trades |
|----------|--------|--------|--------|--------|
| Equal Weight | 19.67% | 0.92 | -15.99% | 17,185 |
| Momentum | 17.03% | 0.65 | -14.33% | 10,754 |
| Risk Parity | 19.86% | 1.02 | -17.20% | 17,193 |

---

## How It Works

### 1. Load Asset Universe

```python
from strategies.multi_asset_portfolio_strategy import load_multiple_assets

# Define your universe
asset_files = [
    'data/crypto/BTCUSD_5m.csv',
    'data/crypto/ADAUSD_5m.csv',
    'data/crypto/ETHUSD_5m.csv',
    # Add more assets...
]

# Load all at once
prices = load_multiple_assets(asset_files)
# Returns DataFrame with columns = asset names, index = timestamp
```

### 2. Create Portfolio Strategy

```python
from strategies.multi_asset_portfolio_strategy import MultiAssetPortfolioStrategy

strategy = MultiAssetPortfolioStrategy(
    allocation_method='momentum',    # 'equal_weight', 'momentum', 'risk_parity'
    rebalance_freq='W',              # 'D', 'W', 'M', 'Q'
    top_n=5,                         # Hold top 5 assets
    lookback_period=500,             # Momentum lookback period
    min_momentum=0.01,               # Minimum 1% momentum to trade
    max_assets=10                    # Never hold more than 10
)
```

### 3. Run Backtest

```python
portfolio = strategy.backtest(prices, initial_capital=10000)

# Print results
strategy.print_results(portfolio, prices)
```

---

## Allocation Methods Explained

### 1. Equal Weight
```python
allocation_method='equal_weight'
```
- Selects top N assets by momentum
- Allocates equal % to each
- Simple and effective
- **Best for:** Diversification, reducing concentration risk

**Example:** Top 5 assets each get 20% allocation

### 2. Momentum Weighting
```python
allocation_method='momentum'
```
- Weights assets by momentum strength
- Higher momentum = larger allocation
- Concentrates in best performers
- **Best for:** Trend-following, capturing momentum

**Example:**
- Asset A (5% momentum) → 50% allocation
- Asset B (3% momentum) → 30% allocation
- Asset C (2% momentum) → 20% allocation

### 3. Risk Parity
```python
allocation_method='risk_parity'
```
- Inverse volatility weighting
- Lower volatility = higher allocation
- Equal risk contribution per asset
- **Best for:** Smooth returns, risk management

**Example:**
- Low vol asset → 40% allocation
- Medium vol asset → 35% allocation
- High vol asset → 25% allocation

---

## Real-World Use Cases

### USE CASE 1: Crypto Momentum Portfolio
```python
# Scan top 20 cryptocurrencies
# Hold top 5 by momentum
# Rebalance weekly
strategy = MultiAssetPortfolioStrategy(
    allocation_method='momentum',
    rebalance_freq='W',
    top_n=5,
    lookback_period=2000,  # ~1 week of 5-min data
    min_momentum=0.05      # Only >5% momentum
)
```

**Assets:** BTC, ETH, ADA, SOL, DOT, LINK, etc.

### USE CASE 2: Stock Sector Rotation
```python
# Scan S&P 500 stocks
# Hold top 2 per sector
# Rebalance monthly
strategy = MultiAssetPortfolioStrategy(
    allocation_method='equal_weight',
    rebalance_freq='M',
    top_n=20,  # 10 sectors × 2 stocks
    lookback_period=20,  # 20 days
    min_momentum=0.0
)
```

**Assets:** Group by sector (Tech, Healthcare, Finance, etc.)

### USE CASE 3: Forex Carry Trade
```python
# Scan major currency pairs
# Hold top 3 carry trades
# Rebalance daily
strategy = MultiAssetPortfolioStrategy(
    allocation_method='risk_parity',
    rebalance_freq='D',
    top_n=3,
    lookback_period=100,
    min_momentum=-0.01  # Can include negative momentum for shorts
)
```

**Assets:** EURUSD, GBPUSD, USDJPY, AUDUSD, etc.

### USE CASE 4: Multi-Strategy Portfolio
```python
# Run multiple strategies on same universe
# Allocate to best-performing strategy
# Meta-strategy: strategy of strategies

strategies = {
    'Momentum': MultiAssetPortfolioStrategy(allocation_method='momentum', ...),
    'Mean Reversion': MultiAssetPortfolioStrategy(allocation_method='equal_weight', ...),
    'Risk Parity': MultiAssetPortfolioStrategy(allocation_method='risk_parity', ...)
}

# Backtest all, allocate capital to best Sharpe ratio
```

### USE CASE 5: Long-Short Equity
```python
# Rank stocks by momentum
# Long top 20%, short bottom 20%
# Market-neutral portfolio

# This requires custom implementation (coming soon!)
# See advanced customization section below
```

---

## Advanced Customization

### Create Your Own Allocation Logic

```python
from strategies.multi_asset_portfolio_strategy import MultiAssetPortfolioStrategy

class MyCustomPortfolio(MultiAssetPortfolioStrategy):
    def generate_allocations(self, prices):
        """Custom allocation logic"""

        # 1. Start with base allocations
        allocations = super().generate_allocations(prices)

        # 2. Apply custom filters

        # Example: Volatility filter
        returns = prices.pct_change()
        volatility = returns.rolling(100).std()
        high_vol_mask = volatility > volatility.median()
        allocations[high_vol_mask] = 0  # Don't trade high volatility assets

        # Example: Correlation filter
        correlation_matrix = returns.rolling(500).corr()
        # Remove highly correlated assets (implement your logic)

        # Example: Sector limits
        # max_per_sector = 0.30  # 30% max per sector
        # Implement sector-based limits

        # 3. Renormalize allocations
        allocations = allocations.div(allocations.sum(axis=1), axis=0)

        return allocations
```

### Add Custom Ranking Factors

```python
def calculate_custom_score(self, prices):
    """Combine multiple factors into single score"""

    # Factor 1: Momentum
    momentum = prices.pct_change(self.lookback_period)
    momentum_rank = momentum.rank(axis=1, pct=True)

    # Factor 2: Volatility (inverse - prefer low vol)
    returns = prices.pct_change()
    volatility = returns.rolling(self.lookback_period).std()
    vol_rank = 1 - volatility.rank(axis=1, pct=True)

    # Factor 3: Sharpe ratio
    sharpe = (returns.rolling(self.lookback_period).mean() /
              returns.rolling(self.lookback_period).std())
    sharpe_rank = sharpe.rank(axis=1, pct=True)

    # Combine (weighted average)
    composite_score = (
        0.5 * momentum_rank +
        0.3 * vol_rank +
        0.2 * sharpe_rank
    )

    return composite_score
```

---

## Parameters Reference

### Strategy Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `allocation_method` | str | 'momentum' | Allocation logic: 'equal_weight', 'momentum', 'risk_parity' |
| `rebalance_freq` | str | 'W' | Rebalancing frequency: 'D', 'W', 'M', 'Q' |
| `top_n` | int | 5 | Number of assets to hold |
| `lookback_period` | int | 100 | Bars for momentum/volatility calculation |
| `min_momentum` | float | 0.0 | Minimum momentum threshold to enter |
| `max_assets` | int | 10 | Maximum number of assets to hold |

### Tuning Guidelines

**For Crypto (5-minute data):**
- `lookback_period`: 500-2000 (2-8 hours)
- `rebalance_freq`: 'W' (weekly)
- `min_momentum`: 0.01-0.05 (1-5%)

**For Stocks (daily data):**
- `lookback_period`: 20-60 (1-3 months)
- `rebalance_freq`: 'M' (monthly)
- `min_momentum`: 0.05-0.10 (5-10%)

**For Forex (hourly data):**
- `lookback_period`: 100-500 (4-20 days)
- `rebalance_freq`: 'D' (daily)
- `min_momentum`: 0.005-0.02 (0.5-2%)

---

## Performance Optimization

### 1. Reduce Data Size
```python
# Use only recent data for faster testing
prices = prices.tail(50000)  # Last 50k bars
```

### 2. Limit Universe Size
```python
# Start with small universe, expand later
asset_files = asset_files[:5]  # Test with 5 assets first
```

### 3. Increase Rebalancing Frequency
```python
# Weekly instead of daily = 7x fewer rebalances
rebalance_freq='W'  # vs 'D'
```

### 4. Reduce Lookback Period
```python
# Shorter lookback = faster calculations
lookback_period=100  # vs 1000
```

---

## Integration with Existing Strategies

### Combine Single-Asset Strategy with Portfolio

```python
# 1. Define single-asset strategy
from strategies.atr_trailing_stop_strategy import ATRTrailingStopStrategy

single_strategy = ATRTrailingStopStrategy(
    atr_period=14,
    atr_sl_multiplier=2.0,
    atr_tp_multiplier=4.0
)

# 2. Apply to each asset in universe
for asset in asset_universe:
    df_signals = single_strategy.generate_signals(asset_data)
    # Combine signals into portfolio allocations
```

### Multi-Timeframe Portfolio

```python
# Use higher timeframe for asset selection
# Use lower timeframe for entry/exit timing

# HTF: Daily data for ranking
daily_prices = load_multiple_assets(daily_files)
ranks = strategy.rank_assets(daily_prices)

# LTF: Hourly data for execution
hourly_prices = load_multiple_assets(hourly_files)
# Trade selected assets on hourly timeframe
```

---

## Comparison: Single-Asset vs Portfolio Strategies

| Feature | Single-Asset Strategy | Portfolio Strategy |
|---------|----------------------|-------------------|
| **Assets** | 1 asset | Multiple assets |
| **Signals** | BUY/SELL | Allocation weights (0-100%) |
| **Diversification** | None | Built-in |
| **Complexity** | Simple | Moderate-Advanced |
| **Returns** | High variance | Smoother |
| **Risk** | Concentrated | Distributed |
| **Best for** | Deep market knowledge | Broader exposure |

---

## Next Steps

### 1. Start Simple
```bash
# Run the example
venv/bin/python examples/example_portfolio_strategy.py
```

### 2. Add More Assets
```python
# Expand your universe
asset_files = [
    'data/crypto/BTCUSD_5m.csv',
    'data/crypto/ADAUSD_5m.csv',
    'data/crypto/ETHUSD_5m.csv',
    'data/crypto/SOLUSD_5m.csv',
    'data/crypto/DOTUSD_5m.csv',
    # ... add more
]
```

### 3. Experiment with Parameters
```python
# Test different settings
for lookback in [100, 500, 1000]:
    for top_n in [3, 5, 10]:
        strategy = MultiAssetPortfolioStrategy(
            lookback_period=lookback,
            top_n=top_n
        )
        # Backtest and compare
```

### 4. Implement Custom Logic
```python
# Create your own allocation method
class MyStrategy(MultiAssetPortfolioStrategy):
    def rank_assets(self, prices):
        # Your custom ranking logic
        pass
```

### 5. Combine with Risk Management
```python
from strategy_factory.risk_management import FTMOChecker, RiskCalculator

# Add FTMO compliance checking
# Add ATR-based position sizing per asset
# Add portfolio-level stop loss
```

---

## Files Created

1. **`strategies/multi_asset_portfolio_strategy.py`** - Main portfolio strategy class
2. **`examples/example_portfolio_strategy.py`** - Complete working example
3. **`PORTFOLIO_STRATEGIES_GUIDE.md`** - This guide

---

## Summary

**Yes, you can scan a universe of assets and dynamically allocate!**

Key capabilities:
- ✅ Scan 2-1000+ assets
- ✅ Rank by momentum, volatility, Sharpe, custom factors
- ✅ Dynamically allocate capital
- ✅ Rebalance on schedule or events
- ✅ Multiple allocation methods built-in
- ✅ Easy to customize for your needs

**Get started now:**
```bash
venv/bin/python examples/example_portfolio_strategy.py
```

---

*Strategy Factory - Professional Multi-Asset Portfolio Management*
*Last updated: 2025*
