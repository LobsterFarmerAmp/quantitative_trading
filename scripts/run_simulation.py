"""
运行模拟交易脚本
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from simulation.simulator import Simulator
from simulation.portfolio_manager import PortfolioManager
from simulation.order_manager import OrderManager
from modules.logger import Logger


def generate_mock_trading_data(symbols, start_date, end_date):
    """生成模拟交易数据"""
    dates = pd.date_range(start_date, end_date, freq='B')
    data_dict = {}
    
    for symbol in symbols:
        np.random.seed(hash(symbol) % 2**32)
        
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = 10 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'date': dates,
            'symbol': symbol,
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        
        data_dict[symbol] = df
        
    return data_dict


def run_simulation_demo():
    """运行模拟交易演示"""
    print("="*60)
    print("模拟交易演示")
    print("="*60)
    
    logger = Logger()
    logger.log_system({'event': '开始模拟交易演示'})
    
    symbols = ['STOCK_A', 'STOCK_B', 'STOCK_C']
    start_date = '2024-01-01'
    end_date = '2024-03-31'
    
    print(f"\n生成模拟数据: {symbols}")
    data_dict = generate_mock_trading_data(symbols, start_date, end_date)
    
    for symbol, df in data_dict.items():
        print(f"  {symbol}: {len(df)} 条数据")
    
    simulator = Simulator(
        initial_cash=100000,
        logger=logger
    )
    
    simulator.start()
    
    print(f"\n初始资金: ¥{simulator.initial_cash:,.2f}")
    
    all_dates = sorted(set().union(*[set(df['date']) for df in data_dict.values()]))
    
    trading_days = [d for d in all_dates if d.weekday() < 5][:50]
    
    print(f"\n开始模拟 {len(trading_days)} 个交易日...")
    
    signals = {}
    
    for i, date in enumerate(trading_days):
        prices = {}
        for symbol in symbols:
            df = data_dict[symbol]
            row = df[df['date'] == date]
            if not row.empty:
                prices[symbol] = row['close'].values[0]
                
        simulator.update_prices(prices, date)
        
        signals = {}
        for symbol in symbols:
            if symbol not in simulator.portfolio.positions:
                if i % 10 == 0:
                    signals[symbol] = 'BUY'
            else:
                pos = simulator.portfolio.get_position(symbol)
                if pos.unrealized_pnl_pct > 0.05 or pos.unrealized_pnl_pct < -0.03:
                    signals[symbol] = 'SELL'
                    
        if signals:
            results = simulator.process_signals(signals)
            
        if (i + 1) % 10 == 0:
            status = simulator.get_status()
            print(f"\n第 {i+1} 天 ({date.strftime('%Y-%m-%d')})")
            print(f"  市值: ¥{status['portfolio']['total_value']:,.2f}")
            print(f"  盈亏: ¥{status['portfolio']['total_pnl']:,.2f} ({status['portfolio']['total_pnl_pct']:.2f}%)")
            print(f"  持仓: {status['portfolio']['num_positions']} 个")
            
    simulator.stop()
    
    print("\n" + "="*60)
    print("模拟交易完成")
    print("="*60)
    
    report = simulator.get_performance_report()
    
    print(f"\n性能报告:")
    print(f"  总交易次数: {report['performance']['total_trades']}")
    print(f"  盈利次数: {report['performance']['win_trades']}")
    print(f"  亏损次数: {report['performance']['lose_trades']}")
    print(f"  胜率: {report['performance']['win_rate']*100:.2f}%")
    print(f"  总盈亏: ¥{report['performance']['total_pnl']:,.2f}")
    
    print(f"\n持仓状态:")
    print(f"  持仓数: {len(report['positions'])}")
    for pos in report['positions']:
        print(f"    {pos['symbol']}: {pos['size']}股, "
              f"成本¥{pos['entry_price']:.2f}, "
              f"现价¥{pos['current_price']:.2f}, "
              f"盈亏¥{pos['unrealized_pnl']:.2f}")
    
    print("\n" + "="*60)
    print("系统状态")
    print("="*60)
    print(f"  风控状态: {'启用' if simulator.risk_manager.enabled else '禁用'}")
    print(f"  连续亏损: {simulator.risk_manager.rules['consecutive_loss'].consecutive_losses}")
    
    logger.log_system({
        'event': '模拟交易完成',
        'total_trades': report['performance']['total_trades'],
        'total_pnl': report['performance']['total_pnl']
    })
    
    logger.close()
    
    return report


def test_portfolio_manager():
    """测试持仓管理器"""
    print("\n测试持仓管理器...")
    
    portfolio = PortfolioManager(initial_cash=100000)
    
    print(f"初始资金: ¥{portfolio.cash:,.2f}")
    
    print("\n买入100股，价格¥10")
    portfolio.buy('STOCK_A', 100, 10.0, datetime.now())
    print(f"现金: ¥{portfolio.cash:,.2f}")
    print(f"持仓市值: ¥{portfolio.get_position('STOCK_A').market_value:,.2f}")
    print(f"未实现盈亏: ¥{portfolio.get_position('STOCK_A').unrealized_pnl:,.2f}")
    
    print("\n更新价格到¥11")
    portfolio.update_prices({'STOCK_A': 11.0})
    print(f"持仓市值: ¥{portfolio.get_position('STOCK_A').market_value:,.2f}")
    print(f"未实现盈亏: ¥{portfolio.get_position('STOCK_A').unrealized_pnl:,.2f}")
    
    print("\n卖出50股，价格¥11")
    result = portfolio.sell('STOCK_A', 50, 11.0, datetime.now())
    print(f"卖出结果: 盈利¥{result['pnl']:.2f}")
    print(f"现金: ¥{portfolio.cash:,.2f}")
    
    print("\n持仓摘要:")
    summary = portfolio.get_positions_summary()
    for pos in summary:
        print(f"  {pos}")
    
    print("\n性能指标:")
    metrics = portfolio.get_performance_metrics()
    print(f"  总交易: {metrics['total_trades']}")
    print(f"  胜率: {metrics['win_rate']*100:.2f}%")
    
    return True


def test_order_manager():
    """测试订单管理器"""
    print("\n测试订单管理器...")
    
    order_mgr = OrderManager()
    
    order1 = order_mgr.buy_market('STOCK_A', 100)
    print(f"创建市价买入单: {order1.order_id}")
    
    order2 = order_mgr.sell_limit('STOCK_B', 200, 15.0)
    print(f"创建限价卖出单: {order2.order_id}")
    
    print(f"\n待成交订单: {len(order_mgr.pending_orders)}")
    
    print("\n成交订单1")
    order_mgr.fill_order(order1, 10.0, datetime.now())
    print(f"订单状态: {order1.status.value}")
    
    print("\n取消订单2")
    order_mgr.cancel_order(order2, '手动取消')
    print(f"订单状态: {order2.status.value}")
    
    print("\n统计信息:")
    stats = order_mgr.get_statistics()
    print(f"  总订单: {stats['total_orders']}")
    print(f"  已成交: {stats['filled_orders']}")
    print(f"  已取消: {stats['cancelled_orders']}")
    
    return True


if __name__ == '__main__':
    print("="*60)
    print("模拟交易系统测试")
    print("="*60)
    
    print("\n1. 测试持仓管理器")
    test_portfolio_manager()
    
    print("\n" + "="*60)
    
    print("\n2. 测试订单管理器")
    test_order_manager()
    
    print("\n" + "="*60)
    
    print("\n3. 运行模拟交易演示")
    run_simulation_demo()
    
    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)
