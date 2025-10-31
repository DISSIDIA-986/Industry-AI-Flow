# 本地开发可行性方案 — 实施型高质量Prompt（用于Vibe Coding）

> 目的：用此Prompt指导智能编程助手，在本仓库逐步产出可运行的代码与配置，实现 `research/local-development-feasibility.md` 中的阶段性目标（优先完成“阶段1：Mac本地极简验证”与“阶段2：云GPU完整MVP验证”的落地代码）。

---

## 角色与总体要求

- 你的角色：一名注重工程质量的全栈工程师，负责端到端实现、文档、可运行示例与自动化脚本。
- 输出标准：
  - 代码可直接运行；提供一键命令或最少步骤运行说明。
  - 目录结构清晰、模块边界清楚、命名语义化、注释只写必要非显然信息。
  - 严格遵循本Prompt中的文件路径与接口约定，避免随意更改。
  - 优先实现“阶段1（Mac本地）”可用性；随后实现“阶段2（云GPU）”的可切换配置。
  - 默认使用中文注释和中文README（必要处可兼容英文）。

---

## 仓库上下文与技术路线

- 文档依据：
  - `research/best-ai-workflow.plan.md`（总体最佳方案基线）
  - `research/local-development-feasibility.md`（本地/云GPU分阶段实施细化）
- 阶段性技术选型（必须对齐）：
  - 阶段1（本地Mac验证，成本$0）：
    - LLM：Ollama + `qwen2.5:7b`
    - 向量库：PostgreSQL + pgvector（Docker Compose）
    - 前端：Streamlit（原型）
    - 目标：文档入库→向量化→RAG问答→基础评测
  - 阶段2（云GPU 验证）：
    - LLM：vLLM + Qwen2.5-14B（或Ollama 14B作过渡）
    - 向量库：Qdrant（Docker部署或Compose独立服务）
    - 前端：React + TypeScript（可先保留Streamlit Demo）
    - 目标：10万文档、性能基准、并发验证与切换配置

---

## 目标功能与验收（对齐 feasibility 文档）

1) 阶段1（Week 1-2）验收：
   - [ ] 文档上传/导入1000份以内测试文档
   - [ ] 向量化流程<10分钟（1000份）
   - [ ] RAG问答响应<10秒
   - [ ] 准确率>70%（提供简单评测脚本与样例集）

2) 阶段2（Week 3-4）验收：
   - [ ] 10万文档向量化<4小时（批处理脚本与监控日志）
   - [ ] 查询P95<3秒
   - [ ] 准确率>80%
   - [ ] 并发10用户稳定（基础压测脚本）

---

## 顶层目录与文件规划（必须按此生成）

```
.
├── research/
│   ├── best-ai-workflow.plan.md
│   ├── local-development-feasibility.md
│   └── local-development-feasibility.prompt.md  ← 本文件
├── apps/
│   ├── streamlit_app/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── web/  （阶段2：React + TS；阶段1可占位）
├── backend/
│   ├── api/  （阶段2可引入 FastAPI；阶段1非必需）
│   └── services/
│       ├── ingestion/            # 文档采集/解析/清洗
│       │   ├── __init__.py
│       │   ├── loaders.py        # PDF/Docx/Markdown/目录批量等
│       │   ├── cleaners.py
│       │   └── chunkers.py       # 语义+结构分块（预留策略）
│       ├── vectorstore/
│       │   ├── __init__.py
│       │   ├── pgvector_client.py # 阶段1
│       │   └── qdrant_client.py   # 阶段2
│       ├── embedding/
│       │   ├── __init__.py
│       │   └── nomic_embed.py    # 默认：nomic-embed-text-v1.5
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── bm25.py           # Week2: 混合检索
│       │   └── hybrid.py         # RRF融合与重排序预留
│       └── llm/
│           ├── __init__.py
│           ├── ollama_client.py  # 阶段1
│           └── vllm_client.py    # 阶段2
├── infra/
│   ├── compose/
│   │   ├── docker-compose.dev.yaml  # Postgres+pgvector、Redis、（可选）Qdrant
│   │   └── docker-compose.prod.yaml # 阶段2：vLLM、Qdrant、API、前端
│   ├── postgres/
│   │   ├── init.sql                 # CREATE EXTENSION vector; 表结构
│   │   └── README.md
│   └── qdrant/ (阶段2)
├── scripts/
│   ├── dev_bootstrap.sh       # 本地一键启动（非交互）
│   ├── import_docs.py         # 批量导入与向量化
│   ├── evaluate_rag.py        # 简单准确率评测
│   ├── benchmark_latency.py   # 延迟与并发压测
│   └── migrate_pg_to_qdrant.py# 阶段2：迁移脚本
├── configs/
│   ├── app.example.env
│   └── app.env                # 本地私有，不纳入git（.gitignore）
├── .gitignore
├── Makefile
└── README.md                  # 根README：分阶段运行指南
```

---

## 实施步骤（按批次提交，确保可运行）

批次A（阶段1最小可用路径）：
1. 基础Infra与环境
   - 新增 `infra/compose/docker-compose.dev.yaml`：PostgreSQL 15 + pgvector、Redis。默认端口映射、健康检查、持久化卷。
   - 新增 `infra/postgres/init.sql`：启用 `vector` 扩展、建库/建表（documents, embeddings, metadata）。
   - 新增 `configs/app.example.env`（变量：DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, EMBED_MODEL, OLLAMA_BASE_URL 等）。
   - 新增 `scripts/dev_bootstrap.sh`：
     - 校验 Docker Desktop/Compose 存在
     - 启动 compose.dev
     - 初始化 pgvector（执行 init.sql）
     - 以“非交互”方式打印后续步骤命令

2. 向量化与检索后端服务（轻量库）
   - `backend/services/vectorstore/pgvector_client.py`：提供建表、插入、相似度查询API。
   - `backend/services/embedding/nomic_embed.py`：封装开源嵌入（若需HTTP/本地模型，预留切换）。
   - `backend/services/ingestion/*`：实现PDF/Docx/Markdown加载、清洗、分块（简单规则先行）。

3. 批处理脚本
   - `scripts/import_docs.py`：从指定目录批量导入→嵌入→存储pgvector，带进度日志与失败重试。
   - `scripts/evaluate_rag.py`：加载样例Q-A对，比对Top-k召回/答案包含度，输出准确率（>70%基线）。

4. 原型前端（Streamlit）
   - `apps/streamlit_app/app.py`：
     - 上传或选择已导入文档
     - 查询输入框
     - 后端：先直连pgvector检索 + 调用Ollama 7B 生成
     - 展示引用片段与分数
   - `apps/streamlit_app/requirements.txt`：最小依赖列表
   - `apps/streamlit_app/README.md`：本地运行说明

5. 顶层文档与自动化
   - 根 `README.md`：提供阶段1一键运行步骤与常见问题（含 Mac 环境说明）。
   - `Makefile`：
     - `make up-dev`（启动本地依赖）
     - `make import DOCS=./samples`（批量导入）
     - `make app`（运行Streamlit）
     - `make eval`（评测）

批次B（阶段1 Week2：混合检索与重排序占位）：
6. 检索优化
   - `backend/services/retrieval/bm25.py`：简版BM25（如rank-bm25）
   - `backend/services/retrieval/hybrid.py`：RRF融合（向量70% + BM25 30% 可配置）
   - 更新 Streamlit：增加“检索模式”切换与参数面板

批次C（阶段2：云GPU与Qdrant切换）：
7. 云侧LLM与向量库
   - `backend/services/llm/vllm_client.py`：vLLM推理接口（URL/模型名可配）
   - `backend/services/vectorstore/qdrant_client.py`：Qdrant CRUD、相似度检索
   - `scripts/migrate_pg_to_qdrant.py`：数据迁移工具
   - `infra/compose/docker-compose.prod.yaml`：vLLM、Qdrant、（可选）FastAPI与前端容器

8. 基准与并发
   - `scripts/benchmark_latency.py`：批量查询、统计P50/P95
   - 在根 README 中新增“阶段2部署到云GPU”的操作步骤与成本提示

---

## 关键接口与约定（摘要）

- 向量表结构：
  - `documents(id UUID, path TEXT, checksum TEXT, created_at TIMESTAMP, metadata JSONB)`
  - `embeddings(doc_id UUID, chunk_id INT, text TEXT, embedding VECTOR(1536), meta JSONB)`
- 检索API（示意）：
  - `pgvector_client.similarity_search(query_text: str, top_k: int) -> List[Chunk]`
  - `hybrid.search(query_text: str, top_k: int, weights: Tuple[float,float]) -> List[Chunk]`
- LLM生成：
  - `ollama_client.generate(prompt: str, stream: bool=False) -> str`

---

## 非功能性要求

- 可配置：所有服务地址与模型名来源于 `configs/app.env`（使用 `.env` 加载）。
- 日志：使用标准输出，包含时戳与模块名；长任务显示进度条。
- 健壮性：批处理支持断点续跑；失败重试与跳过无效文件。
- 安全：对外部命令与文件路径做校验；避免任意代码执行。

---

## 运行与验证（命令示例，需在 README/脚本中实现）

```bash
# 一键启动本地依赖（Postgres+pgvector、Redis）
make up-dev

# 导入示例文档（自带 samples/ 目录或用户指定）
make import DOCS=./samples

# 运行Streamlit原型
make app

# 评测（准确率、Top-k召回）
make eval

#（阶段2）迁移到Qdrant
python scripts/migrate_pg_to_qdrant.py --from pg --to qdrant

#（阶段2）基准测试
python scripts/benchmark_latency.py --queries ./samples/queries.jsonl
```

---

## 交付要求（每批次提交需满足）

- 代码：按本Prompt路径落地，确保可运行。
- 文档：在对应目录下补充 README，包含用途说明、环境变量清单、运行步骤、常见问题。
- 质量门槛：跑通到“阶段1验收”四项勾选；随后提交“阶段2”能力与指标报告。

---

## 禁止与约束

- 禁止引入与方案不符的重型依赖（除非必要并说明理由）。
- 禁止将 `.env` 明文机密写入版本库；用 `app.example.env` 提供模板。
- 优先遵循现有文档结论与技术路线；若需偏离，先在 README 给出对比与理由。

---

## 完成定义（Definition of Done）

- 阶段1：
  - `docker-compose.dev.yaml` 可启动并初始化 pgvector
  - `import_docs.py` 可将本地样例批量入库并完成嵌入
  - `app.py` 可检索并调用 Ollama 7B 进行回答，展示引用
  - `evaluate_rag.py` 输出准确率≥70%
  - 根 `README.md` 指南完整、按步骤可复现
- 阶段2：
  - 可切换到 vLLM + Qdrant，完成10万文档验证
  - `benchmark_latency.py` 显示 P95 < 3s（样例规模下）
  - 提交成本与效果简报（README附录）

---

请严格按照本Prompt逐批实现、提交，并在每批结束后更新相关 README 与脚本的使用说明，确保任何具备基础环境的开发者均可复现运行。

# 本地开发可行性方案 — 实施型高质量Prompt（用于Vibe Coding）

> 目的：用此Prompt指导智能编程助手，在本仓库逐步产出可运行的代码与配置，实现 `research/local-development-feasibility.md` 中的阶段性目标（优先完成“阶段1：Mac本地极简验证”与“阶段2：云GPU完整MVP验证”的落地代码）。

---

## 角色与总体要求

- 你的角色：一名注重工程质量的全栈工程师，负责端到端实现、文档、可运行示例与自动化脚本。
- 输出标准：
  - 代码可直接运行；提供一键命令或最少步骤运行说明。
  - 目录结构清晰、模块边界清楚、命名语义化、注释只写必要非显然信息。
  - 严格遵循本Prompt中的文件路径与接口约定，避免随意更改。
  - 优先实现“阶段1（Mac本地）”可用性；随后实现“阶段2（云GPU）”的可切换配置。
  - 默认使用中文注释和中文README（必要处可兼容英文）。

---

## 仓库上下文与技术路线

- 文档依据：
  - `research/best-ai-workflow.plan.md`（总体最佳方案基线）
  - `research/local-development-feasibility.md`（本地/云GPU分阶段实施细化）
- 阶段性技术选型（必须对齐）：
  - 阶段1（本地Mac验证，成本$0）：
    - LLM：Ollama + `qwen2.5:7b`
    - 向量库：PostgreSQL + pgvector（Docker Compose）
    - 前端：Streamlit（原型）
    - 目标：文档入库→向量化→RAG问答→基础评测
  - 阶段2（云GPU 验证）：
    - LLM：vLLM + Qwen2.5-14B（或Ollama 14B作过渡）
    - 向量库：Qdrant（Docker部署或Compose独立服务）
    - 前端：React + TypeScript（可先保留Streamlit Demo）
    - 目标：10万文档、性能基准、并发验证与切换配置

---

## 目标功能与验收（对齐 feasibility 文档）

1) 阶段1（Week 1-2）验收：
   - [ ] 文档上传/导入1000份以内测试文档
   - [ ] 向量化流程<10分钟（1000份）
   - [ ] RAG问答响应<10秒
   - [ ] 准确率>70%（提供简单评测脚本与样例集）

2) 阶段2（Week 3-4）验收：
   - [ ] 10万文档向量化<4小时（批处理脚本与监控日志）
   - [ ] 查询P95<3秒
   - [ ] 准确率>80%
   - [ ] 并发10用户稳定（基础压测脚本）

---

## 顶层目录与文件规划（必须按此生成）

```
.
├── research/
│   ├── best-ai-workflow.plan.md
│   ├── local-development-feasibility.md
│   └── local-development-feasibility.prompt.md  ← 本文件
├── apps/
│   ├── streamlit_app/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── web/  （阶段2：React + TS；阶段1可占位）
├── backend/
│   ├── api/
│   │   └── main.py              # FastAPI应用入口（阶段1必需）
│   │   └── v1/
│   │       └── routers/
│   │           ├── rag.py       # RAG查询路由
│   │           └── documents.py # 文档管理路由
│   ├── services/
│   │   ├── ingestion/            # 文档采集/解析/清洗
│   │   │   ├── __init__.py
│   │   │   ├── loaders.py        # PDF/Docx/Markdown/目录批量等
│   │   │   ├── cleaners.py
│   │   │   └── chunkers.py       # 语义+结构分块（预留策略）
│   │   ├── vectorstore/
│   │   │   ├── __init__.py
│   │   │   ├── pgvector_client.py # 阶段1
│   │   │   └── qdrant_client.py   # 阶段2
│   │   ├── embedding/
│   │   │   ├── __init__.py
│   │   │   └── nomic_embed.py    # 默认：nomic-embed-text-v1.5
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── bm25.py           # Week2: 混合检索
│   │   │   └── hybrid.py         # RRF融合与重排序预留
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── ollama_client.py  # 阶段1
│   │       └── vllm_client.py    # 阶段2
│   └── tests/
│       ├── unit/
│       │   ├── test_ingestion.py
│       │   └── test_vectorstore.py
│       ├── integration/
│       │   └── test_api.py
│       └── conftest.py
├── infra/
│   ├── compose/
│   │   ├── docker-compose.dev.yaml  # Postgres+pgvector、Redis、（可选）Qdrant
│   │   └── docker-compose.prod.yaml # 阶段2：vLLM、Qdrant、API、前端
│   ├── postgres/
│   │   ├── init.sql                 # CREATE EXTENSION vector; 表结构
│   │   └── README.md
│   └── qdrant/ (阶段2)
├── scripts/
│   ├── dev_bootstrap.sh       # 本地一键启动（非交互）
│   ├── import_docs.py         # 批量导入与向量化
│   ├── evaluate_rag.py        # 简单准确率评测
│   ├── benchmark_latency.py   # 延迟与并发压测
│   └── migrate_pg_to_qdrant.py# 阶段2：迁移脚本
├── configs/
│   ├── app.example.env
│   └── app.env                # 本地私有，不纳入git（.gitignore）
├── .gitignore
├── Makefile
└── README.md                  # 根README：分阶段运行指南
```

---

## 实施步骤（按批次提交，确保可运行）

### 批次A: 核心管道验证 (Week 1) - 极简MVP
- **目标**: 证明"文档 -> 向量化 -> 存储 -> 检索 -> LLM生成"这个核心管道在 Mac 上能跑通。
- **产出**:
  - 后端服务（pgvector_client, nomic_embed, ollama_client）。
  - 一个命令行脚本 `scripts/query.py`，接收一个问题，直接调用服务，打印出答案和引用。
  - FastAPI 应用，封装核心服务。
  - 无需 Streamlit 或完整前端。
- **验收**: python scripts/query.py "我的问题" 能在15秒内返回结果。

1. 基础Infra与环境
   - 新增 `infra/compose/docker-compose.dev.yaml`：PostgreSQL 15 + pgvector、Redis。默认端口映射、健康检查、持久化卷。
   - 新增 `infra/postgres/init.sql`：启用 `vector` 扩展、建库/建表（documents, embeddings, metadata）。
   - 新增 `configs/app.example.env`（变量：DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, EMBED_MODEL, OLLAMA_BASE_URL 等）。
   - 新增 `scripts/dev_bootstrap.sh`：
     - 校验 Docker Desktop/Compose 存在
     - 启动 compose.dev
     - 初始化 pgvector（执行 init.sql）
     - 以"非交互"方式打印后续步骤命令

2. 后端服务与API (API-First)
   - `backend/api/main.py`：创建 FastAPI 入口
   - `backend/api/v1/routers/rag.py`：创建 /api/v1/rag 路由，用于接收查询请求
   - `backend/api/v1/routers/documents.py`：创建 /api/v1/documents 路由，用于文档上传
   - backend/services/* 中的所有逻辑，都通过这个 API 暴露，而不是被前端直接调用

3. 核心服务层
   - `backend/services/vectorstore/pgvector_client.py`：提供建表、插入、相似度查询API。
   - `backend/services/embedding/nomic_embed.py`：封装开源嵌入（若需HTTP/本地模型，预留切换）。
   - `backend/services/ingestion/*`：实现PDF/Docx/Markdown加载、清洗、分块（简单规则先行）。
   - `backend/services/llm/ollama_client.py`：Ollama API封装

4. 测试与质量保障
   - 创建 `backend/tests/` 目录结构
   - `backend/tests/unit/test_ingestion.py`：测试文档解析功能
   - `backend/tests/unit/test_vectorstore.py`：测试向量存储功能
   - `backend/tests/integration/test_api.py`：测试API端到端功能
   - 在 Makefile 中加入测试命令

### 批次B: API 与前端集成 (Week 2) - 原型可用
- **目标**: 在已验证的核心管道之上，封装 API 并提供一个简单的 UI。
- **产出**:
  - 完善的 FastAPI 应用，封装批次A中的服务。
  - Streamlit 应用，调用 FastAPI 接口。
- **验收**: Streamlit 界面功能可用，RAG 问答响应 < 10秒。

5. 原型前端（Streamlit）
   - `apps/streamlit_app/app.py`：
     - 上传或选择已导入文档
     - 查询输入框
     - 后端：必须通过 requests 或 httpx 调用本地的 FastAPI 接口，严禁直接 import backend.services
     - 展示引用片段与分数
   - `apps/streamlit_app/requirements.txt`：最小依赖列表
   - `apps/streamlit_app/README.md`：本地运行说明

6. 顶层文档与自动化
   - 根 `README.md`：提供阶段1一键运行步骤与常见问题（含 Mac 环境说明）。
   - `Makefile`：
     - `make up-dev`（启动本地依赖）
     - `make import DOCS=./samples`（批量导入）
     - `make app`（运行Streamlit）
     - `make eval`（评测）
     - `make test`（运行测试）
     - `make test-coverage`（测试覆盖率）
     - `make lint`（代码检查）
     - `make format`（代码格式化）

### 批次C（阶段2：云GPU与Qdrant切换）：
7. 云侧LLM与向量库
   - `backend/services/llm/vllm_client.py`：vLLM推理接口（URL/模型名可配）
   - `backend/services/vectorstore/qdrant_client.py`：Qdrant CRUD、相似度检索
   - `scripts/migrate_pg_to_qdrant.py`：数据迁移工具
   - `infra/compose/docker-compose.prod.yaml`：vLLM、Qdrant、（可选）FastAPI与前端容器

8. 基准与并发
   - `scripts/benchmark_latency.py`：批量查询、统计P50/P95
   - 在根 README 中新增"阶段2部署到云GPU"的操作步骤与成本提示

---

## 关键接口与约定（摘要）

- 向量表结构：
  - `documents(id UUID, path TEXT, checksum TEXT, created_at TIMESTAMP, metadata JSONB)`
  - `embeddings(doc_id UUID, chunk_id INT, text TEXT, embedding VECTOR(1536), meta JSONB)`
- 检索API（示意）：
  - `pgvector_client.similarity_search(query_text: str, top_k: int) -> List[Chunk]`
  - `hybrid.search(query_text: str, top_k: int, weights: Tuple[float,float]) -> List[Chunk]`
- LLM生成：
  - `ollama_client.generate(prompt: str, stream: bool=False) -> str`

---

## 非功能性要求

- 可配置：所有服务地址与模型名来源于 `configs/app.env`（使用 `.env` 加载）。
- 日志：使用标准输出，包含时戳与模块名；长任务显示进度条。
- 健壮性：批处理支持断点续跑；失败重试与跳过无效文件。
- 安全：对外部命令与文件路径做校验；避免任意代码执行。
- **错误处理**: 所有对外服务（API路由）和与外部系统（数据库、Ollama）的交互点，都必须有明确的 try...except 块，并记录有意义的错误日志。
- **优雅降级**: 在外部服务（如Ollama）不可用时，API应返回一个明确的错误信息（如 HTTP 503），而不是直接崩溃。
- **输入校验**: 所有 API 的输入都必须使用 Pydantic 模型进行严格的类型和格式校验。

---

## 运行与验证（命令示例，需在 README/脚本中实现）

```bash
# 一键启动本地依赖（Postgres+pgvector、Redis）
make up-dev

# 导入示例文档（自带 samples/ 目录或用户指定）
make import DOCS=./samples

# 运行Streamlit原型
make app

# 运行测试
make test

# 运行测试并查看覆盖率
make test-coverage

# 代码格式化
make format

# 代码检查
make lint

# 评测（准确率、Top-k召回）
make eval

#（阶段2）迁移到Qdrant
python scripts/migrate_pg_to_qdrant.py --from pg --to qdrant

#（阶段2）基准测试
python scripts/benchmark_latency.py --queries ./samples/queries.jsonl
```

---

## 交付要求（每批次提交需满足）

- 代码：按本Prompt路径落地，确保可运行。
- 文档：在对应目录下补充 README，包含用途说明、环境变量清单、运行步骤、常见问题。
- 质量门槛：跑通到"阶段1验收"四项勾选；随后提交"阶段2"能力与指标报告。

---

## 禁止与约束

- 禁止引入与方案不符的重型依赖（除非必要并说明理由）。
- 禁止将 `.env` 明文机密写入版本库；用 `app.example.env` 提供模板。
- 优先遵循现有文档结论与技术路线；若需偏离，先在 README 给出对比与理由。
- 严禁 Streamlit 直接调用 backend.services - 必须通过 FastAPI 接口调用

## 完成定义（Definition of Done）

- 阶段1：
  - `docker-compose.dev.yaml` 可启动并初始化 pgvector
  - `import_docs.py` 可将本地样例批量入库并完成嵌入
  - API 可检索并调用 Ollama 7B 进行回答，展示引用
  - `evaluate_rag.py` 输出准确率≥70%
  - 根 `README.md` 指南完整、按步骤可复现
  - 所有核心模块有单元测试，测试覆盖率 > 60%
  - 代码通过 flake8、mypy、black 检查
- 阶段2：
  - 可切换到 vLLM + Qdrant，完成10万文档验证
  - `benchmark_latency.py` 显示 P95 < 3s（样例规模下）
  - 提交成本与效果简报（README附录）

---

## 软件工程质量标准与测试要求

### 测试驱动开发 (Test-Driven Development)
- **测试优先**: 核心业务逻辑（如文档解析、混合检索）的开发应遵循测试优先的原则。
- **单元测试**: backend/services/下的所有模块都必须有对应的单元测试。使用 pytest 作为测试框架，并利用 pytest-mock 模拟外部依赖（如数据库和Ollama API）。
- **测试覆盖率**:
  - 阶段1完成时: 核心逻辑覆盖率 > 60%
  - 阶段2完成时: 整体覆盖率 > 80%
- **自动化测试**: Makefile 中必须包含 make test 和 make test-coverage 命令。

### 代码规范与静态检查
- **代码风格**: 所有 Python 代码必须使用 black 进行格式化，使用 isort 进行 import 排序。
- **静态检查**: 提交前必须通过 flake8 和 mypy 的检查，确保代码风格统一且类型安全。
- **自动化检查**: Makefile 中应包含 make lint 和 make format 命令。

### API-First 与模块化设计
- **API优先**: 所有服务必须封装在 FastAPI 接口中，不允许前端直接调用服务层代码。
- **模块化边界**: 每个服务模块（ingestion, vectorstore, embedding, retrieval, llm）都应有清晰的接口定义和实现分离。
- **依赖注入**: 使用 FastAPI 的依赖注入机制来管理服务之间的依赖关系。

---

请严格按照本Prompt逐批实现、提交，并在每批结束后更新相关 README 与脚本的使用说明，确保任何具备基础环境的开发者均可复现运行。

## 附：配置与脚本示例（整合自英文部分，已中文化并归档到对应章节）

### docker-compose.local.yml（本地环境）

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

### .env.example（本地/云通用）

```bash
RUN_MODE=local
MAX_MEMORY_MB=8192
USE_GPU=false
VECTOR_STORE=pgvector
PGVECTOR_HOST=localhost
PGVECTOR_PORT=5432
PGVECTOR_DB=ai_workflow_local
PGVECTOR_USER=dev
PGVECTOR_PASSWORD=dev123
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
MAX_DOCS_PER_BATCH=50
CHUNK_SIZE=500
MAX_RETRIEVAL_RESULTS=5
MEMORY_WARNING_THRESHOLD=80
SUPPORTED_FORMATS=pdf,txt,md
MAX_FILE_SIZE_MB=10
ENABLE_OCR=false
```

### 配置类示例（backend/app/core/config.py）

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    run_mode: str = os.getenv("RUN_MODE", "local")
    vector_store: str = os.getenv("VECTOR_STORE", "pgvector")
    pgvector_host: str = os.getenv("PGVECTOR_HOST", "localhost")
    pgvector_port: int = int(os.getenv("PGVECTOR_PORT", "5432"))
    pgvector_db: str = os.getenv("PGVECTOR_DB", "ai_workflow_local")
    pgvector_user: str = os.getenv("PGVECTOR_USER", "dev")
    pgvector_password: str = os.getenv("PGVECTOR_PASSWORD", "dev123")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    max_docs_per_batch: int = int(os.getenv("MAX_DOCS_PER_BATCH", "50"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    max_retrieval_results: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    memory_warning_threshold: int = int(os.getenv("MEMORY_WARNING_THRESHOLD", "80"))

settings = Settings()
```

### 本地环境脚本（scripts/setup_local.sh）

```bash
#!/bin/bash
set -e
brew install ollama || true
docker-compose -f docker-compose.local.yml up -d
sleep 10
ollama pull qwen2.5:7b
```

### 云环境脚本（scripts/setup_cloud.sh）

```bash
#!/bin/bash
set -e
sudo apt update && sudo apt install -y docker.io docker-compose postgresql-client
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5:14b
docker-compose -f docker-compose.prod.yml up -d
```

### 迁移脚本（pgvector → Qdrant）

```python
# scripts/migration/pgvector_to_qdrant.py
import asyncio, asyncpg, json
from qdrant_client import QdrantClient
from qdrant_client.http import models

async def migrate_pgvector_to_qdrant():
    pg = await asyncpg.connect(host="localhost", port=5432, database="ai_workflow_local", user="dev", password="dev123")
    q = QdrantClient(host="localhost", port=6333)
    q.recreate_collection("documents", vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
    rows = await pg.fetch("SELECT id, content, metadata, embedding FROM document_chunks ORDER BY id LIMIT 1000")
    points = [models.PointStruct(id=r['id'], vector=r['embedding'], payload={"content": r['content'], "metadata": json.loads(r['metadata']) if r['metadata'] else {}}) for r in rows]
    q.upsert(collection_name="documents", points=points)
    await pg.close()

if __name__ == "__main__":
    asyncio.run(migrate_pgvector_to_qdrant())
```

### RAG 评测框架（scripts/evaluation/rag_evaluation.py）

```python
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    query: str
    response: str
    expected_answer: str
    faithfulness: float
    relevance: float
    answer_correctness: float
    context_precision: float
    overall_score: float
```

### 本地性能监控（backend/app/core/utils/performance_utils.py）

```python
import psutil, time
from dataclasses import dataclass

@dataclass
class LocalPerformanceMetrics:
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    disk_usage_gb: float
    timestamp: float
```

### Makefile（常用命令）

```makefile
.PHONY: env-up env-down setup backend-up frontend-up test
env-up:
	docker-compose -f docker-compose.local.yml up -d
install-model:
	ollama pull qwen2.5:7b
setup: env-up install-model
```

### Phase 1: Local Mac Development (Perplexity-style minimal implementation)
You will implement a 3-layer architecture first, suitable for local development:

#### Layer 1: Frontend Layer
- **Development**: Streamlit (for rapid prototyping, per Perplexity plan)
- **Production**: React 18 with TypeScript
- Real-time streaming responses
- File upload and management interface
- Data visualization with Plotly

#### Layer 2: API Gateway & Core Services Layer
- FastAPI backend (unified in Phase 1 for simplicity)
- JWT-based authentication
- Request/response validation
- Rate limiting and monitoring endpoints
- Document ingestion service
- RAG engine service
- Configuration to switch between pgvector and Qdrant

#### Layer 3: Model Inference & Data Storage Layer
- PostgreSQL with pgvector (local development - suitable for <10k docs on Mac)
- Redis for session management
- Ollama for model serving (Qwen2.5-7B for local development)
- Embedding models (nomic-embed-text-v1.5)
- Re-ranking models (bge-reranker-base-v2)

### Phase 2: Cloud GPU Testing (When needed)
- Migrate to Qdrant vector store
- Upgrade to Qwen2.5-14B model
- Full 6-layer architecture from the main plan

## Implementation Requirements

### Phase 1A Core Requirements (Week 1-2)
Implement only ESSENTIAL functionality for feasibility validation:

### 1. Minimal Security Implementation (Phase 1B+)
- Basic authentication (username/password, no RBAC initially)
- Skip PII detection and comprehensive audit logs for now
- Basic input validation
- **Phase 1A: No security - focus on core functionality**

### 2. Document Ingestion System (Phase 1A: Minimal + Phase 1B: Extended)
Phase 1A: Core document handling
- Support PDF and TXT formats only (no DOCX, XLS, PPT, URLs initially)
- NO OCR support (skip DeepSeek + PaddleOCR for now)
- Simple chunking (by character/word count, not semantic)
- Basic metadata extraction (filename, upload date)
- Optimize for local Mac performance (batch processing, memory limits)

Phase 1B: Enhanced ingestion
- Add document parsing quality checks
- Basic metadata tagging
- Performance monitoring for parsing

### 3. RAG Engine (Phase 1A: Simple + Phase 1B: Basic Enhancement)
Phase 1A: Core RAG functionality
- Simple vector retrieval (no hybrid search initially)
- Basic LLM integration with Ollama
- No re-ranking (bge-reranker-base-v2 for Phase 2+)
- No query optimization (query rewriting/expansion/HyDE for Phase 2+)
- Simple concatenation of context to LLM

Phase 1B: Enhanced RAG
- Basic hybrid search (vector + keyword via pgvector)
- Response streaming (optional for performance)
- Reference/citation tracking
- Basic performance metrics

### 4. AI Agent Framework (Phase 2+)
- DO NOT implement in Phase 1 - this is advanced functionality
- Focus on core RAG first

### 5. Code Execution Environment (Phase 2+)
- DO NOT implement in Phase 1 - this is advanced functionality
- Focus on core RAG first

## Implementation Phases (Following Local Feasibility Assessment - 2-Week Validation Approach)

### Phase 1A: Core Validation (Week 1-2) - FOCUS ON FEASIBILITY
Implement only the ESSENTIAL functionality for technical feasibility validation:
- Basic FastAPI backend (minimal endpoints only)
- Document upload for PDF and TXT formats (no OCR initially)
- Document parsing and basic chunking
- Simple vectorization with PostgreSQL + pgvector
- Basic RAG query functionality (simple vector search + LLM response)
- Command-line testing capability (no UI initially)
- Environment setup and configuration
- **GOAL**: Answer the question "Can this work on Mac with reasonable performance?"

### Phase 1B: Quick Integration (Week 3-4) - IF Phase 1A SUCCEEDS
Only if Phase 1A proves technical feasibility, expand with:
- Streamlit frontend for simple UI
- Basic hybrid search (vector + keyword)
- Reference/citation tracking
- Performance monitoring
- Initial security (basic auth only)
- **GOAL**: Create a minimal working demo for evaluation

### Phase 2: Feature Expansion (Weeks 5-8) - IF EVALUATION IS POSITIVE
- Upgrade architecture to full 6-layer when cloud GPU is used
- Implement OCR with dual-engine fallback
- Implement hybrid search with Qdrant option
- Add AI agent capabilities
- Implement full code execution sandbox
- Enhance with React interface

### Phase 3: Production Readiness (Weeks 9-12) - FOR FULL DEVELOPMENT
- Implement complete security features (RBAC, encryption, audit logs)
- Add monitoring and observability
- Performance optimization
- Comprehensive testing
- Production deployment configuration

## Code Organization (Local-First Structure)

Create the following directory structure that supports local development with clear phase separation:

```
ai-workflow-platform/
├── backend/
│   ├── app/
│   │   ├── main.py (FastAPI app)
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── routers/
│   │   │   │   │   ├── auth.py (Phase 1+)
│   │   │   │   │   ├── documents.py (Phase 1+)
│   │   │   │   │   ├── rag.py (Phase 1+)
│   │   │   │   │   ├── agents.py (Phase 2+) - Implement minimal stub in Phase 1
│   │   │   │   │   └── code_execution.py (Phase 2+) - Implement minimal stub in Phase 1
│   │   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py (local vs cloud configuration)
│   │   │   ├── security.py
│   │   │   ├── database.py (pgvector vs Qdrant abstraction)
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   │   ├── document_service.py (local-optimized, Phase 1+)
│   │   │   │   ├── rag_service.py (configurable backends, Phase 1+)
│   │   │   │   ├── agent_service.py (Phase 2+)
│   │   │   │   └── code_execution_service.py (Phase 2+)
│   │   │   └── utils/
│   │   │       ├── ocr_utils.py (DeepSeek + PaddleOCR)
│   │   │       ├── embedding_utils.py
│   │   │       └── performance_utils.py (for local optimization)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── streamlit_app.py (Phase 1 - local development)
│   └── react/ (Phase 2+)
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   ├── services/
│       │   ├── hooks/
│       │   ├── types/
│       │   └── utils/
│       ├── package.json
│       └── Dockerfile
├── docker-compose.local.yml (PostgreSQL + Redis for local dev)
├── docker-compose.prod.yml (Full production stack)
├── docs/
└── scripts/
    ├── setup_local.sh (Phase 1: Complete local environment setup)
    ├── setup_cloud.sh (Phase 2+: Cloud GPU environment setup)
    └── performance_test.py (Phase 1+: Performance testing script)
```

## Configuration Examples

### docker-compose.local.yml
Purpose: Local development environment with PostgreSQL (pgvector) and Redis.

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
Purpose: Configuration values for local vs cloud environments.

```bash
# Hardware Configuration
RUN_MODE=local  # local | cloud_gpu
MAX_MEMORY_MB=8192  # Mac local limit
USE_GPU=false

# Vector Store
VECTOR_STORE=pgvector  # pgvector | qdrant
PGVECTOR_HOST=localhost
PGVECTOR_PORT=5432
PGVECTOR_DB=ai_workflow_local
PGVECTOR_USER=dev
PGVECTOR_PASSWORD=dev123

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Performance Limits (local)
MAX_DOCS_PER_BATCH=50
CHUNK_SIZE=500
MAX_RETRIEVAL_RESULTS=5  # Reduce for local performance
MEMORY_WARNING_THRESHOLD=80  # Percentage

# Document Processing
SUPPORTED_FORMATS=pdf,txt,md
MAX_FILE_SIZE_MB=10
ENABLE_OCR=false  # Phase 2+ feature
```

### Sample Config Implementation
Purpose: Configuration abstraction layer for local vs cloud environments.

```python
# backend/app/core/config.py
import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Environment
    run_mode: str = os.getenv("RUN_MODE", "local")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Vector Store Configuration
    vector_store: str = os.getenv("VECTOR_STORE", "pgvector")
    pgvector_host: str = os.getenv("PGVECTOR_HOST", "localhost")
    pgvector_port: int = int(os.getenv("PGVECTOR_PORT", "5432"))
    pgvector_db: str = os.getenv("PGVECTOR_DB", "ai_workflow_local")
    pgvector_user: str = os.getenv("PGVECTOR_USER", "dev")
    pgvector_password: str = os.getenv("PGVECTOR_PASSWORD", "dev123")
    
    # LLM Configuration
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    
    # Performance Configuration
    max_docs_per_batch: int = int(os.getenv("MAX_DOCS_PER_BATCH", "50"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    max_retrieval_results: int = int(os.getenv("MAX_RETRIEVAL_RESULTS", "5"))
    memory_warning_threshold: int = int(os.getenv("MEMORY_WARNING_THRESHOLD", "80"))
    
    # Document Processing
    supported_formats: str = os.getenv("SUPPORTED_FORMATS", "pdf,txt,md")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    enable_ocr: bool = os.getenv("ENABLE_OCR", "false").lower() == "true"
    
    class Config:
        case_sensitive = True

settings = Settings()
```

## Sample Script Content

### scripts/setup_local.sh
Purpose: To set up the complete local development environment for Phase 1.

```bash
#!/bin/bash
# scripts/setup_local.sh

set -e  # Exit immediately if a command exits with a non-zero status

echo "🚀 Setting up local development environment..."

# Check system requirements first
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  Warning: Not on macOS. Performance may vary."
fi

# Check if M-series chip
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "⚠️  Warning: Not M1/M2/M3 Mac. Performance may vary."
fi

# Check memory (at least 16GB recommended)
TOTAL_MEM=$(sysctl -n hw.memsize)
TOTAL_MEM_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
if [[ $TOTAL_MEM_GB -lt 16 ]]; then
    echo "⚠️  Warning: Minimum 16GB RAM recommended. You have ${TOTAL_MEM_GB}GB"
fi

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install from https://brew.sh"
    exit 1
fi

# Install Ollama using Homebrew (for local LLM serving)
echo "📦 Installing Ollama..."
brew install ollama || {
    echo "❌ Failed to install Ollama"
    exit 1
}

# All other services (PostgreSQL, Redis) will be managed by Docker Compose
echo "🔧 Starting services via Docker Compose..."
docker-compose -f docker-compose.local.yml up -d || {
    echo "❌ Failed to start Docker services"
    exit 1
}

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Verify PostgreSQL is running via Docker
if ! docker exec $(docker ps -q -f name=postgres) pg_isready > /dev/null 2>&1; then
    echo "❌ PostgreSQL in Docker failed to start"
    exit 1
fi

# Verify Redis is running via Docker
if ! docker exec $(docker ps -q -f name=redis) redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis in Docker failed to start"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt || {
    echo "❌ Failed to install Python dependencies"
    exit 1
}

# Pull the required LLM model
echo "📥 Pulling Qwen2.5-7B model (this may take 5-10 minutes)..."
ollama pull qwen2.5:7b || {
    echo "❌ Failed to pull model"
    exit 1
}

# Verify model was pulled
if ! ollama list | grep -q "qwen2.5"; then
    echo "❌ Model download verification failed"
    exit 1
fi

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
fi

echo "✅ Local environment is ready!"
echo ""
echo "Next steps:"
echo "  1. Verify services: docker-compose -f docker-compose.local.yml ps"
echo "  2. Run the app: cd backend && python -m uvicorn app.main:app --reload"
echo "  3. Or run Streamlit UI: cd frontend && streamlit run streamlit_app.py"
```

### scripts/setup_cloud.sh
Purpose: To set up the cloud GPU environment for Phase 2+.

```bash
#!/bin/bash
# scripts/setup_cloud.sh

echo "Setting up cloud GPU environment..."

# Install system dependencies on cloud instance
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y docker.io docker-compose postgresql-client

# Start Docker service
sudo systemctl start docker
sudo usermod -aG docker $USER

# Install Ollama for cloud GPU
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
systemctl start ollama

# Install Python dependencies
pip install -r requirements.txt

# Pull the required LLM model (larger model for cloud)
echo "Pulling Qwen2.5-14B model for cloud..."
ollama pull qwen2.5:14b

# Start services using production Docker Compose
docker-compose -f docker-compose.prod.yml up -d

echo "Cloud environment is ready."
```

## Specific Implementation Guidelines for Local Feasibility

### 1. Backend Implementation (Local-First)
- Use FastAPI with automatic API documentation
- Implement configuration abstraction (local vs cloud)
- Use SQLAlchemy with async support for PostgreSQL
- Implement custom exception handlers with graceful degradation
- Use Pydantic for request/response validation
- Add performance monitoring with configurable limits for local resources
- **CRITICAL**: All services must have CPU fallbacks when GPU unavailable

### 2. Database Models (Configurable Backend)
- Abstract database operations to support both pgvector and Qdrant
- Document model with metadata, content chunks, embedding status
- User model with role-based permissions
- Session/Conversation model for memory management
- Audit log model for compliance tracking
- Task model for async operations

### 3. API Endpoints (Local-Optimized)
- `/auth/` - Authentication (login, register, token refresh)
- `/documents/` - Document management (upload, list, delete, metadata)
  - Include local performance indicators
  - Progress tracking for long operations
- `/rag/` - RAG operations (query, chat, feedback)
  - Configurable timeout for local performance
  - Fallback responses when models are slow
- `/agents/` - Agent orchestration (create, run, status)
- `/execute/` - Code execution (submit, run, results)
- `/admin/` - Administrative functions (users, settings, monitoring)
- `/health/` - Health checks with resource utilization

### 4. Configuration Management (Local vs Cloud)
- Use environment variables for configuration
- Support different environments (local dev, cloud GPU, production)
- Configuration validation at startup
- Hardware capability detection and optimization
- Easy switching between local (pgvector) and cloud (Qdrant) vector stores

### 5. Local Performance Optimization
- Implement configurable batch sizes for vectorization
- Add memory usage monitoring and limits
- Implement caching strategies for local performance
- Add progress tracking for long-running operations
- Include performance indicators in the UI

## Testing Requirements (Progressive Coverage Based on Phase)

Phase 1A (Week 1-2): Manual + Basic Testing
- No test coverage requirements yet (focus on functionality)
- Manual testing for core flows
- Basic integration tests for key paths only
- Mock external services minimally (LLMs, vector stores)
- **GOAL: Functionality over test coverage**

Phase 1B (Week 3-4): Initial Test Coverage
- Target 40-50% test coverage for core functionality
- Unit tests for critical business logic
- API integration tests for key endpoints

Phase 2+ (Week 5+): Comprehensive Testing
- Target 80%+ coverage overall, 90%+ for core logic
- Mock external services (LLMs, vector stores)
- Test security controls and RBAC
- Performance tests adapted for local hardware constraints
- Compatibility tests between local and cloud configurations

## Quality Standards (Progressive Quality Based on Phase)

### Phase 1A-B Quality Requirements:
- Type hints for public APIs (not 100% strict in Phase 1A)
- **NO** test coverage requirements (40-50% by Phase 1B, 80%+ by Phase 2+)
- All code must pass basic linting (flake8, mypy, black)
- Document core functions with examples
- Add proper error handling with meaningful messages
- Include performance monitoring points
- **CRITICAL**: All code must run on local Mac hardware (M1/M2/M3 with 16GB+ RAM)

### Phase 2+ Quality Requirements:
- 100% type hint coverage for public APIs
- 80%+ test coverage overall, 90%+ for core logic
- All code must pass linting (flake8, mypy, black)
- Document all public functions with examples
- Add proper error handling with meaningful messages
- Include performance monitoring points
- **CRITICAL**: All code must run on local Mac hardware (M1/M2/M3 with 16GB+ RAM)

## Deliverables for Phase 1A (Core Validation - Weeks 1-2)
1. Working FastAPI application with minimal essential endpoints
2. Document upload functionality (PDF, TXT only)
3. Basic document parsing and chunking (no OCR)
4. Simple RAG implementation with PostgreSQL + pgvector
5. Local Docker Compose setup (PostgreSQL, Redis)
6. Ollama integration with Qwen2.5-7B
7. Command-line testing capability (no UI initially)
8. API documentation via Swagger UI/ReDoc
9. Environment verification: Confirm system can process documents and answer basic questions
10. Performance baseline: Document processing and query response times

## Deliverables for Phase 1B (Quick Integration - Weeks 3-4) - ONLY IF Phase 1A SUCCEEDS
1. Streamlit frontend for basic UI
2. Basic hybrid search (vector + keyword)
3. Reference/citation tracking
4. Performance monitoring utilities
5. Initial basic authentication
6. Working demo for evaluation
7. Test coverage: 40-50% of core functionality

## Success Criteria for Local Feasibility

### Phase 1A Success Criteria (Week 1-2)
- **Core Functionality**: System can upload, parse, chunk, and store documents to pgvector
- **RAG Response**: System can answer simple questions from documents in <10 seconds on local Mac (P95)
- **Performance**: Successfully processes 100 documents in <5 minutes on local Mac (Phase 1A)
- **Hardware**: All core functionality works on M1/M2/M3 with 16GB RAM
- **Decision Point**: Clear answer to "Is this technically feasible on local hardware?"
- **No security requirements yet** - focus on core functionality

### Phase 1B Success Criteria (Week 3-4 - ONLY IF Phase 1A SUCCEEDS)
- **UI Integration**: Streamlit frontend allows document upload and Q&A
- **Enhanced RAG**: Hybrid search provides better results
- **Reference Tracking**: System can cite document sources
- **Basic Security**: Simple authentication works
- **Evaluation Ready**: Working demo for decision-making
- **Test Coverage**: 40-50% coverage of core functionality

### General Success Criteria
- Proper error handling without exposing internal details
- All core components pass basic functionality tests on local Mac
- Clear performance metrics available for evaluation
- Easy migration path to cloud GPU when needed

## Implementation Notes for Local Development
- Start with Phase 1A functionality, ensuring core features work on local Mac before adding complexity
- Use factory patterns for creating different types of services (local vs cloud)
- Implement proper resource cleanup and memory management for local constraints
- Use connection pooling with appropriate limits for local resources
- Implement graceful degradation when local resources are constrained
- Add health check endpoints that monitor local resource utilization
- **CRITICAL**: Every GPU-accelerated feature must have a CPU fallback
- Include hardware capability detection and automatic configuration
- Add progress indicators for long-running operations on local hardware

## Weekly Checkpoints for Phase 1A (Week 1-2)

### Week 1: Environment and Basic API (Days 1-5)
Day 1-2: Environment Setup
- [ ] PostgreSQL + pgvector running locally
- [ ] Redis running locally  
- [ ] Ollama + Qwen2.5:7b downloaded and accessible
- [ ] Docker Compose services up (PostgreSQL, Redis)
- [ ] Verify: ollama run qwen2.5:7b "Hello" returns response

Day 3-4: Basic API
- [ ] FastAPI application starts successfully
- [ ] /health endpoint returns status and resource usage
- [ ] Document upload endpoint accepts PDF files
- [ ] Verify: curl -X POST to upload endpoint works

Day 5: Basic Storage
- [ ] PDF parsing successful (using PyMuPDF)
- [ ] Document chunks created and stored in pgvector
- [ ] Verify: Query pgvector table shows embedded chunks

### Week 2: Core RAG Functionality (Days 6-7, then Days 8-10)
Day 6-7: RAG Implementation
- [ ] Vector search returns relevant chunks
- [ ] LLM generates response from retrieved context
- [ ] Basic RAG flow: Query → Retrieve → Generate answer
- [ ] Verify: Ask simple question about uploaded document, get answer

Day 8-10: Performance Validation
- [ ] Response time <15 seconds for basic queries
- [ ] Process 100 test documents successfully
- [ ] Memory usage stays below 80% threshold
- [ ] **DECISION POINT**: Is system technically feasible? Continue to Phase 1B or adjust approach

## Weekly Checkpoints for Phase 1B (Week 3-4 - ONLY IF Phase 1A SUCCEEDS)

### Week 3: UI and Enhanced RAG (Days 11-15)
Day 11-12: Streamlit UI
- [ ] Streamlit app starts successfully
- [ ] Document upload interface works
- [ ] Q&A interface with query input and response display

Day 13-14: Enhanced Retrieval
- [ ] Hybrid search (vector + keyword) implemented
- [ ] Hybrid results provide better quality than vector-only
- [ ] Verify: Compare responses between basic and hybrid search

Day 15: Reference Tracking
- [ ] Response includes document source citations
- [ ] Citation format is clear and useful
- [ ] Verify: Ask question and see document sources in response

### Week 4: Integration and Evaluation (Days 16-20)
Day 16-17: Basic Security
- [ ] Basic authentication implemented
- [ ] Protected endpoints require authentication
- [ ] Verify: Unauthenticated requests are rejected

Day 18-19: Performance and Testing
- [ ] Performance monitoring utilities added
- [ ] Basic test coverage (40-50%) achieved
- [ ] Demo scenario prepared for evaluation

Day 20: Evaluation Preparation
- [ ] Document performance metrics
- [ ] Prepare demo for stakeholders
- [ ] Clear recommendations for Phase 2 decision

## Performance Monitoring Utilities

### backend/app/core/utils/performance_utils.py
Purpose: Monitor local Mac resource usage and performance metrics.

```python
import psutil
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
from contextlib import contextmanager

@dataclass
class LocalPerformanceMetrics:
    """Local Mac performance metrics"""
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    disk_usage_gb: float
    timestamp: float

    @property
    def should_throttle(self) -> bool:
        """Should processing be throttled due to resource constraints"""
        return self.memory_percent > 75 or self.cpu_percent > 80

    @property
    def should_warn_user(self) -> bool:
        """Should users be warned about performance"""
        return self.memory_percent > 85

def get_local_metrics() -> LocalPerformanceMetrics:
    """Get current local performance metrics"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return LocalPerformanceMetrics(
        memory_usage_mb=memory.used / 1024 / 1024,
        memory_percent=memory.percent,
        cpu_percent=psutil.cpu_percent(interval=1),
        disk_usage_gb=disk.used / 1024 / 1024 / 1024,
        timestamp=time.time()
    )

@contextmanager
def performance_monitor(operation_name: str):
    """Context manager to monitor performance of specific operations"""
    start_time = time.time()
    start_metrics = get_local_metrics()
    
    try:
        yield
    finally:
        end_time = time.time()
        end_metrics = get_local_metrics()
        
        duration = end_time - start_time
        memory_delta = end_metrics.memory_usage_mb - start_metrics.memory_usage_mb
        
        print(f"Performance: {operation_name}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Memory delta: {memory_delta:.2f}MB")
        print(f"  CPU: {end_metrics.cpu_percent}%")

def should_limit_batch_processing() -> bool:
    """Check if batch processing should be limited based on current resources"""
    metrics = get_local_metrics()
    return metrics.should_throttle
```

Do not implement Phase 2 or 3 features yet - focus only on Phase 1A feasibility requirements first. Only proceed to Phase 1B if Phase 1A proves technical feasibility. The system should prove it can work on local hardware before expanding functionality. The goal is to answer "Can this work?" not "How sophisticated can it be?" in Phase 1A.## Switchover Configuration and Migration Runbooks

### Environment Switching Configuration (.env)
Purpose: Easily switch between local and cloud environments.

```bash
# Add these switches to .env for easy environment switching:

# Environment Selection
ENVIRONMENT=local  # local | cloud_gpu | production
RUN_MODE=local     # local | cloud_gpu

# Vector Store Switching
VECTOR_STORE=pgvector   # pgvector | qdrant
VECTOR_HOST=localhost   # localhost | cloud-qdrant-host
VECTOR_PORT=5432        # 5432 for pgvector, 6333 for qdrant
VECTOR_CLOUD_ENDPOINT=  # Set when using cloud vector store

# LLM Backend Switching
LLM_BACKEND=ollama      # ollama | vllm | openai_api
OLLAMA_HOST=http://localhost:11434
VLLM_HOST=              # Set when using vLLM
OPENAI_API_BASE=        # Set when using OpenAI-compatible API

# Performance Configuration per Environment
# Local Environment (Mac M1/M2/M3)
LOCAL_MAX_CONCURRENT_REQUESTS=1
LOCAL_MEMORY_LIMIT_MB=8192
LOCAL_TIMEOUT_SECONDS=30

# Cloud GPU Environment
CLOUD_MAX_CONCURRENT_REQUESTS=8
CLOUD_MEMORY_LIMIT_MB=32768
CLOUD_TIMEOUT_SECONDS=10

# Current Active Limits (set based on ENVIRONMENT)
MAX_CONCURRENT_REQUESTS=${LOCAL_MAX_CONCURRENT_REQUESTS}
MEMORY_LIMIT_MB=${LOCAL_MEMORY_LIMIT_MB}
TIMEOUT_SECONDS=${LOCAL_TIMEOUT_SECONDS}

# Switch based on environment
if [ "${ENVIRONMENT}" = "cloud_gpu" ]; then
    MAX_CONCURRENT_REQUESTS=${CLOUD_MAX_CONCURRENT_REQUESTS}
    MEMORY_LIMIT_MB=${CLOUD_MEMORY_LIMIT_MB}
    TIMEOUT_SECONDS=${CLOUD_TIMEOUT_SECONDS}
fi
```

### Vector Store Migration Scripts

#### pgvector to Qdrant Export Script
Purpose: Export documents and embeddings from pgvector to migrate to Qdrant.

```python
# scripts/migration/pgvector_to_qdrant.py
import asyncio
import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.http import models
import json
from typing import List, Dict, Any

async def migrate_pgvector_to_qdrant():
    """
    Migrate documents from pgvector to Qdrant
    Usage: python scripts/migration/pgvector_to_qdrant.py
    """
    
    # Connect to pgvector
    pg_conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        database="ai_workflow_local",
        user="dev",
        password="dev123"
    )
    
    # Connect to Qdrant
    qdrant_client = QdrantClient(host="localhost", port=6333)
    
    # Create collection in Qdrant
    qdrant_client.recreate_collection(
        collection_name="documents",
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),  # Adjust size based on embedding model
    )
    
    # Fetch all documents from pgvector
    records = await pg_conn.fetch("""
        SELECT id, content, metadata, embedding 
        FROM document_chunks 
        ORDER BY id
        LIMIT 1000  -- Process in batches
    """)
    
    # Prepare points for Qdrant
    points = []
    for record in records:
        points.append(models.PointStruct(
            id=record['id'],
            vector=record['embedding'],
            payload={
                "content": record['content'],
                "metadata": json.loads(record['metadata']) if record['metadata'] else {},
            }
        ))
    
    # Upload to Qdrant
    qdrant_client.upsert(collection_name="documents", points=points)
    
    print(f"Migrated {len(points)} documents from pgvector to Qdrant")
    
    await pg_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_pgvector_to_qdrant())
```

#### Qdrant to pgvector Import Script
Purpose: Import documents from Qdrant back to pgvector if needed.

```python
# scripts/migration/qdrant_to_pgvector.py
import psycopg2
from qdrant_client import QdrantClient
import json
from typing import List, Dict

def migrate_qdrant_to_pgvector():
    """
    Migrate documents from Qdrant back to pgvector
    Usage: python scripts/migration/qdrant_to_pgvector.py
    """
    
    # Connect to Qdrant
    qdrant_client = QdrantClient(host="localhost", port=6333)
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="ai_workflow_local",
        user="dev",
        password="dev123"
    )
    pg_cursor = pg_conn.cursor()
    
    # Get all points from Qdrant
    scroll_result = qdrant_client.scroll(
        collection_name="documents",
        limit=1000,
        with_payload=True,
        with_vectors=True
    )
    
    points, _ = scroll_result
    
    # Insert into pgvector table
    for point in points:
        content = point.payload.get("content", "")
        metadata_str = json.dumps(point.payload.get("metadata", {}))
        embedding_list = point.vector  # This should be a list of floats
        
        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(map(str, embedding_list)) + "]"
        
        pg_cursor.execute("""
            INSERT INTO document_chunks (id, content, metadata, embedding)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
        """, (point.id, content, metadata_str, embedding_str))
    
    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    
    print(f"Migrated {len(points)} documents from Qdrant to pgvector")

if __name__ == "__main__":
    migrate_qdrant_to_pgvector()
```

### LLM Backend Switching

#### Ollama to vLLM Migration Guide
1. **Update .env**:
   ```bash
   LLM_BACKEND=vllm
   OLLAMA_HOST=
   VLLM_HOST=http://localhost:8000  # or cloud address
   ```

2. **Start vLLM service**:
   ```bash
   # Using Docker
   docker run --gpus all -p 8000:8000 \
     --shm-size=1g -e CUDA_VISIBLE_DEVICES=0 \
     vllm/vllm-openai:latest \
     --model Qwen/Qwen2-7B-Instruct
   ```

3. **Update API calls**:
   - Change from Ollama client to OpenAI-compatible client
   - Update base URL to VLLM endpoint

#### Embedding Model Migration
When switching embedding models, you'll need to:
1. Update .env with new model name
2. Recreate vector index with new embeddings
3. Re-embed all documents

```bash
# scripts/rebuild_embeddings.sh
#!/bin/bash
# Rebuild all embeddings with new model

echo "Starting embedding rebuild process..."

# Clear existing vectors
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='ai_workflow_local', user='dev', password='dev123')
cur = conn.cursor()
cur.execute('DELETE FROM document_chunks;')
conn.commit()
cur.close()
conn.close()
"

# Re-process all documents with new embedding model
python -m backend.app.scripts.process_documents --rebuild-all

echo "Embedding rebuild completed"
```

## Cost Control and Security Guardrails

### Cloud GPU Budget Monitoring
Purpose: Automatically shut down cloud resources when budget limits are reached.

```bash
# scripts/cost_control/gpu_shutdown.sh
#!/bin/bash
# Automatic shutdown script for cloud GPU resources

BUDGET_ALERT_THRESHOLD=100  # Alert when daily cost exceeds $100
BUDGET_HARD_LIMIT=200       # Shut down when daily cost exceeds $200

# Function to check current usage (example for RunPod)
check_runpod_usage() {
    # This would integrate with cloud provider API
    echo "Checking RunPod usage..."
    
    # Get current running pods
    RUNNING_PODS=$(curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
        "https://api.runpod.io/graphql" \
        -d '{"query":"query { myself { pods { id desiredGpu { name } costPerHr { value } } } }"}' \
        2>/dev/null | jq -r '.data.myself.pods[] | .costPerHr.value' | awk '{sum+=$1} END {print sum+0}')
    
    if [ -z "$RUNNING_PODS" ]; then
        echo "0"  # Default to 0 if API call fails
    else
        echo $RUNNING_PODS
    fi
}

# Check current costs
CURRENT_HOURLY=$(check_runpod_usage)

# Calculate estimated daily cost
ESTIMATED_DAILY_COST=$(echo "$CURRENT_HOURLY * 24" | bc)

if (( $(echo "$ESTIMATED_DAILY_COST > $BUDGET_HARD_LIMIT" | bc -l) )); then
    echo "ALERT: Estimated daily cost ($ESTIMATED_DAILY_COST) exceeds hard limit ($BUDGET_HARD_LIMIT)"
    echo "SHUTTING DOWN GPU resources..."
    # Add shutdown commands here
fi

if (( $(echo "$ESTIMATED_DAILY_COST > $BUDGET_ALERT_THRESHOLD" | bc -l) )); then
    echo "WARNING: Estimated daily cost ($ESTIMATED_DAILY_COST) exceeds alert threshold ($BUDGET_ALERT_THRESHOLD)"
    echo "Consider reducing GPU usage"
fi
```

### Data Privacy and Content Filtering
Purpose: Protect sensitive data and filter inappropriate content.

```python
# backend/app/core/security/content_filter.py
import re
from typing import List, Dict
import logging

class ContentFilter:
    """Content filtering for privacy and safety"""
    
    SENSITIVE_PATTERNS = [
        # Email patterns
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        # Phone numbers
        re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        # Credit card (simplified)
        re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        # SSN (simplified)
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    ]
    
    INAPPROPRIATE_KEYWORDS = [
        'password', 'secret', 'confidential', 'private', 'internal'
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def sanitize_content(self, content: str) -> Dict[str, any]:
        """Remove or mask sensitive information from content"""
        original_length = len(content)
        
        # Replace sensitive patterns with placeholders
        sanitized_content = content
        findings = []
        
        for i, pattern in enumerate(self.SENSITIVE_PATTERNS):
            matches = pattern.findall(content)
            if matches:
                findings.extend([{
                    'type': f'sensitive_pattern_{i}',
                    'value': match,
                    'start': content.find(match)
                } for match in matches])
                
                # Replace with placeholders
                sanitized_content = pattern.sub(f'[REDACTED_{i}]', sanitized_content)
        
        # Check for inappropriate keywords
        for keyword in self.INAPPROPRIATE_KEYWORDS:
            if keyword.lower() in content.lower():
                findings.append({
                    'type': 'keyword',
                    'value': keyword,
                    'start': content.lower().find(keyword.lower())
                })
        
        self.logger.info(f"Content sanitization: {len(findings)} issues found, {original_length} -> {len(sanitized_content)} chars")
        
        return {
            'sanitized_content': sanitized_content,
            'findings': findings,
            'redacted_count': len(findings)
        }
    
    def is_content_safe(self, content: str) -> bool:
        """Check if content is safe for processing"""
        sanitize_result = self.sanitize_content(content)
        return len(sanitize_result['findings']) == 0

# Usage in document processing
content_filter = ContentFilter()

def process_document_safely(content: str):
    """Process document with content filtering"""
    result = content_filter.sanitize_content(content)
    
    if result['findings']:
        print(f"Content filter triggered: {len(result['findings'])} sensitive items found")
        for finding in result['findings']:
            print(f"  - {finding['type']}: {finding['value']}")
    
    return result['sanitized_content']
```

### RAG Evaluation Framework
Purpose: Systematic evaluation of RAG system quality.

```python
# scripts/evaluation/rag_evaluation.py
from typing import List, Dict
import json
import asyncio
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    query: str
    response: str
    expected_answer: str
    faithfulness: float  # How factual the response is
    relevance: float     # How relevant the response is
    answer_correctness: float  # How correct the answer is
    context_precision: float   # How precise the retrieved context is
    overall_score: float

class RAGEvaluator:
    """Comprehensive RAG evaluation framework"""
    
    def __init__(self):
        self.evaluation_dataset = []
    
    def load_evaluation_dataset(self, dataset_path: str):
        """Load evaluation dataset from JSON file"""
        with open(dataset_path, 'r') as f:
            self.evaluation_dataset = json.load(f)
    
    async def evaluate_faithfulness(self, query: str, response: str, context: List[str]) -> float:
        """Evaluate if response is faithful to the context"""
        # Implement faithfulness evaluation using LLM or other method
        # This is a simplified version - in practice would use more sophisticated methods
        return 0.8  # Placeholder
    
    async def evaluate_relevance(self, query: str, response: str) -> float:
        """Evaluate if response is relevant to the query"""
        # Implement relevance evaluation
        return 0.85  # Placeholder
    
    async def evaluate_answer_correctness(self, response: str, expected: str) -> float:
        """Evaluate correctness of the answer"""
        # Implement answer correctness evaluation
        return 0.75  # Placeholder
    
    async def evaluate_context_precision(self, retrieved_context: List[str], expected_context: List[str]) -> float:
        """Evaluate precision of retrieved context"""
        # Implement context precision evaluation
        return 0.9  # Placeholder
    
    async def evaluate_single_query(self, query: str, expected_answer: str) -> EvaluationResult:
        """Evaluate a single query-response pair"""
        # Get response from RAG system
        response = await self.get_rag_response(query)
        
        # Get retrieved context (if available)
        context = await self.get_retrieved_context(query)
        
        # Perform individual evaluations
        faithfulness = await self.evaluate_faithfulness(query, response, context)
        relevance = await self.evaluate_relevance(query, response)
        answer_correctness = await self.evaluate_answer_correctness(response, expected_answer)
        context_precision = await self.evaluate_context_precision(context, [expected_answer])
        
        overall_score = (faithfulness + relevance + answer_correctness + context_precision) / 4
        
        return EvaluationResult(
            query=query,
            response=response,
            expected_answer=expected_answer,
            faithfulness=faithfulness,
            relevance=relevance,
            answer_correctness=answer_correctness,
            context_precision=context_precision,
            overall_score=overall_score
        )
    
    async def evaluate_all(self) -> List[EvaluationResult]:
        """Evaluate the entire dataset"""
        results = []
        
        for item in self.evaluation_dataset:
            query = item['query']
            expected_answer = item['expected_answer']
            
            result = await self.evaluate_single_query(query, expected_answer)
            results.append(result)
        
        return results
    
    async def get_rag_response(self, query: str) -> str:
        """Get response from RAG system - implement based on your RAG implementation"""
        # This should connect to your actual RAG system
        return f"Sample response to: {query}"  # Placeholder
    
    async def get_retrieved_context(self, query: str) -> List[str]:
        """Get retrieved context from RAG system - implement based on your RAG implementation"""
        return [f"Context for {query}"]  # Placeholder

# Evaluation checklist
"""
RAG Evaluation Checklist:

1. Faithfulness Assessment:
   - Does the response reflect the content of the provided context?
   - Are there hallucinations or fabrications?
   - Does the response stay within the bounds of the provided information?

2. Relevance Assessment:
   - Does the response address the query directly?
   - Is the information provided relevant to user's question?
   - Is the response appropriately focused?

3. Answer Correctness:
   - Is the answer factually correct?
   - Does it match known ground truth?
   - Are there any factual errors?

4. Context Precision:
   - Are the retrieved documents relevant to the query?
   - Is the retrieval system efficient?
   - Are irrelevant documents being retrieved?

5. Performance Metrics:
   - Response time (target: <10s P95)
   - Throughput (queries per second)
   - Resource utilization
"""

# Example usage
async def main():
    evaluator = RAGEvaluator()
    evaluator.load_evaluation_dataset('evaluation_dataset.json')
    
    results = await evaluator.evaluate_all()
    
    # Print summary
    avg_overall_score = sum(r.overall_score for r in results) / len(results)
    avg_faithfulness = sum(r.faithfulness for r in results) / len(results)
    
    print(f"Average overall score: {avg_overall_score:.2f}")
    print(f"Average faithfulness: {avg_faithfulness:.2f}")
    
    # Save detailed results
    with open('evaluation_results.json', 'w') as f:
        json.dump([r.__dict__ for r in results], f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
```

## Minimal Makefile and Docker Compose Templates

### Makefile
Purpose: Simplify common development tasks.

```makefile
# Makefile for AI Workflow Platform

# Environment (change to 'cloud_gpu' when needed)
ENVIRONMENT ?= local

# Services
POSTGRES_SERVICE = postgres
REDIS_SERVICE = redis
OLLAMA_SERVICE = ollama

.PHONY: help
help: ## Show this help
	@echo "AI Workflow Platform Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Common Commands:"
	@grep -E '^[a-zA-Z_0-9%-]+:.*?## .*$$' $(word 1,$(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: env-up
env-up: ## Start local development environment
	docker-compose -f docker-compose.local.yml up -d
	brew services start ollama || echo "Ollama not installed via brew, please start manually"
	@echo "Environment started. Waiting for services..."
	sleep 10

.PHONY: env-down
env-down: ## Stop local development environment
	docker-compose -f docker-compose.local.yml down
	brew services stop ollama || echo "Ollama not running via brew"

.PHONY: install-model
install-model: ## Install Qwen2.5-7B model
	ollama pull qwen2.5:7b

.PHONY: setup
setup: env-up install-model ## Complete local setup (environment + model)

.PHONY: backend-up
backend-up: ## Start backend service
	cd backend && python -m uvicorn app.main:app --reload

.PHONY: frontend-up
frontend-up: ## Start frontend (Streamlit)
	cd frontend && streamlit run streamlit_app.py

.PHONY: test
test: ## Run tests
	cd backend && python -m pytest tests/ -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	cd backend && python -m pytest tests/ --cov=app --cov-report=html

.PHONY: lint
lint: ## Lint code
	cd backend && flake8 . && mypy . && black --check .
	cd backend && cd frontend && if [ -f package.json ]; then npm run lint; fi

.PHONY: format
format: ## Format code
	cd backend && black . && isort .
```

Do not implement Phase 2 or 3 features yet - focus only on Phase 1A feasibility requirements first. Only proceed to Phase 1B if Phase 1A proves technical feasibility. The system should prove it can work on local hardware before expanding functionality. The goal is to answer "Can this work?" not "How sophisticated can it be?" in Phase 1A.