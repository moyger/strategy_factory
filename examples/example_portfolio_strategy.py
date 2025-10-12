#!/usr/bin/env python3
"""
Example: Portfolio Strategy with Asset Universe Scanning

This demonstrates how to:
1. Scan a universe of assets
2. Rank them by momentum/volatility/other factors
3. Dynamically allocate capital
4. Rebalance periodically
5. Compare different allocation strategies

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from strategies.multi_asset_portfolio_strategy import MultiAssetPortfolioStrategy, load_multiple_assets


def main():
    print("="*80)
    print("EXAMPLE: MULTI-ASSET PORTFOLIO WITH DYNAMIC ALLOCATION")
    print("="*80)

    # ========================================
    # STEP 1: LOAD ASSET UNIVERSE
    # ========================================
    print("\n📂 Step 1: Loading asset universe...")

    # Define your asset universe
    # In production, this could be:
    # - S&P 500 stocks
    # - Crypto universe (BTC, ETH, ADA, SOL, etc.)
    # - Forex pairs (EURUSD, GBPUSD, USDJPY, etc.)
    # - Commodities (Gold, Oil, Silver, etc.)

    asset_files = [
        'data/crypto/BTCUSD_5m.csv',
        'data/crypto/ADAUSD_5m.csv',
        # Add more assets to expand universe
    ]

    prices = load_multiple_assets(asset_files)

    # Use recent data (last 50k bars)
    prices = prices.tail(50000)

    print(f"✅ Loaded {len(prices.columns)} assets")
    print(f"   Assets: {', '.join(prices.columns)}")
    print(f"   Period: {prices.index[0]} to {prices.index[-1]}")
    print(f"   Total bars: {len(prices):,}")

    # ========================================
    # STEP 2: TEST DIFFERENT STRATEGIES
    # ========================================
    print("\n" + "="*80)
    print("STEP 2: COMPARING ALLOCATION STRATEGIES")
    print("="*80)

    strategies_config = [
        {
            'name': 'Equal Weight',
            'allocation_method': 'equal_weight',
            'rebalance_freq': 'W',
            'top_n': 2,
            'lookback_period': 500,
            'min_momentum': 0.0
        },
        {
            'name': 'Momentum',
            'allocation_method': 'momentum',
            'rebalance_freq': 'W',
            'top_n': 2,
            'lookback_period': 500,
            'min_momentum': 0.01  # Only trade assets with >1% momentum
        },
        {
            'name': 'Risk Parity',
            'allocation_method': 'risk_parity',
            'rebalance_freq': 'W',
            'top_n': 2,
            'lookback_period': 500,
            'min_momentum': 0.0
        },
    ]

    results_summary = {}

    for config in strategies_config:
        print(f"\n{'='*80}")
        print(f"TESTING: {config['name'].upper()}")
        print(f"{'='*80}")

        # Create strategy
        strategy = MultiAssetPortfolioStrategy(
            allocation_method=config['allocation_method'],
            rebalance_freq=config['rebalance_freq'],
            top_n=config['top_n'],
            lookback_period=config['lookback_period'],
            min_momentum=config['min_momentum']
        )

        # Run backtest
        portfolio = strategy.backtest(prices, initial_capital=10000)

        # Store results (handle Series for multi-asset portfolios)
        total_return = portfolio.total_return()
        if isinstance(total_return, pd.Series):
            final_value = portfolio.value().iloc[-1].sum()
            init_cash = portfolio.init_cash.sum()
            total_return = ((final_value / init_cash) - 1) * 100
        else:
            total_return = total_return * 100

        sharpe = portfolio.sharpe_ratio(freq='5min')
        if isinstance(sharpe, pd.Series):
            sharpe = sharpe.mean()

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max() * 100
        else:
            max_dd = max_dd * 100

        trades = portfolio.trades.count()
        if isinstance(trades, pd.Series):
            trades = trades.sum()

        results_summary[config['name']] = {
            'return': total_return,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': trades
        }

        # Print results
        strategy.print_results(portfolio, prices)

    # ========================================
    # STEP 3: COMPARE RESULTS
    # ========================================
    print("\n" + "="*80)
    print("STEP 3: STRATEGY COMPARISON")
    print("="*80)

    print(f"\n{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades':<10}")
    print("-" * 80)

    for name, metrics in results_summary.items():
        print(f"{name:<20} {metrics['return']:>10.2f}%  {metrics['sharpe']:>8.2f}  "
              f"{metrics['max_dd']:>10.2f}%  {metrics['trades']:>8}")

    # ========================================
    # STEP 4: ADVANCED CONFIGURATIONS
    # ========================================
    print("\n" + "="*80)
    print("STEP 4: ADVANCED CONFIGURATION EXAMPLE")
    print("="*80)

    print("""
ADVANCED FEATURES YOU CAN ADD:

1. SECTOR ROTATION:
   - Group assets by sector
   - Rotate to strongest sector
   - Limit exposure per sector

2. RISK MANAGEMENT:
   - Maximum position size limits
   - Portfolio-level stop loss
   - Correlation filtering (avoid correlated assets)
   - Volatility targeting

3. SIGNAL COMBINATION:
   - Momentum + Mean reversion
   - Trend + Volatility filters
   - Technical + Fundamental factors

4. DYNAMIC REBALANCING:
   - Rebalance on volatility spikes
   - Rebalance on correlation changes
   - Event-driven rebalancing

5. POSITION SIZING:
   - Kelly criterion per asset
   - Risk parity across portfolio
   - Equal risk contribution
   - Minimum variance optimization

EXAMPLE CODE:
    """)

    print("""
# Advanced strategy with filters
strategy = MultiAssetPortfolioStrategy(
    allocation_method='momentum',
    rebalance_freq='W',
    top_n=5,                    # Hold top 5 assets
    lookback_period=1000,       # Longer lookback
    min_momentum=0.05,          # Only >5% momentum
    max_assets=10               # Never hold >10 assets
)

# Add custom filters in your own subclass:
class AdvancedPortfolioStrategy(MultiAssetPortfolioStrategy):
    def generate_allocations(self, prices):
        # 1. Calculate base allocations
        allocations = super().generate_allocations(prices)

        # 2. Apply correlation filter
        # Don't hold highly correlated assets

        # 3. Apply sector limits
        # Max 30% per sector

        # 4. Apply volatility targeting
        # Scale positions by inverse volatility

        return allocations
    """)

    # ========================================
    # EXAMPLES OF DIFFERENT USE CASES
    # ========================================
    print("\n" + "="*80)
    print("REAL-WORLD USE CASES")
    print("="*80)

    print("""
USE CASE 1: CRYPTO MOMENTUM PORTFOLIO
- Scan top 20 cryptocurrencies
- Hold top 5 by momentum
- Rebalance weekly
- Equal weight allocation

USE CASE 2: STOCK SECTOR ROTATION
- Scan S&P 500 stocks
- Rank by momentum within each sector
- Hold top 2 stocks per sector
- Rebalance monthly
- Risk parity weighting

USE CASE 3: FOREX CARRY TRADE
- Scan major currency pairs
- Rank by interest rate differential
- Hold top 3 carry trades
- Rebalance daily
- Volatility-weighted positions

USE CASE 4: MULTI-STRATEGY PORTFOLIO
- Run multiple strategies on same universe
- Allocate capital to best-performing strategy
- Meta-strategy: strategy of strategies
- Adaptive allocation based on recent performance

USE CASE 5: LONG-SHORT EQUITY
- Rank stocks by momentum/value/quality
- Long top 20%, short bottom 20%
- Market-neutral portfolio
- Daily rebalancing
    """)

    print("\n✅ Example completed!")
    print("\nNext steps:")
    print("   1. Add more assets to your universe")
    print("   2. Test different rebalancing frequencies")
    print("   3. Experiment with momentum lookback periods")
    print("   4. Add custom filters (volatility, correlation, etc.)")
    print("   5. Implement your own allocation logic")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
