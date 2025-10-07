"""
MT5 Adapter - MetaTrader 5 implementation (Windows only)

Requires MetaTrader 5 terminal installed and running
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️  MetaTrader5 not installed. Run: pip install MetaTrader5")
    print("   Note: MT5 Python API only works on Windows")

from broker_interface import *
import pandas as pd


class MT5Adapter(BaseBroker):
    """MetaTrader 5 adapter (Windows only)"""

    def __init__(self, login: int, password: str, server: str):
        """
        Initialize MT5 adapter

        Args:
            login: MT5 account login
            password: MT5 account password
            server: MT5 server name
        """
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 not installed or not on Windows")

        self.login = login
        self.password = password
        self.server = server
        self.connected = False

    def connect(self) -> bool:
        """Connect to MT5"""
        if not mt5.initialize():
            print(f"❌ MT5 initialize() failed: {mt5.last_error()}")
            return False

        # Login
        authorized = mt5.login(self.login, password=self.password, server=self.server)

        if not authorized:
            print(f"❌ MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            self.connected = False
            return False

        self.connected = True
        print(f"✅ Connected to MT5 (Account: {self.login} @ {self.server})")
        return True

    def disconnect(self) -> None:
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("🔌 Disconnected from MT5")

    def get_balance(self) -> float:
        """Get account balance"""
        if not self.connected:
            return 0.0

        account_info = mt5.account_info()
        return account_info.balance if account_info else 0.0

    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        if not self.connected:
            return {}

        positions = {}
        raw_positions = mt5.positions_get()

        if raw_positions:
            for pos in raw_positions:
                symbol = pos.symbol
                positions[symbol] = Position(
                    symbol=symbol,
                    quantity=pos.volume,
                    avg_price=pos.price_open,
                    unrealized_pnl=pos.profit,
                    realized_pnl=0.0  # Not directly available
                )

        return positions

    def place_order(self, order: Order) -> str:
        """Place order"""
        if not self.connected:
            print("❌ Not connected to MT5")
            return ""

        # Get symbol info
        symbol_info = mt5.symbol_info(order.symbol)
        if symbol_info is None:
            print(f"❌ {order.symbol} not found")
            return ""

        # Prepare order
        point = symbol_info.point
        tick = mt5.symbol_info_tick(order.symbol)
        if not tick:
            print(f"❌ Failed to get tick data for {order.symbol}")
            return ""

        price = tick.ask if order.side == OrderSide.BUY else tick.bid

        # Map order type
        if order.order_type == OrderType.MARKET:
            order_type = mt5.ORDER_TYPE_BUY if order.side == OrderSide.BUY else mt5.ORDER_TYPE_SELL
        elif order.order_type == OrderType.LIMIT:
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if order.side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_LIMIT
            price = order.limit_price
        elif order.order_type == OrderType.STOP:
            order_type = mt5.ORDER_TYPE_BUY_STOP if order.side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_STOP
            price = order.stop_price
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        # Create request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": order.quantity,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Strategy Factory",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ MT5 order failed: {result.comment}")
            return ""

        print(f"📤 MT5 order placed: {order}")
        return str(result.order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if not self.connected:
            return False

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(order_id)
        }
        result = mt5.order_send(request)
        success = result.retcode == mt5.TRADE_RETCODE_DONE

        if success:
            print(f"❌ Order {order_id} cancelled")

        return success

    def get_historical_data(self, symbol: str, timeframe: str,
                           bars: int = 500) -> pd.DataFrame:
        """Get historical data"""
        if not self.connected:
            return pd.DataFrame()

        # Map timeframe
        tf_map = {
            '1m': mt5.TIMEFRAME_M1,
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '30m': mt5.TIMEFRAME_M30,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
            '1d': mt5.TIMEFRAME_D1
        }
        mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M5)

        # Fetch data
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)

        if rates is None:
            print(f"❌ Failed to get data for {symbol}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df = df.rename(columns={'tick_volume': 'volume'})

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    def get_current_price(self, symbol: str) -> float:
        """Get current price"""
        if not self.connected:
            return 0.0

        tick = mt5.symbol_info_tick(symbol)
        return tick.ask if tick else 0.0
