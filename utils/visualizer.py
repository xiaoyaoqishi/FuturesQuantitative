"""
可视化工具模块

提供回测结果的可视化功能
"""

import backtrader as bt
from typing import Optional, List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class Visualizer:
    """
    可视化工具类
    
    用于绘制回测结果图表
    """
    
    @staticmethod
    def plot_backtest(
        cerebro: bt.Cerebro,
        style: str = 'candlestick',
        barup: str = 'green',
        bardown: str = 'red',
        volume: bool = True,
        indicators: bool = True,
        figsize: tuple = (16, 10)
    ) -> None:
        """
        绘制回测结果图表
        
        Args:
            cerebro: Backtrader Cerebro 对象
            style: 图表样式 ('candlestick' 或 'line')
            barup: 上涨K线颜色
            bardown: 下跌K线颜色
            volume: 是否显示成交量
            indicators: 是否显示指标
            figsize: 图表大小
        """
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 绘制图表
        cerebro.plot(
            style=style,
            barup=barup,
            bardown=bardown,
            volume=volume,
            indicators=indicators,
            figsize=figsize
        )
        
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def save_backtest_plot(
        cerebro: bt.Cerebro,
        output_path: str,
        style: str = 'candlestick',
        barup: str = 'green',
        bardown: str = 'red',
        volume: bool = True,
        indicators: bool = True,
        figsize: tuple = (16, 10),
        dpi: int = 300
    ) -> None:
        """
        保存回测结果图表到文件
        
        Args:
            cerebro: Backtrader Cerebro 对象
            output_path: 输出文件路径
            style: 图表样式
            barup: 上涨K线颜色
            bardown: 下跌K线颜色
            volume: 是否显示成交量
            indicators: 是否显示指标
            figsize: 图表大小
            dpi: 图片分辨率
        """
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 绘制图表
        # cerebro.plot() 返回一个列表，包含图形对象
        plot_result = cerebro.plot(
            style=style,
            barup=barup,
            bardown=bardown,
            volume=volume,
            indicators=indicators,
            figsize=figsize
        )
        
        # 获取图形对象
        # plot_result 的结构可能是: [fig] 或 [[fig1, fig2, ...]]
        fig = None
        if isinstance(plot_result, list) and len(plot_result) > 0:
            first_item = plot_result[0]
            # 如果第一个元素也是列表（多个子图），取第一个图形
            if isinstance(first_item, list) and len(first_item) > 0:
                fig = first_item[0]
            # 如果第一个元素直接是图形对象
            elif hasattr(first_item, 'savefig'):
                fig = first_item
            else:
                # 如果无法确定，使用 matplotlib 的当前图形
                fig = plt.gcf()
        else:
            # 如果返回的不是列表，直接使用
            fig = plot_result if hasattr(plot_result, 'savefig') else plt.gcf()
        
        # 如果仍然无法获取图形，使用当前图形
        if fig is None or not hasattr(fig, 'savefig'):
            fig = plt.gcf()
        
        plt.tight_layout()
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        print(f'图表已保存: {output_path}')

