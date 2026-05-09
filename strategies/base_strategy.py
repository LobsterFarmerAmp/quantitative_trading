"""
基础策略类
所有策略必须继承此类
"""

import backtrader as bt
from datetime import datetime


class BaseStrategy(bt.Strategy):
    """量化策略基类"""
    
    params = (
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        self.order = None
        self.trade_log = []
        self.signal_log = []
        self.buy_price = None
        self.buy_comm = None
        
    def generate_signal(self):
        """生成交易信号 - 子类必须重写此方法"""
        raise NotImplementedError("子类必须实现 generate_signal 方法")
        
    def log(self, txt, dt=None):
        """日志记录"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'[{dt.isoformat()}] {txt}')
            
    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入执行: 价格 {order.executed.price:.2f}, '
                        f'数量 {order.executed.size}, '
                        f'成本 {order.executed.value:.2f}, '
                        f'手续费 {order.executed.comm:.2f}')
                self.buy_price = order.executed.price
                self.buy_comm = order.executed.comm
            else:
                self.log(f'卖出执行: 价格 {order.executed.price:.2f}, '
                        f'数量 {order.executed.size}, '
                        f'成本 {order.executed.value:.2f}, '
                        f'手续费 {order.executed.comm:.2f}')
                
            self.bar_executed = len(self)
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单被取消/保证金不足/拒绝')
            
        self.order = None
        
    def notify_trade(self, trade):
        """交易通知"""
        if not trade.isclosed:
            return
            
        self.log(f'交易利润: 毛利润 {trade.pnl:.2f}, 净利润 {trade.pnlcomm:.2f}')
        
        self.trade_log.append({
            'date': self.datas[0].datetime.date(0),
            'symbol': trade.data._name,
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm,
            'size': trade.size,
        })
        
    def next(self):
        """K线数据执行"""
        if self.order:
            return
            
        signal = self.generate_signal()
        
        if signal == 'BUY' and not self.position:
            size = self.calculate_position_size('BUY')
            if size > 0:
                self.order = self.buy()
                self.log(f'买入信号: {self.datas[0]._name}, 价格 {self.data.close[0]:.2f}, 数量 {size}')
                self.signal_log.append({
                    'date': self.datas[0].datetime.date(0),
                    'symbol': self.datas[0]._name,
                    'signal': 'BUY',
                    'price': self.data.close[0],
                    'reason': self.get_signal_reason()
                })
                
        elif signal == 'SELL' and self.position:
            self.order = self.sell()
            self.log(f'卖出信号: {self.datas[0]._name}, 价格 {self.data.close[0]:.2f}')
            self.signal_log.append({
                'date': self.datas[0].datetime.date(0),
                'symbol': self.datas[0]._name,
                'signal': 'SELL',
                'price': self.data.close[0],
                'reason': self.get_signal_reason()
            })
            
    def calculate_position_size(self, signal):
        """计算仓位大小"""
        cash = self.broker.getcash()
        price = self.data.close[0]
        
        max_position_value = cash * 0.1
        
        if signal == 'BUY':
            available_cash = cash * 0.95
            size = int(available_cash / price / 100) * 100
            
            if size * price > max_position_value:
                size = int(max_position_value / price / 100) * 100
                
            return size
        return 0
        
    def get_signal_reason(self):
        """获取信号原因 - 子类可重写"""
        return '策略信号'
        
    def stop(self):
        """策略结束时调用"""
        self.log(f'策略结束, 最终市值 {self.broker.getvalue():.2f}', dt=None)


class MultiSignalStrategy(BaseStrategy):
    """多信号策略基类"""
    
    params = (
        ('max_positions', 5),
        ('position_per_stock', 0.1),
    )
    
    def __init__(self):
        super().__init__()
        self.indicators = {}
        
    def calculate_position_size(self, signal):
        """计算仓位大小 - 支持多持仓"""
        if signal == 'BUY':
            cash = self.broker.getcash()
            num_positions = len([d for d in self.datas if self.getposition(d).size > 0])
            
            if num_positions >= self.params.max_positions:
                return 0
                
            available_positions = self.params.max_positions - num_positions
            position_value = self.broker.getvalue() * self.params.position_per_stock
            
            price = self.data.close[0]
            size = int(position_value / price / 100) * 100
            
            return size
        return 0
