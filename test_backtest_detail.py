"""
详细的回测测试脚本
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
import backtrader as bt
from strategies.dual_ma_strategy import DualMAStrategy


def generate_mock_data():
    """生成模拟数据"""
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


def test_backtest():
    """测试回测"""
    print("开始测试回测...")
    
    df = generate_mock_data()
    print(f"数据形状: {df.shape}")
    print(f"数据列: {df.columns.tolist()}")
    print(f"数据前3行:")
    print(df.head(3))
    
    cerebro = bt.Cerebro()
    
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    
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
    
    cerebro.adddata(data_feed)
    
    cerebro.addstrategy(DualMAStrategy, fast_period=5, slow_period=20)
    
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)
    
    print(f"\n初始资金: {cerebro.broker.getcash():,.2f}")
    
    try:
        results = cerebro.run()
        print(f"回测完成!")
        
        final_value = cerebro.broker.getvalue()
        print(f"最终资金: {final_value:,.2f}")
        print(f"收益率: {(final_value - 100000) / 100000 * 100:.2f}%")
        
        if results and len(results) > 0:
            strategy = results[0]
            print(f"\n策略统计:")
            print(f"  交易次数: {len(strategy.trade_log)}")
            print(f"  信号次数: {len(strategy.signal_log)}")
            
            if hasattr(strategy, 'analyzers') and hasattr(strategy.analyzers, 'backtestanalyzer'):
                analysis = strategy.analyzers.backtestanalyzer.get_analysis()
                print(f"  分析器交易: {analysis.get('total_trades', 0)}")
        
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_backtest()
