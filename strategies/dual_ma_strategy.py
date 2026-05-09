"""
双均线策略
趋势跟踪策略：短期均线上穿长期均线买入，下穿卖出
"""

import backtrader as bt
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from strategies.base_strategy import BaseStrategy


class DualMAStrategy(BaseStrategy):
    """
    双均线趋势跟踪策略
    
    策略逻辑：
    - 当短期均线从下往上穿越长期均线时，产生买入信号
    - 当短期均线从上往下穿越长期均线时，产生卖出信号
    
    适用市场：A股全市场
    交易频率：低频（持仓周期数天至数周）
    风险来源：震荡市频繁止损、趋势反转
    """
    
    params = (
        ('fast_period', 5),      # 短期均线周期
        ('slow_period', 20),     # 长期均线周期
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        self.fast_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.fast_period,
            plotname='短期均线'
        )
        
        self.slow_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.slow_period,
            plotname='长期均线'
        )
        
        self.crossover = bt.indicators.CrossOver(
            self.fast_ma, 
            self.slow_ma,
            plot=False
        )
        
        self.signal_reason = ''
        
    def generate_signal(self):
        """生成交易信号"""
        if len(self) < self.params.slow_period:
            return None
            
        if self.crossover[0] > 0:
            self.signal_reason = f'金叉：短期MA{self.params.fast_period}上穿长期MA{self.params.slow_period}'
            return 'BUY'
            
        elif self.crossover[0] < 0:
            self.signal_reason = f'死叉：短期MA{self.params.fast_period}下穿长期MA{self.params.slow_period}'
            return 'SELL'
            
        return None
        
    def get_signal_reason(self):
        """获取信号原因"""
        return self.signal_reason


class DualMAWithStopLoss(BaseStrategy):
    """
    双均线策略 + 止损
    
    在双均线策略基础上加入移动止损
    """
    
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('stop_loss_pct', 0.05),    # 止损比例 5%
        ('trailing_stop', True),     # 是否使用移动止损
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        self.fast_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.fast_period
        )
        
        self.slow_ma = bt.indicators.SMA(
            self.data.close, 
            period=self.params.slow_period
        )
        
        self.crossover = bt.indicators.CrossOver(
            self.fast_ma, 
            self.slow_ma
        )
        
        self.buy_price = None
        self.signal_reason = ''
        
    def generate_signal(self):
        """生成交易信号"""
        if len(self) < self.params.slow_period:
            return None
            
        if self.crossover[0] > 0 and not self.position:
            self.signal_reason = f'金叉买入，止损设置{self.params.stop_loss_pct*100}%'
            return 'BUY'
            
        elif self.crossover[0] < 0 and self.position:
            self.signal_reason = '死叉卖出'
            return 'SELL'
            
        if self.position and self.params.trailing_stop:
            if self.buy_price:
                current_price = self.data.close[0]
                price_change = (current_price - self.buy_price) / self.buy_price
                
                if price_change < -self.params.stop_loss_pct:
                    self.signal_reason = f'移动止损触发，亏损{abs(price_change)*100:.2f}%'
                    return 'SELL'
                    
        return None
        
    def notify_order(self, order):
        """订单通知"""
        super().notify_order(order)
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_price = order.executed.price
                
    def get_signal_reason(self):
        """获取信号原因"""
        return self.signal_reason


class DualMACrossIndex(DualMAStrategy):
    """
    改进版双均线策略：结合指数择时
    
    只在指数处于上升趋势时买入，下降趋势时保持空仓
    """
    
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
        ('index_code', '000001.XSHG'),
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        
        if len(self.datas) > 1:
            self.index_data = self.datas[1]
            
            self.index_fast_ma = bt.indicators.SMA(
                self.index_data.close,
                period=self.params.fast_period,
                plot=False
            )
            
            self.index_slow_ma = bt.indicators.SMA(
                self.index_data.close,
                period=self.params.slow_period,
                plot=False
            )
            
    def generate_signal(self):
        """生成交易信号"""
        if len(self) < self.params.slow_period:
            return None
            
        if len(self.datas) > 1:
            index_trend = self.index_fast_ma[0] > self.index_slow_ma[0]
            
            if not index_trend and self.position:
                self.signal_reason = '指数下降趋势，卖出'
                return 'SELL'
                
            elif index_trend and not self.position:
                if self.crossover[0] > 0:
                    self.signal_reason = f'金叉买入，指数上升趋势'
                    return 'BUY'
        else:
            if self.crossover[0] > 0 and not self.position:
                self.signal_reason = '金叉买入'
                return 'BUY'
                
            elif self.crossover[0] < 0 and self.position:
                self.signal_reason = '死叉卖出'
                return 'SELL'
                
        return None


if __name__ == '__main__':
    print("双均线策略类定义完成")
    print("\n策略选项:")
    print("1. DualMAStrategy - 基础双均线")
    print("2. DualMAWithStopLoss - 双均线+止损")
    print("3. DualMACrossIndex - 双均线+指数择时")
