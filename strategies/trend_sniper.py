"""
趋势狙击手策略 (Trend Sniper Strategy)

策略逻辑：
1. 趋势条件：Price > Trend_MA 时考虑做多
2. 成交量条件：Volume > Volume_MA * multiplier 时确认入场
3. 止损：基于 ATR 的严格止损，确保生存第一
4. 反脆弱性：严格的资金管理和风险控制
"""

import backtrader as bt
from typing import Optional


class TrendSniperStrategy(bt.Strategy):
    """
    趋势狙击手策略类
    
    核心原则：
    - 只在趋势明确且成交量确认时入场
    - 使用 ATR 进行动态止损
    - 单一资产深度测试
    """
    
    params = (
        ('trend_ma_period', 20),
        ('volume_ma_period', 20),
        ('volume_multiplier', 1.5),
        ('atr_period', 14),
        ('atr_stop_multiplier', 2.0),
        ('position_size', 0.95),
        ('printlog', False),
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
        
        # 趋势均线
        self.trend_ma = bt.indicators.SMA(
            self.dataclose,
            period=self.params.trend_ma_period,
            plotname='趋势均线'
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SMA(
            self.datavolume,
            period=self.params.volume_ma_period,
            plotname='成交量均线'
        )
        
        # ATR 指标（用于止损）
        self.atr = bt.indicators.ATR(
            self.datas[0],
            period=self.params.atr_period,
            plotname='ATR'
        )
        
        # 状态变量
        self.order: Optional[bt.Order] = None
        self.buyprice: Optional[float] = None
        self.buycomm: Optional[float] = None
        self.stop_loss_price: Optional[float] = None
        
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
                self.log(
                    f'买入执行, 价格: {order.executed.price:.2f}, '
                    f'成本: {order.executed.value:.2f}, '
                    f'手续费: {order.executed.comm:.2f}'
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                # 设置止损价格
                self.stop_loss_price = self.buyprice - (
                    self.atr[0] * self.params.atr_stop_multiplier
                )
            else:
                self.log(
                    f'卖出执行, 价格: {order.executed.price:.2f}, '
                    f'成本: {order.executed.value:.2f}, '
                    f'手续费: {order.executed.comm:.2f}'
                )
        
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
            self.log(f'交易盈利: {pnl:.2f}, 扣除手续费后: {pnlcomm:.2f}')
        else:
            self.loss_count += 1
            self.log(f'交易亏损: {pnl:.2f}, 扣除手续费后: {pnlcomm:.2f}')
    
    def check_stop_loss(self) -> bool:
        """
        检查止损条件
        
        Returns:
            bool: 是否需要止损
        """
        if self.position and self.stop_loss_price:
            # 如果当前最低价触及止损价，执行止损
            if self.datalow[0] <= self.stop_loss_price:
                return True
        return False
    
    def check_entry_conditions(self) -> bool:
        """
        检查入场条件
        
        条件：
        1. 价格 > 趋势均线
        2. 成交量 > 成交量均线 * 倍数
        
        Returns:
            bool: 是否满足入场条件
        """
        # 确保有足够的数据
        if len(self.dataclose) < max(
            self.params.trend_ma_period,
            self.params.volume_ma_period,
            self.params.atr_period
        ):
            return False
        
        # 趋势条件：价格 > 趋势均线
        trend_condition = self.dataclose[0] > self.trend_ma[0]
        
        # 成交量条件：成交量 > 成交量均线 * 倍数
        volume_threshold = self.volume_ma[0] * self.params.volume_multiplier
        volume_condition = self.datavolume[0] > volume_threshold
        
        return trend_condition and volume_condition
    
    def next(self) -> None:
        """
        策略主逻辑，每个 bar 都会调用
        """
        # 如果有未完成的订单，不执行新逻辑
        if self.order:
            return
        
        # 检查止损
        if self.check_stop_loss():
            self.log(f'触发止损，价格: {self.stop_loss_price:.2f}')
            self.order = self.close()
            self.stop_loss_price = None
            return
        
        # 如果已持仓，检查是否应该平仓
        if self.position:
            # 如果价格跌破趋势均线，平仓
            if self.dataclose[0] < self.trend_ma[0]:
                self.log('价格跌破趋势均线，平仓')
                self.order = self.close()
                self.stop_loss_price = None
            else:
                # 更新止损价格（追踪止损）
                new_stop = self.dataclose[0] - (
                    self.atr[0] * self.params.atr_stop_multiplier
                )
                if new_stop > self.stop_loss_price:
                    self.stop_loss_price = new_stop
        else:
            # 未持仓，检查入场条件
            if self.check_entry_conditions():
                # 计算仓位大小
                size = int(
                    (self.broker.getcash() * self.params.position_size) /
                    self.dataclose[0]
                )
                
                if size > 0:
                    self.log(
                        f'满足入场条件，买入 {size} 手，'
                        f'价格: {self.dataclose[0]:.2f}, '
                        f'趋势均线: {self.trend_ma[0]:.2f}, '
                        f'成交量: {self.datavolume[0]:.0f}, '
                        f'成交量阈值: {self.volume_ma[0] * self.params.volume_multiplier:.0f}'
                    )
                    self.order = self.buy(size=size)
    
    def stop(self) -> None:
        """
        策略结束时的统计信息输出
        """
        total_return = (self.broker.getvalue() - self.broker.startingcash) / self.broker.startingcash * 100
        
        print('=' * 50)
        print('策略回测结果')
        print('=' * 50)
        print(f'初始资金: {self.broker.startingcash:.2f}')
        print(f'最终资金: {self.broker.getvalue():.2f}')
        print(f'总收益率: {total_return:.2f}%')
        print(f'总交易次数: {self.trade_count}')
        print(f'盈利次数: {self.win_count}')
        print(f'亏损次数: {self.loss_count}')
        if self.trade_count > 0:
            win_rate = self.win_count / self.trade_count * 100
            print(f'胜率: {win_rate:.2f}%')
        print('=' * 50)

