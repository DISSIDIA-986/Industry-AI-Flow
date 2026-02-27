"""Unit tests for code execution contracts."""

from __future__ import annotations

import pytest

from backend.services.code_executor import code_executor, validate_code
from backend.tools.code_execution import (
    code_execution_tool,
    code_validation_tool,
    get_execution_environment_info,
)


def test_environment():
    info = get_execution_environment_info.invoke({})

    assert isinstance(info, dict)
    assert "docker_available" in info
    assert "resource_limits" in info
    assert "available_libraries" in info
    assert "security_features" in info


def test_code_validator():
    test_cases = [
        ("import pandas as pd\nprint('ok')", True),
        ("import os\nos.system('ls')", False),
        ("import subprocess\nsubprocess.run(['ls'])", False),
        ("print(x", False),
    ]

    for code, expected_valid in test_cases:
        result = validate_code(code)
        assert result.is_valid is expected_valid


def test_basic_execution():
    if code_executor is None:
        pytest.skip("code executor unavailable in this environment")

    code = """
import pandas as pd
import numpy as np
df = pd.DataFrame({"a": np.arange(5), "b": np.arange(5) * 2})
print(df.shape)
"""
    result = code_executor.execute_code(code)

    assert result["success"] is True
    assert "stdout" in result


def test_visualization():
    if code_executor is None:
        pytest.skip("code executor unavailable in this environment")

    code = """
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 10, 20)
plt.plot(x, np.sin(x))
plt.savefig('test_plot.png')
print('ok')
"""
    result = code_executor.execute_code(code)

    assert result["success"] is True
    assert "visualizations" in result


def test_langchain_tools():
    if code_executor is None:
        pytest.skip("code executor unavailable in this environment")

    validation_result = code_validation_tool.invoke(
        {"code": "import pandas as pd\nprint('ok')"}
    )
    assert validation_result["valid"] is True

    exec_result = code_execution_tool.invoke(
        {"code": "import numpy as np\nprint(np.__version__)", "timeout": 30}
    )
    assert exec_result["success"] is True


def test_ml_example():
    if code_executor is None:
        pytest.skip("code executor unavailable in this environment")

    code = """
import numpy as np
from sklearn.linear_model import LinearRegression
np.random.seed(42)
X = np.random.randn(100, 3)
y = X @ np.array([2.5, -1.5, 0.8]) + np.random.randn(100) * 0.1
model = LinearRegression().fit(X, y)
print(model.coef_)
"""
    result = code_executor.execute_code(code, timeout=60)

    assert result["success"] is True
    assert "stdout" in result
