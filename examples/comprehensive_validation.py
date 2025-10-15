#!/usr/bin/env python3
"""
Comprehensive Strategy Validation Suite

Runs full validation including:
1. Walk-Forward Validation (out-of-sample testing)
2. Monte Carlo Simulation (uncertainty quantification)
3. Point-in-Time Universe (survivorship bias fix)
4. Full backtest comparison

Author: Strategy Factory
Date: 2025-01-14
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Import strategy
import importlib.util
def load_strategy_module(filename, module_name):
    filepath = Path(__file__).parent.parent / 'strategies' / filename
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

crypto_hybrid_module = load_strategy_module('06_nick_radge_crypto_hybrid.py', 'nick_radge_crypto_hybrid')
NickRadgeCryptoHybrid = crypto_hybrid_module.NickRadgeCryptoHybrid

# Import validation utils
from strategy_factory.validation_utils import WalkForwardValidator, MonteCarloSimulator, PointInTimeUniverse


def download_crypto_data(tickers, start_date, end_date):
    """Download crypto data from Yahoo Finance"""
    print(f"\n📊 Downloading {len(tickers)} cryptocurrencies...")

    data = yf.download(tickers, start=start_date, end=end_date, progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        prices = data['Close']
    else:
        prices = data[['Close']].copy()
        prices.columns = [tickers[0]]

    # Drop columns with too much missing data
    missing_pct = prices.isna().sum() / len(prices)
    valid_cols = missing_pct[missing_pct < 0.30].index.tolist()

    if len(valid_cols) < len(tickers):
        dropped = set(tickers) - set(valid_cols)
        print(f"   ⚠️  Dropping {len(dropped)} tickers with >30% missing data")

    prices = prices[valid_cols]
    print(f"   ✅ Downloaded {len(prices.columns)} tickers, {len(prices)} days")

    return prices


def strategy_runner(prices, btc_prices, initial_capital=100000, fees=0.002, slippage=0.002):
    """
    Wrapper function for strategy execution

    Used by walk-forward validator to run strategy on each fold
    """
    strategy = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=5,
        qualifier_type='tqs',
        use_momentum_weighting=True,
        bear_asset='PAXG-USD',
        regime_hysteresis=0.02  # 2% buffer
    )

    portfolio = strategy.backtest(
        prices,
        btc_prices,
        initial_capital=initial_capital,
        fees=fees,
        slippage=slippage,
        log_trades=False
    )

    return portfolio


def main():
    print("="*80)
    print("COMPREHENSIVE STRATEGY VALIDATION SUITE")
    print("="*80)
    print()
    print("This suite performs:")
    print("1. Walk-Forward Validation (out-of-sample testing)")
    print("2. Monte Carlo Simulation (uncertainty quantification)")
    print("3. Point-in-Time Universe (survivorship bias check)")
    print("4. Full backtest comparison")
    print("="*80)

    # Configuration
    START_DATE = "2020-01-01"
    END_DATE = "2025-10-12"
    INITIAL_CAPITAL = 100000

    # Top 50 crypto universe (same as before, for comparison)
    top_50_cryptos = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
        'ADA-USD', 'AVAX-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD',
        'SHIB-USD', 'LTC-USD', 'UNI7083-USD', 'LINK-USD', 'ATOM-USD',
        'ETC-USD', 'XLM-USD', 'BCH-USD', 'NEAR-USD', 'ALGO-USD',
        'FIL-USD', 'VET-USD', 'ICP-USD', 'APT21794-USD', 'HBAR-USD',
        'ARB11841-USD', 'OP-USD', 'GRT6719-USD', 'STX4847-USD', 'RUNE-USD',
        'AAVE-USD', 'MKR-USD', 'INJ-USD', 'SNX-USD', 'FTM-USD',
        'SAND-USD', 'MANA-USD', 'AXS-USD', 'EGLD-USD', 'XTZ-USD',
        'THETA-USD', 'EOS-USD', 'FLOW-USD', 'KCS-USD', 'ZEC-USD',
        'NEO-USD', 'DASH-USD', 'COMP-USD', 'SUSHI-USD', 'YFI-USD'
    ]

    # Download data
    crypto_prices = download_crypto_data(top_50_cryptos, START_DATE, END_DATE)

    # Download BTC and PAXG
    print(f"\n   Downloading BTC for regime filter...")
    btc_data = yf.download('BTC-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(btc_data.columns, pd.MultiIndex):
        btc_prices = btc_data['Close'].iloc[:, 0]
    else:
        btc_prices = btc_data['Close']

    print(f"   Downloading PAXG for bear protection...")
    paxg_data = yf.download('PAXG-USD', start=START_DATE, end=END_DATE, progress=False)
    if isinstance(paxg_data.columns, pd.MultiIndex):
        paxg_close = paxg_data['Close'].iloc[:, 0]
    else:
        paxg_close = paxg_data['Close']

    crypto_prices['PAXG-USD'] = paxg_close

    print(f"\n✅ Data ready: {len(crypto_prices.columns)} cryptos, {len(crypto_prices)} days")
    print(f"   Period: {crypto_prices.index[0].date()} to {crypto_prices.index[-1].date()}")

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'results' / 'crypto_hybrid' / 'validation'
    output_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================================
    # TEST 1: FULL BACKTEST (BASELINE - with survivorship bias)
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 1: FULL BACKTEST (BASELINE)")
    print(f"{'='*80}")
    print(f"⚠️  WARNING: This test has SURVIVORSHIP BIAS (using 2025 top 50)")
    print(f"{'='*80}\n")

    strategy = NickRadgeCryptoHybrid(
        core_allocation=0.70,
        satellite_allocation=0.30,
        core_assets=['BTC-USD', 'ETH-USD', 'SOL-USD'],
        satellite_size=5,
        qualifier_type='tqs',
        use_momentum_weighting=True,
        bear_asset='PAXG-USD',
        regime_hysteresis=0.02
    )

    portfolio_baseline = strategy.backtest(
        crypto_prices,
        btc_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.002,
        slippage=0.002
    )

    baseline_return = float(portfolio_baseline.total_return().iloc[0] if isinstance(portfolio_baseline.total_return(), pd.Series)
                           else portfolio_baseline.total_return()) * 100
    baseline_sharpe = float(portfolio_baseline.sharpe_ratio(freq='D').iloc[0] if isinstance(portfolio_baseline.sharpe_ratio(freq='D'), pd.Series)
                           else portfolio_baseline.sharpe_ratio(freq='D'))

    print(f"\n📊 Baseline Results (WITH survivorship bias):")
    print(f"   Total Return: {baseline_return:.2f}%")
    print(f"   Sharpe Ratio: {baseline_sharpe:.2f}")

    # ============================================================================
    # TEST 2: WALK-FORWARD VALIDATION
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 2: WALK-FORWARD VALIDATION")
    print(f"{'='*80}\n")

    wf_validator = WalkForwardValidator(
        train_period_days=730,  # 2 years train
        test_period_days=365,   # 1 year test
        step_days=365,          # 1 year step
        min_train_days=365
    )

    try:
        wf_results = wf_validator.run_validation(
            strategy_fn=strategy_runner,
            prices=crypto_prices,
            btc_prices=btc_prices,
            initial_capital=INITIAL_CAPITAL,
            fees=0.002,
            slippage=0.002
        )

        # Save results
        wf_results.to_csv(output_dir / 'walk_forward_results.csv', index=False)
        print(f"✅ Walk-forward results saved to: {output_dir / 'walk_forward_results.csv'}")

    except Exception as e:
        print(f"❌ Walk-Forward Validation FAILED: {e}")
        wf_results = pd.DataFrame()

    # ============================================================================
    # TEST 3: MONTE CARLO SIMULATION
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 3: MONTE CARLO SIMULATION")
    print(f"{'='*80}\n")

    mc_simulator = MonteCarloSimulator(n_simulations=1000)

    try:
        mc_results = mc_simulator.run_simulation(
            portfolio_baseline,
            initial_capital=INITIAL_CAPITAL
        )

        # Save results
        mc_results.to_csv(output_dir / 'monte_carlo_results.csv', index=False)
        print(f"✅ Monte Carlo results saved to: {output_dir / 'monte_carlo_results.csv'}")

        # Plot distribution
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.hist(mc_results['total_return_%'], bins=50, alpha=0.7, edgecolor='black')
        ax.axvline(baseline_return, color='red', linestyle='--', linewidth=2, label=f'Actual: {baseline_return:.1f}%')
        ax.axvline(mc_results['total_return_%'].mean(), color='green', linestyle='--', linewidth=2,
                  label=f'Mean: {mc_results["total_return_%"].mean():.1f}%')
        ax.axvline(mc_results['total_return_%'].quantile(0.05), color='orange', linestyle='--',
                  label=f'5th Percentile: {mc_results["total_return_%"].quantile(0.05):.1f}%')
        ax.set_xlabel('Total Return (%)', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Monte Carlo Simulation - Return Distribution', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'monte_carlo_distribution.png', dpi=300)
        plt.close()
        print(f"✅ Distribution plot saved to: {output_dir / 'monte_carlo_distribution.png'}")

    except Exception as e:
        print(f"❌ Monte Carlo Simulation FAILED: {e}")
        mc_results = pd.DataFrame()

    # ============================================================================
    # TEST 4: POINT-IN-TIME UNIVERSE CHECK
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 4: POINT-IN-TIME UNIVERSE ANALYSIS")
    print(f"{'='*80}\n")

    try:
        pit_universe = PointInTimeUniverse.create_pit_universe(
            crypto_prices,
            rebalance_freq='QS',  # Quarterly
            top_n=50
        )

        # Analyze survivorship bias
        first_universe = set(pit_universe[list(pit_universe.keys())[0]])
        last_universe = set(pit_universe[list(pit_universe.keys())[-1]])

        survivors = first_universe & last_universe
        died = first_universe - last_universe
        new_entrants = last_universe - first_universe

        print(f"\n📊 Survivorship Bias Analysis:")
        print(f"   First period ({list(pit_universe.keys())[0].date()}): {len(first_universe)} assets")
        print(f"   Last period ({list(pit_universe.keys())[-1].date()}): {len(last_universe)} assets")
        print(f"   Survivors (in both): {len(survivors)} ({len(survivors)/len(first_universe)*100:.1f}%)")
        print(f"   Died/Delisted: {len(died)} ({len(died)/len(first_universe)*100:.1f}%)")
        print(f"   New Entrants: {len(new_entrants)}")

        if len(died) > 0:
            print(f"\n   ⚠️  Assets that DIED (not in final universe):")
            for asset in sorted(list(died))[:10]:
                print(f"      - {asset}")
            if len(died) > 10:
                print(f"      ... and {len(died)-10} more")

        print(f"\n   📌 IMPORTANT: Using current top 50 creates {len(died)/len(first_universe)*100:.1f}% survivorship bias!")
        print(f"                  Strategy didn't have to survive {len(died)} failures!")

    except Exception as e:
        print(f"❌ Point-in-Time Universe Analysis FAILED: {e}")

    # ============================================================================
    # FINAL SUMMARY
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"VALIDATION SUITE COMPLETE")
    print(f"{'='*80}\n")

    print(f"📁 All results saved to: {output_dir}")
    print(f"\n📊 Summary of Tests:")
    print(f"   1. Baseline Backtest: {baseline_return:.2f}% return, {baseline_sharpe:.2f} Sharpe")

    if len(wf_results) > 0:
        successful = wf_results[wf_results['status'] == 'SUCCESS']
        if len(successful) > 0:
            avg_wf_return = successful['total_return_%'].mean()
            print(f"   2. Walk-Forward (Out-of-Sample): {avg_wf_return:.2f}% avg return ({len(successful)} folds)")
            print(f"      → Out-of-sample is {avg_wf_return/baseline_return*100:.1f}% of in-sample")

    if len(mc_results) > 0:
        mean_mc_return = mc_results['total_return_%'].mean()
        ci_90_lower = mc_results['total_return_%'].quantile(0.05)
        ci_90_upper = mc_results['total_return_%'].quantile(0.95)
        prob_profit = (mc_results['total_return_%'] > 0).sum() / len(mc_results) * 100
        print(f"   3. Monte Carlo (1000 runs): {mean_mc_return:.2f}% mean, 90% CI [{ci_90_lower:.1f}%, {ci_90_upper:.1f}%]")
        print(f"      → Probability of Profit: {prob_profit:.1f}%")

    print(f"\n⚠️  CRITICAL FINDINGS:")
    print(f"   - Baseline has survivorship bias (using 2025 top 50 for 2020-2025)")
    print(f"   - Out-of-sample performance likely lower than in-sample")
    print(f"   - Monte Carlo shows uncertainty range")
    print(f"   - Use walk-forward results for deployment decisions")

    print(f"\n{'='*80}")
    print(f"REVIEW COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
