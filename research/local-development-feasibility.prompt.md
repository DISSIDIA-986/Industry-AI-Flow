# 本地开发可行性方案 — 实施型高质量Prompt（用于Vibe Coding）

> 目的：用此Prompt指导智能编程助手，在本仓库逐步产出可运行的代码与配置，实现 `research/local-development-feasibility.md` 中的阶段性目标（优先完成“Week 1-2：Mac本地极简验证”的落地代码）。

---

## 1. 总体目标

**单一目标**: 在2周内验证Mac本地技术可行性，回答“是否继续”项目决策问题。

### 验收标准（Week 1-2）
- [ ] 文档上传/导入1000份以内测试文档
- [ ] 向量化流程<10分钟（1000份）
- [ ] RAG问答响应<10秒（P95）
- [ ] 准确率>70%（提供简单评测脚本与样例集）

### 成功定义
- 核心管道验证：文档 → 向量化 → 存储 → 检索 → LLM生成（能跑通）
- 在Mac M1/M2/M3 + 16GB RAM环境下性能可接受
- 明确的下一步决策：继续、调整、或放弃

---

## 2. 技术栈

### 强制选型
- **文档处理**: PyMuPDF (PDF) + 纯文本处理（无OCR）
- **向量库**: PostgreSQL + pgvector
- **LLM**: Ollama + qwen2.5:7b
- **后端**: FastAPI
- **前端**: Streamlit（原型）

### 明确禁止（Week 1-2）
- OCR功能（DeepSeek + PaddleOCR）
- RBAC权限系统
- PII数据检测
- AI Agent框架
- 代码执行沙箱

---

## 3. 目录结构

```
.
├── research/
│   ├── best-ai-workflow.plan.md
│   ├── local-development-feasibility.md
│   └── local-development-feasibility.prompt.md  ← 本文件
├── apps/
│   └── streamlit_app/
│       ├── app.py
│       ├── requirements.txt
│       └── README.md
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI应用入口（必需）
│   │   └── v1/
│   │       └── routers/
│   │           ├── rag.py       # RAG查询路由
│   │           └── documents.py # 文档管理路由
│   ├── services/
│   │   ├── ingestion/           # 文档采集/解析/清洗
│   │   │   ├── __init__.py
│   │   │   ├── loaders.py       # PDF/TXT加载器
│   │   │   ├── cleaners.py
│   │   │   └── chunkers.py      # 简单分块
│   │   ├── vectorstore/
│   │   │   ├── __init__.py
│   │   │   └── pgvector_client.py # pgvector操作封装
│   │   ├── embedding/
│   │   │   ├── __init__.py
│   │   │   └── nomic_embed.py   # nomic嵌入模型封装
│   │   └── llm/
│   │       ├── __init__.py
│   │       └── ollama_client.py # Ollama API封装
│   └── tests/                   # Week 2引入
│       ├── unit/
│       │   └── test_ingestion.py
│       └── conftest.py
├── infra/
│   ├── compose/
│   │   └── docker-compose.dev.yaml # Postgres+pgvector+Redis
│   └── postgres/
│       └── init.sql             # 表结构初始化
├── scripts/
│   ├── dev_bootstrap.sh         # 本地一键启动
│   ├── query.py                 # 命令行查询脚本（Week 1）
│   └── evaluate_rag.py          # 简单准确率评测
├── configs/
│   ├── app.example.env
│   └── app.env
├── .gitignore
├── Makefile
└── README.md
```

---

## 4. Week 1 实施（核心管道验证）

### Day 1-2: 环境搭建
- [ ] `infra/compose/docker-compose.dev.yaml` - PostgreSQL + pgvector + Redis
- [ ] `infra/postgres/init.sql` - 创建vector扩展和表结构
- [ ] `configs/app.example.env` - 配置示例
- [ ] `scripts/dev_bootstrap.sh` - 环境安装脚本
- [ ] 验证：Docker服务正常启动

### Day 3-4: API基础
- [ ] `backend/api/main.py` - FastAPI应用入口
- [ ] `backend/api/v1/routers/documents.py` - 文档上传/管理API
- [ ] `backend/api/v1/routers/rag.py` - RAG查询API
- [ ] 验证：curl POST文档上传接口成功

### Day 5-7: 核心管道
- [ ] `backend/services/ingestion/*` - PDF/TXT解析（无OCR）
- [ ] `backend/services/vectorstore/pgvector_client.py` - 向量存储CRUD
- [ ] `backend/services/embedding/nomic_embed.py` - 嵌入模型封装
- [ ] `backend/services/llm/ollama_client.py` - LLM调用封装
- [ ] `scripts/query.py` - 命令行查询验证脚本
- [ ] 验证：python scripts/query.py "简单问题" 返回答案

---

## 5. Week 2 实施（原型集成）

### Day 8-10: RAG功能完善
- [ ] 完善向量化流程（分块、嵌入、存储）
- [ ] RAG查询功能（检索 + LLM生成）
- [ ] 基础测试覆盖（单元测试）
- [ ] 验证：100文档问答 < 10秒响应

### Day 11-12: 原型前端
- [ ] `apps/streamlit_app/app.py` - 简单UI（上传 + 问答）
- [ ] 严格要求：必须通过HTTP调用FastAPI接口，不能直接导入服务
- [ ] 验证：Streamlit界面可上传文档并问答

### Day 13-14: 评估与决策
- [ ] `scripts/evaluate_rag.py` - 评测脚本
- [ ] 性能基准测试
- [ ] 决策评估：继续/调整/终止的明确建议

---

## 6. 关键约束

### FastAPI要求（必需）
- 所有服务必须封装在FastAPI接口中
- Streamlit严禁直接导入后端服务（必须HTTP调用）

### 测试策略
- **Week 1**: 无测试要求（手动验证为主）
- **Week 2**: 基础单元测试，覆盖率 > 40%

### 安全要求
- **Week 1**: 无安全要求（专注核心功能）
- **Week 2**: 基础输入校验（Pydantic模型）

---

## 7. 配置示例

### docker-compose.dev.yaml
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: ai_workflow_local
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev123
    ports:
      - "5432:5432"
    volumes:
      - ./pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev -d ai_workflow_local"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```

### .env.example
```bash
# 环境配置
RUN_MODE=local

# 数据库配置
PGVECTOR_HOST=localhost
PGVECTOR_PORT=5432
PGVECTOR_DB=ai_workflow_local
PGVECTOR_USER=dev
PGVECTOR_PASSWORD=dev123

# LLM配置
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# 性能参数（本地）
MAX_DOCS_PER_BATCH=50
CHUNK_SIZE=500
MAX_RETRIEVAL_RESULTS=5
MAX_FILE_SIZE_MB=10

# 文档格式
SUPPORTED_FORMATS=pdf,txt,md

# 禁用功能（Week 1-2）
ENABLE_OCR=false
```

### config.py
```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 数据库
    pgvector_host: str = os.getenv("PGVECTOR_HOST", "localhost")
    pgvector_port: int = int(os.getenv("PGVECTOR_PORT", "5432"))
    pgvector_db: str = os.getenv("PGVECTOR_DB", "ai_workflow_local")
    pgvector_user: str = os.getenv("PGVECTOR_USER", "dev")
    pgvector_password: str = os.getenv("PGVECTOR_PASSWORD", "dev123")
    
    # LLM
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    
    # 性能
    max_docs_per_batch: int = int(os.getenv("MAX_DOCS_PER_BATCH", "50"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    max_retrieval_results: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    
    # 文档处理
    supported_formats: str = os.getenv("SUPPORTED_FORMATS", "pdf,txt,md")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    enable_ocr: bool = os.getenv("ENABLE_OCR", "false").lower() == "true"

settings = Settings()
```

---

## 8. 运行命令

```bash
# 一键启动本地环境
make up-dev

# 安装模型
make install-model

# 运行命令行查询测试
python scripts/query.py "你的问题"

# 运行Streamlit
make app

# 运行测试（Week 2）
make test

# 代码格式化
make format

# 代码检查
make lint
```

---

## 9. Makefile

```makefile
.PHONY: help up-dev install-model app test test-coverage lint format

help: ## Show this help
	@echo "AI Workflow Platform Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_0-9%-]+:.*?## .*$$' $(word 1,$(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

up-dev: ## 启动本地开发环境
	docker-compose -f infra/compose/docker-compose.dev.yaml up -d
	@echo "Environment started. Waiting for services..."
	sleep 10

install-model: ## 安装Ollama模型
	ollama pull qwen2.5:7b

app: ## 运行Streamlit应用
	cd apps/streamlit_app && streamlit run app.py

test: ## 运行测试
	cd backend && python -m pytest tests/ -v

test-coverage: ## 测试覆盖率
	cd backend && python -m pytest tests/ --cov=services --cov-report=html

lint: ## 代码检查
	cd backend && flake8 . && mypy .

format: ## 代码格式化
	cd backend && black . && isort .
```

---

## 10. 禁止与约束

- 禁止在Week 1-2实现OCR功能
- 禁止Streamlit直接import backend.services（必须HTTP调用API）
- 禁止偏离此文档的技术选型
- 禁止在Week 1实现测试覆盖要求
- 禁止引入额外重型依赖

---

请严格按照本Prompt实现Week 1-2的任务，确保最终能够回答"Mac本地技术可行性验证"这一核心问题，并为后续开发提供明确决策依据。