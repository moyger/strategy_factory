"""
Bybit Adapter - Official Bybit SDK (pybit)

Uses Bybit's official Python SDK for most reliable and up-to-date API access.

Installation:
    pip install pybit

Documentation:
    https://bybit-exchange.github.io/docs/v5/intro
"""

import sys
from pathlib import Path

try:
    from pybit.unified_trading import HTTP
    PYBIT_AVAILABLE = True
except ImportError:
    PYBIT_AVAILABLE = False
    print("⚠️  pybit not installed. Run: pip install pybit")

from broker_interface import *
import pandas as pd
from typing import Dict, List, Optional
import time


class BybitAdapterOfficial(BaseBroker):
    """
    Bybit adapter using official pybit SDK

    Supports:
    - Spot trading (recommended for this strategy)
    - Unified Trading Account (UTA)
    - V5 API (latest)
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Bybit adapter with official SDK

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet (default: False)
        """
        if not PYBIT_AVAILABLE:
            raise ImportError("pybit not installed. Run: pip install pybit")

        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.session = None
        self.connected = False

    def connect(self) -> bool:
        """Connect to Bybit using official SDK"""
        try:
            # Initialize HTTP session
            self.session = HTTP(
                testnet=self.testnet,
                api_key=self.api_key,
                api_secret=self.api_secret
            )

            # Test connection by fetching wallet balance
            response = self.session.get_wallet_balance(accountType="UNIFIED")

            if response['retCode'] == 0:
                self.connected = True
                env = "Testnet" if self.testnet else "Live"
                print(f"✅ Connected to Bybit ({env}) using official pybit SDK")
                return True
            else:
                print(f"❌ Connection failed: {response['retMsg']}")
                return False

        except Exception as e:
            print(f"❌ Bybit connection error: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from Bybit"""
        self.session = None
        self.connected = False
        print("🔌 Disconnected from Bybit")

    def get_balance(self) -> float:
        """
        Get USDT balance in Unified Trading Account

        Returns:
            Available USDT balance
        """
        if not self.connected:
            return 0.0

        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")

            if response['retCode'] == 0:
                # Parse balance from response
                coins = response['result']['list'][0]['coin']

                # Find USDT balance
                for coin in coins:
                    if coin['coin'] == 'USDT':
                        available = float(coin['availableToWithdraw'])
                        return available

                return 0.0
            else:
                print(f"❌ Error fetching balance: {response['retMsg']}")
                return 0.0

        except Exception as e:
            print(f"❌ Balance fetch error: {e}")
            return 0.0

    def get_positions(self) -> Dict[str, Position]:
        """
        Get all open spot positions

        Note: Spot trading doesn't have "positions" like derivatives.
        This returns current holdings as positions.

        Returns:
            Dict of symbol -> Position
        """
        if not self.connected:
            return {}

        try:
            # Get wallet balance to see holdings
            response = self.session.get_wallet_balance(accountType="UNIFIED")

            if response['retCode'] != 0:
                print(f"❌ Error fetching positions: {response['retMsg']}")
                return {}

            positions = {}
            coins = response['result']['list'][0]['coin']

            # Get current prices for value calculation
            for coin_info in coins:
                coin = coin_info['coin']
                qty = float(coin_info['walletBalance'])

                if qty > 0 and coin != 'USDT':
                    # Get current price
                    symbol = f"{coin}USDT"
                    try:
                        ticker = self.session.get_tickers(
                            category="spot",
                            symbol=symbol
                        )

                        if ticker['retCode'] == 0:
                            current_price = float(ticker['result']['list'][0]['lastPrice'])

                            positions[symbol] = Position(
                                symbol=symbol,
                                quantity=qty,
                                avg_price=current_price,  # Spot doesn't track entry
                                unrealized_pnl=0.0,  # Not tracked in spot
                                realized_pnl=0.0
                            )
                    except:
                        pass  # Skip if can't get price

            return positions

        except Exception as e:
            print(f"❌ Position fetch error: {e}")
            return {}

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")

        Returns:
            Current price or None
        """
        if not self.connected:
            return None

        try:
            # Convert format: "BTC/USDT" -> "BTCUSDT"
            symbol_clean = symbol.replace('/', '').replace('-', '')

            response = self.session.get_tickers(
                category="spot",
                symbol=symbol_clean
            )

            if response['retCode'] == 0:
                price = float(response['result']['list'][0]['lastPrice'])
                return price
            else:
                return None

        except Exception as e:
            print(f"❌ Price fetch error for {symbol}: {e}")
            return None

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = 'market',
        price: Optional[float] = None
    ) -> Order:
        """
        Place an order on Bybit Spot

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "buy" or "sell"
            quantity: Order quantity
            order_type: "market" or "limit"
            price: Limit price (required for limit orders)

        Returns:
            Order object with fill details
        """
        if not self.connected:
            raise Exception("Not connected to Bybit")

        try:
            # Convert format
            symbol_clean = symbol.replace('/', '').replace('-', '')

            # Map order type
            order_type_map = {
                'market': 'Market',
                'limit': 'Limit'
            }

            # Place order
            params = {
                'category': 'spot',
                'symbol': symbol_clean,
                'side': 'Buy' if side.lower() == 'buy' else 'Sell',
                'orderType': order_type_map.get(order_type, 'Market'),
                'qty': str(quantity)
            }

            if order_type == 'limit' and price:
                params['price'] = str(price)

            response = self.session.place_order(**params)

            if response['retCode'] == 0:
                order_id = response['result']['orderId']

                # Wait a moment and get order details
                time.sleep(0.5)
                order_info = self.session.get_order_history(
                    category='spot',
                    orderId=order_id
                )

                if order_info['retCode'] == 0:
                    order_data = order_info['result']['list'][0]

                    return Order(
                        order_id=order_id,
                        symbol=symbol,
                        side=side,
                        quantity=float(order_data['qty']),
                        fill_price=float(order_data['avgPrice']) if order_data['avgPrice'] else None,
                        status='filled' if order_data['orderStatus'] == 'Filled' else 'pending',
                        timestamp=pd.Timestamp.now()
                    )
                else:
                    # Return basic order info
                    return Order(
                        order_id=order_id,
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        fill_price=None,
                        status='pending',
                        timestamp=pd.Timestamp.now()
                    )
            else:
                raise Exception(f"Order failed: {response['retMsg']}")

        except Exception as e:
            print(f"❌ Order placement error: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an open order

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair

        Returns:
            True if cancelled successfully
        """
        if not self.connected:
            return False

        try:
            symbol_clean = symbol.replace('/', '').replace('-', '')

            response = self.session.cancel_order(
                category='spot',
                symbol=symbol_clean,
                orderId=order_id
            )

            return response['retCode'] == 0

        except Exception as e:
            print(f"❌ Order cancellation error: {e}")
            return False

    def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[Order]:
        """
        Get order history

        Args:
            symbol: Filter by symbol (optional)
            limit: Number of orders to return

        Returns:
            List of Order objects
        """
        if not self.connected:
            return []

        try:
            params = {
                'category': 'spot',
                'limit': limit
            }

            if symbol:
                params['symbol'] = symbol.replace('/', '').replace('-', '')

            response = self.session.get_order_history(**params)

            if response['retCode'] != 0:
                return []

            orders = []
            for order_data in response['result']['list']:
                orders.append(Order(
                    order_id=order_data['orderId'],
                    symbol=order_data['symbol'],
                    side='buy' if order_data['side'] == 'Buy' else 'sell',
                    quantity=float(order_data['qty']),
                    fill_price=float(order_data['avgPrice']) if order_data['avgPrice'] else None,
                    status='filled' if order_data['orderStatus'] == 'Filled' else order_data['orderStatus'].lower(),
                    timestamp=pd.Timestamp(int(order_data['createdTime']), unit='ms')
                ))

            return orders

        except Exception as e:
            print(f"❌ Order history error: {e}")
            return []

    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1d',
        bars: int = 500
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1d', '1h', '5m')
            bars: Number of bars to fetch

        Returns:
            DataFrame with OHLCV data
        """
        if not self.connected:
            return pd.DataFrame()

        try:
            # Convert symbol format
            symbol_clean = symbol.replace('/', '').replace('-', '')

            # Map timeframe to Bybit interval
            interval_map = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
                '1d': 'D', '1w': 'W', '1M': 'M'
            }

            interval = interval_map.get(timeframe, 'D')

            # Fetch kline data
            response = self.session.get_kline(
                category='spot',
                symbol=symbol_clean,
                interval=interval,
                limit=bars
            )

            if response['retCode'] != 0:
                print(f"❌ Historical data error: {response['retMsg']}")
                return pd.DataFrame()

            # Parse data
            klines = response['result']['list']

            if not klines:
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # Sort by timestamp (ascending)
            df = df.sort_values('timestamp').reset_index(drop=True)

            # Set timestamp as index
            df.set_index('timestamp', inplace=True)

            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"❌ Historical data fetch error: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Current price as float
        """
        if not self.connected:
            return 0.0

        try:
            symbol_clean = symbol.replace('/', '').replace('-', '')

            response = self.session.get_tickers(
                category='spot',
                symbol=symbol_clean
            )

            if response['retCode'] == 0 and response['result']['list']:
                ticker = response['result']['list'][0]
                return float(ticker['lastPrice'])
            else:
                return 0.0

        except Exception as e:
            print(f"❌ Price fetch error for {symbol}: {e}")
            return 0.0

    def get_account_info(self) -> Dict:
        """
        Get account information

        Returns:
            Dict with account details
        """
        if not self.connected:
            return {}

        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")

            if response['retCode'] == 0:
                account = response['result']['list'][0]

                return {
                    'account_type': account['accountType'],
                    'total_equity': float(account['totalEquity']),
                    'available_balance': float(account['totalAvailableBalance']),
                    'used_margin': float(account.get('totalMarginBalance', 0)),
                    'unrealized_pnl': float(account.get('totalPerpUPL', 0))
                }
            else:
                return {}

        except Exception as e:
            print(f"❌ Account info error: {e}")
            return {}


def compare_adapters():
    """
    Helper function to show differences between CCXT and pybit adapters
    """
    print("="*80)
    print("BYBIT ADAPTER COMPARISON")
    print("="*80)

    print("\n1. CCXT Adapter (bybit_adapter.py)")
    print("   Pros:")
    print("   ✅ Works with 100+ exchanges")
    print("   ✅ Easy to switch brokers")
    print("   ✅ Unified API")
    print("   ✅ Large community")
    print("\n   Cons:")
    print("   ❌ May lag behind exchange updates")
    print("   ❌ Heavier library")
    print("\n   Installation: pip install ccxt")

    print("\n2. Official Bybit SDK (bybit_adapter_official.py) ⭐ RECOMMENDED")
    print("   Pros:")
    print("   ✅ Official from Bybit")
    print("   ✅ Always up-to-date")
    print("   ✅ Best documentation")
    print("   ✅ Optimized for Bybit")
    print("   ✅ Lighter weight")
    print("\n   Cons:")
    print("   ❌ Only works with Bybit")
    print("\n   Installation: pip install pybit")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    print("\nFor dedicated Bybit deployment: Use bybit_adapter_official.py")
    print("For multi-exchange flexibility: Use bybit_adapter.py (CCXT)")
    print("\nBoth adapters implement the same interface, so switching is easy!")


if __name__ == '__main__':
    compare_adapters()
