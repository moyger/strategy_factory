#!/usr/bin/env python3
"""
Hybrid Qualifier - Combines TQS + ML (XGBoost)

Combines the best of both worlds:
- TQS (Trend Quality Score): Hand-crafted ATR-based formula (70% weight)
- XGBoost ML: Machine learning predictions (30% weight)

Expected improvement: +5-15% over single methods

Formula:
    hybrid_score = 0.7 × normalized_tqs + 0.3 × normalized_xgb

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict

from strategy_factory.performance_qualifiers import PerformanceQualifier, TrendQualityScore
from strategy_factory.ml_xgboost import XGBoostQualifier


class HybridQualifier(PerformanceQualifier):
    """
    Hybrid Qualifier combining TQS and XGBoost

    Combines:
    - TQS (70% weight): Proven hand-crafted ATR formula
    - XGBoost (30% weight): ML predictions with sector features

    Benefits:
    - TQS provides strong baseline momentum signal
    - XGBoost adds nuanced pattern recognition
    - Sector features capture macro trends
    - Weighted combination reduces overfitting risk
    """

    def __init__(self,
                 tqs_weight: float = 0.7,
                 xgb_weight: float = 0.3,
                 tqs_params: Optional[Dict] = None,
                 xgb_params: Optional[Dict] = None,
                 sector_prices: Optional[pd.DataFrame] = None):
        """
        Initialize Hybrid Qualifier

        Args:
            tqs_weight: Weight for TQS score (default: 0.7)
            xgb_weight: Weight for XGBoost score (default: 0.3)
            tqs_params: Parameters for TQS qualifier (optional)
            xgb_params: Parameters for XGBoost qualifier (optional)
            sector_prices: Sector ETF prices for XGBoost features (optional)
        """
        super().__init__(
            name="Hybrid TQS + XGBoost",
            description=f"Weighted combination: {tqs_weight:.0%} TQS + {xgb_weight:.0%} XGBoost"
        )

        self.tqs_weight = tqs_weight
        self.xgb_weight = xgb_weight
        self.sector_prices = sector_prices

        # Initialize TQS qualifier
        tqs_defaults = {'ma_period': 100, 'atr_period': 14, 'adx_period': 25}
        tqs_config = {**tqs_defaults, **(tqs_params or {})}
        self.tqs_qualifier = TrendQualityScore(**tqs_config)

        # Initialize XGBoost qualifier
        xgb_defaults = {
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'lookback_years': 3,
            'retrain_freq': 'QS'
        }
        xgb_config = {**xgb_defaults, **(xgb_params or {})}
        self.xgb_qualifier = XGBoostQualifier(**xgb_config)

        # Feature importance (from XGBoost)
        self.feature_importance = None

    def calculate(self, prices: pd.DataFrame, spy_prices: Optional[pd.Series] = None,
                  volumes: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
        """
        Calculate hybrid scores combining TQS and XGBoost

        Steps:
        1. Calculate TQS scores (ATR-based)
        2. Calculate XGBoost scores (ML predictions)
        3. Normalize both to 0-1 range per date
        4. Combine: 70% TQS + 30% XGBoost

        Args:
            prices: Stock prices (DataFrame)
            spy_prices: SPY prices for regime (optional)
            volumes: Volume data (optional)
            **kwargs: Additional arguments

        Returns:
            DataFrame with hybrid scores
        """
        print("   [HYBRID] Calculating TQS scores...")
        tqs_scores = self.tqs_qualifier.calculate(prices, **kwargs)

        print("   [HYBRID] Calculating XGBoost scores...")
        xgb_scores = self.xgb_qualifier.calculate(
            prices, spy_prices, volumes, self.sector_prices, **kwargs
        )

        # Copy feature importance from XGBoost
        if hasattr(self.xgb_qualifier, 'feature_importance'):
            self.feature_importance = self.xgb_qualifier.feature_importance

        print("   [HYBRID] Combining scores (70% TQS + 30% XGBoost)...")

        # Normalize scores to 0-1 range per date (percentile ranking)
        hybrid_scores = pd.DataFrame(index=prices.index, columns=prices.columns)

        for date in prices.index:
            if date not in tqs_scores.index or date not in xgb_scores.index:
                continue

            tqs_row = tqs_scores.loc[date]
            xgb_row = xgb_scores.loc[date]

            # Get valid scores (not NaN)
            valid_stocks = tqs_row.notna() & xgb_row.notna()

            if valid_stocks.sum() < 2:
                # Not enough stocks to rank
                continue

            # Normalize to percentile (0-1)
            tqs_normalized = tqs_row[valid_stocks].rank(pct=True)
            xgb_normalized = xgb_row[valid_stocks].rank(pct=True)

            # Weighted combination
            hybrid_row = (self.tqs_weight * tqs_normalized +
                         self.xgb_weight * xgb_normalized)

            hybrid_scores.loc[date, valid_stocks] = hybrid_row

        print(f"   [HYBRID] Hybrid scores calculated ({self.tqs_weight:.0%} TQS + {self.xgb_weight:.0%} XGBoost)")

        return hybrid_scores


def get_hybrid_qualifier(tqs_weight: float = 0.7,
                         xgb_weight: float = 0.3,
                         sector_prices: Optional[pd.DataFrame] = None,
                         **kwargs) -> HybridQualifier:
    """
    Factory function for Hybrid Qualifier

    Args:
        tqs_weight: Weight for TQS (default: 0.7)
        xgb_weight: Weight for XGBoost (default: 0.3)
        sector_prices: Sector ETF prices (optional)
        **kwargs: Additional parameters split for TQS and XGBoost

    Returns:
        HybridQualifier instance
    """
    # Split kwargs into TQS and XGBoost params
    tqs_params = {}
    xgb_params = {}

    for key, value in kwargs.items():
        if key in ['ma_period', 'atr_period', 'adx_period']:
            tqs_params[key] = value
        elif key in ['n_estimators', 'max_depth', 'learning_rate', 'subsample',
                     'colsample_bytree', 'gamma', 'reg_alpha', 'reg_lambda',
                     'lookback_years', 'retrain_freq']:
            xgb_params[key] = value

    return HybridQualifier(
        tqs_weight=tqs_weight,
        xgb_weight=xgb_weight,
        tqs_params=tqs_params,
        xgb_params=xgb_params,
        sector_prices=sector_prices
    )


if __name__ == "__main__":
    print("="*80)
    print("HYBRID QUALIFIER - TQS + XGBoost")
    print("="*80)
    print()
    print("🎯 Combines the best of both worlds:")
    print("   - TQS (70%): Hand-crafted ATR-based momentum")
    print("   - XGBoost (30%): ML predictions with sector features")
    print()
    print("✅ Benefits:")
    print("   - TQS provides strong baseline momentum signal")
    print("   - XGBoost adds nuanced pattern recognition")
    print("   - Sector features capture macro trends")
    print("   - Weighted combination reduces overfitting risk")
    print()
    print("📊 Expected Performance:")
    print("   - TQS alone: +108.72%")
    print("   - XGBoost + Sectors: +58.79%")
    print("   - Hybrid (70/30): Target +115-125% (+5-15% improvement)")
    print()
    print("="*80)
    print("\n✅ To use:")
    print("   from strategy_factory.hybrid_qualifier import get_hybrid_qualifier")
    print("   qualifier = get_hybrid_qualifier(tqs_weight=0.7, xgb_weight=0.3)")
    print("="*80)
