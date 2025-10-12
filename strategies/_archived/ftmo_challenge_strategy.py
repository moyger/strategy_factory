"""
FTMO Challenge Strategy

Trading strategy compliant with FTMO prop firm challenge rules.

FTMO Rules:
- Maximum daily loss: 5% of starting balance
- Maximum total loss: 10% of starting balance
- Minimum trading days: 4
- Profit target: 10% of starting balance

This strategy implements strict risk management to pass FTMO challenges.

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
import sys
sys.path.append('..')

from strategy_factory.risk_management import (
    RiskCalculator,
    PositionSizer,
    FTMOChecker,
    SessionFilter,
    VolatilityFilter
)


class FTMOChallengeStrategy:
    """
    FTMO-compliant trading strategy

    Conservative approach designed to pass FTMO challenges:
    - 1% risk per trade maximum
    - Only trade during major sessions (London/NY)
    - Strict ATR-based stops
    - Profit targets set for favorable risk/reward

    Parameters:
        challenge_size: '10k', '25k', '50k', '100k', or '200k'
        risk_per_trade: Risk per trade as % (max 1% recommended)
        atr_period: ATR calculation period
        atr_sl_multiplier: Stop loss in ATR units
        atr_tp_multiplier: Take profit in ATR units
        session_filter: Trade only during specific sessions
        require_trend: Require trend confirmation
    """

    def __init__(self,
                 challenge_size: str = '50k',
                 risk_per_trade: float = 1.0,
                 atr_period: int = 14,
                 atr_sl_multiplier: float = 2.0,
                 atr_tp_multiplier: float = 4.0,  # 2:1 RR minimum
                 session_filter: bool = True,
                 require_trend: bool = True):

        self.challenge_size = challenge_size
        self.risk_per_trade = risk_per_trade
        self.atr_period = atr_period
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp_multiplier = atr_tp_multiplier
        self.session_filter = session_filter
        self.require_trend = require_trend

        # Initialize FTMO checker
        self.ftmo_checker = FTMOChecker(challenge_size=challenge_size)
        self.specs = self.ftmo_checker.specs

        self.name = f"FTMO_{challenge_size}_R{risk_per_trade}"

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate FTMO-compliant trading signals

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with signals and risk management levels
        """
        df = df.copy()

        # Calculate ATR
        df['atr'] = RiskCalculator.calculate_atr(df, period=self.atr_period)

        # Trend detection (EMA crossover)
        df['ema_fast'] = df['close'].ewm(span=20).mean()
        df['ema_slow'] = df['close'].ewm(span=50).mean()

        if self.require_trend:
            df['trend_up'] = df['ema_fast'] > df['ema_slow']
            df['trend_down'] = df['ema_fast'] < df['ema_slow']
        else:
            df['trend_up'] = True
            df['trend_down'] = True

        # Session filter (only trade London/NY)
        if self.session_filter:
            df['in_session'] = SessionFilter.is_session_open(
                df.index,
                sessions=['london', 'new_york']
            )
        else:
            df['in_session'] = True

        # Volatility filter (avoid low volatility)
        df['normal_volatility'] = ~VolatilityFilter.is_low_volatility(
            df,
            atr_period=self.atr_period,
            threshold_multiplier=0.5
        )

        # Entry signals: EMA crossover with filters
        buy_condition = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)) &
            (df['in_session']) &
            (df['normal_volatility']) &
            (df['trend_up'])
        )

        sell_condition = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)) &
            (df['in_session']) &
            (df['normal_volatility']) &
            (df['trend_down'])
        )

        # Assign signals
        df['signal'] = None
        df.loc[buy_condition, 'signal'] = 'BUY'
        df.loc[sell_condition, 'signal'] = 'SELL'

        # Calculate stop loss (ATR-based, conservative)
        df['stop_loss_distance'] = df['atr'] * self.atr_sl_multiplier
        df['stop_loss_price'] = df['close'] - df['stop_loss_distance']

        # Calculate take profit (minimum 2:1 reward/risk)
        df['take_profit_distance'] = df['atr'] * self.atr_tp_multiplier
        df['take_profit_price'] = df['close'] + df['take_profit_distance']

        # FTMO-compliant position sizing (1% risk max)
        df['position_size'] = PositionSizer.fixed_percent_risk(
            account_balance=self.specs['balance'],
            risk_percent=self.risk_per_trade,
            stop_distance=df['stop_loss_distance']
        )

        return df

    def backtest(self, df: pd.DataFrame):
        """
        Run backtest and check FTMO rules

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dict with portfolio and FTMO compliance results
        """
        import vectorbt as vbt

        # Generate signals
        df_signals = self.generate_signals(df)

        # Convert to boolean
        entries = (df_signals['signal'] == 'BUY')
        exits = (df_signals['signal'] == 'SELL')

        # Run backtest
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'].values,
            entries=entries,
            exits=exits,

            # Conservative position sizing
            size=df_signals['position_size'].values,
            size_type='amount',

            # Conservative ATR stops
            sl_stop=df_signals['stop_loss_distance'].values,
            sl_trail=True,  # Trailing to protect profits

            # Take profit targets
            tp_stop=df_signals['take_profit_price'].values,

            # OHLC for intrabar execution
            high=df['high'].values,
            low=df['low'].values,
            open=df['open'].values,

            # Realistic costs
            fees=0.001,
            slippage=0.0005,

            init_cash=self.specs['balance']
        )

        # Check FTMO rules
        equity_curve = portfolio.value()

        # Get trade dates
        if portfolio.trades.count() > 0:
            trade_records = portfolio.trades.records_readable
            trade_dates = pd.to_datetime(trade_records['Entry Timestamp'])
        else:
            trade_dates = pd.Series(dtype='datetime64[ns]')

        ftmo_results = self.ftmo_checker.check_all_rules(
            equity_curve=equity_curve,
            trade_dates=trade_dates
        )

        # Combine results
        results = {
            'portfolio': portfolio,
            'ftmo_check': ftmo_results,
            'challenge_passed': ftmo_results['challenge_passed'],
            'strategy_params': self.get_parameters()
        }

        return results

    def print_results(self, results: dict):
        """Print formatted backtest and FTMO results"""
        portfolio = results['portfolio']
        ftmo = results['ftmo_check']

        print("\n" + "=" * 80)
        print(f"FTMO {self.challenge_size} CHALLENGE - BACKTEST RESULTS")
        print("=" * 80)

        # Strategy info
        print(f"\n📊 Strategy: {self.name}")
        print(f"   Starting Balance: ${self.specs['balance']:,}")

        # Performance metrics
        print(f"\n📈 Performance:")
        print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
        print(f"   Final Equity: ${portfolio.value().iloc[-1]:,.2f}")
        print(f"   Profit/Loss: ${(portfolio.value().iloc[-1] - self.specs['balance']):,.2f}")
        print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
        print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")

        # Trade statistics
        print(f"\n💼 Trades:")
        print(f"   Number of Trades: {portfolio.trades.count()}")

        if portfolio.trades.count() > 0:
            print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
            print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
            print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
            print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")
            print(f"   Best Trade: ${portfolio.trades.pnl.max():.2f}")
            print(f"   Worst Trade: ${portfolio.trades.pnl.min():.2f}")

        # FTMO rule checks
        print(f"\n{'='*80}")
        print(f"FTMO CHALLENGE RULES CHECK")
        print(f"{'='*80}")

        print(f"\n✓ Daily Loss Limit Check:")
        dl = ftmo['daily_loss_check']
        print(f"   Status: {dl['message']}")
        print(f"   Violations: {dl['num_violations']}")
        print(f"   Worst Day: ${dl['worst_day_pnl']:.2f}")

        print(f"\n✓ Max Drawdown Check:")
        md = ftmo['max_drawdown_check']
        print(f"   Status: {md['message']}")
        print(f"   Max Loss: ${md['max_loss']:.2f} ({md['max_loss_pct']:.2f}%)")

        print(f"\n✓ Profit Target Check:")
        pt = ftmo['profit_target_check']
        print(f"   Status: {pt['message']}")
        print(f"   Profit: ${pt['profit']:.2f} ({pt['profit_pct']:.2f}%)")

        print(f"\n✓ Trading Days Check:")
        td = ftmo['trading_days_check']
        print(f"   Status: {td['message']}")

        # Final verdict
        print(f"\n{'='*80}")
        if ftmo['challenge_passed']:
            print(f"✅ {ftmo['summary']}")
            print(f"🎉 Congratulations! Strategy passed FTMO {self.challenge_size} challenge!")
        else:
            print(f"❌ {ftmo['summary']}")
            print(f"💡 Strategy needs adjustment to pass FTMO challenge.")
        print(f"{'='*80}\n")

    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'challenge_size': self.challenge_size,
            'risk_per_trade': self.risk_per_trade,
            'atr_period': self.atr_period,
            'atr_sl_multiplier': self.atr_sl_multiplier,
            'atr_tp_multiplier': self.atr_tp_multiplier,
            'session_filter': self.session_filter,
            'require_trend': self.require_trend
        }

    def __str__(self):
        return f"FTMO {self.challenge_size} Challenge Strategy (Risk: {self.risk_per_trade}%, RR: 1:{self.atr_tp_multiplier/self.atr_sl_multiplier:.1f})"


# Example usage
if __name__ == "__main__":
    import pandas as pd

    # Load data
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use recent data (last 6 months for faster test)
    df = df.tail(50000)

    print("=" * 80)
    print("FTMO CHALLENGE STRATEGY - BACKTEST")
    print("=" * 80)

    # Create strategy
    strategy = FTMOChallengeStrategy(
        challenge_size='50k',
        risk_per_trade=1.0,
        atr_period=14,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=4.0,
        session_filter=False,  # Disable for 24/7 crypto
        require_trend=True
    )

    print(f"\nStrategy: {strategy}")
    print(f"Challenge: ${strategy.specs['balance']:,} account")

    # Run backtest
    print(f"\n📊 Running backtest on {len(df):,} bars...")
    results = strategy.backtest(df)

    # Print results
    strategy.print_results(results)
