"""
数据加载器模块

提供 get_pandas_data() 函数，用于读取期货数据 CSV 文件并返回 Backtrader PandasData feed
支持灵活的列映射和自动日期时间解析
"""

import pandas as pd
import backtrader as bt
from typing import Optional, Union, Dict
from pathlib import Path


def get_pandas_data(
    filepath: Union[str, Path],
    datetime_column: Optional[str] = None,
    date_format: Optional[str] = None,
    column_mapping: Optional[Dict[str, str]] = None
) -> bt.feeds.PandasData:
    """
    读取期货数据 CSV 文件并返回 Backtrader PandasData feed
    
    支持灵活的列映射，自动识别常见的列名变体（如 Date/date/DATE, Open/open/OPEN 等）
    
    Args:
        filepath: CSV 文件路径
        datetime_column: 日期时间列名（如果为 None，则自动检测 Date/date/DATE/DateTime 等）
        date_format: 日期格式字符串（如果为 None，则自动推断）
                     例如: '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y' 等
        column_mapping: 自定义列映射字典，格式为 {'backtrader_column': 'csv_column'}
                       例如: {'open': 'Open', 'high': 'High', 'close': 'Close'}
                       如果为 None，则使用默认映射或自动检测
                       必需的映射键: 'open', 'high', 'low', 'close', 'volume'
    
    Returns:
        Backtrader PandasData feed 对象，可直接用于回测
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 数据格式不正确或缺少必需的列
    
    Example:
        >>> # 使用默认列名（Date, Open, High, Low, Close, Volume）
        >>> data = get_pandas_data('data/futures.csv')
        
        >>> # 自定义列映射（CSV 列名为大写）
        >>> data = get_pandas_data(
        ...     'data/futures.csv',
        ...     column_mapping={
        ...         'open': 'Open',
        ...         'high': 'High',
        ...         'low': 'Low',
        ...         'close': 'Close',
        ...         'volume': 'Volume'
        ...     }
        ... )
        
        >>> # 指定日期列和格式
        >>> data = get_pandas_data(
        ...     'data/futures.csv',
        ...     datetime_column='交易日期',
        ...     date_format='%Y-%m-%d'
        ... )
        
        >>> # 中文列名映射
        >>> data = get_pandas_data(
        ...     'data/futures.csv',
        ...     datetime_column='日期',
        ...     column_mapping={
        ...         'open': '开盘价',
        ...         'high': '最高价',
        ...         'low': '最低价',
        ...         'close': '收盘价',
        ...         'volume': '成交量'
        ...     }
        ... )
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f'数据文件不存在: {filepath}')
    
    # 读取 CSV 文件
    df = pd.read_csv(filepath)
    
    # 默认列映射（支持大小写变体和常见命名）
    default_mapping = {
        'datetime': ['Date', 'date', 'DATE', 'DateTime', 'datetime', 'DATETIME', 
                    '时间', '日期', '交易日期', 'TradeDate', 'trade_date'],
        'open': ['Open', 'open', 'OPEN', '开盘', '开盘价', 'OPEN_PRICE'],
        'high': ['High', 'high', 'HIGH', '最高', '最高价', 'HIGH_PRICE'],
        'low': ['Low', 'low', 'LOW', '最低', '最低价', 'LOW_PRICE'],
        'close': ['Close', 'close', 'CLOSE', '收盘', '收盘价', 'CLOSE_PRICE'],
        'volume': ['Volume', 'volume', 'VOLUME', '成交量', 'Vol', 'vol', 'VOL']
    }
    
    # 如果提供了自定义映射，使用自定义映射；否则自动检测
    if column_mapping is None:
        column_mapping = {}
        # 自动检测列名
        for bt_col, possible_names in default_mapping.items():
            for name in possible_names:
                if name in df.columns:
                    column_mapping[bt_col] = name
                    break
        
        # 检查是否找到了所有必需的列
        required_bt_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_bt_cols if col not in column_mapping]
        if missing_cols:
            available_cols = list(df.columns)
            raise ValueError(
                f'无法找到以下必需的列: {missing_cols}\n'
                f'可用列名: {available_cols}\n'
                f'请使用 column_mapping 参数指定列映射\n'
                f'例如: column_mapping={{\'open\': \'{available_cols[0]}\', ...}}'
            )
    else:
        # 验证自定义映射是否包含所有必需的列
        required_bt_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_bt_cols if col not in column_mapping]
        if missing_cols:
            raise ValueError(
                f'column_mapping 缺少以下必需的列: {missing_cols}\n'
                f'必需的映射键: {required_bt_cols}'
            )
        
        # 验证映射的列是否存在于数据中
        missing_csv_cols = []
        for bt_col, csv_col in column_mapping.items():
            if csv_col not in df.columns:
                missing_csv_cols.append(f'{bt_col} -> {csv_col}')
        if missing_csv_cols:
            raise ValueError(
                f'column_mapping 中指定的以下列不存在于数据中: {missing_csv_cols}\n'
                f'可用列名: {list(df.columns)}'
            )
    
    # 处理日期时间列
    if datetime_column is None:
        # 自动检测日期列
        datetime_candidates = default_mapping['datetime']
        datetime_column = None
        for candidate in datetime_candidates:
            if candidate in df.columns:
                datetime_column = candidate
                break
        
        if datetime_column is None:
            # 检查是否在 column_mapping 中指定了 datetime
            if 'datetime' in column_mapping:
                datetime_column = column_mapping['datetime']
            else:
                available_cols = list(df.columns)
                raise ValueError(
                    f'无法找到日期时间列\n'
                    f'可用列名: {available_cols}\n'
                    f'请使用 datetime_column 参数指定日期列名\n'
                    f'例如: datetime_column=\'{available_cols[0]}\''
                )
    elif datetime_column not in df.columns:
        raise ValueError(
            f'指定的日期列 "{datetime_column}" 不存在于数据中\n'
            f'可用列名: {list(df.columns)}'
        )
    
    # 创建数据副本并重命名列为标准名称
    df_processed = df.copy()
    
    # 重命名列（将 CSV 列名映射为 Backtrader 标准列名）
    rename_dict = {}
    for bt_col, csv_col in column_mapping.items():
        if csv_col in df_processed.columns:
            rename_dict[csv_col] = bt_col
    
    df_processed.rename(columns=rename_dict, inplace=True)
    
    # 处理日期时间列
    # 如果日期列已经被重命名，使用新名称；否则使用原始列名
    dt_col = rename_dict.get(datetime_column, datetime_column)
    
    if dt_col not in df_processed.columns:
        # 如果日期列没有被重命名，使用原始列名
        dt_col = datetime_column
    
    if dt_col not in df_processed.columns:
        raise ValueError(f'日期列 "{datetime_column}" 在处理后不存在')
    
    # 确保日期列为 datetime 类型
    df_processed[dt_col] = pd.to_datetime(
        df_processed[dt_col], 
        format=date_format, 
        errors='coerce'
    )
    
    # 检查日期转换是否成功
    if df_processed[dt_col].isna().all():
        raise ValueError(
            f'无法解析日期列 "{datetime_column}"\n'
            f'请检查日期格式，或使用 date_format 参数指定格式\n'
            f'例如: date_format=\'%Y-%m-%d\''
        )
    
    # 设置日期为索引
    df_processed.set_index(dt_col, inplace=True)
    
    # 确保数据类型正确
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in df_processed.columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
    
    # 删除包含 NaN 的行
    initial_len = len(df_processed)
    df_processed.dropna(inplace=True)
    dropped_rows = initial_len - len(df_processed)
    
    if dropped_rows > 0:
        print(f'警告: 删除了 {dropped_rows} 行包含 NaN 的数据')
    
    # 按日期排序
    df_processed.sort_index(inplace=True)
    
    # 验证数据完整性
    if len(df_processed) == 0:
        raise ValueError('处理后的数据为空，请检查数据格式和列映射')
    
    # 验证数据范围
    print(f'数据加载成功: {len(df_processed)} 条记录')
    print(f'日期范围: {df_processed.index.min()} 至 {df_processed.index.max()}')
    
    # 创建 Backtrader PandasData feed
    data = bt.feeds.PandasData(
        dataname=df_processed,
        datetime=None,  # 使用索引作为日期
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1  # 如果没有持仓量数据，设为 -1
    )
    
    return data

