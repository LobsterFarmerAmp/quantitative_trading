"""
回测引擎
使用Backtrader进行策略回测
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from modules.logger import Logger, TradeLogger
from modules.risk_manager import RiskManager
from config import BROKER_PARAMS, RISK_PARAMS


class BacktestAnalyzer(bt.Analyzer):
    """回测结果分析器"""
    
    def __init__(self):
        self.trades = []
        self.returns = []
        self.portfolio_values = []
        
    def notify_trade(self, trade):
        if trade.isclosed:
            price_out = trade.price
            if trade.size > 0 and trade.price > 0:
                price_out = trade.price * (1 + trade.pnl / trade.size / trade.price)
                
            self.trades.append({
                'date_in': bt.num2date(trade.dtopen).strftime('%Y-%m-%d'),
                'date_out': bt.num2date(trade.dtclose).strftime('%Y-%m-%d'),
                'pnl': trade.pnl,
                'pnl_net': trade.pnlcomm,
                'size': trade.size,
                'price_in': trade.price,
                'price_out': price_out
            })
            
    def stop(self):
        self.portfolio_values = [self.strategy.broker.getvalue()]
        
    def get_analysis(self):
        return {
            'total_trades': len(self.trades),
            'trades': self.trades,
            'portfolio_values': self.portfolio_values
        }


class Backtester:
    """回测引擎"""
    
    def __init__(self, initial_cash=None, commission=None, logger=None):
        self.initial_cash = initial_cash or BROKER_PARAMS['初始资金']
        self.commission = commission or BROKER_PARAMS['佣金比例']
        self.logger = logger or Logger()
        self.results = None
        
    def run_backtest(self, strategy_class, data_dict, strategy_params=None, 
                     start_date=None, end_date=None):
        """
        运行回测
        
        Parameters:
        -----------
        strategy_class : class
            策略类
        data_dict : dict
            symbol -> DataFrame 的字典
        strategy_params : dict
            策略参数
        start_date : str
            开始日期
        end_date : str
            结束日期
            
        Returns:
        --------
        dict
            回测结果
        """
        cerebro = bt.Cerebro()
        
        cerebro.broker.setcash(self.initial_cash)
        
        commission_info = self.commission
        cerebro.broker.setcommission(commission=commission_info)
        
        for symbol, df in data_dict.items():
            if df is None or len(df) == 0:
                self.logger.log_error({
                    'event': '数据为空',
                    'symbol': symbol
                })
                continue
                
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime=None,
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            
            data_feed._name = symbol
            cerebro.adddata(data_feed)
            
        strategy_params = strategy_params or {}
        cerebro.addstrategy(strategy_class, **strategy_params)
        
        cerebro.addanalyzer(BacktestAnalyzer)
        
        cerebro.addsizer(bt.sizers.FixedSize, stake=100)
        
        try:
            results = cerebro.run()
            
            if results and len(results) > 0:
                strategy = results[0]
                
                trades = getattr(strategy, 'trade_log', [])
                
                final_value = cerebro.broker.getvalue()
                total_return = (final_value - self.initial_cash) / self.initial_cash
                
                self.results = {
                    'initial_cash': self.initial_cash,
                    'final_value': final_value,
                    'total_return': total_return,
                    'total_return_pct': total_return * 100,
                    'total_trades': len(trades),
                    'trades': trades,
                    'portfolio_history': [],
                    'strategy_class': strategy_class.__name__,
                    'strategy_params': strategy_params
                }
                
                self._calculate_metrics()
                
                return self.results
            else:
                self.logger.log_error({'event': '回测无结果'})
                return None
                
        except Exception as e:
            self.logger.log_error({
                'event': '回测失败',
                'error': str(e)
            })
            import traceback
            traceback.print_exc()
            return None
            
    def _calculate_metrics(self):
        """计算性能指标"""
        if not self.results:
            return
            
        trades = self.results.get('trades', [])
        
        if len(trades) == 0:
            self.results.update({
                'win_rate': 0,
                'win_rate_pct': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'annual_return': 0,
                'annual_return_pct': 0
            })
            return
            
        wins = [t['pnlcomm'] for t in trades if t.get('pnlcomm', 0) > 0]
        losses = [t['pnlcomm'] for t in trades if t.get('pnlcomm', 0) <= 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        portfolio_values = [self.results['initial_cash']]
        for i in range(len(trades)):
            cumulative = self.initial_cash + sum(t.get('pnlcomm', 0) for t in trades[:i+1])
            portfolio_values.append(cumulative)
        
        peak = portfolio_values[0]
        max_drawdown = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                
        returns_list = []
        for i in range(1, len(portfolio_values)):
            if portfolio_values[i-1] > 0:
                ret = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
                returns_list.append(ret)
                
        sharpe_ratio = 0
        if len(returns_list) > 0 and np.std(returns_list) > 0:
            sharpe_ratio = np.mean(returns_list) / np.std(returns_list) * np.sqrt(252)
            
        days = 365
        annual_return = self.results['total_return'] * 365 / days if days > 0 else 0
        
        self.results.update({
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'annual_return': annual_return,
            'annual_return_pct': annual_return * 100
        })
        
    def print_summary(self):
        """打印回测摘要"""
        if not self.results:
            print("没有回测结果")
            return
            
        print("\n" + "="*60)
        print("回测结果摘要")
        print("="*60)
        print(f"策略: {self.results['strategy_class']}")
        print(f"参数: {self.results.get('strategy_params', {})}")
        print("-"*60)
        print(f"初始资金: {self.results['initial_cash']:,.2f}")
        print(f"最终市值: {self.results['final_value']:,.2f}")
        print(f"总收益率: {self.results['total_return_pct']:.2f}%")
        print("-"*60)
        print(f"总交易次数: {self.results['total_trades']}")
        print(f"胜率: {self.results.get('win_rate_pct', 0):.2f}%")
        print(f"平均盈利: {self.results.get('avg_win', 0):,.2f}")
        print(f"平均亏损: {self.results.get('avg_loss', 0):,.2f}")
        print(f"盈亏比: {self.results.get('profit_factor', 0):.2f}")
        print("-"*60)
        print(f"最大回撤: {self.results.get('max_drawdown_pct', 0):.2f}%")
        print(f"夏普比率: {self.results.get('sharpe_ratio', 0):.2f}")
        print(f"年化收益率: {self.results.get('annual_return_pct', 0):.2f}%")
        print("="*60)
        
    def export_results(self, filename):
        """导出回测结果"""
        if not self.results:
            return
            
        import json
        
        export_data = self.results.copy()
        export_data.pop('trades', None)
        export_data.pop('portfolio_history', None)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
        self.logger.log_system({
            'event': '回测结果已导出',
            'filename': filename
        })


if __name__ == '__main__':
    print("回测引擎模块")
