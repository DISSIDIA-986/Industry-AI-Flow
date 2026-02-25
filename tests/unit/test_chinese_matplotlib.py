# EN
# EN ~/Documents/py/auto_chinese_matplotlib.py

import os
import sys


def auto_setup_chinese_matplotlib():
    """ENmatplotlibEN"""
    # EN,EN
    if hasattr(auto_setup_chinese_matplotlib, "_configured"):
        return

    try:
        # EN
        import matplotlib_chinese_support

        matplotlib_chinese_support.setup_chinese_matplotlib()
        auto_setup_chinese_matplotlib._configured = True
        print("✓ EN matplotlib EN")
    except ImportError:
        # EN,EN
        py_dir = os.path.expanduser("~/Documents/py")
        if py_dir not in sys.path:
            sys.path.insert(0, py_dir)
        try:
            import matplotlib_chinese_support

            matplotlib_chinese_support.setup_chinese_matplotlib()
            auto_setup_chinese_matplotlib._configured = True
            print("✓ EN matplotlib EN")
        except ImportError:
            print("⚠ EN matplotlib_chinese_support EN")
    except Exception as e:
        print(f"⚠ EN: {e}")


# EN
auto_setup_chinese_matplotlib()
