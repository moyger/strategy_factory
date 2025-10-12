#!/usr/bin/env python3
"""
Example: Nick Radge Momentum Strategy with Backtest Framework & Monte Carlo

This demonstrates:
1. Running the Nick Radge momentum strategy
2. Using the Strategy Factory backtest framework
3. Monte Carlo simulation
4. QuantStats report generation

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import Nick Radge strategy
from strategies.nick_radge_momentum_strategy import (
    NickRadgeMomentumStrategy,
    download_sp500_stocks,
    download_spy
)

# Import framework components
from strategy_factory.analyzer import StrategyAnalyzer


def run_monte_carlo_simulation(returns, num_simulations=1000, num_days=252):
    """
    Run Monte Carlo simulation on strategy returns

    Args:
        returns: Series of returns
        num_simulations: Number of simulation runs
        num_days: Number of days to simulate

    Returns:
        DataFrame with simulation results
    """
    print(f"\n🎲 Running Monte Carlo Simulation...")
    print(f"   Simulations: {num_simulations}")
    print(f"   Days per simulation: {num_days}")

    # Calculate return statistics
    mean_return = returns.mean()
    std_return = returns.std()

    # Run simulations
    simulations = []

    for i in range(num_simulations):
        # Generate random returns based on historical distribution
        sim_returns = np.random.normal(mean_return, std_return, num_days)

        # Calculate cumulative return
        cum_return = (1 + sim_returns).cumprod()[-1] - 1

        simulations.append({
            'simulation': i + 1,
            'final_return': cum_return * 100,
            'final_value': 10000 * (1 + cum_return)
        })

    sim_df = pd.DataFrame(simulations)

    # Calculate statistics
    print(f"\n📊 Monte Carlo Results ({num_days} days):")
    print(f"   Mean Return: {sim_df['final_return'].mean():.2f}%")
    print(f"   Median Return: {sim_df['final_return'].median():.2f}%")
    print(f"   Std Dev: {sim_df['final_return'].std():.2f}%")
    print(f"   Best Case (95th %ile): {sim_df['final_return'].quantile(0.95):.2f}%")
    print(f"   Worst Case (5th %ile): {sim_df['final_return'].quantile(0.05):.2f}%")
    print(f"   Probability of profit: {(sim_df['final_return'] > 0).mean() * 100:.1f}%")

    return sim_df


def main():
    print("="*80)
    print("NICK RADGE MOMENTUM STRATEGY - BACKTEST FRAMEWORK TEST")
    print("="*80)

    # ========================================
    # STEP 1: CONFIGURATION
    # ========================================
    print("\n⚙️  Step 1: Configuration")

    # Add 200 extra days for warmup period (need 100 days for ROC calculation)
    WARMUP_DAYS = 200
    START_DATE_WITH_WARMUP = (datetime.now() - timedelta(days=365*5 + WARMUP_DAYS)).strftime('%Y-%m-%d')
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000  # $10k starting capital
    NUM_STOCKS = 50

    print(f"   Backtest Period: {START_DATE} to {END_DATE}")
    print(f"   Warmup Period: {START_DATE_WITH_WARMUP} to {START_DATE}")
    print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Universe: Top {NUM_STOCKS} S&P 500 stocks")

    # ========================================
    # STEP 2: DOWNLOAD DATA
    # ========================================
    print(f"\n📥 Step 2: Downloading Data (including warmup period)")

    # Download with warmup period
    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE_WITH_WARMUP, end_date=END_DATE)
    spy_prices = download_spy(start_date=START_DATE_WITH_WARMUP, end_date=END_DATE)

    # Align dates
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Data ready: {len(prices)} days, {len(prices.columns)} stocks")
    print(f"   (includes {WARMUP_DAYS}-day warmup period for indicator calculation)")

    # ========================================
    # STEP 3: CREATE & RUN STRATEGY (Original)
    # ========================================
    print(f"\n📊 Step 3: Running Nick Radge Momentum Strategy (Original - No Bear Trading)")

    strategy = NickRadgeMomentumStrategy(
        portfolio_size=7,
        roc_period=100,
        ma_period=100,
        rebalance_freq='QS',  # Quarterly
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        strong_bull_positions=7,
        weak_bull_positions=3,
        bear_positions=0,
        bear_market_asset=None  # No bear trading
    )

    # Run backtest
    portfolio = strategy.backtest(
        prices=prices,
        spy_prices=spy_prices,
        initial_capital=INITIAL_CAPITAL,
        fees=0.001,
        slippage=0.0005
    )

    # Calculate SPY return for comparison
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Print results
    strategy.print_results(portfolio, prices, spy_return)

    # Store original results
    original_final_value = portfolio.value().iloc[-1]
    if isinstance(original_final_value, pd.Series):
        original_final_value = original_final_value.sum()
    original_return = ((original_final_value / INITIAL_CAPITAL) - 1) * 100

    # ========================================
    # STEP 3B: TEST WITH BEAR MARKET TRADING
    # ========================================
    print(f"\n" + "="*80)
    print("TESTING WITH BEAR MARKET INVERSE ETF")
    print("="*80)

    # Download SQQQ for bear market trading
    print(f"\n📥 Downloading SQQQ (3x inverse NASDAQ)...")
    import yfinance as yf
    sqqq_data = yf.download('SQQQ', start=START_DATE_WITH_WARMUP, end=END_DATE, auto_adjust=True, progress=False)
    sqqq_prices = sqqq_data['Close']

    # Add SQQQ to prices DataFrame
    prices_with_sqqq = prices.copy()
    prices_with_sqqq['SQQQ'] = sqqq_prices

    # Align dates
    common_dates = prices_with_sqqq.index.intersection(spy_prices.index)
    prices_with_sqqq = prices_with_sqqq.loc[common_dates]
    spy_prices_aligned = spy_prices.loc[common_dates]

    print(f"✅ SQQQ data added ({len(sqqq_prices)} days)")

    # Create strategy with bear market asset
    print(f"\n📊 Running strategy WITH bear market trading...")

    strategy_with_bear = NickRadgeMomentumStrategy(
        portfolio_size=7,
        roc_period=100,
        ma_period=100,
        rebalance_freq='QS',
        use_momentum_weighting=True,
        use_regime_filter=True,
        use_relative_strength=True,
        strong_bull_positions=7,
        weak_bull_positions=3,
        bear_positions=0,
        bear_market_asset='SQQQ',  # Trade SQQQ during BEAR
        bear_allocation=1.0  # 100% allocation
    )

    # Run backtest with SQQQ
    portfolio_with_bear = strategy_with_bear.backtest(
        prices=prices_with_sqqq,
        spy_prices=spy_prices_aligned,
        initial_capital=INITIAL_CAPITAL,
        fees=0.001,
        slippage=0.0005
    )

    # Print results
    strategy_with_bear.print_results(portfolio_with_bear, prices_with_sqqq, spy_return)

    # Store bear trading results
    bear_final_value = portfolio_with_bear.value().iloc[-1]
    if isinstance(bear_final_value, pd.Series):
        bear_final_value = bear_final_value.sum()
    bear_return = ((bear_final_value / INITIAL_CAPITAL) - 1) * 100

    # ========================================
    # STEP 3C: COMPARISON
    # ========================================
    print(f"\n" + "="*80)
    print("STRATEGY COMPARISON")
    print("="*80)

    print(f"\n📊 Original Strategy (Cash during BEAR):")
    print(f"   Total Return: {original_return:.2f}%")
    print(f"   Final Value: ${original_final_value:,.2f}")

    print(f"\n📊 Enhanced Strategy (SQQQ during BEAR):")
    print(f"   Total Return: {bear_return:.2f}%")
    print(f"   Final Value: ${bear_final_value:,.2f}")

    print(f"\n📈 Improvement:")
    improvement = bear_return - original_return
    improvement_pct = (improvement / abs(original_return)) * 100 if original_return != 0 else 0
    print(f"   Additional Return: {improvement:+.2f}%")
    print(f"   Relative Improvement: {improvement_pct:+.1f}%")

    if improvement > 0:
        print(f"   Status: ✅ Bear trading IMPROVED returns")
    else:
        print(f"   Status: ❌ Bear trading REDUCED returns")

    # Use portfolio WITH bear trading for remaining analysis
    portfolio = portfolio_with_bear

    # ========================================
    # STEP 4: GENERATE QUANTSTATS REPORT
    # ========================================
    print(f"\n📈 Step 4: Generating QuantStats Report")

    analyzer = StrategyAnalyzer()

    # Get portfolio returns
    returns = portfolio.returns()
    if isinstance(returns, pd.DataFrame):
        # Sum across all positions for multi-asset
        returns = returns.sum(axis=1)

    # Generate full QuantStats report
    report_path = analyzer.generate_full_report(
        returns,
        output_file='nick_radge_momentum_report.html',
        title='Nick Radge Momentum Strategy - Performance Report',
        benchmark=spy_prices.pct_change().dropna()  # SPY as benchmark
    )

    print(f"\n✅ QuantStats report generated: {report_path}")

    # ========================================
    # STEP 5: MONTE CARLO SIMULATION
    # ========================================
    print(f"\n🎲 Step 5: Monte Carlo Simulation")

    # Run simulations for 1 year (252 trading days)
    sim_1year = run_monte_carlo_simulation(returns, num_simulations=1000, num_days=252)

    # Run simulations for 5 years
    sim_5year = run_monte_carlo_simulation(returns, num_simulations=1000, num_days=252*5)

    # ========================================
    # STEP 6: RISK ANALYSIS
    # ========================================
    print(f"\n⚠️  Step 6: Risk Analysis")

    # Calculate risk metrics
    daily_returns = returns

    # Value at Risk (VaR)
    var_95 = daily_returns.quantile(0.05)
    var_99 = daily_returns.quantile(0.01)

    # Conditional Value at Risk (CVaR)
    cvar_95 = daily_returns[daily_returns <= var_95].mean()
    cvar_99 = daily_returns[daily_returns <= var_99].mean()

    # Maximum consecutive losses
    def max_consecutive_losses(returns):
        losses = (returns < 0).astype(int)
        consecutive = []
        count = 0
        for loss in losses:
            if loss:
                count += 1
            else:
                if count > 0:
                    consecutive.append(count)
                count = 0
        if count > 0:
            consecutive.append(count)
        return max(consecutive) if consecutive else 0

    max_losing_streak = max_consecutive_losses(daily_returns)

    print(f"\n📊 Risk Metrics:")
    print(f"   Value at Risk (95%): {var_95 * 100:.2f}%")
    print(f"   Value at Risk (99%): {var_99 * 100:.2f}%")
    print(f"   CVaR (95%): {cvar_95 * 100:.2f}%")
    print(f"   CVaR (99%): {cvar_99 * 100:.2f}%")
    print(f"   Max Consecutive Losing Days: {max_losing_streak}")

    # ========================================
    # STEP 7: SUMMARY
    # ========================================
    print(f"\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    # Get final metrics
    final_value = portfolio.value().iloc[-1]
    if isinstance(final_value, pd.Series):
        final_value = final_value.sum()

    init_cash = portfolio.init_cash
    if isinstance(init_cash, pd.Series):
        init_cash = init_cash.sum()

    total_return = ((final_value / init_cash) - 1) * 100

    print(f"\n✅ Backtest Complete!")
    print(f"\n📊 Performance:")
    print(f"   Initial Capital: ${init_cash:,.2f}")
    print(f"   Final Value: ${final_value:,.2f}")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   SPY Return: {spy_return:.2f}%")
    print(f"   Outperformance: {total_return - spy_return:+.2f}%")

    print(f"\n🎲 Monte Carlo (1 Year):")
    print(f"   Expected Return: {sim_1year['final_return'].mean():.2f}%")
    print(f"   Best Case: {sim_1year['final_return'].quantile(0.95):.2f}%")
    print(f"   Worst Case: {sim_1year['final_return'].quantile(0.05):.2f}%")

    print(f"\n🎲 Monte Carlo (5 Years):")
    print(f"   Expected Return: {sim_5year['final_return'].mean():.2f}%")
    print(f"   Best Case: {sim_5year['final_return'].quantile(0.95):.2f}%")
    print(f"   Worst Case: {sim_5year['final_return'].quantile(0.05):.2f}%")

    print(f"\n📈 QuantStats Report: {report_path}")
    print(f"\n✅ All tests completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
