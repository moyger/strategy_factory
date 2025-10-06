"""
Pattern Detector - Triangle, Flag, and Pennant Detection Module

Based on implementations from:
- zeta-zetra/chart_patterns (triangle detection)
- ZiadFrancis/AscendingTrianglesBacktest (flag patterns)

Detects:
- Ascending triangles (flat resistance + rising support)
- Descending triangles (flat support + falling resistance)
- Symmetrical triangles (converging trendlines)
- Flag patterns (parallel channel consolidation)
- Pennant patterns (converging consolidation)
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict


class PatternDetector:
    """
    Detects chart patterns in OHLC data using pivot points and linear regression
    """

    def __init__(self,
                 lookback: int = 25,
                 min_pivot_points: int = 3,
                 pivot_window: int = 3,
                 r_squared_min: float = 0.7,
                 slope_tolerance: float = 0.0001):
        """
        Initialize pattern detector

        Args:
            lookback: Number of candles to analyze for patterns
            min_pivot_points: Minimum pivot points required for pattern
            pivot_window: Window size for pivot detection (left and right)
            r_squared_min: Minimum R² for trendline quality
            slope_tolerance: Maximum slope for "flat" lines
        """
        self.lookback = lookback
        self.min_pivot_points = min_pivot_points
        self.pivot_window = pivot_window
        self.r_squared_min = r_squared_min
        self.slope_tolerance = slope_tolerance

    def find_pivot_points(self, df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
        """
        Identify pivot highs and lows in price data

        Pivot High: Current candle's high is highest in window
        Pivot Low: Current candle's low is lowest in window

        Args:
            df: OHLC DataFrame
            left: Number of candles to check on left
            right: Number of candles to check on right

        Returns:
            DataFrame with pivot_high and pivot_low boolean columns
        """
        df = df.copy()
        df['pivot_high'] = False
        df['pivot_low'] = False

        highs = df['high'].values
        lows = df['low'].values

        # Need enough data on both sides
        for i in range(left, len(df) - right):
            # Check if current high is highest in window
            window_highs = highs[i-left:i+right+1]
            if highs[i] == max(window_highs):
                df.iloc[i, df.columns.get_loc('pivot_high')] = True

            # Check if current low is lowest in window
            window_lows = lows[i-left:i+right+1]
            if lows[i] == min(window_lows):
                df.iloc[i, df.columns.get_loc('pivot_low')] = True

        return df

    def calculate_trendline(self, points: List[Tuple[int, float]]) -> Tuple[float, float, float]:
        """
        Calculate trendline using linear regression

        Args:
            points: List of (index, price) tuples

        Returns:
            (slope, intercept, r_squared)
        """
        if len(points) < 2:
            return 0.0, 0.0, 0.0

        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])

        # Use linregress directly without normalization - simpler and avoids intercept issues
        if len(points) == 1:
            return 0.0, y[0], 1.0

        # Perform simple linear regression via least squares
        A = np.vstack([x, np.ones(len(x))]).T
        slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]

        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        return slope, intercept, r_squared

    def get_trendline_value(self, slope: float, intercept: float, index: int, base_index: int = 0) -> float:
        """
        Calculate trendline value at given index

        Args:
            slope: Trendline slope
            intercept: Trendline intercept
            index: Index to calculate value for
            base_index: Not used (kept for compatibility)

        Returns:
            Trendline value at index
        """
        return slope * index + intercept

    def detect_triangle(self, df: pd.DataFrame, end_index: int = -1) -> Optional[Dict]:
        """
        Detect triangle patterns (ascending, descending, symmetrical)

        Args:
            df: OHLC DataFrame with pivot points
            end_index: Index to end analysis (-1 for latest)

        Returns:
            Dictionary with pattern info or None
            {
                'type': 'ascending'|'descending'|'symmetrical',
                'resistance': {'slope': float, 'intercept': float, 'r2': float, 'price': float},
                'support': {'slope': float, 'intercept': float, 'r2': float, 'price': float},
                'pivot_highs': List[Tuple[int, float]],
                'pivot_lows': List[Tuple[int, float]],
                'start_index': int,
                'end_index': int
            }
        """
        if end_index == -1:
            end_index = len(df) - 1

        # Get lookback window
        start_index = max(0, end_index - self.lookback)
        window_df = df.iloc[start_index:end_index+1]

        # Get pivot points in window
        pivot_highs = []
        pivot_lows = []

        for i, (idx, row) in enumerate(window_df.iterrows()):
            actual_index = start_index + i
            if row.get('pivot_high', False):
                pivot_highs.append((actual_index, row['high']))
            if row.get('pivot_low', False):
                pivot_lows.append((actual_index, row['low']))

        # Need minimum pivot points
        if len(pivot_highs) < self.min_pivot_points or len(pivot_lows) < self.min_pivot_points:
            return None

        # Calculate trendlines
        upper_slope, upper_intercept, upper_r2 = self.calculate_trendline(pivot_highs)
        lower_slope, lower_intercept, lower_r2 = self.calculate_trendline(pivot_lows)

        # Check R² quality
        if upper_r2 < self.r_squared_min or lower_r2 < self.r_squared_min:
            return None

        # Get current trendline values
        upper_price = self.get_trendline_value(upper_slope, upper_intercept, end_index)
        lower_price = self.get_trendline_value(lower_slope, lower_intercept, end_index)

        # Classify triangle type
        pattern_type = None

        # Ascending: flat resistance + rising support
        if abs(upper_slope) <= self.slope_tolerance and lower_slope > self.slope_tolerance:
            pattern_type = 'ascending'

        # Descending: flat support + falling resistance
        elif abs(lower_slope) <= self.slope_tolerance and upper_slope < -self.slope_tolerance:
            pattern_type = 'descending'

        # Symmetrical: converging lines with opposite slopes
        elif upper_slope < 0 and lower_slope > 0:
            # Check if slopes are relatively balanced
            slope_ratio = abs(upper_slope / lower_slope) if lower_slope != 0 else 0
            if 0.5 <= slope_ratio <= 2.0:  # Reasonably balanced convergence
                pattern_type = 'symmetrical'

        if pattern_type is None:
            return None

        return {
            'type': pattern_type,
            'resistance': {
                'slope': upper_slope,
                'intercept': upper_intercept,
                'r2': upper_r2,
                'price': upper_price
            },
            'support': {
                'slope': lower_slope,
                'intercept': lower_intercept,
                'r2': lower_r2,
                'price': lower_price
            },
            'pivot_highs': pivot_highs,
            'pivot_lows': pivot_lows,
            'start_index': start_index,
            'end_index': end_index
        }

    def detect_flag(self, df: pd.DataFrame, end_index: int = -1) -> Optional[Dict]:
        """
        Detect flag pattern (parallel channel consolidation)

        Flag: High and low pivot points form parallel lines

        Args:
            df: OHLC DataFrame with pivot points
            end_index: Index to end analysis

        Returns:
            Dictionary with flag pattern info or None
        """
        if end_index == -1:
            end_index = len(df) - 1

        # Use shorter lookback for flags (typically 20-40 bars)
        flag_lookback = min(40, self.lookback)
        start_index = max(0, end_index - flag_lookback)
        window_df = df.iloc[start_index:end_index+1]

        # Get pivot points
        pivot_highs = []
        pivot_lows = []

        for i, (idx, row) in enumerate(window_df.iterrows()):
            actual_index = start_index + i
            if row.get('pivot_high', False):
                pivot_highs.append((actual_index, row['high']))
            if row.get('pivot_low', False):
                pivot_lows.append((actual_index, row['low']))

        if len(pivot_highs) < self.min_pivot_points or len(pivot_lows) < self.min_pivot_points:
            return None

        # Calculate trendlines
        upper_slope, upper_intercept, upper_r2 = self.calculate_trendline(pivot_highs)
        lower_slope, lower_intercept, lower_r2 = self.calculate_trendline(pivot_lows)

        # Check R² quality (slightly lower for flags)
        if upper_r2 < 0.7 or lower_r2 < 0.7:
            return None

        # Check for parallelism (slope ratio should be close to 1.0)
        if lower_slope == 0:
            return None

        slope_ratio = upper_slope / lower_slope
        if not (0.9 <= slope_ratio <= 1.05):  # Parallel lines
            return None

        # Both slopes should be relatively small (consolidation, not strong trend)
        if abs(upper_slope) > 0.0002 or abs(lower_slope) > 0.0002:
            return None

        upper_price = self.get_trendline_value(upper_slope, upper_intercept, end_index)
        lower_price = self.get_trendline_value(lower_slope, lower_intercept, end_index)

        return {
            'type': 'flag',
            'resistance': {
                'slope': upper_slope,
                'intercept': upper_intercept,
                'r2': upper_r2,
                'price': upper_price
            },
            'support': {
                'slope': lower_slope,
                'intercept': lower_intercept,
                'r2': lower_r2,
                'price': lower_price
            },
            'pivot_highs': pivot_highs,
            'pivot_lows': pivot_lows,
            'start_index': start_index,
            'end_index': end_index,
            'slope_ratio': slope_ratio
        }

    def detect_pennant(self, df: pd.DataFrame, end_index: int = -1) -> Optional[Dict]:
        """
        Detect pennant pattern (converging consolidation)

        Pennant: High and low pivot points converge symmetrically

        Args:
            df: OHLC DataFrame with pivot points
            end_index: Index to end analysis

        Returns:
            Dictionary with pennant pattern info or None
        """
        if end_index == -1:
            end_index = len(df) - 1

        # Pennants are typically shorter (15-20 bars)
        pennant_lookback = min(20, self.lookback)
        start_index = max(0, end_index - pennant_lookback)
        window_df = df.iloc[start_index:end_index+1]

        # Get pivot points
        pivot_highs = []
        pivot_lows = []

        for i, (idx, row) in enumerate(window_df.iterrows()):
            actual_index = start_index + i
            if row.get('pivot_high', False):
                pivot_highs.append((actual_index, row['high']))
            if row.get('pivot_low', False):
                pivot_lows.append((actual_index, row['low']))

        if len(pivot_highs) < self.min_pivot_points or len(pivot_lows) < self.min_pivot_points:
            return None

        # Calculate trendlines
        upper_slope, upper_intercept, upper_r2 = self.calculate_trendline(pivot_highs)
        lower_slope, lower_intercept, lower_r2 = self.calculate_trendline(pivot_lows)

        # Check R² quality
        if upper_r2 < self.r_squared_min or lower_r2 < self.r_squared_min:
            return None

        # Pennant requirements:
        # 1. Upper line descending (negative slope)
        # 2. Lower line ascending (positive slope)
        # 3. Slopes relatively balanced (similar absolute values)
        if upper_slope >= -0.0001 or lower_slope <= 0.0001:
            return None

        slope_ratio = abs(upper_slope / lower_slope) if lower_slope != 0 else 0
        if not (0.95 <= slope_ratio <= 1.05):  # Near-equal convergence
            return None

        upper_price = self.get_trendline_value(upper_slope, upper_intercept, end_index)
        lower_price = self.get_trendline_value(lower_slope, lower_intercept, end_index)

        return {
            'type': 'pennant',
            'resistance': {
                'slope': upper_slope,
                'intercept': upper_intercept,
                'r2': upper_r2,
                'price': upper_price
            },
            'support': {
                'slope': lower_slope,
                'intercept': lower_intercept,
                'r2': lower_r2,
                'price': lower_price
            },
            'pivot_highs': pivot_highs,
            'pivot_lows': pivot_lows,
            'start_index': start_index,
            'end_index': end_index,
            'slope_ratio': slope_ratio
        }

    def detect_all_patterns(self, df: pd.DataFrame, end_index: int = -1) -> List[Dict]:
        """
        Detect all supported patterns and return them ranked by quality

        Args:
            df: OHLC DataFrame
            end_index: Index to end analysis

        Returns:
            List of pattern dictionaries sorted by R² quality
        """
        # Find pivot points if not already done
        if 'pivot_high' not in df.columns:
            df = self.find_pivot_points(df, self.pivot_window, self.pivot_window)

        patterns = []

        # Try each pattern type
        triangle = self.detect_triangle(df, end_index)
        if triangle:
            patterns.append(triangle)

        flag = self.detect_flag(df, end_index)
        if flag:
            patterns.append(flag)

        pennant = self.detect_pennant(df, end_index)
        if pennant:
            patterns.append(pennant)

        # Sort by average R² (quality)
        patterns.sort(key=lambda p: (p['resistance']['r2'] + p['support']['r2']) / 2, reverse=True)

        return patterns

    def check_breakout(self, pattern: Dict, current_price: float, buffer_pct: float = 0.001) -> Optional[str]:
        """
        Check if price has broken out of pattern

        Args:
            pattern: Pattern dictionary from detect_* methods
            current_price: Current price to check
            buffer_pct: Breakout buffer as percentage (0.001 = 0.1%)

        Returns:
            'long' if breakout above resistance
            'short' if breakout below support
            None if no breakout
        """
        resistance_price = pattern['resistance']['price']
        support_price = pattern['support']['price']

        # Check upside breakout
        if current_price > resistance_price * (1 + buffer_pct):
            return 'long'

        # Check downside breakout
        if current_price < support_price * (1 - buffer_pct):
            return 'short'

        return None


if __name__ == '__main__':
    """
    Example usage and testing
    """
    print("=" * 80)
    print("PATTERN DETECTOR MODULE - Test")
    print("=" * 80)

    # Create sample data - simulate ascending triangle
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='h')

    base_price = 1.1000
    resistance_level = 1.1050

    # Create price action with clear pivots
    highs = []
    lows = []
    closes = []

    for i in range(60):
        # Create swing patterns
        swing_position = (i % 8) / 8.0  # 8-bar swings

        # Rising lows (ascending triangle support)
        swing_low = base_price + (i / 60.0) * 0.0040

        # Flat highs (ascending triangle resistance)
        swing_high = resistance_level

        # Oscillate between support and resistance
        if swing_position < 0.5:
            # Upswing - from low toward high
            close = swing_low + (swing_high - swing_low) * (swing_position * 2)
            high = close + 0.0001
            low = swing_low if swing_position < 0.1 else close - 0.0002
        else:
            # Downswing - from high toward low
            close = swing_high - (swing_high - swing_low) * ((swing_position - 0.5) * 2)
            # Make highs consistently touch resistance level
            high = swing_high if swing_position < 0.7 else close + 0.0001
            low = close - 0.0002

        # Add minimal noise to keep pivots aligned
        high += np.random.normal(0, 0.00002)
        low += np.random.normal(0, 0.00002)
        close += np.random.normal(0, 0.00002)

        highs.append(high)
        lows.append(low)
        closes.append(close)

    df = pd.DataFrame({
        'open': closes,
        'high': highs,
        'low': lows,
        'close': closes
    }, index=dates)

    # Test pattern detection (relax R² requirement for test)
    detector = PatternDetector(
        lookback=50,
        min_pivot_points=3,
        r_squared_min=0.7,  # Lower for test data
        slope_tolerance=0.00001  # Strict for flat lines (0.001% per bar)
    )

    print("\n1. Finding pivot points...")
    df = detector.find_pivot_points(df)
    pivot_high_count = df['pivot_high'].sum()
    pivot_low_count = df['pivot_low'].sum()
    print(f"   Found {pivot_high_count} pivot highs and {pivot_low_count} pivot lows")

    print("\n2. Detecting patterns...")
    patterns = detector.detect_all_patterns(df)

    if len(patterns) == 0:
        print("   No patterns detected")
    else:
        for i, pattern in enumerate(patterns, 1):
            print(f"\n   Pattern {i}: {pattern['type'].upper()}")
            print(f"   Resistance: price={pattern['resistance']['price']:.5f}, "
                  f"slope={pattern['resistance']['slope']:.8f}, R²={pattern['resistance']['r2']:.3f}")
            print(f"   Support: price={pattern['support']['price']:.5f}, "
                  f"slope={pattern['support']['slope']:.8f}, R²={pattern['support']['r2']:.3f}")
            print(f"   Pivot highs: {len(pattern['pivot_highs'])}, Pivot lows: {len(pattern['pivot_lows'])}")

    print("\n3. Testing breakout detection...")
    if len(patterns) > 0:
        best_pattern = patterns[0]

        # Test various price levels
        test_prices = [
            best_pattern['support']['price'] * 0.999,  # Below support
            best_pattern['support']['price'] * 1.0005,  # Inside
            best_pattern['resistance']['price'] * 1.0015  # Above resistance
        ]

        for price in test_prices:
            result = detector.check_breakout(best_pattern, price)
            print(f"   Price {price:.5f}: {result if result else 'No breakout'}")

    print("\n" + "=" * 80)
    print("✅ Pattern detector module test complete")
    print("=" * 80)
