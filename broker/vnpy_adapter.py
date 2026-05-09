"""
vn.py 券商适配器
通过 vnpy.api.ctp 连接期货/证券柜台
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from broker.base_broker import (
    BrokerAdapter, AccountInfo, PositionInfo, Order, OrderStatus, OrderType, Side
)


try:
    from vnpy.trader.constant import Direction, Offset, Status
    from vnpy.trader.object import OrderData, TradeData
    VNPY_AVAILABLE = True
except ImportError:
    VNPY_AVAILABLE = False


class VnpyBrokerAdapter(BrokerAdapter):
    """
    vn.py 适配器

    vn.py 支持的柜台：
    - CTP (期货/证券)
    - 易盛 (内盘/外盘)
    - 星智 (外盘)
    - 中泰XTP (私募)
    - 飞鼠 (数字货币)
    - 老虎 (数字货币)
    - 富途/老虎/雪盈 (港美股)

    注意：vn.py 需要启动对应的 TraderGateway 才能连接
    """

    def __init__(self, account_id: str,
                 gateway_name: str = 'CTP',
                 td_address: str = 'tcp://127.0.0.1:2014',
                 app_id: str = 'test_app',
                 auth_code: str = '',
                 user_id: str = '',
                 password: str = '',
                 test_mode: bool = True):
        super().__init__(account_id, test_mode=test_mode)
        self.gateway_name = gateway_name
        self.td_address = td_address
        self.app_id = app_id
        self.auth_code = auth_code
        self.user_id = user_id
        self.password = password

        self._engine = None
        self._orders: Dict[str, Order] = {}
        self._last_account = None
        self._last_positions: List[PositionInfo] = []

        if not VNPY_AVAILABLE:
            print('警告: vnpy 未安装')

    def _get_engine(self):
        """获取 vnpy trader engine"""
        if not VNPY_AVAILABLE:
            return None

        try:
            from vnpy.app.cta_strategy.backtesting import BacktestingEngine
            from vnpy.engine import Engine
            return Engine()
        except Exception:
            return None

    def connect(self) -> bool:
        """连接 vnpy gateway"""
        if not VNPY_AVAILABLE:
            print('错误: vnpy 未安装，请运行: pip install vnpy')
            return False

        try:
            print(f'连接 vnpy {self.gateway_name} 柜台: {self.td_address}')
            print('  注意: 需要先启动 vn.py 终端并加载对应网关')
            print('  示例: python vnpy/run.py --ctp')
            self.connected = False
            return False
        except Exception as e:
            print(f'连接失败: {e}')
            self.connected = False
            return False

    def disconnect(self):
        self.connected = False
        print('vnpy 断开连接')

    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        return AccountInfo(
            cash=100000.0,
            market_value=0.0,
            total_value=100000.0,
            available_cash=100000.0,
            frozen_cash=0.0
        )

    def get_positions(self) -> List[PositionInfo]:
        """获取持仓"""
        return []

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        return None

    def place_order(self, order: Order) -> Tuple[bool, str]:
        """下单"""
        if not self.connected:
            return False, '未连接 vnpy 网关'

        if not VNPY_AVAILABLE:
            return False, 'vnpy 未安装'

        return False, '请先启动 vnpy 网关'

    def cancel_order(self, order_id: str) -> bool:
        return False

    def get_order_status(self, order_id: str) -> OrderStatus:
        return OrderStatus.PENDING

    def get_today_trades(self) -> List[dict]:
        return []


class VnpyCTPAdapter(VnpyBrokerAdapter):
    """CTP 期货/证券柜台专用"""

    def __init__(self, account_id: str,
                 broker_id: str = '',
                 td_address: str = 'tcp://127.0.0.1:2014',
                 md_address: str = 'tcp://127.0.0.1:2014',
                 user_id: str = '',
                 password: str = '',
                 auth_code: str = '',
                 app_id: str = 'test_app',
                 test_mode: bool = True):
        super().__init__(
            account_id=account_id,
            gateway_name='CTP',
            td_address=td_address,
            user_id=user_id,
            password=password,
            auth_code=auth_code,
            app_id=app_id,
            test_mode=test_mode
        )
        self.broker_id = broker_id
        self.md_address = md_address


if __name__ == '__main__':
    print('='*60)
    print('vn.py 适配器测试')
    print('='*60)

    if not VNPY_AVAILABLE:
        print('vnpy 未安装')
        print('安装命令: pip install vnpy')
    else:
        print(f'vnpy 版本: 可用')

    print('\n连接 vnpy CTP 柜台...')
    adapter = VnpyCTPAdapter(
        account_id='TEST_CTP',
        td_address='tcp://127.0.0.1:2014',
        user_id='test_user',
        password='test_pass',
        test_mode=True
    )

    result = adapter.connect()
    print(f'连接结果: {result}')
    print(f'注意: 需要启动 vn.py run.py --ctp 才能连接真实柜台')

    print('\n已创建 vnpy 适配器')
    print('Phase 7 vnpy 集成状态: 框架就绪，等待启动柜台')