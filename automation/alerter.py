"""
告警系统
发送交易和风控告警
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class AlertLevel(Enum):
    """告警级别"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertType(Enum):
    """告警类型"""
    TRADE = 'trade'               # 交易告警
    RISK = 'risk'                # 风控告警
    SYSTEM = 'system'            # 系统告警
    ANOMALY = 'anomaly'         # 异常告警
    PERFORMANCE = 'performance'   # 绩效告警


class Alert:
    """告警类"""
    
    def __init__(self, level: AlertLevel, alert_type: AlertType,
                 title: str, message: str, details: Optional[dict] = None):
        """
        初始化告警
        
        Parameters:
        -----------
        level : AlertLevel
            告警级别
        alert_type : AlertType
            告警类型
        title : str
            告警标题
        message : str
            告警消息
        details : dict, optional
            详细信息
        """
        self.level = level
        self.type = alert_type
        self.title = title
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.sent = False
        
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'level': self.level.value,
            'type': self.type.value,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'sent': self.sent
        }
        
    def __str__(self) -> str:
        return f"[{self.level.value.upper()}] {self.title}: {self.message}"


class Alerter:
    """告警管理器"""
    
    def __init__(self, logger=None):
        """
        初始化告警管理器
        
        Parameters:
        -----------
        logger : Logger, optional
            日志管理器
        """
        self.logger = logger
        self.alerts: List[Alert] = []
        self.handlers: Dict[AlertLevel, List] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.ERROR: [],
            AlertLevel.CRITICAL: []
        }
        self.enabled = True
        
        self._log('告警系统初始化完成')
        
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        if self.logger:
            self.logger.log_system({
                'event': 'Alerter',
                'level': level,
                'message': message
            })
        else:
            print(f"[Alerter][{level}] {message}")
            
    def register_handler(self, level: AlertLevel, handler):
        """注册告警处理器"""
        if handler not in self.handlers[level]:
            self.handlers[level].append(handler)
            self._log(f'注册处理器: {handler.__name__} for {level.value}')
            
    def send_alert(self, level: AlertLevel, alert_type: AlertType,
                  title: str, message: str, details: Optional[dict] = None) -> Alert:
        """
        发送告警
        
        Returns:
        --------
        Alert
            告警对象
        """
        if not self.enabled:
            self._log(f'告警已禁用，跳过: {title}', 'WARNING')
            return None
            
        alert = Alert(level, alert_type, title, message, details)
        
        self.alerts.append(alert)
        
        self._log(f'发送告警: [{level.value.upper()}] {title} - {message}', level.value.upper())
        
        self._process_alert(alert)
        
        return alert
        
    def _process_alert(self, alert: Alert):
        """处理告警"""
        handlers = self.handlers.get(alert.level, [])
        
        for handler in handlers:
            try:
                handler(alert)
                alert.sent = True
            except Exception as e:
                self._log(f'处理告警失败: {handler.__name__}, 错误: {str(e)}', 'ERROR')
                
    def send_trade_alert(self, symbol: str, action: str, price: float,
                       size: int, pnl: Optional[float] = None):
        """发送交易告警"""
        title = f"交易执行: {symbol}"
        message = f"{action} {size}股 @ ¥{price:.2f}"
        
        if pnl is not None:
            message += f", 盈亏: ¥{pnl:.2f}"
            
        details = {
            'symbol': symbol,
            'action': action,
            'price': price,
            'size': size,
            'pnl': pnl
        }
        
        return self.send_alert(
            level=AlertLevel.INFO,
            alert_type=AlertType.TRADE,
            title=title,
            message=message,
            details=details
        )
        
    def send_risk_alert(self, title: str, message: str, details: dict,
                       level: AlertLevel = AlertLevel.WARNING):
        """发送风控告警"""
        return self.send_alert(
            level=level,
            alert_type=AlertType.RISK,
            title=title,
            message=message,
            details=details
        )
        
    def send_anomaly_alert(self, anomaly_type: str, symbol: str,
                         message: str, details: dict):
        """发送异常告警"""
        return self.send_alert(
            level=AlertLevel.ERROR,
            alert_type=AlertType.ANOMALY,
            title=f"异常检测: {anomaly_type} - {symbol}",
            message=message,
            details=details
        )
        
    def send_critical_alert(self, title: str, message: str, details: Optional[dict] = None):
        """发送严重告警"""
        return self.send_alert(
            level=AlertLevel.CRITICAL,
            alert_type=AlertType.SYSTEM,
            title=title,
            message=message,
            details=details
        )
        
    def send_performance_alert(self, metrics: dict):
        """发送绩效告警"""
        title = "绩效报告"
        message = f"胜率: {metrics.get('win_rate', 0):.1f}%, 总盈亏: ¥{metrics.get('total_pnl', 0):.2f}"
        
        return self.send_alert(
            level=AlertLevel.INFO,
            alert_type=AlertType.PERFORMANCE,
            title=title,
            message=message,
            details=metrics
        )
        
    def get_alerts(self, level: Optional[AlertLevel] = None,
                  alert_type: Optional[AlertType] = None,
                  since: Optional[datetime] = None) -> List[Alert]:
        """获取告警列表"""
        filtered = self.alerts
        
        if level:
            filtered = [a for a in filtered if a.level == level]
            
        if alert_type:
            filtered = [a for a in filtered if a.type == alert_type]
            
        if since:
            filtered = [a for a in filtered if a.timestamp >= since]
            
        return filtered
        
    def get_recent_alerts(self, hours: int = 24, limit: int = 100) -> List[Alert]:
        """获取最近的告警"""
        since = datetime.now() - timedelta(hours=hours)
        return self.get_alerts(since=since)[:limit]
        
    def get_summary(self) -> dict:
        """获取告警摘要"""
        total = len(self.alerts)
        
        by_level = {}
        for level in AlertLevel:
            by_level[level.value] = len([a for a in self.alerts if a.level == level])
            
        by_type = {}
        for alert_type in AlertType:
            by_type[alert_type.value] = len([a for a in self.alerts if a.type == alert_type])
            
        recent = self.get_recent_alerts(hours=24)
        
        return {
            'total_alerts': total,
            'recent_24h': len(recent),
            'by_level': by_level,
            'by_type': by_type,
            'enabled': self.enabled
        }
        
    def enable(self):
        """启用告警"""
        self.enabled = True
        self._log('告警系统已启用')
        
    def disable(self):
        """禁用告警"""
        self.enabled = False
        self._log('告警系统已禁用')
        
    def clear_alerts(self):
        """清除所有告警"""
        self.alerts.clear()
        self._log('所有告警已清除')


def console_alert_handler(alert: Alert):
    """控制台告警处理器"""
    print(f"\n{'='*60}")
    print(f"[{alert.level.value.upper()}] {alert.title}")
    print(f"消息: {alert.message}")
    if alert.details:
        print(f"详情: {alert.details}")
    print(f"时间: {alert.timestamp}")
    print(f"{'='*60}\n")


def email_alert_handler(alert: Alert):
    """邮件告警处理器（示例）"""
    if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
        pass
        

def sms_alert_handler(alert: Alert):
    """短信告警处理器（示例）"""
    if alert.level == AlertLevel.CRITICAL:
        pass
