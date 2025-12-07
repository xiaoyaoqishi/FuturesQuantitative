"""
主程序入口 - TrendVolumeSniper 策略回测

执行趋势成交量狙击手策略的回测，支持单个品种或全部品种回测
"""

import backtrader as bt
import backtrader.analyzers as btanalyzers
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import argparse

from strategy import TrendVolumeSniper
from data_loader import get_pandas_data


def analyze_entry_conditions(
    data_file: Path,
    symbol: str,
    trend_period: int = 60,
    vol_ma_period: int = 20,
    vol_multiplier: float = 1.5,
    breakout_period: int = 20
) -> Dict:
    """
    分析入场条件满足情况
    
    Returns:
        包含条件分析结果的字典
    """
    try:
        data = get_pandas_data(str(data_file))
        if not hasattr(data, 'p') or not hasattr(data.p, 'dataname'):
            return {'error': '无法获取数据'}
        
        df = data.p.dataname
        min_period = max(trend_period, vol_ma_period, breakout_period)
        
        if len(df) < min_period:
            return {
                'error': f'数据量不足: {len(df)} < {min_period}',
                'data_count': len(df),
                'required': min_period
            }
        
        # 计算指标
        trend_ma = df['close'].rolling(window=trend_period).mean()
        volume_ma = df['volume'].rolling(window=vol_ma_period).mean()
        highest_high = df['high'].rolling(window=breakout_period).max()
        
        # 统计条件满足情况
        total_bars = len(df) - min_period
        trend_met = 0
        breakout_met = 0
        volume_met = 0
        all_met = 0
        
        condition_details = []
        
        for i in range(min_period, len(df)):
            if pd.isna(trend_ma.iloc[i]) or pd.isna(volume_ma.iloc[i]) or pd.isna(highest_high.iloc[i]):
                continue
            
            close = df['close'].iloc[i]
            trend_cond = close > trend_ma.iloc[i]
            breakout_cond = close > highest_high.iloc[i]
            volume_cond = df['volume'].iloc[i] > volume_ma.iloc[i] * vol_multiplier
            
            if trend_cond:
                trend_met += 1
            if breakout_cond:
                breakout_met += 1
            if volume_cond:
                volume_met += 1
            if trend_cond and breakout_cond and volume_cond:
                all_met += 1
                if len(condition_details) < 5:  # 只记录前5个满足条件的点
                    condition_details.append({
                        'date': df.index[i],
                        'close': close,
                        'trend_ma': trend_ma.iloc[i],
                        'highest_high': highest_high.iloc[i],
                        'volume': df['volume'].iloc[i],
                        'volume_threshold': volume_ma.iloc[i] * vol_multiplier
                    })
        
        return {
            'total_bars': total_bars,
            'trend_met': trend_met,
            'breakout_met': breakout_met,
            'volume_met': volume_met,
            'all_met': all_met,
            'trend_rate': trend_met / total_bars * 100 if total_bars > 0 else 0,
            'breakout_rate': breakout_met / total_bars * 100 if total_bars > 0 else 0,
            'volume_rate': volume_met / total_bars * 100 if total_bars > 0 else 0,
            'all_met_rate': all_met / total_bars * 100 if total_bars > 0 else 0,
            'condition_details': condition_details,
            'data_count': len(df),
            'date_range': (df.index.min(), df.index.max())
        }
    except Exception as e:
        return {'error': f'分析失败: {e}'}


def run_backtest_for_symbol(
    symbol: str,
    data_file: Path,
    initial_cash: float = 1_000_000.0,
    printlog: bool = False,
    detailed_diagnosis: bool = False
) -> Dict:
    """
    对单个品种运行回测
    
    Args:
        symbol: 品种代码
        data_file: 数据文件路径
        initial_cash: 初始资金
        printlog: 是否打印交易日志
    
    Returns:
        回测结果字典
    """
    # 初始化 Cerebro
    cerebro = bt.Cerebro()
    
    # 设置初始资金
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)
    
    # 加载数据
    try:
        data = get_pandas_data(str(data_file))
        cerebro.adddata(data)
        
        # 检查数据量
        if hasattr(data, 'p'):
            df = data.p.dataname if hasattr(data.p, 'dataname') else None
            if df is not None and len(df) < 60:
                return {
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'message': f'数据量不足: {len(df)} < 60'
                }
    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'load_error',
            'message': f'数据加载失败: {e}'
        }
    
    # 添加策略
    cerebro.addstrategy(
        TrendVolumeSniper,
        trend_period=35,
        vol_ma_period=20,
        vol_multiplier=1.2,
        atr_period=14,
        stop_loss_atr_multiplier=2.0,
        risk_per_trade=0.02,
        use_trailing_stop=True,
        printlog=printlog
    )
    
    # 添加分析器
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
    
    # 运行回测
    try:
        results = cerebro.run()
        strat = results[0]
        
        # 获取结果
        final_value = cerebro.broker.getvalue()
        total_return = ((final_value - initial_cash) / initial_cash) * 100
        
        sharpe_analysis = strat.analyzers.sharpe.get_analysis()
        sharpe_ratio = sharpe_analysis.get('sharperatio', None)
        
        drawdown_analysis = strat.analyzers.drawdown.get_analysis()
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', None)
        
        trades_analysis = strat.analyzers.trades.get_analysis()
        total_trades = trades_analysis.get('total', {}).get('total', 0)
        won_trades = trades_analysis.get('won', {}).get('total', 0)
        lost_trades = trades_analysis.get('lost', {}).get('total', 0)
        
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        pnl_analysis = trades_analysis.get('pnl', {})
        net_pnl = pnl_analysis.get('net', {}).get('total', 0) if 'net' in pnl_analysis else 0
        
        result = {
            'symbol': symbol,
            'status': 'success',
            'initial_cash': initial_cash,
            'final_value': final_value,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'won_trades': won_trades,
            'lost_trades': lost_trades,
            'win_rate': win_rate,
            'net_pnl': net_pnl
        }
        
        # 如果无交易记录且需要详细诊断，分析入场条件
        if total_trades == 0 and detailed_diagnosis:
            condition_analysis = analyze_entry_conditions(
                data_file=data_file,
                symbol=symbol,
                trend_period=60,
                vol_ma_period=20,
                vol_multiplier=1.5,
                breakout_period=20
            )
            result['condition_analysis'] = condition_analysis
        
        return result
    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'backtest_error',
            'message': f'回测失败: {e}'
        }


def main():
    """
    主函数：对期货品种执行 TrendVolumeSniper 策略回测
    支持单个品种或全部品种回测
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='TrendVolumeSniper 策略回测')
    parser.add_argument(
        '--symbol',
        type=str,
        default="JM",
        help='指定单个品种代码（如: JM, LC），如果不指定则回测所有品种'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='无交易记录时输出详细的诊断信息'
    )
    
    args = parser.parse_args()
    
    print('=' * 80)
    if args.symbol:
        print(f'TrendVolumeSniper 策略 - 单品种回测: {args.symbol}')
    else:
        print('TrendVolumeSniper 策略 - 全品种回测')
    print('=' * 80)
    
    # 1. 查找数据文件
    data_dir = Path('data')
    if not data_dir.exists():
        print('❌ 数据目录不存在，请先运行 data_downloader.py 下载数据')
        return
    
    # 根据参数选择数据文件
    if args.symbol:
        # 单个品种
        data_file = data_dir / f'{args.symbol.upper()}.csv'
        if not data_file.exists():
            print(f'❌ 数据文件不存在: {data_file}')
            print('请先运行 data_downloader.py 下载该品种的数据')
            return
        data_files = [data_file]
    else:
        # 所有品种
        data_files = list(data_dir.glob('*.csv'))
        # 排除示例数据
        data_files = [f for f in data_files if f.stem != 'sample_data']
        
        if not data_files:
            print('❌ 未找到数据文件，请先运行 data_downloader.py 下载数据')
            return
    
    print(f'\n找到 {len(data_files)} 个数据文件')
    
    # 2. 策略参数说明
    print('\n策略参数:')
    print('  - 趋势均线周期: 60')
    print('  - 成交量均线周期: 20')
    print('  - 成交量倍数: 1.5')
    print('  - 突破周期: 20')
    print('  - 入场条件: 需要同时满足 1)价格>趋势均线 2)价格>20日最高价 3)成交量>成交量均线×1.5')
    
    # 3. 设置初始资金（每个品种独立）
    initial_cash = 1_000_000.0
    
    # 4. 运行所有品种的回测
    print(f'\n开始回测，每个品种初始资金: {initial_cash:,.2f}')
    print('=' * 80)
    
    results = []
    success_count = 0
    error_count = 0
    no_trade_count = 0
    
    for idx, data_file in enumerate(data_files, 1):
        symbol = data_file.stem  # 文件名（不含扩展名）作为品种代码
        
        print(f'\n[{idx}/{len(data_files)}] 回测品种: {symbol}')
        print('-' * 80)
        
        result = run_backtest_for_symbol(
            symbol=symbol,
            data_file=data_file,
            initial_cash=initial_cash,
            printlog=args.symbol is not None,  # 单品种时开启日志
            detailed_diagnosis=args.detailed or args.symbol is not None  # 单品种或指定详细诊断时分析
        )
        
        results.append(result)
        
        if result['status'] == 'success':
            success_count += 1
            if result['total_trades'] == 0:
                no_trade_count += 1
                print(f'  ⚠️  无交易记录')
                
                # 输出详细诊断信息
                if 'condition_analysis' in result:
                    analysis = result['condition_analysis']
                    if 'error' not in analysis:
                        print(f'\n  【入场条件分析】')
                        print(f'  数据量: {analysis["data_count"]} 条')
                        print(f'  日期范围: {analysis["date_range"][0]} 至 {analysis["date_range"][1]}')
                        print(f'  有效回测周期: {analysis["total_bars"]} 个交易日')
                        print(f'\n  条件满足统计:')
                        print(f'    趋势条件 (Close > 60日均线): {analysis["trend_met"]} 次 ({analysis["trend_rate"]:.1f}%)')
                        print(f'    突破条件 (Close > 20日最高): {analysis["breakout_met"]} 次 ({analysis["breakout_rate"]:.1f}%)')
                        print(f'    成交量条件 (Volume > 成交量均线×1.5): {analysis["volume_met"]} 次 ({analysis["volume_rate"]:.1f}%)')
                        print(f'    同时满足三个条件: {analysis["all_met"]} 次 ({analysis["all_met_rate"]:.1f}%)')
                        
                        if analysis['all_met'] == 0:
                            print(f'\n  【原因分析】')
                            if analysis['trend_rate'] < 50:
                                print(f'    - 趋势条件满足率较低 ({analysis["trend_rate"]:.1f}%)，可能数据整体处于震荡或下跌趋势')
                            if analysis['breakout_rate'] < 10:
                                print(f'    - 突破条件满足率很低 ({analysis["breakout_rate"]:.1f}%)，价格很少突破20日最高价')
                            if analysis['volume_rate'] < 20:
                                print(f'    - 成交量条件满足率较低 ({analysis["volume_rate"]:.1f}%)，成交量放大情况较少')
                            print(f'    - 建议: 尝试放宽参数（如降低 trend_period 或 vol_multiplier）或使用更多历史数据')
                        elif analysis['all_met'] > 0:
                            print(f'\n  ⚠️  有 {analysis["all_met"]} 次满足入场条件但未交易，可能是仓位计算为0或其他原因')
                            if analysis['condition_details']:
                                print(f'\n  前几个满足条件的时点:')
                                for detail in analysis['condition_details'][:3]:
                                    print(f'    - {detail["date"]}: 收盘价={detail["close"]:.2f}, '
                                          f'趋势均线={detail["trend_ma"]:.2f}, '
                                          f'20日最高={detail["highest_high"]:.2f}, '
                                          f'成交量={detail["volume"]:.0f}')
                    else:
                        print(f'  ❌ 条件分析失败: {analysis["error"]}')
            else:
                print(f'  ✓ 回测完成 | 收益率: {result["total_return"]:.2f}% | '
                      f'交易次数: {result["total_trades"]} | '
                      f'胜率: {result["win_rate"]:.2f}%')
        else:
            error_count += 1
            print(f'  ❌ {result.get("message", "回测失败")}')
    
    # 5. 汇总结果
    print('\n' + '=' * 80)
    print('回测汇总报告')
    print('=' * 80)
    
    # 筛选成功的结果
    successful_results = [r for r in results if r['status'] == 'success']
    traded_results = [r for r in successful_results if r['total_trades'] > 0]
    
    print(f'\n【总体统计】')
    print(f'总品种数: {len(results)}')
    print(f'成功回测: {success_count}')
    print(f'回测失败: {error_count}')
    print(f'无交易记录: {no_trade_count}')
    print(f'有交易记录: {len(traded_results)}')
    
    if traded_results:
        print(f'\n【有交易记录的品种统计】')
        
        # 按收益率排序
        sorted_results = sorted(traded_results, key=lambda x: x['total_return'], reverse=True)
        
        # 创建汇总表格
        print(f'\n{"品种":<8} {"收益率(%)":<12} {"交易次数":<10} {"胜率(%)":<10} {"夏普比率":<12} {"最大回撤(%)":<12}')
        print('-' * 80)
        
        for r in sorted_results[:20]:  # 显示前20名
            sharpe_str = f"{r['sharpe_ratio']:.4f}" if r['sharpe_ratio'] is not None else "N/A"
            dd_str = f"{r['max_drawdown']:.2f}" if r['max_drawdown'] is not None else "N/A"
            print(f"{r['symbol']:<8} {r['total_return']:>10.2f}% {r['total_trades']:>8} "
                  f"{r['win_rate']:>8.2f}% {sharpe_str:>12} {dd_str:>12}")
        
        if len(sorted_results) > 20:
            print(f'\n... 还有 {len(sorted_results) - 20} 个品种未显示')
        
        # 统计指标
        avg_return = sum(r['total_return'] for r in traded_results) / len(traded_results)
        avg_trades = sum(r['total_trades'] for r in traded_results) / len(traded_results)
        avg_win_rate = sum(r['win_rate'] for r in traded_results) / len(traded_results)
        
        print(f'\n【平均值统计】')
        print(f'平均收益率: {avg_return:.2f}%')
        print(f'平均交易次数: {avg_trades:.1f}')
        print(f'平均胜率: {avg_win_rate:.2f}%')
        
        # 最佳和最差
        best = sorted_results[0]
        worst = sorted_results[-1]
        
        print(f'\n【最佳表现】')
        print(f'品种: {best["symbol"]} | 收益率: {best["total_return"]:.2f}% | '
              f'交易次数: {best["total_trades"]} | 胜率: {best["win_rate"]:.2f}%')
        
        print(f'\n【最差表现】')
        print(f'品种: {worst["symbol"]} | 收益率: {worst["total_return"]:.2f}% | '
              f'交易次数: {worst["total_trades"]} | 胜率: {worst["win_rate"]:.2f}%')
    
    # 显示失败和错误
    failed_results = [r for r in results if r['status'] != 'success']
    if failed_results:
        print(f'\n【失败/错误品种】')
        for r in failed_results:
            print(f'  - {r["symbol"]}: {r.get("message", "未知错误")}')
    
    print('\n' + '=' * 80)
    print('回测完成')
    print('=' * 80)
    
    # 注释掉图表输出
    # print('\n正在生成图表...')
    # cerebro.plot(style='candlestick', barup='green', bardown='red', volume=True)


if __name__ == '__main__':
    main()
