"""
趋势成交量狙击手策略 (Trend Volume Sniper Strategy)

策略逻辑（双向交易）：
做多条件：
1. 趋势条件：Close > Trend SMA (60周期)
2. 突破条件：Close > Highest High of last 20 bars
3. 成交量确认：Volume > Volume SMA * multiplier
4. 动态仓位：基于账户风险的2%计算仓位大小
5. ATR止损：严格的止损机制，可选追踪止损

做空条件：
1. 趋势条件：Close < Trend SMA (60周期)
2. 支撑位突破：Close < Lowest Low of last 20 bars
3. 成交量确认：Volume > Volume SMA * multiplier
4. 动态仓位：基于账户风险的2%计算仓位大小
5. ATR止损：严格的止损机制，可选追踪止损

退出条件：
- 做多：Close < Trend SMA（趋势反转）
- 做空：Close > Trend SMA（趋势反转）
- 止损触发（硬止损或追踪止损）
"""

import backtrader as bt
from typing import Optional


class TrendVolumeSniper(bt.Strategy):
    """
    趋势成交量狙击手策略类（双向交易）
    
    核心原则：
    - 只在趋势明确、突破确认且成交量放大时入场（做多或做空）
    - 基于账户风险的动态仓位管理
    - 使用 ATR 进行严格的止损控制
    - 支持追踪止损以保护利润
    - 支持做多和做空双向交易
    """
    
    params = (
        ('trend_period', 60),
        ('vol_ma_period', 20),
        ('vol_multiplier', 1.5),
        ('atr_period', 14),
        ('stop_loss_atr_multiplier', 2.0),
        ('risk_per_trade', 0.02),
        ('breakout_period', 20),
        ('trailing_stop_atr_multiplier', 3.0),
        ('use_trailing_stop', True),
        ('printlog', True),
    )
    
    def __init__(self) -> None:
        """
        初始化策略指标和状态变量
        """
        # 价格数据
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.datavolume = self.datas[0].volume
        
        # 趋势均线（主趋势）
        self.trend_ma = bt.indicators.SMA(
            self.dataclose,
            period=self.params.trend_period,
            plotname='趋势均线'
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SMA(
            self.datavolume,
            period=self.params.vol_ma_period,
            plotname='成交量均线'
        )
        
        # ATR 指标（用于止损和仓位计算）
        self.atr = bt.indicators.ATR(
            self.datas[0],
            period=self.params.atr_period,
            plotname='ATR'
        )
        
        # 最高价（用于突破检测）
        self.highest_high = bt.indicators.Highest(
            self.datahigh,
            period=self.params.breakout_period,
            plotname='最高价'
        )
        
        # 最低价（用于支撑位突破检测）
        self.lowest_low = bt.indicators.Lowest(
            self.datalow,
            period=self.params.breakout_period,
            plotname='最低价'
        )
        
        # 状态变量
        self.order: Optional[bt.Order] = None
        self.buyprice: Optional[float] = None
        self.buycomm: Optional[float] = None
        self.stop_loss_price: Optional[float] = None
        self.entry_price: Optional[float] = None
        self.trailing_stop_active: bool = False
        self.position_direction: Optional[str] = None  # 'long' 或 'short'
        
        # 统计信息
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
    
    def log(self, txt: str, dt=None) -> None:
        """
        日志记录函数
        
        Args:
            txt: 日志文本
            dt: 日期时间（可选）
        """
        if self.params.printlog:
            if dt is None:
                # 使用 Backtrader 的 datetime 获取当前日期
                dt = self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')
    
    def notify_order(self, order: bt.Order) -> None:
        """
        订单状态通知
        
        Args:
            order: 订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                # 做多入场
                self.log(
                    f'LONG ENTRY | 价格: {order.executed.price:.2f} | '
                    f'数量: {order.executed.size} | '
                    f'成本: {order.executed.value:.2f} | '
                    f'手续费: {order.executed.comm:.2f}'
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.entry_price = order.executed.price
                self.position_direction = 'long'
                
                # 设置初始止损价格（做多：入场价 - ATR * 倍数）
                self.stop_loss_price = self.entry_price - (
                    self.atr[0] * self.params.stop_loss_atr_multiplier
                )
                self.trailing_stop_active = False
                
                self.log(
                    f'止损设置 [做多] | 入场价: {self.entry_price:.2f} | '
                    f'止损价: {self.stop_loss_price:.2f} | '
                    f'ATR: {self.atr[0]:.2f}'
                )
            else:
                # 可能是做空入场或平仓
                if not self.position:
                    # 做空入场
                    self.log(
                        f'SHORT ENTRY | 价格: {order.executed.price:.2f} | '
                        f'数量: {order.executed.size} | '
                        f'成本: {order.executed.value:.2f} | '
                        f'手续费: {order.executed.comm:.2f}'
                    )
                    self.entry_price = order.executed.price
                    self.position_direction = 'short'
                    
                    # 设置初始止损价格（做空：入场价 + ATR * 倍数）
                    self.stop_loss_price = self.entry_price + (
                        self.atr[0] * self.params.stop_loss_atr_multiplier
                    )
                    self.trailing_stop_active = False
                    
                    self.log(
                        f'止损设置 [做空] | 入场价: {self.entry_price:.2f} | '
                        f'止损价: {self.stop_loss_price:.2f} | '
                        f'ATR: {self.atr[0]:.2f}'
                    )
                else:
                    # 平仓
                    self.log(
                        f'平仓执行 | 价格: {order.executed.price:.2f} | '
                        f'数量: {order.executed.size} | '
                        f'成本: {order.executed.value:.2f} | '
                        f'手续费: {order.executed.comm:.2f}'
                    )
                    # 重置状态
                    self.stop_loss_price = None
                    self.entry_price = None
                    self.position_direction = None
                    self.trailing_stop_active = False
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')
        
        self.order = None
    
    def notify_trade(self, trade: bt.Trade) -> None:
        """
        交易通知
        
        Args:
            trade: 交易对象
        """
        if not trade.isclosed:
            return
        
        self.trade_count += 1
        pnl = trade.pnl
        pnlcomm = trade.pnlcomm
        
        if pnlcomm > 0:
            self.win_count += 1
            self.log(
                f'交易盈利 | 盈亏: {pnl:.2f} | '
                f'扣除手续费后: {pnlcomm:.2f}'
            )
        else:
            self.loss_count += 1
            self.log(
                f'交易亏损 | 盈亏: {pnl:.2f} | '
                f'扣除手续费后: {pnlcomm:.2f}'
            )
    
    def calculate_position_size(self) -> int:
        """
        计算仓位大小
        
        基于账户风险的动态仓位计算：
        size = (Cash * risk_per_trade) / (ATR * stop_loss_atr_multiplier)
        
        Returns:
            int: 仓位大小（手数）
        """
        if len(self.atr) == 0 or self.atr[0] == 0:
            return 0
        
        # 获取可用资金
        cash = self.broker.getcash()
        
        # 计算风险金额
        risk_amount = cash * self.params.risk_per_trade
        
        # 计算每手的风险（止损距离）
        stop_loss_distance = self.atr[0] * self.params.stop_loss_atr_multiplier
        
        if stop_loss_distance == 0:
            return 0
        
        # 计算仓位大小
        position_size = risk_amount / stop_loss_distance
        
        # 转换为整数手数
        size = int(position_size)
        
        # 确保不超过可用资金
        max_size = int(cash / self.dataclose[0])
        size = min(size, max_size)
        
        return max(0, size)
    
    def check_long_conditions(self) -> bool:
        """
        检查做多入场条件
        
        条件：
        1. Close > Trend SMA
        2. Close > Highest High of last 20 bars (突破)
        3. Volume > Volume SMA * vol_multiplier
        
        Returns:
            bool: 是否满足做多入场条件
        """
        # 确保有足够的数据
        min_period = max(
            self.params.trend_period,
            self.params.vol_ma_period,
            self.params.atr_period,
            self.params.breakout_period
        )
        
        if len(self.dataclose) < min_period:
            if self.params.printlog and len(self.dataclose) == min_period - 1:
                # 只在第一次达到最小周期时打印一次
                self.log(f'数据量不足，需要至少 {min_period} 个数据点，当前: {len(self.dataclose)}')
            return False
        
        # 条件1：趋势条件 - 收盘价 > 趋势均线
        trend_condition = self.dataclose[0] > self.trend_ma[0]
        
        # 条件2：突破条件 - 收盘价 > 最近N根K线的最高价
        breakout_condition = self.dataclose[0] > self.highest_high[0]
        
        # 条件3：成交量条件 - 最近3根K线的成交量都 > 成交量均线 * 倍数
        volume_threshold = self.volume_ma[0] * self.params.vol_multiplier
        # 检查当前bar和前两个bar的成交量
        if len(self.datavolume) < 3:
            volume_condition = self.datavolume[0] > volume_threshold
        else:
            volume_condition = (
                self.datavolume[0] > volume_threshold and
                self.datavolume[-1] > volume_threshold and
                self.datavolume[-2] > volume_threshold
            )
        
        # 调试信息：定期输出条件检查结果（每100个bar输出一次）
        if self.params.printlog and len(self.dataclose) % 100 == 0:
            self.log(
                f'入场条件检查 | '
                f'趋势: {trend_condition} ({self.dataclose[0]:.2f} vs {self.trend_ma[0]:.2f}) | '
                f'突破: {breakout_condition} ({self.dataclose[0]:.2f} vs {self.highest_high[0]:.2f}) | '
                f'成交量: {volume_condition} ({self.datavolume[0]:.0f} vs {volume_threshold:.0f})'
            )
        
        return trend_condition and breakout_condition and volume_condition
    
    def check_short_conditions(self) -> bool:
        """
        检查做空入场条件
        
        条件：
        1. Close < Trend SMA (下跌趋势)
        2. Close < Lowest Low of last 20 bars (支撑位突破)
        3. Volume > Volume SMA * vol_multiplier (成交量确认)
        
        Returns:
            bool: 是否满足做空入场条件
        """
        # 确保有足够的数据
        min_period = max(
            self.params.trend_period,
            self.params.vol_ma_period,
            self.params.atr_period,
            self.params.breakout_period
        )
        
        if len(self.dataclose) < min_period:
            return False
        
        # 条件A：下跌趋势 - 收盘价 < 趋势均线
        trend_condition = self.dataclose[0] < self.trend_ma[0]
        
        # 条件B：支撑位突破 - 收盘价 < 最近N根K线的最低价
        breakdown_condition = self.dataclose[0] < self.lowest_low[-1]
        
        # 条件C：成交量条件 - 最近3根K线的成交量都 > 成交量均线 * 倍数
        volume_threshold = self.volume_ma[0] * self.params.vol_multiplier
        # 检查当前bar和前两个bar的成交量
        if len(self.datavolume) < 3:
            volume_condition = self.datavolume[0] > volume_threshold
        else:
            volume_condition = (
                self.datavolume[0] > volume_threshold and
                self.datavolume[-1] > volume_threshold and
                self.datavolume[-2] > volume_threshold
            )
        
        # 调试信息：定期输出条件检查结果（每100个bar输出一次）
        if self.params.printlog and len(self.dataclose) % 100 == 0:
            self.log(
                f'做空条件检查 | '
                f'趋势: {trend_condition} ({self.dataclose[0]:.2f} vs {self.trend_ma[0]:.2f}) | '
                f'突破: {breakdown_condition} ({self.dataclose[0]:.2f} vs {self.lowest_low[-1]:.2f}) | '
                f'成交量: {volume_condition} ({self.datavolume[0]:.0f} vs {volume_threshold:.0f})'
            )
        
        return trend_condition and breakdown_condition and volume_condition
    
    def update_trailing_stop(self) -> None:
        """
        更新追踪止损
        
        如果价格有利移动超过指定倍数的ATR，启用追踪止损
        支持做多和做空双向追踪止损
        """
        if not self.params.use_trailing_stop or not self.position:
            return
        
        if self.entry_price is None or self.position_direction is None:
            return
        
        atr_value = self.atr[0]
        if atr_value == 0:
            return
        
        # 计算价格从入场价的移动距离（以ATR为单位）
        if self.position_direction == 'long':
            price_move = self.dataclose[0] - self.entry_price
            move_in_atr = price_move / atr_value
            
            # 如果价格有利移动超过指定倍数，启用追踪止损
            if move_in_atr >= self.params.trailing_stop_atr_multiplier:
                if not self.trailing_stop_active:
                    self.trailing_stop_active = True
                    self.log(
                        f'追踪止损激活 [做多] | 价格移动: {move_in_atr:.2f}倍ATR | '
                        f'当前价: {self.dataclose[0]:.2f} | '
                        f'入场价: {self.entry_price:.2f}'
                    )
                
                # 更新追踪止损价格（跟随价格上涨）
                new_stop = self.dataclose[0] - (
                    self.atr[0] * self.params.stop_loss_atr_multiplier
                )
                
                # 追踪止损只能向上移动，不能向下
                if new_stop > self.stop_loss_price:
                    old_stop = self.stop_loss_price
                    self.stop_loss_price = new_stop
                    self.log(
                        f'追踪止损更新 [做多] | 旧止损: {old_stop:.2f} | '
                        f'新止损: {self.stop_loss_price:.2f} | '
                        f'当前价: {self.dataclose[0]:.2f}'
                    )
        
        elif self.position_direction == 'short':
            price_move = self.entry_price - self.dataclose[0]  # 做空时，价格下跌是盈利
            move_in_atr = price_move / atr_value
            
            # 如果价格有利移动超过指定倍数，启用追踪止损
            if move_in_atr >= self.params.trailing_stop_atr_multiplier:
                if not self.trailing_stop_active:
                    self.trailing_stop_active = True
                    self.log(
                        f'追踪止损激活 [做空] | 价格移动: {move_in_atr:.2f}倍ATR | '
                        f'当前价: {self.dataclose[0]:.2f} | '
                        f'入场价: {self.entry_price:.2f}'
                    )
                
                # 更新追踪止损价格（跟随价格下跌）
                new_stop = self.dataclose[0] + (
                    self.atr[0] * self.params.stop_loss_atr_multiplier
                )
                
                # 追踪止损只能向下移动（做空时止损价降低），不能向上
                if new_stop < self.stop_loss_price:
                    old_stop = self.stop_loss_price
                    self.stop_loss_price = new_stop
                    self.log(
                        f'追踪止损更新 [做空] | 旧止损: {old_stop:.2f} | '
                        f'新止损: {self.stop_loss_price:.2f} | '
                        f'当前价: {self.dataclose[0]:.2f}'
                    )
    
    def check_stop_loss(self) -> bool:
        """
        检查止损条件
        
        支持做多和做空双向止损
        
        Returns:
            bool: 是否需要止损
        """
        if not self.position or not self.stop_loss_price or not self.position_direction:
            return False
        
        if self.position_direction == 'long':
            # 做多：如果当前最低价触及止损价，执行止损
            if self.datalow[0] <= self.stop_loss_price:
                return True
        elif self.position_direction == 'short':
            # 做空：如果当前最高价触及止损价，执行止损
            if self.datahigh[0] >= self.stop_loss_price:
                return True
        
        return False
    
    def next(self) -> None:
        """
        策略主逻辑，每个 bar 都会调用
        支持做多和做空双向交易
        """
        # 如果有未完成的订单，不执行新逻辑
        if self.order:
            return
        
        # 如果已持仓，更新追踪止损并检查止损和趋势反转
        if self.position:
            # 更新追踪止损
            self.update_trailing_stop()
            
            # 检查止损
            if self.check_stop_loss():
                direction_str = "做多" if self.position_direction == 'long' else "做空"
                self.log(
                    f'触发止损 [{direction_str}] | 止损价: {self.stop_loss_price:.2f} | '
                    f'当前价: {self.dataclose[0]:.2f} | '
                    f'类型: {"追踪止损" if self.trailing_stop_active else "硬止损"}'
                )
                self.order = self.close()
                self.stop_loss_price = None
                self.entry_price = None
                self.position_direction = None
                self.trailing_stop_active = False
                return
            
            # 检查趋势反转退出条件
            if self.position_direction == 'long':
                # 做多：如果收盘价 < 趋势均线，平仓
                if self.dataclose[0] < self.trend_ma[0]:
                    self.log(
                        f'趋势反转退出 [做多] | 收盘价: {self.dataclose[0]:.2f} | '
                        f'趋势均线: {self.trend_ma[0]:.2f}'
                    )
                    self.order = self.close()
                    self.stop_loss_price = None
                    self.entry_price = None
                    self.position_direction = None
                    self.trailing_stop_active = False
                    return
            elif self.position_direction == 'short':
                # 做空：如果收盘价 > 趋势均线，平仓
                if self.dataclose[0] > self.trend_ma[0]:
                    self.log(
                        f'趋势反转退出 [做空] | 收盘价: {self.dataclose[0]:.2f} | '
                        f'趋势均线: {self.trend_ma[0]:.2f}'
                    )
                    self.order = self.close()
                    self.stop_loss_price = None
                    self.entry_price = None
                    self.position_direction = None
                    self.trailing_stop_active = False
                    return
        else:
            # 未持仓，检查入场条件
            # 检查做多条件
            if self.check_long_conditions():
                # 计算仓位大小
                size = self.calculate_position_size()
                
                if size > 0:
                    self.log(
                        f'满足做多入场条件 | '
                        f'收盘价: {self.dataclose[0]:.2f} | '
                        f'趋势均线: {self.trend_ma[0]:.2f} | '
                        f'最高价: {self.highest_high[0]:.2f} | '
                        f'成交量: {self.datavolume[0]:.0f} | '
                        f'成交量阈值: {self.volume_ma[0] * self.params.vol_multiplier:.0f} | '
                        f'ATR: {self.atr[0]:.2f}'
                    )
                    self.order = self.buy(size=size)
                    self.log(
                        f'下单做多 | 数量: {size}手 | '
                        f'预计入场价: {self.dataclose[0]:.2f} | '
                        f'预计止损价: {self.dataclose[0] - (self.atr[0] * self.params.stop_loss_atr_multiplier):.2f}'
                    )
                    return
            
            # 检查做空条件
            if self.check_short_conditions():
                # 计算仓位大小
                size = self.calculate_position_size()
                
                if size > 0:
                    self.log(
                        f'满足做空入场条件 | '
                        f'收盘价: {self.dataclose[0]:.2f} | '
                        f'趋势均线: {self.trend_ma[0]:.2f} | '
                        f'最低价: {self.lowest_low[-1]:.2f} | '
                        f'成交量: {self.datavolume[0]:.0f} | '
                        f'成交量阈值: {self.volume_ma[0] * self.params.vol_multiplier:.0f} | '
                        f'ATR: {self.atr[0]:.2f}'
                    )
                    self.order = self.sell(size=size)
                    self.log(
                        f'下单做空 | 数量: {size}手 | '
                        f'预计入场价: {self.dataclose[0]:.2f} | '
                        f'预计止损价: {self.dataclose[0] + (self.atr[0] * self.params.stop_loss_atr_multiplier):.2f}'
                    )
    
    def stop(self) -> None:
        """
        策略结束时的统计信息输出
        """
        total_return = (
            (self.broker.getvalue() - self.broker.startingcash) / 
            self.broker.startingcash * 100
        )
        
        print('=' * 60)
        print('策略回测结果 - TrendVolumeSniper')
        print('=' * 60)
        print(f'初始资金: {self.broker.startingcash:.2f}')
        print(f'最终资金: {self.broker.getvalue():.2f}')
        print(f'总收益率: {total_return:.2f}%')
        print(f'总交易次数: {self.trade_count}')
        print(f'盈利次数: {self.win_count}')
        print(f'亏损次数: {self.loss_count}')
        if self.trade_count > 0:
            win_rate = self.win_count / self.trade_count * 100
            print(f'胜率: {win_rate:.2f}%')
        print('=' * 60)

