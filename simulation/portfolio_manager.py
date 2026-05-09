"""
持仓管理器
管理模拟盘的持仓、盈亏计算
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from datetime import datetime
from typing import Dict, List, Optional


class Position:
    """持仓类"""
    
    def __init__(self, symbol: str, size: int, entry_price: float, entry_date: datetime):
        self.symbol = symbol
        self.size = size
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.current_price = entry_price
        
    @property
    def market_value(self) -> float:
        """市值"""
        return self.size * self.current_price
        
    @property
    def cost(self) -> float:
        """成本"""
        return self.size * self.entry_price
        
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost
        
    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏比例"""
        return self.unrealized_pnl / self.cost if self.cost > 0 else 0
        
    def update_price(self, price: float):
        """更新当前价格"""
        self.current_price = price


class PortfolioManager:
    """持仓管理器"""
    
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[dict] = []
        
    @property
    def total_market_value(self) -> float:
        """总市值（现金+持仓）"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
        
    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_market_value - self.initial_cash
        
    @property
    def total_pnl_pct(self) -> float:
        """总盈亏比例"""
        return self.total_pnl / self.initial_cash if self.initial_cash > 0 else 0
        
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
        
    @property
    def total_value(self) -> float:
        """总价值（等于总市值）"""
        return self.total_market_value
        
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
        
    def has_position(self, symbol: str) -> bool:
        """检查是否有持仓"""
        return symbol in self.positions
        
    def buy(self, symbol: str, size: int, price: float, date: datetime) -> bool:
        """
        买入
        
        Returns:
        --------
        bool: 是否成功
        """
        amount = size * price
        
        if amount > self.cash:
            return False
            
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.cost + amount
            total_size = pos.size + size
            new_entry_price = total_cost / total_size
            
            pos.size = total_size
            pos.entry_price = new_entry_price
            pos.current_price = price
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                size=size,
                entry_price=price,
                entry_date=date
            )
            
        self.cash -= amount
        return True
        
    def sell(self, symbol: str, size: int, price: float, date: datetime) -> dict:
        """
        卖出
        
        Returns:
        --------
        dict: 交易结果，包含盈亏信息
        """
        if symbol not in self.positions:
            return {'success': False, 'reason': '无持仓'}
            
        pos = self.positions[symbol]
        
        if size > pos.size:
            size = pos.size
            
        amount = size * price
        cost = size * pos.entry_price
        pnl = amount - cost
        
        pos.size -= size
        self.cash += amount
        
        trade_result = {
            'success': True,
            'symbol': symbol,
            'size': size,
            'price': price,
            'amount': amount,
            'cost': cost,
            'pnl': pnl,
            'pnl_pct': pnl / cost if cost > 0 else 0,
            'date': date
        }
        
        self.closed_trades.append(trade_result)
        
        if pos.size == 0:
            del self.positions[symbol]
            
        return trade_result
        
    def update_prices(self, prices: Dict[str, float]):
        """批量更新持仓价格"""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)
                
    def get_status(self) -> dict:
        """获取账户状态"""
        return {
            'initial_cash': self.initial_cash,
            'cash': self.cash,
            'positions_value': sum(pos.market_value for pos in self.positions.values()),
            'total_value': self.total_value,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct * 100,
            'unrealized_pnl': self.unrealized_pnl,
            'num_positions': len(self.positions),
            'num_trades': len(self.closed_trades)
        }
        
    def get_positions_summary(self) -> List[dict]:
        """获取持仓摘要"""
        summary = []
        for symbol, pos in self.positions.items():
            summary.append({
                'symbol': symbol,
                'size': pos.size,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'cost': pos.cost,
                'unrealized_pnl': pos.unrealized_pnl,
                'unrealized_pnl_pct': pos.unrealized_pnl_pct * 100,
                'entry_date': pos.entry_date.strftime('%Y-%m-%d')
            })
        return summary
        
    def get_trades_summary(self) -> List[dict]:
        """获取交易摘要"""
        return self.closed_trades.copy()
        
    def get_performance_metrics(self) -> dict:
        """获取性能指标"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_trades': 0,
                'lose_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': self.total_pnl
            }
            
        wins = [t['pnl'] for t in self.closed_trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in self.closed_trades if t['pnl'] <= 0]
        
        total_trades = len(self.closed_trades)
        win_trades = len(wins)
        lose_trades = len(losses)
        
        metrics = {
            'total_trades': total_trades,
            'win_trades': win_trades,
            'lose_trades': lose_trades,
            'win_rate': win_trades / total_trades if total_trades > 0 else 0,
            'avg_win': sum(wins) / len(wins) if wins else 0,
            'avg_loss': sum(losses) / len(losses) if losses else 0,
            'total_pnl': sum(t['pnl'] for t in self.closed_trades),
            'profit_factor': abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        }
        
        return metrics
