"""
模拟券商适配器
用于 Paper Trading 和回测
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from broker.base_broker import (
    BrokerAdapter, AccountInfo, PositionInfo, Order, OrderStatus, OrderType, Side
)
from modules.logger import Logger


class SimBrokerAdapter(BrokerAdapter):
    """
    模拟券商 - 完全在内存中模拟交易
    适用于 Paper Trading 和策略回测
    """

    def __init__(self, account_id: str, initial_cash: float = 100000,
                 commission_rate: float = 0.0003, slippage_rate: float = 0.0005,
                 test_mode: bool = True):
        super().__init__(account_id, test_mode=test_mode)
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        self.positions: Dict[str, dict] = {}
        self.pending_orders: Dict[str, Order] = {}
        self.filled_orders: Dict[str, Order] = {}
        self.cancelled_orders: Dict[str, Order] = {}
        self.today_trades: List[dict] = []

        self.current_prices: Dict[str, float] = {}
        self.logger = Logger()

    def connect(self) -> bool:
        self.connected = True
        self.logger.log_system({
            'event': 'SimBroker连接',
            'account_id': self.account_id,
            'initial_cash': self.initial_cash,
            'mode': '测试' if self.test_mode else '实盘'
        })
        return True

    def disconnect(self):
        self.connected = False
        self.logger.log_system({'event': 'SimBroker断开连接'})

    def update_prices(self, prices: Dict[str, float]):
        """更新当前价格（外部注入）"""
        self.current_prices.update(prices)

    def get_account(self) -> AccountInfo:
        market_value = sum(
            pos['quantity'] * self.current_prices.get(symbol, pos['avg_cost'])
            for symbol, pos in self.positions.items()
        )
        total_value = self.cash + market_value

        return AccountInfo(
            cash=self.cash,
            market_value=market_value,
            total_value=total_value,
            available_cash=self.cash,
            frozen_cash=0
        )

    def get_positions(self) -> List[PositionInfo]:
        result = []
        for symbol, pos in self.positions.items():
            current_price = self.current_prices.get(symbol, pos['avg_cost'])
            market_value = pos['quantity'] * current_price
            cost = pos['quantity'] * pos['avg_cost']
            unrealized_pnl = market_value - cost
            unrealized_pnl_pct = unrealized_pnl / cost if cost > 0 else 0

            result.append(PositionInfo(
                symbol=symbol,
                quantity=pos['quantity'],
                avg_cost=pos['avg_cost'],
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct
            ))
        return result

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        if symbol not in self.positions:
            return None
        pos = self.positions[symbol]
        current_price = self.current_prices.get(symbol, pos['avg_cost'])
        market_value = pos['quantity'] * current_price
        cost = pos['quantity'] * pos['avg_cost']
        unrealized_pnl = market_value - cost
        unrealized_pnl_pct = unrealized_pnl / cost if cost > 0 else 0

        return PositionInfo(
            symbol=symbol,
            quantity=pos['quantity'],
            avg_cost=pos['avg_cost'],
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct
        )

    def place_order(self, order: Order) -> Tuple[bool, str]:
        if not self.connected:
            return False, '未连接券商'

        if order.symbol not in self.current_prices:
            return False, f'无当前价格: {order.symbol}'

        current_price = self.current_prices[order.symbol]

        if order.order_type == OrderType.MARKET:
            if order.side == Side.BUY:
                execution_price = current_price * (1 + self.slippage_rate)
            else:
                execution_price = current_price * (1 - self.slippage_rate)
        else:
            if order.price is None:
                return False, '限价单未指定价格'
            execution_price = order.price

        order_id = f"ORD_{uuid.uuid4().hex[:12].upper()}"
        order.order_id = order_id
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = datetime.now()
        order.avg_fill_price = execution_price
        order.filled_quantity = order.quantity

        commission = execution_price * order.quantity * self.commission_rate

        if order.side == Side.BUY:
            total_cost = execution_price * order.quantity + commission
            if total_cost > self.cash:
                order.status = OrderStatus.REJECTED
                order.error_message = '资金不足'
                return False, '资金不足'

            self.cash -= total_cost

            if order.symbol in self.positions:
                old_pos = self.positions[order.symbol]
                total_qty = old_pos['quantity'] + order.quantity
                total_cost_sum = old_pos['quantity'] * old_pos['avg_cost'] + order.quantity * execution_price
                new_avg_cost = total_cost_sum / total_qty
                self.positions[order.symbol] = {
                    'quantity': total_qty,
                    'avg_cost': new_avg_cost
                }
            else:
                self.positions[order.symbol] = {
                    'quantity': order.quantity,
                    'avg_cost': execution_price
                }
        else:
            if order.symbol not in self.positions:
                order.status = OrderStatus.REJECTED
                order.error_message = '无持仓'
                return False, '无持仓'

            pos = self.positions[order.symbol]
            if order.quantity > pos['quantity']:
                order.status = OrderStatus.REJECTED
                order.error_message = '持仓不足'
                return False, '持仓不足'

            self.cash += execution_price * order.quantity - commission

            cost_basis = pos['avg_cost'] * order.quantity
            sell_proceeds = execution_price * order.quantity - commission
            pnl = sell_proceeds - cost_basis

            pos['quantity'] -= order.quantity
            if pos['quantity'] == 0:
                del self.positions[order.symbol]

        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()

        self.pending_orders[order_id] = order
        self.filled_orders[order_id] = order

        trade_record = {
            'trade_id': f"TRD_{uuid.uuid4().hex[:8].upper()}",
            'order_id': order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'price': execution_price,
            'quantity': order.quantity,
            'commission': commission,
            'pnl': pnl if order.side == Side.SELL else None,
            'filled_at': order.filled_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        self.today_trades.append(trade_record)

        self.logger.log_trade({
            'symbol': order.symbol,
            'action': order.side.value.upper(),
            'price': execution_price,
            'size': order.quantity,
            'commission': commission,
            'order_id': order_id
        })

        return True, order_id

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            order.status = OrderStatus.CANCELLED
            self.cancelled_orders[order_id] = order
            del self.pending_orders[order_id]
            return True
        return False

    def get_order_status(self, order_id: str) -> OrderStatus:
        if order_id in self.pending_orders:
            return self.pending_orders[order_id].status
        if order_id in self.filled_orders:
            return self.filled_orders[order_id].status
        if order_id in self.cancelled_orders:
            return OrderStatus.CANCELLED
        return OrderStatus.REJECTED

    def get_today_trades(self) -> List[dict]:
        return self.today_trades

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions and self.positions[symbol]['quantity'] > 0

    def get_status(self) -> dict:
        account = self.get_account()
        positions = self.get_positions()
        return {
            'account_id': self.account_id,
            'connected': self.connected,
            'test_mode': self.test_mode,
            'cash': account.cash,
            'market_value': account.market_value,
            'total_value': account.total_value,
            'positions_count': len(positions),
            'pending_orders': len(self.pending_orders),
            'today_trades': len(self.today_trades)
        }