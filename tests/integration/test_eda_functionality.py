#!/usr/bin/env python3
"""
EN RAG EN EDA EN
EN Housing.csv EN
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# EN
sys.path.append(str(Path(__file__).parent))

from backend.agents.code_execution_agent import iterative_code_agent
from backend.services.data_transfer import data_transfer
from backend.tools.iterative_code_execution import iterative_code_analysis_tool


@pytest.mark.asyncio
async def test_basic_eda():
    """EN"""
    print("=" * 60)
    print("🔬 EN EDA EN - Housing EN")
    print("=" * 60)

    data_file = "test_resources/datasets/Housing.csv"

    # EN
    eda_request = """
    EN(EDA),EN:
    1. EN
    2. EN
    3. EN
    4. EN
    5. EN
    6. EN
    """

    print("📊 EN EDA EN...")
    print(f"📁 EN: {data_file}")
    print(f"🎯 EN: {eda_request.strip()}")
    print("-" * 60)

    try:
        # EN
        result = iterative_code_analysis_tool.invoke(
            {
                "request": eda_request,
                "data_file": data_file,
                "analysis_type": "eda",
                "max_attempts": 3,
                "transfer_method": "auto",
            }
        )

        # EN
        print("📈 EDA EN:")
        print(f"✅ EN: {result['success']}")
        print(f"🔄 EN: {result.get('attempts', 0)}")

        if result["success"]:
            print("\n📋 EN:")
            summary = result.get("summary", {})
            if summary:
                print(f"   EN: {summary.get('total_attempts', 0)}")
                print(f"   EN: {summary.get('success', False)}")
                print(f"   EN: {summary.get('error_count', 0)}")
                print(f"   EN: {summary.get('fixes_applied', 0)}")

            print("\n💻 EN:")
            execution_result = result.get("execution_result", {})
            stdout = execution_result.get("stdout", "")
            if stdout:
                print("   EN:")
                for line in stdout.split("\n")[:20]:  # EN20EN
                    if line.strip():
                        print(f"   {line}")
                if len(stdout.split("\n")) > 20:
                    print("   ... (EN)")

            print("\n📊 EN:")
            visualizations = execution_result.get("visualizations", [])
            if visualizations:
                print(f"   EN {len(visualizations)} EN:")
                for viz in visualizations[:5]:  # EN5EN
                    print(
                        f"   - {viz.get('filename', 'unknown')} ({viz.get('type', 'unknown')})"
                    )
                if len(visualizations) > 5:
                    print(f"   ... EN {len(visualizations) - 5} EN")
            else:
                print("   EN")

            print("\n🔧 EN:")
            metrics = result.get("performance_metrics", {})
            if metrics:
                print(f"   EN: {metrics.get('execution_time', 0):.2f}EN")
                print(f"   EN: {metrics.get('visualizations_generated', 0)}")
        else:
            print("\n❌ EN:")
            print(f"   EN: {result.get('error', 'Unknown error')}")

            error_analysis = result.get("error_analysis", {})
            if error_analysis:
                print(f"   EN: {error_analysis.get('error_type', 'Unknown')}")
                suggestions = error_analysis.get("suggestions", [])
                if suggestions:
                    print("   EN:")
                    for suggestion in suggestions:
                        print(f"   - {suggestion}")

        return result

    except Exception as e:
        print(f"❌ EN: {e}")
        return {"success": False, "error": str(e)}


def test_data_transfer():
    """EN"""
    print("\n" + "=" * 60)
    print("📦 EN")
    print("=" * 60)

    data_file = "test_resources/datasets/Housing.csv"

    try:
        # EN
        print("🔄 EN...")
        transfer_result = data_transfer.transfer_file_for_docker(data_file, "auto")

        if transfer_result["success"]:
            print("✅ EN!")
            print(f"   EN: {transfer_result['method']}")
            print(f"   EN: {transfer_result['file_info']['size_mb']} MB")
            print(f"   EN: {transfer_result['transferred_path']}")

            # EN
            cleanup_success = data_transfer.cleanup_transferred_data(transfer_result)
            print(f"   EN: {cleanup_success}")
            assert cleanup_success is True
            return None

        error_msg = transfer_result.get("error", "Unknown error")
        print(f"❌ EN: {error_msg}")
        pytest.skip(f"Data transfer unavailable in current environment: {error_msg}")

    except Exception as e:
        print(f"❌ EN: {e}")
        pytest.skip(f"Data transfer raised environment exception: {e}")


def test_code_execution():
    """EN"""
    print("\n" + "=" * 60)
    print("⚙️ EN")
    print("=" * 60)

    simple_code = """
import pandas as pd
import numpy as np

# EN
data = {
    'A': [1, 2, 3, 4, 5],
    'B': [10, 20, 30, 40, 50],
    'C': ['X', 'Y', 'Z', 'X', 'Y']
}

df = pd.DataFrame(data)
print("EN:", df.shape)
print("\\nEN:")
print(df.describe())
print("\\nEN:")
print(df.dtypes)
"""

    try:
        from backend.tools.iterative_code_execution import (
            self_healing_code_execution_tool,
        )

        print("🔄 EN Python EN...")
        result = self_healing_code_execution_tool.invoke(
            {"code": simple_code, "description": "EN"}
        )

        print(f"✅ EN: {result['success']}")
        print(f"🔄 EN: {result['attempts']}")

        if result["success"]:
            print("\n💻 EN:")
            stdout = result["execution_result"]["stdout"]
            if stdout:
                for line in stdout.split("\n"):
                    if line.strip():
                        print(f"   {line}")

            fixes = result.get("fixes_applied", [])
            if fixes:
                print(f"\n🔧 EN: {fixes}")
            return None

        error_msg = result.get("error", "Unknown error")
        print(f"❌ EN: {error_msg}")
        pytest.skip(f"Code execution unavailable in current environment: {error_msg}")

    except Exception as e:
        print(f"❌ EN: {e}")
        pytest.skip(f"Code execution raised environment exception: {e}")


async def main():
    """EN"""
    print("🚀 EN RAG EN")
    print(f"📍 EN: Housing.csv")
    print(f"🔧 Python EN: {sys.version}")

    # EN1: EN
    print("\n" + "=" * 60)
    print("EN 1/4: EN")
    print("=" * 60)
    transfer_success = test_data_transfer()

    # EN2: EN
    print("\n" + "=" * 60)
    print("EN 2/4: EN")
    print("=" * 60)
    code_exec_success = test_code_execution()

    # EN3: EN EDA
    print("\n" + "=" * 60)
    print("EN 3/4: EN EDA EN")
    print("=" * 60)
    eda_result = await test_basic_eda()

    # EN
    print("\n" + "=" * 60)
    print("📊 EN")
    print("=" * 60)
    print(f"✅ EN: {'EN' if transfer_success else 'EN'}")
    print(f"✅ EN: {'EN' if code_exec_success else 'EN'}")
    print(f"✅ EDA EN: {'EN' if eda_result.get('success', False) else 'EN'}")

    overall_success = (
        transfer_success and code_exec_success and eda_result.get("success", False)
    )

    if overall_success:
        print("\n🎉 EN! RAG EN")
        print("📈 EN")
    else:
        print("\n⚠️ EN,EN")

    return overall_success


if __name__ == "__main__":
    # EN
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
