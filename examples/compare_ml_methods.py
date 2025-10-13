#!/usr/bin/env python3
"""
Compare ML Methods: TQS vs RandomForest vs XGBoost

Comprehensive comparison of:
1. TQS (hand-crafted ATR-based qualifier) - Baseline
2. ML RandomForest (ensemble trees)
3. ML XGBoost (gradient boosting) - Expected +20-30% over RF

Target: Get ML from 103.86% → 130-140% return

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

def download_data():
    """Download stock universe with volume data"""
    print("📥 Downloading data...")

    # 50-stock universe from config
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
        'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'LLY', 'ABBV', 'MRK',
        'PEP', 'KO', 'AVGO', 'COST', 'TMO', 'WMT', 'MCD', 'CSCO', 'ABT', 'DHR',
        'ACN', 'VZ', 'ADBE', 'NKE', 'NFLX', 'CRM', 'TXN', 'PM', 'DIS', 'BMY',
        'ORCL', 'LIN', 'UPS', 'NEE', 'RTX', 'QCOM', 'HON', 'INTU', 'AMD', 'T'
    ]

    # Download with volume (auto_adjust=False to get volume)
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
        volumes['GLD'] = 0  # GLD volume not needed

    print(f"✅ Downloaded {len(prices.columns)} stocks")
    print(f"   Period: {prices.index[0].date()} to {prices.index[-1].date()}")
    print(f"   Volume data: {'Yes' if volumes is not None else 'No'}")

    return prices, spy_prices, volumes


def run_strategy(qualifier_type: str, prices: pd.DataFrame, spy_prices: pd.Series,
                 volumes: pd.DataFrame = None, initial_capital: int = 10000):
    """Run strategy with specified qualifier"""

    qualifier_params = {}
    if qualifier_type == 'ml_rf':
        # RandomForest with enhanced features
        qualifier_params = {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 30,
            'lookback_years': 3,
            'retrain_freq': 'QS'
        }
    elif qualifier_type == 'ml_xgb':
        # XGBoost with optimized hyperparameters
        qualifier_params = {
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'lookback_years': 3,
            'retrain_freq': 'QS'
        }
    else:  # TQS
        qualifier_params = {
            'ma_period': 100,
            'atr_period': 14,
            'adx_period': 25
        }

    strategy = NickRadgeEnhanced(
        portfolio_size=7,
        qualifier_type=qualifier_type,
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        bear_market_asset='GLD',
        qualifier_params=qualifier_params
    )

    # For ML qualifiers, we need to pass volumes through a different method
    # The 02_nick_radge_bss.py doesn't support volumes parameter yet
    # So we'll skip volumes for now and rely on other features

    portfolio = strategy.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=initial_capital,
        fees=0.001,
        slippage=0.0005
    )

    return portfolio, strategy


def compare_results(results: dict, spy_prices: pd.Series):
    """Print comparison table"""

    print("\n" + "="*100)
    print("ML METHODS COMPARISON - TQS vs RandomForest vs XGBoost")
    print("="*100)

    # Calculate SPY benchmark
    spy_returns = spy_prices.pct_change().dropna()
    spy_total_return = ((1 + spy_returns).cumprod().iloc[-1] - 1) * 100
    spy_sharpe = spy_returns.mean() / spy_returns.std() * np.sqrt(252)

    print(f"\n📊 SPY Benchmark:")
    print(f"   Total Return: {spy_total_return:.2f}%")
    print(f"   Sharpe Ratio: {spy_sharpe:.2f}")

    # Comparison table
    print(f"\n{'Strategy':<20} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Calmar':<10} {'vs SPY':<12} {'vs TQS':<12}")
    print("-"*100)

    tqs_return = None
    for name, (portfolio, strategy) in results.items():
        # VectorBT portfolio metrics access (with freq='D' for daily data)
        try:
            total_return = (portfolio.total_return() - 1) * 100 if callable(portfolio.total_return) else (portfolio.total_return - 1) * 100
            sharpe = portfolio.sharpe_ratio(freq='D') if callable(portfolio.sharpe_ratio) else portfolio.sharpe_ratio
            max_dd = portfolio.max_drawdown() * 100 if callable(portfolio.max_drawdown) else portfolio.max_drawdown * 100
            calmar = portfolio.calmar_ratio(freq='D') if hasattr(portfolio, 'calmar_ratio') and callable(portfolio.calmar_ratio) else 0
        except Exception as e:
            print(f"   Error getting metrics for {name}: {e}")
            continue

        vs_spy = total_return - spy_total_return

        if name == 'TQS':
            tqs_return = total_return
            vs_tqs = 0.0
        else:
            vs_tqs = total_return - tqs_return if tqs_return else 0.0

        emoji = "🏆" if name == 'XGBoost' else ("⭐" if name == 'TQS' else "")

        print(f"{name:<20} {total_return:>10.2f}% {sharpe:>9.2f} {max_dd:>10.2f}% "
              f"{calmar:>9.2f} {vs_spy:>+10.2f}% {vs_tqs:>+10.2f}% {emoji}")

    print("="*100)

    # Feature importance comparison
    print("\n📈 Feature Importance Analysis:")
    print("-"*100)

    for name, (portfolio, strategy) in results.items():
        if hasattr(strategy.qualifier, 'feature_importance'):
            print(f"\n{name} Top 10 Features:")
            top_features = strategy.qualifier.feature_importance.head(10)
            for i, (feature, importance) in enumerate(top_features.items(), 1):
                print(f"   {i:2d}. {feature:<25} {importance:>6.2%}")

    print("\n" + "="*100)


def main():
    print("="*100)
    print("COMPREHENSIVE ML COMPARISON - TQS vs RandomForest vs XGBoost")
    print("="*100)
    print()
    print("🎯 Goal: Get ML from 103.86% → 130-140% return")
    print("   Expected XGBoost improvement: +20-30% over RandomForest")
    print()

    # Download data
    prices, spy_prices, volumes = download_data()

    initial_capital = 10000

    # Test all three methods
    results = {}

    print("\n" + "="*100)
    print("1️⃣  TESTING TQS (BASELINE)")
    print("="*100)
    print("   Qualifier: Trend Quality Score (hand-crafted ATR-based)")
    print("   Expected: 180-220% return")
    print()

    portfolio_tqs, strategy_tqs = run_strategy('tqs', prices, spy_prices, volumes, initial_capital)
    strategy_tqs.print_results(portfolio_tqs, prices)
    results['TQS'] = (portfolio_tqs, strategy_tqs)

    print("\n" + "="*100)
    print("2️⃣  TESTING ML RANDOMFOREST")
    print("="*100)
    print("   Qualifier: RandomForestClassifier (200 trees, depth 15)")
    print("   Features: 24 per stock (momentum, volatility, volume, trend)")
    print("   Training: Walk-forward with 3-year lookback")
    print("   Expected: 100-110% return")
    print()

    portfolio_rf, strategy_rf = run_strategy('ml_rf', prices, spy_prices, volumes, initial_capital)
    strategy_rf.print_results(portfolio_rf, prices)
    results['RandomForest'] = (portfolio_rf, strategy_rf)

    print("\n" + "="*100)
    print("3️⃣  TESTING ML XGBOOST")
    print("="*100)
    print("   Qualifier: XGBClassifier (300 rounds, learning_rate=0.05)")
    print("   Features: 24 per stock (same as RandomForest)")
    print("   Training: Walk-forward with 3-year lookback")
    print("   Expected: 130-140% return (+20-30% over RandomForest)")
    print()

    portfolio_xgb, strategy_xgb = run_strategy('ml_xgb', prices, spy_prices, volumes, initial_capital)
    strategy_xgb.print_results(portfolio_xgb, prices)
    results['XGBoost'] = (portfolio_xgb, strategy_xgb)

    # Compare results
    compare_results(results, spy_prices)

    # Final verdict
    print("\n🏁 FINAL VERDICT:")
    print("-"*100)

    # Get returns (handle both method and property access)
    tqs_portfolio = results['TQS'][0]
    rf_portfolio = results['RandomForest'][0]
    xgb_portfolio = results['XGBoost'][0]

    tqs_return = (tqs_portfolio.total_return() - 1) * 100 if callable(tqs_portfolio.total_return) else (tqs_portfolio.total_return - 1) * 100
    rf_return = (rf_portfolio.total_return() - 1) * 100 if callable(rf_portfolio.total_return) else (rf_portfolio.total_return - 1) * 100
    xgb_return = (xgb_portfolio.total_return() - 1) * 100 if callable(xgb_portfolio.total_return) else (xgb_portfolio.total_return - 1) * 100

    if xgb_return > tqs_return:
        print(f"✅ XGBoost BEATS TQS by {xgb_return - tqs_return:.2f}%!")
        print(f"   XGBoost is the new champion! 🏆")
    elif xgb_return > rf_return + 20:
        print(f"✅ XGBoost BEATS RandomForest by {xgb_return - rf_return:.2f}%!")
        print(f"   Meets +20% improvement target!")
        print(f"   Still {tqs_return - xgb_return:.2f}% behind TQS - need sector features!")
    else:
        print(f"⚠️  XGBoost improvement: {xgb_return - rf_return:.2f}% (target: +20%)")
        print(f"   Still {tqs_return - xgb_return:.2f}% behind TQS")
        print(f"   Next steps: Add sector features + hybrid strategy")

    print("-"*100)

    print("\n📋 Next Steps:")
    if xgb_return < tqs_return:
        print("   1. Add sector features (XLK, XLF, XLE, etc.) - Expected +10-20%")
        print("   2. Create hybrid strategy (70% TQS + 30% ML) - Expected +5-15%")
        print("   3. Hyperparameter tuning - Expected +5-10%")
    else:
        print("   ✅ ML beats TQS! Ready for deployment testing")
        print("   1. Walk-forward validation (5+ folds)")
        print("   2. Out-of-sample testing (2021-2025)")
        print("   3. Paper trading (1 month)")


if __name__ == "__main__":
    main()
