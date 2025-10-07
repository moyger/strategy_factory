"""
Strategy Deployer - Deploy strategies to multiple brokers from unified interface

Manages connections to IBKR, Bybit, and MT5 simultaneously
"""

from broker_interface import *
from ibkr_adapter import IBKRAdapter
from bybit_adapter import BybitAdapter
from mt5_adapter import MT5Adapter
from typing import Dict, Any
import json
from pathlib import Path


class StrategyDeployer:
    """
    Deploy strategies to multiple brokers from unified interface

    Example:
        deployer = StrategyDeployer('deployment/config.json')
        deployer.connect_all()
        deployer.deploy_strategy('sma_crossover', 'ibkr', 'AAPL', '5m')
    """

    def __init__(self, config_path: str = 'deployment/config.json'):
        """
        Initialize strategy deployer

        Args:
            config_path: Path to broker configuration file
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.brokers: Dict[str, BaseBroker] = {}

    def _load_config(self, path: str) -> Dict[str, Any]:
        """Load broker configuration"""
        config_file = Path(path)

        if not config_file.exists():
            print(f"⚠️  Config file not found: {path}")
            print(f"   Creating template config...")
            self._create_template_config(path)
            return {}

        with open(path, 'r') as f:
            return json.load(f)

    def _create_template_config(self, path: str) -> None:
        """Create template configuration file"""
        template = {
            "ibkr": {
                "enabled": False,
                "host": "127.0.0.1",
                "port": 7496,
                "client_id": 1
            },
            "bybit": {
                "enabled": False,
                "api_key": "YOUR_BYBIT_API_KEY",
                "api_secret": "YOUR_BYBIT_SECRET",
                "testnet": True
            },
            "mt5": {
                "enabled": False,
                "login": 12345678,
                "password": "YOUR_MT5_PASSWORD",
                "server": "MetaQuotes-Demo"
            }
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(template, f, indent=2)

        print(f"✅ Template config created: {path}")
        print(f"   Please edit the file and set enabled=true for brokers you want to use")

    def connect_all(self) -> None:
        """Connect to all configured brokers"""
        print(f"\n{'='*60}")
        print(f"CONNECTING TO BROKERS")
        print(f"{'='*60}\n")

        # IBKR
        if self.config.get('ibkr', {}).get('enabled', False):
            try:
                ibkr = IBKRAdapter(
                    host=self.config['ibkr']['host'],
                    port=self.config['ibkr']['port'],
                    client_id=self.config['ibkr']['client_id']
                )
                if ibkr.connect():
                    self.brokers['ibkr'] = ibkr
            except Exception as e:
                print(f"❌ IBKR connection error: {e}")

        # Bybit
        if self.config.get('bybit', {}).get('enabled', False):
            try:
                bybit = BybitAdapter(
                    api_key=self.config['bybit']['api_key'],
                    api_secret=self.config['bybit']['api_secret'],
                    testnet=self.config['bybit'].get('testnet', False)
                )
                if bybit.connect():
                    self.brokers['bybit'] = bybit
            except Exception as e:
                print(f"❌ Bybit connection error: {e}")

        # MT5
        if self.config.get('mt5', {}).get('enabled', False):
            try:
                mt5 = MT5Adapter(
                    login=self.config['mt5']['login'],
                    password=self.config['mt5']['password'],
                    server=self.config['mt5']['server']
                )
                if mt5.connect():
                    self.brokers['mt5'] = mt5
            except Exception as e:
                print(f"❌ MT5 connection error: {e}")

        print(f"\n✅ Connected to {len(self.brokers)} broker(s): {', '.join(self.brokers.keys())}")

    def disconnect_all(self) -> None:
        """Disconnect from all brokers"""
        print(f"\n{'='*60}")
        print(f"DISCONNECTING FROM BROKERS")
        print(f"{'='*60}\n")

        for name, broker in self.brokers.items():
            broker.disconnect()

        self.brokers = {}

    def get_all_positions(self) -> Dict[str, Dict[str, Position]]:
        """Get positions from all brokers"""
        all_positions = {}
        for name, broker in self.brokers.items():
            all_positions[name] = broker.get_positions()
        return all_positions

    def get_all_balances(self) -> Dict[str, float]:
        """Get balances from all brokers"""
        balances = {}
        for name, broker in self.brokers.items():
            balances[name] = broker.get_balance()
        return balances

    def print_account_summary(self) -> None:
        """Print account summary for all brokers"""
        print(f"\n{'='*60}")
        print(f"ACCOUNT SUMMARY")
        print(f"{'='*60}\n")

        # Balances
        balances = self.get_all_balances()
        print("💰 Account Balances:")
        for broker, balance in balances.items():
            print(f"  {broker:.<20} ${balance:,.2f}")

        # Positions
        positions = self.get_all_positions()
        print("\n📊 Open Positions:")
        for broker, pos_dict in positions.items():
            print(f"\n{broker}:")
            if len(pos_dict) == 0:
                print("  No open positions")
            else:
                for symbol, pos in pos_dict.items():
                    print(f"  {pos}")

        # Total
        total_balance = sum(balances.values())
        print(f"\n{'='*60}")
        print(f"Total Balance: ${total_balance:,.2f}")
        print(f"{'='*60}\n")

    def place_order_on_broker(self, broker_name: str, order: Order) -> str:
        """
        Place order on specific broker

        Args:
            broker_name: Broker name ('ibkr', 'bybit', 'mt5')
            order: Order object

        Returns:
            Order ID
        """
        if broker_name not in self.brokers:
            print(f"❌ Broker '{broker_name}' not connected")
            return ""

        broker = self.brokers[broker_name]
        return broker.place_order(order)

    def close_all_positions(self, broker_name: str) -> None:
        """
        Close all positions on specific broker

        Args:
            broker_name: Broker name
        """
        if broker_name not in self.brokers:
            print(f"❌ Broker '{broker_name}' not connected")
            return

        broker = self.brokers[broker_name]
        positions = broker.get_positions()

        print(f"\n🔄 Closing {len(positions)} position(s) on {broker_name}...")

        for symbol, pos in positions.items():
            # Close by placing opposite order
            close_side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY

            close_order = Order(
                symbol=symbol,
                side=close_side,
                quantity=abs(pos.quantity),
                order_type=OrderType.MARKET
            )

            order_id = broker.place_order(close_order)
            print(f"  Closed {symbol}: Order ID {order_id}")

        print(f"✅ All positions closed on {broker_name}")

    def get_broker(self, broker_name: str) -> Optional[BaseBroker]:
        """
        Get broker instance

        Args:
            broker_name: Broker name

        Returns:
            Broker instance or None
        """
        return self.brokers.get(broker_name)

    def is_connected(self, broker_name: str) -> bool:
        """
        Check if broker is connected

        Args:
            broker_name: Broker name

        Returns:
            True if connected, False otherwise
        """
        return broker_name in self.brokers
