"""
Broker 适配器基类
定义所有券商接口的统一抽象
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum


class OrderStatus(Enum):
    PENDING = 'pending'
    SUBMITTED = 'submitted'
    PARTIAL_FILLED = 'partial_filled'
    FILLED = 'filled'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'


class OrderType(Enum):
    MARKET = 'market'
    LIMIT = 'limit'
    STOP = 'stop'
    STOP_LIMIT = 'stop_limit'


class Side(Enum):
    BUY = 'buy'
    SELL = 'sell'


class AccountInfo:
    """账户信息"""

    def __init__(self, cash: float, market_value: float,
                 total_value: float, available_cash: float,
                 frozen_cash: float = 0):
        self.cash = cash
        self.market_value = market_value
        self.total_value = total_value
        self.available_cash = available_cash
        self.frozen_cash = frozen_cash

    def to_dict(self) -> dict:
        return {
            'cash': self.cash,
            'market_value': self.market_value,
            'total_value': self.total_value,
            'available_cash': self.available_cash,
            'frozen_cash': self.frozen_cash
        }


class PositionInfo:
    """持仓信息"""

    def __init__(self, symbol: str, quantity: int,
                 avg_cost: float, current_price: float,
                 market_value: float, unrealized_pnl: float,
                 unrealized_pnl_pct: float):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_cost = avg_cost
        self.current_price = current_price
        self.market_value = market_value
        self.unrealized_pnl = unrealized_pnl
        self.unrealized_pnl_pct = unrealized_pnl_pct

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_cost': self.avg_cost,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct
        }


class Order:
    """订单对象"""

    def __init__(self, order_id: str, symbol: str, side: Side,
                 order_type: OrderType, quantity: int,
                 price: Optional[float] = None,
                 stop_price: Optional[float] = None):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.avg_fill_price = 0
        self.submitted_at = None
        self.filled_at = None
        self.error_message = None

    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'avg_fill_price': self.avg_fill_price,
            'submitted_at': self.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if self.submitted_at else None,
            'filled_at': self.filled_at.strftime('%Y-%m-%d %H:%M:%S') if self.filled_at else None,
            'error_message': self.error_message
        }


class BrokerAdapter(ABC):
    """
    券商适配器抽象基类
    所有实盘/模拟券商需实现此接口
    """

    def __init__(self, account_id: str, api_key: Optional[str] = None,
                 api_secret: Optional[str] = None, test_mode: bool = True):
        self.account_id = account_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_mode = test_mode
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """连接券商账户"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        pass

    @abstractmethod
    def get_positions(self) -> List[PositionInfo]:
        """获取所有持仓"""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """获取指定标的持仓"""
        pass

    @abstractmethod
    def place_order(self, order: Order) -> Tuple[bool, str]:
        """
        下单
        Returns: (success, order_id or error_message)
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """查询订单状态"""
        pass

    @abstractmethod
    def get_today_trades(self) -> List[dict]:
        """获取今日成交"""
        pass

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected

    def get_account_id(self) -> str:
        """获取账户ID"""
        return self.account_id

    def is_test_mode(self) -> bool:
        """是否测试模式"""
        return self.test_mode