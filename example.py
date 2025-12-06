"""
示例脚本：快速开始使用系统验证实验室

演示如何使用系统进行回测
"""

from backtest.engine import BacktestEngine
from utils.data_loader import DataLoader
from utils.visualizer import Visualizer
from strategies.trend_sniper import TrendSniperStrategy
from pathlib import Path


def example_backtest():
    """
    示例回测函数
    """
    # 1. 创建示例数据（如果数据文件不存在）
    data_file = Path('data/JM.csv')
    data_dir = data_file.parent
    
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    
    if not data_file.exists():
        print('创建示例数据文件...')
        DataLoader.create_sample_data(
            output_path=str(data_file),
            start_date='2020-01-01',
            end_date='2023-12-31',
            initial_price=100.0
        )
    
    # 2. 加载数据
    print('加载数据...')
    data = DataLoader.load_from_csv(str(data_file))
    
    # 3. 创建回测引擎
    engine = BacktestEngine(
        initial_cash=1000000.0,  # 100万初始资金
        commission=0.001  # 0.1% 手续费
    )
    
    # 4. 添加数据
    engine.add_data(data)
    
    # 5. 设置策略参数
    engine.set_strategy(
        TrendSniperStrategy,
        trend_ma_period=20,          # 趋势均线周期
        volume_ma_period=20,         # 成交量均线周期
        volume_multiplier=1.5,       # 成交量倍数
        atr_period=14,               # ATR 周期
        atr_stop_multiplier=2.0,     # ATR 止损倍数
        position_size=0.95,          # 仓位大小（95%）
        printlog=True                # 打印交易日志
    )
    
    # 6. 添加分析器
    import backtrader.analyzers as btanalyzers
    
    engine.add_analyzer(btanalyzers.SharpeRatio, _name='sharpe')
    engine.add_analyzer(btanalyzers.DrawDown, _name='drawdown')
    engine.add_analyzer(btanalyzers.Returns, _name='returns')
    engine.add_analyzer(btanalyzers.TradeAnalyzer, _name='trades')
    
    # 7. 运行回测
    cerebro = engine.run()
    
    # 8. 输出详细结果
    strat = cerebro.runstrats[0][0]
    
    print('\n' + '=' * 60)
    print('详细回测分析结果')
    print('=' * 60)
    
    # 夏普比率
    sharpe = strat.analyzers.sharpe.get_analysis()
    if 'sharperatio' in sharpe and sharpe['sharperatio'] is not None:
        print(f'夏普比率: {sharpe["sharperatio"]:.4f}')
    
    # 最大回撤
    drawdown = strat.analyzers.drawdown.get_analysis()
    if 'max' in drawdown:
        print(f'最大回撤: {drawdown["max"]["drawdown"]:.2f}%')
        print(f'最大回撤期: {drawdown["max"]["len"]} 天')
    
    # 收益率
    returns = strat.analyzers.returns.get_analysis()
    if 'rnorm100' in returns:
        print(f'年化收益率: {returns["rnorm100"]:.2f}%')
    
    # 交易统计
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    print(f'\n交易统计:')
    print(f'  总交易次数: {total_trades}')
    print(f'  盈利交易: {won_trades}')
    print(f'  亏损交易: {lost_trades}')
    
    if total_trades > 0:
        win_rate = won_trades / total_trades * 100
        print(f'  胜率: {win_rate:.2f}%')
        
        # 平均盈亏（使用安全的访问方式）
        pnl_analysis = trades.get('pnl', {})
        if 'net' in pnl_analysis and 'total' in pnl_analysis['net']:
            net_pnl = pnl_analysis['net']['total']
            print(f'  总盈亏: {net_pnl:,.2f}')
        
        if won_trades > 0 and 'won' in pnl_analysis:
            avg_win = pnl_analysis['won'].get('average', 0)
            if avg_win != 0:
                print(f'  平均盈利: {avg_win:,.2f}')
        
        if lost_trades > 0 and 'lost' in pnl_analysis:
            avg_loss = pnl_analysis['lost'].get('average', 0)
            if avg_loss != 0:
                print(f'  平均亏损: {avg_loss:,.2f}')
    else:
        print('  胜率: 无交易记录')
    
    print('=' * 60)
    
    # 9. 可视化（可选）
    # 取消下面的注释以显示图表
    # Visualizer.plot_backtest(cerebro)
    
    # 或者保存图表到文件
    plot_file = Path('results/backtest_result.png')
    plot_file.parent.mkdir(parents=True, exist_ok=True)
    Visualizer.save_backtest_plot(cerebro, str(plot_file))
    print(f'\n图表已保存到: {plot_file}')


if __name__ == '__main__':
    example_backtest()

