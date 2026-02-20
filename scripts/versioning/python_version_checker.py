#!/usr/bin/env python3
"""
Python版本检查装饰器和工具
为所有测试文件添加Python 3.13版本检查
"""

import functools
import sys
import warnings
from typing import Any, Callable

# 版本要求配置
REQUIRED_PYTHON_VERSION = (3, 13)
PROJECT_NAME = "Industry AI Flow"
CORE_MODULE = "PaddleOCR"


class PythonVersionError(Exception):
    """Python版本不匹配异常"""

    pass


class DependencyError(Exception):
    """依赖缺失异常"""

    pass


def check_python_version():
    """检查Python版本是否满足要求"""
    current_version = (sys.version_info.major, sys.version_info.minor)

    if current_version != REQUIRED_PYTHON_VERSION:
        raise PythonVersionError(
            f"{PROJECT_NAME}需要Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}，"
            f"但当前版本为{current_version[0]}.{current_version[1]}。\n"
            f"请安装Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}并切换环境:\n"
            f"  pyenv install {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.x\n"
            f"  pyenv local {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}.x\n"
            f"  python{REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]} -m venv venv\n"
            f"  source venv/bin/activate"
        )


def check_critical_dependencies():
    """检查关键依赖是否已安装"""
    critical_deps = {
        "paddlepaddle": "PaddlePaddle后端",
        "paddleocr": "OCR识别核心",
        "numpy": "数值计算",
        "opencv-python": "图像处理",
        "pillow": "图像格式支持",
    }

    missing_deps = []

    for dep_name, description in critical_deps.items():
        try:
            if dep_name == "opencv-python":
                import cv2
            elif dep_name == "pillow":
                import PIL
            elif dep_name == "numpy":
                import numpy
            elif dep_name == "paddlepaddle":
                import paddle  # PaddlePaddle imported as 'paddle'
            elif dep_name == "paddleocr":
                import paddleocr
            else:
                __import__(dep_name)
        except ImportError:
            missing_deps.append(f"  - {dep_name}: {description}")

    if missing_deps:
        raise DependencyError(
            f"缺少关键依赖:\n" + "\n".join(missing_deps) + "\n\n"
            f"请安装依赖:\n"
            f"  pip install 'paddlepaddle>=3.0.0b0' 'paddleocr>=3.0.0b0' numpy==1.24.3 opencv-python==4.8.0.76 pillow==10.0.1\n"
            f"或运行专用安装脚本:\n"
            f"  ./scripts/setup/install_python313_paddleocr.sh"
        )


def require_python313(func: Callable) -> Callable:
    """Python 3.13版本检查装饰器"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            check_python_version()
            check_critical_dependencies()
            return func(*args, **kwargs)
        except PythonVersionError as e:
            print(f"❌ Python版本错误:")
            print(f"   {e}")
            return False
        except DependencyError as e:
            print(f"❌ 依赖错误:")
            print(f"   {e}")
            return False
        except Exception as e:
            print(f"❌ 未知错误:")
            print(f"   {e}")
            return False

    return wrapper


def check_paddleocr_availability():
    """检查PaddleOCR可用性"""
    try:
        import paddle  # PaddlePaddle is imported as 'paddle'
        import paddleocr

        paddle_version = getattr(paddleocr, "__version__", "Unknown")
        paddlepaddle_version = getattr(paddle, "__version__", "Unknown")

        print(f"✅ PaddleOCR版本: {paddle_version}")
        print(f"✅ PaddlePaddle版本: {paddlepaddle_version}")

        return True

    except ImportError as e:
        print(f"❌ PaddleOCR导入失败: {e}")
        return False


def print_environment_info():
    """打印环境信息"""
    print("=" * 60)
    print(f"🐍 Python版本: {sys.version}")
    print(f"📍 当前工作目录: {sys.path[0]}")
    print("=" * 60)


def run_with_version_check(func: Callable, *args, **kwargs) -> Any:
    """运行函数前进行版本检查"""
    print_environment_info()

    try:
        check_python_version()
        check_critical_dependencies()
        return func(*args, **kwargs)
    except (PythonVersionError, DependencyError) as e:
        print(f"\n🚨 环境检查失败:")
        print(f"{e}")
        print(f"\n💡 解决方案:")
        print(
            f"1. 确保安装了Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}"
        )
        print(f"2. 运行专用安装脚本: ./scripts/setup/install_python313_paddleocr.sh")
        print(f"3. 激活Python 3.13环境")
        return None


def create_version_test_report() -> dict:
    """创建版本兼容性测试报告"""
    report = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "python_version_ok": (sys.version_info.major, sys.version_info.minor)
        == REQUIRED_PYTHON_VERSION,
        "dependencies": {},
        "overall_status": "UNKNOWN",
        "recommendations": [],
    }

    # 检查依赖状态
    critical_deps = {
        "paddlepaddle": "PaddlePaddle后端",
        "paddleocr": "OCR识别核心",
        "numpy": "数值计算",
        "opencv-python": "图像处理",
        "pillow": "图像格式支持",
        "pandas": "数据处理",
        "matplotlib": "数据可视化",
    }

    installed_count = 0
    total_count = len(critical_deps)

    for dep_name, description in critical_deps.items():
        try:
            if dep_name == "opencv-python":
                import cv2

                version = getattr(cv2, "__version__", "Unknown")
            elif dep_name == "pillow":
                import PIL

                version = getattr(PIL, "__version__", "Unknown")
            elif dep_name == "numpy":
                import numpy

                version = getattr(numpy, "__version__", "Unknown")
            elif dep_name == "pandas":
                import pandas

                version = getattr(pandas, "__version__", "Unknown")
            elif dep_name == "matplotlib":
                import matplotlib

                version = getattr(matplotlib, "__version__", "Unknown")
            elif dep_name == "paddlepaddle":
                import paddle  # PaddlePaddle imported as 'paddle'

                version = getattr(paddle, "__version__", "Unknown")
            elif dep_name == "paddleocr":
                import paddleocr

                version = getattr(paddleocr, "__version__", "Unknown")
            else:
                module = __import__(dep_name)
                version = getattr(module, "__version__", "Unknown")

            report["dependencies"][dep_name] = {
                "installed": True,
                "version": version,
                "description": description,
            }
            installed_count += 1

        except ImportError:
            report["dependencies"][dep_name] = {
                "installed": False,
                "version": None,
                "description": description,
            }

    # 生成建议
    if not report["python_version_ok"]:
        report["recommendations"].append(
            {
                "priority": "CRITICAL",
                "issue": "Python版本不匹配",
                "solution": f"切换到Python {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}环境",
            }
        )

    missing_deps = total_count - installed_count
    if missing_deps > 0:
        report["recommendations"].append(
            {
                "priority": "HIGH",
                "issue": f"缺失{missing_deps}个关键依赖",
                "solution": "运行 ./scripts/setup/install_python313_paddleocr.sh 安装依赖",
            }
        )

    # 总体状态
    success_rate = installed_count / total_count if total_count > 0 else 0
    if report["python_version_ok"] and success_rate >= 0.8:
        report["overall_status"] = "EXCELLENT"
    elif report["python_version_ok"] and success_rate >= 0.6:
        report["overall_status"] = "GOOD"
    elif success_rate >= 0.4:
        report["overall_status"] = "FAIR"
    else:
        report["overall_status"] = "POOR"

    report["success_rate"] = success_rate
    report["installed_count"] = installed_count
    report["total_count"] = total_count

    return report


if __name__ == "__main__":
    # 运行版本检查
    report = create_version_test_report()

    print("🔍 Python 3.13 + PaddleOCR 环境检查报告")
    print("=" * 60)
    print(f"🐍 Python版本: {report['python_version']}")
    print(f"✅ 版本兼容: {'是' if report['python_version_ok'] else '否'}")
    print(f"📦 依赖状态: {report['installed_count']}/{report['total_count']} 已安装")
    print(f"📊 成功率: {report['success_rate']:.1%}")
    print(f"🎯 总体状态: {report['overall_status']}")

    if report["recommendations"]:
        print("\n💡 建议:")
        for i, rec in enumerate(report["recommendations"], 1):
            emoji = "🚨" if rec["priority"] == "CRITICAL" else "⚠️"
            print(f"  {emoji} {rec['issue']}")
            print(f"     {rec['solution']}")

    # 详细依赖状态
    print(f"\n📋 依赖详情:")
    for dep_name, info in report["dependencies"].items():
        status = "✅" if info["installed"] else "❌"
        version = info["version"] if info["installed"] else "未安装"
        print(f"  {status} {dep_name}: {version} ({info['description']})")

    print("=" * 60)

    # 退出码
    success = report["python_version_ok"] and report["success_rate"] >= 0.8
    sys.exit(0 if success else 1)
