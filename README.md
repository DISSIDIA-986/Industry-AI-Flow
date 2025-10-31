# AI Workflow Platform - 本地可行性验证

> Week 1-2: Mac 本地 RAG 技术可行性验证项目

## 项目目标

在 2 周内验证 Mac 本地技术可行性，回答"是否继续投入"的决策问题。

### 验收标准

- [x] 文档导入：1000份文档入库并向量化，耗时<10分钟
- [x] RAG问答：单次查询响应时间<10秒（P95）
- [x] 准确率：简单问答准确率>70%（基于20个测试问题）
- [x] 稳定性：连续运行30分钟无崩溃，内存占用<80%

## 技术栈

- **LLM**: Ollama + Qwen2.5:7b（本地运行）
- **向量库**: PostgreSQL + pgvector（本地 homebrew）
- **嵌入模型**: sentence-transformers/all-MiniLM-L6-v2（384维）
- **后端**: FastAPI
- **前端**: 命令行脚本（Week 1-2）

## 环境要求

- macOS（M1/M2/M3 推荐）
- 内存: 16GB+ RAM
- Python: 3.10+
- PostgreSQL: 14+（通过 homebrew 安装）
- Redis（通过 homebrew 安装）
- Ollama

## 快速开始

### 方式一：使用 Miniconda（推荐）

```bash
# 1. 创建虚拟环境
conda create -n ai_workflow python=3.10
conda activate ai_workflow

# 2. 运行环境搭建脚本
make setup

# 3. 验证环境
bash scripts/verify_env.sh
```

### 方式二：使用 base 环境

```bash
# 如果 base 环境已安装常用库，可直接使用
conda activate base

# 运行环境搭建脚本
make setup
```

## 使用指南

### 1. 启动 API 服务

```bash
make start
```

访问 API 文档：http://localhost:8000/docs

### 2. 导入测试文档

```bash
# 将测试文档放在 samples/ 目录
python scripts/import_docs.py ./samples/
```

**预期输出**：
```
📁 找到 X 个文档
[1/X] 处理: document.pdf
  ✓ 提取文本: 5000 字符
  ✓ 分块完成: 12 块
  ✓ 向量化完成: 12 个向量
  ✓ 存储成功: doc_id=...

📊 导入完成
成功: X/X 文档
总块数: XX
耗时: X.XX 秒
```

### 3. 运行 RAG 测试

```bash
make test
```

**预期输出**：
```
📊 评估结果
准确率: 75.0% (15/20)
平均延迟: 6.2秒
P95延迟: 8.7秒

✅ 验收标准检查
准确率>70%: ✅ 通过
P95延迟<10秒: ✅ 通过
```

### 4. 手动测试 RAG 查询

```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是RAG系统?", "top_k": 3}'
```

## 项目结构

```
Industry-AI-Flow/
├── backend/                    # 后端代码
│   ├── config.py              # 配置管理
│   ├── main.py                # FastAPI 应用
│   ├── requirements.txt       # Python 依赖
│   └── services/              # 业务逻辑
│       ├── document_loader.py # 文档加载
│       ├── chunker.py         # 文档分块
│       ├── embedder.py        # 向量嵌入
│       ├── vectorstore.py     # 向量存储
│       ├── ollama_client.py   # LLM 客户端
│       └── rag_engine.py      # RAG 引擎
├── scripts/                   # 工具脚本
│   ├── setup_local.sh         # 环境搭建
│   ├── verify_env.sh          # 环境验证
│   ├── import_docs.py         # 批量导入
│   └── test_rag.py            # RAG 测试
├── infra/                     # 基础设施配置
│   ├── init.sql               # 数据库初始化
│   └── docker-compose.yaml    # Docker配置（可选）
├── samples/                   # 测试数据
│   └── test_questions.json    # 测试问题集
├── .env.example               # 环境变量模板
├── Makefile                   # 常用命令
└── README.md                  # 项目文档
```

## 配置说明

### 环境变量

复制 `.env.example` 到 `.env` 并根据需要修改：

```bash
# 数据库配置（本地 PostgreSQL）
POSTGRES_HOST=localhost
POSTGRES_DB=ai_workflow

# Ollama 配置
OLLAMA_MODEL=qwen2.5:7b

# 文档处理配置
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# RAG 配置
TOP_K=3
```

## API 接口

### 健康检查

```http
GET /health
```

**响应**：
```json
{
  "status": "ok",
  "memory_usage_mb": 245.67
}
```

### RAG 查询

```http
POST /rag/query
Content-Type: application/json

{
  "question": "你的问题",
  "top_k": 3
}
```

**响应**：
```json
{
  "question": "你的问题",
  "answer": "基于上下文的答案...",
  "sources": ["doc_id_1", "doc_id_2"],
  "retrieved_chunks": [...]
}
```

## 常见问题

### Q: PostgreSQL 连接失败？

```bash
# 检查服务状态
brew services list

# 启动服务
brew services start postgresql
```

### Q: Ollama 模型未下载？

```bash
# 下载模型（约5GB，需5-10分钟）
ollama pull qwen2.5:7b

# 验证
ollama list
```

### Q: 内存不足？

```bash
# 减少批处理大小
# 修改 .env 文件
MAX_BATCH_SIZE=20
CHUNK_SIZE=300
```

### Q: Python 依赖安装失败？

```bash
# 使用 conda 安装
conda install -c conda-forge sentence-transformers psycopg2

# 或使用 pip
pip install -r backend/requirements.txt
```

## 资源优化

本项目优先使用 homebrew 本地服务，相比 Docker 方案：

- **内存节省**: 约 2-3GB（无 Docker 容器开销）
- **磁盘节省**: 无需 Docker 镜像和卷存储
- **性能提升**: 减少虚拟化层开销

## 开发进度

- [x] Day 1-2: 环境搭建
- [x] Day 3-4: FastAPI 基础应用
- [x] Day 5-7: 向量化管道
- [x] Day 8-10: RAG 核心功能
- [x] Day 11-12: 测试评估
- [x] Day 13-14: 文档和工具

## 下一步

根据 Week 1-2 验证结果，选择后续路径：

### 路径A: 效果良好，继续投入

- 进入 Phase 2：云 GPU 测试（AutoDL RTX 4090）
- 升级到 Qwen2.5-14B 模型
- 使用 Qdrant 向量库
- 实现完整 React 前端

### 路径B: 效果一般，优化调整

- 提示词优化
- 检索参数调整
- 数据质量改进

### 路径C: 方案不可行，重新评估

- 转向纯 API 方案（ChatGPT/Claude）
- 采用托管 RAG 服务
- 简化需求

## 许可证

MIT License

## 参考文档

- [本地开发可行性方案](research/local-development-feasibility.md)
- [实施 Prompt v2.2](research/local-development-feasibility.prompt.v2.md)
- [综合架构方案](research/best-ai-workflow.plan.md)
