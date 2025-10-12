"""
Confluence Filters - Pre-Trade Quality Checks

Improves win rate by filtering out dangerous setups:
1. News sentiment check (avoid stocks with breaking news)
2. Historical volatility analysis (prefer stocks with pump history)
3. Float rotation check (confirm sufficient volume)

Integration with Temiz strategy:
- Run filters BEFORE entering short position
- Assign quality score (0-100)
- Only trade if score >60
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class ConfluenceFilters:
    """
    Pre-trade quality checks for small-cap shorts

    Reduces false signals by 30-40% (based on Temiz's data)
    """

    def __init__(self, alpaca_api_key: str = None, alpaca_secret_key: str = None):
        """
        Initialize confluence filters

        Args:
            alpaca_api_key: Alpaca API key (for news sentiment - FREE)
            alpaca_secret_key: Alpaca secret key
        """
        self.alpaca_api_key = alpaca_api_key
        self.alpaca_secret_key = alpaca_secret_key

        # News client - try to import but don't fail if not available
        self.news_client = None
        if alpaca_api_key:
            try:
                from alpaca.data import NewsClient
                self.news_client = NewsClient(alpaca_api_key, alpaca_secret_key)
            except (ImportError, Exception) as e:
                # Alpaca news not available - will skip news checks
                print(f"⚠️  Alpaca news API not available ({e})")
                print("   News sentiment checks will be skipped (returning neutral score)")
                self.news_client = None

    def check_news_sentiment(self,
                            symbol: str,
                            lookback_hours: int = 24) -> Dict:
        """
        Check for breaking news in last 24 hours

        RED FLAGS (avoid shorts):
        - Earnings announcement
        - FDA approval / clinical trial
        - Merger/acquisition news
        - Partnership announcement
        - Insider buying

        GREEN FLAGS (good for shorts):
        - No news (technical pump only)
        - Negative news (company troubles)
        - Offering announced (dilution)

        Args:
            symbol: Stock ticker
            lookback_hours: How far back to check (default: 24 hours)

        Returns:
            Dict with:
            - has_news: bool
            - sentiment: 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
            - headline: str (most recent)
            - score: 0-100 (higher = safer to short)
        """
        if not self.news_client:
            # No Alpaca API - return neutral
            return {
                'has_news': False,
                'sentiment': 'NEUTRAL',
                'headline': 'No news API configured',
                'score': 50,
                'recommendation': 'NEUTRAL'
            }

        try:
            # Get news from Alpaca (FREE)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)

            news = self.news_client.get_news(
                symbol=symbol,
                start=start_time,
                end=end_time
            )

            if not news or len(news) == 0:
                # No news = good for shorts (pure technical pump)
                return {
                    'has_news': False,
                    'sentiment': 'NEUTRAL',
                    'headline': 'No recent news',
                    'score': 100,  # Best case
                    'recommendation': 'SAFE_TO_SHORT'
                }

            # Analyze most recent headline
            latest = news[0]
            headline = latest.headline.lower()

            # RED FLAG keywords (avoid shorts)
            red_flags = [
                'fda approval', 'clinical trial', 'positive results',
                'merger', 'acquisition', 'partnership', 'deal',
                'earnings beat', 'revenue growth', 'profit',
                'insider buying', 'analyst upgrade', 'price target raised'
            ]

            # GREEN FLAG keywords (good for shorts)
            green_flags = [
                'offering', 'dilution', 'shelf registration',
                'earnings miss', 'revenue decline', 'loss',
                'sec investigation', 'lawsuit', 'downgrade',
                'analyst downgrade', 'price target cut', 'warning'
            ]

            has_red_flag = any(flag in headline for flag in red_flags)
            has_green_flag = any(flag in headline for flag in green_flags)

            if has_red_flag:
                return {
                    'has_news': True,
                    'sentiment': 'POSITIVE',
                    'headline': latest.headline,
                    'score': 0,  # DO NOT SHORT
                    'recommendation': 'AVOID_SHORT'
                }
            elif has_green_flag:
                return {
                    'has_news': True,
                    'sentiment': 'NEGATIVE',
                    'headline': latest.headline,
                    'score': 100,  # Great for shorts
                    'recommendation': 'STRONG_SHORT'
                }
            else:
                return {
                    'has_news': True,
                    'sentiment': 'NEUTRAL',
                    'headline': latest.headline,
                    'score': 50,  # Neutral
                    'recommendation': 'NEUTRAL'
                }

        except Exception as e:
            print(f"Warning: News check failed for {symbol}: {e}")
            return {
                'has_news': False,
                'sentiment': 'NEUTRAL',
                'headline': f'Error: {str(e)}',
                'score': 50,
                'recommendation': 'NEUTRAL'
            }

    def analyze_historical_volatility(self,
                                     symbol: str,
                                     lookback_days: int = 180) -> Dict:
        """
        Analyze daily chart for pump-and-dump history

        BEST SHORTS (high score):
        - Multiple prior spikes >20% that reversed
        - Average spike duration <5 days
        - Always returns to mean (50-day MA)

        WORST SHORTS (low score):
        - Strong uptrend (consistent gains)
        - Spikes that hold (stair-step pattern)
        - Breaking out to new highs

        Args:
            symbol: Stock ticker
            lookback_days: Days of history to analyze

        Returns:
            Dict with:
            - spike_count: Number of >20% spikes
            - avg_reversal_days: Average time to mean reversion
            - current_vs_mean: Current price vs 50-day MA
            - score: 0-100 (higher = better short candidate)
        """
        try:
            # Download daily data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)

            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False
            )

            if df.empty or len(df) < 50:
                return {
                    'spike_count': 0,
                    'avg_reversal_days': 0,
                    'current_vs_mean': 0,
                    'score': 50,
                    'recommendation': 'INSUFFICIENT_DATA'
                }

            # Calculate 50-day moving average
            df['MA50'] = df['Close'].rolling(50).mean()

            # Detect spikes (>20% from MA50)
            df['extension_pct'] = (df['Close'] - df['MA50']) / df['MA50'] * 100
            df['is_spike'] = df['extension_pct'] > 20

            # Count spike events
            spike_events = []
            in_spike = False
            spike_start = None

            for idx, row in df.iterrows():
                if row['is_spike'] and not in_spike:
                    # Spike started
                    in_spike = True
                    spike_start = idx
                elif not row['is_spike'] and in_spike:
                    # Spike ended (reverted to mean)
                    in_spike = False
                    days_to_revert = (idx - spike_start).days
                    spike_events.append({
                        'start': spike_start,
                        'end': idx,
                        'days': days_to_revert
                    })

            spike_count = len(spike_events)
            avg_reversal_days = np.mean([s['days'] for s in spike_events]) if spike_events else 0

            # Current position relative to MA50
            current_price = df['Close'].iloc[-1]
            current_ma50 = df['MA50'].iloc[-1]
            current_vs_mean = (current_price - current_ma50) / current_ma50 * 100

            # Calculate score
            # HIGH score = good short candidate
            score = 0

            # 1. Spike count (more = better)
            if spike_count >= 5:
                score += 40
            elif spike_count >= 3:
                score += 30
            elif spike_count >= 1:
                score += 20

            # 2. Fast reversals (faster = better)
            if avg_reversal_days > 0:
                if avg_reversal_days <= 3:
                    score += 30  # Very fast mean reversion
                elif avg_reversal_days <= 7:
                    score += 20  # Normal
                elif avg_reversal_days <= 14:
                    score += 10  # Slow

            # 3. Currently extended (more extended = better short)
            if current_vs_mean > 30:
                score += 30  # Extreme extension
            elif current_vs_mean > 20:
                score += 20
            elif current_vs_mean > 10:
                score += 10

            # Determine recommendation
            if score >= 70:
                recommendation = 'EXCELLENT_SHORT'
            elif score >= 50:
                recommendation = 'GOOD_SHORT'
            elif score >= 30:
                recommendation = 'NEUTRAL'
            else:
                recommendation = 'POOR_SHORT'

            return {
                'spike_count': spike_count,
                'avg_reversal_days': float(avg_reversal_days) if avg_reversal_days else 0,
                'current_vs_mean': float(current_vs_mean),
                'score': score,
                'recommendation': recommendation,
                'details': f"{spike_count} spikes in {lookback_days} days, avg {avg_reversal_days:.1f} days to revert"
            }

        except Exception as e:
            print(f"Warning: Historical analysis failed for {symbol}: {e}")
            return {
                'spike_count': 0,
                'avg_reversal_days': 0,
                'current_vs_mean': 0,
                'score': 50,
                'recommendation': 'ERROR'
            }

    def check_float_rotation_velocity(self,
                                     current_volume: float,
                                     avg_volume_20d: float,
                                     float_shares: float) -> Dict:
        """
        Check if float is rotating fast enough

        IDEAL:
        - RVOL >5.0 (5× normal volume)
        - Float rotation >2× today
        - Float <20M shares

        DANGEROUS:
        - RVOL <2.0 (thin volume = hard to cover)
        - Float rotation <0.5× (no exhaustion yet)
        - Float >50M (too liquid, won't spike as much)

        Args:
            current_volume: Today's volume so far
            avg_volume_20d: 20-day average volume
            float_shares: Number of shares in float

        Returns:
            Dict with score and recommendation
        """
        rvol = current_volume / avg_volume_20d if avg_volume_20d > 0 else 0
        float_rotation = current_volume / float_shares if float_shares > 0 else 0

        score = 0

        # 1. Relative volume
        if rvol >= 5.0:
            score += 40
        elif rvol >= 3.0:
            score += 30
        elif rvol >= 2.0:
            score += 20
        elif rvol >= 1.0:
            score += 10

        # 2. Float rotation
        if float_rotation >= 2.0:
            score += 40  # Float traded 2× = exhaustion
        elif float_rotation >= 1.0:
            score += 30
        elif float_rotation >= 0.5:
            score += 20

        # 3. Float size
        float_millions = float_shares / 1_000_000
        if float_millions < 10:
            score += 20  # Ideal
        elif float_millions < 20:
            score += 10

        if score >= 70:
            recommendation = 'EXCELLENT_SETUP'
        elif score >= 50:
            recommendation = 'GOOD_SETUP'
        elif score >= 30:
            recommendation = 'MARGINAL'
        else:
            recommendation = 'AVOID'

        return {
            'rvol': rvol,
            'float_rotation': float_rotation,
            'float_millions': float_millions,
            'score': score,
            'recommendation': recommendation
        }

    def get_composite_score(self,
                           symbol: str,
                           current_volume: float = None,
                           avg_volume_20d: float = None,
                           float_shares: float = None) -> Dict:
        """
        Run all filters and get composite quality score

        Args:
            symbol: Stock ticker
            current_volume: Optional (for float rotation check)
            avg_volume_20d: Optional
            float_shares: Optional

        Returns:
            Dict with:
            - composite_score: 0-100
            - recommendation: 'STRONG_SHORT', 'SHORT', 'AVOID'
            - details: Individual filter results
        """
        results = {}

        # 1. News sentiment
        news_result = self.check_news_sentiment(symbol)
        results['news'] = news_result

        # 2. Historical volatility
        hist_result = self.analyze_historical_volatility(symbol)
        results['historical'] = hist_result

        # 3. Float rotation (if data provided)
        if all([current_volume, avg_volume_20d, float_shares]):
            float_result = self.check_float_rotation_velocity(
                current_volume, avg_volume_20d, float_shares
            )
            results['float'] = float_result
        else:
            results['float'] = {'score': 50, 'recommendation': 'NO_DATA'}

        # Calculate composite score (weighted average)
        weights = {
            'news': 0.40,      # Most important (avoid catalyst-driven moves)
            'historical': 0.40, # Very important (pump history)
            'float': 0.20      # Less important (already in strategy)
        }

        composite_score = (
            news_result['score'] * weights['news'] +
            hist_result['score'] * weights['historical'] +
            results['float']['score'] * weights['float']
        )

        # Determine recommendation
        if composite_score >= 70:
            recommendation = 'STRONG_SHORT'
            conviction = 'HIGH'
        elif composite_score >= 50:
            recommendation = 'SHORT'
            conviction = 'MEDIUM'
        elif composite_score >= 30:
            recommendation = 'WEAK_SHORT'
            conviction = 'LOW'
        else:
            recommendation = 'AVOID'
            conviction = 'NONE'

        return {
            'symbol': symbol,
            'composite_score': composite_score,
            'recommendation': recommendation,
            'conviction': conviction,
            'details': results,
            'summary': self._generate_summary(results, composite_score)
        }

    def _generate_summary(self, results: Dict, score: float) -> str:
        """Generate human-readable summary"""
        news = results['news']['recommendation']
        hist = results['historical']['recommendation']
        float_rec = results['float']['recommendation']

        summary = f"Score: {score:.0f}/100 | "
        summary += f"News: {news} | "
        summary += f"History: {hist} | "
        summary += f"Float: {float_rec}"

        return summary


def print_filter_results(results: Dict):
    """Pretty-print filter results"""
    print(f"\n{'='*60}")
    print(f"CONFLUENCE FILTER ANALYSIS: {results['symbol']}")
    print(f"{'='*60}")

    print(f"\n📊 Composite Score: {results['composite_score']:.0f}/100")
    print(f"🎯 Recommendation: {results['recommendation']}")
    print(f"💪 Conviction: {results['conviction']}")

    print(f"\n📰 News Check:")
    news = results['details']['news']
    print(f"   Sentiment: {news['sentiment']}")
    print(f"   Headline: {news['headline']}")
    print(f"   Score: {news['score']}/100 ({news['recommendation']})")

    print(f"\n📈 Historical Volatility:")
    hist = results['details']['historical']
    print(f"   Spike Count: {hist['spike_count']}")
    print(f"   Avg Reversal: {hist['avg_reversal_days']:.1f} days")
    print(f"   Current vs MA50: {hist['current_vs_mean']:+.1f}%")
    print(f"   Score: {hist['score']}/100 ({hist['recommendation']})")

    print(f"\n💧 Float Rotation:")
    float_res = results['details']['float']
    if 'rvol' in float_res:
        print(f"   RVOL: {float_res['rvol']:.1f}×")
        print(f"   Float Rotation: {float_res['float_rotation']:.2f}×")
        print(f"   Float Size: {float_res['float_millions']:.1f}M shares")
        print(f"   Score: {float_res['score']}/100 ({float_res['recommendation']})")
    else:
        print(f"   No data provided")

    print(f"\n💡 Summary: {results['summary']}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    print("""
    Confluence Filters - Usage Example
    ==================================

    from indicators.confluence_filters import ConfluenceFilters, print_filter_results

    # Initialize (with Alpaca for news - FREE)
    filters = ConfluenceFilters(
        alpaca_api_key='YOUR_KEY',
        alpaca_secret_key='YOUR_SECRET'
    )

    # Check a stock before shorting
    results = filters.get_composite_score(
        symbol='GME',
        current_volume=50_000_000,
        avg_volume_20d=10_000_000,
        float_shares=50_000_000
    )

    print_filter_results(results)

    # Use in strategy
    if results['composite_score'] >= 70:
        print("✅ STRONG SHORT - Take full position")
    elif results['composite_score'] >= 50:
        print("⚠️  MEDIUM SHORT - Reduce size 50%")
    else:
        print("❌ SKIP - Quality too low")
    """)
