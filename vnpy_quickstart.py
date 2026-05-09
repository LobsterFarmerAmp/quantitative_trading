"""
vn.py 快速启动指南
Phase 7 实盘交易准备
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

print('='*70)
print('vn.py 快速启动指南')
print('='*70)

print('''
第1步：安装 vn.py
-------------------------
pip install vnpy

第2步：启动 vn.py Trader
-------------------------
cd C:\\Users\\Lobst\\AppData\\Roaming\\Python\\Python312\\site-packages\\vnpy

# 启动 CT P 模拟账户
python run.py --ctp

# 或启动 IB API（需要 Interactive Brokers 账户）
python run.py --ib

第3步：配置连接参数
-------------------------
编辑 config/vnpy_connect.json:
{
    "gateway": "CTP",
    "broker_id": "9999",
    "user_id": "your_user_id",
    "password": "your_password",
    "td_address": "tcp://127.0.0.1:2014",
    "md_address": "tcp://127.0.0.1:2014",
    "auth_code": "",
    "app_id": "test_app"
}

第4步：在 vn.py 界面中
-------------------------
1. 登录交易账户
2. 连接行情和交易服务器
3. 确认合约信息

第5步：运行量化策略
-------------------------
from broker import VnpyBrokerAdapter
from live_executor import LiveExecutor

adapter = VnpyBrokerAdapter(
    account_id='YOUR_ACCOUNT',
    td_address='tcp://127.0.0.1:2014',
    user_id='your_user_id',
    password='your_password'
)

if adapter.connect():
    executor = LiveExecutor(broker=adapter)
    executor.start()
    # ... 运行策略
else:
    print("请先启动 vn.py 网关")
''')