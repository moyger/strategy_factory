#!/usr/bin/env python3
"""
Test Hybrid Strategy: 70% TQS + 30% XGBoost

Tests the ultimate combination:
- TQS: Hand-crafted ATR formula (+108.72%)
- XGBoost + Sectors: ML with sector features (+58.79%)
- Hybrid: Weighted combination (target: +115-125%)

Expected improvement: +5-15% over TQS alone

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

# Import the correct strategy class
import importlib.util
spec = importlib.util.spec_from_file_location("nick_radge_bss",
    str(Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeEnhanced = module.NickRadgeEnhanced


def download_all_data():
    """Download stocks, SPY, GLD, and sector ETFs"""
    print("📥 Downloading all data...")

    # 50-stock universe
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
        'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
        'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
        'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T'
    ]

    # Download stocks
    data = yf.download(tickers, start='2020-01-01', end='2025-01-31',
                       progress=False, auto_adjust=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
        volumes = data['Volume']
    else:
        prices = data
        volumes = None

    prices = prices.dropna(how='all').fillna(method='ffill').dropna(axis=1)
    if volumes is not None:
        volumes = volumes[prices.columns].fillna(0)

    # SPY
    spy = yf.download('SPY', start='2020-01-01', end='2025-01-31', progress=False, auto_adjust=False)
    spy_prices = spy['Close'] if isinstance(spy, pd.DataFrame) else spy
    if isinstance(spy_prices, pd.DataFrame):
        spy_prices = spy_prices.iloc[:, 0]

    # GLD
    gld = yf.download('GLD', start='2020-01-01', end='2025-01-31', progress=False, auto_adjust=False)
    gld_prices = gld['Close'] if isinstance(gld, pd.DataFrame) else gld
    if isinstance(gld_prices, pd.DataFrame):
        gld_prices = gld_prices.iloc[:, 0]

    prices['GLD'] = gld_prices
    if volumes is not None:
        volumes['GLD'] = 0

    # Sector ETFs
    sectors = ['XLK', 'XLF', 'XLE', 'XLV', 'XLP', 'XLY', 'XLI', 'XLB', 'XLU']
    sector_data = yf.download(sectors, start='2020-01-01', end='2025-01-31',
                              progress=False, auto_adjust=False)

    if isinstance(sector_data.columns, pd.MultiIndex):
        sector_prices = sector_data['Close']
    else:
        sector_prices = sector_data

    if isinstance(sector_prices, pd.Series):
        sector_prices = sector_prices.to_frame()

    sector_prices = sector_prices.dropna(how='all').fillna(method='ffill')

    print(f"✅ Downloaded {len(prices.columns)} stocks")
    print(f"✅ Downloaded {len(sector_prices.columns)} sector ETFs")
    print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")

    return prices, spy_prices, volumes, sector_prices


def main():
    print("="*100)
    print("HYBRID STRATEGY TEST - TQS + XGBoost ML")
    print("="*100)
    print()
    print("🎯 Goal: Beat TQS baseline with hybrid approach")
    print("   TQS alone: +108.72%")
    print("   XGBoost + Sectors: +58.79%")
    print("   Hybrid target: +115-125% (+5-15% improvement)")
    print()

    # Download data
    prices, spy_prices, volumes, sector_prices = download_all_data()
    initial_capital = 10000

    # Test 1: TQS Baseline
    print("\n" + "="*100)
    print("1️⃣  TQS BASELINE (Hand-Crafted ATR Formula)")
    print("="*100)
    print()

    strategy_tqs = NickRadgeEnhanced(
        portfolio_size=7,
        qualifier_type='tqs',
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        bear_market_asset='GLD',
        qualifier_params={'ma_period': 100, 'atr_period': 14, 'adx_period': 25}
    )

    portfolio_tqs = strategy_tqs.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=initial_capital,
        fees=0.001,
        slippage=0.0005
    )

    strategy_tqs.print_results(portfolio_tqs, prices)
    tqs_return = (portfolio_tqs.total_return() - 1) * 100 if callable(portfolio_tqs.total_return) else (portfolio_tqs.total_return - 1) * 100

    # Test 2: Hybrid Strategy (70% TQS + 30% XGBoost)
    print("\n" + "="*100)
    print("2️⃣  HYBRID STRATEGY (70% TQS + 30% XGBoost)")
    print("="*100)
    print()

    # Create hybrid qualifier
    from strategy_factory.hybrid_qualifier import HybridQualifier

    hybrid_qualifier = HybridQualifier(
        tqs_weight=0.7,
        xgb_weight=0.3,
        tqs_params={'ma_period': 100, 'atr_period': 14, 'adx_period': 25},
        xgb_params={
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'lookback_years': 3,
            'retrain_freq': 'QS'
        },
        sector_prices=sector_prices
    )

    strategy_hybrid = NickRadgeEnhanced(
        portfolio_size=7,
        qualifier_type='tqs',  # Will be overridden
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        bear_market_asset='GLD'
    )

    # Override qualifier with hybrid
    strategy_hybrid.qualifier = hybrid_qualifier
    strategy_hybrid.name = "NickRadge_Hybrid_TQS70_XGB30"

    portfolio_hybrid = strategy_hybrid.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=initial_capital,
        fees=0.001,
        slippage=0.0005
    )

    strategy_hybrid.print_results(portfolio_hybrid, prices)
    hybrid_return = (portfolio_hybrid.total_return() - 1) * 100 if callable(portfolio_hybrid.total_return) else (portfolio_hybrid.total_return - 1) * 100

    # Test 3: Alternative weights (80/20, 60/40)
    print("\n" + "="*100)
    print("3️⃣  TESTING ALTERNATIVE WEIGHT COMBINATIONS")
    print("="*100)

    weights_to_test = [
        (0.8, 0.2, "80% TQS + 20% XGBoost"),
        (0.6, 0.4, "60% TQS + 40% XGBoost"),
    ]

    results = {
        'TQS (100%)': (tqs_return, portfolio_tqs),
        'Hybrid (70/30)': (hybrid_return, portfolio_hybrid)
    }

    for tqs_w, xgb_w, name in weights_to_test:
        print(f"\n   Testing {name}...")

        hybrid_alt = HybridQualifier(
            tqs_weight=tqs_w,
            xgb_weight=xgb_w,
            tqs_params={'ma_period': 100, 'atr_period': 14, 'adx_period': 25},
            xgb_params={
                'n_estimators': 300,
                'max_depth': 8,
                'learning_rate': 0.05,
                'lookback_years': 3,
                'retrain_freq': 'QS'
            },
            sector_prices=sector_prices
        )

        strategy_alt = NickRadgeEnhanced(
            portfolio_size=7,
            qualifier_type='tqs',
            ma_period=100,
            rebalance_freq='QS',
            use_momentum_weighting=True,
            use_regime_filter=True,
            use_relative_strength=True,
            bear_market_asset='GLD'
        )

        strategy_alt.qualifier = hybrid_alt
        portfolio_alt = strategy_alt.backtest(prices=prices, spy_prices=spy_prices,
                                              initial_capital=initial_capital, fees=0.001, slippage=0.0005)

        alt_return = (portfolio_alt.total_return() - 1) * 100 if callable(portfolio_alt.total_return) else (portfolio_alt.total_return - 1) * 100
        results[name] = (alt_return, portfolio_alt)

        print(f"   ✅ {name}: {alt_return:.2f}% return")

    # Compare all results
    print("\n" + "="*100)
    print("COMPREHENSIVE COMPARISON - ALL STRATEGIES")
    print("="*100)

    print(f"\n{'Strategy':<30} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'vs TQS':<12}")
    print("-"*100)

    for name, (ret, portfolio) in sorted(results.items(), key=lambda x: x[1][0], reverse=True):
        sharpe = portfolio.sharpe_ratio(freq='D') if callable(portfolio.sharpe_ratio) else portfolio.sharpe_ratio
        max_dd = portfolio.max_drawdown() * 100 if callable(portfolio.max_drawdown) else portfolio.max_drawdown * 100
        vs_tqs = ret - tqs_return

        emoji = "🏆" if ret == max(r[0] for r in results.values()) else ""
        print(f"{name:<30} {ret:>10.2f}% {sharpe:>9.2f} {max_dd:>10.2f}% {vs_tqs:>+10.2f}% {emoji}")

    print("="*100)

    # Find best hybrid
    best_hybrid_name = max(
        [k for k in results.keys() if 'Hybrid' in k or '/' in k],
        key=lambda k: results[k][0]
    )
    best_hybrid_return = results[best_hybrid_name][0]

    # Final verdict
    print("\n🏁 FINAL VERDICT:")
    print("-"*100)

    if best_hybrid_return > tqs_return:
        improvement = best_hybrid_return - tqs_return
        print(f"✅ HYBRID BEATS TQS by {improvement:.2f}%!")
        print(f"   Winner: {best_hybrid_name}")
        print(f"   {best_hybrid_name}: {best_hybrid_return:.2f}%")
        print(f"   TQS Baseline: {tqs_return:.2f}%")
        print(f"   🏆 New champion strategy!")
    else:
        gap = tqs_return - best_hybrid_return
        print(f"⚠️  TQS still leads by {gap:.2f}%")
        print(f"   TQS: {tqs_return:.2f}%")
        print(f"   Best Hybrid ({best_hybrid_name}): {best_hybrid_return:.2f}%")
        print(f"   Hybrid adds complexity without beating simple TQS")

    print("-"*100)

    print("\n📋 Recommended Strategy:")
    if best_hybrid_return > tqs_return:
        print(f"   ✅ Deploy {best_hybrid_name} (beats TQS)")
        print("   Next: Walk-forward validation, out-of-sample testing, paper trading")
    else:
        print("   ✅ Stick with TQS (simpler is better)")
        print("   ML didn't improve over hand-crafted formula")
        print("   Consider: More ML data, different features, or ensemble methods")


if __name__ == "__main__":
    main()
