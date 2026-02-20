# Industry AI Flow - 问题追踪表（Issues Tracker）

**创建日期**: 2026-02-13 00:50 MST
**最后更新**: 2026-02-13 00:50 MST
**状态**: 进行中

---

## 📋 问题统计

| 优先级 | 总数 | 已解决 | 进行中 | 待解决 |
|--------|------|--------|--------|--------|
| **P0** | 0 | 0 | 0 | 0 |
| **P1** | 3 | 0 | 0 | 3 |
| **P2** | 4 | 0 | 0 | 4 |
| **P3** | 2 | 0 | 0 | 2 |
| **总计** | 9 | 0 | 0 | 9 |

---

## 🚨 P1 - 严重问题（High Priority）

### P1-1: 缺少代码质量工具

**问题描述**: pylint、mypy、pytest未安装

**影响**:
- 无法自动检查代码质量
- 无法进行类型检查
- 无法运行单元测试

**优先级**: P1（严重）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-02-13（1小时内）

**解决方案**:
```bash
# 安装代码质量工具
pip install pylint mypy pytest pytest-cov

# 运行pylint
pylint backend/ --fail-under=8.0

# 运行mypy
mypy backend/ --strict

# 运行pytest
pytest tests/ --cov=backend --cov-report=html --cov-fail-under=80
```

**验证方法**:
```bash
# 验证pylint安装
pylint --version

# 验证mypy安装
mypy --version

# 验证pytest安装
pytest --version
```

**相关文件**:
- requirements/base.txt（需要添加pylint、mypy、pytest）

**相关Issue**: 无

**相关PR**: 无

---

### P1-2: 缺少groundedness_checker.py

**问题描述**: backend/safety/groundedness_checker.py文件缺失

**影响**:
- 无法进行安全检查
- 无法检测生成内容的真实性

**优先级**: P1（严重）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-02-13（1天内）

**解决方案**:
创建`backend/safety/groundedness_checker.py`文件

**实现示例**:
```python
"""
Groundedness Checker - 检查生成内容的真实性
"""

from typing import Dict, List, Optional
from pydantic import BaseModel

class GroundednessCheckRequest(BaseModel):
    """真实性检查请求"""
    generated_text: str
    context: List[str]
    threshold: float = 0.7

class GroundednessCheckResult(BaseModel):
    """真实性检查结果"""
    is_grounded: bool
    confidence_score: float
    ungrounded_claims: List[str]
    details: Dict[str, any]

class GroundednessChecker:
    """真实性检查器"""
    
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name
    
    def check(self, request: GroundednessCheckRequest) -> GroundednessCheckResult:
        """
        检查生成内容的真实性
        
        Args:
            request: 真实性检查请求
            
        Returns:
            真实性检查结果
        """
        # TODO: 实现真实性检查逻辑
        # 1. 提取生成内容中的声明
        # 2. 检查每个声明是否在上下文中得到支持
        # 3. 计算置信度分数
        # 4. 返回检查结果
        
        ungrounded_claims = []
        confidence_score = 0.8  # 示例值
        is_grounded = confidence_score >= request.threshold
        
        return GroundednessCheckResult(
            is_grounded=is_grounded,
            confidence_score=confidence_score,
            ungrounded_claims=ungrounded_claims,
            details={}
        )
    
    def extract_claims(self, text: str) -> List[str]:
        """
        提取文本中的声明
        
        Args:
            text: 输入文本
            
        Returns:
            声明列表
        """
        # TODO: 实现声明提取逻辑
        # 可以使用NLP工具（spaCy、NLTK）或LLM
        pass
    
    def verify_claim(self, claim: str, context: List[str]) -> bool:
        """
        验证声明是否在上下文中得到支持
        
        Args:
            claim: 声明
            context: 上下文
            
        Returns:
            是否得到支持
        """
        # TODO: 实现声明验证逻辑
        # 可以使用语义相似度或LLM
        pass

# 使用示例
if __name__ == "__main__":
    checker = GroundednessChecker()
    request = GroundednessCheckRequest(
        generated_text="The capital of France is Paris.",
        context=["France is a country in Europe.", "Paris is the capital of France."]
    )
    result = checker.check(request)
    print(result)
```

**验证方法**:
```bash
# 运行测试
pytest tests/safety/test_groundedness_checker.py -v

# 手动测试
python backend/safety/groundedness_checker.py
```

**相关文件**:
- backend/safety/__init__.py（需要导入GroundednessChecker）
- tests/safety/test_groundedness_checker.py（需要创建测试）

**相关Issue**: 无

**相关PR**: 无

---

### P1-3: 缺少E2E测试

**问题描述**: tests/e2e目录不存在

**影响**:
- 无法进行端到端测试
- 无法验证完整的用户流程

**优先级**: P1（严重）

**负责人**: 测试团队

**状态**: 待解决

**预计完成时间**: 2026-02-15（3天内）

**解决方案**:
创建`tests/e2e/`目录和E2E测试用例

**实现示例**:
```python
# tests/e2e/test_rag_e2e.py
"""
RAG系统端到端测试
"""

import pytest
from httpx import AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_rag_end_to_end():
    """
    测试RAG系统端到端流程：
    1. 上传文档
    2. 等待文档处理完成
    3. 执行查询
    4. 验证查询结果
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # 1. 上传文档
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": f}
            )
        assert response.status_code == 200
        document_id = response.json()["document_id"]
        
        # 2. 等待文档处理完成
        # TODO: 实现轮询逻辑，等待文档处理完成
        
        # 3. 执行查询
        response = await client.post(
            "/api/v1/query",
            json={"query": "What is RAG?", "top_k": 5}
        )
        assert response.status_code == 200
        results = response.json()["results"]
        
        # 4. 验证查询结果
        assert len(results) > 0
        assert all(r["score"] > 0 for r in results)

# tests/e2e/test_cost_estimation_e2e.py
"""
成本估算系统端到端测试
"""

@pytest.mark.asyncio
async def test_cost_estimation_end_to_end():
    """
    测试成本估算系统端到端流程：
    1. 训练成本估算模型
    2. 执行成本估算
    3. 验证估算结果
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # 1. 训练成本估算模型
        response = await client.post(
            "/api/v1/cost-estimation/train",
            json={"model_name": "gpt-4", "epochs": 10}
        )
        assert response.status_code == 200
        training_job_id = response.json()["job_id"]
        
        # 2. 等待训练完成
        # TODO: 实现轮询逻辑，等待训练完成
        
        # 3. 执行成本估算
        response = await client.post(
            "/api/v1/cost-estimation/predict",
            json={
                "task_description": "Summarize a document",
                "model_name": "gpt-4",
                "input_tokens": 1000
            }
        )
        assert response.status_code == 200
        result = response.json()
        
        # 4. 验证估算结果
        assert "estimated_cost" in result
        assert result["estimated_cost"] > 0

# tests/e2e/test_code_generation_e2e.py
"""
代码生成系统端到端测试
"""

@pytest.mark.asyncio
async def test_code_generation_end_to_end():
    """
    测试代码生成系统端到端流程：
    1. 上传数据集
    2. 生成分析代码
    3. 执行代码
    4. 验证执行结果
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # 1. 上传数据集
        with open("tests/fixtures/sample.csv", "rb") as f:
            response = await client.post(
                "/api/v1/data-analysis/upload",
                files={"file": f}
            )
        assert response.status_code == 200
        dataset_id = response.json()["dataset_id"]
        
        # 2. 生成分析代码
        response = await client.post(
            "/api/v1/data-analysis/analyze",
            json={
                "dataset_id": dataset_id,
                "task_description": "Calculate the mean of the data"
            }
        )
        assert response.status_code == 200
        code = response.json()["code"]
        
        # 3. 执行代码
        response = await client.post(
            "/api/v1/code-execution/execute",
            json={"code": code}
        )
        assert response.status_code == 200
        result = response.json()
        
        # 4. 验证执行结果
        assert "output" in result
        assert "error" not in result or result["error"] is None
```

**验证方法**:
```bash
# 运行E2E测试
pytest tests/e2e/ -v

# 运行特定E2E测试
pytest tests/e2e/test_rag_e2e.py -v
```

**相关文件**:
- tests/e2e/__init__.py（需要创建）
- tests/e2e/conftest.py（需要创建测试配置）

**相关Issue**: 无

**相关PR**: 无

---

## ⚠️ P2 - 中等问题（Medium Priority）

### P2-1: 架构文档位置不统一

**问题描述**: ARCHITECTURE.md在项目根目录缺失

**影响**: 文档查找困难

**优先级**: P2（中等）

**负责人**: 文档负责人

**状态**: 待解决

**预计完成时间**: 2026-02-13（1天内）

**解决方案**:
在项目根目录创建`ARCHITECTURE.md`，引用`docs/ARCHITECTURE.md`

```markdown
# Industry AI Flow - 架构文档

本文档已迁移至 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## 快速导航

- [系统架构](docs/ARCHITECTURE.md#系统架构)
- [技术栈](docs/ARCHITECTURE.md#技术栈)
- [模块说明](docs/ARCHITECTURE.md#模块说明)
- [数据流](docs/ARCHITECTURE.md#数据流)

---

**注意**: 本文档是docs/ARCHITECTURE.md的引用，实际内容请查看docs/ARCHITECTURE.md
```

**验证方法**:
```bash
# 检查文件是否存在
ls -la ARCHITECTURE.md

# 检查内容
cat ARCHITECTURE.md
```

**相关文件**:
- ARCHITECTURE.md（需要创建）
- docs/ARCHITECTURE.md（已存在）

**相关Issue**: 无

**相关PR**: 无

---

### P2-2: 缺少API文档

**问题描述**: 没有Swagger/OpenAPI文档

**影响**: API使用困难

**优先级**: P2（中等）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-02-15（3天内）

**解决方案**:
FastAPI自动生成API文档（/docs、/redoc）

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Industry AI Flow API",
    description="企业级RAG系统API",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Industry AI Flow API",
        version="1.0.0",
        description="企业级RAG系统API",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

**验证方法**:
```bash
# 启动服务
python -m uvicorn backend.main:app

# 访问API文档
open http://localhost:8000/docs
open http://localhost:8000/redoc
```

**相关文件**:
- backend/main.py（需要添加OpenAPI配置）

**相关Issue**: 无

**相关PR**: 无

---

### P2-3: 缺少模型Fallback机制

**问题描述**: LLM集成没有Fallback机制

**影响**: 模型失败时无法降级

**优先级**: P2（中等）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-02-20（1周内）

**解决方案**:
实现模型Fallback策略

```python
# backend/services/llm_integration/fallback_service.py
"""
Fallback Service - 模型降级策略
"""

from typing import List, Optional
from enum import Enum

class ModelProvider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    ZHIPU = "zhipu"

class FallbackStrategy(Enum):
    """降级策略"""
    # 按优先级降级
    PRIORITY = "priority"
    # 按成本降级（优先使用便宜的模型）
    COST = "cost"
    # 按性能降级（优先使用高性能模型）
    PERFORMANCE = "performance"

class FallbackConfig:
    """Fallback配置"""
    
    # 默认优先级降级顺序
    DEFAULT_PRIORITY = [
        ModelProvider.ANTHROPIC,  # 优先使用Claude
        ModelProvider.OPENAI,      # 降级到GPT-4
        ModelProvider.OLLAMA,      # 降级到本地模型
        ModelProvider.LLAMA_CPP,   # 降级到本地模型
    ]
    
    def __init__(
        self,
        strategy: FallbackStrategy = FallbackStrategy.PRIORITY,
        providers: Optional[List[ModelProvider]] = None,
        max_retries: int = 3
    ):
        self.strategy = strategy
        self.providers = providers or self.DEFAULT_PRIORITY
        self.max_retries = max_retries

class FallbackService:
    """Fallback服务"""
    
    def __init__(self, config: FallbackConfig):
        self.config = config
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化所有LLM客户端"""
        # TODO: 初始化所有LLM客户端
        pass
    
    def generate(self, prompt: str, model_name: str = None) -> str:
        """
        生成文本，支持Fallback
        
        Args:
            prompt: 提示词
            model_name: 模型名称（可选）
            
        Returns:
            生成的文本
        """
        last_error = None
        
        for provider in self.config.providers:
            try:
                # 尝试使用当前提供商生成
                response = self._try_generate(provider, prompt, model_name)
                return response
            except Exception as e:
                last_error = e
                # 记录错误，继续尝试下一个提供商
                continue
        
        # 所有提供商都失败
        raise Exception(f"All providers failed: {last_error}")
    
    def _try_generate(self, provider: ModelProvider, prompt: str, model_name: str) -> str:
        """
        尝试使用指定提供商生成
        
        Args:
            provider: 提供商
            prompt: 提示词
            model_name: 模型名称
            
        Returns:
            生成的文本
        """
        # TODO: 实现具体的生成逻辑
        pass

# 使用示例
if __name__ == "__main__":
    config = FallbackConfig(strategy=FallbackStrategy.PRIORITY)
    service = FallbackService(config)
    
    try:
        response = service.generate("Hello, world!")
        print(response)
    except Exception as e:
        print(f"Error: {e}")
```

**验证方法**:
```bash
# 运行测试
pytest tests/llm_integration/test_fallback_service.py -v

# 手动测试
python backend/services/llm_integration/fallback_service.py
```

**相关文件**:
- backend/services/llm_integration/fallback_service.py（需要创建）
- tests/llm_integration/test_fallback_service.py（需要创建测试）

**相关Issue**: 无

**相关PR**: 无

---

### P2-4: 缺少RAG评估指标

**问题描述**: 没有RAGAS评估

**影响**: 无法评估RAG质量

**优先级**: P2（中等）

**负责人**: AI团队

**状态**: 待解决

**预计完成时间**: 2026-02-20（1周内）

**解决方案**:
集成RAGAS评估

```bash
# 安装RAGAS
pip install ragas

# 创建评估脚本
# scripts/evaluation/evaluate_rag.py
```

```python
# scripts/evaluation/evaluate_rag.py
"""
RAG评估脚本 - 使用RAGAS评估RAG质量
"""

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_relevancy,
    context_precision
)
from datasets import Dataset

def evaluate_rag():
    """
    评估RAG质量
    """
    # 准备评估数据
    data = {
        "question": [
            "What is RAG?",
            "How does vector search work?",
            "What is embedding?"
        ],
        "answer": [
            "RAG stands for Retrieval-Augmented Generation.",
            "Vector search uses embeddings to find similar documents.",
            "Embedding is a vector representation of text."
        ],
        "contexts": [
            ["RAG is a technique that combines retrieval and generation."],
            ["Vector search converts text to vectors and finds similar ones."],
            ["Embedding maps text to high-dimensional vectors."]
        ],
        "ground_truth": [
            "RAG stands for Retrieval-Augmented Generation.",
            "Vector search uses embeddings to find similar documents.",
            "Embedding is a vector representation of text."
        ]
    }
    
    dataset = Dataset.from_dict(data)
    
    # 运行评估
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_relevancy,
            context_precision
        ]
    )
    
    # 打印结果
    print(result)
    
    # 返回结果
    return result

if __name__ == "__main__":
    evaluate_rag()
```

**验证方法**:
```bash
# 运行评估
python scripts/evaluation/evaluate_rag.py

# 查看结果
cat results/rag_evaluation.json
```

**相关文件**:
- scripts/evaluation/evaluate_rag.py（需要创建）
- requirements/base.txt（需要添加ragas）

**相关Issue**: 无

**相关PR**: 无

---

## 📝 P3 - 低级问题（Low Priority）

### P3-1: 缺少类型注解

**问题描述**: 部分代码缺少类型注解

**影响**: 代码可读性和IDE支持

**优先级**: P3（低级）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-03-13（1个月内）

**解决方案**:
添加类型注解（Type Hints）

**示例**:
```python
# 之前
def search(query, top_k=5):
    results = []
    # ...
    return results

# 之后
from typing import List, Dict, Optional
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

def search(request: SearchRequest) -> List[Document]:
    results: List[Document] = []
    # ...
    return results
```

**验证方法**:
```bash
# 运行mypy检查
mypy backend/ --strict
```

**相关文件**:
- backend/**/*.py（所有Python文件）

**相关Issue**: 无

**相关PR**: 无

---

### P3-2: 缺少文档字符串

**问题描述**: 部分函数缺少Docstrings

**影响**: 代码可读性

**优先级**: P3（低级）

**负责人**: 开发团队

**状态**: 待解决

**预计完成时间**: 2026-03-13（1个月内）

**解决方案**:
添加Docstrings（Google、NumPy或Sphinx风格）

**示例**:
```python
# Google风格
def search(query: str, top_k: int = 5) -> List[Document]:
    """
    搜索相关文档
    
    Args:
        query: 查询字符串
        top_k: 返回结果数量
        
    Returns:
        相关文档列表
        
    Raises:
        ValueError: 如果query为空
        
    Examples:
        >>> search("What is RAG?", top_k=5)
        [Document(...), Document(...)]
    """
    pass
```

**验证方法**:
```bash
# 使用pydocstyle检查
pip install pydocstyle
pydocstyle backend/
```

**相关文件**:
- backend/**/*.py（所有Python文件）

**相关Issue**: 无

**相关PR**: 无

---

## 📈 进度跟踪

### 本周进度（2026-02-13 - 2026-02-19）

| 任务 | 负责人 | 状态 | 预计完成日期 |
|------|--------|------|--------------|
| P1-1: 安装代码质量工具 | 开发团队 | 待开始 | 2026-02-13 |
| P1-2: 创建groundedness_checker.py | 开发团队 | 待开始 | 2026-02-13 |
| P1-3: 添加E2E测试 | 测试团队 | 待开始 | 2026-02-15 |
| P2-1: 统一架构文档位置 | 文档负责人 | 待开始 | 2026-02-13 |
| P2-2: 添加API文档 | 开发团队 | 待开始 | 2026-02-15 |
| P2-3: 实现模型Fallback机制 | 开发团队 | 待开始 | 2026-02-20 |
| P2-4: 集成RAGAS评估 | AI团队 | 待开始 | 2026-02-20 |

---

## 📝 更新日志

### 2026-02-13 00:50 MST
- 创建问题追踪表
- 添加9个问题（3个P1，4个P2，2个P3）

---

## 📞 联系方式

**评审专家**: AI行业专家 & 资深软件架构师
**创建日期**: 2026-02-13 00:50 MST
**最后更新**: 2026-02-13 00:50 MST

---

## 🎯 下一步行动

1. **立即开始P1问题修复**（2026-02-13）
2. **1周后检查P1问题解决情况**（2026-02-20）
3. **2周后检查P2问题解决情况**（2026-02-27）
4. **1个月后检查P3问题解决情况**（2026-03-13）

---

**问题追踪表版本**: v1.0
**最后更新**: 2026-02-13 00:50 MST
