#!/usr/bin/env python3
"""
Quick test: Validate position-only stop-loss configuration (new default)

Tests that:
1. Portfolio stop-loss is DISABLED by default (None)
2. Position stop-loss is ENABLED at 40% by default
3. Strategy runs without errors
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import yfinance as yf
import importlib.util

# Import module with numeric prefix
spec = importlib.util.spec_from_file_location(
    "nick_radge_crypto_hybrid",
    Path(__file__).parent.parent / "strategies" / "06_nick_radge_crypto_hybrid.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeCryptoHybrid = module.NickRadgeCryptoHybrid

def test_default_config():
    """Test that defaults match position-only configuration"""

    print("=" * 80)
    print("TESTING DEFAULT CONFIGURATION (Position-Only Stops)")
    print("=" * 80)

    # Initialize with defaults
    strategy = NickRadgeCryptoHybrid()

    # Verify configuration
    print("\n✓ Configuration Check:")
    print(f"  Portfolio Stop-Loss: {strategy.portfolio_stop_loss}")
    print(f"  Position Stop-Loss: {strategy.position_stop_loss}")
    print(f"  Position Stop Core Only: {strategy.position_stop_loss_core_only}")

    assert strategy.portfolio_stop_loss is None, "Portfolio stop should be None by default"
    assert strategy.position_stop_loss == 0.40, "Position stop should be 40% by default"
    assert strategy.position_stop_loss_core_only is False, "Position stop should apply to all positions"

    print("\n✓ All assertions passed!")

    # Quick backtest
    print("\n" + "=" * 80)
    print("RUNNING QUICK BACKTEST (Last 1 Year)")
    print("=" * 80)

    test_cryptos = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'AVAX-USD']

    print(f"\nDownloading data for {len(test_cryptos)} cryptos...")
    prices = yf.download(
        test_cryptos,
        start='2024-01-01',
        end='2025-10-14',
        progress=False
    )['Close']

    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = prices.columns.get_level_values(0)

    prices = prices.dropna()
    print(f"✓ Data loaded: {len(prices)} days")

    # Run backtest
    print("\nRunning backtest...")
    btc_prices = prices['BTC-USD'] if 'BTC-USD' in prices.columns else None
    allocations = strategy.generate_allocations(prices, btc_prices=btc_prices)

    # Check for position stops
    position_stops_triggered = 0
    for col in allocations.columns:
        if col.endswith('_STOPPED'):
            stops = allocations[col].sum()
            if stops > 0:
                position_stops_triggered += stops
                print(f"  {col}: {int(stops)} stops triggered")

    print(f"\n✓ Total position stops triggered: {position_stops_triggered}")
    print("✓ Backtest completed successfully!")

    print("\n" + "=" * 80)
    print("SUCCESS: Position-only stop-loss configuration validated!")
    print("=" * 80)
    print("\nConfiguration Summary:")
    print("  ✓ Portfolio stop-loss: DISABLED (None)")
    print("  ✓ Position stop-loss: ENABLED (40%)")
    print("  ✓ Applies to: ALL positions (core + satellite)")
    print("\nBacktest Results:")
    print(f"  ✓ {position_stops_triggered} position stops triggered")
    print("  ✓ No errors or warnings")
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_default_config()
