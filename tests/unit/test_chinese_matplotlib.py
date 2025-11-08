# 自动启用中文支持的启动脚本
# 放置在 ~/Documents/py/auto_chinese_matplotlib.py

import os
import sys


def auto_setup_chinese_matplotlib():
    """自动设置matplotlib中文支持"""
    # 检查是否已经在运行此函数，避免重复执行
    if hasattr(auto_setup_chinese_matplotlib, "_configured"):
        return

    try:
        # 导入我们的中文支持模块
        import matplotlib_chinese_support

        matplotlib_chinese_support.setup_chinese_matplotlib()
        auto_setup_chinese_matplotlib._configured = True
        print("✓ 已自动启用 matplotlib 中文支持")
    except ImportError:
        # 如果模块不在路径中，尝试添加路径
        py_dir = os.path.expanduser("~/Documents/py")
        if py_dir not in sys.path:
            sys.path.insert(0, py_dir)
        try:
            import matplotlib_chinese_support

            matplotlib_chinese_support.setup_chinese_matplotlib()
            auto_setup_chinese_matplotlib._configured = True
            print("✓ 已自动启用 matplotlib 中文支持")
        except ImportError:
            print("⚠ 未找到 matplotlib_chinese_support 模块")
    except Exception as e:
        print(f"⚠ 自动设置中文支持时出错: {e}")


# 自动执行设置
auto_setup_chinese_matplotlib()
