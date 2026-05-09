"""
配置文件
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).parent

def load_json_config(filename):
    """加载JSON配置文件"""
    config_path = CONFIG_DIR / filename
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

RISK_PARAMS = {
    '单笔最大风险比例': 0.005,
    '单一标的最大仓位': 0.10,
    '每日最大亏损': 0.01,
    '总最大回撤': 0.05,
    '最大连续亏损次数': 5,
    '最小交易间隔': 1,
    '滑点比例': 0.0005,
    '最小交易金额': 100,
}

BROKER_PARAMS = {
    '模式': 'simulation',
    '初始资金': 100000,
    '佣金比例': 0.0003,
    '印花税比例': 0.001,
    '滑点比例': 0.0005,
    '最小交易单位': 100,
}

DATA_PARAMS = {
    '数据源': 'akshare',
    '缓存目录': 'data',
    '默认市场': 'A股',
    '时间范围': {
        '开始': '20180101',
        '结束': '20231231',
    },
}

STRATEGY_PARAMS = {
    '默认标的': '000001.XSHE',
    '默认周期': 'daily',
    '均线周期短期': 5,
    '均线周期长期': 20,
    '最大持仓数': 5,
    '最大仓位使用率': 0.8,
}

PROJECT_PARAMS = {
    '项目根目录': Path(__file__).parent.parent,
    '日志目录': 'logs',
    '报告目录': 'reports',
    '数据目录': 'data',
}
