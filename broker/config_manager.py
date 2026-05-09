"""
券商配置管理器
统一管理所有券商的API密钥和连接参数
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
from typing import Optional, Dict


class BrokerConfig:
    """券商配置"""

    def __init__(self, name: str, broker_type: str,
                 api_url: str = '', api_key: str = '',
                 api_secret: str = '', account_id: str = '',
                 test_mode: bool = True, enabled: bool = True,
                 extra: Optional[Dict] = None):
        self.name = name
        self.broker_type = broker_type
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.test_mode = test_mode
        self.enabled = enabled
        self.extra = extra or {}

    @classmethod
    def from_dict(cls, data: dict) -> 'BrokerConfig':
        return cls(
            name=data.get('name', ''),
            broker_type=data.get('broker_type', 'sim'),
            api_url=data.get('api_url', ''),
            api_key=data.get('api_key', ''),
            api_secret=data.get('api_secret', ''),
            account_id=data.get('account_id', ''),
            test_mode=data.get('test_mode', True),
            enabled=data.get('enabled', True),
            extra=data.get('extra', {})
        )

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'broker_type': self.broker_type,
            'api_url': self.api_url,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'account_id': self.account_id,
            'test_mode': self.test_mode,
            'enabled': self.enabled,
            'extra': self.extra
        }


class ConfigManager:
    """
    配置管理器

    支持：
    1. 从 broker_config.yaml/json 加载
    2. 环境变量覆盖
    3. 运行时修改
    """

    DEFAULT_CONFIG = {
        'brokers': [
            {
                'name': '模拟券商',
                'broker_type': 'sim',
                'account_id': 'SIM_ACCOUNT_001',
                'test_mode': True,
                'enabled': True
            },
            {
                'name': 'XTP柜台',
                'broker_type': 'xtp',
                'api_url': 'tcp://127.0.0.1:9000',
                'account_id': '',
                'api_key': '',
                'api_secret': '',
                'test_mode': True,
                'enabled': False
            },
            {
                'name': 'HTTP网关',
                'broker_type': 'http',
                'api_url': 'http://127.0.0.1:8080/api',
                'account_id': '',
                'api_key': '',
                'api_secret': '',
                'test_mode': True,
                'enabled': False
            },
            {
                'name': 'vn.py集成',
                'broker_type': 'vnpy',
                'api_url': 'ws://127.0.0.1:9999',
                'account_id': '',
                'api_key': '',
                'api_secret': '',
                'test_mode': True,
                'enabled': False
            }
        ],
        'risk': {
            '单笔最大仓位': 0.10,
            '单笔最大风险比例': 0.005,
            '每日最大亏损': 0.01,
            '总最大回撤': 0.05,
            '最大连续亏损次数': 5
        },
        'trading': {
            '初始资金': 100000,
            '佣金比例': 0.0003,
            '印花税比例': 0.001,
            '滑点比例': 0.0005,
            '最小交易单位': 100
        },
        'data': {
            '数据源': 'baostock',
            '缓存目录': 'data',
            '刷新间隔秒': 5
        }
    }

    def __init__(self, config_file: str = 'config/broker_config.json'):
        self.config_file = Path(config_file)
        self.config = {}
        self.load()

    def load(self):
        """从文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print(f'从 {self.config_file} 加载配置')
                return
            except Exception as e:
                print(f'加载配置失败: {e}')

        self.config = self.DEFAULT_CONFIG.copy()
        self.save()

    def save(self):
        """保存配置到文件"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f'配置已保存到 {self.config_file}')
        except Exception as e:
            print(f'保存配置失败: {e}')

    def get_enabled_brokers(self) -> list:
        """获取已启用的券商列表"""
        return [
            BrokerConfig.from_dict(b)
            for b in self.config.get('brokers', [])
            if b.get('enabled', False)
        ]

    def get_broker(self, name: str) -> Optional[BrokerConfig]:
        """获取指定券商配置"""
        for b in self.config.get('brokers', []):
            if b.get('name') == name:
                return BrokerConfig.from_dict(b)
        return None

    def get_risk_config(self) -> dict:
        return self.config.get('risk', {})

    def get_trading_config(self) -> dict:
        return self.config.get('trading', {})

    def get_data_config(self) -> dict:
        return self.config.get('data', {})

    def enable_broker(self, name: str):
        """启用券商"""
        for b in self.config.get('brokers', []):
            if b.get('name') == name:
                b['enabled'] = True
                self.save()
                return True
        return False

    def disable_broker(self, name: str):
        """禁用券商"""
        for b in self.config.get('brokers', []):
            if b.get('name') == name:
                b['enabled'] = False
                self.save()
                return True
        return False

    def update_broker_credential(self, name: str, account_id: str = None,
                                   api_key: str = None, api_secret: str = None):
        """更新券商凭证"""
        for b in self.config.get('brokers', []):
            if b.get('name') == name:
                if account_id:
                    b['account_id'] = account_id
                if api_key:
                    b['api_key'] = api_key
                if api_secret:
                    b['api_secret'] = api_secret
                self.save()
                return True
        return False


if __name__ == '__main__':
    mgr = ConfigManager()
    print('已配置券商:')
    for b in mgr.get_enabled_brokers():
        print(f"  {b.name} ({b.broker_type}) - {'测试' if b.test_mode else '实盘'}")

    print(f'\n风控配置: {mgr.get_risk_config()}')
    print(f'\n交易配置: {mgr.get_trading_config()}')