"""
测试 akshare API 可用性

用于检查 akshare 中可用的期货数据下载函数
"""

import akshare as ak


def test_akshare_functions():
    """测试 akshare 中可用的期货数据函数"""
    print('=' * 60)
    print('测试 akshare API 可用性')
    print('=' * 60)
    
    # 检查常见的期货数据函数
    functions_to_check = {
        'futures_zh_daily_sina': '期货日线数据（新浪）',
        'futures_zh_hist_sina': '期货历史数据（新浪）',
        'get_futures_daily': '获取期货日线数据',
        'futures_main_sina': '主力合约列表（新浪）',
        'futures_zh_continuous_sina': '期货连续合约（新浪）',
        'tool_trade_date_hist_sina': '交易日历史数据',
    }
    
    available_functions = {}
    
    for func_name, description in functions_to_check.items():
        if hasattr(ak, func_name):
            available_functions[func_name] = description
            print(f'✓ {func_name:30s} - {description}')
        else:
            print(f'✗ {func_name:30s} - {description} (不可用)')
    
    print('\n' + '=' * 60)
    print(f'找到 {len(available_functions)} 个可用函数')
    print('=' * 60)
    
    # 尝试测试下载数据
    if 'futures_zh_daily_sina' in available_functions:
        print('\n测试下载焦煤数据（JM0）...')
        try:
            df = ak.futures_zh_daily_sina(
                symbol='JM0',
                start_date='20240101',
                end_date='20240131'
            )
            if df is not None and not df.empty:
                print(f'✓ 成功下载数据，共 {len(df)} 条记录')
                print(f'  列名: {list(df.columns)}')
                print(f'  数据预览:')
                print(df.head())
            else:
                print('✗ 下载成功但数据为空')
        except Exception as e:
            print(f'✗ 下载失败: {e}')
    
    return available_functions


if __name__ == '__main__':
    test_akshare_functions()

