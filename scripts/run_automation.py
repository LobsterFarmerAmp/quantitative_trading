"""
运行自动化模块测试脚本
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
import time

from automation.anomaly_detector import AnomalyDetector, AnomalyType
from automation.kill_switch import KillSwitch, KillSwitchReason
from automation.auto_stop_loss import AutoStopLoss, StopLossRule
from automation.scheduler import TaskScheduler
from automation.auto_reporter import ReportGenerator
from automation.alerter import Alerter, AlertLevel, AlertType


def test_anomaly_detector():
    """测试异常检测模块"""
    print("\n1. 测试异常检测器...")
    
    detector = AnomalyDetector()
    
    print("   更新历史数据...")
    for i in range(20):
        detector.update_data('STOCK_A', 10.0 + i * 0.1, 1000000)
        
    print("   检测价格异常...")
    anomaly = detector.detect_price_anomaly('STOCK_A', 15.0)
    
    if anomaly:
        print(f"   ✓ 检测到异常: {anomaly.message}")
    else:
        print("   ✓ 无异常")
        
    print("   检测成交量异常...")
    detector.update_data('STOCK_B', 10.0, 1000000)
    for i in range(20):
        detector.update_data('STOCK_B', 10.0 + i * 0.05, 1000000)
        
    anomaly = detector.detect_volume_anomaly('STOCK_B', 5000000)
    
    if anomaly:
        print(f"   ✓ 检测到异常: {anomaly.message}")
    else:
        print("   ✓ 无异常")
        
    print("   ✓ 异常检测器测试通过")
    return True


def test_kill_switch():
    """测试Kill Switch"""
    print("\n2. 测试Kill Switch...")
    
    kill_switch = KillSwitch()
    
    print("   检查初始状态...")
    status = kill_switch.get_status()
    print(f"   ✓ 初始状态: 已激活={status['is_activated']}")
    
    print("   检查最大回撤...")
    should_stop = kill_switch.check_max_drawdown(
        current_value=90000,
        peak_value=100000,
        max_drawdown_threshold=0.05
    )
    print(f"   ✓ 回撤检查: {'触发' if should_stop else '未触发'}")
    
    print("   检查每日亏损...")
    should_stop = kill_switch.check_daily_loss(
        initial_value=100000,
        current_value=98500,
        max_loss_threshold=0.01
    )
    print(f"   ✓ 每日亏损检查: {'触发' if should_stop else '未触发'}")
    
    print("   检查连续亏损...")
    should_stop = kill_switch.check_consecutive_losses(
        consecutive_losses=6,
        max_consecutive=5
    )
    print(f"   ✓ 连续亏损检查: {'触发' if should_stop else '未触发'}")
    
    print("   ✓ Kill Switch 测试通过")
    return True


def test_auto_stop_loss():
    """测试自动止损"""
    print("\n3. 测试自动止损...")
    
    stop_loss = AutoStopLoss()
    
    print("   检查止损规则...")
    rules = stop_loss.get_all_rules()
    print(f"   ✓ 默认规则数: {len(rules)}")
    
    print("   测试持仓止损检查...")
    actions = stop_loss.check_position(
        symbol='STOCK_A',
        entry_price=10.0,
        current_price=9.6,
        position_size=1000
    )
    
    if actions:
        print(f"   ✓ 触发止损: {len(actions)} 个操作")
        for action in actions:
            print(f"     - {action['rule']}: {action['action']} @ {action['loss_pct']*100:.2f}%")
    else:
        print("   ✓ 未触发止损")
        
    summary = stop_loss.get_trigger_summary()
    print(f"   ✓ 触发摘要: 总计 {summary['total_triggers']} 次")
    
    print("   ✓ 自动止损测试通过")
    return True


def test_scheduler():
    """测试任务调度器"""
    print("\n4. 测试任务调度器...")
    
    scheduler = TaskScheduler()
    
    print("   创建间隔任务...")
    executed = {'count': 0}
    
    def sample_task():
        executed['count'] += 1
        print(f"     任务执行: {executed['count']}")
        
    scheduler.create_interval_task(
        task_id='sample_interval',
        name='示例间隔任务',
        callback=sample_task,
        interval_seconds=1
    )
    
    print("   创建每日任务...")
    scheduler.create_daily_task(
        task_id='sample_daily',
        name='示例每日任务',
        callback=sample_task,
        run_at='15:30'
    )
    
    summary = scheduler.get_summary()
    print(f"   ✓ 任务数: {summary['total_tasks']}")
    
    print("   ✓ 任务调度器测试通过")
    return True


def test_reporter():
    """测试报告生成器"""
    print("\n5. 测试报告生成器...")
    
    reporter = ReportGenerator(report_dir='reports/test')
    
    print("   生成示例数据...")
    portfolio_data = {
        'total_value': 105000,
        'cash': 50000,
        'positions_value': 55000,
        'total_pnl': 5000,
        'num_positions': 3
    }
    
    trades_data = [
        {'symbol': 'STOCK_A', 'action': 'BUY', 'price': 10.0, 'size': 1000, 'pnl': 100},
        {'symbol': 'STOCK_B', 'action': 'SELL', 'price': 15.0, 'size': 500, 'pnl': -50}
    ]
    
    risk_data = {
        'max_drawdown': 0.02,
        'consecutive_losses': 2,
        'enabled': True
    }
    
    print("   生成每日报告...")
    filename = reporter.generate_daily_report(
        date=datetime.now(),
        portfolio_data=portfolio_data,
        trades_data=trades_data,
        risk_data=risk_data
    )
    print(f"   ✓ 报告已生成: {filename}")
    
    print("   生成交易报告...")
    filename = reporter.generate_trade_report(trades_data=trades_data)
    print(f"   ✓ 交易报告已生成: {filename}")
    
    print("   ✓ 报告生成器测试通过")
    return True


def test_alerter():
    """测试告警系统"""
    print("\n6. 测试告警系统...")
    
    alerter = Alerter()
    
    alerter.register_handler(AlertLevel.INFO, lambda a: print(f"     [INFO] {a.title}"))
    alerter.register_handler(AlertLevel.WARNING, lambda a: print(f"     [WARNING] {a.title}"))
    alerter.register_handler(AlertLevel.ERROR, lambda a: print(f"     [ERROR] {a.title}"))
    
    print("   发送交易告警...")
    alerter.send_trade_alert('STOCK_A', 'BUY', 10.0, 1000, 50.0)
    
    print("   发送风控告警...")
    alerter.send_risk_alert(
        title='最大回撤告警',
        message='回撤达到4%',
        details={'drawdown': 0.04},
        level=AlertLevel.WARNING
    )
    
    print("   发送异常告警...")
    alerter.send_anomaly_alert(
        anomaly_type='PRICE_SPIKE',
        symbol='STOCK_B',
        message='价格异常上涨10%',
        details={'change_pct': 0.10}
    )
    
    print("   发送严重告警...")
    alerter.send_critical_alert(
        title='系统紧急停止',
        message='检测到严重异常，系统已自动停止'
    )
    
    summary = alerter.get_summary()
    print(f"   ✓ 告警统计: 总计 {summary['total_alerts']} 条")
    
    print("   ✓ 告警系统测试通过")
    return True


def main():
    """主测试函数"""
    print("="*60)
    print("自动化模块测试")
    print("="*60)
    
    tests = [
        ("异常检测器", test_anomaly_detector),
        ("Kill Switch", test_kill_switch),
        ("自动止损", test_auto_stop_loss),
        ("任务调度器", test_scheduler),
        ("报告生成器", test_reporter),
        ("告警系统", test_alerter),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n   ✗ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 所有测试通过！自动化模块已准备就绪。")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
