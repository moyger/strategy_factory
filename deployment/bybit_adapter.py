"""
Bybit Adapter - Bybit cryptocurrency exchange implementation using CCXT

Supports spot and perpetual futures trading
"""

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("⚠️  ccxt not installed. Run: pip install ccxt")

from broker_interface import *
import pandas as pd


class BybitAdapter(BaseBroker):
    """Bybit adapter using CCXT"""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Bybit adapter

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet (default: False)
        """
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt not installed")

        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.exchange = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Bybit"""
        try:
            self.exchange = ccxt.bybit({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'linear',  # USDT perpetuals
                }
            })

            if self.testnet:
                self.exchange.set_sandbox_mode(True)

            # Test connection
            balance = self.exchange.fetch_balance()
            self.connected = True
            print(f"✅ Connected to Bybit {'(Testnet)' if self.testnet else '(Live)'}")
            return True

        except Exception as e:
            print(f"❌ Bybit connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from Bybit"""
        self.exchange = None
        self.connected = False
        print("🔌 Disconnected from Bybit")

    def get_balance(self) -> float:
        """Get account balance"""
        if not self.connected:
            return 0.0

        try:
            balance = self.exchange.fetch_balance()
            return balance['USDT']['free'] if 'USDT' in balance else 0.0
        except Exception as e:
            print(f"❌ Error fetching balance: {e}")
            return 0.0

    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        if not self.connected:
            return {}

        try:
            positions = {}
            raw_positions = self.exchange.fetch_positions()

            for pos in raw_positions:
                if pos['contracts'] > 0:  # Only open positions
                    symbol = pos['symbol']
                    positions[symbol] = Position(
                        symbol=symbol,
                        quantity=pos['contracts'],
                        avg_price=pos['entryPrice'],
                        unrealized_pnl=pos['unrealizedPnl'],
                        realized_pnl=pos.get('realizedPnl', 0.0)
                    )

            return positions
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return {}

    def place_order(self, order: Order) -> str:
        """Place order"""
        if not self.connected:
            print("❌ Not connected to Bybit")
            return ""

        try:
            params = {}

            # Create order
            ccxt_order = self.exchange.create_order(
                symbol=order.symbol,
                type=order.order_type.value.lower(),
                side=order.side.value.lower(),
                amount=order.quantity,
                price=order.limit_price if order.order_type == OrderType.LIMIT else None,
                params=params
            )

            print(f"📤 Bybit order placed: {order}")
            return ccxt_order['id']

        except Exception as e:
            print(f"❌ Order failed: {e}")
            return ""

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if not self.connected:
            return False

        try:
            self.exchange.cancel_order(order_id)
            print(f"❌ Order {order_id} cancelled")
            return True
        except Exception as e:
            print(f"❌ Cancel failed: {e}")
            return False

    def get_historical_data(self, symbol: str, timeframe: str,
                           bars: int = 500) -> pd.DataFrame:
        """Get historical data"""
        if not self.connected:
            return pd.DataFrame()

        try:
            # Fetch OHLCV
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=bars
            )

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            return df

        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """Get current price"""
        if not self.connected:
            return 0.0

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"❌ Error fetching price: {e}")
            return 0.0
