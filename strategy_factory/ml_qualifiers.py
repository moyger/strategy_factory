#!/usr/bin/env python3
"""
Machine Learning Qualifiers for Stock Selection

Implements RandomForestClassifier and other ML methods to predict
stock outperformance for the Nick Radge momentum strategy.

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')


class MLQualifier:
    """
    Machine Learning-based stock qualifier using RandomForest

    Predicts which stocks will outperform over the next quarter
    using technical indicators and market features.

    Features engineered:
    - Momentum indicators (ROC 20/50/100, acceleration)
    - Volatility (ATR, realized vol, Bollinger Band position)
    - Trend strength (ADX, MACD)
    - Volume (volume trend, volume spike)
    - Relative strength (vs SPY, vs sector)
    - Market regime indicators

    Target:
    - Binary classification: Top 20% performers = 1, rest = 0
    - Predicts next quarter's relative performance
    """

    def __init__(self,
                 lookback_years: int = 3,
                 n_estimators: int = 100,
                 max_depth: int = 10,
                 min_samples_split: int = 50,
                 random_state: int = 42,
                 retrain_freq: str = 'QS'):
        """
        Initialize ML Qualifier

        Args:
            lookback_years: Years of historical data for training (default: 3)
            n_estimators: Number of trees in random forest (default: 100)
            max_depth: Maximum tree depth (default: 10)
            min_samples_split: Minimum samples for split (default: 50)
            random_state: Random seed for reproducibility (default: 42)
            retrain_freq: Retraining frequency ('QS' = quarterly)
        """
        self.name = "ML Random Forest Qualifier"
        self.lookback_years = lookback_years
        self.retrain_freq = retrain_freq

        # Model configuration
        self.model_params = {
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'min_samples_split': min_samples_split,
            'min_samples_leaf': 20,
            'max_features': 'sqrt',
            'random_state': random_state,
            'n_jobs': -1,
            'class_weight': 'balanced'  # Handle class imbalance
        }

        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
        self.trained_dates = []

    def engineer_features(self, prices: pd.DataFrame, spy_prices: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Engineer technical features for ML model

        IMPORTANT: All features use lagged data (t-1) to prevent look-ahead bias

        Args:
            prices: DataFrame with stock prices (columns = tickers)
            spy_prices: SPY prices for relative strength (optional)

        Returns:
            DataFrame with engineered features (rows = dates, cols = tickers × features)
        """
        features_list = []

        for ticker in prices.columns:
            price = prices[ticker]

            # Skip if insufficient data
            if price.isna().sum() > len(price) * 0.5:
                continue

            # Calculate indicators (all lagged by 1 day)

            # 1. MOMENTUM FEATURES
            roc_20 = price.pct_change(20).shift(1)
            roc_50 = price.pct_change(50).shift(1)
            roc_100 = price.pct_change(100).shift(1)
            roc_acceleration = (roc_20 - roc_50).shift(1)

            # 2. VOLATILITY FEATURES
            returns = price.pct_change().shift(1)
            realized_vol_20 = returns.rolling(20).std().shift(1) * np.sqrt(252)

            # ATR (simplified)
            high = price.rolling(2).max().shift(1)
            low = price.rolling(2).min().shift(1)
            prev_close = price.shift(2)
            tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean().shift(1)
            atr_pct = (atr_14 / price.shift(1))

            # Bollinger Bands position
            ma_20 = price.rolling(20).mean().shift(1)
            std_20 = price.rolling(20).std().shift(1)
            bb_upper = ma_20 + 2 * std_20
            bb_lower = ma_20 - 2 * std_20
            bb_position = ((price.shift(1) - bb_lower) / (bb_upper - bb_lower)).clip(0, 1)

            # 3. TREND STRENGTH
            # MACD
            ema_12 = price.ewm(span=12).mean().shift(1)
            ema_26 = price.ewm(span=26).mean().shift(1)
            macd = ema_12 - ema_26
            macd_signal = macd.ewm(span=9).mean().shift(1)
            macd_hist = (macd - macd_signal).shift(1)

            # RSI
            delta = price.diff().shift(1)
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = (100 - (100 / (1 + rs))).shift(1)

            # 4. MOVING AVERAGE FEATURES
            ma_50 = price.rolling(50).mean().shift(1)
            ma_100 = price.rolling(100).mean().shift(1)
            ma_200 = price.rolling(200).mean().shift(1)

            price_vs_ma50 = (price.shift(1) / ma_50 - 1)
            price_vs_ma100 = (price.shift(1) / ma_100 - 1)
            price_vs_ma200 = (price.shift(1) / ma_200 - 1)

            above_ma50 = (price.shift(1) > ma_50).astype(float)
            above_ma100 = (price.shift(1) > ma_100).astype(float)
            above_ma200 = (price.shift(1) > ma_200).astype(float)

            # 5. VOLUME FEATURES (if available - otherwise skip)
            # For now, we'll skip volume since not all data sources have it

            # 6. RELATIVE STRENGTH vs SPY
            if spy_prices is not None:
                spy_returns = spy_prices.pct_change(20).shift(1)
                relative_strength = (roc_20 - spy_returns).shift(1)
            else:
                relative_strength = pd.Series(0, index=price.index)

            # Combine features into DataFrame
            ticker_features = pd.DataFrame({
                f'{ticker}_roc_20': roc_20,
                f'{ticker}_roc_50': roc_50,
                f'{ticker}_roc_100': roc_100,
                f'{ticker}_roc_accel': roc_acceleration,
                f'{ticker}_vol_20': realized_vol_20,
                f'{ticker}_atr_pct': atr_pct,
                f'{ticker}_bb_pos': bb_position,
                f'{ticker}_macd_hist': macd_hist,
                f'{ticker}_rsi': rsi,
                f'{ticker}_vs_ma50': price_vs_ma50,
                f'{ticker}_vs_ma100': price_vs_ma100,
                f'{ticker}_vs_ma200': price_vs_ma200,
                f'{ticker}_above_ma50': above_ma50,
                f'{ticker}_above_ma100': above_ma100,
                f'{ticker}_above_ma200': above_ma200,
                f'{ticker}_rel_strength': relative_strength,
            })

            features_list.append(ticker_features)

        # Combine all ticker features
        if features_list:
            all_features = pd.concat(features_list, axis=1)
            return all_features
        else:
            return pd.DataFrame()

    def create_training_labels(self, prices: pd.DataFrame, forward_periods: int = 63) -> pd.DataFrame:
        """
        Create training labels: 1 if stock is in top 20% of forward returns, 0 otherwise

        Args:
            prices: Stock prices
            forward_periods: Forward-looking period (default: 63 = ~3 months)

        Returns:
            DataFrame with binary labels (1 = outperformer, 0 = underperformer)
        """
        # Calculate forward returns
        forward_returns = prices.pct_change(forward_periods).shift(-forward_periods)

        # Rank stocks at each date (top 20% = 1)
        labels = pd.DataFrame(index=prices.index, columns=prices.columns)

        for date in prices.index:
            date_returns = forward_returns.loc[date]

            # Skip if insufficient data
            if date_returns.isna().sum() > len(date_returns) * 0.5:
                labels.loc[date] = np.nan
                continue

            # Get 80th percentile threshold
            threshold = date_returns.quantile(0.80)

            # Label top 20% as 1, rest as 0 (explicit int conversion)
            labels.loc[date] = (date_returns >= threshold).astype(int)

        return labels.astype(float)  # Ensure float dtype for consistency

    def train_model(self, features: pd.DataFrame, labels: pd.DataFrame,
                    train_start: pd.Timestamp, train_end: pd.Timestamp) -> RandomForestClassifier:
        """
        Train RandomForest model on training period

        Args:
            features: Engineered features
            labels: Training labels (1 = outperform, 0 = underperform)
            train_start: Training period start date
            train_end: Training period end date

        Returns:
            Trained RandomForestClassifier
        """
        # Filter to training period
        train_features = features.loc[train_start:train_end]
        train_labels = labels.loc[train_start:train_end]

        # Determine expected number of features per ticker (use first ticker as reference)
        first_ticker = labels.columns[0]
        first_ticker_cols = [col for col in features.columns if col.startswith(f"{first_ticker}_")]
        n_features = len(first_ticker_cols)

        # Reshape to (samples, features) for sklearn
        X_train_list = []
        y_train_list = []

        for ticker in labels.columns:
            # Get features for this ticker
            ticker_cols = [col for col in features.columns if col.startswith(f"{ticker}_")]

            # Skip if wrong number of features (data quality issue)
            if len(ticker_cols) != n_features:
                continue

            ticker_features = train_features[ticker_cols]
            ticker_labels = train_labels[ticker]

            # Drop NaN rows
            valid_idx = ticker_features.notna().all(axis=1) & ticker_labels.notna()

            if valid_idx.sum() > 0:
                X_train_list.append(ticker_features[valid_idx].values)
                y_train_list.append(ticker_labels[valid_idx].values)

        if len(X_train_list) == 0:
            return None

        # Combine all stocks
        X_train = np.vstack(X_train_list)
        y_train = np.hstack(y_train_list)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Train model
        model = RandomForestClassifier(**self.model_params)
        model.fit(X_train_scaled, y_train)

        # Store feature importance
        self.feature_importance = pd.Series(
            model.feature_importances_,
            index=[col.split('_', 1)[1] for col in features.columns[:len(model.feature_importances_)]]
        ).sort_values(ascending=False)

        return model

    def calculate(self, prices: pd.DataFrame, spy_prices: Optional[pd.Series] = None) -> pd.DataFrame:
        """
        Calculate ML-based scores using walk-forward prediction

        IMPORTANT: Uses walk-forward methodology to prevent look-ahead bias
        - Train on past 3 years
        - Predict next quarter
        - Retrain quarterly

        Args:
            prices: Stock prices (DataFrame)
            spy_prices: SPY prices for relative strength (optional)

        Returns:
            DataFrame with ML scores (probability of outperformance)
        """
        print(f"   [ML] Engineering features for {len(prices.columns)} stocks...")
        features = self.engineer_features(prices, spy_prices)

        if features.empty:
            print("   [ML] WARNING: No features engineered")
            return pd.DataFrame(0, index=prices.index, columns=prices.columns)

        print(f"   [ML] Creating training labels...")
        labels = self.create_training_labels(prices, forward_periods=63)

        # Walk-forward prediction
        print(f"   [ML] Starting walk-forward prediction...")
        predictions = pd.DataFrame(index=prices.index, columns=prices.columns)

        # Determine rebalance dates (quarterly)
        rebalance_dates = pd.date_range(
            start=prices.index[0],
            end=prices.index[-1],
            freq=self.retrain_freq
        )

        # Find nearest trading dates
        actual_rebalance_dates = []
        for date in rebalance_dates:
            nearest_idx = prices.index.searchsorted(date)
            if nearest_idx < len(prices.index):
                actual_rebalance_dates.append(prices.index[nearest_idx])

        print(f"   [ML] Retraining at {len(actual_rebalance_dates)} dates...")

        for i, rebal_date in enumerate(actual_rebalance_dates):
            # Training period: 3 years before rebalance date
            train_end = rebal_date
            train_start = train_end - pd.DateOffset(years=self.lookback_years)

            # Skip if insufficient training data
            if train_start < prices.index[0]:
                continue

            # Train model
            model = self.train_model(features, labels, train_start, train_end)

            if model is None:
                continue

            # Prediction period: from rebalance date to next rebalance (or end)
            if i < len(actual_rebalance_dates) - 1:
                pred_end = actual_rebalance_dates[i + 1]
            else:
                pred_end = prices.index[-1]

            pred_start = rebal_date

            # Predict for each stock
            for ticker in prices.columns:
                ticker_cols = [col for col in features.columns if col.startswith(f"{ticker}_")]

                # Skip if wrong number of features
                if len(ticker_cols) != n_features:
                    continue

                ticker_features = features.loc[pred_start:pred_end, ticker_cols]

                # Drop NaN rows
                valid_idx = ticker_features.notna().all(axis=1)

                if valid_idx.sum() == 0:
                    continue

                # Scale and predict
                X_pred = self.scaler.transform(ticker_features[valid_idx].values)
                probs = model.predict_proba(X_pred)[:, 1]  # Probability of class 1 (outperform)

                # Store predictions
                predictions.loc[ticker_features[valid_idx].index, ticker] = probs

            self.trained_dates.append(rebal_date)

            if (i + 1) % 4 == 0:
                print(f"   [ML] Completed {i + 1}/{len(actual_rebalance_dates)} retraining periods")

        print(f"   [ML] Walk-forward prediction complete!")
        print(f"   [ML] Trained {len(self.trained_dates)} times")

        # Fill remaining NaN with neutral score (0.5)
        predictions = predictions.fillna(0.5)

        return predictions

    def get_feature_importance(self) -> Optional[pd.Series]:
        """
        Get feature importance from last trained model

        Returns:
            Series with feature importance scores (sorted descending)
        """
        return self.feature_importance


def get_ml_qualifier(model_type: str = 'random_forest', **kwargs) -> MLQualifier:
    """
    Factory function to create ML qualifiers

    Args:
        model_type: Type of ML model ('random_forest', 'xgboost', 'lightgbm')
        **kwargs: Additional parameters for the model

    Returns:
        MLQualifier instance
    """
    if model_type == 'random_forest':
        return MLQualifier(**kwargs)
    elif model_type == 'xgboost':
        # Future: Implement XGBoost variant
        raise NotImplementedError("XGBoost not yet implemented")
    elif model_type == 'lightgbm':
        # Future: Implement LightGBM variant
        raise NotImplementedError("LightGBM not yet implemented")
    else:
        raise ValueError(f"Unknown ML model type: {model_type}")
