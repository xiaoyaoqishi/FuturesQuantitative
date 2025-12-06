"""
回测引擎模块

配置和运行 Backtrader 回测引擎
"""

import backtrader as bt
from typing import Optional, Dict, Any

from strategies.trend_sniper import TrendSniperStrategy


class BacktestEngine:
    """
    回测引擎类
    
    封装 Backtrader Cerebro 的配置和运行逻辑
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.001,
        commission_type: str = 'percentage'
    ) -> None:
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
            commission_type: 手续费类型 ('percentage' 或 'fixed')
        """
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(initial_cash)
        
        # 设置手续费
        if commission_type == 'percentage':
            self.cerebro.broker.setcommission(commission=commission)
        else:
            # 固定手续费（每手）
            self.cerebro.broker.setcommission(
                commission=commission,
                mult=1.0,
                margin=None
            )
        
        # 设置滑点（可选）
        self.cerebro.broker.set_slippage_perc(perc=0.001)  # 0.1% 滑点
        
        # 设置数据
        self.data: Optional[bt.feeds.PandasData] = None
        
        # 设置策略
        self.strategy: Optional[type] = None
        self.strategy_params: Dict[str, Any] = {}
    
    def add_data(
        self,
        data: bt.feeds.PandasData,
        name: str = 'main'
    ) -> None:
        """
        添加数据到回测引擎
        
        Args:
            data: Backtrader 数据 feed
            name: 数据名称
        """
        self.data = data
        self.cerebro.adddata(data, name=name)
    
    def set_strategy(
        self,
        strategy_class: type = TrendSniperStrategy,
        **params
    ) -> None:
        """
        设置策略
        
        Args:
            strategy_class: 策略类
            **params: 策略参数
        """
        self.strategy = strategy_class
        self.strategy_params = params
        self.cerebro.addstrategy(strategy_class, **params)
    
    def add_analyzer(self, analyzer_class: type, **params) -> None:
        """
        添加分析器
        
        Args:
            analyzer_class: 分析器类
            **params: 分析器参数
        """
        self.cerebro.addanalyzer(analyzer_class, **params)
    
    def run(self) -> bt.Cerebro:
        """
        运行回测
        
        Returns:
            Cerebro 对象（包含回测结果）
        """
        if self.data is None:
            raise ValueError('请先添加数据')
        
        if self.strategy is None:
            raise ValueError('请先设置策略')
        
        print('=' * 50)
        print('开始回测')
        print('=' * 50)
        print(f'初始资金: {self.cerebro.broker.getcash():.2f}')
        
        # 运行回测
        results = self.cerebro.run()
        
        print('=' * 50)
        print('回测完成')
        print('=' * 50)
        print(f'最终资金: {self.cerebro.broker.getvalue():.2f}')
        
        return self.cerebro
    
    def get_value(self) -> float:
        """
        获取当前资金价值
        
        Returns:
            资金价值
        """
        return self.cerebro.broker.getvalue()
    
    def get_cash(self) -> float:
        """
        获取当前现金
        
        Returns:
            现金金额
        """
        return self.cerebro.broker.getcash()

