"""
风控模块
审核所有交易信号，执行风控检查
"""

import sys
from pathlib import Path
from datetime import datetime, time
sys.path.append(str(Path(__file__).parent.parent))

from config import RISK_PARAMS
from modules.logger import Logger, LogType


class RiskRule:
    """风控规则基类"""
    
    def __init__(self, name, enabled=True):
        self.name = name
        self.enabled = enabled
        
    def check(self, context):
        """
        检查风控规则
        
        Parameters:
        -----------
        context : dict
            包含交易上下文信息
            
        Returns:
        --------
        tuple (bool, str)
            (是否通过, 消息)
        """
        raise NotImplementedError


class MaxPositionPerTrade(RiskRule):
    """单一标的最大仓位"""
    
    def __init__(self, max_pct=0.1):
        super().__init__('单一标的最大仓位')
        self.max_pct = max_pct
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        total_value = context.get('portfolio_value', 0)
        position_value = context.get('position_value', 0)
        max_value = total_value * self.max_pct
        
        if position_value > max_value:
            return False, f"单一仓位超过限制: {position_value/total_value*100:.2f}% > {self.max_pct*100:.2f}%"
            
        return True, f"仓位检查通过: {position_value/total_value*100:.2f}%"


class MaxLossPerTrade(RiskRule):
    """单笔最大亏损"""
    
    def __init__(self, max_pct=0.005):
        super().__init__('单笔最大亏损')
        self.max_pct = max_pct
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        entry_price = context.get('entry_price', 0)
        current_price = context.get('current_price', 0)
        position_size = context.get('position_size', 0)
        
        if entry_price > 0 and position_size > 0:
            loss_per_share = entry_price - current_price
            total_loss = abs(loss_per_share) * position_size
            total_value = context.get('portfolio_value', 1)
            loss_pct = total_loss / total_value
            
            if loss_pct > self.max_pct:
                return False, f"单笔亏损超过限制: {loss_pct*100:.2f}% > {self.max_pct*100:.2f}%"
                
        return True, "单笔亏损检查通过"


class DailyLossLimit(RiskRule):
    """每日最大亏损"""
    
    def __init__(self, max_pct=0.01):
        super().__init__('每日最大亏损')
        self.max_pct = max_pct
        self.daily_loss = 0
        self.last_reset_date = None
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        current_date = datetime.now().date()
        
        if self.last_reset_date != current_date:
            self.daily_loss = 0
            self.last_reset_date = current_date
            
        today_pnl = context.get('daily_pnl', 0)
        total_value = context.get('portfolio_value', 1)
        
        if today_pnl < 0:
            self.daily_loss = abs(today_pnl)
            loss_pct = self.daily_loss / total_value
            
            if loss_pct > self.max_pct:
                return False, f"今日亏损超过限制: {loss_pct*100:.2f}% > {self.max_pct*100:.2f}%"
                
        return True, f"每日亏损检查通过: {self.daily_loss/total_value*100:.2f}%"


class TotalDrawdownLimit(RiskRule):
    """总最大回撤"""
    
    def __init__(self, max_pct=0.05):
        super().__init__('总最大回撤')
        self.max_pct = max_pct
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        current_value = context.get('portfolio_value', 0)
        peak_value = context.get('peak_value', current_value)
        
        if peak_value > 0:
            drawdown = (peak_value - current_value) / peak_value
            
            if drawdown > self.max_pct:
                return False, f"总回撤超过限制: {drawdown*100:.2f}% > {self.max_pct*100:.2f}%"
                
        return True, "总回撤检查通过"


class ConsecutiveLossLimit(RiskRule):
    """连续亏损次数限制"""
    
    def __init__(self, max_losses=5):
        super().__init__('连续亏损次数')
        self.max_losses = max_losses
        self.consecutive_losses = 0
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        if self.consecutive_losses >= self.max_losses:
            return False, f"连续亏损次数超过限制: {self.consecutive_losses} >= {self.max_losses}"
            
        return True, f"连续亏损检查通过: {self.consecutive_losses}/{self.max_losses}"
    
    def record_loss(self):
        """记录一次亏损"""
        self.consecutive_losses += 1
        
    def record_win(self):
        """记录一次盈利，重置计数"""
        self.consecutive_losses = 0


class DataQualityCheck(RiskRule):
    """数据质量检查"""
    
    def __init__(self):
        super().__init__('数据质量')
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        if context.get('data_missing', False):
            return False, "数据缺失，禁止交易"
            
        if context.get('price_anomaly', False):
            return False, "价格异常，禁止交易"
            
        if context.get('volume_anomaly', False):
            return False, "成交量异常，禁止交易"
            
        return True, "数据质量检查通过"


class ReasonabilityCheck(RiskRule):
    """交易原因合理性检查"""
    
    def __init__(self):
        super().__init__('交易合理性')
        
    def check(self, context):
        if not self.enabled:
            return True, "规则已禁用"
            
        reason = context.get('signal_reason', '')
        
        if not reason:
            if context.get('force_trade', False):
                return True, "强制交易"
            return False, "无法解释交易原因，禁止交易"
            
        return True, f"交易合理性检查通过: {reason}"


class RiskManager:
    """风控管理器"""
    
    def __init__(self, params=None, logger=None):
        self.params = params or RISK_PARAMS
        self.logger = logger or Logger()
        
        self.rules = {
            'max_position': MaxPositionPerTrade(self.params['单一标的最大仓位']),
            'max_loss_per_trade': MaxLossPerTrade(self.params['单笔最大风险比例']),
            'daily_loss': DailyLossLimit(self.params['每日最大亏损']),
            'total_drawdown': TotalDrawdownLimit(self.params['总最大回撤']),
            'consecutive_loss': ConsecutiveLossLimit(self.params['最大连续亏损次数']),
            'data_quality': DataQualityCheck(),
            'reasonability': ReasonabilityCheck(),
        }
        
        self.enabled = True
        
    def check_order(self, order_context):
        """
        检查订单是否通过风控
        
        Parameters:
        -----------
        order_context : dict
            订单上下文信息
            
        Returns:
        --------
        tuple (bool, list)
            (是否通过, 拒绝原因列表)
        """
        if not self.enabled:
            return True, []
            
        rejections = []
        
        for rule_name, rule in self.rules.items():
            passed, message = rule.check(order_context)
            
            if not passed:
                rejections.append(f"{rule.name}: {message}")
                self.logger.log_risk({
                    'event': '风控拒绝',
                    '规则': rule.name,
                    '原因': message,
                    '上下文': order_context
                })
                
        if rejections:
            return False, rejections
        else:
            self.logger.log_risk({
                'event': '风控通过',
                '上下文': order_context
            })
            return True, []
            
    def check_signal(self, signal_context):
        """检查信号是否通过风控"""
        return self.check_order(signal_context)
        
    def record_trade_result(self, pnl):
        """记录交易结果"""
        if pnl < 0:
            self.rules['consecutive_loss'].record_loss()
        else:
            self.rules['consecutive_loss'].record_win()
            
    def reset_daily(self):
        """重置每日状态"""
        self.rules['daily_loss'].daily_loss = 0
        
    def get_status(self):
        """获取风控状态"""
        return {
            'enabled': self.enabled,
            'rules': {
                name: {
                    'enabled': rule.enabled,
                    'name': rule.name
                }
                for name, rule in self.rules.items()
            },
            'consecutive_losses': self.rules['consecutive_loss'].consecutive_losses
        }
        
    def enable(self):
        """启用风控"""
        self.enabled = True
        self.logger.log_system({'event': '风控已启用'})
        
    def disable(self, reason='手动禁用'):
        """禁用风控"""
        self.enabled = False
        self.logger.log_system({'event': f'风控已禁用: {reason}'})


if __name__ == '__main__':
    logger = Logger()
    risk_mgr = RiskManager(logger=logger)
    
    test_context = {
        'portfolio_value': 100000,
        'position_value': 5000,
        'entry_price': 10.0,
        'current_price': 9.5,
        'position_size': 1000,
        'daily_pnl': -500,
        'peak_value': 105000,
        'signal_reason': '均线金叉'
    }
    
    passed, reasons = risk_mgr.check_order(test_context)
    
    print(f"\n风控检查结果: {'通过' if passed else '拒绝'}")
    if reasons:
        print("拒绝原因:")
        for reason in reasons:
            print(f"  - {reason}")
            
    print(f"\n风控状态: {risk_mgr.get_status()}")
