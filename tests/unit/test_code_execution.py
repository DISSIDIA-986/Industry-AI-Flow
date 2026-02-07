"""
测试代码执行系统

测试内容:
1. Docker环境检测
2. 代码验证器测试
3. 基础代码执行
4. 数据分析代码
5. 可视化代码
6. LangChain工具集成
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent

from backend.services.code_executor import (
    CodeExecutionError,
    code_executor,
    validate_code,
)
from backend.tools.code_execution import (
    code_execution_tool,
    code_validation_tool,
    get_execution_environment_info,
)


def test_environment():
    """测试执行环境"""
    print("=" * 60)
    print("测试 1: 执行环境检测")
    print("=" * 60)

    try:
        info = get_execution_environment_info.invoke({})
        print(f"✅ Docker可用: {info['docker_available']}")
        print(f"📊 资源限制:")
        for key, value in info["resource_limits"].items():
            print(f"   - {key}: {value}")
        print(f"📦 可用库: {', '.join(info['available_libraries'][:5])}...")
        print(f"🛡️  安全特性: {len(info['security_features'])} 项")
        return True
    except Exception as e:
        print(f"❌ 环境检测失败: {e}")
        return False


def test_code_validator():
    """测试代码验证器"""
    print("\n" + "=" * 60)
    print("测试 2: 代码验证器")
    print("=" * 60)

    # 测试用例
    test_cases = [
        ("import pandas as pd\nprint('Hello')", True, "合法代码"),
        ("import os\nos.system('ls')", False, "危险操作"),
        ("import subprocess\nsubprocess.run(['ls'])", False, "子进程调用"),
        ("print(x", False, "语法错误"),
    ]

    passed = 0
    for code, should_pass, description in test_cases:
        result = validate_code(code)
        is_valid = result.is_valid

        if is_valid == should_pass:
            print(f"✅ {description}: {'通过' if is_valid else '拒绝'}")
            passed += 1
        else:
            print(
                f"❌ {description}: 预期{'通过' if should_pass else '拒绝'}, 实际{'通过' if is_valid else '拒绝'}"
            )
            if not is_valid:
                print(f"   错误: {result.error}")

    print(f"\n验证器测试: {passed}/{len(test_cases)} 通过")
    return passed == len(test_cases)


def test_basic_execution():
    """测试基础代码执行"""
    print("\n" + "=" * 60)
    print("测试 3: 基础代码执行")
    print("=" * 60)

    if code_executor is None:
        print("❌ 代码执行器不可用，跳过测试")
        return False

    code = """
import pandas as pd
import numpy as np

# 创建示例数据
data = pd.DataFrame({
    'A': np.random.randn(10),
    'B': np.random.randn(10)
})

print("DataFrame shape:", data.shape)
print("\\nFirst 3 rows:")
print(data.head(3))
print("\\nSummary statistics:")
print(data.describe())
"""

    try:
        result = code_executor.execute_code(code)
        if result["success"]:
            print(f"✅ 代码执行成功 ({result['execution_time']:.2f}秒)")
            print(f"📤 输出:")
            print(result["stdout"])
            return True
        else:
            print(f"❌ 执行失败: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False


def test_visualization():
    """测试可视化代码"""
    print("\n" + "=" * 60)
    print("测试 4: 数据可视化")
    print("=" * 60)

    if code_executor is None:
        print("❌ 代码执行器不可用，跳过测试")
        return False

    code = """
import matplotlib.pyplot as plt
import numpy as np

# 生成数据
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# 创建图表
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='sin(x)', linewidth=2)
plt.plot(x, y2, label='cos(x)', linewidth=2)
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True, alpha=0.3)

# 保存图表
plt.savefig('test_plot.png', dpi=150, bbox_inches='tight')
print("Plot saved successfully to test_plot.png")
"""

    try:
        result = code_executor.execute_code(code)
        if result["success"]:
            print(f"✅ 可视化执行成功 ({result['execution_time']:.2f}秒)")
            print(f"📊 生成文件: {len(result['visualizations'])} 个")
            for viz in result["visualizations"]:
                print(f"   - {viz}")
            return True
        else:
            print(f"❌ 执行失败: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False


def test_langchain_tools():
    """测试LangChain工具集成"""
    print("\n" + "=" * 60)
    print("测试 5: LangChain工具集成")
    print("=" * 60)

    if code_executor is None:
        print("❌ 代码执行器不可用，跳过测试")
        return False

    # 测试代码验证工具
    print("\n5.1 代码验证工具:")
    validation_result = code_validation_tool.invoke(
        {"code": "import pandas as pd\nprint('Hello')"}
    )
    print(f"   验证结果: {'✅ 有效' if validation_result['valid'] else '❌ 无效'}")

    # 测试代码执行工具
    print("\n5.2 代码执行工具:")
    exec_result = code_execution_tool.invoke(
        {
            "code": "import numpy as np\nprint('NumPy version:', np.__version__)",
            "timeout": 30,
        }
    )
    if exec_result["success"]:
        print(f"   ✅ 执行成功")
        print(f"   输出: {exec_result['stdout'].strip()}")
        return True
    else:
        print(f"   ❌ 执行失败: {exec_result.get('error', 'Unknown')}")
        return False


def test_ml_example():
    """测试机器学习示例"""
    print("\n" + "=" * 60)
    print("测试 6: 机器学习代码")
    print("=" * 60)

    if code_executor is None:
        print("❌ 代码执行器不可用，跳过测试")
        return False

    code = """
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

# 生成数据
np.random.seed(42)
X = np.random.randn(100, 3)
y = X @ np.array([2.5, -1.5, 0.8]) + np.random.randn(100) * 0.1

# 分割数据
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 训练模型
model = LinearRegression()
model.fit(X_train, y_train)

# 评估
y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)

print(f"Model coefficients: {model.coef_}")
print(f"R² Score: {r2:.4f}")
print("✅ Model training completed successfully!")
"""

    try:
        result = code_executor.execute_code(code, timeout=60)
        if result["success"]:
            print(f"✅ ML代码执行成功 ({result['execution_time']:.2f}秒)")
            print(f"📤 输出:")
            print(result["stdout"])
            return True
        else:
            print(f"❌ 执行失败: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("代码执行系统测试套件")
    print("=" * 60)

    results = {
        "环境检测": test_environment(),
        "代码验证": test_code_validator(),
        "基础执行": test_basic_execution(),
        "数据可视化": test_visualization(),
        "LangChain工具": test_langchain_tools(),
        "机器学习": test_ml_example(),
    }

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
