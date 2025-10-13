#!/usr/bin/env python3
"""
Performance Qualifiers - ATR-Based Stock Ranking Systems

Implements Tomas Nesnidal's ATR-based principles for momentum stock selection.
Alternative ranking methods to ROC for Nick Radge momentum strategy.

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


def calculate_atr(prices: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average True Range for all stocks

    Args:
        prices: DataFrame with close prices (columns = tickers)
        period: ATR period (default: 14)

    Returns:
        DataFrame with ATR values
    """
    high = prices.rolling(window=2).max()
    low = prices.rolling(window=2).min()
    prev_close = prices.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Reshape back to match prices structure
    if isinstance(prices, pd.Series):
        atr = true_range.rolling(window=period).mean()
    else:
        # For DataFrame, calculate per column
        atr = pd.DataFrame(index=prices.index, columns=prices.columns)
        for col in prices.columns:
            high_col = prices[col].rolling(window=2).max()
            low_col = prices[col].rolling(window=2).min()
            prev_close_col = prices[col].shift(1)

            tr1_col = high_col - low_col
            tr2_col = (high_col - prev_close_col).abs()
            tr3_col = (low_col - prev_close_col).abs()

            true_range_col = pd.concat([tr1_col, tr2_col, tr3_col], axis=1).max(axis=1)
            atr[col] = true_range_col.rolling(window=period).mean()

    return atr


def calculate_adx(prices: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (trend strength)

    Args:
        prices: DataFrame with close prices
        period: ADX period (default: 14)

    Returns:
        DataFrame with ADX values
    """
    # Simplified ADX calculation
    # For production, consider using ta-lib or more sophisticated implementation

    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    adx_df = pd.DataFrame(index=prices.index, columns=prices.columns)

    for col in prices.columns:
        price_series = prices[col]

        # Calculate +DM and -DM
        high = price_series.rolling(window=2).max()
        low = price_series.rolling(window=2).min()

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # ATR for this stock
        atr = calculate_atr(price_series.to_frame(), period=period).iloc[:, 0]

        # Smooth DM
        plus_di = 100 * pd.Series(plus_dm, index=price_series.index).rolling(window=period).mean() / atr
        minus_di = 100 * pd.Series(minus_dm, index=price_series.index).rolling(window=period).mean() / atr

        # Calculate DX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)

        # ADX is smoothed DX
        adx_df[col] = dx.rolling(window=period).mean()

    return adx_df


class PerformanceQualifier:
    """Base class for performance qualifiers"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate qualifier scores for all stocks"""
        raise NotImplementedError

    def rank_stocks(self,
                   prices: pd.DataFrame,
                   date: pd.Timestamp,
                   above_ma: pd.Series,
                   **kwargs) -> pd.DataFrame:
        """
        Rank stocks at given date

        Args:
            prices: Stock prices DataFrame
            date: Date to rank stocks
            above_ma: Boolean series of stocks above MA
            **kwargs: Additional parameters

        Returns:
            DataFrame with ranked stocks and scores
        """
        scores = self.calculate(prices, **kwargs)

        if date not in scores.index:
            return pd.DataFrame()

        score_row = scores.loc[date]

        # Filter: Only stocks above MA and with valid scores
        valid_stocks = above_ma[above_ma == True].index
        valid_stocks = [s for s in valid_stocks if pd.notna(score_row[s])]

        if len(valid_stocks) == 0:
            return pd.DataFrame()

        scores_valid = score_row[valid_stocks].dropna()

        if len(scores_valid) == 0:
            return pd.DataFrame()

        # Sort by score (descending)
        ranked = scores_valid.sort_values(ascending=False)

        return pd.DataFrame({
            'ticker': ranked.index,
            'score': ranked.values
        })


class ATRNormalizedMomentum(PerformanceQualifier):
    """
    ATR-Normalized Momentum (ANM)

    Measures momentum relative to volatility.
    Formula: (Price - Price[n]) / ATR(n)

    High ANM = strong directional move with controlled volatility
    """

    def __init__(self, momentum_period: int = 100, atr_period: int = 14):
        super().__init__(
            name="ATR-Normalized Momentum",
            description="Momentum adjusted for volatility"
        )
        self.momentum_period = momentum_period
        self.atr_period = atr_period

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate ATR-normalized momentum"""
        # Raw momentum
        momentum = (prices - prices.shift(self.momentum_period)) / prices.shift(self.momentum_period)

        # ATR as percentage of price
        atr = calculate_atr(prices, period=self.atr_period)
        atr_pct = atr / prices

        # Normalize momentum by ATR
        anm = momentum / atr_pct

        return anm


class BreakoutStrengthScore(PerformanceQualifier):
    """
    Breakout Strength Score (BSS)

    Identifies stocks breaking out with conviction.
    Formula: (Price - POI) / (k × ATR)

    Where POI = Point of Initiation (100-day MA or previous high)
    BSS > 2.0 = strong breakout
    """

    def __init__(self, poi_period: int = 100, atr_period: int = 14, k: float = 2.0):
        super().__init__(
            name="Breakout Strength Score",
            description="Distance from POI in ATR multiples"
        )
        self.poi_period = poi_period
        self.atr_period = atr_period
        self.k = k

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate breakout strength"""
        # Point of Initiation (using MA)
        poi = prices.rolling(window=self.poi_period).mean()

        # ATR
        atr = calculate_atr(prices, period=self.atr_period)

        # Breakout strength
        bss = (prices - poi) / (self.k * atr)

        return bss


class VolatilityExpansionMomentum(PerformanceQualifier):
    """
    Volatility Expansion Momentum (VEM)

    Combines momentum with volatility regime.
    Formula: ROC × (Current ATR / Historical Avg ATR)

    High VEM = strong momentum + increasing volatility (breakout conditions)
    """

    def __init__(self, roc_period: int = 100, atr_period: int = 14, atr_avg_period: int = 50):
        super().__init__(
            name="Volatility Expansion Momentum",
            description="Momentum during volatility expansion"
        )
        self.roc_period = roc_period
        self.atr_period = atr_period
        self.atr_avg_period = atr_avg_period

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate volatility expansion momentum"""
        # ROC
        roc = prices.pct_change(self.roc_period) * 100

        # ATR expansion ratio
        atr_current = calculate_atr(prices, period=self.atr_period)
        atr_avg = atr_current.rolling(window=self.atr_avg_period).mean()
        atr_expansion = atr_current / atr_avg

        # VEM
        vem = roc * atr_expansion

        return vem


class TrendQualityScore(PerformanceQualifier):
    """
    Trend Quality Score (TQS)

    Combines distance above MA with ADX trend strength.
    Formula: (Price - MA) / ATR × ADX / 25

    High TQS = stock in strong, clean uptrend with low noise
    """

    def __init__(self, ma_period: int = 100, atr_period: int = 14, adx_period: int = 25):
        super().__init__(
            name="Trend Quality Score",
            description="Trend strength with ADX confirmation"
        )
        self.ma_period = ma_period
        self.atr_period = atr_period
        self.adx_period = adx_period

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate trend quality score"""
        # Distance above MA
        ma = prices.rolling(window=self.ma_period).mean()
        distance = prices - ma

        # Normalize by ATR
        atr = calculate_atr(prices, period=self.atr_period)
        normalized_distance = distance / atr

        # ADX (trend strength)
        adx = calculate_adx(prices, period=self.adx_period)

        # TQS
        tqs = normalized_distance * (adx / 25)

        return tqs


class RiskAdjustedMomentum(PerformanceQualifier):
    """
    Risk-Adjusted Momentum (RAM)

    Penalizes stocks with high ROC but severe drawdowns.
    Formula: ROC / (Max Drawdown / ATR%)

    High RAM = smooth momentum without brutal drawdowns
    """

    def __init__(self, roc_period: int = 100, atr_period: int = 14):
        super().__init__(
            name="Risk-Adjusted Momentum",
            description="Momentum adjusted for drawdown risk"
        )
        self.roc_period = roc_period
        self.atr_period = atr_period

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate risk-adjusted momentum"""
        # ROC
        roc = prices.pct_change(self.roc_period) * 100

        # Rolling maximum and drawdown
        rolling_max = prices.rolling(window=self.roc_period, min_periods=1).max()
        drawdown = (prices - rolling_max) / rolling_max
        max_dd = drawdown.rolling(window=self.roc_period).min().abs()

        # ATR as percentage
        atr = calculate_atr(prices, period=self.atr_period)
        atr_pct = atr / prices

        # Risk metric (drawdown normalized by ATR)
        risk = max_dd / atr_pct

        # Avoid division by zero
        risk = risk.replace(0, np.nan)

        # RAM
        ram = roc / risk

        return ram


class CompositeScore(PerformanceQualifier):
    """
    Composite Score - Weighted combination of multiple qualifiers

    Default weights:
    - 30% ATR-Normalized Momentum
    - 25% Breakout Strength Score
    - 20% Volatility Expansion Momentum
    - 15% Trend Quality Score
    - 10% Risk-Adjusted Momentum
    """

    def __init__(self,
                 weights: Optional[Dict[str, float]] = None,
                 momentum_period: int = 100,
                 atr_period: int = 14):
        super().__init__(
            name="Composite Score",
            description="Weighted combination of ATR-based qualifiers"
        )

        self.weights = weights or {
            'anm': 0.30,
            'bss': 0.25,
            'vem': 0.20,
            'tqs': 0.15,
            'ram': 0.10
        }

        # Initialize sub-qualifiers
        self.qualifiers = {
            'anm': ATRNormalizedMomentum(momentum_period, atr_period),
            'bss': BreakoutStrengthScore(momentum_period, atr_period),
            'vem': VolatilityExpansionMomentum(momentum_period, atr_period),
            'tqs': TrendQualityScore(momentum_period, atr_period),
            'ram': RiskAdjustedMomentum(momentum_period, atr_period)
        }

    def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Calculate composite score"""
        # Calculate all sub-scores
        scores = {}
        for name, qualifier in self.qualifiers.items():
            scores[name] = qualifier.calculate(prices, **kwargs)

        # Normalize each score to 0-1 range per date
        normalized_scores = {}
        for name, score_df in scores.items():
            # Rank-based normalization (percentile)
            normalized = score_df.rank(axis=1, pct=True)
            normalized_scores[name] = normalized

        # Weighted combination
        composite = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

        for name, weight in self.weights.items():
            if name in normalized_scores:
                composite += normalized_scores[name] * weight

        return composite


# Factory function
def get_qualifier(qualifier_type: str, **kwargs) -> PerformanceQualifier:
    """
    Get performance qualifier by type

    Args:
        qualifier_type: One of 'anm', 'bss', 'vem', 'tqs', 'ram', 'composite', 'roc', 'ml_rf', 'ml_xgb'
        **kwargs: Additional parameters for qualifier

    Returns:
        PerformanceQualifier instance
    """
    qualifiers = {
        'anm': ATRNormalizedMomentum,
        'bss': BreakoutStrengthScore,
        'vem': VolatilityExpansionMomentum,
        'tqs': TrendQualityScore,
        'ram': RiskAdjustedMomentum,
        'composite': CompositeScore
    }

    if qualifier_type == 'roc':
        # Return simple ROC calculator
        class ROCQualifier(PerformanceQualifier):
            def __init__(self, roc_period: int = 100):
                super().__init__(name="ROC", description="Rate of Change")
                self.roc_period = roc_period

            def calculate(self, prices: pd.DataFrame, **kwargs) -> pd.DataFrame:
                return prices.pct_change(self.roc_period) * 100

        return ROCQualifier(**kwargs)

    if qualifier_type == 'ml_rf':
        # ML-based qualifier (imported on demand to avoid requiring sklearn for basic usage)
        from strategy_factory.ml_qualifiers import MLQualifier
        return MLQualifier(**kwargs)

    if qualifier_type == 'ml_xgb':
        # XGBoost-based qualifier (imported on demand)
        from strategy_factory.ml_xgboost import XGBoostQualifier
        return XGBoostQualifier(**kwargs)

    if qualifier_type not in qualifiers:
        raise ValueError(f"Unknown qualifier: {qualifier_type}. Choose from {list(qualifiers.keys())}, 'roc', 'ml_rf', or 'ml_xgb'")

    return qualifiers[qualifier_type](**kwargs)


if __name__ == "__main__":
    print("="*80)
    print("PERFORMANCE QUALIFIERS - ATR-BASED STOCK RANKING")
    print("="*80)

    print("\n📊 Available Qualifiers:\n")

    qualifiers_info = [
        ("roc", "Rate of Change", "Traditional momentum (Nick Radge default)"),
        ("anm", "ATR-Normalized Momentum", "Momentum adjusted for volatility"),
        ("bss", "Breakout Strength Score", "Distance from POI in ATR multiples"),
        ("vem", "Volatility Expansion Momentum", "Momentum during volatility expansion"),
        ("tqs", "Trend Quality Score", "Trend strength with ADX confirmation"),
        ("ram", "Risk-Adjusted Momentum", "Momentum adjusted for drawdown risk"),
        ("composite", "Composite Score", "Weighted combination of all qualifiers")
    ]

    for code, name, desc in qualifiers_info:
        print(f"   {code.upper()}: {name}")
        print(f"        {desc}\n")

    print("="*80)
    print("\n✅ To use in Nick Radge strategy, modify rank_stocks() method:")
    print("   qualifier = get_qualifier('composite')  # or 'anm', 'bss', etc.")
    print("   scores = qualifier.calculate(prices)")
    print("="*80)
