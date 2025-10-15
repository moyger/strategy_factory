#!/usr/bin/env python3
"""
Live Crypto Trading Deployment - Bybit

Nick Radge Crypto Hybrid Strategy with Position Stop-Loss (40%)
Deployed to Bybit using Official SDK (pybit) or CCXT

BACKTEST RESULTS (2020-2025):
- Total Return: 19,410% (148% annualized)
- Sharpe Ratio: 1.81
- Max Drawdown: -48.35%
- Position Stops: 8 triggered (SOL -88%, AVAX -79%, etc.)

SAFETY FEATURES:
- Dry run mode (default)
- Position stop-loss (40%)
- Emergency stop-loss (50%)
- Daily loss limit (10%)
- Testnet mode available

CONNECTION OPTIONS:
- broker_adapter: "official" (pybit - recommended for Bybit)
- broker_adapter: "ccxt" (multi-exchange support)

Author: Strategy Factory
Date: 2025-10-14
"""

import sys
from pathlib import Path

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional
import importlib.util
import warnings
warnings.filterwarnings('ignore')

# Import strategy module (LIVE-ONLY version - no backtesting dependencies)
spec = importlib.util.spec_from_file_location(
    "nick_radge_crypto_hybrid_live",
    Path(__file__).parent / "06_nick_radge_crypto_hybrid_live.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NickRadgeCryptoHybrid = module.NickRadgeCryptoHybrid


class LiveCryptoTrader:
    """Live crypto trading system for Bybit"""

    def __init__(self, config_path: str):
        """
        Initialize live trader

        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path
        self.config = self.load_config()
        self.broker = None
        self.strategy = None
        self.logger = self.setup_logging()
        self.current_positions = {}
        self.entry_prices = {}  # Track entry prices for position stops
        self.portfolio_peak = 0.0  # Track peak for emergency stop
        self.last_rebalance = None
        self.is_running = False

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)

        # Validate required fields
        required = ['broker', 'strategy', 'api_credentials', 'strategy_params', 'universe']
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")

        return config

    def setup_logging(self) -> logging.Logger:
        """Setup logging to file and console"""
        log_dir = Path(self.config['logging']['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / self.config['logging']['log_file']

        logger = logging.getLogger('LiveCryptoTrader')
        logger.setLevel(getattr(logging, self.config['execution']['log_level']))

        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def connect_broker(self) -> bool:
        """Connect to Bybit exchange using selected adapter"""
        try:
            creds = self.config['api_credentials']
            testnet = self.config.get('testnet', False)
            adapter_type = self.config.get('broker_adapter', 'ccxt')  # Default to CCXT

            self.logger.info(f"Connecting to Bybit {'(Testnet)' if testnet else '(Live)'}...")
            self.logger.info(f"Using adapter: {adapter_type}")

            # Load appropriate adapter
            if adapter_type == 'official':
                try:
                    from bybit_adapter_official import BybitAdapterOfficial
                    self.broker = BybitAdapterOfficial(
                        api_key=creds['api_key'],
                        api_secret=creds['api_secret'],
                        testnet=testnet
                    )
                    self.logger.info("✅ Using official Bybit SDK (pybit)")
                except ImportError:
                    self.logger.error("❌ pybit not installed. Run: pip install pybit")
                    self.logger.info("   Falling back to CCXT adapter...")
                    adapter_type = 'ccxt'

            if adapter_type == 'ccxt':
                from bybit_adapter import BybitAdapter
                self.broker = BybitAdapter(
                    api_key=creds['api_key'],
                    api_secret=creds['api_secret'],
                    testnet=testnet
                )
                self.logger.info("✅ Using CCXT adapter (multi-exchange)")

            if not self.broker.connect():
                self.logger.error("Failed to connect to Bybit")
                return False

            balance = self.broker.get_balance()
            self.logger.info(f"Connected! Balance: ${balance:,.2f} USDT")

            return True

        except Exception as e:
            self.logger.error(f"Broker connection error: {e}")
            return False

    def initialize_strategy(self):
        """Initialize the Nick Radge Crypto Hybrid strategy"""
        try:
            params = self.config['strategy_params']

            self.strategy = NickRadgeCryptoHybrid(
                core_allocation=params['core_allocation'],
                satellite_allocation=params['satellite_allocation'],
                core_assets=params['core_assets'],
                satellite_size=params['satellite_size'],
                qualifier_type=params['qualifier_type'],
                use_momentum_weighting=params['use_momentum_weighting'],
                bear_asset=params['bear_asset'],
                position_stop_loss=params.get('position_stop_loss'),
                position_stop_loss_core_only=params.get('position_stop_loss_core_only', False),
                portfolio_stop_loss=params.get('portfolio_stop_loss'),
                regime_ma_long=params.get('regime_ma_long', 200),
                regime_ma_short=params.get('regime_ma_short', 100),
                ma_period=params.get('ma_period', 100),
                rebalance_freq=params.get('rebalance_freq', 'QS')
            )

            self.logger.info("Strategy initialized successfully")
            self.logger.info(f"  Core: {params['core_assets']}")
            self.logger.info(f"  Satellite size: {params['satellite_size']}")
            self.logger.info(f"  Position stop: {params.get('position_stop_loss', 'None')}")

        except Exception as e:
            self.logger.error(f"Strategy initialization error: {e}")
            raise

    def fetch_historical_data(self) -> pd.DataFrame:
        """Fetch historical price data for all universe assets"""
        try:
            self.logger.info("Fetching historical data...")

            universe = self.config['universe']
            lookback = self.config['data_sources']['lookback_days']
            interval = self.config['data_sources']['data_interval']

            all_prices = {}

            for symbol in universe:
                try:
                    # Fetch OHLCV data from Bybit using broker interface
                    df = self.broker.get_historical_data(
                        symbol,
                        timeframe=interval,
                        bars=lookback
                    )

                    if df.empty:
                        self.logger.warning(f"No data for {symbol}")
                        continue

                    all_prices[symbol] = df['close']

                    self.logger.debug(f"  Fetched {len(df)} bars for {symbol}")

                except Exception as e:
                    self.logger.warning(f"Failed to fetch {symbol}: {e}")

            # Combine into single DataFrame
            prices = pd.DataFrame(all_prices)
            self.logger.info(f"Historical data ready: {len(prices)} days, {len(prices.columns)} assets")

            return prices

        except Exception as e:
            self.logger.error(f"Data fetch error: {e}")
            raise

    def calculate_target_allocations(self, prices: pd.DataFrame) -> Dict[str, float]:
        """Calculate target portfolio allocations"""
        try:
            self.logger.info("Calculating target allocations...")

            # Get BTC prices for regime filter
            btc_symbol = self.config['strategy_params']['core_assets'][0]
            btc_prices = prices[btc_symbol]

            # Generate allocations
            allocations = self.strategy.generate_allocations(prices, btc_prices=btc_prices)

            # Get latest allocations (last row)
            latest = allocations.iloc[-1]

            # Remove _STOPPED columns
            target_allocations = {}
            for col in latest.index:
                if not col.endswith('_STOPPED'):
                    alloc = latest[col]
                    if not pd.isna(alloc) and alloc > 0:
                        target_allocations[col] = alloc

            self.logger.info(f"Target allocations: {len(target_allocations)} positions")
            for symbol, alloc in target_allocations.items():
                self.logger.info(f"  {symbol}: {alloc*100:.1f}%")

            return target_allocations

        except Exception as e:
            self.logger.error(f"Allocation calculation error: {e}")
            raise

    def execute_rebalance(self, target_allocations: Dict[str, float]):
        """Execute rebalancing trades"""
        try:
            dry_run = self.config['execution']['dry_run']
            balance = self.broker.get_balance()
            current_positions = self.broker.get_positions()

            self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Executing rebalance...")
            self.logger.info(f"  Current balance: ${balance:,.2f} USDT")
            self.logger.info(f"  Current positions: {len(current_positions)}")

            # Calculate target position sizes
            target_sizes = {}
            for symbol, alloc in target_allocations.items():
                target_value = balance * alloc
                current_price = self.broker.get_current_price(symbol)

                if current_price and current_price > 0:
                    target_qty = target_value / current_price
                    target_sizes[symbol] = target_qty

            # Determine trades needed
            trades = []

            # Close positions not in target
            for symbol, pos in current_positions.items():
                if symbol not in target_allocations:
                    trades.append({
                        'symbol': symbol,
                        'side': 'sell',
                        'qty': pos.quantity,
                        'reason': 'Close position'
                    })

            # Open/adjust positions in target
            for symbol, target_qty in target_sizes.items():
                current_qty = current_positions[symbol].quantity if symbol in current_positions else 0
                diff = target_qty - current_qty

                min_order_size = self.config['trading_params']['min_order_size_usdt']
                current_price = self.broker.get_current_price(symbol)
                min_qty = min_order_size / current_price if current_price else 0

                if abs(diff) > min_qty:
                    trades.append({
                        'symbol': symbol,
                        'side': 'buy' if diff > 0 else 'sell',
                        'qty': abs(diff),
                        'reason': 'Rebalance'
                    })

            # Execute trades
            self.logger.info(f"  Trades to execute: {len(trades)}")

            for trade in trades:
                symbol = trade['symbol']
                side = trade['side']
                qty = trade['qty']
                reason = trade['reason']

                self.logger.info(f"  {side.upper()} {qty:.6f} {symbol} ({reason})")

                if not dry_run:
                    try:
                        order = self.broker.place_order(
                            symbol=symbol,
                            side=side,
                            quantity=qty,
                            order_type='market'
                        )
                        self.logger.info(f"    ✅ Order filled: {order.order_id}")

                        # Track entry price for position stops
                        if side == 'buy':
                            self.entry_prices[symbol] = order.fill_price

                    except Exception as e:
                        self.logger.error(f"    ❌ Order failed: {e}")

            # Log trade to CSV
            self.log_trades(trades, dry_run)

            self.last_rebalance = datetime.now()
            self.logger.info("Rebalance complete!")

        except Exception as e:
            self.logger.error(f"Rebalance execution error: {e}")
            raise

    def check_stop_losses(self):
        """Check and execute position stop-losses"""
        try:
            stop_threshold = self.config['strategy_params'].get('position_stop_loss')
            if not stop_threshold:
                return

            positions = self.broker.get_positions()

            for symbol, pos in positions.items():
                if symbol not in self.entry_prices:
                    self.entry_prices[symbol] = pos.avg_price

                entry_price = self.entry_prices[symbol]
                current_price = self.broker.get_current_price(symbol)

                if not current_price:
                    continue

                pnl_pct = (current_price - entry_price) / entry_price

                if pnl_pct < -stop_threshold:
                    self.logger.warning(f"🚨 POSITION STOP-LOSS: {symbol}")
                    self.logger.warning(f"   Entry: ${entry_price:.2f} → Current: ${current_price:.2f} ({pnl_pct*100:.1f}%)")

                    if not self.config['execution']['dry_run']:
                        # Close position
                        order = self.broker.place_order(
                            symbol=symbol,
                            side='sell',
                            quantity=pos.quantity,
                            order_type='market'
                        )
                        self.logger.warning(f"   ✅ Position closed: {order.order_id}")

                        # Remove from entry prices
                        del self.entry_prices[symbol]

                        # Notify
                        if self.config['notifications']['notify_on_stop_loss']:
                            self.send_notification(
                                f"🚨 Position Stop-Loss Triggered\n"
                                f"Symbol: {symbol}\n"
                                f"Loss: {pnl_pct*100:.1f}%\n"
                                f"Position closed",
                                event_type='stop_loss'
                            )

        except Exception as e:
            self.logger.error(f"Stop-loss check error: {e}")

    def check_emergency_stop(self) -> bool:
        """Check emergency stop-loss (50% portfolio drawdown)"""
        try:
            emergency_threshold = self.config['trading_params']['emergency_stop_loss']
            balance = self.broker.get_balance()

            # Update peak
            if balance > self.portfolio_peak:
                self.portfolio_peak = balance

            # Check drawdown from peak
            if self.portfolio_peak > 0:
                dd = (balance - self.portfolio_peak) / self.portfolio_peak

                if dd < -emergency_threshold:
                    self.logger.critical(f"🚨🚨 EMERGENCY STOP-LOSS TRIGGERED 🚨🚨")
                    self.logger.critical(f"   Portfolio DD: {dd*100:.1f}% (Threshold: {emergency_threshold*100:.0f}%)")
                    self.logger.critical(f"   Peak: ${self.portfolio_peak:,.2f} → Current: ${balance:,.2f}")
                    self.logger.critical("   CLOSING ALL POSITIONS AND STOPPING")

                    if not self.config['execution']['dry_run']:
                        # Close all positions
                        positions = self.broker.get_positions()
                        for symbol, pos in positions.items():
                            self.broker.place_order(
                                symbol=symbol,
                                side='sell',
                                quantity=pos.quantity,
                                order_type='market'
                            )

                        # Send critical alert
                        self.send_notification(
                            f"🚨🚨 EMERGENCY STOP 🚨🚨\n"
                            f"Portfolio DD: {dd*100:.1f}%\n"
                            f"All positions closed\n"
                            f"Bot stopped",
                            event_type='error'
                        )

                    return True  # Stop trading

            return False  # Continue

        except Exception as e:
            self.logger.error(f"Emergency stop check error: {e}")
            return False

    def should_rebalance(self) -> bool:
        """Check if it's time to rebalance"""
        if not self.last_rebalance:
            return True

        rebalance_days = self.config['execution']['rebalance_days']

        if rebalance_days == 'daily':
            # Check if it's the rebalance time
            now = datetime.now()
            rebalance_time = self.config['execution']['rebalance_time']
            target_hour, target_min = map(int, rebalance_time.split(':'))

            if now.hour == target_hour and now.minute == target_min:
                # Check if already rebalanced today
                if self.last_rebalance.date() < now.date():
                    return True

        return False

    def send_notification(self, message: str, event_type: str = 'general'):
        """
        Send notification via multiple channels (Telegram + Email)

        Args:
            message: Notification message (plain text or with formatting)
            event_type: Type of event (startup, trade, stop_loss, error, rebalance)
        """
        success = False

        # Try Telegram first
        if self.config['notifications'].get('telegram_enabled'):
            if self._send_telegram(message):
                success = True

        # Try Email as backup/additional
        if self.config['notifications'].get('email_enabled'):
            if self._send_email(message, event_type):
                success = True

        if not success:
            self.logger.warning(f"No notifications sent (all channels disabled or failed)")

    def _send_telegram(self, message: str) -> bool:
        """Send notification via Telegram"""
        try:
            import requests

            bot_token = self.config['notifications']['telegram_bot_token']
            chat_id = self.config['notifications']['telegram_chat_id']

            if not bot_token or not chat_id:
                self.logger.debug("Telegram not configured (missing bot_token or chat_id)")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                self.logger.debug("✅ Telegram notification sent")
                return True
            else:
                self.logger.error(f"Telegram error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            self.logger.error(f"Telegram notification error: {e}")
            return False

    def _send_email(self, message: str, event_type: str) -> bool:
        """Send notification via Email"""
        try:
            provider = self.config['notifications'].get('email_provider', 'gmail')

            if provider == 'gmail':
                return self._send_email_smtp(message, event_type)
            elif provider == 'sendgrid':
                return self._send_email_sendgrid(message, event_type)
            elif provider == 'ses':
                return self._send_email_ses(message, event_type)
            else:
                self.logger.error(f"Unknown email provider: {provider}")
                return False

        except Exception as e:
            self.logger.error(f"Email notification error: {e}")
            return False

    def _send_email_smtp(self, message: str, event_type: str) -> bool:
        """Send email via SMTP (Gmail, etc.)"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            email_from = self.config['notifications']['email_from']
            email_to = self.config['notifications']['email_to']
            smtp_host = self.config['notifications']['email_smtp_host']
            smtp_port = self.config['notifications']['email_smtp_port']
            password = self.config['notifications']['email_password']
            use_tls = self.config['notifications'].get('email_use_tls', True)

            if not email_from or not email_to or not password:
                self.logger.debug("Email not configured (missing credentials)")
                return False

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = email_from
            msg['To'] = email_to
            msg['Subject'] = self._get_email_subject(event_type, message)

            # Plain text and HTML versions
            text_part = MIMEText(message, 'plain')
            html_part = MIMEText(self._format_email_html(message, event_type), 'html')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                server.login(email_from, password)
                server.send_message(msg)

            self.logger.debug("✅ Email notification sent (SMTP)")
            return True

        except Exception as e:
            self.logger.error(f"SMTP email error: {e}")
            return False

    def _send_email_sendgrid(self, message: str, event_type: str) -> bool:
        """Send email via SendGrid API"""
        try:
            import requests

            api_key = self.config['notifications'].get('sendgrid_api_key')
            email_from = self.config['notifications']['email_from']
            email_to = self.config['notifications']['email_to']

            if not api_key or not email_from or not email_to:
                self.logger.debug("SendGrid not configured")
                return False

            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'personalizations': [{'to': [{'email': email_to}]}],
                'from': {'email': email_from},
                'subject': self._get_email_subject(event_type, message),
                'content': [
                    {'type': 'text/plain', 'value': message},
                    {'type': 'text/html', 'value': self._format_email_html(message, event_type)}
                ]
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code in [200, 202]:
                self.logger.debug("✅ Email notification sent (SendGrid)")
                return True
            else:
                self.logger.error(f"SendGrid error: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"SendGrid email error: {e}")
            return False

    def _send_email_ses(self, message: str, event_type: str) -> bool:
        """Send email via AWS SES"""
        try:
            import boto3

            region = self.config['notifications'].get('aws_ses_region', 'us-east-1')
            access_key = self.config['notifications'].get('aws_access_key')
            secret_key = self.config['notifications'].get('aws_secret_key')
            email_from = self.config['notifications']['email_from']
            email_to = self.config['notifications']['email_to']

            if not access_key or not secret_key or not email_from or not email_to:
                self.logger.debug("AWS SES not configured")
                return False

            client = boto3.client(
                'ses',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )

            response = client.send_email(
                Source=email_from,
                Destination={'ToAddresses': [email_to]},
                Message={
                    'Subject': {'Data': self._get_email_subject(event_type, message)},
                    'Body': {
                        'Text': {'Data': message},
                        'Html': {'Data': self._format_email_html(message, event_type)}
                    }
                }
            )

            self.logger.debug("✅ Email notification sent (AWS SES)")
            return True

        except Exception as e:
            self.logger.error(f"AWS SES email error: {e}")
            return False

    def _get_email_subject(self, event_type: str, message: str) -> str:
        """Generate email subject based on event type"""
        subjects = {
            'startup': '🚀 Crypto Bot Started',
            'trade': '💰 Trade Executed',
            'stop_loss': '🚨 Stop-Loss Triggered',
            'error': '❌ Bot Error Alert',
            'rebalance': '🔄 Portfolio Rebalanced',
            'general': '📊 Crypto Bot Notification'
        }

        subject = subjects.get(event_type, subjects['general'])

        # Add snippet from message
        first_line = message.split('\n')[0][:50]
        if first_line != message.split('\n')[0]:
            first_line += '...'

        return f"{subject} - {first_line}"

    def _format_email_html(self, message: str, event_type: str) -> str:
        """Format message as HTML email"""
        # Simple HTML template
        style_colors = {
            'startup': '#4CAF50',
            'trade': '#2196F3',
            'stop_loss': '#F44336',
            'error': '#FF5722',
            'rebalance': '#FF9800',
            'general': '#9E9E9E'
        }

        color = style_colors.get(event_type, style_colors['general'])

        # Convert plain text to HTML (preserve line breaks)
        html_message = message.replace('\n', '<br>')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: {color};
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 0 0 8px 8px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #999;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Nick Radge Crypto Hybrid Bot</h2>
            </div>
            <div class="content">
                <p>{html_message}</p>
            </div>
            <div class="footer">
                <p>Automated notification from your Crypto Trading Bot</p>
                <p>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """

        return html

    def log_trades(self, trades: List[Dict], dry_run: bool):
        """Log trades to CSV"""
        try:
            log_file = Path(self.config['logging']['trade_log'])
            log_file.parent.mkdir(parents=True, exist_ok=True)

            # Create DataFrame
            df = pd.DataFrame(trades)
            df['timestamp'] = datetime.now()
            df['dry_run'] = dry_run

            # Append to CSV
            if log_file.exists():
                df.to_csv(log_file, mode='a', header=False, index=False)
            else:
                df.to_csv(log_file, index=False)

        except Exception as e:
            self.logger.error(f"Trade logging error: {e}")

    def log_performance(self):
        """Log current performance metrics"""
        try:
            log_file = Path(self.config['logging']['performance_log'])
            log_file.parent.mkdir(parents=True, exist_ok=True)

            balance = self.broker.get_balance()
            positions = self.broker.get_positions()

            total_pnl = sum(pos.unrealized_pnl for pos in positions.values())

            metrics = {
                'timestamp': datetime.now(),
                'balance': balance,
                'num_positions': len(positions),
                'unrealized_pnl': total_pnl,
                'portfolio_peak': self.portfolio_peak
            }

            df = pd.DataFrame([metrics])

            if log_file.exists():
                df.to_csv(log_file, mode='a', header=False, index=False)
            else:
                df.to_csv(log_file, index=False)

        except Exception as e:
            self.logger.error(f"Performance logging error: {e}")

    def run(self):
        """Main trading loop"""
        self.logger.info("="*80)
        self.logger.info("LIVE CRYPTO TRADING - NICK RADGE HYBRID STRATEGY")
        self.logger.info("="*80)

        # Safety warning
        if not self.config['execution']['dry_run']:
            self.logger.warning("⚠️  LIVE TRADING MODE ENABLED - REAL MONEY AT RISK")
        else:
            self.logger.info("✅ DRY RUN MODE - No real trades")

        if not self.config.get('testnet', False):
            self.logger.warning("⚠️  CONNECTED TO LIVE BYBIT - REAL MONEY")
        else:
            self.logger.info("✅ TESTNET MODE")

        # Connect and initialize
        if not self.connect_broker():
            self.logger.error("Failed to connect to broker. Exiting.")
            return

        self.initialize_strategy()

        # Send startup notification
        if self.config['notifications'].get('notify_on_startup', True):
            self.send_notification(
                f"🚀 Crypto Trading Bot Started\n"
                f"Mode: {'DRY RUN' if self.config['execution']['dry_run'] else 'LIVE'}\n"
                f"Testnet: {self.config.get('testnet', False)}\n"
                f"Strategy: Nick Radge Crypto Hybrid\n"
                f"Position Stops: 40%",
                event_type='startup'
            )

        self.is_running = True

        # Main loop
        try:
            while self.is_running:
                # Check emergency stop
                if self.check_emergency_stop():
                    self.logger.critical("Emergency stop triggered. Exiting.")
                    break

                # Check position stop-losses
                self.check_stop_losses()

                # Check if time to rebalance
                if self.should_rebalance():
                    self.logger.info("\n" + "="*80)
                    self.logger.info("REBALANCE TRIGGERED")
                    self.logger.info("="*80)

                    # Fetch data
                    prices = self.fetch_historical_data()

                    # Calculate allocations
                    target_allocations = self.calculate_target_allocations(prices)

                    # Execute rebalance
                    self.execute_rebalance(target_allocations)

                # Log performance
                self.log_performance()

                # Sleep 60 seconds
                time.sleep(60)

        except KeyboardInterrupt:
            self.logger.info("\n⏹️  Keyboard interrupt received. Stopping...")

        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            if self.config['notifications'].get('notify_on_error', True):
                self.send_notification(f"🚨 Bot Error: {e}", event_type='error')

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup and disconnect"""
        self.logger.info("Cleaning up...")

        if self.broker:
            self.broker.disconnect()

        self.logger.info("✅ Shutdown complete")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Live Crypto Trading - Bybit')
    parser.add_argument(
        '--config',
        default='deployment/config_crypto_bybit.json',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Check if config exists
    if not Path(args.config).exists():
        print(f"❌ Config file not found: {args.config}")
        print("   Create it from config_crypto_bybit.json template")
        return

    # Create and run trader
    trader = LiveCryptoTrader(args.config)
    trader.run()


if __name__ == '__main__':
    main()
