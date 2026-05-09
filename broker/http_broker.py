"""
HTTP 券商适配器
通过 HTTP REST API 连接券商柜台
适用于：vn.py网关 / 自定义交易服务 / 券商开放API
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from broker.base_broker import (
    BrokerAdapter, AccountInfo, PositionInfo, Order, OrderStatus, OrderType, Side
)


class HttpBrokerAdapter(BrokerAdapter):
    """
    HTTP券商适配器

    适用场景：
    1. vn.py 的 REST API 网关
    2. 自开发的交易服务
    3. 券商开放的 HTTP 接口（如华泰、东方财富等）
    4. 任何提供 REST API 的交易系统
    """

    def __init__(self, account_id: str,
                 api_url: str,
                 api_key: str = '',
                 api_secret: str = '',
                 timeout: int = 10,
                 retry_times: int = 3,
                 test_mode: bool = True):
        super().__init__(
            account_id=account_id,
            api_key=api_key,
            api_secret=api_secret,
            test_mode=test_mode
        )
        self.api_url = api_url.rstrip('/')
        self.timeout = timeout
        self.retry_times = retry_times
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'

        self._account_cache: Optional[AccountInfo] = None
        self._positions_cache: List[PositionInfo] = []
        self._last_fetch_time: Optional[datetime] = None

    def _request(self, method: str, endpoint: str,
                data: Optional[dict] = None,
                retry: int = None) -> dict:
        """发送HTTP请求，带重试"""
        if retry is None:
            retry = self.retry_times

        url = f'{self.api_url}/{endpoint.lstrip("/")}'
        payload = json.dumps(data) if data else None

        for attempt in range(retry):
            try:
                resp = self.session.request(
                    method=method.upper(),
                    url=url,
                    data=payload,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt < retry - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise ConnectionError(f'HTTP请求失败 ({attempt+1}次): {e}')

        return {}

    def connect(self) -> bool:
        """连接券商API"""
        try:
            result = self._request('GET', '/account/info')
            self.connected = True
            print(f'HTTP券商连接成功: {self.api_url}')
            return True
        except Exception as e:
            self.connected = False
            print(f'HTTP券商连接失败: {e}')
            return False

    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.session.close()
        print('HTTP券商连接已断开')

    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        try:
            result = self._request('GET', '/account')
            return AccountInfo(
                cash=float(result.get('cash', 0)),
                market_value=float(result.get('market_value', 0)),
                total_value=float(result.get('total_value', 0)),
                available_cash=float(result.get('available_cash', 0)),
                frozen_cash=float(result.get('frozen_cash', 0))
            )
        except Exception as e:
            if self._account_cache:
                return self._account_cache
            raise ConnectionError(f'获取账户失败: {e}')

    def get_positions(self) -> List[PositionInfo]:
        """获取所有持仓"""
        try:
            result = self._request('GET', '/positions')
            positions = []
            for item in result.get('positions', []):
                positions.append(PositionInfo(
                    symbol=item['symbol'],
                    quantity=int(item['quantity']),
                    avg_cost=float(item['avg_cost']),
                    current_price=float(item['current_price']),
                    market_value=float(item['market_value']),
                    unrealized_pnl=float(item.get('unrealized_pnl', 0)),
                    unrealized_pnl_pct=float(item.get('unrealized_pnl_pct', 0))
                ))
            self._positions_cache = positions
            self._last_fetch_time = datetime.now()
            return positions
        except Exception as e:
            return self._positions_cache

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """获取指定标的持仓"""
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None

    def place_order(self, order: Order) -> Tuple[bool, str]:
        """下单"""
        try:
            payload = {
                'symbol': order.symbol,
                'side': order.side.value,
                'order_type': order.order_type.value,
                'quantity': order.quantity,
                'price': order.price,
                'stop_price': order.stop_price,
                'client_order_id': str(uuid.uuid4())
            }

            result = self._request('POST', '/orders', data=payload)

            if result.get('success', False) or result.get('error_code') == '0':
                order_id = result.get('order_id', result.get('data', {}).get('order_id', ''))
                return True, order_id
            else:
                error_msg = result.get('error_msg', '下单失败')
                return False, error_msg

        except ConnectionError as e:
            return False, f'网络错误: {e}'
        except Exception as e:
            return False, f'下单异常: {e}'

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        try:
            result = self._request('DELETE', f'/orders/{order_id}')
            return result.get('success', False) or result.get('error_code') == '0'
        except Exception:
            return False

    def get_order_status(self, order_id: str) -> OrderStatus:
        """查询订单状态"""
        try:
            result = self._request('GET', f'/orders/{order_id}')
            status_map = {
                'pending': OrderStatus.PENDING,
                'submitted': OrderStatus.SUBMITTED,
                'partial_filled': OrderStatus.PARTIAL_FILLED,
                'filled': OrderStatus.FILLED,
                'cancelled': OrderStatus.CANCELLED,
                'rejected': OrderStatus.REJECTED
            }
            return status_map.get(result.get('status', ''), OrderStatus.PENDING)
        except Exception:
            return OrderStatus.PENDING

    def get_today_trades(self) -> List[dict]:
        """获取今日成交"""
        try:
            result = self._request('GET', '/trades/today')
            return result.get('trades', [])
        except Exception:
            return []


class WebSocketBrokerAdapter(BrokerAdapter):
    """
    WebSocket 券商适配器

    适用于需要实时行情和快速订单确认的场景
    如：XTP、顶点等柜台
    """

    def __init__(self, account_id: str,
                 ws_url: str,
                 api_key: str = '',
                 api_secret: str = '',
                 test_mode: bool = True):
        super().__init__(
            account_id=account_id,
            api_key=api_key,
            api_secret=api_secret,
            test_mode=test_mode
        )
        self.ws_url = ws_url
        self._ws = None
        self._pending_orders: Dict[str, Order] = {}
        self._last_quotes: Dict[str, dict] = {}

    def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            import websocket
            self._ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            thread.start()
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            print(f'WebSocket连接失败: {e}')
            return False

    def disconnect(self):
        if self._ws:
            self._ws.close()
        self.connected = False

    def _on_message(self, ws, message):
        import json
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')
            if msg_type == 'quote':
                self._last_quotes[data['symbol']] = data
            elif msg_type == 'order':
                order_id = data.get('order_id')
                if order_id in self._pending_orders:
                    self._pending_orders[order_id].status = OrderStatus.FILLED
        except Exception:
            pass

    def _on_error(self, ws, error):
        print(f'WebSocket错误: {error}')

    def _on_close(self, ws, close_status_code, close_msg):
        self.connected = False

    def _on_open(self, ws):
        import json
        ws.send(json.dumps({
            'type': 'auth',
            'account_id': self.account_id,
            'api_key': self.api_key,
            'api_secret': self.api_secret
        }))

    def place_order(self, order: Order) -> Tuple[bool, str]:
        if not self.connected:
            return False, '未连接'
        self._pending_orders[order.order_id] = order
        import json
        self._ws.send(json.dumps({
            'type': 'order',
            'symbol': order.symbol,
            'side': order.side.value,
            'price': order.price,
            'quantity': order.quantity
        }))
        return True, order.order_id

    def get_account(self) -> AccountInfo:
        return AccountInfo(0, 0, 0, 0, 0)

    def get_positions(self) -> List[PositionInfo]:
        return []

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        return None

    def cancel_order(self, order_id: str) -> bool:
        return False

    def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.PENDING

    def get_today_trades(self) -> List[dict]:
        return []


import threading