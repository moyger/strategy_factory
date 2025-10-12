"""
ATR Trailing Stop Strategy

Advanced breakout strategy with ATR-based trailing stop loss.

Features:
- ATR-based dynamic stop loss
- Trailing stop that moves with price
- ATR-based take profit
- Volatility filtering
- Position sizing based on ATR risk

Author: Strategy Factory
"""

import pandas as pd
import numpy as np
import sys
sys.path.append('..')

from strategy_factory.risk_management import (
    RiskCalculator,
    PositionSizer,
    VolatilityFilter
)


class ATRTrailingStopStrategy:
    """
    Breakout strategy with ATR-based trailing stops

    Entry: Price breaks above recent high
    Stop Loss: ATR-based trailing stop
    Take Profit: ATR-based target

    Parameters:
        lookback: Lookback period for breakout detection
        breakout_pct: Breakout percentage threshold
        atr_period: ATR calculation period
        atr_sl_multiplier: Stop loss distance in ATR units
        atr_tp_multiplier: Take profit distance in ATR units
        use_trailing_stop: Enable trailing stop
        risk_percent: Risk per trade as percentage of account
        require_high_volatility: Only trade during high volatility
    """

    def __init__(self,
                 lookback: int = 20,
                 breakout_pct: float = 1.0,
                 atr_period: int = 14,
                 atr_sl_multiplier: float = 2.0,
                 atr_tp_multiplier: float = 3.0,
                 use_trailing_stop: bool = True,
                 risk_percent: float = 1.0,
                 require_high_volatility: bool = False):

        self.lookback = lookback
        self.breakout_pct = breakout_pct
        self.atr_period = atr_period
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_tp_multiplier = atr_tp_multiplier
        self.use_trailing_stop = use_trailing_stop
        self.risk_percent = risk_percent
        self.require_high_volatility = require_high_volatility

        self.name = f"ATR_Trailing_{lookback}_{breakout_pct}_{atr_sl_multiplier}x{atr_tp_multiplier}"

    def generate_signals(self, df: pd.DataFrame, account_balance: float = 10000) -> pd.DataFrame:
        """
        Generate trading signals with ATR-based stops

        Args:
            df: DataFrame with OHLCV data
            account_balance: Current account balance for position sizing

        Returns:
            DataFrame with signals and stop/target levels
        """
        df = df.copy()

        # Calculate ATR
        df['atr'] = RiskCalculator.calculate_atr(df, period=self.atr_period)

        # Calculate rolling high/low for breakout
        df['rolling_high'] = df['high'].rolling(self.lookback).max()
        df['rolling_low'] = df['low'].rolling(self.lookback).min()

        # Breakout thresholds
        df['buy_threshold'] = df['rolling_high'] * (1 + self.breakout_pct / 100)
        df['sell_threshold'] = df['rolling_low'] * (1 - self.breakout_pct / 100)

        # Volatility filter (optional)
        if self.require_high_volatility:
            df['high_volatility'] = VolatilityFilter.is_high_volatility(
                df,
                atr_period=self.atr_period,
                threshold_multiplier=1.5
            )
        else:
            df['high_volatility'] = True

        # Entry signals
        buy_condition = (
            (df['close'] > df['buy_threshold'].shift(1)) &
            (df['high_volatility'])
        )

        sell_condition = (
            (df['close'] < df['sell_threshold'].shift(1)) &
            (df['high_volatility'])
        )

        # Assign signals
        df['signal'] = None
        df.loc[buy_condition, 'signal'] = 'BUY'
        df.loc[sell_condition, 'signal'] = 'SELL'

        # Calculate stop loss levels (ATR-based)
        df['stop_loss_distance'] = df['atr'] * self.atr_sl_multiplier
        df['stop_loss_price'] = df['close'] - df['stop_loss_distance']

        # Calculate take profit levels (ATR-based)
        df['take_profit_distance'] = df['atr'] * self.atr_tp_multiplier
        df['take_profit_price'] = df['close'] + df['take_profit_distance']

        # Calculate position size based on risk
        df['position_size'] = PositionSizer.fixed_percent_risk(
            account_balance=account_balance,
            risk_percent=self.risk_percent,
            stop_distance=df['stop_loss_distance']
        )

        return df

    def backtest(self, df: pd.DataFrame, initial_capital: float = 10000):
        """
        Run backtest with ATR trailing stops

        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital

        Returns:
            vectorbt Portfolio object
        """
        import vectorbt as vbt

        # Generate signals
        df_signals = self.generate_signals(df, initial_capital)

        # Convert to boolean arrays
        entries = (df_signals['signal'] == 'BUY')
        exits = (df_signals['signal'] == 'SELL')

        # Run backtest with advanced features
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'].values,
            entries=entries,
            exits=exits,

            # Dynamic position sizing based on ATR risk
            size=df_signals['position_size'].values,
            size_type='amount',

            # ATR-based stop loss (trailing!)
            sl_stop=df_signals['stop_loss_distance'].values,
            sl_trail=self.use_trailing_stop,

            # ATR-based take profit
            tp_stop=df_signals['take_profit_price'].values,

            # OHLC data for intrabar stop execution
            high=df['high'].values,
            low=df['low'].values,
            open=df['open'].values,

            # Fees and slippage
            fees=0.001,      # 0.1% commission
            slippage=0.0005, # 0.05% slippage

            init_cash=initial_capital
        )

        return portfolio

    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'lookback': self.lookback,
            'breakout_pct': self.breakout_pct,
            'atr_period': self.atr_period,
            'atr_sl_multiplier': self.atr_sl_multiplier,
            'atr_tp_multiplier': self.atr_tp_multiplier,
            'use_trailing_stop': self.use_trailing_stop,
            'risk_percent': self.risk_percent,
            'require_high_volatility': self.require_high_volatility
        }

    def __str__(self):
        trail_str = "Trailing" if self.use_trailing_stop else "Fixed"
        return f"ATR {trail_str} Stop Strategy (L={self.lookback}, SL={self.atr_sl_multiplier}x ATR, TP={self.atr_tp_multiplier}x ATR)"


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

    print("=" * 80)
    print("ATR TRAILING STOP STRATEGY - BACKTEST")
    print("=" * 80)

    # Create strategy
    strategy = ATRTrailingStopStrategy(
        lookback=20,
        breakout_pct=1.0,
        atr_period=14,
        atr_sl_multiplier=2.0,
        atr_tp_multiplier=3.0,
        use_trailing_stop=True,
        risk_percent=1.0
    )

    print(f"\nStrategy: {strategy}")
    print(f"Parameters: {strategy.get_parameters()}")

    # Run backtest
    print(f"\n📊 Running backtest on {len(df):,} bars...")
    portfolio = strategy.backtest(df, initial_capital=10000)

    # Print results
    print(f"\n✅ Backtest Results:")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
    print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
    print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")
    print(f"   Number of Trades: {portfolio.trades.count()}")
    print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")

    if portfolio.trades.count() > 0:
        print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
        print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
        print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")

    print("\n" + "=" * 80)
