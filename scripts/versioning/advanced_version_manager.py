#!/usr/bin/env python3
"""
高级版本管理器 - 处理复杂的测试场景
解决test_cases和test_resources中发现的各种版本管理问题
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AdvancedVersionManager:
    def __init__(self):
        self.version_requirements = {
            "python": {
                "target_version": (3, 13),
                "critical_modules": {
                    # OCR核心模块 - Nightly build版本
                    "paddleocr": {
                        "min_version": (3, 13),
                        "max_version": (3, 14),
                        "recommended": (3, 13),
                        "version": ">=3.0.0b0",
                        "critical": True,
                        "notes": "建筑图纸OCR识别核心模块 - Nightly build",
                    },
                    "paddlepaddle": {
                        "min_version": (3, 13),
                        "max_version": (3, 14),
                        "recommended": (3, 13),
                        "version": ">=3.0.0b0",
                        "critical": True,
                        "notes": "PaddleOCR后端支持 - Nightly build",
                    },
                    # 图像处理模块
                    "opencv-python": {
                        "min_version": (3, 8),
                        "max_version": (3, 14),
                        "version": "4.8.0.76",
                        "critical": True,
                        "notes": "图像处理和计算机视觉",
                    },
                    "pillow": {
                        "min_version": (3, 8),
                        "max_version": (3, 14),
                        "version": "10.0.1",
                        "critical": True,
                        "notes": "图像格式支持",
                    },
                    # 数据科学模块
                    "numpy": {
                        "min_version": (3, 8),
                        "max_version": (3, 14),
                        "version": "1.24.3",
                        "critical": True,
                        "notes": "数值计算基础",
                    },
                    "pandas": {
                        "min_version": (3, 8),
                        "max_version": (3, 14),
                        "version": "1.5.3",
                        "critical": True,
                        "notes": "数据处理和分析",
                    },
                },
                # 可选AI模块
                "optional_modules": {
                    "torch": {
                        "min_version": (3, 8),
                        "max_version": (3, 12),
                        "version": "2.0.1",
                        "notes": "深度学习框架，Python 3.13不支持",
                    },
                    "langchain": {
                        "min_version": (3, 8),
                        "max_version": (3, 12),
                        "version": "0.1.0",
                        "notes": "RAG系统，Python 3.13不支持",
                    },
                    "sentence-transformers": {
                        "min_version": (3, 8),
                        "max_version": (3, 12),
                        "version": "2.2.2",
                        "notes": "文本嵌入，Python 3.13不支持",
                    },
                },
            }
        }

    def get_python_version(self) -> Tuple[int, int, int]:
        """获取当前Python版本"""
        version = sys.version_info
        return (version.major, version.minor, version.micro)

    def check_python_compatibility(self) -> Tuple[bool, str]:
        """检查Python版本兼容性"""
        current_version = self.get_python_version()
        current_py_version = (current_version[0], current_version[1])
        target_version = self.version_requirements["python"]["target_version"]

        if current_py_version == target_version:
            return (
                True,
                f"✅ Python版本完美匹配: {current_py_version[0]}.{current_py_version[1]} (目标版本)",
            )
        else:
            return (
                False,
                f"❌ Python版本不匹配: {current_py_version[0]}.{current_py_version[1]} ≠ {target_version[0]}.{target_version[1]} (目标版本)",
            )

    def test_module_import(
        self, module_name: str, import_name: str = None
    ) -> Tuple[bool, str]:
        """测试模块导入"""
        try:
            if import_name is None:
                import_name = module_name.replace("-", "_").replace(".", "_")

            spec = importlib.util.find_spec(import_name)
            if spec is not None:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return True, f"✅ {module_name}: 导入成功"
            else:
                return False, f"❌ {module_name}: 模块未找到"
        except ImportError as e:
            return False, f"❌ {module_name}: 导入失败 - {e}"
        except Exception as e:
            return False, f"❌ {module_name}: 其他错误 - {e}"

    def check_test_dependencies(self, test_file_path: str) -> Dict:
        """检查测试文件的依赖需求"""
        results = {
            "file_path": test_file_path,
            "critical_modules": {},
            "optional_modules": {},
            "python_version_ok": False,
            "can_run": False,
        }

        try:
            with open(test_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            results["error"] = f"无法读取文件: {e}"
            return results

        # 检查Python版本
        python_ok, python_msg = self.check_python_compatibility()
        results["python_version_ok"] = python_ok
        results["python_message"] = python_msg

        # 检查导入语句
        critical_modules = self.version_requirements["python"]["critical_modules"]
        optional_modules = self.version_requirements["python"]["optional_modules"]

        for module_name in critical_modules:
            if module_name in content.lower() or any(
                alias in content for alias in self._get_module_aliases(module_name)
            ):
                import_ok, import_msg = self.test_module_import(module_name)
                results["critical_modules"][module_name] = {
                    "imported": import_ok,
                    "message": import_msg,
                    "critical": True,
                }

        for module_name in optional_modules:
            if module_name in content.lower() or any(
                alias in content for alias in self._get_module_aliases(module_name)
            ):
                import_ok, import_msg = self.test_module_import(module_name)
                results["optional_modules"][module_name] = {
                    "imported": import_ok,
                    "message": import_msg,
                    "critical": False,
                }

        # 判断是否可以运行
        critical_imported = all(
            m["imported"] for m in results["critical_modules"].values()
        )
        results["can_run"] = python_ok and critical_imported

        return results

    def _get_module_aliases(self, module_name: str) -> List[str]:
        """获取模块的可能别名"""
        aliases = {
            "paddleocr": ["paddleocr"],
            "paddlepaddle": ["paddle", "paddlepaddle"],
            "opencv-python": ["cv2", "opencv"],
            "pillow": ["PIL", "pillow"],
            "numpy": ["numpy", "np"],
            "pandas": ["pandas", "pd"],
            "torch": ["torch"],
            "langchain": ["langchain"],
            "sentence-transformers": ["sentence_transformers", "sentence_transformers"],
        }
        return aliases.get(module_name, [module_name])

    def analyze_test_directory(self, test_dir: str = "docs/testing/test-case-specs") -> Dict:
        """分析测试目录中的所有文件"""
        test_path = Path(test_dir)
        if not test_path.exists():
            return {"error": f"测试目录不存在: {test_dir}"}

        results = {
            "directory": test_dir,
            "total_files": 0,
            "python_files": 0,
            "analysis": {},
            "summary": {
                "can_run": 0,
                "cannot_run": 0,
                "python_version_issues": 0,
                "missing_critical_deps": 0,
                "missing_optional_deps": 0,
            },
        }

        for file_path in test_path.rglob("*.py"):
            if file_path.is_file():
                results["total_files"] += 1
                if file_path.suffix == ".py":
                    results["python_files"] += 1

                    # 分析每个Python文件
                    analysis = self.check_test_dependencies(str(file_path))
                    results["analysis"][
                        str(file_path.relative_to(test_path))
                    ] = analysis

                    # 更新统计
                    if analysis.get("can_run", False):
                        results["summary"]["can_run"] += 1
                    else:
                        results["summary"]["cannot_run"] += 1

                        if not analysis.get("python_version_ok", False):
                            results["summary"]["python_version_issues"] += 1

                        missing_critical = sum(
                            1
                            for m in analysis.get("critical_modules", {}).values()
                            if not m.get("imported", False) and m.get("critical", False)
                        )
                        results["summary"]["missing_critical_deps"] += missing_critical

                        missing_optional = sum(
                            1
                            for m in analysis.get("optional_modules", {}).values()
                            if not m.get("imported", False)
                            and not m.get("critical", False)
                        )
                        results["summary"]["missing_optional_deps"] += missing_optional

        return results

    def analyze_test_resources(self, resources_dir: str = "test_resources") -> Dict:
        """分析测试资源目录"""
        resources_path = Path(resources_dir)
        if not resources_path.exists():
            return {"error": f"资源目录不存在: {resources_dir}"}

        results = {
            "directory": resources_dir,
            "total_files": 0,
            "file_types": {},
            "image_files": [],
            "dataset_files": [],
            "other_files": [],
        }

        for file_path in resources_path.rglob("*"):
            if file_path.is_file():
                results["total_files"] += 1
                file_ext = file_path.suffix.lower()

                if file_ext not in results["file_types"]:
                    results["file_types"][file_ext] = 0
                results["file_types"][file_ext] += 1

                # 分类文件
                if file_ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif"]:
                    results["image_files"].append(
                        str(file_path.relative_to(resources_path))
                    )
                elif file_ext in [".csv", ".json", ".xlsx", ".parquet"]:
                    results["dataset_files"].append(
                        str(file_path.relative_to(resources_path))
                    )
                else:
                    results["other_files"].append(
                        str(file_path.relative_to(resources_path))
                    )

        return results

    def generate_comprehensive_report(self) -> Dict:
        """生成综合报告"""
        report = {
            "timestamp": time.time(),
            "python_version": f"{self.get_python_version()[0]}.{self.get_python_version()[1]}.{self.get_python_version()[2]}",
            "test_cases_analysis": self.analyze_test_directory(),
            "test_resources_analysis": self.analyze_test_resources(),
            "recommendations": [],
        }

        # 生成建议
        python_ok, python_msg = self.check_python_compatibility()

        if not python_ok:
            report["recommendations"].append(
                {
                    "priority": "CRITICAL",
                    "issue": "Python版本不兼容",
                    "message": python_msg,
                    "solution": "安装Python 3.13并切换环境: pyenv install 3.13.x && pyenv local 3.13.x",
                }
            )

        # 分析测试用例问题
        test_analysis = report["test_cases_analysis"]
        if "summary" in test_analysis:
            summary = test_analysis["summary"]

            if summary["python_version_issues"] > 0:
                report["recommendations"].append(
                    {
                        "priority": "HIGH",
                        "issue": f'{summary["python_version_issues"]}个测试用例因Python版本问题无法运行',
                        "solution": "切换到Python 3.13环境",
                    }
                )

            if summary["missing_critical_deps"] > 0:
                report["recommendations"].append(
                    {
                        "priority": "CRITICAL",
                        "issue": f'{summary["missing_critical_deps"]}个关键依赖缺失',
                        "solution": "运行专用安装脚本: ./scripts/setup/install_python313_paddleocr.sh",
                    }
                )

            if summary["missing_optional_deps"] > 0:
                report["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "issue": f'{summary["missing_optional_deps"]}个可选依赖缺失',
                        "solution": "根据需要安装可选AI依赖（注意Python 3.13兼容性）",
                    }
                )

        # 计算成功率
        total_tests = test_analysis.get("python_files", 0)
        can_run = test_analysis.get("summary", {}).get("can_run", 0)
        if total_tests > 0:
            success_rate = can_run / total_tests
            report["success_rate"] = success_rate

            if success_rate >= 0.8:
                report["overall_status"] = "EXCELLENT"
            elif success_rate >= 0.6:
                report["overall_status"] = "GOOD"
            elif success_rate >= 0.4:
                report["overall_status"] = "FAIR"
            else:
                report["overall_status"] = "POOR"

        return report

    def print_comprehensive_report(self):
        """打印综合报告"""
        report = self.generate_comprehensive_report()

        print("=" * 80)
        print("🔍 高级版本管理器 - 全面测试环境分析报告")
        print("=" * 80)
        print(f"📅 分析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🐍 Python版本: {report['python_version']}")
        print()

        # 测试用例分析
        if "error" not in report["test_cases_analysis"]:
            test_analysis = report["test_cases_analysis"]
            summary = test_analysis.get("summary", {})

            print("📋 测试用例分析:")
            print(f"  总文件数: {test_analysis.get('total_files', 0)}")
            print(f"  Python文件: {test_analysis.get('python_files', 0)}")
            print(f"  可运行: {summary.get('can_run', 0)}")
            print(f"  无法运行: {summary.get('cannot_run', 0)}")
            print(f"  成功率: {report.get('success_rate', 0):.1%}")
            print()

            # 问题统计
            print("🚨 问题统计:")
            if summary.get("python_version_issues", 0) > 0:
                print(f"  ❌ Python版本问题: {summary['python_version_issues']} 个")
            if summary.get("missing_critical_deps", 0) > 0:
                print(f"  ❌ 缺失关键依赖: {summary['missing_critical_deps']} 个")
            if summary.get("missing_optional_deps", 0) > 0:
                print(f"  ⚠️ 缺失可选依赖: {summary['missing_optional_deps']} 个")
            print()

        # 测试资源分析
        if "error" not in report["test_resources_analysis"]:
            resources_analysis = report["test_resources_analysis"]
            print("📁 测试资源分析:")
            print(f"  总文件数: {resources_analysis.get('total_files', 0)}")
            print(f"  图像文件: {len(resources_analysis.get('image_files', []))}")
            print(f"  数据集文件: {len(resources_analysis.get('dataset_files', []))}")
            print(f"  文件类型: {list(resources_analysis.get('file_types', {}).keys())}")
            print()

        # 建议和解决方案
        if report["recommendations"]:
            print("💡 改进建议:")
            for i, rec in enumerate(report["recommendations"], 1):
                priority_emoji = {
                    "CRITICAL": "🚨",
                    "HIGH": "⚠️",
                    "MEDIUM": "💡",
                    "LOW": "ℹ️",
                }
                emoji = priority_emoji.get(rec["priority"], "ℹ️")
                print(f"  {emoji} {rec['issue']}")
                print(f"     解决方案: {rec['solution']}")
                print()

        # 总体状态
        overall_status = report.get("overall_status", "UNKNOWN")
        status_emoji = {
            "EXCELLENT": "🎉",
            "GOOD": "✅",
            "FAIR": "⚠️",
            "POOR": "❌",
            "UNKNOWN": "❓",
        }
        emoji = status_emoji.get(overall_status, "❓")

        print("=" * 80)
        print(f"总体评估: {emoji} {overall_status}")
        print("=" * 80)

        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="高级版本管理器 - 全面测试环境分析")
    parser.add_argument("--test-dir", default="docs/testing/test-case-specs", help="测试目录路径")
    parser.add_argument("--resources-dir", default="test_resources", help="资源目录路径")
    parser.add_argument("--save-report", action="store_true", help="保存详细报告到JSON文件")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    args = parser.parse_args()

    vm = AdvancedVersionManager()

    if args.quiet:
        report = vm.generate_comprehensive_report()
        # 基于成功率决定退出码
        success_rate = report.get("success_rate", 0)
        sys.exit(0 if success_rate >= 0.8 else 1)
    else:
        report = vm.print_comprehensive_report()

        if args.save_report:
            try:
                filename = (
                    f"advanced_version_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                print(f"📁 详细报告已保存: {filename}")
            except Exception as e:
                print(f"⚠️ 保存报告失败: {e}")


if __name__ == "__main__":
    main()
