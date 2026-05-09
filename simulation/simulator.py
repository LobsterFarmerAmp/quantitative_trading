"""
模拟交易引擎
模拟真实交易环境，执行策略信号
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
import pandas as pd
import numpy as np

from simulation.portfolio_manager import PortfolioManager
from simulation.order_manager import OrderManager, OrderSide, OrderType
from modules.logger import Logger, TradeLogger
from modules.risk_manager import RiskManager
from config import BROKER_PARAMS, RISK_PARAMS


class Simulator:
    """模拟交易引擎"""
    
    def __init__(self, initial_cash: Optional[float] = None,
                 commission_rate: Optional[float] = None,
                 slippage_rate: Optional[float] = None,
                 logger: Optional[Logger] = None):
        """
        初始化模拟交易引擎
        
        Parameters:
        -----------
        initial_cash : float
            初始资金
        commission_rate : float
            佣金比例
        slippage_rate : float
            滑点比例
        logger : Logger
            日志管理器
        """
        self.initial_cash = initial_cash or BROKER_PARAMS['初始资金']
        self.commission_rate = commission_rate or BROKER_PARAMS['佣金比例']
        self.slippage_rate = slippage_rate or BROKER_PARAMS['滑点比例']
        
        self.logger = logger or Logger()
        self.trade_logger = TradeLogger()
        
        self.portfolio = PortfolioManager(self.initial_cash)
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager(logger=self.logger)
        
        self.current_date = None
        self.current_prices = {}
        self.trading_history = []
        
        self.is_running = False
        self.is_paused = False
        
        self.logger.log_system({
            'event': '模拟交易引擎初始化',
            'initial_cash': self.initial_cash,
            'commission_rate': self.commission_rate,
            'slippage_rate': self.slippage_rate
        })
        
    def start(self):
        """启动模拟"""
        self.is_running = True
        self.logger.log_system({'event': '模拟交易开始'})
        
    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        self.logger.log_system({'event': '模拟交易暂停'})
        
    def resume(self):
        """恢复模拟"""
        self.is_paused = False
        self.logger.log_system({'event': '模拟交易恢复'})
        
    def stop(self):
        """停止模拟"""
        self.is_running = False
        self.logger.log_system({'event': '模拟交易停止'})
        
    def update_prices(self, prices: Dict[str, float], date: datetime):
        """更新当前价格"""
        self.current_prices = prices
        self.current_date = date
        self.portfolio.update_prices(prices)
        
    def execute_order(self, order) -> dict:
        """
        执行订单
        
        Parameters:
        -----------
        order : Order
            订单对象
            
        Returns:
        --------
        dict: 执行结果
        """
        if not self.is_running or self.is_paused:
            return {'success': False, 'reason': '模拟未运行或已暂停'}
            
        symbol = order.symbol
        size = order.size
        
        if symbol not in self.current_prices:
            self.order_manager.reject_order(order, '无当前价格')
            return {'success': False, 'reason': '无当前价格'}
            
        current_price = self.current_prices[symbol]
        
        if order.order_type == OrderType.MARKET:
            execution_price = current_price * (1 + self.slippage_rate if order.is_buy else 1 - self.slippage_rate)
        else:
            if order.price is None:
                self.order_manager.reject_order(order, '限价单未指定价格')
                return {'success': False, 'reason': '限价单未指定价格'}
            execution_price = order.price
            
            if order.is_buy and execution_price < current_price:
                return {'success': False, 'reason': '价格未达到'}
            if order.is_sell and execution_price > current_price:
                return {'success': False, 'reason': '价格未达到'}
                
        commission = execution_price * size * self.commission_rate
        total_cost = execution_price * size + (commission if order.is_buy else -commission)
        
        risk_context = {
            'portfolio_value': self.portfolio.total_value,
            'position_value': self.portfolio.get_position(symbol).market_value if self.portfolio.has_position(symbol) else 0,
            'signal_reason': '策略信号'
        }
        
        passed, reasons = self.risk_manager.check_order(risk_context)
        
        if not passed:
            self.order_manager.reject_order(order, f'风控拒绝: {reasons}')
            self.logger.log_risk({
                'event': '订单被风控拒绝',
                'order': order.to_dict(),
                'reasons': reasons
            })
            return {'success': False, 'reason': f'风控拒绝: {reasons}'}
            
        if order.is_buy:
            if total_cost > self.portfolio.cash:
                self.order_manager.reject_order(order, '资金不足')
                return {'success': False, 'reason': '资金不足'}
                
            success = self.portfolio.buy(symbol, size, execution_price, self.current_date)
            
            if success:
                self.order_manager.fill_order(order, execution_price, self.current_date)
                
                self.logger.log_trade({
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': execution_price,
                    'size': size,
                    'amount': execution_price * size,
                    'commission': commission
                })
                
                self.trade_logger.log_trade({
                    'date': self.current_date.strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': execution_price,
                    'size': size,
                    'amount': execution_price * size,
                    'commission': commission,
                    'reason': '策略信号'
                })
                
                self.trading_history.append({
                    'date': self.current_date,
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': execution_price,
                    'size': size,
                    'commission': commission
                })
                
                return {
                    'success': True,
                    'order': order.to_dict(),
                    'execution_price': execution_price,
                    'commission': commission
                }
            else:
                self.order_manager.reject_order(order, '买入失败')
                return {'success': False, 'reason': '买入失败'}
                
        else:
            if not self.portfolio.has_position(symbol):
                self.order_manager.reject_order(order, '无持仓')
                return {'success': False, 'reason': '无持仓'}
                
            result = self.portfolio.sell(symbol, size, execution_price, self.current_date)
            
            if result['success']:
                self.order_manager.fill_order(order, execution_price, self.current_date)
                pnl = result['pnl']
                
                self.risk_manager.record_trade_result(pnl)
                
                self.logger.log_trade({
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': execution_price,
                    'size': size,
                    'amount': execution_price * size,
                    'commission': commission,
                    'pnl': pnl
                })
                
                self.trade_logger.log_trade({
                    'date': self.current_date.strftime('%Y-%m-%d'),
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': execution_price,
                    'size': size,
                    'amount': execution_price * size,
                    'commission': commission,
                    'pnl': pnl,
                    'reason': '策略信号'
                })
                
                self.trading_history.append({
                    'date': self.current_date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': execution_price,
                    'size': size,
                    'commission': commission,
                    'pnl': pnl
                })
                
                return {
                    'success': True,
                    'order': order.to_dict(),
                    'execution_price': execution_price,
                    'commission': commission,
                    'pnl': pnl
                }
            else:
                self.order_manager.reject_order(order, result.get('reason', '卖出失败'))
                return {'success': False, 'reason': result.get('reason', '卖出失败')}
                
    def process_signals(self, signals: Dict[str, str]) -> List[dict]:
        """
        处理交易信号
        
        Parameters:
        -----------
        signals : dict
            信号字典，格式: {symbol: 'BUY'/'SELL'/'HOLD'}
            
        Returns:
        --------
        List[dict]: 执行结果列表
        """
        results = []
        
        for symbol, signal in signals.items():
            if signal == 'BUY':
                if not self.portfolio.has_position(symbol):
                    price = self.current_prices.get(symbol)
                    if price:
                        position_value = self.portfolio.total_value * 0.1
                        size = int(position_value / price / 100) * 100
                        
                        if size > 0:
                            order = self.order_manager.buy_market(symbol, size)
                            result = self.execute_order(order)
                            results.append(result)
                            
            elif signal == 'SELL':
                if self.portfolio.has_position(symbol):
                    pos = self.portfolio.get_position(symbol)
                    order = self.order_manager.sell_market(symbol, pos.size)
                    result = self.execute_order(order)
                    results.append(result)
                    
        return results
        
    def get_status(self) -> dict:
        """获取模拟状态"""
        portfolio_status = self.portfolio.get_status()
        order_stats = self.order_manager.get_statistics()
        risk_status = self.risk_manager.get_status()
        
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'current_date': self.current_date.strftime('%Y-%m-%d') if self.current_date else None,
            'portfolio': portfolio_status,
            'orders': order_stats,
            'risk': {
                'enabled': risk_status['enabled'],
                'consecutive_losses': risk_status['consecutive_losses']
            }
        }
        
    def get_performance_report(self) -> dict:
        """获取性能报告"""
        performance = self.portfolio.get_performance_metrics()
        portfolio_status = self.portfolio.get_status()
        
        return {
            'performance': performance,
            'portfolio': portfolio_status,
            'trading_history': len(self.trading_history),
            'positions': self.portfolio.get_positions_summary(),
            'trades': self.portfolio.get_trades_summary()
        }
        
    def generate_daily_report(self) -> dict:
        """生成每日报告"""
        status = self.get_status()
        report = {
            'date': status['current_date'],
            'portfolio_value': status['portfolio']['total_value'],
            'daily_pnl': status['portfolio']['total_pnl'],
            'daily_pnl_pct': status['portfolio']['total_pnl_pct'],
            'positions': len(status['portfolio']['num_positions']),
            'pending_orders': status['orders']['pending_orders'],
            'risk_status': status['risk']
        }
        return report
