#!/usr/bin/env python3
"""
Analyze Top Stocks Selected by BSS vs ROC

Shows which stocks qualify for each ranking method and why.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf

from strategies.nick_radge_momentum_strategy import download_sp500_stocks, download_spy
from strategy_factory.performance_qualifiers import get_qualifier


def analyze_stock_selection(prices, spy_prices, analysis_date=None):
    """
    Compare stock selection between ROC and BSS at a specific date
    """
    if analysis_date is None:
        analysis_date = prices.index[-1]

    print(f"\n{'='*80}")
    print(f"STOCK SELECTION ANALYSIS - {analysis_date.date()}")
    print(f"{'='*80}")

    # Calculate indicators
    ma100 = prices.rolling(window=100).mean()
    above_ma = prices > ma100

    # ROC qualifier
    roc_qualifier = get_qualifier('roc', roc_period=100)
    roc_scores = roc_qualifier.calculate(prices)

    # BSS qualifier
    bss_qualifier = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)
    bss_scores = bss_qualifier.calculate(prices)

    # Get scores at analysis date
    if analysis_date not in roc_scores.index:
        print(f"⚠️  Date {analysis_date} not in dataset")
        return

    roc_at_date = roc_scores.loc[analysis_date]
    bss_at_date = bss_scores.loc[analysis_date]
    above_ma_at_date = above_ma.loc[analysis_date]
    prices_at_date = prices.loc[analysis_date]
    ma_at_date = ma100.loc[analysis_date]

    # Filter valid stocks (above MA, not GLD)
    valid_stocks = above_ma_at_date[above_ma_at_date == True].index
    valid_stocks = [s for s in valid_stocks if s != 'GLD']
    valid_stocks = [s for s in valid_stocks if pd.notna(roc_at_date[s]) and pd.notna(bss_at_date[s])]

    # Create comparison dataframe
    comparison = pd.DataFrame({
        'Price': prices_at_date[valid_stocks],
        'MA100': ma_at_date[valid_stocks],
        'Distance_from_MA': ((prices_at_date[valid_stocks] - ma_at_date[valid_stocks]) / ma_at_date[valid_stocks] * 100),
        'ROC_Score': roc_at_date[valid_stocks],
        'BSS_Score': bss_at_date[valid_stocks]
    })

    # Add rankings
    comparison['ROC_Rank'] = comparison['ROC_Score'].rank(ascending=False)
    comparison['BSS_Rank'] = comparison['BSS_Score'].rank(ascending=False)

    # Sort by BSS score
    comparison = comparison.sort_values('BSS_Score', ascending=False)

    # Top 7 by each method
    roc_top7 = comparison.nsmallest(7, 'ROC_Rank').index.tolist()
    bss_top7 = comparison.nsmallest(7, 'BSS_Rank').index.tolist()

    print(f"\n📊 Valid Stocks (Above MA100, excl. GLD): {len(valid_stocks)}")

    # Show top 7 by BSS
    print(f"\n{'='*80}")
    print("🏆 TOP 7 STOCKS BY BSS (BREAKOUT STRENGTH SCORE)")
    print(f"{'='*80}")
    print("\nTicker  Price    MA100   % Above  ROC     BSS    ROC    BSS")
    print("                         MA       Score   Score  Rank   Rank")
    print("-" * 80)

    top7_bss = comparison.head(7)
    for ticker, row in top7_bss.iterrows():
        roc_flag = "✓" if ticker in roc_top7 else " "
        print(f"{ticker:6} ${row['Price']:6.2f} ${row['MA100']:6.2f}  {row['Distance_from_MA']:5.1f}%  "
              f"{row['ROC_Score']:5.1f}  {row['BSS_Score']:5.2f}  {row['ROC_Rank']:4.0f}  {row['BSS_Rank']:4.0f} {roc_flag}")

    # Show top 7 by ROC
    print(f"\n{'='*80}")
    print("📈 TOP 7 STOCKS BY ROC (RATE OF CHANGE)")
    print(f"{'='*80}")
    print("\nTicker  Price    MA100   % Above  ROC     BSS    ROC    BSS")
    print("                         MA       Score   Score  Rank   Rank")
    print("-" * 80)

    top7_roc = comparison.nsmallest(7, 'ROC_Rank')
    for ticker, row in top7_roc.iterrows():
        bss_flag = "✓" if ticker in bss_top7 else " "
        print(f"{ticker:6} ${row['Price']:6.2f} ${row['MA100']:6.2f}  {row['Distance_from_MA']:5.1f}%  "
              f"{row['ROC_Score']:5.1f}  {row['BSS_Score']:5.2f}  {row['ROC_Rank']:4.0f}  {row['BSS_Rank']:4.0f} {bss_flag}")

    # Show overlap
    overlap = set(roc_top7).intersection(set(bss_top7))
    bss_only = set(bss_top7) - set(roc_top7)
    roc_only = set(roc_top7) - set(bss_top7)

    print(f"\n{'='*80}")
    print("🔍 SELECTION COMPARISON")
    print(f"{'='*80}")
    print(f"\n✅ Both methods selected: {len(overlap)} stocks")
    if overlap:
        print(f"   {', '.join(sorted(overlap))}")

    print(f"\n🆕 BSS only (not ROC): {len(bss_only)} stocks")
    if bss_only:
        print(f"   {', '.join(sorted(bss_only))}")
        print("\n   Why BSS selected these:")
        for ticker in sorted(bss_only):
            row = comparison.loc[ticker]
            print(f"   {ticker}: High conviction breakout (BSS={row['BSS_Score']:.2f}, "
                  f"but ROC rank #{int(row['ROC_Rank'])})")

    print(f"\n📊 ROC only (not BSS): {len(roc_only)} stocks")
    if roc_only:
        print(f"   {', '.join(sorted(roc_only))}")
        print("\n   Why BSS rejected these:")
        for ticker in sorted(roc_only):
            row = comparison.loc[ticker]
            print(f"   {ticker}: High ROC but low conviction (ROC={row['ROC_Score']:.1f}, "
                  f"BSS rank #{int(row['BSS_Rank'])})")

    # Calculate ATR for detailed analysis
    from strategy_factory.performance_qualifiers import calculate_atr
    atr = calculate_atr(prices, period=14)
    atr_at_date = atr.loc[analysis_date]
    atr_pct = (atr_at_date / prices_at_date * 100)

    # Detailed comparison for top stocks
    print(f"\n{'='*80}")
    print("🔬 DETAILED ANALYSIS - WHY BSS PICKS DIFFERENT STOCKS")
    print(f"{'='*80}")

    print("\nBSS Formula: (Price - MA100) / (2.0 × ATR)")
    print("High BSS = Strong move relative to volatility (conviction)")

    if len(bss_only) > 0:
        print(f"\n📌 Example: Why BSS picked {list(bss_only)[0]} but ROC didn't:")
        ticker = list(bss_only)[0]
        row = comparison.loc[ticker]

        print(f"\n   {ticker}:")
        print(f"   - Price: ${row['Price']:.2f}")
        print(f"   - MA100: ${row['MA100']:.2f}")
        print(f"   - Distance from MA: {row['Distance_from_MA']:.1f}%")
        print(f"   - ATR: ${atr_at_date[ticker]:.2f} ({atr_pct[ticker]:.1f}% of price)")
        print(f"   - ROC: {row['ROC_Score']:.1f}% (Rank #{int(row['ROC_Rank'])})")
        print(f"   - BSS: {row['BSS_Score']:.2f} (Rank #{int(row['BSS_Rank'])})")
        print(f"\n   ✓ Low ATR relative to price movement = HIGH CONVICTION")
        print(f"     Stock moved {row['Distance_from_MA']:.1f}% above MA with only {atr_pct[ticker]:.1f}% volatility")

    if len(roc_only) > 0:
        print(f"\n📌 Example: Why ROC picked {list(roc_only)[0]} but BSS didn't:")
        ticker = list(roc_only)[0]
        row = comparison.loc[ticker]

        print(f"\n   {ticker}:")
        print(f"   - Price: ${row['Price']:.2f}")
        print(f"   - MA100: ${row['MA100']:.2f}")
        print(f"   - Distance from MA: {row['Distance_from_MA']:.1f}%")
        print(f"   - ATR: ${atr_at_date[ticker]:.2f} ({atr_pct[ticker]:.1f}% of price)")
        print(f"   - ROC: {row['ROC_Score']:.1f}% (Rank #{int(row['ROC_Rank'])})")
        print(f"   - BSS: {row['BSS_Score']:.2f} (Rank #{int(row['BSS_Rank'])})")
        print(f"\n   ✗ High ATR relative to price movement = LOW CONVICTION")
        print(f"     Stock moved {row['Distance_from_MA']:.1f}% above MA but has {atr_pct[ticker]:.1f}% volatility (choppy)")

    return comparison


def analyze_historical_selections(prices, spy_prices, num_samples=5):
    """
    Analyze stock selections over multiple rebalance dates
    """
    print(f"\n{'='*80}")
    print("📅 HISTORICAL STOCK SELECTIONS (Last 5 Quarterly Rebalances)")
    print(f"{'='*80}")

    # Get quarterly rebalance dates
    rebalance_dates = pd.date_range(
        start=prices.index[0],
        end=prices.index[-1],
        freq='QS'
    )

    # Find actual trading dates
    actual_dates = []
    for ideal_date in rebalance_dates:
        idx = prices.index.searchsorted(ideal_date)
        if idx < len(prices.index):
            actual_dates.append(prices.index[idx])

    # Skip early dates without enough data
    min_date = prices.index[0] + pd.Timedelta(days=100)
    actual_dates = [d for d in actual_dates if d >= min_date]

    # Take last N
    sample_dates = actual_dates[-num_samples:]

    # Track stock frequency
    bss_selections = {}
    roc_selections = {}

    for date in sample_dates:
        print(f"\n{'─'*80}")
        print(f"Date: {date.date()}")

        # Calculate indicators
        ma100 = prices.rolling(window=100).mean()
        above_ma = prices > ma100

        # ROC and BSS
        roc_qualifier = get_qualifier('roc', roc_period=100)
        bss_qualifier = get_qualifier('bss', poi_period=100, atr_period=14, k=2.0)

        roc_scores = roc_qualifier.calculate(prices).loc[date]
        bss_scores = bss_qualifier.calculate(prices).loc[date]
        above_ma_at_date = above_ma.loc[date]

        # Valid stocks
        valid = above_ma_at_date[above_ma_at_date == True].index
        valid = [s for s in valid if s != 'GLD' and pd.notna(roc_scores[s]) and pd.notna(bss_scores[s])]

        # Top 7
        roc_sorted = roc_scores[valid].sort_values(ascending=False)
        bss_sorted = bss_scores[valid].sort_values(ascending=False)

        roc_top7 = roc_sorted.head(7).index.tolist()
        bss_top7 = bss_sorted.head(7).index.tolist()

        # Track
        for stock in bss_top7:
            bss_selections[stock] = bss_selections.get(stock, 0) + 1
        for stock in roc_top7:
            roc_selections[stock] = roc_selections.get(stock, 0) + 1

        # Show selections
        overlap = set(roc_top7).intersection(set(bss_top7))
        print(f"  ROC: {', '.join(roc_top7)}")
        print(f"  BSS: {', '.join(bss_top7)}")
        print(f"  Overlap: {len(overlap)}/7 stocks")

    # Summary
    print(f"\n{'='*80}")
    print(f"📊 MOST FREQUENTLY SELECTED STOCKS (Last {num_samples} rebalances)")
    print(f"{'='*80}")

    print(f"\n🏆 BSS Favorites:")
    bss_sorted = sorted(bss_selections.items(), key=lambda x: x[1], reverse=True)
    for i, (stock, count) in enumerate(bss_sorted[:10], 1):
        print(f"  {i:2}. {stock:6} - {count}/{num_samples} times ({count/num_samples*100:.0f}%)")

    print(f"\n📈 ROC Favorites:")
    roc_sorted = sorted(roc_selections.items(), key=lambda x: x[1], reverse=True)
    for i, (stock, count) in enumerate(roc_sorted[:10], 1):
        print(f"  {i:2}. {stock:6} - {count}/{num_samples} times ({count/num_samples*100:.0f}%)")

    # Unique to BSS
    bss_only_stocks = set(bss_selections.keys()) - set(roc_selections.keys())
    if bss_only_stocks:
        print(f"\n🆕 Stocks ONLY selected by BSS (never by ROC):")
        for stock in sorted(bss_only_stocks):
            print(f"   {stock} ({bss_selections[stock]} times)")


if __name__ == "__main__":
    print("="*80)
    print("STOCK SELECTION ANALYSIS - BSS vs ROC")
    print("="*80)

    # Configuration
    START_DATE = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
    END_DATE = datetime.now().strftime('%Y-%m-%d')

    print(f"\n⚙️  Period: {START_DATE} to {END_DATE}")

    # Download data
    print(f"\n{'='*80}")
    print("DOWNLOADING DATA")
    print(f"{'='*80}")

    prices = download_sp500_stocks(num_stocks=50, start_date=START_DATE, end_date=END_DATE)

    # Add GLD
    if 'GLD' not in prices.columns:
        print(f"\n⚠️  Adding GLD...")
        import yfinance as yf
        gld_data = yf.download('GLD', start=START_DATE, end=END_DATE, auto_adjust=True, progress=False)
        if isinstance(gld_data.columns, pd.MultiIndex):
            gld_data.columns = gld_data.columns.get_level_values(0)
        prices['GLD'] = gld_data['Close']
        prices = prices.dropna()
        print(f"✅ GLD added")

    spy_prices = download_spy(start_date=START_DATE, end_date=END_DATE)

    # Align
    common_dates = prices.index.intersection(spy_prices.index)
    prices = prices.loc[common_dates]
    spy_prices = spy_prices.loc[common_dates]

    print(f"\n✅ Ready: {len(prices)} days, {len(prices.columns)} stocks")

    # Analyze current selection
    comparison = analyze_stock_selection(prices, spy_prices)

    # Analyze historical
    analyze_historical_selections(prices, spy_prices, num_samples=5)

    print(f"\n{'='*80}")
    print("✅ ANALYSIS COMPLETE")
    print(f"{'='*80}")
