#!/usr/bin/env python3
"""
Backtest Comparison: ML RandomForest vs TQS Qualifier

Tests the new ML-based stock selection against the proven TQS qualifier.

Performance Comparison:
- ML RandomForest Qualifier (ml_rf)
- TQS Qualifier (baseline)

Expected improvements:
- ML may discover non-linear patterns TQS misses
- Adaptive to changing market conditions
- Combines multiple signals automatically

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
import importlib.util

# Import strategy (using importlib for numbered file)
spec = importlib.util.spec_from_file_location(
    "nick_radge_enhanced",
    Path(__file__).parent.parent / "strategies" / "02_nick_radge_bss.py"
)
enhanced_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enhanced_module)
NickRadgeEnhanced = enhanced_module.NickRadgeEnhanced

# Import helper functions
from strategies.nick_radge_bss_strategy import download_sp500_stocks, download_spy


def main():
    print("=" * 80)
    print("BACKTEST COMPARISON: ML RANDOMFOREST vs TQS")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # =================================================================
    # DOWNLOAD DATA
    # =================================================================
    print("📊 STEP 1: Downloading data...")
    print()

    # Download top 50 S&P 500 stocks (2020-2025)
    tickers = [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA', 'AVGO', 'ADBE', 'CRM',
        'ORCL', 'CSCO', 'AMD', 'INTC', 'QCOM', 'TXN', 'INTU', 'NOW',
        'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'AXP',
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT',
        'AMZN', 'HD', 'NKE', 'MCD', 'SBUX', 'LOW',
        'XOM', 'CVX', 'COP', 'CAT', 'UNP',
        'SPY', 'GLD'  # Benchmark + bear asset
    ]

    print(f"   Downloading {len(tickers)} tickers...")

    data = yf.download(tickers, start='2020-01-01', end='2025-01-31', progress=False, auto_adjust=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
        volumes = data['Volume']
    else:
        prices = data
        volumes = None

    print(f"   ✅ Downloaded {len(prices)} bars ({prices.index[0].date()} to {prices.index[-1].date()})")
    if volumes is not None:
        print(f"   ✅ Volume data available for {len(volumes.columns)} tickers")
    print()

    # =================================================================
    # STRATEGY PARAMETERS
    # =================================================================
    common_params = {
        'portfolio_size': 7,
        'ma_period': 100,
        'rebalance_freq': 'QS',  # Quarterly
        'use_momentum_weighting': True,
        'use_regime_filter': True,
        'use_relative_strength': True,
        'regime_ma_long': 200,
        'regime_ma_short': 50,
        'strong_bull_positions': 7,
        'weak_bull_positions': 3,
        'bear_positions': 0,
        'bear_market_asset': 'GLD',
        'bear_allocation': 1.0
    }

    # =================================================================
    # STRATEGY 1: TQS (BASELINE)
    # =================================================================
    print("=" * 80)
    print("STRATEGY 1: TQS (Trend Quality Score) - BASELINE")
    print("=" * 80)
    print()

    strategy_tqs = NickRadgeEnhanced(
        qualifier_type='tqs',
        **common_params
    )

    print("🔄 Running TQS backtest...")
    portfolio_tqs = strategy_tqs.backtest(
        prices=prices,
        initial_capital=100000,
        fees=0.001,  # 0.1%
        slippage=0.0005  # 0.05%
    )

    print("\n📊 TQS RESULTS:")
    print("-" * 80)
    strategy_tqs.print_results(portfolio_tqs, prices)

    # =================================================================
    # STRATEGY 2: ML RANDOMFOREST
    # =================================================================
    print("\n" + "=" * 80)
    print("STRATEGY 2: ML RANDOMFOREST")
    print("=" * 80)
    print()

    strategy_ml = NickRadgeEnhanced(
        qualifier_type='ml_rf',
        qualifier_params={
            'lookback_years': 3,
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 50,
            'retrain_freq': 'QS'  # Retrain quarterly
        },
        **common_params
    )

    print("🔄 Running ML RandomForest backtest...")
    print("   Note: This will take longer due to model training...")
    print()

    portfolio_ml = strategy_ml.backtest(
        prices=prices,
        initial_capital=100000,
        fees=0.001,
        slippage=0.0005
    )

    print("\n📊 ML RANDOMFOREST RESULTS:")
    print("-" * 80)
    strategy_ml.print_results(portfolio_ml, prices)

    # =================================================================
    # COMPARISON
    # =================================================================
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    print()

    # Get metrics
    tqs_return = portfolio_tqs.total_return() * 100
    ml_return = portfolio_ml.total_return() * 100

    try:
        tqs_sharpe = portfolio_tqs.sharpe_ratio(freq='D')
    except:
        tqs_sharpe = 0.0

    try:
        ml_sharpe = portfolio_ml.sharpe_ratio(freq='D')
    except:
        ml_sharpe = 0.0

    tqs_dd = portfolio_tqs.max_drawdown() * 100
    ml_dd = portfolio_ml.max_drawdown() * 100

    # Calculate SPY benchmark
    spy_prices = prices['SPY']
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Comparison table
    print("📊 KEY METRICS:")
    print("-" * 80)
    print(f"{'Metric':<25} {'TQS':<15} {'ML RF':<15} {'Winner':<15}")
    print("-" * 80)

    def compare_metric(name, tqs_val, ml_val, higher_is_better=True):
        tqs_str = f"{tqs_val:,.2f}%"
        ml_str = f"{ml_val:,.2f}%"

        if higher_is_better:
            winner = "ML RF" if ml_val > tqs_val else "TQS"
            diff = ml_val - tqs_val
        else:  # Lower is better (drawdown)
            winner = "ML RF" if ml_val > tqs_val else "TQS"  # More negative = worse
            diff = tqs_val - ml_val  # Flip sign for better comparison

        diff_str = f"({diff:+.2f}%)"

        print(f"{name:<25} {tqs_str:<15} {ml_str:<15} {winner:<15} {diff_str}")

    compare_metric("Total Return", tqs_return, ml_return, higher_is_better=True)
    compare_metric("Sharpe Ratio", tqs_sharpe, ml_sharpe, higher_is_better=True)
    compare_metric("Max Drawdown", tqs_dd, ml_dd, higher_is_better=False)

    print("-" * 80)
    print(f"SPY Benchmark Return: {spy_return:,.2f}%")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    if ml_return > tqs_return and ml_sharpe > tqs_sharpe:
        print("🏆 WINNER: ML RANDOMFOREST")
        print(f"   Better return: {ml_return - tqs_return:+.2f}%")
        print(f"   Better Sharpe: {ml_sharpe - tqs_sharpe:+.2f}")
        print()
        print("✅ ML successfully learned patterns that TQS missed!")
    elif ml_return > tqs_return:
        print("🏆 PARTIAL WIN: ML RANDOMFOREST")
        print(f"   Better return: {ml_return - tqs_return:+.2f}%")
        print(f"   But lower Sharpe: {ml_sharpe - tqs_sharpe:+.2f}")
        print()
        print("⚠️  ML has higher returns but worse risk-adjusted performance")
    else:
        print("🏆 WINNER: TQS (BASELINE)")
        print(f"   Better return: {tqs_return - ml_return:+.2f}%")
        print(f"   Better Sharpe: {tqs_sharpe - ml_sharpe:+.2f}")
        print()
        print("📝 ML needs further tuning. Consider:")
        print("   - More features (volume, sector, fundamentals)")
        print("   - Different hyperparameters (deeper trees, more estimators)")
        print("   - Ensemble methods (XGBoost, LightGBM)")

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Review ML feature importance (which indicators matter most)")
    print("2. Test different hyperparameters (n_estimators, max_depth)")
    print("3. Add more features (volume, sector rotation, fundamentals)")
    print("4. Try ensemble methods (XGBoost, LightGBM)")
    print("5. Implement ML regime predictor (predict bear markets early)")
    print()

    # Feature importance (if available)
    from strategy_factory.performance_qualifiers import get_qualifier

    ml_qualifier = get_qualifier('ml_rf')

    # Note: Feature importance only available after running ML strategy
    # Would need to access it from strategy_ml.qualifier
    print("💡 TIP: Access feature importance with:")
    print("   ml_qualifier.get_feature_importance()")
    print()


if __name__ == "__main__":
    main()
