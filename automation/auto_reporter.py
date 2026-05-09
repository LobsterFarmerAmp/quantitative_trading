"""
自动报告生成器
定期生成交易报告和风控报告
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import pandas as pd


class ReportType:
    """报告类型"""
    DAILY = 'daily'             # 每日报告
    WEEKLY = 'weekly'         # 每周报告
    MONTHLY = 'monthly'       # 每月报告
    TRADE = 'trade'          # 交易报告
    RISK = 'risk'            # 风控报告
    PERFORMANCE = 'performance'  # 绩效报告


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, report_dir: str = 'reports'):
        """
        初始化报告生成器
        
        Parameters:
        -----------
        report_dir : str
            报告目录
        """
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_dir = self.report_dir / 'daily'
        self.weekly_dir = self.report_dir / 'weekly'
        self.monthly_dir = self.report_dir / 'monthly'
        
        for dir_path in [self.daily_dir, self.weekly_dir, self.monthly_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def generate_daily_report(self, date: datetime, portfolio_data: dict,
                            trades_data: List[dict], risk_data: dict) -> str:
        """
        生成每日报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        date_str = date.strftime('%Y%m%d')
        filename = self.daily_dir / f'daily_report_{date_str}.json'
        
        report = {
            'report_type': ReportType.DAILY,
            'date': date_str,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': portfolio_data,
            'trades': trades_data,
            'risk': risk_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def generate_weekly_report(self, start_date: datetime, end_date: datetime,
                            portfolio_data: dict, trades_data: List[dict],
                            risk_data: dict, performance_data: dict) -> str:
        """
        生成每周报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        filename = self.weekly_dir / f'weekly_report_{start_str}_{end_str}.json'
        
        report = {
            'report_type': ReportType.WEEKLY,
            'period': f'{start_str} to {end_str}',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': portfolio_data,
            'trades': trades_data,
            'risk': risk_data,
            'performance': performance_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def generate_monthly_report(self, year: int, month: int,
                              portfolio_data: dict, trades_data: List[dict],
                              risk_data: dict, performance_data: dict) -> str:
        """
        生成每月报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        filename = self.monthly_dir / f'monthly_report_{year}{month:02d}.json'
        
        report = {
            'report_type': ReportType.MONTHLY,
            'period': f'{year}-{month:02d}',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': portfolio_data,
            'trades': trades_data,
            'risk': risk_data,
            'performance': performance_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def generate_trade_report(self, trades_data: List[dict]) -> str:
        """
        生成交易报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        filename = self.report_dir / f'trade_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        trades_df = pd.DataFrame(trades_data)
        
        report = {
            'report_type': ReportType.TRADE,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_trades': len(trades_data),
            'summary': {
                'total': len(trades_data),
                'wins': len(trades_df[trades_df.get('pnl', 0) > 0]) if trades_data else 0,
                'losses': len(trades_df[trades_df.get('pnl', 0) <= 0]) if trades_data else 0,
                'win_rate': 0,
                'total_pnl': float(trades_df['pnl'].sum()) if trades_data else 0,
                'avg_pnl': float(trades_df['pnl'].mean()) if trades_data else 0
            },
            'trades': trades_data
        }
        
        if trades_data:
            wins = trades_df[trades_df['pnl'] > 0]
            report['summary']['win_rate'] = len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def generate_risk_report(self, risk_data: dict, portfolio_data: dict) -> str:
        """
        生成风控报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        filename = self.report_dir / f'risk_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        report = {
            'report_type': ReportType.RISK,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': portfolio_data,
            'risk': risk_data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def generate_performance_report(self, trades_data: List[dict],
                                   portfolio_data: dict) -> str:
        """
        生成绩效报告
        
        Returns:
        --------
        str
            报告文件路径
        """
        filename = self.report_dir / f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        trades_df = pd.DataFrame(trades_data) if trades_data else pd.DataFrame()
        
        report = {
            'report_type': ReportType.PERFORMANCE,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio': portfolio_data,
            'performance': {}
        }
        
        if not trades_df.empty:
            wins = trades_df[trades_df['pnl'] > 0]['pnl'] if 'pnl' in trades_df.columns else pd.Series()
            losses = trades_df[trades_df['pnl'] <= 0]['pnl'] if 'pnl' in trades_df.columns else pd.Series()
            
            report['performance'] = {
                'total_trades': len(trades_df),
                'win_trades': len(wins),
                'lose_trades': len(losses),
                'win_rate': len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
                'avg_win': float(wins.mean()) if len(wins) > 0 else 0,
                'avg_loss': float(losses.mean()) if len(losses) > 0 else 0,
                'profit_factor': abs(wins.sum() / losses.sum()) if len(losses) > 0 and losses.sum() != 0 else 0,
                'total_pnl': float(trades_df['pnl'].sum()) if 'pnl' in trades_df.columns else 0
            }
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
        return str(filename)
        
    def get_recent_reports(self, report_type: Optional[str] = None, limit: int = 10) -> List[dict]:
        """获取最近的报告"""
        import os
        
        reports = []
        
        if report_type == ReportType.DAILY or report_type is None:
            reports.extend(self.daily_dir.glob('daily_report_*.json'))
            
        if report_type == ReportType.WEEKLY or report_type is None:
            reports.extend(self.weekly_dir.glob('weekly_report_*.json'))
            
        if report_type == ReportType.MONTHLY or report_type is None:
            reports.extend(self.monthly_dir.glob('monthly_report_*.json'))
            
        if report_type in [ReportType.TRADE, ReportType.RISK, ReportType.PERFORMANCE] or report_type is None:
            reports.extend(self.report_dir.glob(f'{report_type}_report_*.json'))
            
        reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        result = []
        for report_file in reports[:limit]:
            result.append({
                'filename': report_file.name,
                'path': str(report_file),
                'modified_time': datetime.fromtimestamp(report_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return result
