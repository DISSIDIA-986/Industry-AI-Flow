#!/usr/bin/env python3
"""
版本管理器 - 检查和管理Python版本兼容性
解决因版本不兼容导致的测试中断问题
"""

import sys
import subprocess
import os
import time
from pathlib import Path
import json
from typing import Dict, List, Tuple, Optional

class VersionManager:
    def __init__(self):
        self.version_requirements = {
            'python': {
                'target_version': (3, 13),
                'critical_dependencies': {
                    'paddleocr': {
                        'min_version': (3, 7),
                        'max_version': (3, 14),
                        'recommended': (3, 13),
                        'version': '2.7.0',
                        'critical': True,
                        'notes': '核心OCR模块，必须支持'
                    },
                    'paddlepaddle': {
                        'min_version': (3, 7),
                        'max_version': (3, 14),
                        'recommended': (3, 13),
                        'version': '2.6.1',
                        'critical': True,
                        'notes': 'PaddleOCR后端，必须支持'
                    }
                },
                'optional_dependencies': {
                    'opencv-python': {
                        'min_version': (3, 8),
                        'max_version': (3, 14),
                        'version': '4.8.0.76',
                        'notes': '图像处理支持'
                    },
                    'pillow': {
                        'min_version': (3, 8),
                        'max_version': (3, 14),
                        'version': '10.0.1',
                        'notes': '图像格式支持'
                    }
                }
            }
        }

        # Python 3.13专用兼容性矩阵
        self.compatibility_matrix = {
            (3, 13): {
                'paddleocr': {'supported': True, 'version': '2.7.0', 'notes': '核心模块，完全支持'},
                'paddlepaddle': {'supported': True, 'version': '2.6.1', 'notes': 'PaddleOCR后端，完全支持'},
                'opencv-python': {'supported': True, 'version': '4.8.0.76', 'notes': '图像处理，完全支持'},
                'pillow': {'supported': True, 'version': '10.0.1', 'notes': '图像格式，完全支持'},
                'numpy': {'supported': True, 'version': '1.24.3', 'notes': '数值计算，完全支持'},
                'pandas': {'supported': True, 'version': '1.5.3', 'notes': '数据处理，完全支持'}
            }
        }

    def get_python_version(self) -> Tuple[int, int, int]:
        """获取当前Python版本"""
        version = sys.version_info
        return (version.major, version.minor, version.micro)

    def check_python_version(self) -> Tuple[bool, str]:
        """检查Python版本兼容性 - 专注Python 3.13"""
        version = self.get_python_version()
        current_version = (version[0], version[1])
        target_version = self.version_requirements['python']['target_version']

        if current_version == target_version:
            return True, f"✅ Python版本完美匹配: {current_version[0]}.{current_version[1]} (PaddleOCR核心版本)"
        else:
            return False, f"❌ Python版本不匹配: {current_version[0]}.{current_version[1]} ≠ {target_version[0]}.{target_version[1]} (需要Python 3.13以支持PaddleOCR)"

    def check_dependency_compatibility(self, dep_name: str) -> Tuple[bool, str]:
        """检查特定依赖的版本兼容性 - 专注Python 3.13"""
        current_version = self.get_python_version()
        current_py_version = (current_version[0], current_version[1])
        target_version = self.version_requirements['python']['target_version']

        if current_py_version != target_version:
            return False, f"❌ {dep_name} 需要Python {target_version[0]}.{target_version[1]} (当前: {current_py_version[0]}.{current_py_version[1]})"

        # 检查核心依赖
        if dep_name in self.version_requirements['python']['critical_dependencies']:
            dep_info = self.version_requirements['python']['critical_dependencies'][dep_name]
            return True, f"✅ {dep_name} 是核心依赖，Python 3.13完全支持 - {dep_info.get('notes', '')}"

        # 检查可选依赖
        if dep_name in self.version_requirements['python']['optional_dependencies']:
            dep_info = self.version_requirements['python']['optional_dependencies'][dep_name]
            return True, f"✅ {dep_name} 是可选依赖，Python 3.13支持 - {dep_info.get('notes', '')}"

        # 检查兼容性矩阵
        if current_py_version in self.compatibility_matrix:
            dep_info = self.compatibility_matrix[current_py_version].get(dep_name, {})
            if dep_info.get('supported', False):
                return True, f"✅ {dep_name} 在Python 3.13下完全支持 - {dep_info.get('notes', '')}"
            else:
                return False, f"❌ {dep_name} 在Python 3.13下不支持 - {dep_info.get('notes', '')}"
        else:
            return False, f"❌ {dep_name} 不在Python 3.13支持列表中"

    def check_virtual_environment(self) -> Tuple[bool, str]:
        """检查虚拟环境状态"""
        # 检查是否在虚拟环境中
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix)

        if in_venv:
            venv_path = sys.prefix
            return True, f"✅ 虚拟环境已激活: {venv_path}"
        else:
            return False, "❌ 未检测到虚拟环境，建议使用虚拟环境隔离依赖"

    def check_critical_packages(self) -> List[Tuple[str, bool, str]]:
        """检查关键包的安装状态 - 专注PaddleOCR核心功能"""
        critical_packages = ['paddleocr', 'paddlepaddle', 'opencv-python', 'pillow']
        results = []

        for package in critical_packages:
            try:
                # 特殊处理一些包名
                import_name = package.replace('-', '_')
                if import_name == 'paddleocr':
                    import_name = 'paddleocr'
                elif import_name == 'opencv_python':
                    import_name = 'cv2'

                __import__(import_name)
                compatible, msg = self.check_dependency_compatibility(package)
                results.append((package, True, f"✅ 已安装 - {msg}"))
            except ImportError:
                compatible, msg = self.check_dependency_compatibility(package)
                results.append((package, False, f"❌ 未安装 - {msg}"))

        return results

    def generate_version_report(self) -> Dict:
        """生成完整的版本兼容性报告"""
        report = {
            'timestamp': time.time(),
            'python_version': f"{self.get_python_version()[0]}.{self.get_python_version()[1]}.{self.get_python_version()[2]}",
            'compatibility': {},
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'package_status': {}
        }

        # 检查Python版本
        python_ok, python_msg = self.check_python_version()
        report['compatibility']['python'] = python_ok
        if not python_ok:
            report['errors'].append(python_msg)
        elif "推荐版本" not in python_msg:
            report['warnings'].append(python_msg)

        # 检查虚拟环境
        venv_ok, venv_msg = self.check_virtual_environment()
        report['compatibility']['virtual_environment'] = venv_ok
        if not venv_ok:
            report['warnings'].append(venv_msg)

        # 检查关键包
        package_results = self.check_critical_packages()
        for package, installed, msg in package_results:
            report['package_status'][package] = {
                'installed': installed,
                'message': msg
            }
            if not installed and "支持" in msg:
                report['errors'].append(f"{package}: {msg}")

        # 生成建议 - 专注Python 3.13
        current_version = self.get_python_version()[:2]
        target_version = self.version_requirements['python']['target_version']

        if current_version != target_version:
            report['recommendations'].append(
                f"⚠️ 必须使用Python {target_version[0]}.{target_version[1]}以支持PaddleOCR核心功能"
            )
            report['recommendations'].append(
                f"💡 安装Python 3.13: pyenv install 3.13.x && pyenv global 3.13.x"
            )

        if not venv_ok:
            report['recommendations'].append("🔒 建议创建虚拟环境：python3.13 -m venv venv && source venv/bin/activate")

        # 根据缺失的包给出安装建议
        missing_packages = [pkg for pkg, installed, _ in package_results if not installed]
        if missing_packages:
            if current_version == target_version:
                # Python 3.13 专用安装建议
                report['recommendations'].append(
                    "🔧 Python 3.13环境安装命令："
                )
                report['recommendations'].append(
                    "   pip install paddlepaddle==2.6.1 paddleocr==2.7.0 opencv-python==4.8.0.76 pillow==10.0.1"
                )
                report['recommendations'].append(
                    "   或运行自动化脚本: ./install_with_compatibility_check.sh"
                )
            else:
                # 其他版本的错误提示
                report['recommendations'].append(
                    "❌ 当前Python版本不支持PaddleOCR，请先切换到Python 3.13"
                )

        return report

    def print_version_report(self):
        """打印版本报告"""
        report = self.generate_version_report()

        print("=" * 60)
        print("🔍 Python环境版本兼容性检查报告")
        print("=" * 60)
        print(f"📅 检查时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🐍 Python版本: {report['python_version']}")
        print()

        # 兼容性状态
        print("📊 兼容性状态:")
        for component, status in report['compatibility'].items():
            status_emoji = "✅" if status else "❌"
            status_text = "兼容" if status else "不兼容"
            component_name = {
                'python': 'Python版本',
                'virtual_environment': '虚拟环境'
            }.get(component, component)
            print(f"  {status_emoji} {component_name}: {status_text}")
        print()

        # 包状态
        print("📦 关键包状态:")
        for package, info in report['package_status'].items():
            print(f"  {info['message']}")
        print()

        # 警告和错误
        if report['errors']:
            print("🚨 错误:")
            for error in report['errors']:
                print(f"  {error}")
            print()

        if report['warnings']:
            print("⚠️ 警告:")
            for warning in report['warnings']:
                print(f"  {warning}")
            print()

        # 建议
        if report['recommendations']:
            print("💡 建议:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
            print()

        # 总体评估
        total_errors = len(report['errors'])
        total_warnings = len(report['warnings'])

        if total_errors == 0 and total_warnings == 0:
            print("🎉 完美! 环境配置完全兼容，可以正常运行所有测试")
        elif total_errors == 0:
            print("✅ 良好! 环境基本兼容，建议关注警告信息")
        else:
            print("❌ 需要修复! 请解决错误后再运行测试")

        print("=" * 60)

        return report

    def save_report(self, filename: str = None):
        """保存报告到文件"""
        if filename is None:
            import time
            filename = f"version_compatibility_report_{time.strftime('%Y%m%d_%H%M%S')}.json"

        report = self.generate_version_report()

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"📁 详细报告已保存: {filename}")
            return filename
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")
            return None

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Python环境版本兼容性检查工具')
    parser.add_argument('--save-report', action='store_true', help='保存详细报告到JSON文件')
    parser.add_argument('--quiet', action='store_true', help='静默模式，只输出结果')
    parser.add_argument('--check-deps', nargs='+', help='检查指定依赖的兼容性')

    args = parser.parse_args()

    vm = VersionManager()

    if args.check_deps:
        # 检查指定依赖
        for dep in args.check_deps:
            compatible, msg = vm.check_dependency_compatibility(dep)
            print(f"{dep}: {msg}")
        return

    if args.quiet:
        # 静默模式
        report = vm.generate_version_report()
        total_errors = len(report['errors'])
        sys.exit(0 if total_errors == 0 else 1)
    else:
        # 详细模式
        vm.print_version_report()

        if args.save_report:
            vm.save_report()

        # 根据错误数量决定退出码
        report = vm.generate_version_report()
        total_errors = len(report['errors'])
        sys.exit(0 if total_errors == 0 else 1)

if __name__ == "__main__":
    main()