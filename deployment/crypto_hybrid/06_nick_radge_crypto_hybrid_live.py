"""
Nick Radge Crypto Hybrid Strategy - LIVE TRADING ONLY VERSION

This is a clean version with NO backtesting dependencies.
Only contains the allocation logic needed for live trading.

Strategy:
- 70/30 Core/Satellite allocation
- Core: BTC, ETH, SOL (fixed)
- Satellite: Top 3 from universe by momentum (TQS)
- Position stop-loss: 40%
- Quarterly rebalancing

Author: Strategy Factory
Date: 2025-10-15
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


class NickRadgeCryptoHybrid:
    """
    Nick Radge Crypto Hybrid Strategy - Live Trading Version

    No backtesting dependencies - only allocation calculation logic.
    """

    def __init__(
        self,
        core_allocation: float = 0.70,
        satellite_allocation: float = 0.30,
        core_assets: List[str] = None,
        satellite_size: int = 3,
        position_stop_loss: float = 0.40,
        regime_ma_long: int = 200,
        regime_ma_short: int = 100,
        ma_period: int = 100
    ):
        """
        Initialize strategy

        Args:
            core_allocation: Allocation to core assets (default 0.70)
            satellite_allocation: Allocation to satellite assets (default 0.30)
            core_assets: List of core assets (default: BTC, ETH, SOL)
            satellite_size: Number of satellite assets (default: 3)
            position_stop_loss: Position stop loss threshold (default: 0.40)
            regime_ma_long: Long MA for regime filter (default: 200)
            regime_ma_short: Short MA for regime filter (default: 100)
            ma_period: MA period for momentum (default: 100)
        """
        self.core_allocation = core_allocation
        self.satellite_allocation = satellite_allocation
        self.core_assets = core_assets or ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        self.satellite_size = satellite_size
        self.position_stop_loss = position_stop_loss
        self.regime_ma_long = regime_ma_long
        self.regime_ma_short = regime_ma_short
        self.ma_period = ma_period

    def detect_regime(self, btc_prices: pd.Series) -> str:
        """
        Detect market regime using BTC moving averages

        Args:
            btc_prices: BTC price series

        Returns:
            'STRONG_BULL', 'WEAK_BULL', or 'BEAR'
        """
        if len(btc_prices) < self.regime_ma_long:
            return 'STRONG_BULL'  # Default if not enough data

        ma_long = btc_prices.rolling(self.regime_ma_long).mean()
        ma_short = btc_prices.rolling(self.regime_ma_short).mean()

        current_price = btc_prices.iloc[-1]
        current_ma_long = ma_long.iloc[-1]
        current_ma_short = ma_short.iloc[-1]

        if current_price > current_ma_long and current_price > current_ma_short:
            return 'STRONG_BULL'
        elif current_price > current_ma_long:
            return 'WEAK_BULL'
        else:
            return 'BEAR'

    def calculate_tqs(self, prices: pd.Series) -> float:
        """
        Calculate TQS (Trend Quality Score) momentum ranking

        Args:
            prices: Price series for asset

        Returns:
            TQS score (higher = better momentum)
        """
        if len(prices) < self.ma_period:
            return 0.0

        # Rate of Change (ROC) - momentum component
        roc = (prices.iloc[-1] - prices.iloc[-self.ma_period]) / prices.iloc[-self.ma_period]

        # Moving average trend
        ma = prices.rolling(self.ma_period).mean()
        above_ma = 1.0 if prices.iloc[-1] > ma.iloc[-1] else 0.0

        # Combine components
        tqs_score = roc * (1.0 + above_ma)

        return tqs_score

    def select_satellites(
        self,
        prices: pd.DataFrame,
        exclude_assets: List[str] = None
    ) -> List[str]:
        """
        Select top satellite assets by momentum

        Args:
            prices: DataFrame with price data for all assets
            exclude_assets: Assets to exclude (e.g., core assets)

        Returns:
            List of selected satellite asset symbols
        """
        exclude_assets = exclude_assets or []

        # Calculate TQS for all non-core assets
        tqs_scores = {}
        for symbol in prices.columns:
            if symbol not in exclude_assets:
                tqs_score = self.calculate_tqs(prices[symbol])
                tqs_scores[symbol] = tqs_score

        # Sort by TQS score (descending)
        sorted_assets = sorted(tqs_scores.items(), key=lambda x: x[1], reverse=True)

        # Return top N
        satellites = [asset for asset, score in sorted_assets[:self.satellite_size]]

        return satellites

    def generate_allocations(
        self,
        prices: pd.DataFrame,
        btc_prices: pd.Series = None
    ) -> Dict[str, float]:
        """
        Generate target allocations for all assets

        Args:
            prices: DataFrame with price data for all assets (columns = symbols)
            btc_prices: BTC price series for regime detection (optional)

        Returns:
            Dictionary mapping symbol to target allocation (0.0 to 1.0)
        """
        # Detect regime
        if btc_prices is None:
            btc_prices = prices['BTC/USDT'] if 'BTC/USDT' in prices.columns else prices.iloc[:, 0]

        regime = self.detect_regime(btc_prices)

        # Initialize allocations
        allocations = {}

        # BEAR regime: Go to cash (or bear asset)
        if regime == 'BEAR':
            for symbol in prices.columns:
                allocations[symbol] = 0.0
            return allocations

        # Select satellites
        satellites = self.select_satellites(prices, exclude_assets=self.core_assets)

        # Calculate core allocations (equal weighted)
        core_allocation_per_asset = self.core_allocation / len(self.core_assets)
        for symbol in self.core_assets:
            allocations[symbol] = core_allocation_per_asset

        # Calculate satellite allocations (equal weighted)
        satellite_allocation_per_asset = self.satellite_allocation / len(satellites)
        for symbol in satellites:
            allocations[symbol] = satellite_allocation_per_asset

        # Set all other assets to 0
        for symbol in prices.columns:
            if symbol not in allocations:
                allocations[symbol] = 0.0

        return allocations

    def apply_position_stops(
        self,
        current_positions: Dict[str, float],
        entry_prices: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> Dict[str, bool]:
        """
        Check which positions should be stopped out

        Args:
            current_positions: Current position sizes
            entry_prices: Entry prices for each position
            current_prices: Current prices for each position

        Returns:
            Dictionary mapping symbol to should_close (True/False)
        """
        stop_signals = {}

        for symbol, position_size in current_positions.items():
            if position_size > 0 and symbol in entry_prices:
                entry_price = entry_prices[symbol]
                current_price = current_prices.get(symbol, 0)

                if current_price > 0:
                    # Calculate loss from entry
                    loss_pct = (current_price - entry_price) / entry_price

                    # Check if stop triggered
                    if loss_pct < -self.position_stop_loss:
                        stop_signals[symbol] = True
                    else:
                        stop_signals[symbol] = False

        return stop_signals


def main():
    """Example usage"""
    print("Nick Radge Crypto Hybrid - Live Trading Version")
    print("=" * 60)
    print("This version has NO backtesting dependencies.")
    print("Only contains allocation logic for live trading.")
    print("")
    print("Strategy Parameters:")
    print("  - Core Allocation: 70%")
    print("  - Satellite Allocation: 30%")
    print("  - Core Assets: BTC, ETH, SOL")
    print("  - Satellite Size: 3")
    print("  - Position Stop Loss: 40%")
    print("")
    print("Use with live_crypto_bybit.py for live trading.")


if __name__ == '__main__':
    main()
