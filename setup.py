"""
安装依赖并初始化项目
"""

import subprocess
import sys
from pathlib import Path


def install_requirements():
    """安装项目依赖"""
    print("="*60)
    print("安装项目依赖")
    print("="*60)
    
    requirements_file = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_file.exists():
        print("错误: requirements.txt 文件不存在")
        return False
        
    try:
        print("\n正在安装依赖...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
        ])
        print("\n依赖安装完成!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n安装失败: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    print("\n创建项目目录...")
    
    directories = [
        'data',
        'data/raw',
        'data/processed',
        'logs',
        'logs/trades',
        'logs/risk',
        'logs/system',
        'reports',
        'reports/daily',
        'reports/weekly',
        'reports/monthly',
        'strategies',
        'modules',
        'backtest',
        'simulation',
        'scripts',
        'config',
        'tests'
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        
    print(f"已创建 {len(directories)} 个目录")


def verify_installation():
    """验证安装"""
    print("\n" + "="*60)
    print("验证安装")
    print("="*60)
    
    required_modules = [
        'backtrader',
        'akshare',
        'pandas',
        'numpy',
        'matplotlib'
    ]
    
    all_ok = True
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            print(f"✗ {module} - 未安装")
            all_ok = False
            
    return all_ok


def run_test():
    """运行测试"""
    print("\n" + "="*60)
    print("运行测试")
    print("="*60)
    
    try:
        from scripts.run_backtest import run_simple_backtest
        print("\n运行简单回测测试...")
        run_simple_backtest()
        print("\n✓ 回测测试完成")
        return True
    except Exception as e:
        print(f"\n✗ 回测测试失败: {e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("量化交易系统初始化")
    print("="*60)
    
    install_requirements()
    
    create_directories()
    
    if verify_installation():
        print("\n" + "="*60)
        print("初始化完成!")
        print("="*60)
        print("\n下一步:")
        print("1. 运行 'python main.py' 启动系统")
        print("2. 运行 'python scripts/run_backtest.py' 运行回测")
        print("3. 查看 'reports' 目录查看回测结果")
    else:
        print("\n部分依赖未安装成功，请手动安装")


if __name__ == '__main__':
    main()
