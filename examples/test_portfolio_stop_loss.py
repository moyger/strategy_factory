#!/usr/bin/env python3
"""
Test Portfolio Stop-Loss Implementation

Tests the portfolio-level stop-loss on the crypto hybrid strategy
to verify it protects against black swan events (like Trump tariff crash).

Expected behavior:
- When portfolio drops -25% from peak → Exit all positions to PAXG
- Enter 30-day cooldown
- Resume normal signals after cooldown

Author: Strategy Factory
Date: 2025-01-14
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import using importlib for more reliable loading
def load_strategy_module(filename, module_name):
    """Load strategy module using importlib"""
    filepath = Path(__file__).parent.parent / 'strategies' / filename
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load strategy module
crypto_hybrid_module = load_strategy_module('06_nick_radge_crypto_hybrid.py', 'nick_radge_crypto_hybrid')
NickRadgeCryptoHybrid = crypto_hybrid_module.NickRadgeCryptoHybrid

def main():
    print("="*80)
    print("TESTING PORTFOLIO STOP-LOSS IMPLEMENTATION")
    print("="*80)

    # Configuration
    START_DATE = "2020-01-01"
    END_DATE = "2025-10-12"
    INITIAL_CAPITAL = 100000

    # Small test universe for faster testing
    test_cryptos = [
        'BTC-USD', 'ETH-USD', 'SOL-USD',  # Core
        'ADA-USD', 'AVAX-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD',  # Satellite options
        'PAXG-USD'  # Bear asset
    ]

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Test Universe: {len(test_cryptos)} cryptos")
    print(f"   Portfolio Stop-Loss: 25%")
    print(f"   Smart Re-entry: 2 days + 3% recovery")

    # Download data
    print(f"\n📊 Downloading crypto data...")
    crypto_prices = yf.download(
        test_cryptos,
        start=START_DATE,
        end=END_DATE,
        progress=False
    )

    if isinstance(crypto_prices.columns, pd.MultiIndex):
        crypto_prices = crypto_prices['Close']

    # Download BTC for regime filter
    btc_data = yf.download('BTC-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(btc_data.columns, pd.MultiIndex):
        btc_prices = btc_data['Close'].iloc[:, 0]
    else:
        btc_prices = btc_data['Close']

    print(f"   ✅ Downloaded {len(crypto_prices.columns)} cryptos, {len(crypto_prices)} days")

    # TEST 1: Strategy WITH smart stop-loss (25%)
    print("\n" + "="*80)
    print("TEST 1: STRATEGY WITH SMART PORTFOLIO STOP-LOSS (25%)")
    print("="*80)

    strategy_with_sl = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=3,
        qualifier_type='tqs',
        use_momentum_weighting=True,
        bear_asset='PAXG-USD',
        portfolio_stop_loss=0.25,  # 25% stop-loss (default)
        stop_loss_min_cooldown_days=2,  # Wait 2 days minimum
        stop_loss_reentry_threshold=0.03  # Re-enter on 3% recovery
    )

    portfolio_with_sl = strategy_with_sl.backtest(
        crypto_prices,
        btc_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.002,
        slippage=0.002,
        log_trades=False
    )

    # TEST 2: Strategy WITHOUT stop-loss (baseline)
    print("\n" + "="*80)
    print("TEST 2: STRATEGY WITHOUT STOP-LOSS (Baseline)")
    print("="*80)

    strategy_no_sl = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=3,
        qualifier_type='tqs',
        use_momentum_weighting=True,
        bear_asset='PAXG-USD',
        portfolio_stop_loss=None  # No stop-loss
    )

    portfolio_no_sl = strategy_no_sl.backtest(
        crypto_prices,
        btc_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.002,
        slippage=0.002,
        log_trades=False
    )

    # Compare results
    print("\n" + "="*80)
    print("COMPARISON: WITH vs WITHOUT STOP-LOSS")
    print("="*80)

    # Extract metrics
    def get_metrics(portfolio):
        total_ret = portfolio.total_return()
        if isinstance(total_ret, pd.Series):
            total_ret = float(total_ret.iloc[0])

        ann_ret = portfolio.annualized_return()
        if isinstance(ann_ret, pd.Series):
            ann_ret = float(ann_ret.iloc[0])

        sharpe = portfolio.sharpe_ratio(freq='D')
        if isinstance(sharpe, pd.Series):
            sharpe = float(sharpe.iloc[0])

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = float(max_dd.iloc[0])

        return total_ret, ann_ret, sharpe, max_dd

    with_sl_ret, with_sl_ann, with_sl_sharpe, with_sl_dd = get_metrics(portfolio_with_sl)
    no_sl_ret, no_sl_ann, no_sl_sharpe, no_sl_dd = get_metrics(portfolio_no_sl)

    print(f"\n📊 Performance Comparison:")
    print(f"\n   WITH Stop-Loss (25%):")
    print(f"      Total Return:      {with_sl_ret*100:>8.2f}%")
    print(f"      Annualized Return: {with_sl_ann*100:>8.2f}%")
    print(f"      Sharpe Ratio:      {with_sl_sharpe:>8.2f}")
    print(f"      Max Drawdown:      {with_sl_dd*100:>8.2f}%")

    print(f"\n   WITHOUT Stop-Loss (Baseline):")
    print(f"      Total Return:      {no_sl_ret*100:>8.2f}%")
    print(f"      Annualized Return: {no_sl_ann*100:>8.2f}%")
    print(f"      Sharpe Ratio:      {no_sl_sharpe:>8.2f}")
    print(f"      Max Drawdown:      {no_sl_dd*100:>8.2f}%")

    print(f"\n📈 Impact Analysis:")
    ret_diff = with_sl_ret - no_sl_ret
    dd_diff = with_sl_dd - no_sl_dd
    sharpe_diff = with_sl_sharpe - no_sl_sharpe

    print(f"      Return Difference:  {ret_diff*100:>+8.2f}%")
    print(f"      Max DD Difference:  {dd_diff*100:>+8.2f}%")
    print(f"      Sharpe Difference:  {sharpe_diff:>+8.2f}")

    # Verdict
    print(f"\n🎯 Verdict:")
    if abs(dd_diff) > 0.05:  # Stop-loss reduced DD by >5%
        print(f"   ✅ Stop-loss EFFECTIVE: Reduced max DD by {abs(dd_diff)*100:.1f}%")
        if ret_diff < -0.10:  # But cost >10% return
            print(f"   ⚠️  Trade-off: Lost {abs(ret_diff)*100:.1f}% return for protection")
            print(f"   💡 Consider: Adjust threshold (25% → 30%) or cooldown (30 → 20 days)")
        else:
            print(f"   ✅ Return impact acceptable: {ret_diff*100:+.1f}%")
    else:
        print(f"   ⚠️  Stop-loss NOT triggered or minimal impact")
        print(f"   💡 Consider: Lower threshold (25% → 20%) for more aggressive protection")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
