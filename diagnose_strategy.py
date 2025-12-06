"""
策略诊断脚本

用于分析为什么策略没有产生交易
"""

import pandas as pd
from pathlib import Path
from data_loader import get_pandas_data


def diagnose_data(data_file: str):
    """
    诊断数据文件，检查是否满足策略要求
    """
    print('=' * 60)
    print('策略数据诊断')
    print('=' * 60)
    
    filepath = Path(data_file)
    if not filepath.exists():
        print(f'❌ 数据文件不存在: {filepath}')
        return
    
    # 加载数据
    try:
        data = get_pandas_data(str(filepath))
        df = data.p.dataname if hasattr(data.p, 'dataname') else None
        
        if df is None:
            print('❌ 无法读取数据内容')
            return
        
        print(f'\n【数据基本信息】')
        print(f'数据文件: {filepath}')
        print(f'总记录数: {len(df)}')
        print(f'日期范围: {df.index.min()} 至 {df.index.max()}')
        
        # 检查数据量
        min_required = 60  # trend_period
        print(f'\n【数据量检查】')
        if len(df) < min_required:
            print(f'❌ 数据量不足: 需要至少 {min_required} 条记录，当前只有 {len(df)} 条')
            print(f'   策略需要 {min_required} 个数据点才能开始计算趋势均线')
        else:
            print(f'✓ 数据量充足: {len(df)} >= {min_required}')
        
        # 检查数据质量
        print(f'\n【数据质量检查】')
        missing_cols = []
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                missing_cols.append(col)
        
        if missing_cols:
            print(f'❌ 缺少必需的列: {missing_cols}')
        else:
            print(f'✓ 所有必需的列都存在')
        
        # 检查是否有 NaN
        nan_count = df[['open', 'high', 'low', 'close', 'volume']].isna().sum().sum()
        if nan_count > 0:
            print(f'⚠️  警告: 数据中包含 {nan_count} 个 NaN 值')
        else:
            print(f'✓ 数据中没有 NaN 值')
        
        # 模拟策略条件检查
        print(f'\n【策略条件模拟检查】')
        print('检查前100个数据点是否满足入场条件...')
        
        # 计算指标
        trend_ma = df['close'].rolling(window=60).mean()
        volume_ma = df['volume'].rolling(window=20).mean()
        highest_high = df['high'].rolling(window=20).max()
        
        # 检查条件
        conditions_met = 0
        for i in range(min_required, min(len(df), min_required + 100)):
            if pd.isna(trend_ma.iloc[i]) or pd.isna(volume_ma.iloc[i]) or pd.isna(highest_high.iloc[i]):
                continue
            
            trend_cond = df['close'].iloc[i] > trend_ma.iloc[i]
            breakout_cond = df['close'].iloc[i] > highest_high.iloc[i]
            volume_cond = df['volume'].iloc[i] > volume_ma.iloc[i] * 1.5
            
            if trend_cond and breakout_cond and volume_cond:
                conditions_met += 1
                if conditions_met == 1:
                    print(f'  ✓ 找到满足条件的点 (第 {i+1} 个数据点):')
                    print(f'    日期: {df.index[i]}')
                    print(f'    收盘价: {df["close"].iloc[i]:.2f} > 趋势均线: {trend_ma.iloc[i]:.2f}')
                    print(f'    收盘价: {df["close"].iloc[i]:.2f} > 20日最高: {highest_high.iloc[i]:.2f}')
                    print(f'    成交量: {df["volume"].iloc[i]:.0f} > 成交量阈值: {volume_ma.iloc[i] * 1.5:.0f}')
        
        if conditions_met == 0:
            print(f'  ❌ 在前100个有效数据点中，没有找到同时满足三个条件的点')
            print(f'     建议:')
            print(f'     1. 检查数据是否包含明显的上升趋势')
            print(f'     2. 尝试放宽参数（如降低 trend_period 或 vol_multiplier）')
            print(f'     3. 使用更多历史数据')
        else:
            print(f'  ✓ 找到 {conditions_met} 个满足条件的点')
        
        # 统计各条件单独满足的情况
        print(f'\n【各条件单独统计（前100个有效点）】')
        trend_count = 0
        breakout_count = 0
        volume_count = 0
        
        for i in range(min_required, min(len(df), min_required + 100)):
            if pd.isna(trend_ma.iloc[i]) or pd.isna(volume_ma.iloc[i]) or pd.isna(highest_high.iloc[i]):
                continue
            
            if df['close'].iloc[i] > trend_ma.iloc[i]:
                trend_count += 1
            if df['close'].iloc[i] > highest_high.iloc[i]:
                breakout_count += 1
            if df['volume'].iloc[i] > volume_ma.iloc[i] * 1.5:
                volume_count += 1
        
        valid_points = min(100, len(df) - min_required)
        print(f'  趋势条件满足: {trend_count}/{valid_points} ({trend_count/valid_points*100:.1f}%)')
        print(f'  突破条件满足: {breakout_count}/{valid_points} ({breakout_count/valid_points*100:.1f}%)')
        print(f'  成交量条件满足: {volume_count}/{valid_points} ({volume_count/valid_points*100:.1f}%)')
        
        print('\n' + '=' * 60)
        print('诊断完成')
        print('=' * 60)
        
    except Exception as e:
        print(f'❌ 诊断过程中出错: {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 诊断默认数据文件
    data_file = 'data/JM.csv'
    
    if not Path(data_file).exists():
        data_file = 'data/futures_data.csv'
    
    if not Path(data_file).exists():
        print('请先运行 main.py 或 data_downloader.py 生成数据文件')
    else:
        diagnose_data(data_file)

