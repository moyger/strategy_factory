"""
Live Trading System - London Breakout v4.1 (Enhanced UI)
FTMO-Compliant with Better Terminal Display

IMPROVEMENTS:
- Clear status dashboard in terminal
- Color-coded messages
- Progress indicators
- Real-time statistics
- Better error handling
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta, timezone
import time as time_module
import json
import logging
from typing import Optional, Dict, Tuple
import os

from strategies.strategy_breakout_v4_1_optimized import LondonBreakoutV41Optimized
from strategies.pattern_detector import PatternDetector
from live.config_live import *

# ANSI Color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text, color=Colors.CYAN):
    """Print formatted header"""
    print(f"\n{color}{'='*80}{Colors.ENDC}")
    print(f"{color}{text.center(80)}{Colors.ENDC}")
    print(f"{color}{'='*80}{Colors.ENDC}\n")

def print_status(label, value, status='info'):
    """Print status line with color coding"""
    colors = {
        'good': Colors.GREEN,
        'warning': Colors.YELLOW,
        'error': Colors.RED,
        'info': Colors.CYAN
    }
    color = colors.get(status, Colors.CYAN)
    print(f"  {label:.<40} {color}{value}{Colors.ENDC}")

def print_box(title, lines, color=Colors.BLUE):
    """Print a box with information"""
    width = 78
    print(f"\n{color}┌{'─' * width}┐{Colors.ENDC}")
    print(f"{color}│{Colors.BOLD} {title.center(width-2)} {Colors.ENDC}{color}│{Colors.ENDC}")
    print(f"{color}├{'─' * width}┤{Colors.ENDC}")
    for line in lines:
        print(f"{color}│{Colors.ENDC} {line.ljust(width-2)} {color}│{Colors.ENDC}")
    print(f"{color}└{'─' * width}┘{Colors.ENDC}\n")

# Import existing FTMOSafetyManager from original file
from live.live_trader import FTMOSafetyManager

class LiveTraderEnhanced:
    """Enhanced live trading system with better UI"""

    def __init__(self, config_dict):
        self.config = config_dict
        self.logger = self._setup_logging()

        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'total_checks': 0,
            'signals_detected': 0,
            'trades_opened': 0,
            'trades_closed': 0,
            'total_pnl': 0,
            'last_update': None
        }

        # Initialize MT5
        if not mt5.initialize():
            self.logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            raise Exception("Failed to initialize MT5")

        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            raise Exception("Failed to get account info")

        self.account_balance = account_info.balance
        self.account_equity = account_info.equity
        self.account_number = account_info.login

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

    def _setup_logging(self):
        """Setup logging system"""
        logger = logging.getLogger('LiveTrader')
        logger.setLevel(getattr(logging, self.config['LOG_LEVEL']))

        # File handler only (terminal has custom display)
        if self.config['LOG_TO_FILE']:
            Path(self.config['LOG_FILE_PATH']).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.config['LOG_FILE_PATH'])
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)

        return logger

    def display_startup_screen(self):
        """Display startup information"""
        clear_screen()

        print_header("LONDON BREAKOUT v4.1 - LIVE TRADING SYSTEM", Colors.BOLD + Colors.CYAN)

        # Account Information
        account_info = [
            f"Account Number: {self.account_number}",
            f"Balance: ${self.account_balance:,.2f}",
            f"Equity: ${self.account_equity:,.2f}",
            f"Mode: {'PAPER TRADING' if self.config['PAPER_TRADE_MODE'] else '🔴 LIVE TRADING'}",
        ]
        print_box("ACCOUNT INFORMATION", account_info, Colors.GREEN)

        # Strategy Settings
        strategy_info = [
            f"Risk Per Trade: {self.config['RISK_PER_TRADE']}%",
            f"Asia Breakout: {'✅ Enabled' if self.config['STRATEGY_PARAMS']['enable_asia_breakout'] else '❌ Disabled'}",
            f"Triangle Patterns: {'✅ Enabled' if self.config['STRATEGY_PARAMS']['enable_triangle_breakout'] else '❌ Disabled'}",
            f"Trading Hours: {self.config['LONDON_SESSION_START']}:00 - {self.config['LONDON_SESSION_END']}:00 GMT",
        ]
        print_box("STRATEGY SETTINGS", strategy_info, Colors.BLUE)

        # Safety Limits
        safety_info = [
            f"FTMO Max Loss: -{self.config['FTMO_MAX_TOTAL_LOSS_PCT']}%  →  Safety Stop: -{self.config['SAFETY_STOP_AT_DD_PCT']}%",
            f"FTMO Daily Loss: -{self.config['FTMO_MAX_DAILY_LOSS_PCT']}%  →  Safety Stop: -{self.config['SAFETY_STOP_AT_DAILY_LOSS_PCT']}%",
            f"Max Consecutive Losses: {self.config['MAX_CONSECUTIVE_LOSSES']}",
            f"Max Daily Trades: {self.config['MAX_DAILY_TRADES']}",
        ]
        print_box("SAFETY LIMITS (FTMO COMPLIANT)", safety_info, Colors.YELLOW)

        print(f"\n{Colors.GREEN}✅ System initialized successfully!{Colors.ENDC}")
        print(f"{Colors.CYAN}Press Ctrl+C to stop{Colors.ENDC}\n")

        time_module.sleep(3)

    def display_status_dashboard(self):
        """Display real-time status dashboard"""
        clear_screen()

        # Header
        current_time = datetime.now()
        uptime = current_time - self.stats['start_time']

        print_header(f"LIVE TRADING STATUS - {current_time.strftime('%Y-%m-%d %H:%M:%S GMT')}", Colors.BOLD + Colors.CYAN)

        # Get current account info
        account_info = mt5.account_info()
        if account_info:
            current_equity = account_info.equity
            current_balance = account_info.balance
        else:
            current_equity = self.account_equity
            current_balance = self.account_balance

        # Update safety manager
        safety_status = self.safety_manager.update_balance(current_equity)

        # Account Status
        pnl = current_equity - self.account_balance
        pnl_pct = (pnl / self.account_balance) * 100

        pnl_color = 'good' if pnl >= 0 else 'error'
        trading_status = 'good' if safety_status['trading_enabled'] else 'error'

        print(f"\n{Colors.BOLD}ACCOUNT STATUS{Colors.ENDC}")
        print_status("Balance", f"${current_balance:,.2f}", 'info')
        print_status("Equity", f"${current_equity:,.2f}", 'info')
        print_status("P&L", f"${pnl:,.2f} ({pnl_pct:+.2f}%)", pnl_color)
        print_status("Peak Balance", f"${safety_status['peak_balance']:,.2f}", 'info')

        # Drawdown Status
        dd_status = 'good' if abs(safety_status['total_dd_pct']) < 5 else 'warning' if abs(safety_status['total_dd_pct']) < 8 else 'error'
        daily_status = 'good' if abs(safety_status['daily_loss_pct']) < 2 else 'warning' if abs(safety_status['daily_loss_pct']) < 4 else 'error'

        print(f"\n{Colors.BOLD}RISK METRICS{Colors.ENDC}")
        print_status("Max Drawdown", f"{safety_status['total_dd_pct']:.2f}% (limit: -10%)", dd_status)
        print_status("Daily Loss", f"{safety_status['daily_loss_pct']:.2f}% (limit: -5%)", daily_status)
        print_status("Trading Status", "✅ ENABLED" if safety_status['trading_enabled'] else "🔴 DISABLED", trading_status)

        # Trading Status
        safety = self.safety_manager.get_status()

        print(f"\n{Colors.BOLD}TRADING ACTIVITY{Colors.ENDC}")
        print_status("Consecutive Losses", f"{safety['consecutive_losses']}/{self.config['MAX_CONSECUTIVE_LOSSES']}",
                    'error' if safety['consecutive_losses'] >= 3 else 'warning' if safety['consecutive_losses'] >= 2 else 'good')
        print_status("Daily Trades", f"{safety['daily_trades']}/{self.config['MAX_DAILY_TRADES']}", 'info')
        print_status("Trades Today", f"{self.stats['trades_opened']} opened, {self.stats['trades_closed']} closed", 'info')

        # Current Position
        print(f"\n{Colors.BOLD}CURRENT POSITION{Colors.ENDC}")
        if self.current_position:
            print_status("Status", "🟢 IN POSITION", 'warning')
            print_status("Type", self.current_position.get('type', 'N/A').upper(), 'info')
            print_status("Entry Price", f"${self.current_position.get('entry_price', 0):.5f}", 'info')
        else:
            print_status("Status", "⚪ NO POSITION", 'good')

        # Trading Time Status
        is_trading_time = self.is_trading_time()
        now = datetime.now(timezone.utc)

        print(f"\n{Colors.BOLD}MARKET HOURS{Colors.ENDC}")
        print_status("Current Time (GMT)", now.strftime('%H:%M:%S'), 'info')
        print_status("Trading Hours", f"{self.config['LONDON_SESSION_START']}:00 - {self.config['LONDON_SESSION_END']}:00 GMT", 'info')
        print_status("Market Status", "🟢 OPEN (Trading)" if is_trading_time else "🔴 CLOSED (Monitoring)",
                    'good' if is_trading_time else 'warning')

        # Statistics
        print(f"\n{Colors.BOLD}SESSION STATISTICS{Colors.ENDC}")
        print_status("Uptime", f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m", 'info')
        print_status("Total Checks", f"{self.stats['total_checks']}", 'info')
        print_status("Signals Detected", f"{self.stats['signals_detected']}", 'info')
        print_status("Last Update", self.stats['last_update'].strftime('%H:%M:%S') if self.stats['last_update'] else 'Never', 'info')

        # Footer
        print(f"\n{Colors.CYAN}{'─' * 80}{Colors.ENDC}")
        print(f"{Colors.YELLOW}⚡ Monitoring... {Colors.ENDC}Press Ctrl+C to stop")
        print(f"{Colors.CYAN}{'─' * 80}{Colors.ENDC}\n")

    def is_trading_time(self) -> bool:
        """Check if current time is within trading hours"""
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        current_weekday = now.weekday()

        # Check if today is a trading day
        if current_weekday not in self.config['TRADING_DAYS']:
            return False

        # Check if within trading hours (London session)
        if not (self.config['LONDON_SESSION_START'] <= current_hour < self.config['LONDON_SESSION_END']):
            return False

        return True

    def run(self):
        """Main trading loop with enhanced display"""
        self.running = True

        # Show startup screen
        self.display_startup_screen()

        last_dashboard_update = datetime.now()
        dashboard_refresh_seconds = 10  # Refresh every 10 seconds

        try:
            while self.running:
                # Update dashboard periodically
                if (datetime.now() - last_dashboard_update).seconds >= dashboard_refresh_seconds:
                    self.display_status_dashboard()
                    last_dashboard_update = datetime.now()
                    self.stats['last_update'] = datetime.now()

                # Check connection
                if not mt5.terminal_info():
                    self.logger.error("MT5 terminal not connected!")
                    time_module.sleep(60)
                    continue

                # Update account balance
                account_info = mt5.account_info()
                if account_info:
                    current_equity = account_info.equity
                    self.safety_manager.update_balance(current_equity)

                # Check if trading is allowed
                can_trade, reason = self.safety_manager.can_trade()

                if not can_trade:
                    self.logger.warning(f"Trading disabled: {reason}")
                    time_module.sleep(60)
                    continue

                # Check trading hours
                if not self.is_trading_time():
                    time_module.sleep(60)
                    continue

                # Increment check counter
                self.stats['total_checks'] += 1

                # Check for entry signals (TODO: Implement)
                # if self.current_position is None:
                #     self._check_entry_signals()

                # Check for exit signals (TODO: Implement)
                # elif self.current_position is not None:
                #     self._check_exit_signals()

                # Sleep before next iteration
                time_module.sleep(10)  # Check every 10 seconds for responsive UI

        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Shutting down gracefully...{Colors.ENDC}\n")
        except Exception as e:
            self.logger.exception(f"Error in main loop: {e}")
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.ENDC}\n")
        finally:
            self.stop()

    def stop(self):
        """Stop the trading system"""
        print(f"\n{Colors.CYAN}Stopping trader...{Colors.ENDC}")
        self.running = False
        mt5.shutdown()
        print(f"{Colors.GREEN}✅ Trader stopped successfully{Colors.ENDC}\n")


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
    print("Validating configuration...")
    if not validate_config():
        print("\n❌ Configuration validation failed. Please fix errors before running.")
        return

    # Create and run trader
    trader = LiveTraderEnhanced(config_dict)

    try:
        trader.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        trader.stop()


if __name__ == '__main__':
    main()
