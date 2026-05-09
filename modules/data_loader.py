"""
数据加载器模块
从AKShare获取和处理市场数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: AKShare未安装，数据加载功能将受限")


class DataLoader:
    """数据加载器类"""
    
    def __init__(self, cache_dir='data'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_stock_data(self, symbol, start_date, end_date, adjust='qfq'):
        """
        获取股票数据
        
        Parameters:
        -----------
        symbol : str
            股票代码，如 '000001.XSHE' 或 '600000.XSHG'
        start_date : str
            开始日期，格式 'YYYYMMDD'
        end_date : str
            结束日期，格式 'YYYYMMDD'
        adjust : str
            复权类型，'qfq'前复权，'hfq'后复权，''不复权
            
        Returns:
        --------
        pd.DataFrame
            包含 OHLCV 数据的DataFrame
        """
        symbol_code = symbol.split('.')[0]
        exchange = symbol.split('.')[1] if '.' in symbol else 'XSHE'
        
        cache_file = self.cache_dir / f"{symbol_code}_{start_date}_{end_date}_{adjust}.csv"
        
        if cache_file.exists():
            print(f"从缓存加载数据: {symbol}")
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            return df
            
        if not AKSHARE_AVAILABLE:
            print("错误: AKShare未安装，无法获取数据")
            return None
            
        try:
            print(f"从AKShare获取数据: {symbol}")
            
            if exchange == 'XSHE':
                stock_code = symbol_code
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period='daily',
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            elif exchange == 'XSHG':
                stock_code = symbol_code
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period='daily',
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )
            else:
                print(f"不支持的交易所: {exchange}")
                return None
                
            if df is not None and len(df) > 0:
                col_map = {
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                }
                df.rename(columns=col_map, inplace=True)
                needed = ['date', 'open', 'high', 'low', 'close', 'volume']
                available = [c for c in needed if c in df.columns]
                if len(available) < 6:
                    print(f"数据列不全: {list(df.columns)}, 需要: {needed}")
                    return None
                df = df[needed].copy()
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)
                
                df.to_csv(cache_file)
                print(f"数据已缓存到: {cache_file}")
                
                return df
            else:
                print(f"未获取到数据: {symbol}")
                return None
                
        except Exception as e:
            print(f"获取数据失败: {symbol}, 错误: {e}")
            return None
            
    def get_multiple_stocks(self, symbols, start_date, end_date, adjust='qfq'):
        """
        获取多只股票数据
        
        Returns:
        --------
        dict
            symbol -> DataFrame 的字典
        """
        data_dict = {}
        for symbol in symbols:
            df = self.get_stock_data(symbol, start_date, end_date, adjust)
            if df is not None:
                data_dict[symbol] = df
        return data_dict
        
    def validate_data(self, df):
        """
        验证数据质量
        
        检查项：
        - 数据是否为空
        - 是否有缺失值
        - 是否有异常值
        - 数据是否连续
        """
        if df is None or len(df) == 0:
            return False, "数据为空"
            
        if df.isnull().any().any():
            missing_pct = (df.isnull().sum() / len(df) * 100).to_dict()
            return False, f"存在缺失值: {missing_pct}"
            
        if (df['high'] < df['low']).any():
            return False, "存在最高价<最低价的异常数据"
            
        if (df['close'] <= 0).any() or (df['volume'] < 0).any():
            return False, "存在价格<=0或成交量<0的异常数据"
            
        date_range = pd.date_range(df.index.min(), df.index.max(), freq='D')
        trading_days = set(df.index)
        expected_days = set(date_range)
        
        if len(expected_days - trading_days) > len(df) * 0.1:
            return False, f"数据不连续，缺失超过10%的交易日"
            
        return True, "数据验证通过"
        
    def get_trading_calendar(self, start_date, end_date):
        """
        获取交易日历
        """
        if not AKSHARE_AVAILABLE:
            return pd.date_range(start_date, end_date, freq='B')
            
        try:
            calendar = ak.tool_trade_date_hist_sse()
            calendar['trade_date'] = pd.to_datetime(calendar['trade_date'])
            calendar = calendar[
                (calendar['trade_date'] >= start_date) & 
                (calendar['trade_date'] <= end_date)
            ]
            return calendar['trade_date'].tolist()
        except Exception as e:
            print(f"获取交易日历失败: {e}")
            return pd.date_range(start_date, end_date, freq='B')


if __name__ == '__main__':
    loader = DataLoader()
    
    test_symbol = '000001.XSHE'
    df = loader.get_stock_data(test_symbol, '20230101', '20231231')
    
    if df is not None:
        valid, msg = loader.validate_data(df)
        print(f"\n数据验证结果: {msg}")
        print(f"数据形状: {df.shape}")
        print(f"时间范围: {df.index.min()} ~ {df.index.max()}")
        print(f"\n前5行数据:")
        print(df.head())
