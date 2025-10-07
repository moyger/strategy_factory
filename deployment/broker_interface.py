"""
Broker Interface - Abstract base class for unified broker API

Defines common interface for all brokers (IBKR, Bybit, MT5)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
import pandas as pd


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class Order:
    """Unified order structure"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    def __str__(self):
        return f"{self.side.value} {self.quantity} {self.symbol} @ {self.order_type.value}"


@dataclass
class Position:
    """Unified position structure"""
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float
    realized_pnl: float

    def __str__(self):
        return f"{self.symbol}: {self.quantity} @ ${self.avg_price:.2f} (P&L: ${self.unrealized_pnl:.2f})"


@dataclass
class BarData:
    """Unified OHLCV bar"""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


class BaseBroker(ABC):
    """Abstract base class for all broker adapters"""

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to broker

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from broker"""
        pass

    @abstractmethod
    def get_balance(self) -> float:
        """
        Get account balance

        Returns:
            Account balance in base currency
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        """
        Get all open positions

        Returns:
            Dictionary of {symbol: Position}
        """
        pass

    @abstractmethod
    def place_order(self, order: Order) -> str:
        """
        Place order

        Args:
            order: Order object

        Returns:
            Order ID
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str,
                           bars: int = 500) -> pd.DataFrame:
        """
        Get historical OHLCV data

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            bars: Number of bars to fetch

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """
        Get current market price

        Args:
            symbol: Trading symbol

        Returns:
            Current price
        """
        pass

    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information (optional, can be overridden)

        Returns:
            Dictionary with account details
        """
        return {
            'balance': self.get_balance(),
            'positions': self.get_positions()
        }
