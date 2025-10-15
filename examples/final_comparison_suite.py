#!/usr/bin/env python3
"""
Final Comparison Suite

Tests:
1. 2017-2018 Crash Period (bear market stress test)
2. Simple 60/40 BTC/ETH Baseline
3. Simple 70/30 BTC/ETH/SOL Baseline
4. Complex Crypto Hybrid Strategy

Author: Strategy Factory
Date: 2025-01-14
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import yfinance as yf
import vectorbt as vbt
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
    valid_cols = missing_pct[missing_pct < 0.40].index.tolist()

    if len(valid_cols) < len(tickers):
        dropped = set(tickers) - set(valid_cols)
        print(f"   ⚠️  Dropping {len(dropped)} tickers with >40% missing data")

    prices = prices[valid_cols]
    print(f"   ✅ Downloaded {len(prices.columns)} tickers, {len(prices)} days")

    return prices


def test_simple_6040(prices, btc_col='BTC-USD', eth_col='ETH-USD', initial_capital=100000):
    """Test simple 60/40 BTC/ETH portfolio"""

    if btc_col not in prices.columns or eth_col not in prices.columns:
        print(f"❌ Missing {btc_col} or {eth_col}")
        return None

    # Create 60/40 allocation
    allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    allocations[btc_col] = 0.60
    allocations[eth_col] = 0.40

    # Rebalance quarterly
    rebalance_dates = pd.date_range(start=prices.index[0], end=prices.index[-1], freq='QS')
    allocations_rebalanced = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    for reb_date in rebalance_dates:
        nearest = prices.index[prices.index >= reb_date]
        if len(nearest) > 0:
            actual_date = nearest[0]
            allocations_rebalanced.loc[actual_date, btc_col] = 0.60
            allocations_rebalanced.loc[actual_date, eth_col] = 0.40

    # Backtest
    portfolio = vbt.Portfolio.from_orders(
        close=prices,
        size=allocations_rebalanced,
        size_type='targetpercent',
        fees=0.002,
        slippage=0.002,
        init_cash=initial_capital,
        cash_sharing=True,
        group_by=True,
        call_seq='auto',
        freq='D'
    )

    return portfolio


def test_simple_703030(prices, btc_col='BTC-USD', eth_col='ETH-USD', sol_col='SOL-USD', initial_capital=100000):
    """Test simple 70/30 BTC/ETH with 30% SOL split"""

    if btc_col not in prices.columns or eth_col not in prices.columns:
        print(f"❌ Missing {btc_col} or {eth_col}")
        return None

    has_sol = sol_col in prices.columns

    # Create allocation
    allocations = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    if has_sol:
        # 70% BTC/ETH (35% each), 30% SOL
        allocations[btc_col] = 0.35
        allocations[eth_col] = 0.35
        allocations[sol_col] = 0.30
    else:
        # Fall back to 70/30 BTC/ETH
        allocations[btc_col] = 0.70
        allocations[eth_col] = 0.30

    # Rebalance quarterly
    rebalance_dates = pd.date_range(start=prices.index[0], end=prices.index[-1], freq='QS')
    allocations_rebalanced = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    for reb_date in rebalance_dates:
        nearest = prices.index[prices.index >= reb_date]
        if len(nearest) > 0:
            actual_date = nearest[0]
            if has_sol:
                allocations_rebalanced.loc[actual_date, btc_col] = 0.35
                allocations_rebalanced.loc[actual_date, eth_col] = 0.35
                allocations_rebalanced.loc[actual_date, sol_col] = 0.30
            else:
                allocations_rebalanced.loc[actual_date, btc_col] = 0.70
                allocations_rebalanced.loc[actual_date, eth_col] = 0.30

    # Backtest
    portfolio = vbt.Portfolio.from_orders(
        close=prices,
        size=allocations_rebalanced,
        size_type='targetpercent',
        fees=0.002,
        slippage=0.002,
        init_cash=initial_capital,
        cash_sharing=True,
        group_by=True,
        call_seq='auto',
        freq='D'
    )

    return portfolio


def extract_metrics(portfolio, name):
    """Extract metrics from portfolio"""
    try:
        total_return = float(portfolio.total_return().iloc[0] if isinstance(portfolio.total_return(), pd.Series)
                           else portfolio.total_return()) * 100
        sharpe = float(portfolio.sharpe_ratio(freq='D').iloc[0] if isinstance(portfolio.sharpe_ratio(freq='D'), pd.Series)
                     else portfolio.sharpe_ratio(freq='D'))
        max_dd = float(portfolio.max_drawdown().iloc[0] if isinstance(portfolio.max_drawdown(), pd.Series)
                     else portfolio.max_drawdown()) * 100

        try:
            win_rate = float(portfolio.trades.win_rate().iloc[0] if isinstance(portfolio.trades.win_rate(), pd.Series)
                           else portfolio.trades.win_rate()) * 100
        except:
            win_rate = np.nan

        num_trades = len(portfolio.trades.records)

        final_value = float(portfolio.value().iloc[-1].iloc[0] if isinstance(portfolio.value().iloc[-1], pd.Series)
                          else portfolio.value().iloc[-1])

        return {
            'strategy': name,
            'total_return_%': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown_%': max_dd,
            'win_rate_%': win_rate,
            'num_trades': num_trades,
            'final_value': final_value
        }
    except Exception as e:
        print(f"   ⚠️  Error extracting metrics for {name}: {e}")
        return {
            'strategy': name,
            'total_return_%': np.nan,
            'sharpe_ratio': np.nan,
            'max_drawdown_%': np.nan,
            'win_rate_%': np.nan,
            'num_trades': 0,
            'final_value': np.nan
        }


def main():
    print("="*80)
    print("FINAL COMPARISON SUITE")
    print("="*80)
    print()
    print("Tests:")
    print("1. 2017-2018 Crash Period (bear market stress test)")
    print("2. Simple 60/40 BTC/ETH Baseline")
    print("3. Simple 35/35/30 BTC/ETH/SOL Baseline")
    print("4. Complex Crypto Hybrid Strategy")
    print("="*80)

    INITIAL_CAPITAL = 100000

    # Crypto universe (minimal for 2017-2018, expanded for 2020+)
    core_cryptos = ['BTC-USD', 'ETH-USD']
    expanded_cryptos = [
        'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
        'ADA-USD', 'AVAX-USD', 'DOGE-USD', 'DOT-USD', 'MATIC-USD',
        'SHIB-USD', 'LTC-USD', 'LINK-USD', 'ATOM-USD', 'PAXG-USD'
    ]

    all_results = []

    # ============================================================================
    # TEST 1: 2017-2018 CRASH PERIOD
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 1: 2017-2018 CRASH PERIOD")
    print(f"{'='*80}\n")

    crash_start = "2017-01-01"
    crash_end = "2018-12-31"

    print(f"Period: {crash_start} to {crash_end}")
    print(f"Context: BTC peaked at $20K (Dec 2017), crashed to $3.2K (Dec 2018)")
    print(f"Expected: -84% for BTC buy-and-hold")

    crash_prices = download_crypto_data(core_cryptos + ['PAXG-USD'], crash_start, crash_end)

    if 'BTC-USD' in crash_prices.columns:
        crash_btc = crash_prices['BTC-USD']

        # Test 60/40
        print(f"\n   Testing 60/40 BTC/ETH...")
        portfolio_6040_crash = test_simple_6040(crash_prices, initial_capital=INITIAL_CAPITAL)
        if portfolio_6040_crash:
            metrics = extract_metrics(portfolio_6040_crash, '60/40 BTC/ETH (2017-2018)')
            all_results.append(metrics)
            print(f"   ✅ 60/40: {metrics['total_return_%']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe, {metrics['max_drawdown_%']:.2f}% MaxDD")

        # Test Complex Strategy (if enough data)
        if len(crash_prices.columns) >= 5:
            print(f"\n   Testing Complex Hybrid Strategy...")
            try:
                strategy = NickRadgeCryptoHybrid(
                    core_allocation=0.70,
                    satellite_allocation=0.30,
                    core_assets=['BTC-USD', 'ETH-USD'],  # SOL didn't exist yet
                    satellite_size=2,  # Smaller universe
                    qualifier_type='tqs',
                    use_momentum_weighting=True,
                    bear_asset='PAXG-USD' if 'PAXG-USD' in crash_prices.columns else 'BTC-USD',
                    regime_hysteresis=0.02
                )

                portfolio_hybrid_crash = strategy.backtest(
                    crash_prices,
                    crash_btc,
                    initial_capital=INITIAL_CAPITAL,
                    fees=0.002,
                    slippage=0.002
                )

                metrics = extract_metrics(portfolio_hybrid_crash, 'Crypto Hybrid (2017-2018)')
                all_results.append(metrics)
                print(f"   ✅ Hybrid: {metrics['total_return_%']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe, {metrics['max_drawdown_%']:.2f}% MaxDD")

            except Exception as e:
                print(f"   ❌ Complex strategy failed: {e}")
        else:
            print(f"   ⚠️  Not enough data for complex strategy (need 5+ assets)")

    # ============================================================================
    # TEST 2: 2020-2025 PERIOD (ALL STRATEGIES)
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"TEST 2: 2020-2025 BULL PERIOD (FULL COMPARISON)")
    print(f"{'='*80}\n")

    bull_start = "2020-01-01"
    bull_end = "2025-10-12"

    print(f"Period: {bull_start} to {bull_end}")
    print(f"Context: Greatest crypto bull run in history")

    bull_prices = download_crypto_data(expanded_cryptos, bull_start, bull_end)

    if 'BTC-USD' in bull_prices.columns:
        bull_btc = bull_prices['BTC-USD']

        # Test 60/40
        print(f"\n   Testing 60/40 BTC/ETH...")
        portfolio_6040_bull = test_simple_6040(bull_prices, initial_capital=INITIAL_CAPITAL)
        if portfolio_6040_bull:
            metrics = extract_metrics(portfolio_6040_bull, '60/40 BTC/ETH (2020-2025)')
            all_results.append(metrics)
            print(f"   ✅ 60/40: {metrics['total_return_%']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe, {metrics['max_drawdown_%']:.2f}% MaxDD")

        # Test 70/30 with SOL
        print(f"\n   Testing 35/35/30 BTC/ETH/SOL...")
        portfolio_703030_bull = test_simple_703030(bull_prices, initial_capital=INITIAL_CAPITAL)
        if portfolio_703030_bull:
            metrics = extract_metrics(portfolio_703030_bull, '35/35/30 BTC/ETH/SOL (2020-2025)')
            all_results.append(metrics)
            print(f"   ✅ 35/35/30: {metrics['total_return_%']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe, {metrics['max_drawdown_%']:.2f}% MaxDD")

        # Test Complex Strategy
        print(f"\n   Testing Complex Hybrid Strategy...")
        try:
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

            portfolio_hybrid_bull = strategy.backtest(
                bull_prices,
                bull_btc,
                initial_capital=INITIAL_CAPITAL,
                fees=0.002,
                slippage=0.002
            )

            metrics = extract_metrics(portfolio_hybrid_bull, 'Crypto Hybrid (2020-2025)')
            all_results.append(metrics)
            print(f"   ✅ Hybrid: {metrics['total_return_%']:.2f}% return, {metrics['sharpe_ratio']:.2f} Sharpe, {metrics['max_drawdown_%']:.2f}% MaxDD")

        except Exception as e:
            print(f"   ❌ Complex strategy failed: {e}")

    # ============================================================================
    # FINAL COMPARISON
    # ============================================================================
    print(f"\n{'='*80}")
    print(f"FINAL COMPARISON")
    print(f"{'='*80}\n")

    results_df = pd.DataFrame(all_results)

    if len(results_df) > 0:
        print(results_df.to_string(index=False))

        # Save results
        output_dir = Path(__file__).parent.parent / 'results' / 'crypto_hybrid' / 'final_comparison'
        output_dir.mkdir(parents=True, exist_ok=True)
        results_df.to_csv(output_dir / 'final_comparison.csv', index=False)
        print(f"\n✅ Results saved to: {output_dir / 'final_comparison.csv'}")

        # Analysis
        print(f"\n{'='*80}")
        print(f"ANALYSIS")
        print(f"{'='*80}\n")

        # 2017-2018 Crash
        crash_results = results_df[results_df['strategy'].str.contains('2017-2018')]
        if len(crash_results) > 0:
            print(f"📉 2017-2018 CRASH PERFORMANCE:")
            for _, row in crash_results.iterrows():
                print(f"   {row['strategy']}: {row['total_return_%']:.2f}% return, {row['max_drawdown_%']:.2f}% MaxDD")

            best_crash = crash_results.loc[crash_results['total_return_%'].idxmax()]
            print(f"   🏆 Best in crash: {best_crash['strategy']}")

        # 2020-2025 Bull
        bull_results = results_df[results_df['strategy'].str.contains('2020-2025')]
        if len(bull_results) > 0:
            print(f"\n📈 2020-2025 BULL PERFORMANCE:")
            for _, row in bull_results.iterrows():
                print(f"   {row['strategy']}: {row['total_return_%']:.2f}% return, {row['sharpe_ratio']:.2f} Sharpe")

            best_bull_return = bull_results.loc[bull_results['total_return_%'].idxmax()]
            best_bull_sharpe = bull_results.loc[bull_results['sharpe_ratio'].idxmax()]
            print(f"   🏆 Best return: {best_bull_return['strategy']} ({best_bull_return['total_return_%']:.2f}%)")
            print(f"   🏆 Best Sharpe: {best_bull_sharpe['strategy']} ({best_bull_sharpe['sharpe_ratio']:.2f})")

        # Recommendation
        print(f"\n{'='*80}")
        print(f"RECOMMENDATION")
        print(f"{'='*80}\n")

        print(f"Based on testing across bear AND bull markets:")

        if len(bull_results) > 0:
            # Find simple strategies
            simple_60_40 = bull_results[bull_results['strategy'].str.contains('60/40')]
            simple_703030 = bull_results[bull_results['strategy'].str.contains('35/35/30')]
            complex_hybrid = bull_results[bull_results['strategy'].str.contains('Hybrid')]

            if len(simple_60_40) > 0 and len(complex_hybrid) > 0:
                simple_return = simple_60_40['total_return_%'].values[0]
                complex_return = complex_hybrid['total_return_%'].values[0]

                if simple_return > complex_return * 0.9:  # Within 10%
                    print(f"\n🎯 RECOMMENDATION: Use Simple 60/40 BTC/ETH")
                    print(f"   - Return: {simple_return:.2f}% vs Complex {complex_return:.2f}%")
                    print(f"   - Much simpler to implement and maintain")
                    print(f"   - Lower risk of errors")
                    print(f"   - Rebalance quarterly")
                else:
                    print(f"\n🎯 RECOMMENDATION: Complex strategy MAY be worth it")
                    print(f"   - Return: {complex_return:.2f}% vs Simple {simple_return:.2f}%")
                    print(f"   - But requires careful monitoring")
                    print(f"   - Test more in paper trading")
    else:
        print(f"❌ No results to display")

    print(f"\n{'='*80}")
    print(f"TESTING COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
