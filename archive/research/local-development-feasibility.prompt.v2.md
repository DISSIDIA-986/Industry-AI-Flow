# 本地开发可行性实施 Prompt v2.0

> **目的**: 用2周时间在Mac本地验证RAG技术可行性，回答"能否继续投入"的问题。
> **原则**: 最小化实现、快速验证、数据驱动决策。

---

## 1. 核心目标与验收标准

### 1.1 唯一目标
**在Mac本地（M1/M2/M3 + 16GB RAM）证明基础RAG流程技术可行**

### 1.2 验收标准（Week 2结束时必须达成）
- [ ] 文档导入：1000份文档入库并向量化，耗时<10分钟
- [ ] RAG问答：单次查询响应时间<10秒（P95）
- [ ] 准确率：简单问答准确率>70%（基于20个测试问题）
- [ ] 稳定性：连续运行30分钟无崩溃，内存占用<80%

### 1.3 决策标准
**Week 2结束评估**：
- ✅ 4项全部达标 → 继续投入（进入Phase 2）
- ⚠️ 3项达标 → 调整方案后重试1周
- ❌ <3项达标 → 暂停项目或重新评估架构

---

## 2. 技术栈（固定，不可变）

### 2.1 Week 1-2 技术选型
```yaml
LLM: Ollama + Qwen2.5:7b（本地运行）
向量库: PostgreSQL + pgvector（优先使用本地homebrew安装）
嵌入: sentence-transformers/all-MiniLM-L6-v2（本地模型，384维）
后端: FastAPI（轻量级API）
前端: 命令行脚本（Week 1）→ Streamlit（Week 2，可选）
容器: Docker Compose（可选，仅当本地服务不可用时使用）
```

### 2.2 明确禁止（推迟到Phase 2+）
```
❌ OCR（DeepSeek/PaddleOCR）
❌ 混合检索（BM25+向量融合）
❌ 重排序（bge-reranker）
❌ 认证系统（RBAC）
❌ Agent框架
❌ 代码执行沙箱
❌ React前端
```

---

## 3. 目录结构（最小化）

```
Industry-AI-Flow/
├── research/                    # 已有调研文档
├── backend/
│   ├── main.py                  # FastAPI入口（Week 1）
│   ├── config.py                # 配置管理（Week 1）
│   ├── services/
│   │   ├── document_loader.py   # 文档加载（Week 1）
│   │   ├── chunker.py           # 文档分块（Week 1）
│   │   ├── embedder.py          # 向量化（Week 1）
│   │   ├── vectorstore.py       # pgvector客户端（Week 1）
│   │   └── rag_engine.py        # RAG核心（Week 2）
│   └── requirements.txt         # Python依赖
├── scripts/
│   ├── setup_local.sh           # 一键环境搭建（Week 1 Day 1）
│   ├── import_docs.py           # 批量导入脚本（Week 1 Day 5）
│   └── test_rag.py              # RAG测试脚本（Week 2）
├── infra/
│   ├── docker-compose.yaml      # PostgreSQL + Redis（Week 1）
│   └── init.sql                 # 数据库初始化（Week 1）
├── samples/                     # 测试文档（用户提供）
├── .env.example                 # 配置模板
├── .env                         # 本地配置（.gitignore）
├── Makefile                     # 常用命令
└── README.md                    # 运行指南
```

---

## 4. Week 1 实施计划：核心管道搭建

### 目标
建立"文档→向量化→存储"的基础管道，无需UI

### Day 1-2: 环境搭建

**核心任务**：创建自动化脚本 `scripts/setup_local.sh`，该脚本包含以下所有环境搭建和验证步骤。最终开发者只需运行 `bash scripts/setup_local.sh` 即可完成环境准备。

**脚本应包含的步骤**：
```bash
# 1. 检查现有安装
brew list | grep postgresql  # 检查PostgreSQL是否已安装
brew list | grep redis       # 检查Redis是否已安装
ollama list                  # 检查Ollama及模型

# 2. 如果服务未安装，执行安装（通常可跳过）
# brew install postgresql redis ollama

# 3. 启动本地服务（优先使用本地服务）
brew services start postgresql  # 启动PostgreSQL
brew services start redis       # 启动Redis

# 4. 初始化PostgreSQL数据库和pgvector
createdb ai_workflow  # 创建数据库（如果不存在）
psql ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;"  # 启用pgvector

# 5. 下载LLM模型（如果未下载）
ollama pull qwen2.5:7b

# 6. 验证环境
ollama run qwen2.5:7b "你好"  # 应返回中文回复
psql -h localhost -d ai_workflow -c "SELECT 1;"  # 应返回1
redis-cli ping  # 应返回PONG
```

**验收检查**：
- [ ] PostgreSQL服务运行中（`brew services list | grep postgresql` 显示started）
- [ ] Redis服务运行中（`brew services list | grep redis` 显示started）
- [ ] Ollama模型可用（`ollama list` 显示qwen2.5:7b）
- [ ] PostgreSQL连接成功
- [ ] pgvector扩展已启用（`psql ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';"` 显示vector）

**产出文件**：
- `infra/init.sql`（建表SQL + pgvector扩展）
- `scripts/setup_local.sh`（自动化脚本，优先使用本地服务）
- `.env`（基于.env.example创建）
- `infra/docker-compose.yaml`（可选，仅当本地服务不可用时使用）

---

### Day 3-4: 基础API

**任务清单**：
```python
# backend/main.py - FastAPI应用
from fastapi import FastAPI, UploadFile
import uvicorn

app = FastAPI(title="RAG Feasibility Test")

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "memory_usage_mb": get_memory_usage()}

def get_memory_usage() -> float:
    """获取当前进程内存使用(MB)"""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

@app.post("/documents/upload")
async def upload_document(file: UploadFile):
    """上传单个文档（仅PDF和TXT）"""
    # 保存文件 → 返回文档ID
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**验收检查**：
- [ ] `python backend/main.py` 启动成功
- [ ] 访问 http://localhost:8000/docs 看到Swagger文档
- [ ] `curl http://localhost:8000/health` 返回JSON
- [ ] 上传PDF文件成功（`curl -F "file=@test.pdf" http://localhost:8000/documents/upload`）

**产出文件**：
- `backend/main.py`（FastAPI核心）
- `backend/config.py`（环境变量加载）
- `backend/requirements.txt`（依赖列表，见下方示例）

**backend/requirements.txt 示例**：
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
pgvector==0.2.5
sentence-transformers==2.2.2
PyMuPDF==1.23.8
requests==2.31.0
pydantic==1.10.13
psutil==5.9.6
python-multipart==0.0.6
```

---

### Day 5-7: 向量化管道

**任务清单**：
```python
# backend/services/document_loader.py
def load_pdf(file_path: str) -> str:
    """提取PDF文本（使用PyMuPDF）"""
    import fitz
    doc = fitz.open(file_path)
    text = "\n".join(page.get_text() for page in doc)
    return text

# backend/services/chunker.py
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """简单分块：按字符数切分，带重叠"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

# backend/services/embedder.py
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_texts(texts: list[str]) -> list[list[float]]:
    """向量化文本"""
    return model.encode(texts, show_progress_bar=True).tolist()

# backend/services/vectorstore.py
import psycopg2
from pgvector.psycopg2 import register_vector

def store_chunks(doc_id: str, chunks: list[str], embeddings: list[list[float]]):
    """存储文档块和向量"""
    conn = psycopg2.connect(...)
    register_vector(conn)
    cur = conn.cursor()

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        cur.execute(
            "INSERT INTO document_chunks (doc_id, chunk_id, content, embedding) VALUES (%s, %s, %s, %s)",
            (doc_id, i, chunk, embedding)
        )
    conn.commit()
```

**验收检查**：
- [ ] PDF文件解析成功（文本提取正确）
- [ ] 文本分块合理（每块约500字符）
- [ ] 向量化完成（384维float数组）
- [ ] 数据写入pgvector（`SELECT COUNT(*) FROM document_chunks;` 显示数据）
- [ ] 批量导入1000文档<10分钟（`time python scripts/import_docs.py ./samples`）

**产出文件**：
- `backend/services/document_loader.py`
- `backend/services/chunker.py`
- `backend/services/embedder.py`
- `backend/services/vectorstore.py`
- `scripts/import_docs.py`（批量导入脚本）

---

## 5. Week 2 实施计划：RAG功能验证

### 目标
实现查询→检索→生成的完整流程，验证准确率

### Day 8-10: RAG核心实现

**任务清单**：
```python
# backend/services/rag_engine.py
class SimpleRAG:
    def __init__(self, vectorstore, llm_client):
        self.vectorstore = vectorstore
        self.llm_client = llm_client

    def query(self, question: str, top_k: int = 3) -> dict:
        """RAG查询流程"""
        # 1. 向量化问题
        query_embedding = embed_texts([question])[0]

        # 2. 检索相似文档块
        similar_chunks = self.vectorstore.similarity_search(
            query_embedding, top_k=top_k
        )

        # 3. 构建提示词
        context = "\n---\n".join([chunk['content'] for chunk in similar_chunks])
        prompt = f"""基于以下上下文回答问题。如果无法从上下文中找到答案，请说"我不知道"。

上下文：
{context}

问题：{question}

答案："""

        # 4. LLM生成答案
        answer = self.llm_client.generate(prompt)

        # 5. 返回结果
        return {
            "question": question,
            "answer": answer,
            "sources": [chunk['doc_id'] for chunk in similar_chunks],
            "retrieved_chunks": similar_chunks
        }

# backend/services/ollama_client.py
import requests
from backend.config import settings

class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_host
        self.model = model or settings.ollama_model

    def generate(self, prompt: str) -> str:
        """调用Ollama生成文本"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False}
        )
        return response.json()["response"]
```

**API端点**：
```python
# backend/main.py 添加
@app.post("/rag/query")
async def rag_query(question: str):
    """RAG查询接口"""
    try:
        result = rag_engine.query(question)
        return result
    except Exception as e:
        # Week 1-2阶段：简单错误处理即可
        return {
            "error": str(e),
            "question": question,
            "answer": "系统错误，请查看日志"
        }
```

**验收检查**：
- [ ] 向量检索返回相关文档块（余弦相似度>0.5）
- [ ] LLM生成答案正常（非空，非乱码）
- [ ] 单次查询<10秒（含检索+生成）
- [ ] API端点工作正常（`curl -X POST http://localhost:8000/rag/query -d '{"question": "测试问题"}'`）

**产出文件**：
- `backend/services/rag_engine.py`
- `backend/services/ollama_client.py`
- 更新 `backend/main.py`（添加/rag/query端点）

---

### Day 11-12: 测试与评估

**任务清单**：
```python
# scripts/test_rag.py
"""RAG系统测试脚本"""
import json
import time
from backend.services.rag_engine import SimpleRAG

def load_test_cases(file_path: str = "samples/test_questions.json"):
    """加载测试问题集"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def evaluate_accuracy(test_cases):
    """评估准确率"""
    correct = 0
    total = len(test_cases)
    latencies = []

    for case in test_cases:
        start = time.time()
        result = rag_engine.query(case["question"])
        latency = time.time() - start
        latencies.append(latency)

        # 判断：答案中包含所有期望关键词
        answer_lower = result["answer"].lower()
        keywords_matched = all(
            keyword.lower() in answer_lower
            for keyword in case.get("expected_keywords", [])
        )

        if keywords_matched:
            correct += 1
            print(f"✅ {case['question']}")
        else:
            print(f"❌ {case['question']}")
            print(f"   期望关键词: {case.get('expected_keywords', [])}")
            print(f"   实际答案: {result['answer'][:100]}...")

    accuracy = correct / total
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\n--- 评估结果 ---")
    print(f"准确率: {accuracy*100:.1f}% ({correct}/{total})")
    print(f"平均延迟: {avg_latency:.2f}秒")
    print(f"P95延迟: {p95_latency:.2f}秒")

    return {
        "accuracy": accuracy,
        "avg_latency": avg_latency,
        "p95_latency": p95_latency,
        "correct": correct,
        "total": total
    }

if __name__ == "__main__":
    # 加载测试问题集
    test_cases = load_test_cases()

    # 执行评估
    results = evaluate_accuracy(test_cases)

    # 保存结果
    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
```

**验收检查**：
- [ ] 准确率>70%（至少14/20正确）
- [ ] P95延迟<10秒
- [ ] 无内存泄漏（`htop` 观察内存稳定）
- [ ] 测试结果保存到JSON文件

**产出文件**：
- `scripts/test_rag.py`（评估脚本）
- `evaluation_results.json`（测试结果）
- `samples/test_questions.json`（测试问题集，格式见下方）

**测试问题集格式**（`samples/test_questions.json`）：
```json
[
  {
    "question": "什么是RAG系统?",
    "expected_keywords": ["检索", "增强", "生成"],
    "category": "basic"
  },
  {
    "question": "pgvector的主要功能是什么?",
    "expected_keywords": ["向量", "相似度", "搜索"],
    "category": "technical"
  }
]
```

---

### Day 13-14: 决策准备

**任务**：
1. **性能报告**：汇总Week 1-2所有指标
2. **问题清单**：记录所有技术问题和解决方案
3. **成本估算**：记录实际开发时间和遇到的困难
4. **下一步建议**：是否继续、需要什么资源

**决策会议准备材料**：
```markdown
# Week 1-2 可行性验证报告

## 验收结果
- [x/✗] 1000文档入库 <10分钟: ___分钟
- [x/✗] 查询响应 <10秒: P95=___秒
- [x/✗] 准确率 >70%: ___% (___/20)
- [x/✗] 稳定性: 内存峰值___%, 无崩溃

## 技术发现
1. Mac M1性能表现: ___
2. pgvector性能: ___
3. Ollama 7B效果: ___
4. 主要瓶颈: ___

## 遇到的问题
1. 问题描述 → 解决方案 → 耗时
2. ...

## 下一步建议
- [ ] 继续Phase 2（云GPU测试）
- [ ] 调整方案后重试
- [ ] 暂停项目

## 资源需求（如果继续）
- 云GPU: AutoDL RTX 4090, 预计¥___/月
- 开发时间: ___周
- 团队规模: ___人
```

---

## 6. 关键约束与规则

### 6.1 技术约束
```yaml
必须遵守:
  - Python 3.10+
  - FastAPI（不要Flask）
  - pgvector（不要Chroma/Qdrant）
  - sentence-transformers本地模型（不要OpenAI API）
  - Docker Compose（不要K8s）

明确禁止:
  - 引入新的向量库
  - 使用付费API（OpenAI/Claude）
  - 实现认证系统
  - 写单元测试（Week 1-2仅手动测试）
  - 过度抽象（避免工厂模式等）
```

### 6.2 质量标准
```yaml
Week 1-2 标准（宽松）:
  - 代码可运行 > 代码优雅
  - 功能验证 > 测试覆盖
  - 直接实现 > 架构设计
  - 硬编码配置 > 灵活配置

允许的"坏实践":
  - 全局变量: OK（快速验证阶段）
  - 硬编码: OK（配置少时）
  - 无日志: OK（能print调试即可）
  - 无异常处理: OK（能看到错误栈即可）
```

### 6.3 性能目标
```yaml
Mac M1/M2/M3 (16GB RAM):
  文档导入: 100文档/分钟
  向量化: 1000段/分钟
  查询延迟: P95 <10秒
  内存占用: <12GB (留4GB给系统)
  并发: 1用户（无并发要求）
```

---

## 7. 配置文件示例

### 7.1 docker-compose.yaml（可选，仅当本地服务不可用时使用）

> **说明**: 如果您已通过homebrew安装PostgreSQL和Redis，建议直接使用本地服务而非Docker，可节省约2-3GB内存和CPU资源。只有在本地服务无法安装或配置失败时才使用此Docker Compose配置。

```yaml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:latest
    container_name: rag_postgres
    environment:
      POSTGRES_DB: ai_workflow
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev123
    ports:
      - "5432:5432"
    volumes:
      - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev -d ai_workflow"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: rag_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### 7.2 infra/init.sql
```sql
-- 启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档表
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    chunk_count INTEGER DEFAULT 0
);

-- 创建文档块表（带向量列）
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 输出384维
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建向量索引（加速相似度搜索）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 为doc_id创建索引
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks(doc_id);
```

### 7.3 .env.example
```bash
# 数据库配置（使用本地homebrew安装的PostgreSQL）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_workflow
# 注意：本地PostgreSQL使用当前用户名，无需密码
# 如果使用Docker，则需要配置POSTGRES_USER和POSTGRES_PASSWORD

# Ollama配置
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# 向量化配置
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384

# 文档处理配置
CHUNK_SIZE=500
CHUNK_OVERLAP=50
MAX_FILE_SIZE_MB=10
SUPPORTED_FORMATS=pdf,txt

# RAG配置
TOP_K=3
MAX_CONTEXT_LENGTH=2000

# 性能配置
MAX_BATCH_SIZE=50
MEMORY_LIMIT_GB=12
```

### 7.4 backend/config.py
```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 数据库（支持本地homebrew PostgreSQL）
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_workflow")
    postgres_user: str = os.getenv("POSTGRES_USER", "")  # 本地PostgreSQL留空使用当前用户
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")  # 本地PostgreSQL无密码

    # Ollama
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    # 向量化
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # 文档处理
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # RAG
    top_k: int = int(os.getenv("TOP_K", "3"))

    @property
    def database_url(self) -> str:
        # 本地PostgreSQL: postgresql://localhost:5432/ai_workflow
        # Docker PostgreSQL: postgresql://user:password@localhost:5432/ai_workflow
        if self.postgres_user and self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        else:
            return f"postgresql://{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

settings = Settings()
```

### 7.5 Makefile
```makefile
.PHONY: help setup start stop test clean

help:
	@echo "可用命令:"
	@echo "  make setup   - 初始化环境（首次运行）"
	@echo "  make start   - 启动API服务"
	@echo "  make stop    - 停止API服务"
	@echo "  make test    - 运行RAG测试"
	@echo "  make clean   - 清理数据库数据"

setup:
	@echo "🚀 初始化环境..."
	@bash scripts/setup_local.sh

start:
	@echo "▶️  启动API服务..."
	@echo "确保PostgreSQL和Redis已启动: brew services list"
	cd backend && python main.py

stop:
	@echo "⏸️  停止API服务（使用Ctrl+C）"
	@echo "如需停止数据库服务: brew services stop postgresql redis"

test:
	@echo "🧪 运行测试..."
	python scripts/test_rag.py

clean:
	@echo "🗑️  清理数据库数据..."
	psql ai_workflow -c "TRUNCATE TABLE document_chunks, documents CASCADE;"
	@echo "如需完全删除数据库: dropdb ai_workflow"
```

---

## 8. 最终验收清单

### 8.1 环境验收（Day 2结束）
```bash
# 运行验收脚本
bash scripts/verify_env.sh

# 预期输出：
✅ PostgreSQL服务运行中（brew services）
✅ PostgreSQL连接成功
✅ pgvector扩展已启用
✅ Redis服务运行中（brew services）
✅ Redis连接成功
✅ Ollama模型可用（qwen2.5:7b）
✅ Python依赖已安装
```

### 8.2 管道验收（Day 7结束）
```bash
# 运行导入测试
python scripts/import_docs.py ./samples/test100/

# 预期输出：
✅ 导入100文档，耗时: 2.3分钟
✅ 总块数: 1247
✅ 平均每文档: 12.5块
✅ 向量化成功率: 100%
✅ 数据库写入成功

# 手动验证
psql -h localhost -U dev -d ai_workflow -c "SELECT COUNT(*) FROM documents;"
# 应显示: 100

psql -h localhost -U dev -d ai_workflow -c "SELECT COUNT(*) FROM document_chunks;"
# 应显示: 1247
```

### 8.3 RAG验收（Day 12结束）
```bash
# 运行RAG测试
python scripts/test_rag.py

# 预期输出：
测试问题: 20个
✅ 问题1: 什么是RAG? (正确)
✅ 问题2: pgvector是什么? (正确)
...
❌ 问题5: 复杂问题... (错误)

--- 评估结果 ---
准确率: 75.0% (15/20) ✅ 达标
平均延迟: 6.2秒
P95延迟: 8.7秒 ✅ 达标
内存峰值: 9.2GB ✅ 达标
```

### 8.4 最终决策检查表
```
Week 2 结束时回答以下问题：

技术可行性:
[ ] Mac本地能否流畅运行? (是/否)
[ ] 4项验收标准达成几项? (___/4)
[ ] 最大技术瓶颈是? ___________

成本可行性:
[ ] 实际开发耗时vs预估? (___天 vs 10天)
[ ] 遇到阻塞性问题数量? (___个)
[ ] 云GPU预计月成本? (¥____/月)

业务可行性:
[ ] 准确率能否满足业务需求? (是/否)
[ ] 响应速度用户能否接受? (是/否)
[ ] 需要多少人力继续开发? (___人)

决策:
[ ] 继续投入 → 进入Phase 2（云GPU验证）
[ ] 调整优化 → 针对___问题优化1周后重试
[ ] 暂停项目 → 原因：___________
```

---

## 9. 常见问题与故障排查

### 9.1 环境问题
**Q: Ollama模型下载慢**
```bash
# 使用代理
export https_proxy=http://127.0.0.1:7890
ollama pull qwen2.5:7b

# 或使用国内镜像（如果有）
OLLAMA_HOST=https://ollama.your-mirror.com ollama pull qwen2.5:7b
```

**Q: PostgreSQL连接失败**
```bash
# 检查容器状态
docker ps | grep postgres

# 查看日志
docker logs rag_postgres

# 重启容器
docker-compose restart postgres
```

**Q: 内存不足**
```bash
# 减少批处理大小
# 修改.env
MAX_BATCH_SIZE=20  # 从50降到20
CHUNK_SIZE=300     # 从500降到300
```

### 9.2 性能问题
**Q: 向量化太慢**
```python
# 使用GPU加速（如果有）
model = SentenceTransformer('all-MiniLM-L6-v2', device='mps')  # Mac M1/M2

# 或增加批处理
embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)
```

**Q: 查询超过10秒**
```sql
-- 检查索引是否生效
EXPLAIN ANALYZE
SELECT content, embedding <=> '[0.1, 0.2, ...]' AS similarity
FROM document_chunks
ORDER BY similarity
LIMIT 3;

-- 如果没有使用索引，重建索引
DROP INDEX idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 9.3 准确率问题
**Q: 准确率<70%**
```
可能原因:
1. 文档质量差（PDF扫描件、乱码）
2. 分块策略不合理（块太大/太小）
3. 检索不准（Top-K太小）
4. LLM提示词不清晰

改进措施:
1. 清洗测试文档，确保文本提取正确
2. 调整CHUNK_SIZE（尝试300/700）
3. 增加TOP_K（3→5）
4. 优化提示词模板
```

---

## 10. 提交规范

### 10.1 每日提交
```bash
# Day 1-2
git add infra/ scripts/setup_local.sh .env.example
git commit -m "feat: 环境搭建完成 - Day 2验收通过"

# Day 3-4
git add backend/main.py backend/config.py backend/requirements.txt
git commit -m "feat: FastAPI基础API - Day 4验收通过"

# Day 5-7
git add backend/services/ scripts/import_docs.py
git commit -m "feat: 向量化管道 - 1000文档8.5分钟"

# Day 8-10
git add backend/services/rag_engine.py backend/services/ollama_client.py
git commit -m "feat: RAG核心功能 - P95延迟7.2秒"

# Day 11-12
git add scripts/test_rag.py evaluation_results.json
git commit -m "test: Week2验收 - 准确率76%, 4/4达标"
```

### 10.2 Week 2 总结报告
创建 `reports/week1-2-summary.md`，包含：
- 4项验收结果（通过/失败）
- 关键指标数据
- 遇到的问题清单
- 下一步建议
- 决策建议

---

## 11. 成功标准总结

```
Week 2 结束时，必须能明确回答：

✅ 技术可行?
   → 4项验收≥3项通过

✅ 成本可控?
   → 实际耗时≤15天，云GPU成本明确

✅ 业务价值?
   → 准确率满足最低要求（70%）

✅ 继续投入?
   → 基于上述3个答案做决策
```

**如果全部✅ → 启动Phase 2（云GPU + Qdrant + 14B模型）**

---

## 附录：完整示例代码

### scripts/setup_local.sh
```bash
#!/bin/bash
set -e

echo "🚀 开始设置本地环境..."

# 1. 检查系统
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  非macOS系统，性能可能不同"
fi

if [[ "$(uname -m)" != "arm64" ]]; then
    echo "⚠️  非Apple Silicon，性能可能不同"
fi

# 2. 检查内存
TOTAL_MEM_GB=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
if [[ $TOTAL_MEM_GB -lt 16 ]]; then
    echo "❌ 内存不足: ${TOTAL_MEM_GB}GB < 16GB"
    exit 1
fi

# 3. 检查并安装依赖
echo "🔍 检查现有安装..."

# 检查PostgreSQL
if brew list | grep -q "postgresql"; then
    echo "✅ PostgreSQL已通过homebrew安装"
else
    echo "⚠️  PostgreSQL未安装，建议运行: brew install postgresql"
    exit 1
fi

# 检查Redis
if brew list | grep -q "redis"; then
    echo "✅ Redis已通过homebrew安装"
else
    echo "⚠️  Redis未安装，建议运行: brew install redis"
    exit 1
fi

# 检查Ollama
command -v ollama >/dev/null || { echo "❌ 未安装Ollama，建议运行: brew install ollama"; exit 1; }
echo "✅ Ollama已安装"

# 4. 启动本地服务
echo "▶️  启动本地服务..."

# 启动PostgreSQL
if brew services list | grep "postgresql" | grep -q "started"; then
    echo "✅ PostgreSQL已运行"
else
    echo "启动PostgreSQL..."
    brew services start postgresql
    sleep 2
fi

# 启动Redis
if brew services list | grep "redis" | grep -q "started"; then
    echo "✅ Redis已运行"
else
    echo "启动Redis..."
    brew services start redis
    sleep 2
fi

# 5. 初始化数据库
echo "🗄️  初始化数据库..."

# 检查数据库是否存在
if psql -lqt | cut -d \| -f 1 | grep -qw ai_workflow; then
    echo "✅ 数据库ai_workflow已存在"
else
    echo "创建数据库ai_workflow..."
    createdb ai_workflow
fi

# 启用pgvector扩展
echo "启用pgvector扩展..."
psql ai_workflow -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null

# 执行初始化SQL
if [ -f "infra/init.sql" ]; then
    echo "执行初始化SQL..."
    psql ai_workflow -f infra/init.sql
fi

# 6. 检查并下载模型
echo "📥 检查Ollama模型..."
if ollama list | grep -q "qwen2.5:7b"; then
    echo "✅ 模型qwen2.5:7b已下载"
else
    echo "下载Qwen2.5-7B（约5GB，需5-10分钟）..."
    ollama pull qwen2.5:7b
fi

# 7. 安装Python依赖
echo "🐍 安装Python依赖..."
pip install -q -r backend/requirements.txt

# 8. 创建.env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ 创建.env文件"
fi

echo ""
echo "✅ 环境搭建完成!"
echo ""
echo "验证命令:"
echo "  brew services list                 # 查看服务状态"
echo "  ollama list                        # 应显示qwen2.5:7b"
echo "  psql ai_workflow -c 'SELECT 1;'    # 应返回1"
echo "  redis-cli ping                     # 应返回PONG"
echo ""
echo "资源使用:"
echo "  本地服务模式: 节省约2-3GB内存（相比Docker）"
echo ""
echo "下一步:"
echo "  cd backend && python main.py       # 启动API服务"
```

### scripts/verify_env.sh
```bash
#!/bin/bash

echo "🔍 验证环境..."

# 检查PostgreSQL服务
if brew services list | grep "postgresql" | grep -q "started"; then
    echo "✅ PostgreSQL服务 - 运行中（brew services）"
else
    echo "❌ PostgreSQL服务 - 未运行"
    echo "   运行: brew services start postgresql"
    exit 1
fi

# 检查PostgreSQL连接
if psql ai_workflow -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ PostgreSQL连接 - 成功"
else
    echo "❌ PostgreSQL连接 - 失败"
    exit 1
fi

# 检查pgvector
if psql ai_workflow -c "SELECT * FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q "vector"; then
    echo "✅ pgvector扩展 - 已启用"
else
    echo "❌ pgvector扩展 - 未启用"
    echo "   运行: psql ai_workflow -c 'CREATE EXTENSION vector;'"
    exit 1
fi

# 检查Redis服务
if brew services list | grep "redis" | grep -q "started"; then
    echo "✅ Redis服务 - 运行中（brew services）"
else
    echo "❌ Redis服务 - 未运行"
    echo "   运行: brew services start redis"
    exit 1
fi

# 检查Redis连接
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis连接 - 成功"
else
    echo "❌ Redis连接 - 失败"
    exit 1
fi

# 检查Ollama
if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
    echo "✅ Ollama - 模型qwen2.5:7b已下载"
else
    echo "❌ Ollama - 模型未下载"
    echo "   运行: ollama pull qwen2.5:7b"
    exit 1
fi

# 检查Python包
if python -c "import fastapi, sentence_transformers, psycopg2, pgvector" 2>/dev/null; then
    echo "✅ Python依赖 - 已安装"
else
    echo "❌ Python依赖 - 未安装"
    echo "   运行: pip install -r backend/requirements.txt"
    exit 1
fi

echo ""
echo "✅ 所有验收通过!"
echo ""
echo "资源使用情况:"
echo "  本地服务模式: 比Docker节省约2-3GB内存"
```

---

**文档版本**: v2.2
**最后更新**: 2025-10-31
**预计工作量**: 2周（10工作日）
**目标**: 用数据回答"是否继续投入"的问题

**v2.2 更新内容**（基于 Qwen3 和 Gemini 反馈）：
- ✅ 修复 OllamaClient 硬编码模型名称问题
- ✅ 添加完整 requirements.txt 依赖列表
- ✅ 添加内存监控函数实现（get_memory_usage）
- ✅ 添加测试问题集格式定义
- ✅ 添加基础错误处理示例
- ✅ 澄清 setup_local.sh 的自动化脚本角色
- ✅ 资源优化：优先使用homebrew本地服务，节省2-3GB内存
