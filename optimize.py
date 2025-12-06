"""
参数优化脚本 - TrendVolumeSniper 策略

使用 Backtrader 的 optstrategy 进行网格搜索，寻找最优参数组合
优化目标：最大化夏普比率（符合"反脆弱"理念）
"""

import backtrader as bt
import backtrader.analyzers as btanalyzers
from pathlib import Path
from typing import List, Dict, Tuple
import multiprocessing

from strategy import TrendVolumeSniper
from data_loader import get_pandas_data


def run_optimization():
    """
    运行参数优化
    """
    # 1. 初始化 Cerebro
    cerebro = bt.Cerebro(optreturn=False)  # optreturn=False 返回所有结果
    
    # 2. 设置初始资金
    initial_cash = 1_000_000.0
    cerebro.broker.setcash(initial_cash)
    
    # 设置手续费（0.1%）
    cerebro.broker.setcommission(commission=0.001)
    
    # 设置滑点（0.1%）
    cerebro.broker.set_slippage_perc(perc=0.001)
    
    # 3. 加载数据
    data_file = Path('data/JM.csv')
    
    # 如果数据文件不存在，创建示例数据
    if not data_file.exists():
        print(f'数据文件不存在: {data_file}')
        print('正在创建示例数据...')
        from utils.data_loader import DataLoader
        data_file.parent.mkdir(parents=True, exist_ok=True)
        DataLoader.create_sample_data(
            output_path=str(data_file),
            start_date='2020-01-01',
            end_date='2023-12-31',
            initial_price=100.0
        )
        print(f'示例数据已创建: {data_file}')
    
    # 使用 data_loader.py 加载数据
    print(f'正在加载数据: {data_file}')
    data = get_pandas_data(str(data_file))
    cerebro.adddata(data)
    
    # 4. 添加优化策略（使用 optstrategy）
    print('\n设置参数优化空间...')
    
    # trend_period: range(20, 100, 10) -> [20, 30, 40, 50, 60, 70, 80, 90]
    trend_periods = list(range(5, 100, 5))
    
    # vol_multiplier: [1.2, 1.5, 2.0]
    vol_multipliers = [1, 1.2, 1.5, 2.0]
    
    print(f'趋势周期范围: {trend_periods}')
    print(f'成交量倍数范围: {vol_multipliers}')
    print(f'总参数组合数: {len(trend_periods) * len(vol_multipliers)}')
    
    # 使用 optstrategy 添加策略（传递参数范围）
    cerebro.optstrategy(
        TrendVolumeSniper,
        trend_period=trend_periods,
        vol_multiplier=vol_multipliers,
        # 固定其他参数
        vol_ma_period=20,
        atr_period=14,
        stop_loss_atr_multiplier=2.0,
        risk_per_trade=0.02,
        use_trailing_stop=True,
        printlog=False  # 优化时关闭日志以提高性能
    )
    
    # 5. 添加分析器（用于评估优化结果）
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
    
    # 6. 运行优化（使用多进程）
    print('\n' + '=' * 60)
    print('开始参数优化')
    print('=' * 60)
    print(f'使用多进程加速（最大CPU数: {multiprocessing.cpu_count()}）')
    
    # 运行优化
    opt_results = cerebro.run(maxcpus=None)  # None 表示使用所有可用CPU
    
    # 7. 处理优化结果
    print('\n处理优化结果...')
    
    results_list = []
    
    # opt_results 是一个列表，每个元素对应一个参数组合的结果
    # 每个元素是一个列表，包含该参数组合下的策略实例
    for result in opt_results:
        if len(result) > 0:
            strat_result = result[0]  # 获取策略实例
            
            # 获取策略参数
            params = strat_result.p
            
            # 获取分析结果
            sharpe_analysis = strat_result.analyzers.sharpe.get_analysis()
            sharpe_ratio = sharpe_analysis.get('sharperatio', None)
            
            drawdown_analysis = strat_result.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', None)
            
            returns_analysis = strat_result.analyzers.returns.get_analysis()
            total_return = returns_analysis.get('rtot', None)  # 总收益率
            
            trades_analysis = strat_result.analyzers.trades.get_analysis()
            total_trades = trades_analysis.get('total', {}).get('total', 0)
            won_trades = trades_analysis.get('won', {}).get('total', 0)
            
            # 计算胜率
            win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            # 获取最终资金（需要从策略中获取）
            # 注意：在多进程优化中，每个进程有独立的broker状态
            # 我们需要从策略的broker获取最终价值
            try:
                final_value = strat_result.broker.getvalue()
            except (AttributeError, TypeError):
                # 如果无法获取，使用初始资金和收益率计算
                final_value = initial_cash * (1 + total_return) if total_return is not None else initial_cash
            
            # 只保留有有效夏普比率的结果
            if sharpe_ratio is not None and not (isinstance(sharpe_ratio, float) and (sharpe_ratio != sharpe_ratio)):  # 检查NaN
                results_list.append({
                    'trend_period': params.trend_period,
                    'vol_multiplier': params.vol_multiplier,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown if max_drawdown is not None else 0.0,
                    'total_return': total_return if total_return is not None else 0.0,
                    'final_value': final_value,
                    'total_trades': total_trades,
                    'win_rate': win_rate
                })
    
    # 8. 按夏普比率排序，获取前5名
    if not results_list:
        print('警告: 没有有效的优化结果')
        return
    
    # 按夏普比率降序排序
    results_list.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
    top_5 = results_list[:5]
    
    # 9. 输出结果
    print('\n' + '=' * 80)
    print('优化结果 - Top 5 参数组合（按夏普比率排序）')
    print('=' * 80)
    print(f'{"排名":<6} {"趋势周期":<10} {"成交量倍数":<12} {"夏普比率":<12} '
          f'{"最大回撤(%)":<14} {"总收益率(%)":<14} {"胜率(%)":<10} {"交易次数":<10}')
    print('-' * 80)
    
    for idx, result in enumerate(top_5, 1):
        print(f'{idx:<6} '
              f'{result["trend_period"]:<10} '
              f'{result["vol_multiplier"]:<12.2f} '
              f'{result["sharpe_ratio"]:<12.4f} '
              f'{result["max_drawdown"]:<14.2f} '
              f'{(result["total_return"] * 100):<14.2f} '
              f'{result["win_rate"]:<10.2f} '
              f'{result["total_trades"]:<10}')
    
    print('=' * 80)
    
    # 10. 输出最佳参数组合的详细信息
    if top_5:
        best = top_5[0]
        print('\n【最佳参数组合】')
        print(f'趋势周期 (trend_period): {best["trend_period"]}')
        print(f'成交量倍数 (vol_multiplier): {best["vol_multiplier"]}')
        print(f'\n性能指标:')
        print(f'  夏普比率: {best["sharpe_ratio"]:.4f}')
        print(f'  最大回撤: {best["max_drawdown"]:.2f}%')
        print(f'  总收益率: {best["total_return"] * 100:.2f}%')
        print(f'  胜率: {best["win_rate"]:.2f}%')
        print(f'  交易次数: {best["total_trades"]}')
        print(f'  最终资金: {best["final_value"]:,.2f}')
    
    print('\n优化完成！')
    print('=' * 80)


if __name__ == '__main__':
    run_optimization()

