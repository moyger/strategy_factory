"""
Trading Session Manager
Handles Forex trading session logic (Asia, London, NY sessions)
All times in EST (FTMO broker timezone)
"""

from datetime import time as datetime_time


class TradingSession:
    """
    Manages trading session times and filters
    """

    # Session times (EST)
    ASIA = {
        'start': datetime_time(19, 0),   # 7:00 PM
        'end': datetime_time(2, 0),       # 2:00 AM next day
        'name': 'Asia'
    }

    LONDON = {
        'start': datetime_time(3, 0),     # 3:00 AM
        'end': datetime_time(12, 0),      # 12:00 PM
        'name': 'London'
    }

    NY = {
        'start': datetime_time(8, 0),     # 8:00 AM
        'end': datetime_time(17, 0),      # 5:00 PM
        'name': 'New York'
    }

    OVERLAP = {
        'start': datetime_time(8, 0),     # 8:00 AM
        'end': datetime_time(12, 0),      # 12:00 PM
        'name': 'London/NY Overlap'
    }

    @staticmethod
    def is_in_session(timestamp, session):
        """
        Check if timestamp falls within trading session

        Args:
            timestamp: datetime object
            session: Dict with 'start' and 'end' time objects

        Returns:
            bool
        """
        t = timestamp.time()
        start = session['start']
        end = session['end']

        # Handle sessions that cross midnight (Asia)
        if start > end:
            return t >= start or t < end
        else:
            return start <= t < end

    @staticmethod
    def get_session_name(timestamp):
        """
        Get current active session name

        Args:
            timestamp: datetime object

        Returns:
            str: 'Asia', 'London', 'NY', 'Overlap', or 'None'
        """
        if TradingSession.is_in_session(timestamp, TradingSession.OVERLAP):
            return 'Overlap'
        elif TradingSession.is_in_session(timestamp, TradingSession.LONDON):
            return 'London'
        elif TradingSession.is_in_session(timestamp, TradingSession.NY):
            return 'NY'
        elif TradingSession.is_in_session(timestamp, TradingSession.ASIA):
            return 'Asia'
        else:
            return 'None'

    @staticmethod
    def get_asia_range(bars, current_date):
        """
        Get high/low range from Asia session for London breakout

        Args:
            bars: DataFrame with datetime index
            current_date: date object

        Returns:
            Dict with 'high', 'low', 'range_pips' or None
        """
        # Asia session: 7 PM previous day to 2 AM current day
        from datetime import datetime, timedelta

        # Previous day 7 PM
        asia_start = datetime.combine(current_date - timedelta(days=1), datetime_time(19, 0))
        # Current day 2 AM
        asia_end = datetime.combine(current_date, datetime_time(2, 0))

        # Filter bars
        mask = (bars.index >= asia_start) & (bars.index < asia_end)
        asia_bars = bars[mask]

        if len(asia_bars) < 5:  # Need minimum bars
            return None

        asia_high = asia_bars['high'].max()
        asia_low = asia_bars['low'].min()
        range_pips = (asia_high - asia_low) / 0.0001

        return {
            'high': asia_high,
            'low': asia_low,
            'range_pips': range_pips,
            'start': asia_start,
            'end': asia_end
        }

    @staticmethod
    def is_high_liquidity_time(timestamp):
        """
        Check if during high-liquidity periods (London or NY open hours)

        Args:
            timestamp: datetime object

        Returns:
            bool
        """
        return (
            TradingSession.is_in_session(timestamp, TradingSession.LONDON) or
            TradingSession.is_in_session(timestamp, TradingSession.NY)
        )

    @staticmethod
    def is_london_open_hour(timestamp):
        """Check if at London open hour (3 AM EST)"""
        return timestamp.hour == 3

    @staticmethod
    def is_overlap_session(timestamp):
        """Check if in London/NY overlap (8 AM - 12 PM EST)"""
        return TradingSession.is_in_session(timestamp, TradingSession.OVERLAP)


# Example usage
if __name__ == '__main__':
    from datetime import datetime

    # Test session detection
    test_times = [
        datetime(2024, 1, 15, 3, 0),   # London open
        datetime(2024, 1, 15, 8, 30),  # Overlap
        datetime(2024, 1, 15, 15, 0),  # NY only
        datetime(2024, 1, 15, 20, 0),  # Asia
    ]

    for dt in test_times:
        session = TradingSession.get_session_name(dt)
        is_overlap = TradingSession.is_overlap_session(dt)
        print(f"{dt.time()}: Session={session}, Overlap={is_overlap}")
