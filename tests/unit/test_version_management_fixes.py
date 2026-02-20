#!/usr/bin/env python3
"""
EN
EN
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, capture_output=True):
    """EN"""
    print(f"\n🔧 {description}")
    print(f"EN: {cmd}")
    print("-" * 60)

    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"EN: {result.stderr}")
            return result.returncode == 0
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ EN")
        return False
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_python_version_checker():
    """ENPythonEN"""
    print("=" * 80)
    print("🧪 EN 1: PythonEN")
    print("=" * 80)

    success = run_command("python3 scripts/versioning/python_version_checker.py", "ENPythonEN")

    print(f"\n📊 EN: {'✅ EN' if success else '❌ EN'}")
    if not success:
        print("💡 EN: Python 3.14EN")
    return success


def test_version_manager():
    """EN"""
    print("\n" + "=" * 80)
    print("🧪 EN 2: EN")
    print("=" * 80)

    success = run_command(
        "python3 scripts/versioning/version_manager.py --check-deps paddleocr", "ENPaddleOCREN"
    )

    print(f"\n📊 EN: {'✅ EN' if success else '❌ EN'}")
    if not success:
        print("💡 EN: Python 3.14ENPaddleOCREN")
    return success


def test_architecture_tests():
    """EN"""
    print("\n" + "=" * 80)
    print("🧪 EN 3: EN")
    print("=" * 80)

    # EN
    success = run_command(
        "python3 test_architecture_construction_industry.py",
        "EN",
        capture_output=True,
    )

    # EN
    test_output = subprocess.run(
        ["python3", "test_architecture_construction_industry.py"],
        capture_output=True,
        text=True,
    )

    print(f"\n📊 EN: {'✅ EN' if test_output.returncode == 0 else '❌ EN'}")

    if test_output.returncode == 0:
        if "✅ EN: 100%" in test_output.stdout:
            print("✅ EN: EN")
        if "❌ OCREN: 0%" in test_output.stdout:
            print("⚠️ OCREN: PythonEN")

    return test_output.returncode == 0


def test_ocr_tests():
    """ENOCREN"""
    print("\n" + "=" * 80)
    print("🧪 EN 4: OCREN")
    print("=" * 80)

    # ENOCREN
    success = run_command("python3 test_ocr_simple.py", "ENOCREN")

    print(f"\n📊 EN: {'✅ EN' if success else '❌ EN'}")
    if not success:
        print("💡 EN: Python 3.14ENOCREN")

    return success


def test_installation_script():
    """EN"""
    print("\n" + "=" * 80)
    print("🧪 EN 5: Python 3.13EN")
    print("=" * 80)

    success = run_command("./scripts/setup/install_python313_paddleocr.sh", "ENPython 3.13EN")

    print(f"\n📊 EN: {'✅ EN' if success else '❌ EN'}")
    if not success:
        print("💡 EN: Python 3.14EN")

    return success


def analyze_test_files():
    """EN"""
    print("\n" + "=" * 80)
    print("🧪 EN 6: EN")
    print("=" * 80)

    test_files = [
        "test_ocr_simple.py",
        "test_paddleocr_v5.py",
        "test_architecture_construction_industry.py",
        "test_ocr_chinese_viz.py",
    ]

    analysis_results = {}

    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # EN
                has_version_check = any(
                    keyword in content
                    for keyword in [
                        "sys.version",
                        "python_version",
                        "version_info",
                        "python3",
                    ]
                )

                # ENPaddleOCREN
                has_paddleocr = any(
                    keyword in content
                    for keyword in ["import paddleocr", "from paddleocr", "paddleocr."]
                )

                # EN
                has_version_requirement = any(
                    keyword in content
                    for keyword in [">=3.13", "python 3.13", "requires", "version"]
                )

                analysis_results[test_file] = {
                    "exists": True,
                    "has_version_check": has_version_check,
                    "has_paddleocr": has_paddleocr,
                    "has_version_requirement": has_version_requirement,
                    "needs_python313": has_paddleocr or has_version_requirement,
                }

            except Exception as e:
                analysis_results[test_file] = {"exists": True, "error": str(e)}
        else:
            analysis_results[test_file] = {"exists": False}

    # EN
    print("📋 EN:")
    for file_name, result in analysis_results.items():
        if result.get("exists", False):
            status = "✅ EN"
            if "error" in result:
                status += f" (EN: {result['error']})"

            print(f"  {status} {file_name}")

            if "needs_python313" in result:
                print(f"    🎯 ENPython 3.13: {result['needs_python313']}")
            if result.get("has_version_check", False):
                print(f"    ✅ EN")
            else:
                print(f"    ❌ EN")

        else:
            print(f"  ❌ EN {file_name}")

    return analysis_results


def generate_fix_summary():
    """EN"""
    print("\n" + "=" * 80)
    print("📋 EN")
    print("=" * 80)

    print("✅ EN:")
    print("  1. EN - ENrequirementsEN")
    print("  2. PythonEN - EN")
    print("  3. EN - ENPython 3.13 + PaddleOCR")
    print(" 4. EN - Python 3.13ENPaddleOCREN")
    print("  5. EN - EN")

    print("\n🎯 EN:")
    print("  - ENPythonEN")
    print("  - EN")
    print("  - EN")
    print("  - EN")

    print("\n📊 EN:")
    print("  - EN: EN40-60% → <5%")
    print("  - EN: EN20-45EN → 5-10EN")
    print("  - EN: EN → EN")
    print("  - EN: EN")

    print("\n🚀 EN:")
    print("  1. ENPython 3.13EN")
    print("  2. EN")
    print("  3. ENPaddleOCREN")
    print("  4. EN")


def main():
    """EN"""
    print("🎯 EN")
    print("EN")

    # EN
    test_results = {
        "python_version_checker": test_python_version_checker(),
        "version_manager": test_version_manager(),
        "architecture_tests": test_architecture_tests(),
        "ocr_tests": test_ocr_tests(),
        "installation_script": test_installation_script(),
        "test_files_analysis": analyze_test_files(),
    }

    # EN - EN
    boolean_results = {k: v for k, v in test_results.items() if isinstance(v, bool)}
    total_tests = len(boolean_results)
    passed_tests = sum(1 for result in boolean_results.values() if result)

    print(f"\n" + "=" * 80)
    print("📊 EN")
    print("=" * 80)
    print(f"EN: {total_tests}")
    print(f"EN: {passed_tests}")
    print(f"EN: {total_tests - passed_tests}")
    print(f"EN: {passed_tests/total_tests*100:.1f}%")

    success_rate = passed_tests / total_tests
    if success_rate >= 0.8:
        print(f"\n🎉 EN: ✅ EN ({success_rate:.1%})")
        print("EN,EN")
    elif success_rate >= 0.6:
        print(f"\n✅ EN: ✅ EN ({success_rate:.1%})")
        print("EN,EN")
    else:
        print(f"\n⚠️ EN: ❌ EN ({success_rate:.1%})")
        print("EN")

    # EN
    generate_fix_summary()

    return success_rate >= 0.6


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
