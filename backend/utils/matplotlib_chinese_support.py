#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极 matplotlib 中文支持解决方案
放置于 ~/Documents/py/matplotlib_chinese_support.py
使用方法：在需要中文支持的脚本开头添加:
    from matplotlib_chinese_support import setup_chinese_matplotlib
    setup_chinese_matplotlib()
或者，将此文件添加到 PYTHONPATH 并在启动时自动导入
"""

import os
import sys

def setup_chinese_matplotlib():
    """
    设置 matplotlib 支持中文显示
    """
    try:
        import matplotlib
        import matplotlib.font_manager as fm
        
        # macOS 系统中文字体路径
        font_paths = [
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf'
        ]
        
        # 尝试使用字体文件路径（最可靠的方法）
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_prop = fm.FontProperties(fname=font_path)
                    matplotlib.rcParams['font.family'] = font_prop.get_name()
                    print(f"✓ 已设置中文字体: {font_prop.get_name()}")
                    break
                except Exception as e:
                    continue
        else:
            # 如果字体文件方法失败，使用字体名称
            chinese_fonts = [
                'Arial Unicode MS',
                'Heiti TC',
                'Heiti SC', 
                'STHeiti Light',
                'STHeiti Medium',
                'PingFang SC',
                'SimHei',
                'Microsoft YaHei',
                'DejaVu Sans'
            ]
            matplotlib.rcParams['font.sans-serif'] = chinese_fonts
            matplotlib.rcParams['font.family'] = 'sans-serif'
            print("✓ 已设置中文字体（备选方案）")
        
        # 关键设置：解决负号显示问题
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        return True
        
    except ImportError:
        print("⚠ matplotlib 未安装")
        return False
    except Exception as e:
        print(f"⚠ 设置中文支持时出错: {e}")
        return False

def test_chinese_display():
    """测试中文显示功能"""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        # 创建测试图形
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 示例数据
        x = np.linspace(0, 2*np.pi, 100)
        y = np.sin(x)
        
        ax.plot(x, y, label='正弦函数', linewidth=2)
        ax.set_title('matplotlib 中文显示测试 - 正弦波', fontsize=16)
        ax.set_xlabel('X轴 - 弧度值', fontsize=12)
        ax.set_ylabel('Y轴 - 函数值', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 添加中文注释
        ax.text(np.pi, 0.5, '中文注释测试', fontsize=14, ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        
        plt.tight_layout()
        plt.savefig(os.path.expanduser('~/Documents/py/chinese_test.png'), 
                   dpi=150, bbox_inches='tight')
        print("✓ 中文显示测试完成，图像已保存到 ~/Documents/py/chinese_test.png")
        plt.close()  # 避免在Jupyter中重复显示
        
        return True
    except Exception as e:
        print(f"⚠ 测试中文显示时出错: {e}")
        return False

# 如果直接运行此脚本，则执行完整设置和测试
if __name__ == "__main__":
    print("正在设置 matplotlib 中文支持...")
    success = setup_chinese_matplotlib()
    
    if success:
        print("正在测试中文显示...")
        test_chinese_display()
        print("\n✓ matplotlib 中文支持已设置完成！")
        print("✓ 对于现有脚本，只需在开头添加以下代码：")
        print("  from matplotlib_chinese_support import setup_chinese_matplotlib")
        print("  setup_chinese_matplotlib()")
    else:
        print("✗ 设置失败")