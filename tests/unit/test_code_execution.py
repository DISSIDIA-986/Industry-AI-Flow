"""
EN

EN:
1. DockerEN
2. EN
3. EN
4. EN
5. EN
6. LangChainEN
"""

import sys
from pathlib import Path

# EN
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
    """EN"""
    print("=" * 60)
    print("EN 1: EN")
    print("=" * 60)

    try:
        info = get_execution_environment_info.invoke({})
        print(f"✅ DockerEN: {info['docker_available']}")
        print(f"📊 EN:")
        for key, value in info["resource_limits"].items():
            print(f"   - {key}: {value}")
        print(f"📦 EN: {', '.join(info['available_libraries'][:5])}...")
        print(f"🛡️  EN: {len(info['security_features'])} EN")
        return True
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_code_validator():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 2: EN")
    print("=" * 60)

    # EN
    test_cases = [
        ("import pandas as pd\nprint('Hello')", True, "EN"),
        ("import os\nos.system('ls')", False, "EN"),
        ("import subprocess\nsubprocess.run(['ls'])", False, "EN"),
        ("print(x", False, "EN"),
    ]

    passed = 0
    for code, should_pass, description in test_cases:
        result = validate_code(code)
        is_valid = result.is_valid

        if is_valid == should_pass:
            print(f"✅ {description}: {'EN' if is_valid else 'EN'}")
            passed += 1
        else:
            print(
                f"❌ {description}: EN{'EN' if should_pass else 'EN'}, EN{'EN' if is_valid else 'EN'}"
            )
            if not is_valid:
                print(f"   EN: {result.error}")

    print(f"\nEN: {passed}/{len(test_cases)} EN")
    return passed == len(test_cases)


def test_basic_execution():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 3: EN")
    print("=" * 60)

    if code_executor is None:
        print("❌ EN,EN")
        return False

    code = """
import pandas as pd
import numpy as np

# EN
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
            print(f"✅ EN ({result['execution_time']:.2f}EN)")
            print(f"📤 EN:")
            print(result["stdout"])
            return True
        else:
            print(f"❌ EN: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_visualization():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 4: EN")
    print("=" * 60)

    if code_executor is None:
        print("❌ EN,EN")
        return False

    code = """
import matplotlib.pyplot as plt
import numpy as np

# EN
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# EN
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='sin(x)', linewidth=2)
plt.plot(x, y2, label='cos(x)', linewidth=2)
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Trigonometric Functions')
plt.legend()
plt.grid(True, alpha=0.3)

# EN
plt.savefig('test_plot.png', dpi=150, bbox_inches='tight')
print("Plot saved successfully to test_plot.png")
"""

    try:
        result = code_executor.execute_code(code)
        if result["success"]:
            print(f"✅ EN ({result['execution_time']:.2f}EN)")
            print(f"📊 EN: {len(result['visualizations'])} EN")
            for viz in result["visualizations"]:
                print(f"   - {viz}")
            return True
        else:
            print(f"❌ EN: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def test_langchain_tools():
    """ENLangChainEN"""
    print("\n" + "=" * 60)
    print("EN 5: LangChainEN")
    print("=" * 60)

    if code_executor is None:
        print("❌ EN,EN")
        return False

    # EN
    print("\n5.1 EN:")
    validation_result = code_validation_tool.invoke(
        {"code": "import pandas as pd\nprint('Hello')"}
    )
    print(f"   EN: {'✅ EN' if validation_result['valid'] else '❌ EN'}")

    # EN
    print("\n5.2 EN:")
    exec_result = code_execution_tool.invoke(
        {
            "code": "import numpy as np\nprint('NumPy version:', np.__version__)",
            "timeout": 30,
        }
    )
    if exec_result["success"]:
        print(f"   ✅ EN")
        print(f"   EN: {exec_result['stdout'].strip()}")
        return True
    else:
        print(f"   ❌ EN: {exec_result.get('error', 'Unknown')}")
        return False


def test_ml_example():
    """EN"""
    print("\n" + "=" * 60)
    print("EN 6: EN")
    print("=" * 60)

    if code_executor is None:
        print("❌ EN,EN")
        return False

    code = """
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

# EN
np.random.seed(42)
X = np.random.randn(100, 3)
y = X @ np.array([2.5, -1.5, 0.8]) + np.random.randn(100) * 0.1

# EN
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# EN
model = LinearRegression()
model.fit(X_train, y_train)

# EN
y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)

print(f"Model coefficients: {model.coef_}")
print(f"R² Score: {r2:.4f}")
print("✅ Model training completed successfully!")
"""

    try:
        result = code_executor.execute_code(code, timeout=60)
        if result["success"]:
            print(f"✅ MLEN ({result['execution_time']:.2f}EN)")
            print(f"📤 EN:")
            print(result["stdout"])
            return True
        else:
            print(f"❌ EN: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ EN: {e}")
        return False


def main():
    """EN"""
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    results = {
        "EN": test_environment(),
        "EN": test_code_validator(),
        "EN": test_basic_execution(),
        "EN": test_visualization(),
        "LangChainEN": test_langchain_tools(),
        "EN": test_ml_example(),
    }

    # EN
    print("\n" + "=" * 60)
    print("EN")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {name}")

    print(f"\nEN: {passed}/{total} EN ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 EN!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} EN")
        return 1


if __name__ == "__main__":
    sys.exit(main())
