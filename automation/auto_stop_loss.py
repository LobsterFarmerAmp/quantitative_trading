"""
自动止损模块
根据持仓亏损情况自动执行止损
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable


class StopLossRule:
    """止损规则"""
    
    def __init__(self, name: str, loss_threshold: float, 
                 action: str = 'close', enabled: bool = True):
        """
        初始化止损规则
        
        Parameters:
        -----------
        name : str
            规则名称
        loss_threshold : float
            亏损阈值（比例）
        action : str
            动作：'close' 关闭仓位, 'reduce' 减仓, 'alert' 仅告警
        enabled : bool
            是否启用
        """
        self.name = name
        self.loss_threshold = loss_threshold
        self.action = action
        self.enabled = enabled
        self.triggered_count = 0
        self.last_trigger_time = None
        
    def should_trigger(self, current_loss: float) -> bool:
        """判断是否应该触发"""
        if not self.enabled:
            return False
            
        if current_loss >= self.loss_threshold:
            self.triggered_count += 1
            self.last_trigger_time = datetime.now()
            return True
            
        return False
        
    def get_info(self) -> dict:
        """获取规则信息"""
        return {
            'name': self.name,
            'loss_threshold': self.loss_threshold,
            'action': self.action,
            'enabled': self.enabled,
            'triggered_count': self.triggered_count,
            'last_trigger_time': self.last_trigger_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_trigger_time else None
        }


class AutoStopLoss:
    """自动止损管理器"""
    
    def __init__(self, logger=None):
        """
        初始化自动止损
        
        Parameters:
        -----------
        logger : Logger, optional
            日志管理器
        """
        self.logger = logger
        self.rules: List[StopLossRule] = []
        self.callbacks: List[Callable] = []
        self.is_enabled = True
        
        self._setup_default_rules()
        self._log('自动止损初始化完成')
        
    def _setup_default_rules(self):
        """设置默认止损规则"""
        self.add_rule(StopLossRule(
            name='止损线',
            loss_threshold=0.05,  # 5%
            action='close',
            enabled=True
        ))
        
        self.add_rule(StopLossRule(
            name='警告线',
            loss_threshold=0.03,  # 3%
            action='alert',
            enabled=True
        ))
        
        self.add_rule(StopLossRule(
            name='减仓线',
            loss_threshold=0.02,  # 2%
            action='reduce',
            enabled=True
        ))
        
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        if self.logger:
            self.logger.log_system({
                'event': 'AutoStopLoss',
                'level': level,
                'message': message
            })
        else:
            print(f"[AutoStopLoss][{level}] {message}")
            
    def add_rule(self, rule: StopLossRule):
        """添加止损规则"""
        self.rules.append(rule)
        self._log(f'添加止损规则: {rule.name} - 亏损阈值 {rule.loss_threshold*100:.1f}%')
        
    def remove_rule(self, name: str) -> bool:
        """移除止损规则"""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                self._log(f'移除止损规则: {name}')
                return True
        return False
        
    def get_rule(self, name: str) -> Optional[StopLossRule]:
        """获取止损规则"""
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None
        
    def enable_rule(self, name: str) -> bool:
        """启用规则"""
        rule = self.get_rule(name)
        if rule:
            rule.enabled = True
            self._log(f'启用止损规则: {name}')
            return True
        return False
        
    def disable_rule(self, name: str) -> bool:
        """禁用规则"""
        rule = self.get_rule(name)
        if rule:
            rule.enabled = False
            self._log(f'禁用止损规则: {name}')
            return True
        return False
        
    def register_callback(self, callback: Callable):
        """注册回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self._log(f'注册回调函数: {callback.__name__}')
            
    def check_position(self, symbol: str, entry_price: float, 
                      current_price: float, position_size: int) -> List[dict]:
        """
        检查持仓是否应该止损
        
        Returns:
        --------
        List[dict]
            需要执行的操作列表
        """
        if not self.is_enabled:
            return []
            
        actions = []
        
        cost = entry_price * position_size
        current_value = current_price * position_size
        loss = cost - current_value
        loss_pct = loss / cost if cost > 0 else 0
        
        triggered_rules = []
        
        for rule in self.rules:
            if rule.should_trigger(loss_pct):
                triggered_rules.append(rule)
                
        if not triggered_rules:
            return []
            
        triggered_rules.sort(key=lambda r: r.loss_threshold, reverse=True)
        
        primary_rule = triggered_rules[0]
        
        action = {
            'symbol': symbol,
            'loss_pct': loss_pct,
            'loss_amount': loss,
            'rule': primary_rule.name,
            'action': primary_rule.action,
            'trigger_time': datetime.now()
        }
        
        actions.append(action)
        
        self._log(f'触发止损: {symbol} - 亏损 {loss_pct*100:.2f}% - 规则: {primary_rule.name} - 动作: {primary_rule.action}', 
                 'WARNING')
        
        self._execute_callbacks(symbol, action)
        
        return actions
        
    def _execute_callbacks(self, symbol: str, action: dict):
        """执行回调函数"""
        for callback in self.callbacks:
            try:
                callback(symbol, action)
            except Exception as e:
                self._log(f'回调执行失败: {callback.__name__}, 错误: {str(e)}', 'ERROR')
                
    def get_all_rules(self) -> List[dict]:
        """获取所有规则"""
        return [rule.get_info() for rule in self.rules]
        
    def get_trigger_summary(self) -> dict:
        """获取触发摘要"""
        total_triggers = sum(rule.triggered_count for rule in self.rules)
        
        by_rule = {}
        for rule in self.rules:
            by_rule[rule.name] = {
                'triggered_count': rule.triggered_count,
                'enabled': rule.enabled
            }
            
        return {
            'total_triggers': total_triggers,
            'by_rule': by_rule,
            'enabled': self.is_enabled
        }
        
    def reset(self):
        """重置统计"""
        for rule in self.rules:
            rule.triggered_count = 0
        self._log('统计已重置')
        
    def enable(self):
        """启用自动止损"""
        self.is_enabled = True
        self._log('自动止损已启用')
        
    def disable(self):
        """禁用自动止损"""
        self.is_enabled = False
        self._log('自动止损已禁用')
