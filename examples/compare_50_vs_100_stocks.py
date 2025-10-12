#!/usr/bin/env python3
"""
Compare 50-Stock Universe vs 100-Stock Universe

Analyzes:
1. Performance difference (50 vs 100 stocks)
2. Which stocks were missed with only 50 stocks
3. Top performers that ranked 51-100
4. Whether expanding universe improves returns

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_momentum_strategy import download_spy
from examples.compare_qualifiers import test_qualifier_on_nick_radge


def download_sp500_stocks_100(num_stocks: int = 100, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Download top 100 S&P 500 stocks by market cap

    Args:
        num_stocks: Number of stocks to download (default: 100)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        DataFrame with close prices (columns = tickers)
    """
    # Top 100 S&P 500 stocks by market cap (approximate)
    tickers = [
        # Mega Cap Tech (Top 10)
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'ORCL', 'ADBE',

        # Large Cap Tech (11-30)
        'CRM', 'AMD', 'INTC', 'CSCO', 'QCOM', 'INTU', 'NOW', 'AMAT', 'MU', 'PLTR',
        'PANW', 'SNPS', 'CDNS', 'MRVL', 'ADSK', 'FTNT', 'ABNB', 'TEAM', 'DDOG', 'SNOW',

        # Financials (31-50)
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'C', 'SCHW', 'AXP', 'SPGI',
        'CB', 'PGR', 'MMC', 'ICE', 'CME', 'AON', 'TFC', 'USB', 'PNC', 'COF',

        # Healthcare (51-70)
        'UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'TMO', 'ABT', 'PFE', 'DHR', 'AMGN',
        'BMY', 'GILD', 'VRTX', 'CI', 'CVS', 'ELV', 'REGN', 'ISRG', 'ZTS', 'HCA',

        # Consumer (71-90)
        'WMT', 'HD', 'MCD', 'NKE', 'COST', 'SBUX', 'TGT', 'LOW', 'DIS', 'CMCSA',
        'PG', 'KO', 'PEP', 'PM', 'UL', 'CL', 'MDLZ', 'MNST', 'KHC', 'GIS',

        # Industrials & Energy (91-100)
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL'
    ][:num_stocks]

    print(f"📥 Downloading {len(tickers)} stocks...")
    print(f"   Period: {start_date} to {end_date}")

    # Download data
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)

    # Extract close prices
    if len(tickers) == 1:
        prices = data['Close'].to_frame()
        prices.columns = tickers
    else:
        prices = data['Close']

    # Remove any stocks with insufficient data
    prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)

    print(f"✅ Downloaded {len(prices.columns)} stocks with sufficient data")

    return prices


def analyze_missed_opportunities(prices_50, prices_100, spy_prices, analysis_dates):
    """
    Analyze which stocks ranked 51-100 and their performance

    Args:
        prices_50: 50-stock universe prices
        prices_100: 100-stock universe prices
        spy_prices: SPY prices for regime
        analysis_dates: List of dates to analyze

    Returns:
        DataFrame with missed opportunities analysis
    """
    from strategy_factory.performance_qualifiers import get_qualifier

    print(f"\n{'='*100}")
    print("ANALYZING MISSED OPPORTUNITIES (Stocks Ranked 51-100)")
    print("="*100)

    # Get BSS qualifier
    bss = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)

    # Stocks in 100 but not in 50
    stocks_51_100 = [s for s in prices_100.columns if s not in prices_50.columns and s != 'GLD']

    print(f"\n📊 Stocks in extended universe (51-100): {len(stocks_51_100)}")
    print(f"   {', '.join(sorted(stocks_51_100)[:20])}...")

    missed_opportunities = []

    for date in analysis_dates:
        if date not in prices_100.index:
            continue

        print(f"\n{'─'*100}")
        print(f"Date: {date.date()}")

        # Calculate BSS for all 100 stocks
        bss_scores = bss.calculate(prices_100)

        if date not in bss_scores.index:
            continue

        scores_at_date = bss_scores.loc[date]

        # Calculate MA
        ma100 = prices_100.rolling(window=100).mean()
        above_ma = prices_100 > ma100
        above_ma_at_date = above_ma.loc[date]

        # Filter valid stocks
        valid_stocks = above_ma_at_date[above_ma_at_date == True].index
        valid_stocks = [s for s in valid_stocks if s != 'GLD' and pd.notna(scores_at_date[s])]

        # Get scores and rank
        scores_valid = scores_at_date[valid_stocks].dropna()
        ranked = scores_valid.sort_values(ascending=False)

        # Top 7 from full 100-stock universe
        top7_full = ranked.head(7)

        # Top 7 from 50-stock universe only
        stocks_in_50 = [s for s in valid_stocks if s in prices_50.columns]
        scores_50_only = scores_at_date[stocks_in_50].dropna()
        ranked_50 = scores_50_only.sort_values(ascending=False)
        top7_limited = ranked_50.head(7)

        # Find stocks that would rank in top 7 if we had 100 stocks
        missed = []
        for stock in top7_full.index:
            if stock not in top7_limited.index:
                rank_in_full = list(ranked.index).index(stock) + 1
                score = top7_full[stock]
                missed.append({
                    'date': date,
                    'ticker': stock,
                    'bss_score': score,
                    'rank_in_100': rank_in_full,
                    'in_50_universe': stock in prices_50.columns
                })

        if missed:
            print(f"\n   🎯 Missed stocks (would be in top 7 with 100-stock universe):")
            for m in missed:
                universe_status = "In 50 (but ranked lower)" if m['in_50_universe'] else "NOT in 50 ❌"
                print(f"      {m['ticker']:6} - BSS: {m['bss_score']:5.2f}, Rank: #{m['rank_in_100']} ({universe_status})")
        else:
            print(f"\n   ✅ No stocks missed - top 7 same in both universes")

        # Show top 7 comparison
        print(f"\n   Top 7 with 50 stocks:  {', '.join(top7_limited.index)}")
        print(f"   Top 7 with 100 stocks: {', '.join(top7_full.index)}")

        missed_opportunities.extend(missed)

    if missed_opportunities:
        missed_df = pd.DataFrame(missed_opportunities)

        # Frequency analysis
        print(f"\n{'='*100}")
        print("MOST FREQUENTLY MISSED STOCKS")
        print("="*100)

        freq = missed_df['ticker'].value_counts()
        print(f"\n📊 Stocks that would have ranked in top 7:")
        for ticker, count in freq.head(10).items():
            in_50 = "Yes" if ticker in prices_50.columns else "No"
            print(f"   {ticker:6} - {count} times (In 50-stock universe: {in_50})")

        return missed_df
    else:
        print(f"\n✅ No missed opportunities - 50-stock universe captured all top performers")
        return pd.DataFrame()


if __name__ == "__main__":
    print("="*100)
    print("50-STOCK vs 100-STOCK UNIVERSE COMPARISON")
    print("="*100)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    INITIAL_CAPITAL = 10000

    print(f"\n⚙️  Configuration:")
    print(f"   Period: {START_DATE} to {END_DATE}")
    print(f"   Capital: ${INITIAL_CAPITAL:,}")
    print(f"   Test 1: 50-stock universe")
    print(f"   Test 2: 100-stock universe")

    # Download both universes
    print(f"\n{'='*100}")
    print("DOWNLOADING DATA")
    print("="*100)

    print("\n📊 Downloading 50-stock universe...")
    from strategies.nick_radge_momentum_strategy import download_sp500_stocks
    prices_50 = download_sp500_stocks(num_stocks=50, start_date=START_DATE, end_date=END_DATE)

    print("\n📊 Downloading 100-stock universe...")
    prices_100 = download_sp500_stocks_100(num_stocks=100, start_date=START_DATE, end_date=END_DATE)

    # Add GLD to both
    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    for prices_df, label in [(prices_50, '50'), (prices_100, '100')]:
        if 'GLD' not in prices_df.columns:
            print(f"\n⚠️  Adding GLD to {label}-stock universe...")
            gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
            if isinstance(gld_data.columns, pd.MultiIndex):
                gld_data.columns = gld_data.columns.get_level_values(0)
            prices_df['GLD'] = gld_data['Close']
            prices_df.dropna(inplace=True)

    # Align dates
    common_dates = prices_50.index.intersection(prices_100.index).intersection(spy_prices.index)
    prices_50 = prices_50.loc[common_dates]
    prices_100 = prices_100.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready:")
    print(f"   50-stock universe: {len(prices_50.columns)} stocks")
    print(f"   100-stock universe: {len(prices_100.columns)} stocks")
    print(f"   Common dates: {len(common_dates)} days")

    # Stocks in 100 but not in 50
    additional_stocks = [s for s in prices_100.columns if s not in prices_50.columns]
    print(f"\n📋 Additional stocks in 100-stock universe: {len(additional_stocks)}")
    print(f"   {', '.join(sorted(additional_stocks)[:30])}")
    if len(additional_stocks) > 30:
        print(f"   ... and {len(additional_stocks) - 30} more")

    # Run backtests
    print(f"\n{'='*100}")
    print("RUNNING BACKTESTS")
    print("="*100)

    results = []

    print(f"\n{'='*100}")
    print("1. BSS with 50-STOCK UNIVERSE")
    print("="*100)
    result_50 = test_qualifier_on_nick_radge('bss', prices_50, spy_prices, INITIAL_CAPITAL)
    if result_50:
        result_50['Universe'] = '50 stocks'
        results.append(result_50)

    print(f"\n{'='*100}")
    print("2. BSS with 100-STOCK UNIVERSE")
    print("="*100)
    result_100 = test_qualifier_on_nick_radge('bss', prices_100, spy_prices, INITIAL_CAPITAL)
    if result_100:
        result_100['Universe'] = '100 stocks'
        results.append(result_100)

    # Comparison
    comparison_df = pd.DataFrame(results)

    print(f"\n{'='*100}")
    print("PERFORMANCE COMPARISON")
    print("="*100)

    print("\n" + comparison_df[['Universe', 'Total Return %', 'Annualized %', 'Sharpe Ratio',
                                  'Max Drawdown %', 'Trades', 'Win Rate %', 'Profit Factor']].to_string(index=False))

    # Calculate difference
    if len(results) == 2:
        diff_return = result_100['Total Return %'] - result_50['Total Return %']
        diff_sharpe = result_100['Sharpe Ratio'] - result_50['Sharpe Ratio']
        diff_dd = result_100['Max Drawdown %'] - result_50['Max Drawdown %']

        print(f"\n{'='*100}")
        print("IMPACT OF EXPANDING UNIVERSE")
        print("="*100)

        print(f"\n📊 Performance Differences (100 stocks - 50 stocks):")
        print(f"   Total Return: {diff_return:+.2f}%")
        print(f"   Sharpe Ratio: {diff_sharpe:+.2f}")
        print(f"   Max Drawdown: {diff_dd:+.2f}%")
        print(f"   Trade Count: {result_100['Trades'] - result_50['Trades']:+.0f}")

        if diff_return > 5:
            print(f"\n   ✅ SIGNIFICANT IMPROVEMENT with 100 stocks!")
            print(f"      Expanding universe added {diff_return:.2f}% returns")
        elif diff_return > 0:
            print(f"\n   ✓ Modest improvement with 100 stocks")
            print(f"      Expanding universe added {diff_return:.2f}% returns")
        else:
            print(f"\n   ✗ No improvement with 100 stocks")
            print(f"      50-stock universe was sufficient")

    # Missed opportunities analysis
    rebalance_dates = pd.date_range(start=prices_100.index[0], end=prices_100.index[-1], freq='QS')
    actual_dates = []
    for ideal_date in rebalance_dates:
        idx = prices_100.index.searchsorted(ideal_date)
        if idx < len(prices_100.index):
            actual_dates.append(prices_100.index[idx])

    min_date = prices_100.index[0] + pd.Timedelta(days=100)
    analysis_dates = [d for d in actual_dates if d >= min_date][-5:]  # Last 5 rebalances

    missed_df = analyze_missed_opportunities(prices_50, prices_100, spy_prices, analysis_dates)

    # Save results
    comparison_df.to_csv('results/50_vs_100_comparison.csv', index=False)
    if len(missed_df) > 0:
        missed_df.to_csv('results/missed_opportunities_51_100.csv', index=False)
        print(f"\n💾 Saved: results/missed_opportunities_51_100.csv")

    print(f"\n💾 Saved: results/50_vs_100_comparison.csv")

    print(f"\n{'='*100}")
    print("CONCLUSION")
    print("="*100)

    if len(results) == 2:
        if diff_return > 5:
            print(f"\n✅ RECOMMENDATION: Use 100-stock universe")
            print(f"   - {diff_return:+.2f}% better returns")
            print(f"   - Access to stocks ranked 51-100")
            print(f"   - More diversification opportunities")
        elif diff_return > 0:
            print(f"\n~ RECOMMENDATION: Consider 100-stock universe")
            print(f"   - Marginal improvement ({diff_return:+.2f}%)")
            print(f"   - Slightly more opportunity")
            print(f"   - 50 stocks may be sufficient")
        else:
            print(f"\n✓ RECOMMENDATION: 50-stock universe is sufficient")
            print(f"   - No meaningful improvement with 100 stocks")
            print(f"   - Simpler to manage")
            print(f"   - Lower data/trading costs")

    print(f"\n{'='*100}")
    print("✅ ANALYSIS COMPLETE")
    print("="*100)
