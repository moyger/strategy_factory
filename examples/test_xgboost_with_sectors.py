#!/usr/bin/env python3
"""
Test XGBoost ML Qualifier with Sector Features

Tests XGBoost with 9 sector ETF momentum features added:
- XLK (Technology)
- XLF (Financials)
- XLE (Energy)
- XLV (Healthcare)
- XLP (Consumer Staples)
- XLY (Consumer Discretionary)
- XLI (Industrials)
- XLB (Materials)
- XLU (Utilities)

Expected improvement: +10-20% over XGBoost without sectors

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

# Import the correct strategy class (using full module path)
import importlib.util
spec = importlib.util.spec_from_file_location("nick_radge_bss",
    str(Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeEnhanced = module.NickRadgeEnhanced


def download_sector_etfs():
    """Download 9 sector ETF prices"""
    print("📥 Downloading sector ETFs...")

    sectors = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'XLP': 'Consumer Staples',
        'XLY': 'Consumer Discretionary',
        'XLI': 'Industrials',
        'XLB': 'Materials',
        'XLU': 'Utilities'
    }

    sector_data = yf.download(list(sectors.keys()),
                              start='2020-01-01',
                              end='2025-01-31',
                              progress=False,
                              auto_adjust=False)

    if isinstance(sector_data.columns, pd.MultiIndex):
        sector_prices = sector_data['Close']
    else:
        sector_prices = sector_data

    # Ensure Series if single sector
    if isinstance(sector_prices, pd.Series):
        sector_prices = sector_prices.to_frame()

    sector_prices = sector_prices.dropna(how='all').fillna(method='ffill')

    print(f"✅ Downloaded {len(sector_prices.columns)} sector ETFs")
    for ticker, name in sectors.items():
        if ticker in sector_prices.columns:
            print(f"   {ticker}: {name}")

    return sector_prices


def download_stock_data():
    """Download stock universe"""
    print("\n📥 Downloading stock universe...")

    # 50-stock universe from config
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
        'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
        'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
        'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T'
    ]

    # Download with volume
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

    # SPY for regime
    spy = yf.download('SPY', start='2020-01-01', end='2025-01-31', progress=False, auto_adjust=False)
    if isinstance(spy, pd.DataFrame) and 'Close' in spy.columns:
        spy_prices = spy['Close']
    elif isinstance(spy, pd.DataFrame):
        spy_prices = spy.iloc[:, 0]
    else:
        spy_prices = spy

    # Ensure Series
    if isinstance(spy_prices, pd.DataFrame):
        spy_prices = spy_prices.iloc[:, 0]

    # GLD for bear asset
    gld = yf.download('GLD', start='2020-01-01', end='2025-01-31', progress=False, auto_adjust=False)
    if isinstance(gld, pd.DataFrame) and 'Close' in gld.columns:
        gld_prices = gld['Close']
    elif isinstance(gld, pd.DataFrame):
        gld_prices = gld.iloc[:, 0]
    else:
        gld_prices = gld

    # Ensure Series
    if isinstance(gld_prices, pd.DataFrame):
        gld_prices = gld_prices.iloc[:, 0]

    # Combine
    prices['GLD'] = gld_prices
    if volumes is not None:
        volumes['GLD'] = 0

    print(f"✅ Downloaded {len(prices.columns)} stocks")
    print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")

    return prices, spy_prices, volumes


def main():
    print("="*100)
    print("XGBOOST WITH SECTOR FEATURES TEST")
    print("="*100)
    print()
    print("🎯 Goal: Improve XGBoost from 49.64% → 70-80% return")
    print("   Expected sector feature boost: +10-20%")
    print()

    # Download data
    sector_prices = download_sector_etfs()
    prices, spy_prices, volumes = download_stock_data()

    initial_capital = 10000

    # Test 1: XGBoost WITHOUT sector features (baseline)
    print("\n" + "="*100)
    print("1️⃣  XGBOOST WITHOUT SECTOR FEATURES (BASELINE)")
    print("="*100)
    print("   Features: 20 per stock (no volume, no sectors)")
    print()

    strategy_baseline = NickRadgeEnhanced(
        portfolio_size=7,
        qualifier_type='ml_xgb',
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        bear_market_asset='GLD',
        qualifier_params={
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'lookback_years': 3,
            'retrain_freq': 'QS'
        }
    )

    portfolio_baseline = strategy_baseline.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=initial_capital,
        fees=0.001,
        slippage=0.0005
    )

    strategy_baseline.print_results(portfolio_baseline, prices)
    baseline_return = (portfolio_baseline.total_return() - 1) * 100 if callable(portfolio_baseline.total_return) else (portfolio_baseline.total_return - 1) * 100

    # Test 2: XGBoost WITH sector features
    print("\n" + "="*100)
    print("2️⃣  XGBOOST WITH SECTOR FEATURES")
    print("="*100)
    print(f"   Features: {20 + len(sector_prices.columns)} per stock (20 base + {len(sector_prices.columns)} sectors)")
    print("   Sectors: XLK, XLF, XLE, XLV, XLP, XLY, XLI, XLB, XLU")
    print()

    # Create custom XGBoost qualifier that accepts sector_prices
    from strategy_factory.ml_xgboost import XGBoostQualifier

    class XGBoostWithSectors(XGBoostQualifier):
        """XGBoost qualifier that passes sector prices through"""

        def __init__(self, sector_prices=None, **kwargs):
            super().__init__(**kwargs)
            self.sector_prices = sector_prices

        def calculate(self, prices, spy_prices=None, volumes=None, **kwargs):
            # Override to inject sector_prices
            return super().calculate(prices, spy_prices, volumes, self.sector_prices, **kwargs)

    # Create strategy with sector-aware qualifier
    xgb_sectors_qualifier = XGBoostWithSectors(
        sector_prices=sector_prices,
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        lookback_years=3,
        retrain_freq='QS'
    )

    strategy_sectors = NickRadgeEnhanced(
        portfolio_size=7,
        qualifier_type='ml_xgb',  # Will be overridden below
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        bear_market_asset='GLD'
    )

    # Override the qualifier
    strategy_sectors.qualifier = xgb_sectors_qualifier

    portfolio_sectors = strategy_sectors.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=initial_capital,
        fees=0.001,
        slippage=0.0005
    )

    strategy_sectors.print_results(portfolio_sectors, prices)
    sectors_return = (portfolio_sectors.total_return() - 1) * 100 if callable(portfolio_sectors.total_return) else (portfolio_sectors.total_return - 1) * 100

    # Compare results
    print("\n" + "="*100)
    print("COMPARISON: XGBoost WITHOUT vs WITH Sector Features")
    print("="*100)

    print(f"\n{'Strategy':<30} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Improvement':<15}")
    print("-"*100)

    baseline_sharpe = portfolio_baseline.sharpe_ratio(freq='D') if callable(portfolio_baseline.sharpe_ratio) else portfolio_baseline.sharpe_ratio
    baseline_dd = portfolio_baseline.max_drawdown() * 100 if callable(portfolio_baseline.max_drawdown) else portfolio_baseline.max_drawdown * 100

    sectors_sharpe = portfolio_sectors.sharpe_ratio(freq='D') if callable(portfolio_sectors.sharpe_ratio) else portfolio_sectors.sharpe_ratio
    sectors_dd = portfolio_sectors.max_drawdown() * 100 if callable(portfolio_sectors.max_drawdown) else portfolio_sectors.max_drawdown * 100

    improvement = sectors_return - baseline_return

    print(f"{'XGBoost (Baseline)':<30} {baseline_return:>10.2f}% {baseline_sharpe:>9.2f} {baseline_dd:>10.2f}% {'--':<15}")
    print(f"{'XGBoost + Sectors':<30} {sectors_return:>10.2f}% {sectors_sharpe:>9.2f} {sectors_dd:>10.2f}% {improvement:>+13.2f}%")

    print("\n" + "="*100)

    # Feature importance analysis
    if hasattr(strategy_sectors.qualifier, 'feature_importance'):
        print("\n📈 Feature Importance (XGBoost + Sectors):")
        print("-"*100)

        top_features = strategy_sectors.qualifier.feature_importance.head(15)
        for i, (feature, importance) in enumerate(top_features.items(), 1):
            # Highlight sector features
            marker = "🎯" if feature.startswith('vs_XL') else ""
            print(f"   {i:2d}. {feature:<30} {importance:>6.2%} {marker}")

        # Count sector features in top 15
        sector_count = sum(1 for f in top_features.index if f.startswith('vs_XL'))
        print(f"\n   Sector features in top 15: {sector_count}/15 ({sector_count/15*100:.1f}%)")

    print("\n" + "="*100)

    # Final verdict
    print("\n🏁 FINAL VERDICT:")
    print("-"*100)

    if improvement >= 10:
        print(f"✅ Sector features ADD {improvement:.2f}% return! Target met! 🎯")
        print(f"   XGBoost + Sectors: {sectors_return:.2f}%")
    elif improvement >= 5:
        print(f"✅ Sector features ADD {improvement:.2f}% return - good progress!")
        print(f"   Close to +10% target")
    elif improvement > 0:
        print(f"⚠️  Sector features ADD {improvement:.2f}% return - modest improvement")
        print(f"   Expected +10-20%, got +{improvement:.2f}%")
    else:
        print(f"❌ Sector features HURT performance by {abs(improvement):.2f}%")
        print(f"   Need to investigate why")

    print("-"*100)

    print("\n📋 Next Steps:")
    if sectors_return > 100:
        print("   ✅ ML beats 100% return! Ready for hybrid strategy")
        print("   1. Create 70% TQS + 30% XGBoost hybrid")
        print("   2. Walk-forward validation")
    elif improvement >= 10:
        print("   ✅ Sector features working! Next:")
        print("   1. Add volume features (+5-10%)")
        print("   2. Hyperparameter tuning (+5-10%)")
        print("   3. Create hybrid strategy (70% TQS + 30% ML)")
    else:
        print("   1. Debug sector feature implementation")
        print("   2. Try different sector combinations")
        print("   3. Analyze feature importance")


if __name__ == "__main__":
    main()
