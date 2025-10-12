#!/usr/bin/env python3
"""
Compare Performance Qualifiers for Nick Radge Strategy

Quick test script using existing strategy_factory framework.
Tests ROC vs ATR-based qualifiers on 5-year historical data.

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy, download_sp500_stocks, download_spy
from strategy_factory.performance_qualifiers import (
    get_qualifier,
    ATRNormalizedMomentum,
    BreakoutStrengthScore,
    VolatilityExpansionMomentum,
    TrendQualityScore,
    RiskAdjustedMomentum,
    CompositeScore
)


def test_qualifier_on_nick_radge(qualifier_name: str, prices: pd.DataFrame, spy_prices: pd.Series, initial_capital: float = 10000):
    """
    Test a single qualifier by modifying Nick Radge's rank_stocks method

    Returns:
        Dict with performance metrics
    """
    print(f"\n{'='*80}")
    print(f"Testing: {qualifier_name.upper()}")
    print(f"{'='*80}")

    # Create base strategy
    strategy = NickRadgeMomentumStrategy(
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
        bear_market_asset='GLD',
        bear_allocation=1.0
    )

    # Get the qualifier with proper parameters
    if qualifier_name == 'roc':
        qualifier = None  # Use default ROC
    elif qualifier_name == 'anm':
        qualifier = get_qualifier('anm', momentum_period=100, atr_period=14)
    elif qualifier_name == 'bss':
        qualifier = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)
    elif qualifier_name == 'vem':
        qualifier = get_qualifier('vem', roc_period=100, atr_period=14, atr_avg_period=50)
    elif qualifier_name == 'tqs':
        qualifier = get_qualifier('tqs', ma_period=100, atr_period=14, adx_period=25)
    elif qualifier_name == 'ram':
        qualifier = get_qualifier('ram', roc_period=100, atr_period=14)
    elif qualifier_name == 'composite':
        qualifier = get_qualifier('composite', momentum_period=100, atr_period=14)
    else:
        qualifier = get_qualifier(qualifier_name)

    # Monkey-patch the strategy to use our qualifier
    if qualifier is not None:
        original_rank_stocks = strategy.rank_stocks

        def new_rank_stocks(prices, indicators, date, benchmark_roc=None):
            """Modified rank_stocks using custom qualifier"""
            if date not in prices.index:
                return pd.DataFrame()

            # Calculate scores using the qualifier
            scores = qualifier.calculate(prices)

            if date not in scores.index:
                return pd.DataFrame()

            score_row = scores.loc[date]
            above_ma = indicators['above_ma'].loc[date]

            # Filter: Only stocks above MA and with valid scores
            valid_stocks = above_ma[above_ma == True].index

            # Exclude bear market asset
            if strategy.bear_market_asset:
                valid_stocks = [s for s in valid_stocks if s != strategy.bear_market_asset]

            valid_stocks = [s for s in valid_stocks if pd.notna(score_row[s])]

            if len(valid_stocks) == 0:
                return pd.DataFrame()

            scores_valid = score_row[valid_stocks].dropna()

            if len(scores_valid) == 0:
                return pd.DataFrame()

            # Relative strength filter
            if strategy.use_relative_strength and benchmark_roc is not None and date in benchmark_roc.index:
                benchmark_score = benchmark_roc.loc[date]
                if pd.notna(benchmark_score):
                    scores_valid = scores_valid[scores_valid > benchmark_score]

            if len(scores_valid) == 0:
                return pd.DataFrame()

            # Sort by score (descending)
            ranked = scores_valid.sort_values(ascending=False)

            return pd.DataFrame({
                'ticker': ranked.index,
                'roc': ranked.values  # Keep the key name 'roc' for compatibility
            })

        # Replace the method
        strategy.rank_stocks = new_rank_stocks

    # Run backtest
    try:
        portfolio = strategy.backtest(
            prices=prices,
            spy_prices=spy_prices,
            initial_capital=initial_capital,
            fees=0.001,
            slippage=0.0005
        )

        # Extract metrics
        final_value = portfolio.value().iloc[-1]
        if isinstance(final_value, pd.Series):
            final_value = final_value.sum()

        init_cash = portfolio.init_cash
        if isinstance(init_cash, pd.Series):
            init_cash = init_cash.sum()

        total_return = ((final_value / init_cash) - 1) * 100

        try:
            sharpe = portfolio.sharpe_ratio(freq='D')
            if isinstance(sharpe, pd.Series):
                sharpe = sharpe.mean()
        except:
            sharpe = 0.0

        max_dd = portfolio.max_drawdown()
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.max()

        trades_count = portfolio.trades.count()
        if isinstance(trades_count, pd.Series):
            trades_count = trades_count.sum()

        try:
            win_rate = portfolio.trades.win_rate()
            if isinstance(win_rate, pd.Series):
                win_rate = win_rate.mean()
        except:
            win_rate = 0.0

        try:
            profit_factor = portfolio.trades.profit_factor()
            if isinstance(profit_factor, pd.Series):
                profit_factor = profit_factor.mean()
        except:
            profit_factor = 0.0

        # Calculate annualized return
        days = (prices.index[-1] - prices.index[0]).days
        years = days / 365.25
        annualized_return = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0

        print(f"\n✅ Results:")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Annualized: {annualized_return:.2f}%")
        print(f"   Sharpe: {sharpe:.2f}")
        print(f"   Max DD: {max_dd*100:.2f}%")
        print(f"   Trades: {trades_count}")
        print(f"   Win Rate: {win_rate*100:.1f}%")

        return {
            'Qualifier': qualifier_name.upper(),
            'Total Return %': total_return,
            'Annualized %': annualized_return,
            'Sharpe Ratio': sharpe,
            'Max Drawdown %': max_dd * 100,
            'Trades': trades_count,
            'Win Rate %': win_rate * 100,
            'Profit Factor': profit_factor,
            'Final Value': final_value
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("="*80)
    print("NICK RADGE STRATEGY - PERFORMANCE QUALIFIER COMPARISON")
    print("="*80)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000
    NUM_STOCKS = 50

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE} (~5 years)")
    print(f"   Universe: {NUM_STOCKS} S&P 500 stocks + GLD")
    print(f"   Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Portfolio: 7 stocks (quarterly rebalance)")
    print(f"   Bear Asset: GLD (100%)")

    # Download data
    print(f"\n{'='*80}")
    print("DOWNLOADING DATA")
    print("="*80)

    prices = download_sp500_stocks(num_stocks=NUM_STOCKS, start_date=START_DATE, end_date=END_DATE)

    # CRITICAL: Add GLD for bear market allocation
    if 'GLD' not in prices.columns:
        print(f"\n⚠️  GLD not in dataset - downloading separately...")
        import yfinance as yf
        gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
        if isinstance(gld_data.columns, pd.MultiIndex):
            gld_data.columns = gld_data.columns.get_level_values(0)
        prices['GLD'] = gld_data['Close']
        prices = prices.dropna()  # Align dates
        print(f"✅ GLD added to dataset")

    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align dates
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready: {len(prices)} days, {len(prices.columns)} stocks")

    # SPY benchmark
    spy_return = ((spy_prices.iloc[-1] / spy_prices.iloc[0]) - 1) * 100

    # Test qualifiers
    qualifiers = [
        'roc',       # Baseline (original)
        'anm',       # ATR-Normalized Momentum
        'bss',       # Breakout Strength Score
        'vem',       # Volatility Expansion Momentum
        'tqs',       # Trend Quality Score
        'ram',       # Risk-Adjusted Momentum
        'composite'  # Weighted combination
    ]

    print(f"\n{'='*80}")
    print("RUNNING BACKTESTS")
    print("="*80)

    results = []
    for q in qualifiers:
        result = test_qualifier_on_nick_radge(q, prices, spy_prices, INITIAL_CAPITAL)
        if result:
            results.append(result)

    # Create comparison table
    comparison_df = pd.DataFrame(results)

    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON")
    print("="*80)

    print("\n" + comparison_df.to_string(index=False))

    print(f"\n{'='*80}")
    print("WINNERS")
    print("="*80)

    best_return = comparison_df.loc[comparison_df['Total Return %'].idxmax()]
    best_sharpe = comparison_df.loc[comparison_df['Sharpe Ratio'].idxmax()]
    best_drawdown = comparison_df.loc[comparison_df['Max Drawdown %'].idxmin()]

    print(f"\n🏆 Best Return: {best_return['Qualifier']} ({best_return['Total Return %']:.2f}%)")
    print(f"🏆 Best Sharpe: {best_sharpe['Qualifier']} ({best_sharpe['Sharpe Ratio']:.2f})")
    print(f"🏆 Best Drawdown: {best_drawdown['Qualifier']} ({best_drawdown['Max Drawdown %']:.2f}%)")

    print(f"\n📊 SPY Buy-Hold: {spy_return:.2f}%")

    # Save results
    output_file = 'results/qualifier_comparison.csv'
    Path('results').mkdir(exist_ok=True)
    comparison_df.to_csv(output_file, index=False)
    print(f"\n💾 Saved: {output_file}")

    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)
