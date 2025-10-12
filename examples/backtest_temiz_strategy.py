"""
Backtest Engine for Temiz Small-Cap Short Strategy

Simulates realistic intraday trading with:
- Position scaling (1/3 at R1, 1/3 at R2, runner to VWAP)
- Slippage modeling (0.5-2% based on volume)
- Short availability (70-90% based on conviction)
- Daily kill switch (-2% max loss)
- End-of-day exits (close all at 3:55 PM)

Usage:
    python examples/backtest_temiz_strategy.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

from data.alpaca_data_loader import AlpacaDataLoader
from indicators.intraday_indicators import calculate_all_indicators
from strategies.temiz_small_cap_short_strategy import TemizSmallCapShortStrategy


@dataclass
class Trade:
    """Individual trade result"""
    symbol: str
    entry_time: datetime
    exit_time: datetime
    setup_type: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    r_multiple: float  # Profit in R-multiples
    conviction: str
    exit_reason: str  # 'R1', 'R2', 'VWAP', 'STOP', 'EOD'


class TemizBacktester:
    """
    Backtest engine for Temiz strategy

    Handles:
    - Position scaling (partial exits)
    - Slippage and commission
    - Short availability
    - Daily P&L tracking
    - Kill switch
    """

    def __init__(self,
                 initial_capital: float = 100000,
                 commission_per_share: float = 0.005):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital
            commission_per_share: Commission per share (default: $0.005)
        """
        self.initial_capital = initial_capital
        self.commission_per_share = commission_per_share
        self.equity = initial_capital
        self.trades = []
        self.daily_pnl = {}

    def backtest_single_day(self,
                           symbol: str,
                           bars: pd.DataFrame,
                           strategy: TemizSmallCapShortStrategy,
                           verbose: bool = True) -> Dict:
        """
        Backtest a single day

        Args:
            symbol: Stock ticker
            bars: DataFrame with 1-minute OHLCV data for one day
            strategy: TemizSmallCapShortStrategy instance
            verbose: Print progress

        Returns:
            Dict with day results
        """
        if len(bars) == 0:
            return {'trades': [], 'pnl': 0, 'ending_equity': self.equity}

        if verbose:
            print(f"\n{'='*60}")
            print(f"Backtesting {symbol} - {bars.iloc[0]['timestamp'].date()}")
            print(f"{'='*60}")

        # Calculate indicators
        indicators = calculate_all_indicators(bars)

        # Scan for signals
        signals = strategy.scan_for_signals(bars, indicators)

        if verbose:
            print(f"Found {len(signals)} potential signals")

        # Track positions
        active_positions = []
        day_trades = []
        day_start_equity = self.equity

        # Simulate each bar
        for idx in range(len(bars)):
            current_bar = bars.iloc[idx]
            current_time = current_bar['timestamp']

            # Check for new signals at this bar
            matching_signals = [s for s in signals if s['idx'] == idx]

            for signal in matching_signals:
                # Check if we can take this trade
                if len(active_positions) >= strategy.max_positions:
                    continue

                # Check short availability
                if not strategy.simulate_short_availability(signal['conviction']):
                    if verbose:
                        print(f"   ❌ {current_time.strftime('%H:%M')} - Short unavailable ({signal['setup_type']})")
                    continue

                # Calculate position size
                shares = strategy.calculate_position_size(self.equity, signal)
                if shares == 0:
                    continue

                # Apply slippage
                avg_volume = indicators['volume_mean'].iloc[idx]
                entry_price_slipped = strategy.apply_slippage(
                    signal['entry_price'],
                    current_bar['volume'],
                    avg_volume
                )

                # Calculate commission
                commission = shares * self.commission_per_share

                # Calculate targets
                targets = strategy.calculate_targets(signal)
                target_r1, target_r2, target_vwap = targets

                # Open position
                position = {
                    'signal': signal,
                    'entry_time': current_time,
                    'entry_price': entry_price_slipped,
                    'shares_remaining': shares,
                    'shares_initial': shares,
                    'stop_loss': signal['stop_loss'],
                    'target_r1': target_r1,
                    'target_r2': target_r2,
                    'commission_paid': commission,
                    'exits': []
                }

                active_positions.append(position)

                if verbose:
                    print(f"   🔴 {current_time.strftime('%H:%M')} - SHORT {shares} @ ${entry_price_slipped:.2f}")
                    print(f"      Setup: {signal['setup_type']} ({signal['conviction']})")
                    print(f"      Stop: ${signal['stop_loss']:.2f}, R1: ${target_r1:.2f}, R2: ${target_r2:.2f}")

            # Manage existing positions
            for position in active_positions[:]:  # Copy list to modify during iteration
                # Update VWAP target (it moves)
                current_vwap = indicators['vwap'].iloc[idx]
                position['target_vwap'] = current_vwap

                # Check stops and targets
                low = current_bar['low']
                high = current_bar['high']
                close = current_bar['close']

                # 1. Check stop loss (priority)
                if high >= position['stop_loss']:
                    # Stopped out
                    exit_price = position['stop_loss']  # Assume filled at stop
                    shares_exited = position['shares_remaining']

                    pnl, pnl_pct, r_multiple = self._calculate_exit_pnl(
                        position, exit_price, shares_exited
                    )

                    self.equity += pnl

                    trade = Trade(
                        symbol=symbol,
                        entry_time=position['entry_time'],
                        exit_time=current_time,
                        setup_type=position['signal']['setup_type'],
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        shares=shares_exited,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        r_multiple=r_multiple,
                        conviction=position['signal']['conviction'],
                        exit_reason='STOP'
                    )
                    day_trades.append(trade)
                    self.trades.append(trade)
                    active_positions.remove(position)

                    if verbose:
                        print(f"   ❌ {current_time.strftime('%H:%M')} - STOP @ ${exit_price:.2f} | {r_multiple:.2f}R | ${pnl:+,.0f}")

                    continue

                # 2. Check R2 target (scale 1/3)
                if low <= position['target_r2'] and position['shares_remaining'] == position['shares_initial']:
                    # Take 1/3 off at R2
                    exit_price = position['target_r2']
                    shares_exited = position['shares_initial'] // 3

                    if shares_exited > 0:
                        pnl, pnl_pct, r_multiple = self._calculate_exit_pnl(
                            position, exit_price, shares_exited
                        )

                        self.equity += pnl
                        position['shares_remaining'] -= shares_exited

                        position['exits'].append({
                            'reason': 'R2',
                            'price': exit_price,
                            'shares': shares_exited,
                            'pnl': pnl
                        })

                        if verbose:
                            print(f"   ✅ {current_time.strftime('%H:%M')} - R2 (1/3) @ ${exit_price:.2f} | {r_multiple:.2f}R | ${pnl:+,.0f}")

                # 3. Check R1 target (scale another 1/3)
                elif low <= position['target_r1'] and len(position['exits']) == 1:
                    # Take 1/3 off at R1
                    exit_price = position['target_r1']
                    shares_exited = position['shares_initial'] // 3

                    if shares_exited > 0:
                        pnl, pnl_pct, r_multiple = self._calculate_exit_pnl(
                            position, exit_price, shares_exited
                        )

                        self.equity += pnl
                        position['shares_remaining'] -= shares_exited

                        position['exits'].append({
                            'reason': 'R1',
                            'price': exit_price,
                            'shares': shares_exited,
                            'pnl': pnl
                        })

                        if verbose:
                            print(f"   ✅ {current_time.strftime('%H:%M')} - R1 (1/3) @ ${exit_price:.2f} | {r_multiple:.2f}R | ${pnl:+,.0f}")

                # 4. Check VWAP target (runner - final 1/3)
                elif low <= current_vwap and len(position['exits']) == 2:
                    # Close runner at VWAP
                    exit_price = current_vwap
                    shares_exited = position['shares_remaining']

                    if shares_exited > 0:
                        pnl, pnl_pct, r_multiple = self._calculate_exit_pnl(
                            position, exit_price, shares_exited
                        )

                        self.equity += pnl

                        trade = Trade(
                            symbol=symbol,
                            entry_time=position['entry_time'],
                            exit_time=current_time,
                            setup_type=position['signal']['setup_type'],
                            entry_price=position['entry_price'],
                            exit_price=exit_price,
                            shares=shares_exited,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            r_multiple=r_multiple,
                            conviction=position['signal']['conviction'],
                            exit_reason='VWAP'
                        )
                        day_trades.append(trade)
                        self.trades.append(trade)
                        active_positions.remove(position)

                        if verbose:
                            print(f"   ✅ {current_time.strftime('%H:%M')} - VWAP (runner) @ ${exit_price:.2f} | {r_multiple:.2f}R | ${pnl:+,.0f}")

            # 5. Check end of day (close all at 3:55 PM)
            if current_time.time() >= datetime.strptime('15:55', '%H:%M').time():
                for position in active_positions[:]:
                    exit_price = close
                    shares_exited = position['shares_remaining']

                    if shares_exited > 0:
                        pnl, pnl_pct, r_multiple = self._calculate_exit_pnl(
                            position, exit_price, shares_exited
                        )

                        self.equity += pnl

                        trade = Trade(
                            symbol=symbol,
                            entry_time=position['entry_time'],
                            exit_time=current_time,
                            setup_type=position['signal']['setup_type'],
                            entry_price=position['entry_price'],
                            exit_price=exit_price,
                            shares=shares_exited,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            r_multiple=r_multiple,
                            conviction=position['signal']['conviction'],
                            exit_reason='EOD'
                        )
                        day_trades.append(trade)
                        self.trades.append(trade)
                        active_positions.remove(position)

                        if verbose:
                            print(f"   ⏰ {current_time.strftime('%H:%M')} - EOD @ ${exit_price:.2f} | {r_multiple:.2f}R | ${pnl:+,.0f}")

            # 6. Check daily kill switch
            day_pnl = self.equity - day_start_equity
            if day_pnl / day_start_equity < -strategy.max_daily_loss:
                if verbose:
                    print(f"   🛑 KILL SWITCH TRIGGERED: {day_pnl/day_start_equity:.2%} loss")
                break

        # Day summary
        day_pnl = self.equity - day_start_equity
        day_date = bars.iloc[0]['timestamp'].date()
        self.daily_pnl[day_date] = day_pnl

        if verbose:
            print(f"\n📊 Day Summary:")
            print(f"   Trades: {len(day_trades)}")
            print(f"   Day P&L: ${day_pnl:+,.2f} ({day_pnl/day_start_equity:+.2%})")
            print(f"   Ending Equity: ${self.equity:,.2f}")

        return {
            'trades': day_trades,
            'pnl': day_pnl,
            'ending_equity': self.equity
        }

    def _calculate_exit_pnl(self,
                           position: Dict,
                           exit_price: float,
                           shares: int) -> Tuple[float, float, float]:
        """Calculate P&L for partial or full exit"""
        entry_price = position['entry_price']
        risk_per_share = position['signal']['risk_per_share']

        # For shorts: profit = entry - exit
        pnl_per_share = entry_price - exit_price
        pnl_pct = pnl_per_share / entry_price

        # Commission
        commission = shares * self.commission_per_share
        pnl_gross = pnl_per_share * shares
        pnl_net = pnl_gross - commission

        # R-multiple
        r_multiple = pnl_per_share / risk_per_share if risk_per_share > 0 else 0

        return (pnl_net, pnl_pct, r_multiple)

    def print_results(self):
        """Print backtest results"""
        if not self.trades:
            print("\n❌ No trades executed")
            return

        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")

        # Overall metrics
        total_return = (self.equity - self.initial_capital) / self.initial_capital
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        avg_r = np.mean([t.r_multiple for t in self.trades])

        gross_wins = sum(t.pnl for t in winning_trades)
        gross_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0

        print(f"\n📈 Performance:")
        print(f"   Initial Capital: ${self.initial_capital:,.0f}")
        print(f"   Ending Equity: ${self.equity:,.0f}")
        print(f"   Total Return: {total_return:+.2%}")
        print(f"   Net P&L: ${self.equity - self.initial_capital:+,.0f}")

        print(f"\n📊 Trade Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {len(winning_trades)} ({win_rate:.1%})")
        print(f"   Losing Trades: {len(losing_trades)}")
        print(f"   Average Win: ${avg_win:,.0f}")
        print(f"   Average Loss: ${avg_loss:,.0f}")
        print(f"   Average R: {avg_r:.2f}R")
        print(f"   Profit Factor: {profit_factor:.2f}")

        # By setup type
        print(f"\n🎯 By Setup Type:")
        for setup in ['PARABOLIC', 'FIRST_RED_DAY', 'BACKSIDE']:
            setup_trades = [t for t in self.trades if t.setup_type == setup]
            if setup_trades:
                setup_wins = [t for t in setup_trades if t.pnl > 0]
                setup_wr = len(setup_wins) / len(setup_trades)
                setup_pnl = sum(t.pnl for t in setup_trades)
                setup_avg_r = np.mean([t.r_multiple for t in setup_trades])
                print(f"   {setup}:")
                print(f"      Trades: {len(setup_trades)} | WR: {setup_wr:.1%} | Avg R: {setup_avg_r:.2f}R | P&L: ${setup_pnl:+,.0f}")

        # By conviction
        print(f"\n🎖️  By Conviction:")
        for conviction in ['HIGH', 'MEDIUM', 'LOW']:
            conv_trades = [t for t in self.trades if t.conviction == conviction]
            if conv_trades:
                conv_wins = [t for t in conv_trades if t.pnl > 0]
                conv_wr = len(conv_wins) / len(conv_trades)
                conv_pnl = sum(t.pnl for t in conv_trades)
                conv_avg_r = np.mean([t.r_multiple for t in conv_trades])
                print(f"   {conviction}:")
                print(f"      Trades: {len(conv_trades)} | WR: {conv_wr:.1%} | Avg R: {conv_avg_r:.2f}R | P&L: ${conv_pnl:+,.0f}")


def main():
    """Run backtest example"""
    print("Temiz Small-Cap Short Strategy - Backtest")
    print("="*60)

    # NOTE: Replace with your Alpaca paper API keys
    # Free account: https://alpaca.markets
    print("\n⚠️  To run this backtest, you need Alpaca API keys.")
    print("   1. Sign up at https://alpaca.markets (free)")
    print("   2. Get paper trading API keys")
    print("   3. Replace 'YOUR_PAPER_KEY' and 'YOUR_PAPER_SECRET' below\n")

    # Example: Backtest GME on Jan 28, 2021 (famous short squeeze)
    # (You would need Alpaca keys to actually download data)

    print("Example backtest structure:")
    print("""
    # Initialize data loader
    loader = AlpacaDataLoader(
        api_key='YOUR_PAPER_KEY',
        secret_key='YOUR_PAPER_SECRET',
        paper=True
    )

    # Download 1-minute data for GME
    bars = loader.get_1min_bars('GME', '2021-01-28', '2021-01-28')

    # Initialize strategy
    strategy = TemizSmallCapShortStrategy(
        risk_per_trade=0.005,  # 0.5% risk
        max_daily_loss=0.02    # 2% kill switch
    )

    # Run backtest
    backtester = TemizBacktester(initial_capital=100000)
    results = backtester.backtest_single_day('GME', bars, strategy, verbose=True)

    # Print results
    backtester.print_results()
    """)


if __name__ == '__main__':
    main()
