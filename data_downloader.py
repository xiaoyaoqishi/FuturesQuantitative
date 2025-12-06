"""
数据下载器模块

用于从 akshare 下载中国国内期货主力连续合约数据
支持焦煤、碳酸锂等期货品种

注意：akshare 的 API 可能会更新，如果遇到问题，请：
1. 更新 akshare: pip install akshare --upgrade
2. 查看最新文档: https://akshare.readthedocs.io/
"""

import pandas as pd
import akshare as ak
from pathlib import Path
from typing import Optional
from datetime import datetime
import time


def check_akshare_api():
    """
    检查 akshare 中可用的期货数据下载函数
    
    Returns:
        list: 可用的函数名列表
    """
    print('检查 akshare 中可用的期货数据函数...')
    available_functions = []
    
    # 检查常见的期货数据函数
    functions_to_check = [
        'futures_zh_daily_sina',
        'futures_zh_hist_sina',
        'get_futures_daily',
        'futures_main_sina',
        'futures_zh_continuous_sina',
    ]
    
    for func_name in functions_to_check:
        if hasattr(ak, func_name):
            available_functions.append(func_name)
            print(f'  ✓ {func_name} 可用')
        else:
            print(f'  ✗ {func_name} 不可用')
    
    return available_functions


def get_all_futures_symbols() -> list:
    """
    获取所有期货品种列表
    
    Returns:
        list: 期货品种列表，格式为 [(symbol, name), ...]
    """
    print('正在获取所有期货品种列表...')
    futures_list = []
    
    try:
        # 方法1: 尝试使用 futures_contracts_info 获取所有合约信息
        if hasattr(ak, 'futures_contracts_info'):
            try:
                contracts_info = ak.futures_contracts_info()
                if contracts_info is not None and not contracts_info.empty:
                    # 提取品种代码和名称
                    for _, row in contracts_info.iterrows():
                        symbol = str(row.get('symbol', '')).strip()
                        name = str(row.get('name', '')).strip()
                        if symbol and name:
                            futures_list.append((symbol, name))
                    print(f'通过 futures_contracts_info 获取到 {len(futures_list)} 个品种')
                    return futures_list
            except Exception as e:
                print(f'futures_contracts_info 失败: {e}')
        
        # 方法2: 尝试使用期货品种列表接口
        if hasattr(ak, 'futures_zh_spot'):
            try:
                # 获取期货实时行情，从中提取品种列表
                spot_data = ak.futures_zh_spot()
                if spot_data is not None and not spot_data.empty:
                    # 提取品种代码（通常在前几列）
                    symbol_col = None
                    name_col = None
                    for col in spot_data.columns:
                        col_lower = str(col).lower()
                        if 'symbol' in col_lower or '代码' in col or 'code' in col_lower:
                            symbol_col = col
                        if 'name' in col_lower or '名称' in col or '品种' in col:
                            name_col = col
                    
                    if symbol_col:
                        symbols = spot_data[symbol_col].unique()
                        for symbol in symbols:
                            symbol_str = str(symbol).strip()
                            if symbol_str and len(symbol_str) <= 4:  # 品种代码通常很短
                                # 尝试获取名称
                                name = symbol_str
                                if name_col:
                                    name_data = spot_data[spot_data[symbol_col] == symbol]
                                    if not name_data.empty:
                                        name = str(name_data.iloc[0][name_col]).strip()
                                futures_list.append((symbol_str, name))
                        print(f'通过 futures_zh_spot 获取到 {len(futures_list)} 个品种')
                        return futures_list
            except Exception as e:
                print(f'futures_zh_spot 失败: {e}')
        
        # 方法3: 使用预定义的常见期货品种列表（如果API都失败）
        print('使用预定义的常见期货品种列表...')
        common_futures = [
            # 黑色系
            ('JM', '焦煤'), ('J', '焦炭'), ('I', '铁矿石'), ('RB', '螺纹钢'),
            ('HC', '热轧卷板'), ('SS', '不锈钢'), ('SF', '硅铁'), ('SM', '锰硅'),
            # 有色金属
            ('CU', '沪铜'), ('AL', '沪铝'), ('ZN', '沪锌'), ('PB', '沪铅'),
            ('NI', '沪镍'), ('SN', '沪锡'), ('AU', '黄金'), ('AG', '白银'),
            # 能源化工
            ('RU', '橡胶'), ('BU', '沥青'), ('FU', '燃料油'), ('LU', '低硫燃料油'),
            ('NR', '20号胶'), ('L', '塑料'), ('V', 'PVC'), ('PP', '聚丙烯'),
            ('EB', '苯乙烯'), ('EG', '乙二醇'), ('TA', 'PTA'), ('MA', '甲醇'),
            ('UR', '尿素'), ('SA', '纯碱'), ('PG', '液化石油气'), ('PF', '短纤'),
            # 农产品
            ('C', '玉米'), ('CS', '玉米淀粉'), ('A', '豆一'), ('B', '豆二'),
            ('M', '豆粕'), ('Y', '豆油'), ('P', '棕榈油'), ('L', '豆粕'),
            ('CF', '棉花'), ('CY', '棉纱'), ('SR', '白糖'), ('CJ', '红枣'),
            ('AP', '苹果'), ('PK', '花生'), ('OI', '菜籽油'), ('RM', '菜粕'),
            ('WH', '强麦'), ('PM', '普麦'), ('RI', '早籼稻'), ('LR', '晚籼稻'),
            ('JR', '粳稻'), ('RS', '菜籽'), ('WT', '硬麦'),
            # 其他
            ('LC', '碳酸锂'), ('BR', '丁二烯橡胶'), ('EC', '集运指数'),
        ]
        futures_list = common_futures
        print(f'使用预定义列表，共 {len(futures_list)} 个品种')
        
    except Exception as e:
        print(f'获取期货品种列表时出错: {e}')
        # 如果所有方法都失败，返回常见品种列表
        print('使用预定义的常见期货品种列表...')
        futures_list = [
            ('JM', '焦煤'), ('LC', '碳酸锂'), ('CU', '沪铜'), ('AL', '沪铝'),
            ('ZN', '沪锌'), ('RB', '螺纹钢'), ('I', '铁矿石'), ('J', '焦炭'),
        ]
    
    return futures_list


def download_dominant_contract(
    symbol: str,
    start_date: str,
    end_date: str,
    retry_times: int = 3,
    retry_delay: int = 2
) -> Optional[pd.DataFrame]:
    """
    下载期货主力连续合约数据
    
    Args:
        symbol: 期货代码（如 "JM" 表示焦煤，"LC" 表示碳酸锂）
                对于主力连续合约，通常使用 "JM0" 或 "LC0" 格式
        start_date: 开始日期，格式 "YYYYMMDD"（如 "20200101"）
        end_date: 结束日期，格式 "YYYYMMDD"（如 "20231231"）
        retry_times: 网络错误重试次数
        retry_delay: 重试延迟（秒）
    
    Returns:
        清洗后的 DataFrame，如果失败返回 None
    
    Raises:
        ValueError: 日期格式错误
        Exception: 网络错误或其他异常
    """
    # 验证日期格式
    try:
        datetime.strptime(start_date, '%Y%m%d')
        datetime.strptime(end_date, '%Y%m%d')
    except ValueError:
        raise ValueError(f'日期格式错误，应为 YYYYMMDD 格式，如 "20200101"')
    
    print(f'正在下载 {symbol} 期货数据...')
    print(f'日期范围: {start_date} 至 {end_date}')
    
    # 尝试下载数据（带重试机制）
    df = None
    last_error = None
    
    for attempt in range(retry_times):
        try:
            # 方法1: 使用 futures_zh_daily_sina 获取期货日线数据（主力连续合约）
            # 注意：该函数可能不接受 start_date 和 end_date 参数，需要先下载全部数据再过滤
            try:
                contract_symbol = symbol if symbol.endswith('0') else f'{symbol}0'
                
                # akshare 的期货日线数据接口（只传 symbol 参数）
                # 函数返回所有可用历史数据，我们稍后过滤日期范围
                df = ak.futures_zh_daily_sina(symbol=contract_symbol)
                
                if df is not None and not df.empty:
                    print(f'成功通过 futures_zh_daily_sina 获取数据（合约: {contract_symbol}）')
                    # 数据会在 clean_futures_data 函数中按日期过滤
                    break
            except TypeError as e:
                # 如果参数错误，尝试不同的调用方式
                if 'unexpected keyword argument' in str(e) or 'positional' in str(e):
                    print(f'方法1参数错误，尝试仅传 symbol 参数...')
                    try:
                        contract_symbol = symbol if symbol.endswith('0') else f'{symbol}0'
                        # 尝试只传 symbol 参数（位置参数）
                        df = ak.futures_zh_daily_sina(contract_symbol)
                        if df is not None and not df.empty:
                            print(f'成功通过 futures_zh_daily_sina 获取数据（仅symbol参数）')
                            break
                    except Exception as e2:
                        print(f'方法1（仅symbol）失败: {e2}')
                        last_error = e2
                else:
                    last_error = e
            except AttributeError:
                # 如果函数不存在，尝试其他方法
                print(f'futures_zh_daily_sina 函数不存在，尝试其他方法...')
                last_error = AttributeError('futures_zh_daily_sina 函数不存在')
            except Exception as e:
                print(f'方法1失败（合约 {contract_symbol if "contract_symbol" in locals() else symbol}）: {e}')
                last_error = e
                
                # 如果使用 "0" 后缀失败，尝试不使用后缀
                if not symbol.endswith('0'):
                    try:
                        df = ak.futures_zh_daily_sina(symbol=symbol)
                        if df is not None and not df.empty:
                            print(f'成功通过 futures_zh_daily_sina 获取数据（合约: {symbol}）')
                            break
                    except Exception as e2:
                        print(f'方法1（无后缀）失败: {e2}')
                        pass
            
            # 方法2: 尝试使用 get_futures_daily 接口（akshare 的另一个接口）
            try:
                contract_symbol = symbol if symbol.endswith('0') else f'{symbol}0'
                # 尝试不同的参数格式
                try:
                    df = ak.get_futures_daily(symbol=contract_symbol)
                except TypeError:
                    # 如果失败，尝试位置参数
                    df = ak.get_futures_daily(contract_symbol)
                
                if df is not None and not df.empty:
                    print(f'成功通过 get_futures_daily 获取数据（合约: {contract_symbol}）')
                    break
            except Exception as e:
                print(f'方法2失败: {e}')
                pass
            
            # 方法3: 尝试获取主力合约列表，然后下载历史数据
            try:
                # 获取当前主力合约
                main_contracts = ak.futures_main_sina(symbol=symbol)
                if main_contracts is not None and not main_contracts.empty:
                    # 尝试从返回的数据中获取合约代码
                    # akshare 返回的列名可能不同，需要灵活处理
                    contract_col = None
                    for col in main_contracts.columns:
                        col_str = str(col)
                        if '合约' in col_str or 'code' in col_str.lower() or 'symbol' in col_str.lower() or '名称' in col_str:
                            contract_col = col
                            break
                    
                    if contract_col:
                        main_contract = main_contracts.iloc[0][contract_col]
                        print(f'找到主力合约: {main_contract}')
                        
                        # 尝试使用 futures_zh_daily_sina 下载该合约的历史数据
                        try:
                            df = ak.futures_zh_daily_sina(symbol=str(main_contract))
                            if df is not None and not df.empty:
                                print(f'成功通过主力合约获取数据')
                                break
                        except:
                            # 如果失败，尝试 get_futures_daily
                            try:
                                df = ak.get_futures_daily(symbol=str(main_contract))
                                if df is not None and not df.empty:
                                    print(f'成功通过主力合约（get_futures_daily）获取数据')
                                    break
                            except:
                                pass
            except Exception as e:
                print(f'方法3失败: {e}')
                pass
            
            # 方法4: 尝试使用工具函数获取期货连续合约
            try:
                # 检查是否有工具函数可以获取连续合约代码
                if hasattr(ak, 'tool_trade_date_hist_sina'):
                    # 尝试获取连续合约数据
                    contract_symbol = symbol if symbol.endswith('0') else f'{symbol}0'
                    # 注意：这个函数可能需要不同的参数格式
                    pass  # 暂时跳过，需要根据实际 API 调整
            except Exception as e:
                print(f'方法4失败: {e}')
                pass
            
            # 如果所有方法都失败，等待后重试
            if df is None or df.empty:
                if attempt < retry_times - 1:
                    print(f'第 {attempt + 1} 次尝试失败，{retry_delay} 秒后重试...')
                    time.sleep(retry_delay)
                else:
                    # 提供更详细的错误信息和建议
                    error_msg = f'所有下载方法均失败，最后错误: {last_error}'
                    error_msg += '\n提示: 请尝试以下方法:'
                    error_msg += '\n1. 更新 akshare: pip install akshare --upgrade'
                    error_msg += '\n2. 检查合约代码是否正确（如 JM0, LC0）'
                    error_msg += '\n3. 查看 akshare 最新文档: https://akshare.readthedocs.io/'
                    raise Exception(error_msg)
        
        except Exception as e:
            last_error = e
            if attempt < retry_times - 1:
                print(f'网络错误: {e}')
                print(f'{retry_delay} 秒后重试...')
                time.sleep(retry_delay)
            else:
                print(f'下载失败，已重试 {retry_times} 次')
                raise Exception(f'下载数据失败: {e}')
    
    if df is None or df.empty:
        raise Exception('未能获取数据，请检查代码和网络连接')
    
    print(f'原始数据下载成功，共 {len(df)} 条记录')
    print(f'原始列名: {list(df.columns)}')
    
    # 数据清洗
    df_cleaned = clean_futures_data(df, start_date, end_date)
    
    return df_cleaned


def clean_futures_data(
    df: pd.DataFrame,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    清洗期货数据，转换为 Backtrader 兼容格式
    
    Args:
        df: 原始 DataFrame
        start_date: 开始日期（用于过滤）
        end_date: 结束日期（用于过滤）
    
    Returns:
        清洗后的 DataFrame
    """
    df_cleaned = df.copy()
    
    # 定义列名映射（中文 -> 英文）
    column_mapping = {
        # 日期列
        '日期': 'date',
        'date': 'date',
        'Date': 'date',
        'DATE': 'date',
        '交易日期': 'date',
        'time': 'date',
        'Time': 'date',
        
        # 开盘价
        '开盘': 'open',
        '开盘价': 'open',
        'open': 'open',
        'Open': 'open',
        'OPEN': 'open',
        
        # 最高价
        '最高': 'high',
        '最高价': 'high',
        'high': 'high',
        'High': 'high',
        'HIGH': 'high',
        
        # 最低价
        '最低': 'low',
        '最低价': 'low',
        'low': 'low',
        'Low': 'low',
        'LOW': 'low',
        
        # 收盘价
        '收盘': 'close',
        '收盘价': 'close',
        'close': 'close',
        'Close': 'close',
        'CLOSE': 'close',
        
        # 成交量
        '成交量': 'volume',
        'volume': 'volume',
        'Volume': 'volume',
        'VOLUME': 'volume',
        'vol': 'volume',
        'Vol': 'volume',
    }
    
    # 重命名列
    df_cleaned.rename(columns=column_mapping, inplace=True)
    
    # 检查必需的列是否存在
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing_columns = [col for col in required_columns if col not in df_cleaned.columns]
    
    if missing_columns:
        # 尝试查找相似的列名
        available_columns = list(df_cleaned.columns)
        print(f'警告: 缺少必需的列: {missing_columns}')
        print(f'可用列名: {available_columns}')
        
        # 如果缺少关键列，尝试使用索引或其他方式
        if 'date' not in df_cleaned.columns:
            # 尝试使用索引作为日期
            if df_cleaned.index.name in ['date', '日期', 'Date']:
                df_cleaned.reset_index(inplace=True)
                if 'date' not in df_cleaned.columns:
                    raise ValueError(f'无法找到日期列，可用列: {available_columns}')
        
        # 对于其他缺失的列，尝试使用数值列
        for col in missing_columns:
            if col == 'date':
                continue
            # 尝试查找包含该关键词的列
            possible_cols = [c for c in available_columns if col in c.lower()]
            if possible_cols:
                df_cleaned.rename(columns={possible_cols[0]: col}, inplace=True)
            else:
                raise ValueError(f'无法找到必需的列: {col}，可用列: {available_columns}')
    
    # 确保日期列为 datetime 类型
    if 'date' in df_cleaned.columns:
        df_cleaned['date'] = pd.to_datetime(df_cleaned['date'], errors='coerce')
        # 删除无法解析的日期行
        df_cleaned = df_cleaned.dropna(subset=['date'])
    else:
        raise ValueError('无法找到日期列')
    
    # 过滤日期范围
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    df_cleaned = df_cleaned[
        (df_cleaned['date'] >= start_dt) & 
        (df_cleaned['date'] <= end_dt)
    ]
    
    # 确保数值列为数值类型
    numeric_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_columns:
        if col in df_cleaned.columns:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
    
    # 删除包含 NaN 的行
    initial_len = len(df_cleaned)
    df_cleaned = df_cleaned.dropna(subset=numeric_columns)
    dropped_rows = initial_len - len(df_cleaned)
    
    if dropped_rows > 0:
        print(f'警告: 删除了 {dropped_rows} 行包含 NaN 的数据')
    
    # 按日期排序
    df_cleaned = df_cleaned.sort_values('date').reset_index(drop=True)
    
    # 只保留必需的列
    df_cleaned = df_cleaned[required_columns]
    
    print(f'数据清洗完成，共 {len(df_cleaned)} 条有效记录')
    print(f'日期范围: {df_cleaned["date"].min()} 至 {df_cleaned["date"].max()}')
    
    return df_cleaned


def save_futures_data(
    df: pd.DataFrame,
    symbol: str,
    output_dir: str = 'data'
) -> Path:
    """
    保存期货数据到 CSV 文件
    
    Args:
        df: 清洗后的 DataFrame
        symbol: 期货代码
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    filename = f'{symbol}.csv'
    filepath = output_path / filename
    
    # 保存为 CSV
    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    
    print(f'数据已保存到: {filepath.absolute()}')
    
    return filepath


def download_and_save(
    symbol: str,
    start_date: str,
    end_date: str,
    output_dir: str = 'data'
) -> Path:
    """
    下载并保存期货数据（便捷函数）
    
    Args:
        symbol: 期货代码
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        output_dir: 输出目录
    
    Returns:
        保存的文件路径
    """
    # 下载数据
    df = download_dominant_contract(symbol, start_date, end_date)
    
    # 保存数据
    filepath = save_futures_data(df, symbol, output_dir)
    
    return filepath


if __name__ == '__main__':
    """
    主执行块：下载所有期货品种的数据
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='下载中国国内期货数据')
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        help='指定要下载的品种代码（如: --symbols JM LC CU），如果不指定则下载所有品种'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='20200101',
        help='开始日期，格式 YYYYMMDD（默认: 20200101）'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='结束日期，格式 YYYYMMDD（默认: 今天）'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已存在的数据文件'
    )
    
    args = parser.parse_args()
    
    print('=' * 60)
    print('开始下载中国国内期货数据')
    print('=' * 60)
    
    # 首先检查可用的 API
    try:
        available_funcs = check_akshare_api()
        if not available_funcs:
            print('\n警告: 未找到常用的期货数据函数')
            print('请确保已安装最新版本的 akshare: pip install akshare --upgrade')
    except Exception as e:
        print(f'检查 API 时出错: {e}')
        print('继续尝试下载...')
    
    # 设置日期范围
    start_date = args.start_date
    end_date = args.end_date if args.end_date else datetime.now().strftime('%Y%m%d')
    
    # 获取期货品种列表
    if args.symbols:
        # 如果指定了品种，使用指定的品种
        futures_symbols = []
        all_symbols = get_all_futures_symbols()
        symbol_dict = {s[0]: s[1] for s in all_symbols}
        
        for symbol in args.symbols:
            symbol_upper = symbol.upper()
            if symbol_upper in symbol_dict:
                futures_symbols.append((symbol_upper, symbol_dict[symbol_upper]))
            else:
                # 如果不在列表中，使用代码作为名称
                futures_symbols.append((symbol_upper, symbol_upper))
                print(f'警告: 品种 {symbol_upper} 不在已知列表中，将尝试下载')
    else:
        # 下载所有品种
        print('\n获取所有期货品种列表...')
        futures_symbols = get_all_futures_symbols()
        print(f'找到 {len(futures_symbols)} 个期货品种')
    
    print(f'\n日期范围: {start_date} 至 {end_date}')
    print(f'将下载 {len(futures_symbols)} 个品种的数据')
    
    if len(futures_symbols) > 10:
        response = input(f'\n⚠️  将下载 {len(futures_symbols)} 个品种，可能需要较长时间，是否继续？(y/n): ')
        if response.lower() != 'y':
            print('已取消下载')
            exit(0)
    
    success_count = 0
    failed_symbols = []
    skipped_count = 0
    
    for idx, (symbol, name) in enumerate(futures_symbols, 1):
        try:
            print(f'\n【[{idx}/{len(futures_symbols)}] 下载 {name} ({symbol})】')
            print('-' * 60)
            
            # 检查文件是否已存在
            output_file = Path('data') / f'{symbol}.csv'
            if args.skip_existing and output_file.exists():
                print(f'⏭️  跳过（文件已存在: {output_file}）')
                skipped_count += 1
                continue
            
            # 下载并保存数据
            filepath = download_and_save(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                output_dir='data'
            )
            
            print(f'✅ {name} ({symbol}) 数据下载成功！')
            print(f'   文件路径: {filepath}')
            success_count += 1
            
            # 添加短暂延迟，避免请求过快
            if idx < len(futures_symbols):
                time.sleep(0.5)
            
        except Exception as e:
            print(f'❌ {name} ({symbol}) 数据下载失败: {e}')
            failed_symbols.append((symbol, name, str(e)))
            continue
    
    # 输出总结
    print('\n' + '=' * 60)
    print('下载完成')
    print('=' * 60)
    print(f'总计: {len(futures_symbols)} 个品种')
    print(f'成功: {success_count} 个')
    print(f'跳过: {skipped_count} 个')
    print(f'失败: {len(failed_symbols)} 个')
    
    if failed_symbols:
        print('\n失败的品种:')
        for symbol, name, error in failed_symbols[:20]:  # 只显示前20个
            print(f'  - {name} ({symbol}): {error}')
        if len(failed_symbols) > 20:
            print(f'  ... 还有 {len(failed_symbols) - 20} 个失败的品种')
        print('\n提示: 请检查网络连接和 akshare 库版本')
        print('      akshare 的 API 可能会更新，请查看最新文档')
        print('      某些品种可能不支持主力连续合约下载')
    else:
        print('\n✅ 所有数据下载成功！')

