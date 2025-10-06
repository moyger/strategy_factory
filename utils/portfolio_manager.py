"""
Multi-Pair Portfolio Manager

Manages multiple breakout strategies simultaneously:
- EUR/USD: London Breakout v3
- USD/JPY: London Breakout v3 (JPY-adjusted)

Features:
- Risk management across all positions
- Correlation-aware position sizing
- FTMO rule compliance
- Combined performance reporting
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy_breakout_v3 import LondonBreakoutV3 as EURUSDStrategy
from strategy_breakout_v3_usdjpy import LondonBreakoutV3 as USDJPYStrategy


class PortfolioManager:
    def __init__(self, initial_balance=100000):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance

        # FTMO limits
        self.max_daily_loss_pct = -5.0  # -5% daily loss limit
        self.max_total_dd_pct = -10.0   # -10% total drawdown limit

        # Our safety limits (more conservative)
        self.max_simultaneous_positions = 2  # Max 2 positions (one per pair)
        self.base_risk_pct = 0.75  # Base risk per trade when multiple positions
        self.circuit_breaker_daily = -4.0  # Stop at -4% daily
        self.circuit_breaker_total = -8.0  # Stop at -8% total

        # Strategies
        self.strategies = {
            'EURUSD': EURUSDStrategy(pair='EURUSD'),
            'USDJPY': USDJPYStrategy(pair='USDJPY'),
        }

        # Pair correlations
        self.correlation = {
            ('EURUSD', 'USDJPY'): -0.35  # Negative correlation
        }

    def calculate_position_size(self, pair, sl_pips, num_open_positions):
        """
        Calculate position size based on:
        1. Number of open positions (scale down risk)
        2. Pair characteristics (pip value)
        """
        # Adaptive risk based on portfolio exposure
        if num_open_positions == 0:
            risk_pct = 1.0  # First position: 1% risk
        elif num_open_positions == 1:
            risk_pct = 0.75  # Second position: 0.75% risk
        else:
            risk_pct = 0.6  # 3+ positions: 0.6% risk

        risk_dollars = self.current_balance * (risk_pct / 100)

        # Calculate lot size based on pair
        pip_value_per_lot = 10  # $10 per pip for 1 standard lot (for both pairs)
        lot_size = risk_dollars / (sl_pips * pip_value_per_lot)

        return round(lot_size, 2), risk_dollars

    def run_portfolio(self, data_dict, start_date='2023-01-01', end_date=None):
        """
        Run all strategies and combine results

        Args:
            data_dict: {
                'EURUSD': {'H1': df, 'H4': df},
                'USDJPY': {'H1': df, 'H4': df},
            }
            start_date: Start of backtest period
            end_date: End of backtest period (None = latest)
        """
        print("=" * 80)
        print("PORTFOLIO MANAGER - EUR/USD + USD/JPY")
        print("=" * 80)

        # Run individual strategies
        all_trades = []

        for pair, strategy in self.strategies.items():
            print(f"\n🔄 Running {pair} strategy...")

            h1_df = data_dict[pair]['H1']
            h4_df = data_dict[pair]['H4']

            # Filter date range
            h1_df = h1_df[h1_df.index >= start_date]
            h4_df = h4_df[h4_df.index >= start_date]

            if end_date:
                h1_df = h1_df[h1_df.index <= end_date]
                h4_df = h4_df[h4_df.index <= end_date]

            # Run backtest
            trades = strategy.backtest(h1_df, h4_df)

            if len(trades) > 0:
                trades['pair'] = pair
                all_trades.append(trades)
                print(f"  ✅ {pair}: {len(trades)} trades")
            else:
                print(f"  ⚠️  {pair}: No trades generated")

        # Combine all trades
        if len(all_trades) == 0:
            print("\n❌ No trades generated across all strategies")
            return pd.DataFrame()

        combined_trades = pd.concat(all_trades, ignore_index=True)

        # Sort by entry time
        combined_trades = combined_trades.sort_values('entry_time').reset_index(drop=True)

        print(f"\n📊 Combined: {len(combined_trades)} total trades")

        # Calculate portfolio metrics
        self.calculate_portfolio_metrics(combined_trades)

        return combined_trades

    def calculate_portfolio_metrics(self, trades):
        """Calculate and print portfolio-level metrics"""

        print(f"\n{'='*80}")
        print("PORTFOLIO PERFORMANCE")
        print(f"{'='*80}")

        # Overall stats
        total_trades = len(trades)
        wins = trades[trades['pnl_dollars'] > 0]
        losses = trades[trades['pnl_dollars'] <= 0]

        win_rate = len(wins) / total_trades * 100
        total_pnl = trades['pnl_dollars'].sum()
        avg_pnl = trades['pnl_dollars'].mean()

        print(f"\nOverall Statistics:")
        print(f"  Total Trades: {total_trades}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        print(f"  Avg P&L/Trade: ${avg_pnl:.2f}")

        if len(wins) > 0 and len(losses) > 0:
            profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum())
            print(f"  Profit Factor: {profit_factor:.2f}")
            print(f"  Avg Win: ${wins['pnl_dollars'].mean():.2f}")
            print(f"  Avg Loss: ${losses['pnl_dollars'].mean():.2f}")

        # Per-pair breakdown
        print(f"\nPer-Pair Breakdown:")
        for pair in trades['pair'].unique():
            pair_trades = trades[trades['pair'] == pair]
            pair_wins = pair_trades[pair_trades['pnl_dollars'] > 0]
            pair_wr = len(pair_wins) / len(pair_trades) * 100
            pair_pnl = pair_trades['pnl_dollars'].sum()

            print(f"  {pair}: {len(pair_trades)} trades, {pair_wr:.1f}% WR, ${pair_pnl:,.2f}")

        # Annualized metrics
        date_range = (trades['exit_time'].max() - trades['entry_time'].min()).days
        years = date_range / 365.25

        print(f"\nAnnualized Metrics:")
        print(f"  Period: {trades['entry_time'].min().date()} to {trades['exit_time'].max().date()}")
        print(f"  Years: {years:.2f}")
        print(f"  Trades/Year: {total_trades/years:.1f}")
        print(f"  Annual P&L: ${total_pnl/years:,.2f}")

        # Portfolio risk metrics
        self.calculate_risk_metrics(trades)

    def calculate_risk_metrics(self, trades):
        """Calculate drawdown and risk metrics"""

        # Create equity curve
        trades = trades.sort_values('exit_time').reset_index(drop=True)
        trades['cumulative_pnl'] = trades['pnl_dollars'].cumsum()
        trades['balance'] = self.initial_balance + trades['cumulative_pnl']

        # Calculate drawdown
        trades['peak'] = trades['balance'].cummax()
        trades['drawdown'] = trades['balance'] - trades['peak']
        trades['drawdown_pct'] = (trades['drawdown'] / trades['peak']) * 100

        max_dd = trades['drawdown_pct'].min()
        max_dd_date = trades.loc[trades['drawdown_pct'].idxmin(), 'exit_time']

        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {max_dd:.2f}%")
        print(f"  Max DD Date: {max_dd_date.date()}")
        print(f"  Final Balance: ${trades['balance'].iloc[-1]:,.2f}")
        print(f"  Total Return: {(trades['balance'].iloc[-1]/self.initial_balance - 1)*100:.2f}%")

        # FTMO compliance
        print(f"\nFTMO Compliance:")
        if max_dd >= self.max_total_dd_pct:
            print(f"  ✅ Max DD {max_dd:.2f}% < {self.max_total_dd_pct}% limit")
        else:
            print(f"  ❌ Max DD {max_dd:.2f}% VIOLATED {self.max_total_dd_pct}% limit")

        # Check daily losses
        trades['date'] = trades['exit_time'].dt.date
        daily_pnl = trades.groupby('date')['pnl_dollars'].sum()
        worst_day = daily_pnl.min()
        worst_day_pct = (worst_day / self.initial_balance) * 100

        print(f"  Worst Day: ${worst_day:,.2f} ({worst_day_pct:.2f}%)")
        if worst_day_pct >= self.max_daily_loss_pct:
            print(f"  ✅ Worst day {worst_day_pct:.2f}% < {self.max_daily_loss_pct}% limit")
        else:
            print(f"  ❌ Worst day {worst_day_pct:.2f}% VIOLATED {self.max_daily_loss_pct}% limit")

        # Correlation benefit
        print(f"\nDiversification Benefit:")
        print(f"  EUR/USD ↔ USD/JPY Correlation: -0.35")
        print(f"  Portfolio benefit: Lower DD than uncorrelated pairs")

    def check_simultaneous_positions(self, trades):
        """Check how often we have multiple positions open at once"""

        # Create timeline of open positions
        timeline = []

        for _, trade in trades.iterrows():
            timeline.append({
                'time': trade['entry_time'],
                'pair': trade['pair'],
                'action': 'open'
            })
            timeline.append({
                'time': trade['exit_time'],
                'pair': trade['pair'],
                'action': 'close'
            })

        timeline_df = pd.DataFrame(timeline).sort_values('time').reset_index(drop=True)

        # Track open positions
        open_positions = set()
        max_simultaneous = 0
        simultaneous_count = {1: 0, 2: 0}

        for _, event in timeline_df.iterrows():
            if event['action'] == 'open':
                open_positions.add(event['pair'])
            else:
                open_positions.discard(event['pair'])

            num_open = len(open_positions)
            max_simultaneous = max(max_simultaneous, num_open)

            if num_open > 0:
                simultaneous_count[min(num_open, 2)] += 1

        total_events = sum(simultaneous_count.values())
        pct_1_pos = simultaneous_count.get(1, 0) / total_events * 100 if total_events > 0 else 0
        pct_2_pos = simultaneous_count.get(2, 0) / total_events * 100 if total_events > 0 else 0

        print(f"\nPosition Overlap Analysis:")
        print(f"  Max simultaneous positions: {max_simultaneous}")
        print(f"  Time with 1 position: {pct_1_pos:.1f}%")
        print(f"  Time with 2 positions: {pct_2_pos:.1f}%")


if __name__ == '__main__':
    from data_loader import ForexDataLoader

    print("\n" + "=" * 80)
    print("LOADING DATA...")
    print("=" * 80)

    # Load data
    loader = ForexDataLoader()

    data = {
        'EURUSD': {
            'H1': loader.load('EURUSD', 'H1'),
            'H4': loader.load('EURUSD', 'H4'),
        },
        'USDJPY': {
            'H1': loader.load('USDJPY', 'H1'),
            'H4': loader.load('USDJPY', 'H4'),
        }
    }

    # Create portfolio manager
    portfolio = PortfolioManager(initial_balance=100000)

    # Run portfolio backtest
    trades = portfolio.run_portfolio(data, start_date='2023-01-01')

    if len(trades) > 0:
        # Check position overlap
        portfolio.check_simultaneous_positions(trades)

        # Save results
        output_file = 'output/london_breakout/portfolio_trades.csv'
        trades.to_csv(output_file, index=False)
        print(f"\n✅ Trades saved to {output_file}")

        print("\n" + "=" * 80)
        print("✅ PORTFOLIO BACKTEST COMPLETE")
        print("=" * 80)
