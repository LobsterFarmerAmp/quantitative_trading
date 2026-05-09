"""
Kill Switch 紧急停止模块
在紧急情况下立即停止所有交易
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum


class KillSwitchReason(Enum):
    """停止原因"""
    MANUAL = 'manual'                     # 手动触发
    MAX_DRAWDOWN = 'max_drawdown'       # 最大回撤
    MAX_DAILY_LOSS = 'max_daily_loss'   # 每日最大亏损
    CONSECUTIVE_LOSSES = 'consecutive_losses'  # 连续亏损
    SYSTEM_ERROR = 'system_error'        # 系统错误
    NETWORK_ERROR = 'network_error'      # 网络错误
    DATA_ERROR = 'data_error'          # 数据错误
    RISK_VIOLATION = 'risk_violation' # 风控违规
    ANOMALY_DETECTED = 'anomaly_detected'  # 检测到异常


class KillSwitch:
    """紧急停止开关"""
    
    def __init__(self, logger=None):
        """
        初始化Kill Switch
        
        Parameters:
        -----------
        logger : Logger, optional
            日志管理器
        """
        self.logger = logger
        self.is_activated = False
        self.activation_time = None
        self.reason = None
        self.trading_systems = []
        self.callbacks: List[Callable] = []
        
        self._log('Kill Switch 初始化完成')
        
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        if self.logger:
            self.logger.log_system({
                'event': 'KillSwitch',
                'level': level,
                'message': message
            })
        else:
            print(f"[KillSwitch][{level}] {message}")
            
    def register_trading_system(self, system):
        """注册交易系统"""
        if system not in self.trading_systems:
            self.trading_systems.append(system)
            self._log(f'注册交易系统: {type(system).__name__}')
            
    def unregister_trading_system(self, system):
        """注销交易系统"""
        if system in self.trading_systems:
            self.trading_systems.remove(system)
            self._log(f'注销交易系统: {type(system).__name__}')
            
    def register_callback(self, callback: Callable):
        """注册回调函数"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            self._log(f'注册回调函数: {callback.__name__}')
            
    def activate(self, reason: KillSwitchReason, message: str = '', force: bool = False):
        """
        激活Kill Switch
        
        Parameters:
        -----------
        reason : KillSwitchReason
            停止原因
        message : str
            详细消息
        force : bool
            是否强制停止
        """
        if self.is_activated and not force:
            self._log(f'Kill Switch 已经激活，无法重复激活', 'WARNING')
            return False
            
        self.is_activated = True
        self.activation_time = datetime.now()
        self.reason = reason
        
        self._log(f'!!! Kill Switch 激活 !!!', 'CRITICAL')
        self._log(f'原因: {reason.value} - {message}', 'CRITICAL')
        
        self._stop_all_systems()
        
        self._execute_callbacks()
        
        return True
        
    def deactivate(self):
        """停用Kill Switch（需要手动确认）"""
        if not self.is_activated:
            self._log('Kill Switch 未激活', 'WARNING')
            return False
            
        self.is_activated = False
        self.activation_time = None
        self.reason = None
        
        self._log('Kill Switch 已停用')
        
        return True
        
    def _stop_all_systems(self):
        """停止所有交易系统"""
        for system in self.trading_systems:
            try:
                if hasattr(system, 'stop'):
                    system.stop()
                    self._log(f'已停止系统: {type(system).__name__}')
                    
                if hasattr(system, 'pause'):
                    system.pause()
                    self._log(f'已暂停系统: {type(system).__name__}')
                    
            except Exception as e:
                self._log(f'停止系统失败: {type(system).__name__}, 错误: {str(e)}', 'ERROR')
                
    def _execute_callbacks(self):
        """执行回调函数"""
        for callback in self.callbacks:
            try:
                callback(self.reason, self.activation_time)
                self._log(f'执行回调: {callback.__name__}')
            except Exception as e:
                self._log(f'回调执行失败: {callback.__name__}, 错误: {str(e)}', 'ERROR')
                
    def check_max_drawdown(self, current_value: float, peak_value: float, 
                          max_drawdown_threshold: float = 0.05) -> bool:
        """
        检查最大回撤
        
        Returns:
        --------
        bool
            是否触发Kill Switch
        """
        if peak_value <= 0:
            return False
            
        drawdown = (peak_value - current_value) / peak_value
        
        if drawdown >= max_drawdown_threshold:
            message = f'最大回撤 {drawdown*100:.2f}% 超过阈值 {max_drawdown_threshold*100:.2f}%'
            self.activate(KillSwitchReason.MAX_DRAWDOWN, message)
            return True
            
        return False
        
    def check_daily_loss(self, initial_value: float, current_value: float,
                        max_loss_threshold: float = 0.01) -> bool:
        """
        检查每日亏损
        
        Returns:
        --------
        bool
            是否触发Kill Switch
        """
        if initial_value <= 0:
            return False
            
        loss = (initial_value - current_value) / initial_value
        
        if loss >= max_loss_threshold:
            message = f'每日亏损 {loss*100:.2f}% 超过阈值 {max_loss_threshold*100:.2f}%'
            self.activate(KillSwitchReason.MAX_DAILY_LOSS, message)
            return True
            
        return False
        
    def check_consecutive_losses(self, consecutive_losses: int,
                                max_consecutive: int = 5) -> bool:
        """
        检查连续亏损
        
        Returns:
        --------
        bool
            是否触发Kill Switch
        """
        if consecutive_losses >= max_consecutive:
            message = f'连续亏损 {consecutive_losses} 次，超过阈值 {max_consecutive} 次'
            self.activate(KillSwitchReason.CONSECUTIVE_LOSSES, message)
            return True
            
        return False
        
    def trigger_manual(self, message: str = '手动触发'):
        """手动触发Kill Switch"""
        self.activate(KillSwitchReason.MANUAL, message, force=True)
        
    def trigger_system_error(self, error_message: str):
        """触发系统错误"""
        self.activate(KillSwitchReason.SYSTEM_ERROR, error_message, force=True)
        
    def trigger_network_error(self, error_message: str):
        """触发网络错误"""
        self.activate(KillSwitchReason.NETWORK_ERROR, error_message, force=True)
        
    def trigger_data_error(self, error_message: str):
        """触发数据错误"""
        self.activate(KillSwitchReason.DATA_ERROR, error_message, force=True)
        
    def get_status(self) -> dict:
        """获取状态"""
        return {
            'is_activated': self.is_activated,
            'activation_time': self.activation_time.strftime('%Y-%m-%d %H:%M:%S') if self.activation_time else None,
            'reason': self.reason.value if self.reason else None,
            'registered_systems': len(self.trading_systems),
            'callbacks': len(self.callbacks)
        }
        
    def is_active(self) -> bool:
        """检查是否激活"""
        return self.is_activated


class KillSwitchManager:
    """Kill Switch管理器"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.kill_switches: Dict[str, KillSwitch] = {}
        self.default_kill_switch = KillSwitch(logger)
        
        self._log('Kill Switch 管理器初始化')
        
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        if self.logger:
            self.logger.log_system({
                'event': 'KillSwitchManager',
                'level': level,
                'message': message
            })
        else:
            print(f"[KillSwitchManager][{level}] {message}")
            
    def create_kill_switch(self, name: str) -> KillSwitch:
        """创建命名的Kill Switch"""
        if name in self.kill_switches:
            self._log(f'Kill Switch 已存在: {name}', 'WARNING')
            return self.kill_switches[name]
            
        kill_switch = KillSwitch(self.logger)
        self.kill_switches[name] = kill_switch
        self._log(f'创建 Kill Switch: {name}')
        
        return kill_switch
        
    def get_kill_switch(self, name: str) -> Optional[KillSwitch]:
        """获取命名的Kill Switch"""
        return self.kill_switches.get(name)
        
    def get_default(self) -> KillSwitch:
        """获取默认Kill Switch"""
        return self.default_kill_switch
        
    def check_all(self) -> List[tuple]:
        """检查所有Kill Switch状态"""
        results = []
        
        if self.default_kill_switch.is_active():
            results.append(('default', True))
            
        for name, ks in self.kill_switches.items():
            if ks.is_active():
                results.append((name, True))
                
        return results
        
    def emergency_stop_all(self, reason: str):
        """紧急停止所有"""
        self._log('!!! 紧急停止所有系统 !!!', 'CRITICAL')
        
        self.default_kill_switch.trigger_manual(reason)
        
        for name, ks in self.kill_switches.items():
            ks.activate(KillSwitchReason.MANUAL, reason, force=True)
