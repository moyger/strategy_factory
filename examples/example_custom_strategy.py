#!/usr/bin/env python3
"""
Example: Create Your Own Custom Strategy

This template shows you how to create a completely custom strategy
from scratch. Use this as a starting point for your own ideas!

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import vectorbt as vbt


class MyCustomStrategy:
    """
    YOUR CUSTOM STRATEGY

    Replace this with your own logic!

    Example: Buy when RSI < 30 AND price above 50 SMA
             Sell when RSI > 70 OR price below 50 SMA
    """

    def __init__(self,
                 rsi_period: int = 14,
                 rsi_oversold: int = 30,
                 rsi_overbought: int = 70,
                 sma_period: int = 50):

        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.sma_period = sma_period
        self.name = "My_Custom_Strategy"

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals

        Args:
            df: DataFrame with OHLCV data (must have: open, high, low, close, volume)

        Returns:
            DataFrame with 'signal' column ('BUY', 'SELL', or None)
        """
        df = df.copy()

        # Calculate indicators
        df['rsi'] = self.calculate_rsi(df['close'])
        df['sma'] = df['close'].rolling(self.sma_period).mean()

        # Define your entry conditions
        buy_condition = (
            (df['rsi'] < self.rsi_oversold) &           # RSI oversold
            (df['close'] > df['sma']) &                 # Price above SMA
            (df['rsi'].shift(1) >= self.rsi_oversold)   # Just crossed oversold
        )

        # Define your exit conditions
        sell_condition = (
            (df['rsi'] > self.rsi_overbought) |         # RSI overbought
            (df['close'] < df['sma'])                   # Price below SMA
        )

        # Assign signals
        df['signal'] = None
        df.loc[buy_condition, 'signal'] = 'BUY'
        df.loc[sell_condition, 'signal'] = 'SELL'

        return df

    def __str__(self):
        return f"Custom Strategy (RSI {self.rsi_period}, SMA {self.sma_period})"


def main():
    print("="*80)
    print("EXAMPLE: CREATE YOUR OWN CUSTOM STRATEGY")
    print("="*80)

    # Step 1: Load data
    print("\n📂 Loading data...")
    df = pd.read_csv('../data/crypto/BTCUSD_5m.csv')
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use last 50k bars
    df = df.tail(50000)

    print(f"✅ Loaded {len(df):,} bars")

    # Step 2: Create your custom strategy
    print("\n📊 Creating custom strategy...")
    strategy = MyCustomStrategy(
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
        sma_period=50
    )

    print(f"   Strategy: {strategy}")

    # Step 3: Generate signals
    print("\n🔍 Generating signals...")
    df_signals = strategy.generate_signals(df)

    buy_signals = (df_signals['signal'] == 'BUY').sum()
    sell_signals = (df_signals['signal'] == 'SELL').sum()

    print(f"   Buy signals: {buy_signals}")
    print(f"   Sell signals: {sell_signals}")

    # Step 4: Run backtest
    print("\n📈 Running backtest...")

    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001,
        slippage=0.0005
    )

    # Step 5: Print results
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)

    print(f"\n📈 Performance:")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
    print(f"   Final Equity: ${portfolio.value().iloc[-1]:,.2f}")
    print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
    print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")

    print(f"\n💼 Trades:")
    print(f"   Number of Trades: {portfolio.trades.count()}")

    if portfolio.trades.count() > 0:
        print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
        print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
        print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
        print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")

    # Step 6: How to improve your strategy
    print("\n" + "="*80)
    print("HOW TO CUSTOMIZE THIS STRATEGY")
    print("="*80)

    print("""
1. ADD MORE INDICATORS:
   - MACD, Bollinger Bands, ADX, etc.
   - Import from TA-Lib or calculate manually
   - Combine multiple indicators for confirmation

2. IMPROVE ENTRY/EXIT LOGIC:
   - Use multiple timeframes (5min + 1hour)
   - Add volume confirmation
   - Use support/resistance levels
   - Add trend filters

3. ADD RISK MANAGEMENT:
   from strategy_factory.risk_management import RiskCalculator, PositionSizer

   # ATR-based stops
   df['atr'] = RiskCalculator.calculate_atr(df, period=14)
   df['stop_loss'] = df['close'] - df['atr'] * 2

   # Position sizing
   df['position_size'] = PositionSizer.fixed_percent_risk(
       account_balance=10000,
       risk_percent=1.0,
       stop_distance=df['atr'] * 2
   )

4. ADD FILTERS:
   from strategy_factory.risk_management import SessionFilter, VolatilityFilter

   # Only trade during specific sessions
   df['in_session'] = SessionFilter.is_session_open(
       df.index,
       sessions=['london', 'new_york']
   )

   # Only trade during high volatility
   df['high_vol'] = VolatilityFilter.is_high_volatility(df)

5. TEST THOROUGHLY:
   - Walk-forward analysis
   - Monte Carlo simulation
   - Out-of-sample testing
   - Different market conditions

6. OPTIMIZE PARAMETERS:
   from strategy_factory.optimizer import StrategyOptimizer

   optimizer = StrategyOptimizer()
   best_params = optimizer.optimize_genetic(
       strategy_class=MyCustomStrategy,
       df=df,
       param_ranges={
           'rsi_period': (10, 20),
           'rsi_oversold': (20, 40),
           'rsi_overbought': (60, 80),
           'sma_period': (20, 100)
       }
   )
    """)

    print("\n✅ Example completed!")
    print("\nNext steps:")
    print("   1. Modify the strategy logic in MyCustomStrategy class")
    print("   2. Add your own indicators and conditions")
    print("   3. Test on different data and timeframes")
    print("   4. Add risk management features")
    print("   5. Optimize parameters for best performance")
    print("\n   Copy this file and make it your own!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
