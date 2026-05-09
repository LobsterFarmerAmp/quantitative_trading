"""
日志模块
记录所有交易、风控、系统行为
"""

import os
import json
from datetime import datetime
from pathlib import Path
from enum import Enum


class LogType(Enum):
    """日志类型"""
    TRADE = 'trades'
    RISK = 'risk'
    SYSTEM = 'system'
    ERROR = 'error'
    SIGNAL = 'signal'


class Logger:
    """日志管理器"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_files = {}
        for log_type in LogType:
            log_file = self.log_dir / f"{log_type.value}.log"
            self.log_files[log_type] = log_file
            
        self.log_buffer = {log_type: [] for log_type in LogType}
        self.buffer_size = 100
        
    def log(self, log_type, message, data=None):
        """
        记录日志
        
        Parameters:
        -----------
        log_type : LogType
            日志类型
        message : str
            日志消息
        data : dict, optional
            附加数据
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            'timestamp': timestamp,
            'type': log_type.value,
            'message': message,
            'data': data
        }
        
        log_line = json.dumps(log_entry, ensure_ascii=False, default=str)
        
        print(f"[{log_type.value.upper()}] {timestamp} - {message}")
        
        self.log_buffer[log_type].append(log_line)
        
        if len(self.log_buffer[log_type]) >= self.buffer_size:
            self._flush_log(log_type)
            
    def _flush_log(self, log_type):
        """刷新日志到文件"""
        if self.log_buffer[log_type]:
            with open(self.log_files[log_type], 'a', encoding='utf-8') as f:
                for line in self.log_buffer[log_type]:
                    f.write(line + '\n')
            self.log_buffer[log_type] = []
            
    def log_trade(self, trade_info):
        """记录交易"""
        self.log(LogType.TRADE, f"交易执行", trade_info)
        
    def log_signal(self, signal_info):
        """记录信号"""
        self.log(LogType.SIGNAL, f"交易信号", signal_info)
        
    def log_risk(self, risk_info):
        """记录风控"""
        self.log(LogType.RISK, f"风控事件", risk_info)
        
    def log_system(self, system_info):
        """记录系统事件"""
        self.log(LogType.SYSTEM, f"系统事件", system_info)
        
    def log_error(self, error_info):
        """记录错误"""
        self.log(LogType.ERROR, f"错误发生", error_info)
        
    def flush_all(self):
        """刷新所有日志到文件"""
        for log_type in LogType:
            self._flush_log(log_type)
            
    def get_recent_logs(self, log_type, n=100):
        """获取最近的日志"""
        log_file = self.log_files[log_type]
        if not log_file.exists():
            return []
            
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        return [json.loads(line) for line in lines[-n:]]
        
    def get_trades_summary(self):
        """获取交易摘要"""
        trades = self.get_recent_logs(LogType.TRADE, n=10000)
        
        if not trades:
            return {
                'total_trades': 0,
                'win_trades': 0,
                'lose_trades': 0,
                'total_pnl': 0,
                'win_rate': 0
            }
            
        total = len(trades)
        wins = sum(1 for t in trades if t.get('data', {}).get('pnl', 0) > 0)
        loses = total - wins
        total_pnl = sum(t.get('data', {}).get('pnl', 0) for t in trades)
        
        return {
            'total_trades': total,
            'win_trades': wins,
            'lose_trades': loses,
            'total_pnl': total_pnl,
            'win_rate': wins / total if total > 0 else 0
        }
        
    def close(self):
        """关闭日志系统"""
        self.flush_all()
        

class TradeLogger:
    """交易专用日志"""
    
    def __init__(self, log_dir='logs/trades'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.trade_log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
        
        if not self.trade_log_file.exists():
            with open(self.trade_log_file, 'w', encoding='utf-8') as f:
                f.write('timestamp,date,symbol,action,price,size,amount,commission,pnl,reason\n')
                
    def log_trade(self, trade_data):
        """记录交易到CSV"""
        with open(self.trade_log_file, 'a', encoding='utf-8') as f:
            line = (
                f"{trade_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))},"
                f"{trade_data.get('date', '')},"
                f"{trade_data.get('symbol', '')},"
                f"{trade_data.get('action', '')},"
                f"{trade_data.get('price', 0)},"
                f"{trade_data.get('size', 0)},"
                f"{trade_data.get('amount', 0)},"
                f"{trade_data.get('commission', 0)},"
                f"{trade_data.get('pnl', 0)},"
                f"{trade_data.get('reason', '')}\n"
            )
            f.write(line)


if __name__ == '__main__':
    logger = Logger()
    
    logger.log_trade({
        'symbol': '000001.XSHE',
        'action': 'BUY',
        'price': 10.5,
        'size': 1000,
        'amount': 10500,
        'commission': 3.15
    })
    
    logger.log_signal({
        'symbol': '000001.XSHE',
        'signal': 'BUY',
        'reason': '均线金叉'
    })
    
    logger.log_risk({
        'event': '下单检查通过',
        '单笔风险': '0.3%',
        '当前仓位': '10%'
    })
    
    logger.flush_all()
    
    print("\n交易摘要:")
    print(logger.get_trades_summary())
