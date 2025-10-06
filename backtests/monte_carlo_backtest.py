"""
Monte Carlo Enhanced Backtesting

Addresses intra-bar execution uncertainty by simulating random entry/exit prices
within the H1 bar range. This provides more realistic performance estimates.

Key enhancements:
1. Random entry price within breakout bar
2. Random SL/TP execution price within bar that crosses threshold
3. Dynamic spread modeling based on session and volatility
4. Multiple simulation runs to get confidence intervals
"""
import pandas as pd
import numpy as np
from strategy_breakout import LondonBreakout
from session_manager import TradingSession
from data_loader import ForexDataLoader

class MonteCarloBacktest:
    def __init__(self, num_simulations=1000):
        """
        Args:
        - num_simulations: Number of Monte Carlo runs (default: 1000)
        """
        self.num_simulations = num_simulations
        self.pip_value = 0.0001

    def get_dynamic_spread(self, timestamp, atr_value):
        """
        Calculate dynamic bid/ask spread based on session and volatility

        Spread varies by:
        - Session (Asia: wider, London/NY: tighter)
        - Volatility (high ATR = wider spread)
        - Time of day (open = wider, mid-session = tighter)

        Returns: spread in pips
        """
        base_spread = 0.3  # Base spread in pips

        # Session multiplier
        if TradingSession.is_in_session(timestamp, TradingSession.ASIA):
            session_mult = 1.5  # Asia: wider spread
        elif TradingSession.is_in_session(timestamp, TradingSession.OVERLAP):
            session_mult = 1.2  # Overlap: slightly wider (high volume)
        elif TradingSession.is_in_session(timestamp, TradingSession.LONDON):
            session_mult = 1.0  # London: normal
        else:
            session_mult = 1.3  # Off-hours: wider

        # Volatility multiplier (ATR-based)
        avg_atr = 0.0004  # ~4 pips typical
        if atr_value > avg_atr * 2:
            vol_mult = 2.0  # High volatility: double spread
        elif atr_value > avg_atr * 1.5:
            vol_mult = 1.5
        else:
            vol_mult = 1.0

        # London open hour: extra wide
        if timestamp.hour == 3:
            session_mult *= 1.5

        spread_pips = base_spread * session_mult * vol_mult
        return spread_pips

    def simulate_intra_bar_execution(self, bar, entry_trigger, sl, tp, position_type):
        """
        Simulate execution within a bar using random walk

        Args:
        - bar: OHLC bar data
        - entry_trigger: Price level that triggers entry
        - sl: Stop loss price
        - tp: Take profit price
        - position_type: 'long' or 'short'

        Returns: ('tp', price) or ('sl', price) or ('time', price)
        """
        high = bar['high']
        low = bar['low']
        close = bar['close']
        open_price = bar['open']

        # Check if entry was actually triggered
        if position_type == 'long':
            if high < entry_trigger:
                return None  # Entry never triggered
            entry_price = np.random.uniform(entry_trigger, min(entry_trigger + 2*self.pip_value, high))
        else:  # short
            if low > entry_trigger:
                return None  # Entry never triggered
            entry_price = np.random.uniform(max(entry_trigger - 2*self.pip_value, low), entry_trigger)

        # Simulate intra-bar price movement
        # Assumption: price follows random walk between open and close

        # Check if SL was hit
        sl_hit = (low <= sl) if position_type == 'long' else (high >= sl)

        # Check if TP was hit
        tp_hit = (high >= tp) if position_type == 'long' else (low <= tp)

        # If both hit, randomize which was hit first
        if sl_hit and tp_hit:
            # Random 50/50 which came first
            if np.random.random() < 0.5:
                # SL hit first
                exit_price = sl + np.random.uniform(-self.pip_value, self.pip_value)
                return ('sl', exit_price)
            else:
                # TP hit first
                exit_price = tp + np.random.uniform(-self.pip_value, self.pip_value)
                return ('tp', exit_price)

        elif sl_hit:
            exit_price = sl + np.random.uniform(-self.pip_value, self.pip_value)
            return ('sl', exit_price)

        elif tp_hit:
            exit_price = tp + np.random.uniform(-self.pip_value, self.pip_value)
            return ('tp', exit_price)

        else:
            # Neither hit, exit at close (time-based)
            return ('time', close)

    def run_single_simulation(self, df, strategy):
        """Run single Monte Carlo simulation"""
        trades = []
        position = None
        asia_ranges = {}

        for idx in df.index:
            row = df.loc[idx]

            # Check exit first
            if position is not None:
                exit_result = self.simulate_intra_bar_execution(
                    row,
                    position['entry_price'],
                    position['sl'],
                    position['tp'],
                    position['type']
                )

                if exit_result:
                    exit_reason, exit_price = exit_result
                    entry_price = position['entry_price']
                    position_type = position['type']

                    # Calculate P&L
                    if position_type == 'long':
                        pnl_pips = (exit_price - entry_price) / self.pip_value
                    else:
                        pnl_pips = (entry_price - exit_price) / self.pip_value

                    # Get dynamic spread and slippage
                    atr_val = row.get('atr', 0.0004)
                    spread_pips = self.get_dynamic_spread(idx, atr_val)

                    # Costs
                    lot_size = 1.0
                    pnl_dollars = pnl_pips * 10.0 * lot_size
                    commission = 0.0005 * 100000  # 0.05%
                    slippage = np.random.uniform(0.3, 1.0) * 10  # Variable slippage
                    spread_cost = spread_pips * 10  # Bid/ask spread

                    total_costs = commission + slippage + spread_cost
                    pnl_dollars -= total_costs

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': idx,
                        'type': position_type,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pips': pnl_pips,
                        'pnl_dollars': pnl_dollars,
                        'exit_reason': exit_reason,
                        'spread_pips': spread_pips,
                        'total_costs': total_costs
                    })

                    position = None

            # Check entry
            if position is None:
                # Get Asia range
                current_date = idx.date()
                if current_date not in asia_ranges:
                    asia_range = strategy.get_asia_range(df, idx)
                    if asia_range:
                        asia_ranges[current_date] = asia_range

                # Check breakout
                if TradingSession.is_in_session(idx, TradingSession.LONDON):
                    asia_range = asia_ranges.get(current_date)
                    if asia_range and strategy.min_asia_range_pips <= asia_range['range_pips'] <= strategy.max_asia_range_pips:
                        buffer = strategy.breakout_buffer_pips * self.pip_value

                        # Bullish breakout
                        if row['high'] > (asia_range['high'] + buffer):
                            entry_trigger = asia_range['high'] + buffer
                            sl = asia_range['low']
                            tp_pips = max(asia_range['range_pips'], strategy.min_tp_pips)
                            tp = entry_trigger + (tp_pips * self.pip_value)

                            position = {
                                'type': 'long',
                                'entry_price': entry_trigger,
                                'entry_time': idx,
                                'sl': sl,
                                'tp': tp
                            }

                        # Bearish breakout
                        elif row['low'] < (asia_range['low'] - buffer):
                            entry_trigger = asia_range['low'] - buffer
                            sl = asia_range['high']
                            tp_pips = max(asia_range['range_pips'], strategy.min_tp_pips)
                            tp = entry_trigger - (tp_pips * self.pip_value)

                            position = {
                                'type': 'short',
                                'entry_price': entry_trigger,
                                'entry_time': idx,
                                'sl': sl,
                                'tp': tp
                            }

        return pd.DataFrame(trades)

    def run_monte_carlo(self, df, strategy):
        """
        Run multiple Monte Carlo simulations

        Returns: dict with statistics and confidence intervals
        """
        print(f"Running {self.num_simulations} Monte Carlo simulations...")

        all_results = []

        for i in range(self.num_simulations):
            trades = self.run_single_simulation(df, strategy)

            if len(trades) > 0:
                total_pnl = trades['pnl_dollars'].sum()
                win_rate = (trades['pnl_dollars'] > 0).sum() / len(trades)
                avg_pnl = trades['pnl_dollars'].mean()
                num_trades = len(trades)
                avg_spread = trades['spread_pips'].mean()
                avg_costs = trades['total_costs'].mean()

                all_results.append({
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'num_trades': num_trades,
                    'avg_spread': avg_spread,
                    'avg_costs': avg_costs
                })

            if (i + 1) % 100 == 0:
                print(f"  Completed {i+1}/{self.num_simulations} simulations")

        results_df = pd.DataFrame(all_results)

        # Calculate statistics
        stats = {
            'mean_total_pnl': results_df['total_pnl'].mean(),
            'median_total_pnl': results_df['total_pnl'].median(),
            'std_total_pnl': results_df['total_pnl'].std(),
            'pnl_5th_percentile': results_df['total_pnl'].quantile(0.05),
            'pnl_95th_percentile': results_df['total_pnl'].quantile(0.95),

            'mean_win_rate': results_df['win_rate'].mean(),
            'win_rate_5th_percentile': results_df['win_rate'].quantile(0.05),
            'win_rate_95th_percentile': results_df['win_rate'].quantile(0.95),

            'mean_avg_pnl': results_df['avg_pnl'].mean(),
            'mean_num_trades': results_df['num_trades'].mean(),
            'mean_avg_spread': results_df['avg_spread'].mean(),
            'mean_avg_costs': results_df['avg_costs'].mean(),
        }

        return stats, results_df


if __name__ == '__main__':
    print("=" * 60)
    print("MONTE CARLO ENHANCED BACKTEST")
    print("=" * 60)

    # Load data
    loader = ForexDataLoader()
    df = loader.load('EURUSD', 'H1')
    df = df[df.index >= '2024-01-01']  # Use 2024 only for faster testing

    print(f"Data: {len(df):,} H1 bars from {df.index.min()} to {df.index.max()}\n")

    # Initialize strategy
    strategy = LondonBreakout()
    df = strategy.calculate_indicators(df) if hasattr(strategy, 'calculate_indicators') else df

    # Run Monte Carlo with 100 simulations (faster)
    mc = MonteCarloBacktest(num_simulations=100)
    stats, results_df = mc.run_monte_carlo(df, strategy)

    print("\n" + "=" * 60)
    print("MONTE CARLO RESULTS (100 simulations)")
    print("=" * 60)

    print("\nTotal P&L:")
    print(f"  Mean: ${stats['mean_total_pnl']:,.2f}")
    print(f"  Median: ${stats['median_total_pnl']:,.2f}")
    print(f"  Std Dev: ${stats['std_total_pnl']:,.2f}")
    print(f"  90% CI: ${stats['pnl_5th_percentile']:,.2f} to ${stats['pnl_95th_percentile']:,.2f}")

    print("\nWin Rate:")
    print(f"  Mean: {stats['mean_win_rate']*100:.2f}%")
    print(f"  90% CI: {stats['win_rate_5th_percentile']*100:.2f}% to {stats['win_rate_95th_percentile']*100:.2f}%")

    print("\nTrade Statistics:")
    print(f"  Avg P&L per trade: ${stats['mean_avg_pnl']:.2f}")
    print(f"  Avg trades: {stats['mean_num_trades']:.0f}")
    print(f"  Avg spread: {stats['mean_avg_spread']:.2f} pips")
    print(f"  Avg total costs: ${stats['mean_avg_costs']:.2f}")

    # Save results
    results_df.to_csv('output/london_breakout/monte_carlo_results.csv', index=False)
    print(f"\n✅ Results saved to output/london_breakout/monte_carlo_results.csv")

    print("\n" + "=" * 60)
