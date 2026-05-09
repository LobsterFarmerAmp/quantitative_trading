"""
运行回测脚本
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from modules.data_loader import DataLoader
from backtest.backtester import Backtester
from strategies.dual_ma_strategy import DualMAStrategy
from modules.logger import Logger
import json


def run_simple_backtest():
    """运行简单回测示例"""
    print("="*60)
    print("双均线策略回测")
    print("="*60)
    
    logger = Logger()
    logger.log_system({'event': '开始回测'})
    
    data_loader = DataLoader(cache_dir='data')
    
    test_symbol = '000001.XSHE'
    print(f"\n准备数据: {test_symbol}")
    
    df = data_loader.get_stock_data(
        symbol=test_symbol,
        start_date='20230101',
        end_date='20231231',
        adjust='qfq'
    )
    
    if df is None:
        print("数据获取失败，尝试使用模拟数据...")
        df = generate_mock_data()
        
    valid, msg = data_loader.validate_data(df)
    print(f"数据验证: {msg}")
    
    if not valid:
        print("数据验证失败，使用模拟数据")
        df = generate_mock_data()
    
    data_dict = {test_symbol: df}
    
    backtester = Backtester(
        initial_cash=100000,
        logger=logger
    )
    
    strategy_params = {
        'fast_period': 5,
        'slow_period': 20,
        'printlog': False
    }
    
    print(f"\n策略参数: {strategy_params}")
    
    results = backtester.run_backtest(
        strategy_class=DualMAStrategy,
        data_dict=data_dict,
        strategy_params=strategy_params
    )
    
    if results:
        backtester.print_summary()
        
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)
        
        export_file = reports_dir / 'backtest_result.json'
        backtester.export_results(str(export_file))
        
        logger.log_system({
            'event': '回测完成',
            'total_return': results.get('total_return_pct', 0),
            'max_drawdown': results.get('max_drawdown_pct', 0)
        })
        
        print(f"\n回测结果已保存到: {export_file}")
    else:
        logger.log_error({'event': '回测失败'})
        
    logger.close()


def generate_mock_data():
    """生成模拟数据用于测试"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    print("生成模拟数据...")
    
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='B')
    
    np.random.seed(42)
    
    returns = np.random.normal(0.0005, 0.02, len(dates))
    prices = 10 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
        'high': prices * (1 + np.random.uniform(0, 0.02, len(dates))),
        'low': prices * (1 + np.random.uniform(-0.02, 0, len(dates))),
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, len(dates))
    })
    
    df.set_index('date', inplace=True)
    
    return df


def run_parameter_optimization():
    """运行参数优化"""
    print("="*60)
    print("双均线策略参数优化")
    print("="*60)
    
    logger = Logger()
    data_loader = DataLoader(cache_dir='data')
    
    test_symbol = '000001.XSHE'
    df = data_loader.get_stock_data(
        symbol=test_symbol,
        start_date='20220101',
        end_date='20231231'
    )
    
    if df is None:
        df = generate_mock_data()
    
    data_dict = {test_symbol: df}
    
    param_grid = {
        'fast_period': [3, 5, 10],
        'slow_period': [15, 20, 30]
    }
    
    results_list = []
    
    for fast in param_grid['fast_period']:
        for slow in param_grid['slow_period']:
            if fast >= slow:
                continue
                
            backtester = Backtester(initial_cash=100000, logger=logger)
            
            results = backtester.run_backtest(
                strategy_class=DualMAStrategy,
                data_dict=data_dict,
                strategy_params={'fast_period': fast, 'slow_period': slow}
            )
            
            if results:
                results_list.append({
                    'fast_period': fast,
                    'slow_period': slow,
                    'total_return': results.get('total_return_pct', 0),
                    'max_drawdown': results.get('max_drawdown_pct', 0),
                    'sharpe_ratio': results.get('sharpe_ratio', 0),
                    'win_rate': results.get('win_rate_pct', 0),
                    'total_trades': results.get('total_trades', 0)
                })
                
                print(f"\n快速期={fast}, 慢速期={slow}")
                print(f"  收益率: {results.get('total_return_pct', 0):.2f}%")
                print(f"  最大回撤: {results.get('max_drawdown_pct', 0):.2f}%")
                print(f"  夏普比率: {results.get('sharpe_ratio', 0):.2f}")
    
    if results_list:
        results_df = pd.DataFrame(results_list)
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)
        
        print("\n" + "="*60)
        print("参数优化结果（按夏普比率排序）")
        print("="*60)
        print(results_df.to_string(index=False))
        
        best_params = results_df.iloc[0]
        print(f"\n最优参数:")
        print(f"  快速期: {best_params['fast_period']}")
        print(f"  慢速期: {best_params['slow_period']}")
        print(f"  夏普比率: {best_params['sharpe_ratio']:.2f}")
        
        reports_dir = Path('reports')
        results_df.to_csv(reports_dir / 'parameter_optimization.csv', index=False)
        
    logger.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'optimize':
            run_parameter_optimization()
        else:
            run_simple_backtest()
    else:
        run_simple_backtest()
