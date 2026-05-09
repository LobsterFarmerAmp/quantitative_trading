"""
Broker 适配器模块
提供统一的券商接口，支持多种券商
"""

from broker.base_broker import (
    BrokerAdapter,
    AccountInfo,
    PositionInfo,
    Order,
    OrderStatus,
    OrderType,
    Side
)

from broker.sim_broker import SimBrokerAdapter
from broker.order_mapper import OrderMapper
from broker.http_broker import HttpBrokerAdapter, WebSocketBrokerAdapter
from broker.config_manager import ConfigManager, BrokerConfig
from broker.quote_service import QuoteService, MarketCalendar
from broker.vnpy_adapter import VnpyBrokerAdapter, VnpyCTPAdapter

__all__ = [
    'BrokerAdapter',
    'AccountInfo',
    'PositionInfo',
    'Order',
    'OrderStatus',
    'OrderType',
    'Side',
    'SimBrokerAdapter',
    'HttpBrokerAdapter',
    'WebSocketBrokerAdapter',
    'VnpyBrokerAdapter',
    'VnpyCTPAdapter',
    'OrderMapper',
    'ConfigManager',
    'BrokerConfig',
    'QuoteService',
    'MarketCalendar'
]