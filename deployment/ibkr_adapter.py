"""
IBKR Adapter - Interactive Brokers implementation using ib_async

Requires TWS or IB Gateway running on localhost:7496
"""

try:
    from ib_async import IB, Stock, MarketOrder, LimitOrder, StopOrder
    from ib_async import util
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    print("⚠️  ib_async not installed. Run: pip install ib_async")

from broker_interface import *
import pandas as pd


class IBKRAdapter(BaseBroker):
    """Interactive Brokers adapter using ib_async"""

    def __init__(self, host='127.0.0.1', port=7496, client_id=1):
        """
        Initialize IBKR adapter

        Args:
            host: TWS/Gateway host
            port: TWS/Gateway port (7496 for TWS live, 7497 for TWS paper)
            client_id: Unique client ID
        """
        if not IB_AVAILABLE:
            raise ImportError("ib_async not installed")

        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False

    def connect(self) -> bool:
        """Connect to TWS/IB Gateway"""
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.connected = True
            print(f"✅ Connected to IBKR @ {self.host}:{self.port} (clientId={self.client_id})")
            return True
        except Exception as e:
            print(f"❌ IBKR connection failed: {e}")
            print(f"   Make sure TWS or IB Gateway is running on port {self.port}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            print("🔌 Disconnected from IBKR")

    def get_balance(self) -> float:
        """Get account balance"""
        if not self.connected:
            return 0.0

        summary = self.ib.accountSummary()
        for item in summary:
            if item.tag == 'NetLiquidation':
                return float(item.value)
        return 0.0

    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        if not self.connected:
            return {}

        positions = {}
        for pos in self.ib.positions():
            symbol = pos.contract.symbol
            positions[symbol] = Position(
                symbol=symbol,
                quantity=pos.position,
                avg_price=pos.avgCost / abs(pos.position) if pos.position != 0 else 0,
                unrealized_pnl=pos.unrealizedPNL,
                realized_pnl=0.0  # Not directly available
            )
        return positions

    def place_order(self, order: Order) -> str:
        """Place order"""
        if not self.connected:
            print("❌ Not connected to IBKR")
            return ""

        # Create contract
        contract = Stock(order.symbol, 'SMART', 'USD')

        # Create order based on type
        if order.order_type == OrderType.MARKET:
            ib_order = MarketOrder(
                order.side.value,
                order.quantity
            )
        elif order.order_type == OrderType.LIMIT:
            ib_order = LimitOrder(
                order.side.value,
                order.quantity,
                order.limit_price
            )
        elif order.order_type == OrderType.STOP:
            ib_order = StopOrder(
                order.side.value,
                order.quantity,
                order.stop_price
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        # Place order
        trade = self.ib.placeOrder(contract, ib_order)
        print(f"📤 IBKR order placed: {order}")

        return str(trade.order.orderId)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        if not self.connected:
            return False

        for trade in self.ib.openTrades():
            if str(trade.order.orderId) == order_id:
                self.ib.cancelOrder(trade.order)
                print(f"❌ Order {order_id} cancelled")
                return True
        return False

    def get_historical_data(self, symbol: str, timeframe: str,
                           bars: int = 500) -> pd.DataFrame:
        """Get historical data"""
        if not self.connected:
            return pd.DataFrame()

        contract = Stock(symbol, 'SMART', 'USD')

        # Map timeframe (e.g., '5m' -> '5 mins')
        bar_size = self._map_timeframe(timeframe)
        duration = f"{bars * self._timeframe_to_seconds(timeframe)} S"

        # Request data
        bars_data = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=False
        )

        if not bars_data:
            return pd.DataFrame()

        # Convert to DataFrame
        df = util.df(bars_data)
        df = df.rename(columns={
            'date': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })

        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    def get_current_price(self, symbol: str) -> float:
        """Get current price"""
        if not self.connected:
            return 0.0

        contract = Stock(symbol, 'SMART', 'USD')
        ticker = self.ib.reqMktData(contract)
        self.ib.sleep(1)  # Wait for data

        if ticker.last:
            return ticker.last
        elif ticker.close:
            return ticker.close
        else:
            return 0.0

    def _map_timeframe(self, tf: str) -> str:
        """Map timeframe to IBKR format"""
        mapping = {
            '1m': '1 min',
            '5m': '5 mins',
            '15m': '15 mins',
            '30m': '30 mins',
            '1h': '1 hour',
            '4h': '4 hours',
            '1d': '1 day'
        }
        return mapping.get(tf, '5 mins')

    def _timeframe_to_seconds(self, tf: str) -> int:
        """Convert timeframe to seconds"""
        mapping = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400
        }
        return mapping.get(tf, 300)
