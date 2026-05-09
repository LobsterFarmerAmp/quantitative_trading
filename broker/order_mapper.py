"""
订单映射器
将系统内部订单格式转换为券商API格式
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from typing import Dict, Optional
from broker.base_broker import Order, OrderType, Side


class OrderMapper:
    """
    订单格式映射器
    将项目内部的 Order 转换为券商API需要的格式
    """

    BROKER_ORDER_TYPE_MAP = {
        OrderType.MARKET: '0',
        OrderType.LIMIT: '2',
        OrderType.STOP: '5',
        OrderType.STOP_LIMIT: '6'
    }

    BROKER_SIDE_MAP = {
        Side.BUY: 'buy',
        Side.SELL: 'sell'
    }

    def __init__(self, broker_type: str = 'sim'):
        self.broker_type = broker_type

    def to_broker_order(self, order: Order) -> dict:
        """
        将内部 Order 转换为券商API格式
        """
        if self.broker_type == 'sim':
            return self._to_sim_order(order)
        elif self.broker_type == 'xtquant':
            return self._to_xtquant_order(order)
        elif self.broker_type == 'rqalpha':
            return self._to_rqalpha_order(order)
        else:
            return self._to_sim_order(order)

    def _to_sim_order(self, order: Order) -> dict:
        """SimBroker 格式"""
        return {
            'symbol': order.symbol,
            'side': self.BROKER_SIDE_MAP.get(order.side, 'buy'),
            'order_type': order.order_type.value,
            'quantity': order.quantity,
            'price': order.price,
            'stop_price': order.stop_price
        }

    def _to_xtquant_order(self, order: Order) -> dict:
        """迅投 QMT 格式"""
        return {
            'stock_code': order.symbol.split('.')[0],
            'trade_side': 'self.BUY' if order.side == Side.BUY else 'self.SELL',
            'price_type': self.BROKER_ORDER_TYPE_MAP.get(order.order_type, '0'),
            'price': order.price or 0,
            'qty': order.quantity
        }

    def _to_rqalpha_order(self, order: Order) -> dict:
        """米筐 RQAlpha 格式"""
        return {
            'order_book_id': order.symbol,
            'side': 'BUY' if order.side == Side.BUY else 'SELL',
            'order_type': self.BROKER_ORDER_TYPE_MAP.get(order.order_type, '0'),
            'price': order.price or 0,
            'quantity': order.quantity
        }

    def from_broker_response(self, response: dict) -> Optional[str]:
        """
        从券商响应中提取订单ID
        """
        if self.broker_type == 'sim':
            return response.get('order_id')
        elif self.broker_type == 'xtquant':
            return response.get('m_strOrderId')
        elif self.broker_type == 'rqalpha':
            return str(response.get('order_id', ''))
        else:
            return response.get('order_id')

    def parse_order_status(self, status_code: str) -> str:
        """
        解析券商返回的订单状态码
        """
        status_map = {
            '0': 'pending',
            '1': 'submitted',
            '2': 'partial_filled',
            '3': 'filled',
            '4': 'cancelled',
            '5': 'rejected'
        }
        return status_map.get(str(status_code), 'pending')