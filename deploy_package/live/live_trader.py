"""
Live Trading System - London Breakout v4.1
FTMO-Compliant with Safety Checks

SAFETY FEATURES:
- FTMO max loss protection (-10%)
- FTMO daily loss protection (-5%)
- Consecutive loss limit
- Daily trade limit
- Emergency stop mechanisms
- Real-time monitoring
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import time as time_module
import json
import logging
from typing import Optional, Dict, Tuple

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from live.config_live import *

# ==============================================================================
# FTMO SAFETY MANAGER
# ==============================================================================

class FTMOSafetyManager:
    """Enforces FTMO rules and safety limits"""

    def __init__(self, initial_balance: float, config):
        self.initial_balance = initial_balance
        self.config = config
        self.peak_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.today = datetime.now().date()

        # Track violations
        self.max_dd_violated = False
        self.daily_loss_violated = False
        self.consecutive_losses = 0
        self.daily_trades = 0

        # State
        self.trading_enabled = True
        self.stop_reason = None

        self.logger = logging.getLogger('FTMOSafety')

    def update_balance(self, current_balance: float, is_new_day: bool = False):
        """Update balance and check limits"""

        # Reset daily counters on new day
        if is_new_day or datetime.now().date() != self.today:
            self.today = datetime.now().date()
            self.daily_start_balance = current_balance
            self.daily_trades = 0

            # Resume trading if auto-resume enabled
            if self.config['AUTO_RESUME_NEXT_DAY'] and self.daily_loss_violated:
                self.logger.info("New day - resetting daily loss violation")
                self.daily_loss_violated = False
                self.trading_enabled = True
                self.stop_reason = None

        # Update peak
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance

        # Calculate drawdowns
        total_dd_pct = (current_balance - self.peak_balance) / self.peak_balance * 100
        daily_loss_pct = (current_balance - self.daily_start_balance) / self.daily_start_balance * 100

        # Check FTMO limits
        self._check_ftmo_limits(total_dd_pct, daily_loss_pct)

        # Check safety stops
        self._check_safety_stops(total_dd_pct, daily_loss_pct)

        return {
            'total_dd_pct': total_dd_pct,
            'daily_loss_pct': daily_loss_pct,
            'peak_balance': self.peak_balance,
            'daily_start_balance': self.daily_start_balance,
            'trading_enabled': self.trading_enabled
        }

    def _check_ftmo_limits(self, total_dd_pct: float, daily_loss_pct: float):
        """Check FTMO hard limits"""

        # Max total loss limit
        if abs(total_dd_pct) >= self.config['FTMO_MAX_TOTAL_LOSS_PCT']:
            self.max_dd_violated = True
            self.trading_enabled = False
            self.stop_reason = f"FTMO MAX LOSS LIMIT VIOLATED: {total_dd_pct:.2f}%"
            self.logger.critical(self.stop_reason)
            self._send_critical_alert(self.stop_reason)

        # Max daily loss limit
        if abs(daily_loss_pct) >= self.config['FTMO_MAX_DAILY_LOSS_PCT']:
            self.daily_loss_violated = True
            self.trading_enabled = False
            self.stop_reason = f"FTMO DAILY LOSS LIMIT VIOLATED: {daily_loss_pct:.2f}%"
            self.logger.critical(self.stop_reason)
            self._send_critical_alert(self.stop_reason)

    def _check_safety_stops(self, total_dd_pct: float, daily_loss_pct: float):
        """Check safety margins before hitting FTMO limits"""

        if self.max_dd_violated or self.daily_loss_violated:
            return  # Already stopped

        # Safety stop at drawdown threshold
        if abs(total_dd_pct) >= self.config['SAFETY_STOP_AT_DD_PCT']:
            self.trading_enabled = False
            self.stop_reason = f"SAFETY STOP: Drawdown {total_dd_pct:.2f}% (limit: {self.config['SAFETY_STOP_AT_DD_PCT']}%)"
            self.logger.warning(self.stop_reason)
            self._send_alert(self.stop_reason)

        # Safety stop at daily loss threshold
        if abs(daily_loss_pct) >= self.config['SAFETY_STOP_AT_DAILY_LOSS_PCT']:
            self.trading_enabled = False
            self.stop_reason = f"SAFETY STOP: Daily loss {daily_loss_pct:.2f}% (limit: {self.config['SAFETY_STOP_AT_DAILY_LOSS_PCT']}%)"
            self.logger.warning(self.stop_reason)
            self._send_alert(self.stop_reason)

    def on_trade_closed(self, pnl: float):
        """Track trade results for consecutive loss limit"""

        if pnl < 0:
            self.consecutive_losses += 1

            if self.consecutive_losses >= self.config['MAX_CONSECUTIVE_LOSSES']:
                self.trading_enabled = False
                self.stop_reason = f"MAX CONSECUTIVE LOSSES: {self.consecutive_losses}"
                self.logger.warning(self.stop_reason)
                self._send_alert(self.stop_reason)
        else:
            self.consecutive_losses = 0  # Reset on win

    def on_trade_opened(self):
        """Track daily trade count"""
        self.daily_trades += 1

    def can_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed"""

        if not self.trading_enabled:
            return False, self.stop_reason or "Trading disabled"

        # Check daily trade limit
        if self.daily_trades >= self.config['MAX_DAILY_TRADES']:
            return False, f"Daily trade limit reached ({self.daily_trades}/{self.config['MAX_DAILY_TRADES']})"

        return True, "OK"

    def _send_alert(self, message: str):
        """Send alert (implement Telegram/Email here)"""
        # TODO: Implement Telegram/Email notifications
        self.logger.warning(f"ALERT: {message}")

    def _send_critical_alert(self, message: str):
        """Send critical alert"""
        # TODO: Implement critical notifications
        self.logger.critical(f"CRITICAL: {message}")

    def get_status(self) -> Dict:
        """Get current safety status"""
        return {
            'trading_enabled': self.trading_enabled,
            'stop_reason': self.stop_reason,
            'consecutive_losses': self.consecutive_losses,
            'daily_trades': self.daily_trades,
            'max_dd_violated': self.max_dd_violated,
            'daily_loss_violated': self.daily_loss_violated
        }


# ==============================================================================
# LIVE TRADER
# ==============================================================================

class LiveTrader:
    """Main live trading system"""

    def __init__(self, config_dict):
        self.config = config_dict
        self.logger = self._setup_logging()

        # Initialize MT5
        if not mt5.initialize():
            self.logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            raise Exception("Failed to initialize MT5")

        self.logger.info("MT5 initialized successfully")

        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            raise Exception("Failed to get account info")

        self.account_balance = account_info.balance
        self.account_equity = account_info.equity

        # Initialize safety manager
        self.safety_manager = FTMOSafetyManager(
            initial_balance=self.config['INITIAL_BALANCE'],
            config=self.config
        )

        # Initialize strategy
        self.strategy = LondonBreakoutV41Optimized(
            risk_percent=self.config['RISK_PER_TRADE'],
            initial_capital=self.config['INITIAL_BALANCE'],
            enable_asia_breakout=self.config['STRATEGY_PARAMS']['enable_asia_breakout'],
            enable_triangle_breakout=self.config['STRATEGY_PARAMS']['enable_triangle_breakout']
        )

        # Apply strategy parameters
        for key, value in self.config['STRATEGY_PARAMS'].items():
            if hasattr(self.strategy, key):
                setattr(self.strategy, key, value)

        self.strategy.pattern_detector = PatternDetector(
            lookback=self.config['STRATEGY_PARAMS']['triangle_lookback'],
            r_squared_min=self.config['STRATEGY_PARAMS']['triangle_r2_min'],
            slope_tolerance=self.config['STRATEGY_PARAMS']['triangle_slope_tolerance']
        )

        # State
        self.current_position = None
        self.running = False

        self.logger.info(f"LiveTrader initialized - Account: {account_info.login}, Balance: ${self.account_balance:,.2f}")

    def _setup_logging(self):
        """Setup logging system"""
        logger = logging.getLogger('LiveTrader')
        logger.setLevel(getattr(logging, self.config['LOG_LEVEL']))

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(console)

        # File handler
        if self.config['LOG_TO_FILE']:
            Path(self.config['LOG_FILE_PATH']).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.config['LOG_FILE_PATH'])
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)

        return logger

    def is_trading_time(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now(datetime.UTC)
        current_hour = now.hour
        current_weekday = now.weekday()

        # Check if today is a trading day
        if current_weekday not in self.config['TRADING_DAYS']:
            return False

        # Check if within trading hours (London session)
        if not (self.config['LONDON_SESSION_START'] <= current_hour < self.config['LONDON_SESSION_END']):
            return False

        return True

    def get_market_data(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """Fetch market data from MT5"""

        # Map timeframe string to MT5 constant
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }

        mt5_timeframe = tf_map.get(timeframe)
        if mt5_timeframe is None:
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return None

        # Get bars
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)

        if rates is None or len(rates) == 0:
            self.logger.error(f"Failed to get rates for {symbol} {timeframe}")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)

        return df[['open', 'high', 'low', 'close', 'volume']]

    def run(self):
        """Main trading loop"""
        self.running = True
        self.logger.info("="*80)
        self.logger.info("STARTING LIVE TRADER")
        self.logger.info("="*80)
        self.logger.info(f"Paper Trade Mode: {self.config['PAPER_TRADE_MODE']}")
        self.logger.info(f"Risk Per Trade: {self.config['RISK_PER_TRADE']}%")
        self.logger.info(f"Symbol: {self.config['SYMBOL']}")
        self.logger.info("="*80)

        try:
            while self.running:
                # Check connection
                if not mt5.terminal_info():
                    self.logger.error("MT5 terminal not connected!")
                    time_module.sleep(60)
                    continue

                # Update account balance
                account_info = mt5.account_info()
                if account_info:
                    current_equity = account_info.equity

                    # Update safety manager
                    safety_status = self.safety_manager.update_balance(current_equity)

                    # Log status
                    if safety_status['total_dd_pct'] < -2:  # Only log if significant DD
                        self.logger.info(f"Account Status - Equity: ${current_equity:,.2f}, "
                                       f"DD: {safety_status['total_dd_pct']:.2f}%, "
                                       f"Daily: {safety_status['daily_loss_pct']:.2f}%")

                # Check if trading is allowed
                can_trade, reason = self.safety_manager.can_trade()

                if not can_trade:
                    self.logger.warning(f"Trading disabled: {reason}")
                    time_module.sleep(300)  # Check every 5 minutes
                    continue

                # Check trading hours
                if not self.is_trading_time():
                    time_module.sleep(300)  # Check every 5 minutes
                    continue

                # Check for entry signals
                if self.current_position is None:
                    self._check_entry_signals()

                # Check for exit signals
                elif self.current_position is not None:
                    self._check_exit_signals()

                # Sleep before next iteration
                time_module.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.exception(f"Error in main loop: {e}")
        finally:
            self.stop()

    def _check_entry_signals(self):
        """Check for entry signals"""
        # Get market data
        df_h1 = self.get_market_data(self.config['SYMBOL'], 'H1', bars=200)
        df_h4 = self.get_market_data(self.config['SYMBOL'], 'H4', bars=100)

        if df_h1 is None or df_h4 is None:
            return

        # Run strategy signal detection
        # TODO: Implement signal detection from strategy
        # This requires adapting the backtest code to work in real-time

        self.logger.debug("Checking for entry signals...")

    def _check_exit_signals(self):
        """Check for exit signals"""
        # TODO: Implement exit signal detection
        self.logger.debug("Checking for exit signals...")

    def stop(self):
        """Stop the trading system"""
        self.logger.info("Stopping trader...")
        self.running = False

        # Close any open positions if configured
        # TODO: Implement position closing

        # Shutdown MT5
        mt5.shutdown()
        self.logger.info("Trader stopped successfully")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Main entry point"""

    # Load configuration
    config_dict = {
        'INITIAL_BALANCE': INITIAL_BALANCE,
        'RISK_PER_TRADE': RISK_PER_TRADE,
        'FTMO_MAX_TOTAL_LOSS_PCT': FTMO_MAX_TOTAL_LOSS_PCT,
        'FTMO_MAX_DAILY_LOSS_PCT': FTMO_MAX_DAILY_LOSS_PCT,
        'SAFETY_STOP_AT_DD_PCT': SAFETY_STOP_AT_DD_PCT,
        'SAFETY_STOP_AT_DAILY_LOSS_PCT': SAFETY_STOP_AT_DAILY_LOSS_PCT,
        'MAX_CONSECUTIVE_LOSSES': MAX_CONSECUTIVE_LOSSES,
        'MAX_DAILY_TRADES': MAX_DAILY_TRADES,
        'STRATEGY_PARAMS': STRATEGY_PARAMS,
        'LONDON_SESSION_START': LONDON_SESSION_START,
        'LONDON_SESSION_END': LONDON_SESSION_END,
        'TRADING_DAYS': TRADING_DAYS,
        'SYMBOL': SYMBOL,
        'PAPER_TRADE_MODE': PAPER_TRADE_MODE,
        'LOG_LEVEL': LOG_LEVEL,
        'LOG_TO_FILE': LOG_TO_FILE,
        'LOG_FILE_PATH': LOG_FILE_PATH,
        'AUTO_RESUME_NEXT_DAY': AUTO_RESUME_NEXT_DAY
    }

    # Validate configuration
    if not validate_config():
        print("\n❌ Configuration validation failed. Please fix errors before running.")
        return

    # Create and run trader
    trader = LiveTrader(config_dict)

    try:
        trader.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        trader.stop()


if __name__ == '__main__':
    main()
