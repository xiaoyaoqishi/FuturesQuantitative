# 趋势跟踪期货交易系统验证实验室

基于 Backtrader 的趋势跟踪期货交易系统，专注于单一资产的深度验证和逻辑稳健性测试。

## 项目理念

### 1. 趋势狙击手 (Trend Sniper)
- **入场条件**：价格 > 趋势均线 **且** 成交量 > 成交量均线 × 倍数
- **突破确认**：价格突破最近 N 根 K 线的最高价
- 只在趋势明确、突破确认且成交量放大时入场，避免假突破

### 2. 反脆弱性 (Anti-Fragile)
- **生存第一**：严格的 ATR 止损机制
- **动态仓位管理**：基于账户风险的 2% 风险控制
- **追踪止损**：价格有利移动后启用追踪止损，保护利润
- 资金管理和风险控制优先于利润最大化
- **优化目标**：最大化夏普比率而非单纯的总利润

### 3. 单一资产聚焦
- 系统设计用于深度测试特定资产（如焦煤、锂等）
- 不是用于扫描数千只股票的通用系统
- 专注于单一资产的策略验证和参数优化

### 4. 验证优先于利润
- 目标是验证逻辑的稳健性
- 通过回测验证策略在不同市场环境下的表现
- 关注风险指标（最大回撤、夏普比率等）而不仅仅是总收益
- 使用参数优化寻找风险调整后收益最优的参数组合

## 技术栈

- **Python 3.9+**
- **Backtrader** - 回测引擎
- **Pandas** - 数据处理
- **Matplotlib** - 可视化
- **NumPy** - 数值计算（数据生成）

## 项目结构

```
FuturesQuantitative/
├── strategy.py              # TrendVolumeSniper 策略（主策略）
├── data_loader.py           # 数据加载器（根目录，灵活列映射）
├── main.py                  # 主程序入口（回测执行）
├── optimize.py              # 参数优化脚本（网格搜索）
├── example.py               # 示例脚本
├── requirements.txt         # 依赖包
├── README.md               # 项目说明
├── .gitignore              # Git 忽略文件
│
├── strategies/             # 策略模块（旧版策略）
│   ├── __init__.py
│   └── trend_sniper.py     # TrendSniperStrategy（原始策略）
│
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── data_loader.py      # DataLoader 类（数据加载工具）
│   └── visualizer.py       # 可视化工具
│
├── backtest/               # 回测模块
│   ├── __init__.py
│   └── engine.py          # BacktestEngine 类
│
├── data/                   # 数据目录
│   └── .gitkeep
│
└── results/                # 结果目录（图表输出）
    └── .gitkeep
```

## 安装

1. **克隆或下载项目**

2. **安装依赖**：
```bash
pip install -r requirements.txt
```

依赖包包括：
- `backtrader==1.9.78.123` - 回测引擎
- `pandas>=1.5.0` - 数据处理
- `matplotlib>=3.6.0` - 可视化
- `numpy>=1.23.0` - 数值计算

## 核心模块说明

### 1. strategy.py - TrendVolumeSniper 策略

**主要策略类**，实现趋势成交量狙击手逻辑。

#### 策略参数：
- `trend_period` (默认 60): 主趋势均线周期
- `vol_ma_period` (默认 20): 成交量均线周期
- `vol_multiplier` (默认 1.5): 成交量倍数阈值
- `atr_period` (默认 14): ATR 计算周期
- `stop_loss_atr_multiplier` (默认 2.0): 止损 ATR 倍数
- `risk_per_trade` (默认 0.02): 每笔交易的风险（账户的 2%）
- `breakout_period` (默认 20): 突破检测周期
- `trailing_stop_atr_multiplier` (默认 3.0): 追踪止损触发倍数
- `use_trailing_stop` (默认 True): 是否使用追踪止损
- `printlog` (默认 True): 是否打印交易日志

#### 入场条件（三个条件同时满足）：
1. **趋势条件**：`Close > Trend SMA (60周期)`
2. **突破条件**：`Close > Highest High of last 20 bars`
3. **成交量确认**：`Volume > Volume SMA × vol_multiplier`

#### 仓位管理：
动态计算仓位大小：
```python
size = (Cash × risk_per_trade) / (ATR × stop_loss_atr_multiplier)
```
确保每笔交易风险控制在账户的 2%。

#### 止损机制：
- **硬止损**：入场价 - (ATR × 2.0)
- **追踪止损**：价格有利移动超过 3 倍 ATR 后启用，止损价跟随价格上涨

### 2. data_loader.py - 数据加载器

**灵活的数据加载函数**，支持自动列名检测和自定义映射。

#### 主要函数：
```python
get_pandas_data(
    filepath: Union[str, Path],
    datetime_column: Optional[str] = None,
    date_format: Optional[str] = None,
    column_mapping: Optional[Dict[str, str]] = None
) -> bt.feeds.PandasData
```

#### 特性：
- ✅ 自动检测常见列名变体（Date/date/DATE, Open/open/OPEN 等）
- ✅ 支持中文列名（日期、开盘价、最高价等）
- ✅ 灵活的日期格式解析
- ✅ 自定义列映射
- ✅ 数据验证和清洗

#### 使用示例：
```python
from data_loader import get_pandas_data

# 自动检测列名
data = get_pandas_data('data/futures.csv')

# 自定义列映射
data = get_pandas_data(
    'data/futures.csv',
    column_mapping={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }
)

# 中文列名
data = get_pandas_data(
    'data/futures.csv',
    datetime_column='日期',
    column_mapping={
        'open': '开盘价',
        'high': '最高价',
        'low': '最低价',
        'close': '收盘价',
        'volume': '成交量'
    }
)
```

### 3. main.py - 回测主程序

**执行策略回测并输出详细报告**。

#### 功能：
- 初始化 Cerebro 回测引擎
- 加载数据（自动创建示例数据如果不存在）
- 添加 TrendVolumeSniper 策略
- 添加分析器（SharpeRatio, DrawDown, TradeAnalyzer）
- 输出性能报告
- 显示可视化图表

#### 使用方法：
```bash
python main.py
```

#### 输出内容：
- 资金情况（初始资金、最终资金、总收益率）
- 风险指标（夏普比率、最大回撤）
- 交易统计（总交易次数、盈利/亏损交易、胜率、平均盈亏）
- 可视化图表（K线图、指标、买卖点）

### 4. optimize.py - 参数优化脚本

**使用网格搜索进行参数优化**，寻找最优参数组合。

#### 优化空间：
- `trend_period`: `range(20, 100, 10)` → [20, 30, 40, 50, 60, 70, 80, 90]
- `vol_multiplier`: [1.2, 1.5, 2.0]
- 总组合数：8 × 3 = 24 个参数组合

#### 优化目标：
**最大化夏普比率**（符合"反脆弱"理念，优先考虑风险调整后的收益）

#### 使用方法：
```bash
python optimize.py
```

#### 特性：
- ✅ 使用 `cerebro.optstrategy()` 进行网格搜索
- ✅ 多进程并行优化（自动使用所有可用 CPU）
- ✅ 按夏普比率排序结果
- ✅ 输出 Top 5 参数组合
- ✅ 显示详细的性能指标

#### 输出示例：
```
================================================================================
优化结果 - Top 5 参数组合（按夏普比率排序）
================================================================================
排名    趋势周期    成交量倍数    夏普比率      最大回撤(%)     总收益率(%)     胜率(%)     交易次数    
--------------------------------------------------------------------------------
1       60          1.50         1.2345        5.67           15.23          60.00       25
2       50          1.50         1.1890        6.12           14.56          58.33       24
...
```

## 使用方法

### 1. 准备数据

数据文件应为 CSV 格式，包含以下列：
- `Date` 或 `date` 或 `datetime`: 日期时间
- `Open` 或 `open`: 开盘价
- `High` 或 `high`: 最高价
- `Low` 或 `low`: 最低价
- `Close` 或 `close`: 收盘价
- `Volume` 或 `volume`: 成交量

#### 示例数据格式：
```csv
Date,Open,High,Low,Close,Volume
2020-01-01,100.0,102.0,99.0,101.0,1000000
2020-01-02,101.0,103.0,100.0,102.5,1200000
2020-01-03,102.5,104.0,101.5,103.5,1500000
...
```

**注意**：`data_loader.py` 支持多种列名格式，会自动检测。如果数据文件不存在，`main.py` 会自动创建示例数据。

### 2. 运行回测

#### 基本用法：
```bash
python main.py
```

程序会自动：
1. 检查数据文件是否存在（`data/futures_data.csv`）
2. 如果不存在，自动创建示例数据
3. 加载数据并运行回测
4. 输出详细的性能报告
5. 显示可视化图表

### 3. 运行参数优化

```bash
python optimize.py
```

优化脚本会：
1. 测试所有参数组合（24 个组合）
2. 使用多进程加速（自动使用所有 CPU）
3. 按夏普比率排序结果
4. 输出 Top 5 参数组合的详细报告

### 4. 使用示例脚本

```bash
python example.py
```

示例脚本演示了如何使用系统的各个模块。

## 策略逻辑详解

### TrendVolumeSniper 策略

#### 入场条件（三个条件同时满足）：

1. **趋势确认**：
   ```
   Close > Trend SMA (trend_period 周期，默认 60)
   ```
   确保在上升趋势中交易

2. **突破确认**：
   ```
   Close > Highest High of last N bars (breakout_period，默认 20)
   ```
   确认价格突破近期高点，避免在震荡市场中交易

3. **成交量确认**：
   ```
   Volume > Volume SMA (vol_ma_period) × vol_multiplier
   ```
   确保有足够的成交量支撑，避免假突破

#### 仓位管理：

**动态仓位计算**，基于账户风险：
```python
风险金额 = 账户资金 × risk_per_trade (默认 2%)
止损距离 = ATR × stop_loss_atr_multiplier (默认 2.0)
仓位大小 = 风险金额 / 止损距离
```

这确保了每笔交易的风险都控制在账户的 2%，符合"反脆弱"理念。

#### 止损机制：

1. **硬止损**：
   - 初始止损：`入场价 - (ATR × stop_loss_atr_multiplier)`
   - 如果价格触及止损价，立即平仓

2. **追踪止损**（可选）：
   - 触发条件：价格从入场价有利移动超过 `trailing_stop_atr_multiplier` 倍 ATR（默认 3.0）
   - 行为：止损价跟随价格上涨，保护利润
   - 特点：只能向上移动，不能向下

#### 出场条件：

- 触发止损（硬止损或追踪止损）
- 价格跌破趋势均线（可选，当前版本未实现）

## 输出结果

### 回测报告（main.py）

回测完成后会输出：

#### 1. 资金情况
- 初始资金
- 最终资金
- 总收益率（百分比）

#### 2. 风险指标
- **夏普比率**：风险调整后的收益指标（越高越好）
- **最大回撤**：最大资金回撤百分比（越低越好）

#### 3. 交易统计
- 总交易次数
- 盈利交易次数
- 亏损交易次数
- **胜率**：盈利交易 / 总交易 × 100%
- 总盈亏
- 平均盈利金额
- 平均亏损金额

#### 4. 可视化图表
- K线图（蜡烛图）
- 趋势均线
- 成交量柱状图
- 买卖点标记
- ATR 指标

### 优化报告（optimize.py）

优化完成后会输出：

#### 1. Top 5 参数组合表格
包含以下列：
- 排名
- 趋势周期
- 成交量倍数
- 夏普比率（排序依据）
- 最大回撤（%）
- 总收益率（%）
- 胜率（%）
- 交易次数

#### 2. 最佳参数组合详情
- 参数值
- 性能指标（夏普比率、最大回撤、总收益率、胜率、交易次数、最终资金）

## 代码特点

- ✅ **模块化设计**：策略、数据、回测引擎分离，易于维护和扩展
- ✅ **类型提示**：完整的类型注解，提高代码可读性
- ✅ **PEP 8 规范**：符合 Python 编码规范
- ✅ **详细注释**：中文注释，易于理解
- ✅ **错误处理**：完善的异常处理机制
- ✅ **灵活配置**：支持多种参数组合和自定义设置
- ✅ **性能优化**：多进程并行优化，提高效率

## 注意事项

1. **数据质量**：
   - 确保数据准确完整，缺失数据会影响回测结果
   - 数据应按日期排序
   - 建议使用至少 1-2 年的历史数据

2. **参数调优**：
   - 不同资产可能需要不同的参数设置
   - 使用 `optimize.py` 进行参数优化
   - 注意避免过度拟合（过拟合）

3. **手续费设置**：
   - 根据实际交易成本调整手续费率
   - 默认设置为 0.1%（0.001）
   - 期货交易可能需要调整

4. **滑点影响**：
   - 系统默认设置 0.1% 滑点
   - 可根据实际情况调整
   - 滑点会影响回测结果的准确性

5. **单一资产测试**：
   - 本系统专注于单一资产的深度验证
   - 不适合多资产组合回测
   - 每个资产应单独优化参数

6. **优化注意事项**：
   - 参数优化可能需要较长时间（取决于数据量和参数组合数）
   - 建议先用小数据集测试
   - 优化结果应在样本外数据上验证

## 扩展开发

### 添加新策略

1. 创建新的策略文件（如 `my_strategy.py`）
2. 继承 `bt.Strategy` 类
3. 实现 `__init__()` 和 `next()` 方法
4. 在 `main.py` 中导入并使用：

```python
from my_strategy import MyStrategy

cerebro.addstrategy(MyStrategy, param1=value1, param2=value2)
```

### 添加新指标

在策略的 `__init__()` 方法中添加 Backtrader 指标：

```python
def __init__(self):
    # 现有指标...
    
    # 添加自定义指标
    self.custom_indicator = bt.indicators.YourIndicator(
        self.dataclose,
        period=20
    )
```

### 自定义数据加载

如果需要处理特殊格式的数据，可以扩展 `data_loader.py`：

```python
def load_custom_data(filepath):
    # 自定义加载逻辑
    df = pd.read_csv(filepath)
    # 数据处理...
    return bt.feeds.PandasData(dataname=df, ...)
```

### 添加新的分析器

在回测脚本中添加 Backtrader 分析器：

```python
import backtrader.analyzers as btanalyzers

cerebro.addanalyzer(btanalyzers.SQN, _name='sqn')  # 系统质量指标
cerebro.addanalyzer(btanalyzers.Calmar, _name='calmar')  # 卡尔玛比率
```

## 文件说明

### 核心文件

- **strategy.py**: TrendVolumeSniper 策略实现（主策略）
- **data_loader.py**: 灵活的数据加载函数（根目录）
- **main.py**: 回测主程序
- **optimize.py**: 参数优化脚本

### 模块文件

- **strategies/trend_sniper.py**: TrendSniperStrategy（原始策略，保留兼容性）
- **utils/data_loader.py**: DataLoader 类（工具类）
- **utils/visualizer.py**: 可视化工具
- **backtest/engine.py**: BacktestEngine 类（回测引擎封装）

### 辅助文件

- **example.py**: 示例脚本
- **requirements.txt**: 依赖包列表
- **.gitignore**: Git 忽略文件

## 常见问题

### Q: 如何修改初始资金？
A: 在 `main.py` 中修改 `initial_cash` 变量，或在 `optimize.py` 中修改。

### Q: 如何调整手续费？
A: 修改 `cerebro.broker.setcommission(commission=0.001)` 中的值。

### Q: 优化需要多长时间？
A: 取决于数据量、参数组合数和 CPU 性能。24 个组合通常需要几分钟到几十分钟。

### Q: 如何添加新的优化参数？
A: 在 `optimize.py` 的 `cerebro.optstrategy()` 中添加参数列表，例如：
```python
cerebro.optstrategy(
    TrendVolumeSniper,
    trend_period=trend_periods,
    vol_multiplier=vol_multipliers,
    atr_period=[10, 14, 20],  # 新增参数
    ...
)
```

### Q: 数据文件格式要求？
A: CSV 格式，包含 Date/Open/High/Low/Close/Volume 列（大小写不敏感）。`data_loader.py` 会自动检测。

## 许可证

本项目仅供学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0 (最新)
- ✅ 实现 TrendVolumeSniper 策略
- ✅ 添加灵活的数据加载器（支持自动列名检测）
- ✅ 实现参数优化脚本（网格搜索）
- ✅ 完善回测报告输出
- ✅ 支持多进程优化
- ✅ 添加追踪止损功能
- ✅ 动态仓位管理（基于风险）

### 未来计划
- [ ] 添加更多策略变体
- [ ] 支持多时间框架分析
- [ ] 添加实时数据接口
- [ ] 优化可视化功能
- [ ] 添加回测结果导出功能
