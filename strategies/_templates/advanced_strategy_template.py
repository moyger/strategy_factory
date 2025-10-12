"""
Advanced Strategy Template

Full-featured strategy template demonstrating ALL advanced capabilities:
- ATR-based trailing stops
- Dynamic position sizing (Kelly Criterion, Fixed %, Volatility-based)
- FTMO rule compliance
- Session-based filtering
- Volatility filtering
- Multi-timeframe confirmation
- Risk/Reward optimization
- Trade journaling

This is the ULTIMATE template showing every feature available.
Use this as a starting point for your own advanced strategies.

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


class AdvancedStrategyTemplate:
    """
    Ultra-advanced trading strategy with all bells and whistles

    Features:
    ✅ ATR-based trailing stops
    ✅ Dynamic position sizing
    ✅ FTMO compliance checking
    ✅ Session filtering
    ✅ Volatility filtering
    ✅ Multi-timeframe analysis
    ✅ Risk/Reward targeting
    ✅ Performance tracking

    Parameters:
        # Strategy Logic
        fast_period: Fast EMA period
        slow_period: Slow EMA period

        # Risk Management
        atr_period: ATR calculation period
        atr_sl_multiplier: Stop loss distance (ATR units)
        atr_tp_multiplier: Take profit distance (ATR units)
        use_trailing_stop: Enable trailing stop loss

        # Position Sizing
        sizing_method: 'fixed_percent', 'kelly', or 'volatility'
        risk_percent: Risk per trade (for fixed_percent)
        kelly_fraction: Fraction of Kelly to use (for kelly)
        target_volatility: Target portfolio volatility (for volatility)

        # Filters
        session_filter: Trade only during specific sessions
        sessions: List of sessions ['london', 'new_york', etc.]
        require_high_volatility: Only trade high volatility periods
        min_atr_threshold: Minimum ATR to allow trades

        # FTMO Compliance
        check_ftmo_rules: Enable FTMO rule checking
        ftmo_challenge_size: '10k', '50k', etc.
        max_daily_loss_pct: Max daily loss percentage
        max_total_loss_pct: Max total loss percentage

        # Multi-Timeframe
        use_htf_filter: Use higher timeframe trend filter
        htf_period: Higher timeframe EMA period
    """

    def __init__(self,
                 # Strategy params
                 fast_period: int = 20,
                 slow_period: int = 50,

                 # Risk management
                 atr_period: int = 14,
                 atr_sl_multiplier: float = 2.0,
                 atr_tp_multiplier: float = 4.0,
                 use_trailing_stop: bool = True,

                 # Position sizing
                 sizing_method: str = 'fixed_percent',
                 risk_percent: float = 1.0,
                 kelly_fraction: float = 0.5,
                 target_volatility: float = 0.01,

                 # Filters
                 session_filter: bool = False,
                 sessions: list = ['london', 'new_york'],
                 require_high_volatility: bool = False,
                 min_atr_threshold: float = 0.0,

                 # FTMO
                 check_ftmo_rules: bool = False,
                 ftmo_challenge_size: str = '50k',
                 max_daily_loss_pct: float = 5.0,
                 max_total_loss_pct: float = 10.0,

                 # Multi-timeframe
                 use_htf_filter: bool = False,
                 htf_period: int = 200):

        # Store all parameters
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_period = atr_period
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp_multiplier = atr_tp_multiplier
        self.use_trailing_stop = use_trailing_stop
        self.sizing_method = sizing_method
        self.risk_percent = risk_percent
        self.kelly_fraction = kelly_fraction
        self.target_volatility = target_volatility
        self.session_filter = session_filter
        self.sessions = sessions
        self.require_high_volatility = require_high_volatility
        self.min_atr_threshold = min_atr_threshold
        self.check_ftmo_rules = check_ftmo_rules
        self.ftmo_challenge_size = ftmo_challenge_size
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_total_loss_pct = max_total_loss_pct
        self.use_htf_filter = use_htf_filter
        self.htf_period = htf_period

        # Initialize FTMO checker if needed
        if self.check_ftmo_rules:
            self.ftmo_checker = FTMOChecker(challenge_size=ftmo_challenge_size)
            self.starting_balance = self.ftmo_checker.specs['balance']
        else:
            self.starting_balance = 10000

        self.name = f"Advanced_{sizing_method}_{fast_period}x{slow_period}"

    def calculate_position_size(self,
                                df: pd.DataFrame,
                                account_balance: float,
                                win_rate: float = 0.5,
                                avg_win: float = 100,
                                avg_loss: float = 50) -> pd.Series:
        """
        Calculate position size using selected method

        Args:
            df: DataFrame with signals
            account_balance: Current account balance
            win_rate: Historical win rate (for Kelly)
            avg_win: Average win size (for Kelly)
            avg_loss: Average loss size (for Kelly)

        Returns:
            Series with position sizes
        """
        if self.sizing_method == 'fixed_percent':
            return PositionSizer.fixed_percent_risk(
                account_balance=account_balance,
                risk_percent=self.risk_percent,
                stop_distance=df['stop_loss_distance']
            )

        elif self.sizing_method == 'kelly':
            kelly_size = PositionSizer.kelly_criterion(
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                account_balance=account_balance,
                kelly_fraction=self.kelly_fraction
            )
            # Convert to per-trade position size
            return pd.Series(kelly_size, index=df.index)

        elif self.sizing_method == 'volatility':
            return PositionSizer.volatility_based(
                df=df,
                account_balance=account_balance,
                target_volatility=self.target_volatility,
                atr_period=self.atr_period
            )

        else:
            raise ValueError(f"Unknown sizing method: {self.sizing_method}")

    def generate_signals(self, df: pd.DataFrame, account_balance: float = None) -> pd.DataFrame:
        """
        Generate trading signals with ALL advanced features

        Args:
            df: DataFrame with OHLCV data
            account_balance: Current account balance (uses starting balance if None)

        Returns:
            DataFrame with signals, stops, and all indicators
        """
        df = df.copy()

        if account_balance is None:
            account_balance = self.starting_balance

        # ========================================
        # STEP 1: Calculate Indicators
        # ========================================

        # ATR for risk management
        df['atr'] = RiskCalculator.calculate_atr(df, period=self.atr_period)

        # EMAs for trend
        df['ema_fast'] = df['close'].ewm(span=self.fast_period).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period).mean()

        # Higher timeframe trend (if enabled)
        if self.use_htf_filter:
            df['ema_htf'] = df['close'].ewm(span=self.htf_period).mean()
            df['htf_bullish'] = df['close'] > df['ema_htf']
            df['htf_bearish'] = df['close'] < df['ema_htf']
        else:
            df['htf_bullish'] = True
            df['htf_bearish'] = True

        # ========================================
        # STEP 2: Apply Filters
        # ========================================

        # Session filter
        if self.session_filter:
            df['in_session'] = SessionFilter.is_session_open(df.index, self.sessions)
        else:
            df['in_session'] = True

        # Volatility filters
        if self.require_high_volatility:
            df['high_vol'] = VolatilityFilter.is_high_volatility(df, self.atr_period)
        else:
            df['high_vol'] = True

        # Minimum ATR threshold
        df['above_atr_threshold'] = df['atr'] > self.min_atr_threshold

        # ========================================
        # STEP 3: Generate Entry Signals
        # ========================================

        # Basic signal: EMA crossover
        buy_signal = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        )

        sell_signal = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
        )

        # Apply all filters
        buy_condition = (
            buy_signal &
            df['in_session'] &
            df['high_vol'] &
            df['above_atr_threshold'] &
            df['htf_bullish']
        )

        sell_condition = (
            sell_signal &
            df['in_session'] &
            df['high_vol'] &
            df['above_atr_threshold'] &
            df['htf_bearish']
        )

        # Assign signals
        df['signal'] = None
        df.loc[buy_condition, 'signal'] = 'BUY'
        df.loc[sell_condition, 'signal'] = 'SELL'

        # ========================================
        # STEP 4: Calculate Risk Management Levels
        # ========================================

        # Stop loss (ATR-based)
        df['stop_loss_distance'] = df['atr'] * self.atr_sl_multiplier
        df['stop_loss_price'] = df['close'] - df['stop_loss_distance']

        # Take profit (ATR-based, favorable RR)
        df['take_profit_distance'] = df['atr'] * self.atr_tp_multiplier
        df['take_profit_price'] = df['close'] + df['take_profit_distance']

        # Risk/Reward ratio
        df['risk_reward_ratio'] = df['take_profit_distance'] / df['stop_loss_distance']

        # ========================================
        # STEP 5: Calculate Position Sizing
        # ========================================

        df['position_size'] = self.calculate_position_size(
            df=df,
            account_balance=account_balance
        )

        # ========================================
        # STEP 6: Add Trade Journal Info
        # ========================================

        df['entry_reason'] = ''
        df.loc[buy_condition, 'entry_reason'] = 'EMA Cross + Filters'
        df.loc[sell_condition, 'entry_reason'] = 'EMA Cross + Filters'

        df['expected_profit'] = df['position_size'] * df['take_profit_distance']
        df['expected_loss'] = df['position_size'] * df['stop_loss_distance']

        return df

    def backtest(self, df: pd.DataFrame, initial_capital: float = None):
        """
        Run backtest with all advanced features

        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital (uses FTMO balance if checking rules)

        Returns:
            Dict with portfolio and analysis results
        """
        import vectorbt as vbt

        if initial_capital is None:
            initial_capital = self.starting_balance

        # Generate signals
        df_signals = self.generate_signals(df, initial_capital)

        # Convert to boolean
        entries = (df_signals['signal'] == 'BUY')
        exits = (df_signals['signal'] == 'SELL')

        # Run backtest
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'].values,
            entries=entries,
            exits=exits,

            # Dynamic position sizing
            size=df_signals['position_size'].values,
            size_type='amount',

            # ATR-based stops
            sl_stop=df_signals['stop_loss_distance'].values,
            sl_trail=self.use_trailing_stop,

            # Take profit targets
            tp_stop=df_signals['take_profit_price'].values,

            # OHLC for intrabar execution
            high=df['high'].values,
            low=df['low'].values,
            open=df['open'].values,

            # Costs
            fees=0.001,
            slippage=0.0005,

            init_cash=initial_capital
        )

        # Prepare results
        results = {
            'portfolio': portfolio,
            'signals_df': df_signals,
            'strategy_params': self.get_parameters()
        }

        # Check FTMO rules if enabled
        if self.check_ftmo_rules:
            equity_curve = portfolio.value()

            if portfolio.trades.count() > 0:
                trade_records = portfolio.trades.records_readable
                trade_dates = pd.to_datetime(trade_records['Entry Timestamp'])
            else:
                trade_dates = pd.Series(dtype='datetime64[ns]')

            ftmo_results = self.ftmo_checker.check_all_rules(
                equity_curve=equity_curve,
                trade_dates=trade_dates
            )

            results['ftmo_check'] = ftmo_results
            results['challenge_passed'] = ftmo_results['challenge_passed']

        return results

    def print_results(self, results: dict):
        """Print comprehensive results"""
        portfolio = results['portfolio']

        print("\n" + "=" * 80)
        print(f"ADVANCED STRATEGY - BACKTEST RESULTS")
        print("=" * 80)

        print(f"\n📊 Strategy: {self.name}")
        print(f"   Sizing Method: {self.sizing_method}")
        print(f"   ATR Stops: {self.atr_sl_multiplier}x / {self.atr_tp_multiplier}x")
        print(f"   Trailing Stop: {self.use_trailing_stop}")

        print(f"\n📈 Performance:")
        print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
        print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
        print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")
        print(f"   Calmar Ratio: {portfolio.calmar_ratio():.2f}")

        print(f"\n💼 Trades:")
        print(f"   Total Trades: {portfolio.trades.count()}")

        if portfolio.trades.count() > 0:
            print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
            print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")
            print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
            print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
            print(f"   Best Trade: ${portfolio.trades.pnl.max():.2f}")
            print(f"   Worst Trade: ${portfolio.trades.pnl.min():.2f}")

        # FTMO results if applicable
        if 'ftmo_check' in results:
            ftmo = results['ftmo_check']
            print(f"\n🏆 FTMO Challenge: {self.ftmo_challenge_size}")
            print(f"   Status: {ftmo['summary']}")
            print(f"   Passed: {'✅ YES' if ftmo['challenge_passed'] else '❌ NO'}")

        print("\n" + "=" * 80)

    def get_parameters(self) -> dict:
        """Get all strategy parameters"""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'atr_period': self.atr_period,
            'atr_sl_multiplier': self.atr_sl_multiplier,
            'atr_tp_multiplier': self.atr_tp_multiplier,
            'use_trailing_stop': self.use_trailing_stop,
            'sizing_method': self.sizing_method,
            'risk_percent': self.risk_percent,
            'session_filter': self.session_filter,
            'sessions': self.sessions,
            'require_high_volatility': self.require_high_volatility,
            'check_ftmo_rules': self.check_ftmo_rules
        }

    def __str__(self):
        return f"Advanced Strategy ({self.sizing_method} sizing, {self.fast_period}x{self.slow_period} EMA, {self.atr_sl_multiplier}:{self.atr_tp_multiplier} RR)"


# Example usage demonstrating all features
if __name__ == "__main__":
    import pandas as pd

    # Load data
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use recent data
    df = df.tail(50000)

    print("=" * 80)
    print("ADVANCED STRATEGY TEMPLATE - DEMO")
    print("=" * 80)

    # Example 1: Fixed percent sizing with FTMO rules
    print("\n\n=== Example 1: FTMO Challenge (Fixed % Risk) ===")
    strategy1 = AdvancedStrategyTemplate(
        fast_period=20,
        slow_period=50,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=4.0,
        use_trailing_stop=True,
        sizing_method='fixed_percent',
        risk_percent=1.0,
        check_ftmo_rules=True,
        ftmo_challenge_size='50k'
    )

    results1 = strategy1.backtest(df)
    strategy1.print_results(results1)

    # Example 2: Kelly Criterion sizing
    print("\n\n=== Example 2: Kelly Criterion Sizing ===")
    strategy2 = AdvancedStrategyTemplate(
        fast_period=20,
        slow_period=50,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=3.0,
        use_trailing_stop=True,
        sizing_method='kelly',
        kelly_fraction=0.5,  # Half Kelly
        require_high_volatility=True
    )

    results2 = strategy2.backtest(df, initial_capital=10000)
    strategy2.print_results(results2)

    # Example 3: Volatility-based sizing
    print("\n\n=== Example 3: Volatility Targeting ===")
    strategy3 = AdvancedStrategyTemplate(
        fast_period=20,
        slow_period=50,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=3.0,
        use_trailing_stop=True,
        sizing_method='volatility',
        target_volatility=0.01,  # 1% daily volatility target
        use_htf_filter=True,
        htf_period=200
    )

    results3 = strategy3.backtest(df, initial_capital=10000)
    strategy3.print_results(results3)

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
