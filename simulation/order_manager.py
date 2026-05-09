"""
订单管理器
管理模拟盘的订单执行
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from enum import Enum
from typing import List, Optional, Callable


class OrderType(Enum):
    """订单类型"""
    MARKET = 'market'      # 市价单
    LIMIT = 'limit'        # 限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(Enum):
    """订单状态"""
    PENDING = 'pending'       # 待成交
    FILLED = 'filled'        # 已成交
    CANCELLED = 'cancelled'   # 已取消
    REJECTED = 'rejected'    # 已拒绝


class Order:
    """订单类"""
    
    def __init__(self, order_id: str, symbol: str, side: OrderSide, 
                 order_type: OrderType, size: int, price: Optional[float] = None):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.size = size
        self.price = price
        self.filled_price = None
        self.status = OrderStatus.PENDING
        self.create_time = datetime.now()
        self.fill_time = None
        self.reason = None
        
    @property
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY
        
    @property
    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL
        
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
        
    @property
    def is_pending(self) -> bool:
        return self.status == OrderStatus.PENDING
        
    def fill(self, price: float, time: datetime):
        """成交"""
        self.filled_price = price
        self.status = OrderStatus.FILLED
        self.fill_time = time
        
    def cancel(self, reason: str = ''):
        """取消"""
        self.status = OrderStatus.CANCELLED
        self.reason = reason
        
    def reject(self, reason: str = ''):
        """拒绝"""
        self.status = OrderStatus.REJECTED
        self.reason = reason
        
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'size': self.size,
            'price': self.price,
            'filled_price': self.filled_price,
            'status': self.status.value,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'fill_time': self.fill_time.strftime('%Y-%m-%d %H:%M:%S') if self.fill_time else None,
            'reason': self.reason
        }


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders: List[Order] = []
        self.order_counter = 0
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.cancelled_orders: List[Order] = []
        self.rejected_orders: List[Order] = []
        
    def create_order_id(self) -> str:
        """生成订单ID"""
        self.order_counter += 1
        return f"ORDER_{self.order_counter:06d}"
        
    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                     size: int, price: Optional[float] = None) -> Order:
        """创建订单"""
        order_id = self.create_order_id()
        order = Order(order_id, symbol, side, order_type, size, price)
        self.orders.append(order)
        self.pending_orders.append(order)
        return order
        
    def buy_market(self, symbol: str, size: int) -> Order:
        """市价买入"""
        return self.create_order(symbol, OrderSide.BUY, OrderType.MARKET, size)
        
    def sell_market(self, symbol: str, size: int) -> Order:
        """市价卖出"""
        return self.create_order(symbol, OrderSide.SELL, OrderType.MARKET, size)
        
    def buy_limit(self, symbol: str, size: int, price: float) -> Order:
        """限价买入"""
        return self.create_order(symbol, OrderSide.BUY, OrderType.LIMIT, size, price)
        
    def sell_limit(self, symbol: str, size: int, price: float) -> Order:
        """限价卖出"""
        return self.create_order(symbol, OrderSide.SELL, OrderType.LIMIT, size, price)
        
    def fill_order(self, order: Order, price: float, time: datetime) -> bool:
        """成交订单"""
        if order not in self.pending_orders:
            return False
            
        order.fill(price, time)
        self.pending_orders.remove(order)
        self.filled_orders.append(order)
        return True
        
    def cancel_order(self, order: Order, reason: str = '') -> bool:
        """取消订单"""
        if order not in self.pending_orders:
            return False
            
        order.cancel(reason)
        self.pending_orders.remove(order)
        self.cancelled_orders.append(order)
        return True
        
    def reject_order(self, order: Order, reason: str = '') -> bool:
        """拒绝订单"""
        if order not in self.pending_orders:
            return False
            
        order.reject(reason)
        self.pending_orders.remove(order)
        self.rejected_orders.append(order)
        return True
        
    def get_pending_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """获取待成交订单"""
        if symbol:
            return [o for o in self.pending_orders if o.symbol == symbol]
        return self.pending_orders.copy()
        
    def get_filled_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """获取已成交订单"""
        if symbol:
            return [o for o in self.filled_orders if o.symbol == symbol]
        return self.filled_orders.copy()
        
    def get_all_orders(self) -> List[Order]:
        """获取所有订单"""
        return self.orders.copy()
        
    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """根据ID获取订单"""
        for order in self.orders:
            if order.order_id == order_id:
                return order
        return None
        
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'total_orders': len(self.orders),
            'pending_orders': len(self.pending_orders),
            'filled_orders': len(self.filled_orders),
            'cancelled_orders': len(self.cancelled_orders),
            'rejected_orders': len(self.rejected_orders)
        }
