"""
异常检测模块
检测市场异常和系统异常
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class AnomalyType:
    """异常类型枚举"""
    PRICE_SPIKE = 'price_spike'           # 价格异常波动
    VOLUME_SPIKE = 'volume_spike'         # 成交量异常
    PRICE_DROP = 'price_drop'             # 价格异常下跌
    PRICE_RISE = 'price_rise'             # 价格异常上涨
    VOLUME_ZERO = 'volume_zero'          # 成交量为零
    DATA_MISSING = 'data_missing'         # 数据缺失
    SYSTEM_ERROR = 'system_error'         # 系统错误
    NETWORK_ERROR = 'network_error'      # 网络错误
    ORDER_FAIL = 'order_fail'            # 订单失败


class Anomaly:
    """异常类"""
    
    def __init__(self, anomaly_type: str, symbol: str, severity: str,
                 message: str, details: Optional[dict] = None):
        self.type = anomaly_type
        self.symbol = symbol
        self.severity = severity  # LOW, MEDIUM, HIGH, CRITICAL
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.resolved = False
        
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'type': self.type,
            'symbol': self.symbol,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'resolved': self.resolved
        }
        
    def resolve(self):
        """标记为已解决"""
        self.resolved = True


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化异常检测器
        
        Parameters:
        -----------
        config : dict
            配置参数
        """
        self.config = config or self._default_config()
        self.anomalies: List[Anomaly] = []
        self.price_history: Dict[str, List[float]] = {}
        self.volume_history: Dict[str, List[int]] = {}
        self.history_window = 30
        
    def _default_config(self) -> dict:
        """默认配置"""
        return {
            'price_spike_threshold': 0.05,      # 5% 价格波动阈值
            'volume_spike_threshold': 3.0,       # 3倍成交量阈值
            'price_drop_threshold': 0.03,        # 3% 下跌阈值
            'price_rise_threshold': 0.03,        # 3% 上涨阈值
            'consecutive_zero_volume': 3,         # 连续零成交量天数
            'severity': {
                AnomalyType.PRICE_SPIKE: 'HIGH',
                AnomalyType.VOLUME_SPIKE: 'MEDIUM',
                AnomalyType.PRICE_DROP: 'HIGH',
                AnomalyType.PRICE_RISE: 'MEDIUM',
                AnomalyType.VOLUME_ZERO: 'LOW',
                AnomalyType.DATA_MISSING: 'HIGH',
                AnomalyType.SYSTEM_ERROR: 'CRITICAL',
                AnomalyType.NETWORK_ERROR: 'HIGH',
                AnomalyType.ORDER_FAIL: 'MEDIUM',
            }
        }
        
    def update_data(self, symbol: str, price: float, volume: int, 
                   timestamp: Optional[datetime] = None):
        """更新数据"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
            
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        
        if len(self.price_history[symbol]) > self.history_window:
            self.price_history[symbol].pop(0)
        if len(self.volume_history[symbol]) > self.history_window:
            self.volume_history[symbol].pop(0)
            
    def detect_price_anomaly(self, symbol: str, current_price: float) -> Optional[Anomaly]:
        """检测价格异常"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 5:
            return None
            
        prices = self.price_history[symbol]
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        
        if std_price == 0:
            return None
            
        z_score = abs(current_price - mean_price) / std_price
        
        threshold = self.config['price_spike_threshold']
        
        if z_score > 3 or abs(current_price - mean_price) / mean_price > threshold:
            change_pct = (current_price - mean_price) / mean_price * 100
            
            if change_pct > 0:
                anomaly_type = AnomalyType.PRICE_RISE
                message = f"价格异常上涨: {symbol} 涨幅 {change_pct:.2f}%"
            else:
                anomaly_type = AnomalyType.PRICE_DROP
                message = f"价格异常下跌: {symbol} 跌幅 {abs(change_pct):.2f}%"
                
            severity = self.config['severity'].get(anomaly_type, 'HIGH')
            
            anomaly = Anomaly(
                anomaly_type=anomaly_type,
                symbol=symbol,
                severity=severity,
                message=message,
                details={
                    'current_price': current_price,
                    'mean_price': mean_price,
                    'std_price': std_price,
                    'z_score': z_score,
                    'change_pct': change_pct
                }
            )
            
            return anomaly
            
        return None
        
    def detect_volume_anomaly(self, symbol: str, current_volume: int) -> Optional[Anomaly]:
        """检测成交量异常"""
        if symbol not in self.volume_history or len(self.volume_history[symbol]) < 5:
            return None
            
        volumes = self.volume_history[symbol]
        mean_volume = np.mean(volumes)
        
        if mean_volume == 0:
            if current_volume == 0:
                return None
            else:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.VOLUME_SPIKE,
                    symbol=symbol,
                    severity='MEDIUM',
                    message=f"成交量异常: {symbol} 从0突增到 {current_volume}",
                    details={
                        'current_volume': current_volume,
                        'mean_volume': mean_volume
                    }
                )
                return anomaly
                
        ratio = current_volume / mean_volume
        
        if ratio > self.config['volume_spike_threshold']:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                symbol=symbol,
                severity='MEDIUM',
                message=f"成交量异常放大: {symbol} 是平均的 {ratio:.1f} 倍",
                details={
                    'current_volume': current_volume,
                    'mean_volume': mean_volume,
                    'ratio': ratio
                }
            )
            return anomaly
            
        if current_volume == 0 and ratio == 0:
            consecutive_zeros = sum(1 for v in self.volume_history[symbol][-self.config['consecutive_zero_volume']:] if v == 0)
            
            if consecutive_zeros >= self.config['consecutive_zero_volume']:
                anomaly = Anomaly(
                    anomaly_type=AnomalyType.VOLUME_ZERO,
                    symbol=symbol,
                    severity='LOW',
                    message=f"成交量持续为零: {symbol} 连续 {consecutive_zeros} 天",
                    details={
                        'current_volume': current_volume,
                        'consecutive_days': consecutive_zeros
                    }
                )
                return anomaly
                
        return None
        
    def check_data_quality(self, symbol: str, data: pd.DataFrame) -> List[Anomaly]:
        """检查数据质量"""
        anomalies = []
        
        if data is None or len(data) == 0:
            anomaly = Anomaly(
                anomaly_type=AnomalyType.DATA_MISSING,
                symbol=symbol,
                severity='HIGH',
                message=f"数据缺失: {symbol}",
                details={'data_length': 0}
            )
            anomalies.append(anomaly)
            return anomalies
            
        if data.isnull().any().any():
            missing_cols = data.columns[data.isnull().any()].tolist()
            anomaly = Anomaly(
                anomaly_type=AnomalyType.DATA_MISSING,
                symbol=symbol,
                severity='MEDIUM',
                message=f"数据存在缺失值: {symbol}, 列: {missing_cols}",
                details={'missing_columns': missing_cols}
            )
            anomalies.append(anomaly)
            
        if (data['close'] <= 0).any() or (data['volume'] < 0).any():
            anomaly = Anomaly(
                anomaly_type=AnomalyType.DATA_MISSING,
                symbol=symbol,
                severity='HIGH',
                message=f"数据存在异常值: {symbol}",
                details={'has_invalid': True}
            )
            anomalies.append(anomaly)
            
        return anomalies
        
    def detect(self, symbol: str, price: float, volume: int) -> List[Anomaly]:
        """
        检测异常
        
        Returns:
        --------
        List[Anomaly]
            检测到的异常列表
        """
        anomalies = []
        
        self.update_data(symbol, price, volume)
        
        price_anomaly = self.detect_price_anomaly(symbol, price)
        if price_anomaly:
            anomalies.append(price_anomaly)
            
        volume_anomaly = self.detect_volume_anomaly(symbol, volume)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
            
        return anomalies
        
    def record_anomaly(self, anomaly: Anomaly):
        """记录异常"""
        self.anomalies.append(anomaly)
        
    def get_anomalies(self, symbol: Optional[str] = None,
                      severity: Optional[str] = None,
                      unresolved_only: bool = False) -> List[Anomaly]:
        """获取异常列表"""
        filtered = self.anomalies
        
        if symbol:
            filtered = [a for a in filtered if a.symbol == symbol]
            
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
            
        if unresolved_only:
            filtered = [a for a in filtered if not a.resolved]
            
        return filtered
        
    def get_critical_anomalies(self) -> List[Anomaly]:
        """获取严重异常"""
        return self.get_anomalies(severity='CRITICAL', unresolved_only=True)
        
    def get_high_anomalies(self) -> List[Anomaly]:
        """获取高优先级异常"""
        return self.get_anomalies(severity='HIGH', unresolved_only=True)
        
    def resolve_anomaly(self, anomaly: Anomaly):
        """解决异常"""
        anomaly.resolve()
        
    def get_summary(self) -> dict:
        """获取异常摘要"""
        total = len(self.anomalies)
        unresolved = len([a for a in self.anomalies if not a.resolved])
        
        by_severity = {}
        for anomaly in self.anomalies:
            severity = anomaly.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
        by_type = {}
        for anomaly in self.anomalies:
            atype = anomaly.type
            by_type[atype] = by_type.get(atype, 0) + 1
            
        return {
            'total_anomalies': total,
            'unresolved_anomalies': unresolved,
            'by_severity': by_severity,
            'by_type': by_type
        }
        
    def should_block_trading(self) -> Tuple[bool, str]:
        """
        判断是否应该阻止交易
        
        Returns:
        --------
        Tuple[bool, str]
            (是否阻止, 原因)
        """
        critical = self.get_critical_anomalies()
        if critical:
            return True, f"存在 {len(critical)} 个严重异常"

        high_anomalies = self.get_high_anomalies()
        high_price_anomalies = [a for a in high_anomalies 
                                if a.type in [AnomalyType.PRICE_DROP, AnomalyType.PRICE_RISE]]
        
        if len(high_price_anomalies) >= 3:
            return True, f"存在 {len(high_price_anomalies)} 个价格异常"
            
        data_missing = [a for a in high_anomalies 
                       if a.type == AnomalyType.DATA_MISSING]
        if data_missing:
            return True, f"存在 {len(data_missing)} 个数据缺失"
            
        return False, "无异常"
