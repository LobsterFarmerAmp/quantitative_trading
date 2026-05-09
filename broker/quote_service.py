"""
实时行情服务
支持多数据源：baostock(免费) / HTTP接口
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
import threading
from datetime import datetime, time as dtime
from typing import Dict, Optional, Callable, List
import json

try:
    import baostock as bs
    BAOSTOCK_AVAILABLE = True
except ImportError:
    BAOSTOCK_AVAILABLE = False


class QuoteService:
    """
    实时行情服务

    功能：
    1. 全市场扫描获取最新价格
    2. 定时刷新（交易时段每5秒，非交易时段每30秒）
    3. 订阅回调，支持实时推送
    4. 断线重连机制
    """

    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.prices: Dict[str, float] = {}
        self.volumes: Dict[str, int] = {}
        self.last_update: Dict[str, datetime] = {}
        self.subscribers: List[Callable] = []
        self.is_running = False
        self.thread = None
        self._stop_event = threading.Event()

        if BAOSTOCK_AVAILABLE:
            self.bs_logged_in = False

    def login_baostock(self) -> bool:
        if not BAOSTOCK_AVAILABLE:
            return False
        try:
            if not self.bs_logged_in:
                lg = bs.login()
                self.bs_logged_in = (lg.error_code == '0')
                return self.bs_logged_in
            return True
        except Exception:
            return False

    def logout_baostock(self):
        if BAOSTOCK_AVAILABLE and self.bs_logged_in:
            try:
                bs.logout()
            except Exception:
                pass
            self.bs_logged_in = False

    def get_price(self, symbol: str) -> Optional[float]:
        """获取单个标的价格"""
        return self.prices.get(symbol)

    def get_all_prices(self) -> Dict[str, float]:
        """获取所有价格"""
        return self.prices.copy()

    def get_quote(self, symbol: str) -> Optional[dict]:
        """获取完整行情"""
        return {
            'symbol': symbol,
            'price': self.prices.get(symbol),
            'volume': self.volumes.get(symbol),
            'last_update': self.last_update.get(symbol)
        }

    def subscribe(self, callback: Callable):
        """订阅行情更新"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """取消订阅"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def _notify_subscribers(self):
        """通知订阅者"""
        for cb in self.subscribers:
            try:
                cb(self.prices.copy())
            except Exception:
                pass

    def _fetch_baostock_quotes(self, symbols: List[str]) -> Dict[str, float]:
        """通过baostock获取行情"""
        prices = {}
        self.login_baostock()

        stock_codes = []
        for sym in symbols:
            if sym.endswith('.XSHG'):
                stock_codes.append(f'sh.{sym.split(".")[0]}')
            elif sym.endswith('.XSHE'):
                stock_codes.append(f'sz.{sym.split(".")[0]}')

        if not stock_codes:
            return {}

        rs = bs.query_trade_dates(start_date=datetime.now().strftime('%Y-%m-%d'),
                                  end_date=datetime.now().strftime('%Y-%m-%d'))

        for code in stock_codes:
            try:
                rs = bs.query_realtime_quots(code)
                data = []
                while rs.error_code == '0' and rs.next():
                    data.append(rs.get_row_data())

                if data and len(data) > 0:
                    row = data[0]
                    price = float(row[3]) if len(row) > 3 and row[3] else None
                    volume = int(float(row[5])) if len(row) > 5 and row[5] else 0

                    orig_sym = symbols[stock_codes.index(code)]
                    if price:
                        prices[orig_sym] = price
                        self.prices[orig_sym] = price
                        self.volumes[orig_sym] = volume
                        self.last_update[orig_sym] = datetime.now()
            except Exception:
                pass

        return prices

    def _fetch_fallback(self, symbols: List[str]) -> Dict[str, float]:
        """备用：从缓存或静态获取"""
        result = {}
        for sym in symbols:
            if sym in self.prices:
                result[sym] = self.prices[sym]
        return result

    def fetch_quotes(self, symbols: List[str]) -> Dict[str, float]:
        """统一获取行情接口"""
        if BAOSTOCK_AVAILABLE:
            try:
                return self._fetch_baostock_quotes(symbols)
            except Exception:
                pass
        return self._fetch_fallback(symbols)

    def start(self, symbols: List[str]):
        """启动行情服务"""
        if self.is_running:
            return

        self.symbols = symbols
        self.is_running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止行情服务"""
        self.is_running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        self.logout_baostock()

    def _run_loop(self):
        """主循环"""
        while not self._stop_event.is_set():
            try:
                prices = self.fetch_quotes(self.symbols)
                if prices:
                    self._notify_subscribers()
            except Exception:
                pass

            if self._is_trading_time():
                time.sleep(self.refresh_interval)
            else:
                time.sleep(30)

    def _is_trading_time(self) -> bool:
        """判断是否在交易时间"""
        now = datetime.now()
        current_time = now.time()
        trading_start = dtime(9, 30)
        trading_end = dtime(15, 0)
        is_weekday = now.weekday() < 5

        if not is_weekday:
            return False

        return trading_start <= current_time <= trading_end

    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'symbols_count': len(self.prices),
            'subscribers_count': len(self.subscribers),
            'last_updates': {s: t.strftime('%H:%M:%S') for s, t in self.last_update.items()}
        }


class MarketCalendar:
    """交易日历"""

    @staticmethod
    def is_trading_day(dt: datetime = None) -> bool:
        """判断是否为交易日"""
        if dt is None:
            dt = datetime.now()
        if dt.weekday() >= 5:
            return False

        if BAOSTOCK_AVAILABLE:
            try:
                lg = bs.login()
                rs = bs.query_trade_dates(
                    start_date=dt.strftime('%Y-%m-%d'),
                    end_date=dt.strftime('%Y-%m-%d')
                )
                data = []
                while rs.next():
                    data.append(rs.get_row_data())
                if lg.error_code == '0':
                    bs.logout()
                if data:
                    return data[0][1] == '1'
            except Exception:
                pass

        return dt.weekday() < 5

    @staticmethod
    def is_trading_time() -> bool:
        """判断是否在交易时间内"""
        now = datetime.now()
        t = now.time()
        is_weekday = now.weekday() < 5
        is_上午 = dtime(9, 30) <= t <= dtime(11, 30)
        is_下午 = dtime(13, 0) <= t <= dtime(15, 0)
        return is_weekday and (is_上午 or is_下午)

    @staticmethod
    def get_next_trading_day(dt: datetime = None) -> str:
        """获取下一个交易日"""
        if dt is None:
            dt = datetime.now()

        from datetime import timedelta
        for _ in range(10):
            dt += timedelta(days=1)
            if MarketCalendar.is_trading_day(dt):
                return dt.strftime('%Y-%m-%d')
        return ''


if __name__ == '__main__':
    print('实时行情服务测试')

    svc = QuoteService(refresh_interval=5)
    symbols = ['000001.XSHE', '600000.XSHG', '601318.XSHG']

    def on_update(prices):
        print(f'行情更新: {prices}')

    svc.subscribe(on_update)
    svc.login_baostock()

    prices = svc.fetch_quotes(symbols)
    print(f'行情: {prices}')
    print(f'状态: {svc.get_status()}')

    svc.logout_baostock()
    print('测试完成')