"""
量化交易系统主入口
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from modules.logger import Logger, TradeLogger
from modules.risk_manager import RiskManager
from modules.data_loader import DataLoader
from backtest.backtester import Backtester
from strategies.dual_ma_strategy import DualMAStrategy
from config import RISK_PARAMS, BROKER_PARAMS


class QuantitativeTradingSystem:
    """量化交易系统主类"""
    
    def __init__(self, mode='backtest'):
        """
        初始化交易系统
        
        Parameters:
        -----------
        mode : str
            运行模式：'backtest' 回测, 'simulation' 模拟, 'live' 实盘
        """
        self.mode = mode
        self.logger = Logger()
        self.trade_logger = TradeLogger()
        self.risk_manager = RiskManager(logger=self.logger)
        self.data_loader = DataLoader()
        self.backtester = None
        
        self.logger.log_system({
            'event': '系统启动',
            'mode': mode,
            'risk_params': RISK_PARAMS,
            'broker_params': BROKER_PARAMS
        })
        
    def run_backtest(self, strategy_class, symbols, start_date, end_date, 
                     strategy_params=None):
        """
        运行回测
        
        Parameters:
        -----------
        strategy_class : class
            策略类
        symbols : list
            股票代码列表
        start_date : str
            开始日期
        end_date : str
            结束日期
        strategy_params : dict
            策略参数
        """
        self.logger.log_system({
            'event': '开始回测',
            'strategy': strategy_class.__name__,
            'symbols': symbols,
            'period': f'{start_date} - {end_date}'
        })
        
        self.backtester = Backtester(
            initial_cash=BROKER_PARAMS['初始资金'],
            logger=self.logger
        )
        
        data_dict = {}
        for symbol in symbols:
            df = self.data_loader.get_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            if df is not None:
                data_dict[symbol] = df
                
        if not data_dict:
            self.logger.log_error({'event': '无有效数据'})
            return None
            
        results = self.backtester.run_backtest(
            strategy_class=strategy_class,
            data_dict=data_dict,
            strategy_params=strategy_params
        )
        
        if results:
            self.backtester.print_summary()
            
            for trade in results.get('trades', []):
                self.trade_logger.log_trade({
                    'date': trade.get('date_out'),
                    'symbol': symbols[0],
                    'action': 'CLOSE',
                    'price': trade.get('price_out', 0),
                    'size': trade.get('size', 0),
                    'pnl': trade.get('pnl_net', 0),
                    'reason': '策略信号'
                })
                
        return results
        
    def get_system_status(self):
        """获取系统状态"""
        return {
            'mode': self.mode,
            'risk_status': self.risk_manager.get_status(),
            'broker_status': BROKER_PARAMS
        }
        
    def shutdown(self):
        """关闭系统"""
        self.logger.log_system({'event': '系统关闭'})
        self.logger.close()


def main():
    """主函数"""
    print("="*60)
    print("量化交易系统 v1.0")
    print("="*60)
    print("\n模式选择:")
    print("1. 回测模式 (backtest)")
    print("2. 模拟交易 (simulation)")
    print("3. 实盘交易 (live) - 待开发")
    
    mode = input("\n请选择模式 [1]: ").strip()
    
    if mode == '2':
        mode = 'simulation'
    elif mode == '3':
        print("实盘模式正在开发中...")
        mode = 'backtest'
    else:
        mode = 'backtest'
        
    system = QuantitativeTradingSystem(mode=mode)
    
    print(f"\n系统启动: {mode} 模式")
    print("\n系统状态:")
    status = system.get_system_status()
    print(f"  风控状态: {'已启用' if status['risk_status']['enabled'] else '已禁用'}")
    print(f"  连续亏损次数: {status['risk_status']['consecutive_losses']}")
    print(f"  初始资金: {status['broker_status']['初始资金']:,.2f}")
    
    if mode == 'backtest':
        print("\n运行示例回测...")
        
        results = system.run_backtest(
            strategy_class=DualMAStrategy,
            symbols=['000001.XSHE'],
            start_date='20230101',
            end_date='20231231',
            strategy_params={
                'fast_period': 5,
                'slow_period': 20
            }
        )
        
        if results:
            print("\n回测完成!")
        else:
            print("\n回测失败!")
            
    system.shutdown()
    
    print("\n系统已关闭。")


if __name__ == '__main__':
    main()
