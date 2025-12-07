"""
趋势成交量狙击手策略 (Trend Volume Sniper Strategy) - 逻辑修复版

保留了原有的日志打印模式，修复了入场逻辑死锁和条件过严的问题。
"""

import backtrader as bt
from typing import Optional


class TrendVolumeSniper(bt.Strategy):
    """
    趋势成交量狙击手策略类（双向交易 + 逻辑修复）
    """

    params = (
        ('trend_period', 60),
        ('vol_ma_period', 20),
        ('vol_multiplier', 1.2),  # [优化] 默认下调至 1.2
        ('atr_period', 14),
        ('stop_loss_atr_multiplier', 2.0),
        ('risk_per_trade', 0.02),
        ('breakout_period', 20),
        ('trailing_stop_atr_multiplier', 3.0),
        ('use_trailing_stop', True),
        ('volatility_threshold', 0.002),  # [新增] 波动率阈值 0.2%
        ('printlog', True),
    )

    def __init__(self) -> None:
        """初始化策略指标和状态变量"""
        # 价格数据
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.datavolume = self.datas[0].volume

        # 趋势均线
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

        # ATR 指标
        self.atr = bt.indicators.ATR(
            self.datas[0],
            period=self.params.atr_period,
            plotname='ATR'
        )

        # 支撑/阻力 (注意：回测时需取 [-1] 避免未来函数)
        self.highest_high = bt.indicators.Highest(
            self.datahigh,
            period=self.params.breakout_period,
            plotname='最高价'
        )

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
        self.position_direction: Optional[str] = None

        # 统计信息
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0

    def log(self, txt: str, dt=None) -> None:
        """
        日志记录函数 (保持原有格式)
        """
        if self.params.printlog:
            if dt is None:
                dt = self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')

    def notify_order(self, order: bt.Order) -> None:
        """订单状态通知 (保持原有格式)"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # 区分是做多入场还是平空
                if self.position.size > 0:  # 多单持仓中
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

                    # 初始止损
                    self.stop_loss_price = self.entry_price - (
                            self.atr[0] * self.params.stop_loss_atr_multiplier
                    )
                    self.trailing_stop_active = False

                    self.log(
                        f'止损设置 [做多] | 入场价: {self.entry_price:.2f} | '
                        f'止损价: {self.stop_loss_price:.2f} | '
                        f'ATR: {self.atr[0]:.2f}'
                    )
                else:  # 平空单
                    self.log(
                        f'CLOSE SHORT | 价格: {order.executed.price:.2f} | '
                        f'数量: {order.executed.size} | '
                        f'成本: {order.executed.value:.2f} | '
                        f'手续费: {order.executed.comm:.2f}'
                    )
                    self._reset_position_status()

            elif order.issell():
                # 区分是做空入场还是平多
                if self.position.size < 0:  # 空单持仓中
                    self.log(
                        f'SHORT ENTRY | 价格: {order.executed.price:.2f} | '
                        f'数量: {order.executed.size} | '
                        f'成本: {order.executed.value:.2f} | '
                        f'手续费: {order.executed.comm:.2f}'
                    )
                    self.entry_price = order.executed.price
                    self.position_direction = 'short'

                    # 初始止损
                    self.stop_loss_price = self.entry_price + (
                            self.atr[0] * self.params.stop_loss_atr_multiplier
                    )
                    self.trailing_stop_active = False

                    self.log(
                        f'止损设置 [做空] | 入场价: {self.entry_price:.2f} | '
                        f'止损价: {self.stop_loss_price:.2f} | '
                        f'ATR: {self.atr[0]:.2f}'
                    )
                else:  # 平多单
                    self.log(
                        f'CLOSE LONG | 价格: {order.executed.price:.2f} | '
                        f'数量: {order.executed.size} | '
                        f'成本: {order.executed.value:.2f} | '
                        f'手续费: {order.executed.comm:.2f}'
                    )
                    self._reset_position_status()

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单取消/保证金不足/拒绝')

        self.order = None

    def _reset_position_status(self):
        """重置持仓状态变量"""
        self.stop_loss_price = None
        self.entry_price = None
        self.position_direction = None
        self.trailing_stop_active = False

    def notify_trade(self, trade: bt.Trade) -> None:
        """交易通知 (保持原有格式)"""
        if not trade.isclosed:
            return

        self.trade_count += 1
        pnl = trade.pnl
        pnlcomm = trade.pnlcomm

        if pnlcomm > 0:
            self.win_count += 1
            self.log(f'交易盈利 | 盈亏: {pnl:.2f} | 扣除手续费后: {pnlcomm:.2f}')
        else:
            self.loss_count += 1
            self.log(f'交易亏损 | 盈亏: {pnl:.2f} | 扣除手续费后: {pnlcomm:.2f}')

    def calculate_position_size(self) -> int:
        """计算仓位大小"""
        if len(self.atr) == 0 or self.atr[0] == 0: return 0
        cash = self.broker.getcash()
        risk_amount = cash * self.params.risk_per_trade
        stop_loss_distance = self.atr[0] * self.params.stop_loss_atr_multiplier
        if stop_loss_distance == 0: return 0
        position_size = risk_amount / stop_loss_distance
        size = int(position_size)
        max_size = int(cash / self.dataclose[0])
        return max(0, min(size, max_size))

    def check_long_conditions(self) -> bool:
        """
        检查做多入场条件 (已修复逻辑)
        """
        # 数据量保护
        min_len = max(self.params.trend_period, self.params.breakout_period)
        if len(self.dataclose) < min_len: return False

        # 1. 波动率过滤 (新增)
        if self.dataclose[0] > 0:
            natr = self.atr[0] / self.dataclose[0]
            if natr < self.params.volatility_threshold:
                return False

        # 2. 趋势条件
        trend_condition = self.dataclose[0] > self.trend_ma[0]

        # 3. 突破条件 (修正: 必须比较前一根K线的最高价 [-1])
        breakout_condition = self.dataclose[0] > self.highest_high[-1]

        # 4. 成交量条件 (修正: 使用 OR 逻辑，最近3根有任意一根放量即可)
        threshold = self.volume_ma[0] * self.params.vol_multiplier
        # 保护防止索引越界
        if len(self.datavolume) < 3:
            volume_condition = self.datavolume[0] > threshold
        else:
            volume_condition = (
                    self.datavolume[0] > threshold or
                    self.datavolume[-1] > threshold or
                    self.datavolume[-2] > threshold
            )

        # 调试日志 (可选，保留原有的定期打印习惯)
        if self.params.printlog and len(self.dataclose) % 100 == 0:
            self.log(
                f'Check Long | Trend:{trend_condition} | Break:{breakout_condition} | Vol:{volume_condition}'
            )

        return trend_condition and breakout_condition and volume_condition

    def check_short_conditions(self) -> bool:
        """
        检查做空入场条件 (已修复逻辑)
        """
        min_len = max(self.params.trend_period, self.params.breakout_period)
        if len(self.dataclose) < min_len: return False

        # 1. 波动率过滤
        if self.dataclose[0] > 0:
            natr = self.atr[0] / self.dataclose[0]
            if natr < self.params.volatility_threshold:
                return False

        # 2. 趋势条件 (下跌)
        trend_condition = self.dataclose[0] < self.trend_ma[0]

        # 3. 突破条件 (修正: 比较前一根K线最低价 [-1])
        breakdown_condition = self.dataclose[0] < self.lowest_low[-1]

        # 4. 成交量条件 (修正: OR 逻辑)
        threshold = self.volume_ma[0] * self.params.vol_multiplier
        if len(self.datavolume) < 3:
            volume_condition = self.datavolume[0] > threshold
        else:
            volume_condition = (
                    self.datavolume[0] > threshold or
                    self.datavolume[-1] > threshold or
                    self.datavolume[-2] > threshold
            )

        return trend_condition and breakdown_condition and volume_condition

    def update_trailing_stop(self) -> None:
        """更新追踪止损 (保持原有逻辑)"""
        if not self.params.use_trailing_stop or not self.position: return
        if self.entry_price is None or self.position_direction is None: return

        atr_value = self.atr[0]
        if atr_value == 0: return

        # 做多追踪
        if self.position_direction == 'long':
            price_move = self.dataclose[0] - self.entry_price
            move_in_atr = price_move / atr_value

            if move_in_atr >= self.params.trailing_stop_atr_multiplier:
                if not self.trailing_stop_active:
                    self.trailing_stop_active = True
                    self.log(f'追踪止损激活 [做多] | 移动: {move_in_atr:.2f}ATR')

                new_stop = self.dataclose[0] - (self.atr[0] * self.params.stop_loss_atr_multiplier)
                if new_stop > self.stop_loss_price:
                    self.stop_loss_price = new_stop
                    self.log(f'追踪止损更新 [做多] | 新止损: {self.stop_loss_price:.2f}')

        # 做空追踪
        elif self.position_direction == 'short':
            price_move = self.entry_price - self.dataclose[0]
            move_in_atr = price_move / atr_value

            if move_in_atr >= self.params.trailing_stop_atr_multiplier:
                if not self.trailing_stop_active:
                    self.trailing_stop_active = True
                    self.log(f'追踪止损激活 [做空] | 移动: {move_in_atr:.2f}ATR')

                new_stop = self.dataclose[0] + (self.atr[0] * self.params.stop_loss_atr_multiplier)
                if new_stop < self.stop_loss_price:
                    self.stop_loss_price = new_stop
                    self.log(f'追踪止损更新 [做空] | 新止损: {self.stop_loss_price:.2f}')

    def check_stop_loss(self) -> bool:
        """检查止损 (保持原有逻辑)"""
        if not self.position or not self.stop_loss_price: return False

        if self.position_direction == 'long':
            if self.datalow[0] <= self.stop_loss_price: return True
        elif self.position_direction == 'short':
            if self.datahigh[0] >= self.stop_loss_price: return True
        return False

    def next(self) -> None:
        """策略主逻辑"""
        if self.order: return

        # 持仓管理
        if self.position:
            self.update_trailing_stop()

            # 止损触发
            if self.check_stop_loss():
                self.log(f'触发止损 | 价格: {self.stop_loss_price:.2f}')
                self.order = self.close()
                self._reset_position_status()
                return

            # 趋势反转退出
            if self.position_direction == 'long':
                if self.dataclose[0] < self.trend_ma[0]:
                    self.log(f'趋势反转退出 [做多] | Close < MA')
                    self.order = self.close()
                    self._reset_position_status()
            elif self.position_direction == 'short':
                if self.dataclose[0] > self.trend_ma[0]:
                    self.log(f'趋势反转退出 [做空] | Close > MA')
                    self.order = self.close()
                    self._reset_position_status()

        # 空仓开单
        else:
            # 检查做多
            if self.check_long_conditions():
                size = self.calculate_position_size()
                if size > 0:
                    self.log(f'满足做多条件 | 突破前高: {self.highest_high[-1]:.2f}')
                    self.order = self.buy(size=size)
                    return  # 避免同日反向信号

            # 检查做空
            if self.check_short_conditions():
                size = self.calculate_position_size()
                if size > 0:
                    self.log(f'满足做空条件 | 跌破前低: {self.lowest_low[-1]:.2f}')
                    self.order = self.sell(size=size)

    def stop(self) -> None:
        """回测结束统计"""
        total_return = (self.broker.getvalue() - self.broker.startingcash) / self.broker.startingcash * 100
        print('=' * 60)
        print('策略回测结果 - TrendVolumeSniper (修复版)')
        print('=' * 60)
        print(f'最终资金: {self.broker.getvalue():.2f}')
        print(f'总收益率: {total_return:.2f}%')
        print(f'交易次数: {self.trade_count}')
        if self.trade_count > 0:
            print(f'胜率: {self.win_count / self.trade_count * 100:.2f}%')
        print('=' * 60)