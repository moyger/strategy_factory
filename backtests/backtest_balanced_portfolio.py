"""
Complete Backtesting Engine for Balanced Portfolio

Combines all 3 strategies:
- Volatility Gap Scalping (M5)
- Trend Following (H4)
- London Breakout (H1)

Walks through data chronologically at M5 resolution to ensure:
- Accurate signal generation
- Proper position management
- Realistic fills and slippage
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_loader import ForexDataLoader
from multi_strategy_portfolio import MultiStrategyPortfolio
from strategy_scalping import VolatilityGapScalping
from strategy_trend import TrendFollowing
from strategy_breakout import LondonBreakout

class BalancedPortfolioBacktest:
    def __init__(self, start_date='2023-01-01', end_date='2025-09-26', initial_equity=100000):
        """
        Args:
        - start_date: Backtest start date
        - end_date: Backtest end date
        - initial_equity: Starting account size
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_equity = initial_equity

        # Load data
        print("Loading data...")
        loader = ForexDataLoader()
        self.m5_data = loader.load('EURUSD', 'M5')
        self.h1_data = loader.load('EURUSD', 'H1')
        self.h4_data = loader.load('EURUSD', 'H4')

        # Filter to date range
        self.m5_data = self.m5_data[(self.m5_data.index >= start_date) & (self.m5_data.index <= end_date)]
        self.h1_data = self.h1_data[(self.h1_data.index >= start_date) & (self.h1_data.index <= end_date)]
        self.h4_data = self.h4_data[(self.h4_data.index >= start_date) & (self.h4_data.index <= end_date)]

        print(f"M5 bars: {len(self.m5_data):,}")
        print(f"H1 bars: {len(self.h1_data):,}")
        print(f"H4 bars: {len(self.h4_data):,}")

        # Initialize portfolio and strategies
        self.portfolio = MultiStrategyPortfolio(initial_equity)
        self.scalping_strategy = VolatilityGapScalping()
        self.trend_strategy = TrendFollowing(timeframe='H4')
        self.breakout_strategy = LondonBreakout()

        # Pre-calculate indicators
        print("Calculating indicators...")
        self.m5_data = self.scalping_strategy.calculate_indicators(self.m5_data)
        self.h1_data = self.breakout_strategy.calculate_indicators(self.h1_data) if hasattr(self.breakout_strategy, 'calculate_indicators') else self.h1_data
        self.h4_data = self.trend_strategy.calculate_indicators(self.h4_data)

        # Results
        self.trades = []
        self.equity_curve = []

    def get_current_bar(self, df, timestamp):
        """Get bar at or before timestamp"""
        mask = df.index <= timestamp
        if mask.any():
            return df[mask].iloc[-1]
        return None

    def check_scalping_signals(self, timestamp):
        """Check M5 scalping strategy signals"""
        # Get current M5 bar
        if timestamp not in self.m5_data.index:
            return None, None

        # Check exit first
        if self.portfolio.positions['scalping'] is not None:
            exit_signal = self.scalping_strategy.check_exit_signal(self.m5_data, timestamp)
            if exit_signal:
                return 'exit', exit_signal

        # Check entry
        if self.portfolio.positions['scalping'] is None:
            entry_signal = self.scalping_strategy.check_entry_signal(self.m5_data, timestamp)
            if entry_signal:
                return 'entry', entry_signal

        return None, None

    def check_trend_signals(self, timestamp):
        """Check H4 trend strategy signals"""
        # Get current H4 bar
        bar = self.get_current_bar(self.h4_data, timestamp)
        if bar is None:
            return None, None

        idx = bar.name

        # Check exit first
        if self.portfolio.positions['trend'] is not None:
            exit_signal = self.trend_strategy.check_exit_signal(self.h4_data, idx)
            if exit_signal:
                return 'exit', exit_signal

        # Check entry
        if self.portfolio.positions['trend'] is None:
            entry_signal = self.trend_strategy.check_entry_signal(self.h4_data, idx)
            if entry_signal:
                return 'entry', entry_signal

        return None, None

    def check_breakout_signals(self, timestamp):
        """Check H1 breakout strategy signals"""
        # Get current H1 bar
        bar = self.get_current_bar(self.h1_data, timestamp)
        if bar is None:
            return None, None

        idx = bar.name

        # Check exit first
        if self.portfolio.positions['breakout'] is not None:
            exit_signal = self.breakout_strategy.check_exit_signal(self.h1_data, idx)
            if exit_signal:
                return 'exit', exit_signal

        # Check entry
        if self.portfolio.positions['breakout'] is None:
            entry_signal = self.breakout_strategy.check_entry_signal(self.h1_data, idx)
            if entry_signal:
                return 'entry', entry_signal

        return None, None

    def run(self):
        """Run complete backtest"""
        print(f"\nRunning backtest from {self.start_date} to {self.end_date}...")

        # Walk through M5 data (master timeline)
        for i, (timestamp, row) in enumerate(self.m5_data.iterrows()):
            # Process scalping signals (M5)
            signal_type, signal = self.check_scalping_signals(timestamp)
            if signal_type == 'entry':
                position_type, entry_price, sl, tp = signal
                lot_size = self.portfolio.open_position('scalping', position_type, entry_price, sl, tp, timestamp)
            elif signal_type == 'exit':
                exit_reason, exit_price = signal
                result = self.portfolio.close_position('scalping', exit_price, timestamp, exit_reason)
                if result:
                    self.trades.append(result)

            # Process trend signals (H4) - only check every 4 hours
            if timestamp.hour % 4 == 0 and timestamp.minute == 0:
                signal_type, signal = self.check_trend_signals(timestamp)
                if signal_type == 'entry':
                    position_type, entry_price, sl, tp = signal
                    lot_size = self.portfolio.open_position('trend', position_type, entry_price, sl, tp, timestamp)
                elif signal_type == 'exit':
                    exit_reason, exit_price = signal
                    result = self.portfolio.close_position('trend', exit_price, timestamp, exit_reason)
                    if result:
                        self.trades.append(result)

            # Process breakout signals (H1) - only check every hour
            if timestamp.minute == 0:
                signal_type, signal = self.check_breakout_signals(timestamp)
                if signal_type == 'entry':
                    position_type, entry_price, sl, tp, asia_range = signal
                    lot_size = self.portfolio.open_position('breakout', position_type, entry_price, sl, tp, timestamp)
                elif signal_type == 'exit':
                    exit_reason, exit_price = signal
                    result = self.portfolio.close_position('breakout', exit_price, timestamp, exit_reason)
                    if result:
                        self.trades.append(result)

            # Record equity every hour
            if timestamp.minute == 0:
                self.equity_curve.append({
                    'timestamp': timestamp,
                    'equity': self.portfolio.equity,
                    'active_positions': len([p for p in self.portfolio.positions.values() if p is not None])
                })

            # Progress update every 10k bars
            if (i + 1) % 10000 == 0:
                pct = (i + 1) / len(self.m5_data) * 100
                print(f"Progress: {pct:.1f}% | Equity: ${self.portfolio.equity:,.0f} | Trades: {len(self.trades)}")

            # Check if challenge ended
            if not self.portfolio.risk_manager.is_challenge_active:
                print(f"\nChallenge ended at {timestamp}")
                break

        print(f"\nBacktest complete!")
        return self.analyze_results()

    def analyze_results(self):
        """Analyze backtest results"""
        trades_df = pd.DataFrame(self.trades)
        equity_df = pd.DataFrame(self.equity_curve)

        if len(trades_df) == 0:
            print("❌ No trades generated")
            return None

        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)

        # Overall performance
        total_return = (self.portfolio.equity - self.initial_equity) / self.initial_equity
        print(f"\nOverall Performance:")
        print(f"  Initial equity: ${self.initial_equity:,.2f}")
        print(f"  Final equity: ${self.portfolio.equity:,.2f}")
        print(f"  Total return: {total_return*100:.2f}%")
        print(f"  Total trades: {len(trades_df)}")

        # Win rate
        wins = trades_df[trades_df['pnl_dollars'] > 0]
        losses = trades_df[trades_df['pnl_dollars'] <= 0]
        win_rate = len(wins) / len(trades_df)
        print(f"\n  Wins: {len(wins)} ({win_rate*100:.1f}%)")
        print(f"  Losses: {len(losses)} ({(1-win_rate)*100:.1f}%)")
        print(f"  Avg win: ${wins['pnl_dollars'].mean():.2f}" if len(wins) > 0 else "  Avg win: N/A")
        print(f"  Avg loss: ${losses['pnl_dollars'].mean():.2f}" if len(losses) > 0 else "  Avg loss: N/A")

        # Per-strategy breakdown
        print(f"\nPer-Strategy Performance:")
        for strategy in ['scalping', 'trend', 'breakout']:
            strat_trades = trades_df[trades_df['strategy'] == strategy]
            if len(strat_trades) > 0:
                strat_wins = strat_trades[strat_trades['pnl_dollars'] > 0]
                strat_wr = len(strat_wins) / len(strat_trades)
                strat_pnl = strat_trades['pnl_dollars'].sum()
                print(f"  {strategy.capitalize()}: {len(strat_trades)} trades | WR: {strat_wr*100:.1f}% | P&L: ${strat_pnl:,.2f}")

        # Drawdown
        if len(equity_df) > 0:
            equity_series = pd.Series(equity_df['equity'].values, index=equity_df['timestamp'])
            peak = equity_series.expanding().max()
            dd = (equity_series - peak) / peak
            max_dd = dd.min()
            print(f"\nRisk Metrics:")
            print(f"  Max drawdown: {max_dd*100:.2f}%")

        # FTMO status
        risk_summary = self.portfolio.risk_manager.get_summary()
        print(f"\nFTMO Challenge Status:")
        print(f"  Challenge passed: {risk_summary['Challenge Passed']}")
        print(f"  Challenge failed: {risk_summary['Challenge Failed']}")
        if risk_summary['Failure Reason']:
            print(f"  Failure reason: {risk_summary['Failure Reason']}")

        return {
            'trades': trades_df,
            'equity_curve': equity_df,
            'summary': risk_summary
        }

if __name__ == '__main__':
    print("=" * 60)
    print("BALANCED PORTFOLIO BACKTEST")
    print("=" * 60)

    # Run backtest on recent data (2024-2025)
    bt = BalancedPortfolioBacktest(
        start_date='2024-01-01',
        end_date='2025-09-26',
        initial_equity=100000
    )

    results = bt.run()

    if results:
        # Save results
        results['trades'].to_csv('output/london_breakout/portfolio_trades.csv', index=False)
        results['equity_curve'].to_csv('output/london_breakout/portfolio_equity.csv', index=False)
        print(f"\n✅ Results saved to output/london_breakout/")
