# 测试指南

本文档介绍 Industry AI Flow 项目的测试框架和测试方法。

## 🧪 测试架构

### 测试套件概览
项目包含以下主要测试套件：

1. **问题分类测试** - 验证问题分类器的准确性
2. **向量检索测试** - 测试文档检索性能
3. **回答生成测试** - 评估AI回答质量
4. **OCR集成测试** - 验证OCR文字识别功能
5. **代码执行测试** - 测试数据分析能力
6. **界面测试** - 验证用户界面功能
7. **聊天测试** - 测试聊天界面稳定性
8. **反馈测试** - 验证用户反馈学习效果

## 🚀 运行测试

### 综合测试
```bash
# 运行所有测试
python tests/run_comprehensive_tests.py

# 运行特定类别测试
python tests/run_comprehensive_tests.py --categories core_functionality

# 按优先级运行测试
python tests/run_comprehensive_tests.py --priorities 1 2

# 并行运行测试
python tests/run_comprehensive_tests.py --parallel --max-workers 4
```

### 单独测试模块
```bash
# 问题分类测试
python tests/test_question_classification.py

# 向量检索测试
python tests/test_vector_retrieval.py

# 回答生成测试
python tests/test_answer_generation.py
```

### pytest 运行
```bash
# 运行所有 pytest 测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_question_classification.py -v

# 运行特定测试函数
pytest tests/test_question_classification.py::test_question_classification_comprehensive -v
```

## 📊 测试报告

### 报告生成
测试完成后会自动生成详细报告：
- 控制台输出：实时显示测试进度和结果
- JSON报告：保存到 `test_reports/` 目录
- 质量评分：系统整体质量评估

### 报告内容
- **执行摘要**：测试数量、成功率、执行时间
- **分类表现**：各功能类别的测试结果
- **覆盖率分析**：测试覆盖率统计
- **失败分析**：失败测试的详细信息
- **改进建议**：基于测试结果的优化建议

## 🔧 测试配置

### 环境变量
```bash
# 测试环境
export TEST_ENV=development

# 测试数据库
export TEST_DB_URL=sqlite:///test.db

# 日志级别
export LOG_LEVEL=INFO
```

### 配置文件
```python
# tests/config.py
TEST_CONFIG = {
    "timeout": 300,
    "retry_attempts": 3,
    "mock_external_services": True,
    "parallel_workers": 4
}
```

## 📝 编写测试

### 测试结构
```python
import pytest
import asyncio
from your_module import YourClass

class TestYourClass:
    @pytest.fixture
    def setup_test(self):
        # 测试前准备
        setup_data = {}
        yield setup_data
        # 测试后清理
        pass

    @pytest.mark.asyncio
    async def test_basic_functionality(self, setup_test):
        # 测试基础功能
        result = await your_function()
        assert result.success == True

    def test_edge_cases(self, setup_test):
        # 测试边界情况
        with pytest.raises(ValueError):
            your_function(invalid_input)
```

### Mock 使用
```python
from unittest.mock import Mock, patch

@pytest.mark.asyncio
async def test_with_mock():
    # Mock 外部服务
    with patch('your_module.external_service') as mock_service:
        mock_service.return_value = {"status": "success"}
        result = await your_function()
        assert result.success == True
```

### 参数化测试
```python
@pytest.mark.parametrize("input_data,expected_output", [
    ("简单问题", "简单回答"),
    ("复杂问题", "详细回答"),
    ("错误输入", None)
])
async def test_question_classification(input_data, expected_output):
    result = await classify_question(input_data)
    assert result == expected_output
```

## 🔍 调试测试

### 调试技巧
1. **详细输出**：使用 `-v` 参数显示详细测试信息
2. **断点调试**：在测试中添加 `breakpoint()` 或 `import pdb; pdb.set_trace()`
3. **日志输出**：增加日志输出来跟踪执行流程

### 常见问题
```python
# 异步测试问题
@pytest.mark.asyncio
async def test_async_function():
    # 确保使用 asyncio 装饰器
    result = await async_function()
    assert result is not None

# Mock 问题
def test_with_proper_mock():
    # 确保 mock 配置正确
    mock_service = Mock(return_value="expected_value")
    with patch('module.service', mock_service):
        result = function_using_service()
        assert result == "expected_value"
```

## 📈 性能测试

### 基准测试
```python
import time

def test_performance():
    start_time = time.time()
    result = expensive_function()
    execution_time = time.time() - start_time

    assert execution_time < 5.0  # 应在5秒内完成
    assert result.success == True
```

### 压力测试
```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    tasks = [make_request() for _ in range(100)]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.success)
    assert success_count >= 95  # 95%的请求应该成功
```

## 🔗 持续集成

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python tests/run_comprehensive_tests.py
```

## 📋 测试清单

在提交代码前，确保：
- [ ] 所有新功能都有对应测试
- [ ] 现有测试仍然通过
- [ ] 测试覆盖率达到要求
- [ ] 性能测试通过基准
- [ ] 集成测试验证完整流程

## 🆘 获取帮助

- 查看现有测试用例了解最佳实践
- 参考测试框架文档
- 在 Issues 中提出测试相关问题
- 参与代码审查获得反馈

---

*测试是质量保证的重要环节，请认真对待每一项测试！*