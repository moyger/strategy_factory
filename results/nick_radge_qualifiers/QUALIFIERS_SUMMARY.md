# Nick Radge Qualifiers Comparison

**Test Period:** 2020-01-02 to 2024-12-30
**Initial Capital:** $100,000
**SPY Return:** +95.30%

## Performance Ranking

| Rank | Qualifier | Return | Sharpe | Max DD | vs SPY |
|------|-----------|--------|--------|--------|--------|
| 1 | Breakout Strength Score (BSS) | +217.1% | 0.00 | -21.5% | +121.8% |
| 2 | ATR-Normalized Momentum (ANM) | +193.6% | 0.00 | -23.2% | +98.3% |
| 3 | Volatility Expansion Momentum (VEM) | +177.9% | 0.00 | -33.5% | +82.6% |
| 4 | ROC (Original Nick Radge) (ROC) | +166.1% | 0.00 | -30.4% | +70.8% |

## Winner

**Breakout Strength Score** (BSS) is the best performer:
- Total Return: +217.14%
- Sharpe Ratio: 0.00
- Max Drawdown: -21.52%
- Outperformance vs SPY: +121.85%

## Qualifier Descriptions

### ROC (Rate of Change)
- **Original Nick Radge method**
- Formula: (Price - Price[100 days ago]) / Price[100 days ago]
- Measures pure momentum

### BSS (Breakout Strength Score)
- **Tomas Nesnidal inspired**
- Formula: (Price - POI) / (k × ATR)
- Measures breakout conviction (distance from 100-day MA in ATR units)
- BSS > 2.0 = strong breakout

### ANM (ATR-Normalized Momentum)
- Formula: Momentum / ATR%
- Adjusts momentum for volatility
- High ANM = strong move with controlled volatility

### VEM (Volatility Expansion Momentum)
- Formula: ROC × (Current ATR / Avg ATR)
- Combines momentum with volatility expansion
- High VEM = strong momentum + increasing volatility (breakout conditions)

