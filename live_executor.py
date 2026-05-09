"""
实盘执行器
整合券商、风控、日志的完整执行链路
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
import threading
import time

from broker import BrokerAdapter, SimBrokerAdapter, Order, OrderType, Side
from modules.risk_manager import RiskManager
from modules.logger import Logger
from automation.kill_switch import KillSwitch, KillSwitchReason
from automation.anomaly_detector import AnomalyDetector
from automation.alerter import Alerter


class ExecutionResult:
    """执行结果"""

    def __init__(self, success: bool, order_id: Optional[str] = None,
                 message: str = '', pnl: float = 0,
                 fill_price: float = 0, fill_time: Optional[datetime] = None):
        self.success = success
        self.order_id = order_id
        self.message = message
        self.pnl = pnl
        self.fill_price = fill_price
        self.fill_time = fill_time

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'order_id': self.order_id,
            'message': self.message,
            'pnl': self.pnl,
            'fill_price': self.fill_price,
            'fill_time': self.fill_time.strftime('%Y-%m-%d %H:%M:%S') if self.fill_time else None
        }


class LiveExecutor:
    """
    实盘执行器

    负责：
    1. 接收策略信号
    2. 风控检查
    3. 订单执行
    4. 持仓同步
    5. 事件回调
    """

    def __init__(self, broker: BrokerAdapter,
                 risk_manager: Optional[RiskManager] = None,
                 kill_switch: Optional[KillSwitch] = None,
                 alerter: Optional[Alerter] = None,
                 logger: Optional[Logger] = None):
        self.broker = broker
        self.risk_manager = risk_manager or RiskManager()
        self.kill_switch = kill_switch or KillSwitch(logger)
        self.alerter = alerter or Alerter(logger)
        self.logger = logger or Logger()

        self.order_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        self.position_callbacks: List[Callable] = []

        self.order_count = 0
        self.is_running = False
        self.sync_thread = None

        self.logger.log_system({'event': 'LiveExecutor初始化', 'broker': broker.account_id})

    def start(self):
        """启动执行器"""
        if not self.broker.connect():
            self.logger.log_error({'event': '券商连接失败', 'account': self.broker.account_id})
            return False

        self.is_running = True
        self.kill_switch.register_trading_system(self)
        self.logger.log_system({'event': 'LiveExecutor启动', 'account': self.broker.account_id})
        return True

    def stop(self):
        """停止执行器"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)

        self.broker.disconnect()
        self.logger.log_system({'event': 'LiveExecutor停止'})

    def pause(self):
        """暂停交易"""
        self.is_running = False
        self.logger.log_system({'event': '交易已暂停'})

    def resume(self):
        """恢复交易"""
        self.is_running = True
        self.logger.log_system({'event': '交易已恢复'})

    def _build_risk_context(self, symbol: str, side: Side) -> dict:
        """构建风控上下文"""
        account = self.broker.get_account()
        position = self.broker.get_position(symbol)

        position_value = position.market_value if position else 0

        return {
            'portfolio_value': account.total_value,
            'position_value': position_value,
            'symbol': symbol,
            'side': side.value,
            'signal_reason': f'策略信号_{datetime.now().strftime("%H:%M:%S")}'
        }

    def buy_market(self, symbol: str, quantity: int) -> ExecutionResult:
        """市价买入"""
        return self._execute_order(symbol, Side.BUY, OrderType.MARKET, quantity)

    def sell_market(self, symbol: str, quantity: int) -> ExecutionResult:
        """市价卖出"""
        return self._execute_order(symbol, Side.SELL, OrderType.MARKET, quantity)

    def buy_limit(self, symbol: str, quantity: int, price: float) -> ExecutionResult:
        """限价买入"""
        return self._execute_order(symbol, Side.BUY, OrderType.LIMIT, quantity, price)

    def sell_limit(self, symbol: str, quantity: int, price: float) -> ExecutionResult:
        """限价卖出"""
        return self._execute_order(symbol, Side.SELL, OrderType.LIMIT, quantity, price)

    def _execute_order(self, symbol: str, side: Side,
                      order_type: OrderType, quantity: int,
                      price: Optional[float] = None) -> ExecutionResult:
        """执行订单核心逻辑"""

        if not self.is_running:
            return ExecutionResult(False, message='执行器已暂停')

        if self.kill_switch.is_activated:
            return ExecutionResult(False, message='Kill Switch已激活')

        block, reason = self._check_anomaly_block(symbol)
        if block:
            self.logger.log_risk({'event': '异常阻断交易', 'symbol': symbol, 'reason': reason})
            self.alerter.send_risk_alert('交易阻断', reason, {'symbol': symbol, 'reason': reason})
            return ExecutionResult(False, message=f'异常阻断: {reason}')

        risk_context = self._build_risk_context(symbol, side)
        passed, rejections = self.risk_manager.check_order(risk_context)

        if not passed:
            reason_str = '; '.join(rejections)
            self.logger.log_risk({'event': '风控拒绝', 'symbol': symbol, 'reason': reason_str})
            self.alerter.send_risk_alert('风控拒绝', reason_str, {'symbol': symbol})
            return ExecutionResult(False, message=f'风控拒绝: {reason_str}')

        order = Order(
            order_id='',
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price
        )

        success, result = self.broker.place_order(order)

        if success:
            self.order_count += 1
            self.logger.log_trade({
                'event': '订单提交',
                'order_id': result,
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity,
                'price': price,
                'type': order_type.value
            })
            self.alerter.send_trade_alert(symbol, side.value.upper(), price or 0, quantity)
            self._notify_order_callbacks(result, True, '')
        else:
            self.logger.log_error({'event': '订单失败', 'symbol': symbol, 'reason': result})
            self._notify_order_callbacks(None, False, result)

        return ExecutionResult(
            success=success,
            order_id=result if success else None,
            message=result if not success else '订单提交成功'
        )

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        result = self.broker.cancel_order(order_id)
        if result:
            self.logger.log_trade({'event': '撤单成功', 'order_id': order_id})
        return result

    def _check_anomaly_block(self, symbol: str) -> Tuple[bool, str]:
        """检查异常阻断"""
        detector = AnomalyDetector()

        price = self.broker.current_prices.get(symbol)
        if price is None:
            return False, ''

        current_prices = self.broker.current_prices
        for sym, p in current_prices.items():
            detector.update_data(sym, p, 1000000)

        block, reason = detector.should_block_trading()
        return block, reason

    def get_account_summary(self) -> dict:
        """获取账户摘要"""
        account = self.broker.get_account()
        positions = self.broker.get_positions()

        return {
            'account_id': self.broker.account_id,
            'cash': account.cash,
            'market_value': account.market_value,
            'total_value': account.total_value,
            'positions': [p.to_dict() for p in positions],
            'positions_count': len(positions),
            'orders_today': self.order_count,
            'kill_switch_active': self.kill_switch.is_active(),
            'is_running': self.is_running
        }

    def register_order_callback(self, callback: Callable):
        """注册订单回调"""
        self.order_callbacks.append(callback)

    def register_trade_callback(self, callback: Callable):
        """注册成交回调"""
        self.trade_callbacks.append(callback)

    def register_position_callback(self, callback: Callable):
        """注册持仓变更回调"""
        self.position_callbacks.append(callback)

    def _notify_order_callbacks(self, order_id: Optional[str], success: bool, error: str):
        """通知订单回调"""
        for cb in self.order_callbacks:
            try:
                cb(order_id, success, error)
            except Exception as e:
                self.logger.log_error({'event': '订单回调异常', 'error': str(e)})

    def _notify_trade_callbacks(self, trade: dict):
        """通知成交回调"""
        for cb in self.trade_callbacks:
            try:
                cb(trade)
            except Exception as e:
                self.logger.log_error({'event': '成交回调异常', 'error': str(e)})

    def _notify_position_callbacks(self, positions: List[dict]):
        """通知持仓变更回调"""
        for cb in self.position_callbacks:
            try:
                cb(positions)
            except Exception as e:
                self.logger.log_error({'event': '持仓回调异常', 'error': str(e)})

    def trigger_emergency_stop(self, reason: str):
        """触发紧急停止"""
        self.pause()
        self.kill_switch.trigger_manual(f'紧急停止: {reason}')
        self.alerter.send_critical_alert('紧急停止触发', reason)
        self.logger.log_system({'event': '紧急停止', 'reason': reason})

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False