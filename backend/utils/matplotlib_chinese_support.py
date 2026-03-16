#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPRECATED: Legacy Chinese-font helper kept for historical compatibility.
This module is not used in the default AIFlow runtime path.

终极 matplotlib 中文支持解决方案
放置于 ~/Documents/py/matplotlib_chinese_support.py
使用方法：在需要中文支持的脚本开头添加:
    from matplotlib_chinese_support import setup_chinese_matplotlib
    setup_chinese_matplotlib()
或者，将此文件添加到 PYTHONPATH 并在启动时自动导入
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)


def setup_chinese_matplotlib():
    """
    Set up matplotlib font support
    """
    logger.warning(
        "matplotlib_chinese_support is deprecated and excluded from default runtime."
    )
    try:
        import matplotlib
        import matplotlib.font_manager as fm

        # macOS 系统中文字体路径
        font_paths = [
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
        ]

        # 尝试使用字体文件路径（最可靠的方法）
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font_prop = fm.FontProperties(fname=font_path)
                    matplotlib.rcParams["font.family"] = font_prop.get_name()
                    logger.info("Font set: %s", font_prop.get_name())
                    break
                except Exception as e:
                    continue
        else:
            # 如果字体文件方法失败，使用字体名称
            chinese_fonts = [
                "Arial Unicode MS",
                "Heiti TC",
                "Heiti SC",
                "STHeiti Light",
                "STHeiti Medium",
                "PingFang SC",
                "SimHei",
                "Microsoft YaHei",
                "DejaVu Sans",
            ]
            matplotlib.rcParams["font.sans-serif"] = chinese_fonts
            matplotlib.rcParams["font.family"] = "sans-serif"
            logger.info("Font set (fallback method)")

        # 关键设置：解决负号显示问题
        matplotlib.rcParams["axes.unicode_minus"] = False

        return True

    except ImportError:
        logger.warning("matplotlib is not installed")
        return False
    except Exception as e:
        logger.error("Error setting up font support: %s", e)
        return False


def test_chinese_display():
    """Test font display functionality"""
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        # 创建测试图形
        fig, ax = plt.subplots(figsize=(10, 6))

        # 示例数据
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x)

        ax.plot(x, y, label="Sine function", linewidth=2)
        ax.set_title("Matplotlib font display test - Sine wave", fontsize=16)
        ax.set_xlabel("X-axis - Radian values", fontsize=12)
        ax.set_ylabel("Y-axis - Function values", fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 添加中文注释
        ax.text(
            np.pi,
            0.5,
            "Font rendering test",
            fontsize=14,
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7),
        )

        plt.tight_layout()
        plt.savefig(
            os.path.expanduser("~/Documents/py/chinese_test.png"),
            dpi=150,
            bbox_inches="tight",
        )
        logger.info(
            "Font display test complete, image saved to ~/Documents/py/chinese_test.png"
        )
        plt.close()  # Avoid duplicate display in Jupyter

        return True
    except Exception as e:
        logger.error("Error testing font display: %s", e)
        return False


# 如果直接运行此脚本，则执行完整设置和测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Setting up matplotlib font support...")
    success = setup_chinese_matplotlib()

    if success:
        logger.info("Testing font rendering...")
        test_chinese_display()
        logger.info("matplotlib Font support configured!")
        logger.info("For existing scripts, add the following at the top:")
        logger.info("  from matplotlib_chinese_support import setup_chinese_matplotlib")
        logger.info("  setup_chinese_matplotlib()")
    else:
        logger.error("Setup failed")
