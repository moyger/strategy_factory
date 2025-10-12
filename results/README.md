# Results Folder Structure

All backtest results, trade logs, and performance analysis organized by strategy.

## 📁 Directory Organization

```
results/
├── nick_radge/        # Nick Radge momentum strategy results (PRODUCTION)
├── crypto/            # Institutional crypto perpetuals strategy
├── temiz/             # Temiz small-cap short strategy (ABANDONED)
├── analysis_reports/  # Generated HTML/PDF reports from QuantStats
└── archive/           # Old test results and comparisons
```

---

## 📊 Nick Radge Strategy Results

**Location:** `results/nick_radge/`

**Key Files:**
- `clean_5year_equity.csv` - Daily equity curve (2015-2024)
- `clean_5year_trades.csv` - All trades with entry/exit/P&L
- `5year_baseline_10_pos_1.5×_lev_100%_paxg_equity.csv` - Baseline configuration
- `5year_conservative_5_pos_1.0×_lev_100%_paxg_equity.csv` - Conservative (lower leverage)
- `5year_optimized_5_pos_1.5×_lev_100%_paxg_equity.csv` - Optimized configuration
- `bear_alternatives_comparison.csv` - Bear regime asset comparison (GLD vs TLT vs SH vs Cash)
- `gld_test_results.csv` - GLD allocation testing
- `qualifier_comparison.csv` - Different entry filter tests
- `qualifier_comparison.png` - Visual performance comparison
- `rebalancing_frequency_comparison.csv` - Daily vs weekly vs monthly rebalancing
- `adaptive_comparison.csv` - Adaptive position sizing tests
- `50_vs_100_comparison.csv` - 50 stock vs 100 stock universe
- `missed_opportunities_51_100.csv` - Analysis of missed trades in larger universe

**Performance (Optimized 5 pos 1.5× config):**
- Total Return: +221.06%
- Annualized: 23.47%
- Sharpe Ratio: 1.19
- Max Drawdown: -32.38%
- Win Rate: 63.0%
- Profit Factor: 4.50

---

## 🪙 Crypto Strategy Results

**Location:** `results/crypto/`

**Key Files:**
- `institutional_perp_equity.csv` - Equity curve for pure trend-following
- `institutional_perp_trades.csv` - Trade log for pure strategy
- `institutional_perp_hybrid_equity.csv` - Hybrid strategy (trend + mean reversion)
- `institutional_perp_hybrid_trades.csv` - Trade log for hybrid
- `crypto_strategy_comparison.csv` - Pure vs hybrid comparison
- `crypto_selection_history.csv` - Asset selection over time (BTC/ETH/SOL)
- `crypto_hybrid_regime_comparison.csv` - Regime filter performance
- `paxg_allocation_comparison.csv` - PAXG (tokenized gold) allocation tests

**Performance (Pure Trend-Following):**
- Total Return: +580.77%
- Annualized: 51.24%
- Sharpe Ratio: 1.40
- Max Drawdown: -26.77%
- Win Rate: 57.8%
- Profit Factor: 3.85

**Note:** Crypto strategies use perpetual futures (20× leverage) for capital efficiency.

---

## ⚠️ Temiz Strategy Results (ABANDONED)

**Location:** `results/temiz/`

**Key Files:**
- `temiz_full_backtest.txt` - Daily data backtest (FALSE POSITIVE: +17%)
- `temiz_1min_backtest_results.txt` - 1-minute data backtest (REAL: -1.08%)
- `temiz_2024_test.txt` - Comprehensive 2024 test (55 days, -0.57%)
- `temiz_filtered_backtest.txt` - With confluence filters (0% WR - all filtered)
- `temiz_backtest_trades.csv` - Trade log

**Why Abandoned:**
- 2021 test: -1.08% return, 33.3% win rate (9 trades)
- 2024 test: -0.57% return, 35.7% win rate (28 trades on 55 parabolic days)
- Confluence filters: Filtered out ALL signals (too strict)
- Daily data test showed +17% (MISLEADING - don't trust daily backtests for intraday strategies)

**Lesson Learned:** Always use 1-minute data for intraday strategy validation.

---

## 📈 Analysis Reports

**Location:** `results/analysis_reports/`

Contains auto-generated HTML tearsheets and performance analysis from QuantStats:
- Full performance metrics (50+ metrics)
- Drawdown analysis
- Rolling returns
- Monthly/yearly heatmaps
- Distribution plots

**Generate new reports:**
```bash
python generate_reports.py
```

---

## 🗄️ Archive

**Location:** `results/archive/`

Contains old test results:
- Early strategy generation tests (`top_50_strategies.csv`, `filtered_strategies.csv`)
- Walk-forward validation attempts (`walk_forward_results.csv`, `top20_walk_forward.csv`)
- Monte Carlo simulation results (`monte_carlo_results.csv`, `top20_monte_carlo.csv`)
- Comparison tests (`comparison_output.txt`, `monthly_comparison.csv`, `quarterly_comparison.csv`)
- Top20/Top50 rebalancing tests (`top20_rebalanced_trades.csv`, `top50_rebalanced_trades.csv`)

These are kept for reference but superseded by cleaner final results.

---

## 🔄 Naming Conventions

**Equity Files:** `{strategy}_{config}_equity.csv`
- Columns: `date`, `equity`, `returns`
- Daily equity curve for plotting

**Trade Files:** `{strategy}_{config}_trades.csv`
- Columns: `entry_date`, `exit_date`, `ticker`, `side`, `size`, `entry_price`, `exit_price`, `pnl`, `pnl_pct`, `mae`, `mfe`, `holding_period`
- Complete trade log for analysis

**Comparison Files:** `{test_name}_comparison.csv`
- Side-by-side comparison of different configurations
- Columns: `config`, `total_return`, `sharpe`, `max_dd`, `win_rate`, etc.

---

## 📌 Quick Commands

**View Nick Radge equity curve:**
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('results/nick_radge/clean_5year_equity.csv', parse_dates=['date'])
df.set_index('date')['equity'].plot(figsize=(12,6), title='Nick Radge 5-Year Equity')
plt.show()
```

**Analyze trade performance:**
```python
trades = pd.read_csv('results/nick_radge/clean_5year_trades.csv')
print(f"Total trades: {len(trades)}")
print(f"Win rate: {(trades['pnl'] > 0).mean():.1%}")
print(f"Avg winner: ${trades[trades['pnl'] > 0]['pnl'].mean():.2f}")
print(f"Avg loser: ${trades[trades['pnl'] < 0]['pnl'].mean():.2f}")
```

**Compare configurations:**
```python
comparison = pd.read_csv('results/nick_radge/rebalancing_frequency_comparison.csv')
print(comparison[['config', 'total_return', 'sharpe', 'max_dd']])
```

---

## 🚨 Important Notes

1. **File Sizes:** Some equity/trade CSVs are 20-50MB. Use pandas chunking for large files.
2. **Date Formats:** All dates in ISO format (YYYY-MM-DD) for consistency.
3. **Currency:** All P&L in USD unless specified otherwise.
4. **Leverage:** Nick Radge = 1.5×, Crypto = 20× (perpetual futures).
5. **Slippage:** Already included in trade results (0.5-2% realistic).

---

**Last updated:** October 2025
