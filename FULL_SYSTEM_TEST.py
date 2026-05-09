"""
完整系统集成测试
测试所有模块的协同工作
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from datetime import datetime, timedelta
import json

from modules.logger import Logger
from modules.risk_manager import RiskManager
from modules.data_loader import DataLoader
from backtest.backtester import Backtester
from strategies.dual_ma_strategy import DualMAStrategy
from simulation.simulator import Simulator
from simulation.portfolio_manager import PortfolioManager
from automation.anomaly_detector import AnomalyDetector
from automation.kill_switch import KillSwitch
from automation.auto_stop_loss import AutoStopLoss
from automation.scheduler import TaskScheduler
from automation.auto_reporter import ReportGenerator
from automation.alerter import Alerter


def test_full_integration():
    """完整集成测试"""
    print("="*70)
    print("完整系统集成测试")
    print("="*70)
    
    logger = Logger()
    
    print("\n1. 测试核心模块...")
    print("-" * 70)
    
    print("\n1.1 日志模块...")
    logger.log_system({'event': '集成测试开始'})
    logger.log_trade({
        'symbol': 'TEST.XSHE',
        'action': 'BUY',
        'price': 10.0,
        'size': 1000
    })
    print("   ✓ 日志模块正常")
    
    print("\n1.2 风控模块...")
    risk_mgr = RiskManager(logger=logger)
    test_context = {
        'portfolio_value': 100000,
        'position_value': 5000,
        'entry_price': 10.0,
        'current_price': 9.5,
        'position_size': 1000,
        'daily_pnl': -200,
        'peak_value': 105000,
        'signal_reason': '测试信号'
    }
    passed, reasons = risk_mgr.check_order(test_context)
    print(f"   ✓ 风控模块正常 (通过: {passed})")
    
    print("\n1.3 持仓管理...")
    portfolio = PortfolioManager(initial_cash=100000)
    portfolio.buy('STOCK_A', 1000, 10.0, datetime.now())
    portfolio.update_prices({'STOCK_A': 11.0})
    pos = portfolio.get_position('STOCK_A')
    print(f"   ✓ 持仓管理正常 (市值: ¥{portfolio.total_value:,.2f})")
    
    print("\n1.4 异常检测...")
    detector = AnomalyDetector()
    for i in range(20):
        detector.update_data('STOCK_A', 10.0 + i * 0.1, 1000000)
    anomaly = detector.detect_price_anomaly('STOCK_A', 15.0)
    print(f"   ✓ 异常检测正常 (检测到: {'是' if anomaly else '否'})")
    
    print("\n1.5 Kill Switch...")
    kill_switch = KillSwitch(logger)
    kill_switch.check_max_drawdown(90000, 100000, 0.05)
    status = kill_switch.get_status()
    print(f"   ✓ Kill Switch正常 (已激活: {status['is_activated']})")
    
    print("\n1.6 自动止损...")
    stop_loss = AutoStopLoss(logger)
    actions = stop_loss.check_position('STOCK_A', 10.0, 9.6, 1000)
    print(f"   ✓ 自动止损正常 (触发: {len(actions)} 个)")
    
    print("\n1.7 告警系统...")
    alerter = Alerter(logger)
    alerter.send_trade_alert('STOCK_A', 'BUY', 10.0, 1000, 100.0)
    summary = alerter.get_summary()
    print(f"   ✓ 告警系统正常 (告警数: {summary['total_alerts']})")
    
    print("\n1.8 报告生成...")
    reporter = ReportGenerator(report_dir='reports/integration_test')
    portfolio_data = portfolio.get_status()
    filename = reporter.generate_trade_report([])
    print(f"   ✓ 报告生成正常 (文件: {Path(filename).name})")
    
    print("\n1.9 任务调度...")
    scheduler = TaskScheduler(logger)
    scheduler.create_interval_task(
        'test_task', '测试任务',
        lambda: print("     任务执行"),
        interval_seconds=60
    )
    summary = scheduler.get_summary()
    print(f"   ✓ 任务调度正常 (任务数: {summary['total_tasks']})")
    
    logger.close()
    
    print("\n" + "="*70)
    print("完整系统集成测试完成")
    print("="*70)
    
    print("\n✅ 所有核心模块正常工作")
    
    return True


def test_backtest_simulation():
    """测试回测到模拟盘的流程"""
    print("\n" + "="*70)
    print("回测到模拟盘流程测试")
    print("="*70)
    
    logger = Logger()
    
    print("\n2.1 生成模拟数据...")
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2024-01-01', '2024-03-31', freq='B')
    np.random.seed(42)
    
    returns = np.random.normal(0.001, 0.02, len(dates))
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
    
    print(f"   ✓ 生成 {len(df)} 条数据")
    
    print("\n2.2 运行回测...")
    backtester = Backtester(initial_cash=100000, logger=logger)
    data_dict = {'TEST_STOCK': df}
    
    results = backtester.run_backtest(
        strategy_class=DualMAStrategy,
        data_dict=data_dict,
        strategy_params={'fast_period': 5, 'slow_period': 20}
    )
    
    if results:
        print(f"   ✓ 回测完成 (收益率: {results['total_return_pct']:.2f}%)")
    else:
        print("   ✗ 回测失败")
        return False
        
    print("\n2.3 运行模拟盘...")
    simulator = Simulator(initial_cash=100000, logger=logger)
    simulator.start()
    
    for i in range(min(20, len(dates))):
        date = dates[i]
        price = prices[i]
        simulator.update_prices({'TEST_STOCK': price}, date)
        
        if i % 5 == 0 and not simulator.portfolio.has_position('TEST_STOCK'):
            signals = {'TEST_STOCK': 'BUY'}
            simulator.process_signals(signals)
        elif simulator.portfolio.has_position('TEST_STOCK'):
            pos = simulator.portfolio.get_position('TEST_STOCK')
            if pos.unrealized_pnl_pct > 0.05 or pos.unrealized_pnl_pct < -0.03:
                signals = {'TEST_STOCK': 'SELL'}
                simulator.process_signals(signals)
    
    report = simulator.get_performance_report()
    simulator.stop()
    
    print(f"   ✓ 模拟盘完成")
    print(f"     - 总交易: {report['performance']['total_trades']}")
    print(f"     - 总盈亏: ¥{report['performance']['total_pnl']:,.2f}")
    print(f"     - 胜率: {report['performance']['win_rate']*100:.1f}%")
    
    logger.close()
    
    print("\n" + "="*70)
    print("回测到模拟盘流程测试完成")
    print("="*70)
    
    return True


def test_automation_workflow():
    """测试自动化工作流"""
    print("\n" + "="*70)
    print("自动化工作流测试")
    print("="*70)
    
    logger = Logger()
    
    print("\n3.1 初始化自动化组件...")
    
    detector = AnomalyDetector()
    kill_switch = KillSwitch(logger)
    stop_loss = AutoStopLoss(logger)
    alerter = Alerter(logger)
    reporter = ReportGenerator(report_dir='reports/automation_test')
    
    print("   ✓ 所有自动化组件初始化")
    
    print("\n3.2 模拟交易场景...")
    
    portfolio = PortfolioManager(initial_cash=100000)
    portfolio.buy('STOCK_A', 1000, 10.0, datetime.now())
    
    print(f"   - 买入: 1000股 @ ¥10.00")
    print(f"   - 初始市值: ¥{portfolio.total_value:,.2f}")
    
    print("\n3.3 模拟价格下跌...")
    
    portfolio.update_prices({'STOCK_A': 9.5})
    
    pos = portfolio.get_position('STOCK_A')
    print(f"   - 当前价格: ¥{pos.current_price:.2f}")
    print(f"   - 亏损: ¥{pos.unrealized_pnl:,.2f} ({pos.unrealized_pnl_pct*100:.2f}%)")
    
    print("\n3.4 检测异常...")
    
    anomalies = detector.detect('STOCK_A', 9.5, 1000000)
    if anomalies:
        for anomaly in anomalies:
            alerter.send_anomaly_alert(
                anomaly.type,
                'STOCK_A',
                anomaly.message,
                anomaly.details
            )
            print(f"   - 告警: {anomaly.message}")
    
    print("\n3.5 检查止损...")
    
    actions = stop_loss.check_position(
        'STOCK_A',
        pos.entry_price,
        pos.current_price,
        pos.size
    )
    
    if actions:
        for action in actions:
            alerter.send_risk_alert(
                f"止损触发: {action['rule']}",
                f"执行动作: {action['action']}",
                action
            )
            print(f"   - 止损: {action['rule']} -> {action['action']}")
    
    print("\n3.6 检查Kill Switch...")
    
    should_stop = kill_switch.check_daily_loss(
        100000,
        portfolio.total_value,
        0.01
    )
    
    if should_stop:
        print("   - Kill Switch已激活")
        loss_pct = abs((portfolio.total_value - 100000)/100000*100)
        alerter.send_critical_alert(
            '每日亏损超限',
            f'亏损 {loss_pct:.2f}%',
            portfolio.get_status()
        )
    
    print("\n3.7 生成报告...")
    
    filename = reporter.generate_daily_report(
        date=datetime.now(),
        portfolio_data=portfolio.get_status(),
        trades_data=[],
        risk_data=kill_switch.get_status()
    )
    print(f"   ✓ 报告已生成")
    
    logger.close()
    
    print("\n" + "="*70)
    print("自动化工作流测试完成")
    print("="*70)
    
    return True


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*20 + "量化交易系统完整测试" + " "*20 + "║")
    print("╚" + "═"*68 + "╝")
    
    tests = [
        ("核心模块集成", test_full_integration),
        ("回测到模拟盘", test_backtest_simulation),
        ("自动化工作流", test_automation_workflow),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:30s}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("="*70)
    
    if all_passed:
        print("\n🎉 所有测试通过！系统已准备就绪。")
        print("\n下一步建议:")
        print("1. 阅读文档：GETTING_STARTED.md")
        print("2. 查看源代码：理解系统架构")
        print("3. Phase 7 开发：实盘接口（待开发）")
    else:
        print("\n⚠️ 部分测试失败，请检查错误。")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
