"""
定时任务调度器
定时执行交易任务和报告生成
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import threading
import time


class TaskType:
    """任务类型"""
    ONCE = 'once'               # 执行一次
    INTERVAL = 'interval'       # 间隔执行
    DAILY = 'daily'           # 每日执行
    WEEKLY = 'weekly'         # 每周执行


class Task:
    """任务类"""
    
    def __init__(self, task_id: str, name: str, task_type: str,
                 callback: Callable, interval_seconds: int = 0,
                 run_at: Optional[str] = None,  # HH:MM 格式
                 enabled: bool = True):
        """
        初始化任务
        
        Parameters:
        -----------
        task_id : str
            任务ID
        name : str
            任务名称
        task_type : TaskType
            任务类型
        callback : Callable
            回调函数
        interval_seconds : int
            间隔秒数（用于 INTERVAL 类型）
        run_at : str
            执行时间（用于 DAILY/WEEKLY 类型）
        enabled : bool
            是否启用
        """
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.callback = callback
        self.interval_seconds = interval_seconds
        self.run_at = run_at
        self.enabled = enabled
        
        self.last_run_time = None
        self.next_run_time = None
        self.run_count = 0
        self.error_count = 0
        self.last_error = None
        
    def should_run(self, current_time: datetime) -> bool:
        """判断是否应该执行"""
        if not self.enabled:
            return False
            
        if self.task_type == TaskType.ONCE:
            if self.last_run_time is not None:
                return False
            return True
            
        elif self.task_type == TaskType.INTERVAL:
            if self.last_run_time is None:
                return True
            elapsed = (current_time - self.last_run_time).total_seconds()
            return elapsed >= self.interval_seconds
            
        elif self.task_type == TaskType.DAILY:
            if self.run_at is None:
                return False
            if self.last_run_time is not None:
                last_run_date = self.last_run_time.date()
                if last_run_date == current_time.date():
                    return False
            target_hour, target_minute = map(int, self.run_at.split(':'))
            return (current_time.hour == target_hour and 
                   current_time.minute == target_minute)
           
        elif self.task_type == TaskType.WEEKLY:
            if self.run_at is None:
                return False
            if self.last_run_time is not None:
                days_since = (current_time.date() - self.last_run_time.date()).days
                if days_since < 7:
                    return False
            target_hour, target_minute = map(int, self.run_at.split(':'))
            return (current_time.weekday() == 0 and  # 周一
                   current_time.hour == target_hour and
                   current_time.minute == target_minute)
           
        return False
        
    def execute(self) -> bool:
        """执行任务"""
        try:
            self.callback()
            self.last_run_time = datetime.now()
            self.run_count += 1
            return True
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            return False
            
    def get_info(self) -> dict:
        """获取任务信息"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'type': self.task_type,
            'enabled': self.enabled,
            'last_run_time': self.last_run_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_run_time else None,
            'next_run_time': self.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if self.next_run_time else None,
            'run_count': self.run_count,
            'error_count': self.error_count,
            'last_error': self.last_error
        }


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, logger=None):
        """
        初始化调度器
        
        Parameters:
        -----------
        logger : Logger, optional
            日志管理器
        """
        self.logger = logger
        self.tasks: Dict[str, Task] = {}
        self.is_running = False
        self.thread = None
        self.check_interval = 60  # 每分钟检查一次
        
        self._log('任务调度器初始化')
        
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        if self.logger:
            self.logger.log_system({
                'event': 'TaskScheduler',
                'level': level,
                'message': message
            })
        else:
            print(f"[TaskScheduler][{level}] {message}")
            
    def add_task(self, task: Task) -> bool:
        """添加任务"""
        if task.task_id in self.tasks:
            self._log(f'任务ID已存在: {task.task_id}', 'WARNING')
            return False
            
        self.tasks[task.task_id] = task
        self._log(f'添加任务: {task.name} ({task.task_id})')
        return True
        
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks.pop(task_id)
        self._log(f'移除任务: {task.name} ({task_id})')
        return True
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
        
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        task = self.get_task(task_id)
        if task:
            task.enabled = True
            self._log(f'启用任务: {task.name}')
            return True
        return False
        
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        task = self.get_task(task_id)
        if task:
            task.enabled = False
            self._log(f'禁用任务: {task.name}')
            return True
        return False
        
    def _run_loop(self):
        """运行循环"""
        while self.is_running:
            current_time = datetime.now()
            
            for task_id, task in self.tasks.items():
                if task.should_run(current_time):
                    self._log(f'执行任务: {task.name}')
                    
                    success = task.execute()
                    
                    if success:
                        self._log(f'任务执行成功: {task.name}')
                    else:
                        self._log(f'任务执行失败: {task.name}, 错误: {task.last_error}', 'ERROR')
                        
            time.sleep(self.check_interval)
            
    def start(self):
        """启动调度器"""
        if self.is_running:
            self._log('调度器已在运行', 'WARNING')
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._log('任务调度器已启动')
        
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            self._log('调度器未运行', 'WARNING')
            return
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        self._log('任务调度器已停止')
        
    def run_now(self, task_id: str) -> bool:
        """立即执行任务"""
        task = self.get_task(task_id)
        if not task:
            self._log(f'任务不存在: {task_id}', 'ERROR')
            return False
            
        self._log(f'立即执行任务: {task.name}')
        return task.execute()
        
    def get_all_tasks(self) -> List[dict]:
        """获取所有任务"""
        return [task.get_info() for task in self.tasks.values()]
        
    def get_summary(self) -> dict:
        """获取摘要"""
        total = len(self.tasks)
        enabled = sum(1 for task in self.tasks.values() if task.enabled)
        running = self.is_running
        
        return {
            'total_tasks': total,
            'enabled_tasks': enabled,
            'disabled_tasks': total - enabled,
            'is_running': running,
            'check_interval': self.check_interval
        }
        
    def create_interval_task(self, task_id: str, name: str, 
                           callback: Callable, interval_seconds: int) -> Task:
        """创建间隔任务"""
        task = Task(
            task_id=task_id,
            name=name,
            task_type=TaskType.INTERVAL,
            callback=callback,
            interval_seconds=interval_seconds
        )
        self.add_task(task)
        return task
        
    def create_daily_task(self, task_id: str, name: str,
                         callback: Callable, run_at: str) -> Task:
        """创建每日任务"""
        task = Task(
            task_id=task_id,
            name=name,
            task_type=TaskType.DAILY,
            callback=callback,
            run_at=run_at
        )
        self.add_task(task)
        return task
        
    def create_weekly_task(self, task_id: str, name: str,
                          callback: Callable, run_at: str) -> Task:
        """创建每周任务"""
        task = Task(
            task_id=task_id,
            name=name,
            task_type=TaskType.WEEKLY,
            callback=callback,
            run_at=run_at
        )
        self.add_task(task)
        return task
