# 代码执行与文档处理系统设计

## 🎯 整体架构

```
用户上传文档/数据
    ↓
文档预处理 Pipeline
    ├── OCR (PaddleOCR) - 图片/PDF 文字提取
    ├── 表格解析 (Pandas) - Excel/CSV 处理
    └── 文档分块 (LangChain) - 语义分块
    ↓
向量化 + 存储 (VectorDB)
    ↓
Multi-Agent 协作系统
    ├── RAG Agent (知识问答)
    ├── Code Execution Agent (数据分析)
    └── Orchestrator Agent (任务路由)
    ↓
结果返回（文本 + 可视化 + 代码）
```

---

## 📦 模块设计

### 1. 文档预处理 Pipeline

#### 1.1 OCR 集成方案对比

| 方案 | 优势 | 劣势 | 推荐场景 |
|------|------|------|----------|
| **本地 PaddleOCR** | 免费、速度快、隐私安全 | 需要模型下载、占用存储 | 开发测试、隐私敏感场景 |
| **百度 OCR API** | 无需本地部署、精度高 | 付费、网络依赖 | 生产环境、高精度需求 |
| **混合方案** | 本地优先、API 降级 | 实现复杂 | 最佳实践 |

**推荐**: **混合方案** - 本地 PaddleOCR 作为主力，API 作为备用

#### 1.2 文档预处理流程

```python
文档上传
    ↓
文件类型检测
    ├── PDF/图片 → OCR 提取文字
    ├── Excel/CSV → Pandas 读取
    ├── Word/Markdown → 直接提取
    └── 扫描件 → OCR + 表格识别
    ↓
文本清洗和规范化
    ↓
语义分块 (LangChain)
    ↓
向量化 (nomic-embed)
    ↓
存入 VectorDB
```

#### 1.3 LangChain 1.0 集成

使用 LangChain 的 `DocumentLoader` + `TextSplitter`:

```python
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 文档加载
loader = UnstructuredFileLoader("file.pdf", mode="elements", strategy="ocr_only")
documents = loader.load()

# 智能分块
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", ".", " "]
)
chunks = splitter.split_documents(documents)
```

---

### 2. Code Execution Agent

#### 2.1 Docker 沙箱环境设计

**Dockerfile** (预装数据分析库):
```dockerfile
FROM python:3.12-slim

# 安装数据分析库
RUN pip install --no-cache-dir \
    pandas==2.1.0 \
    numpy==1.26.0 \
    matplotlib==3.8.0 \
    seaborn==0.13.0 \
    plotly==5.17.0 \
    scikit-learn==1.5.0 \
    xgboost==2.0.0 \
    lightgbm==4.3.0 \
    scipy==1.11.0

# 工作目录
WORKDIR /workspace
```

**安全机制**:
1. 网络隔离 (`--network=none`)
2. 资源限制 (`--memory="512m" --cpus="1.0"`)
3. 只读挂载 (`--read-only`)
4. 超时控制 (30秒)
5. 文件系统限制 (仅 `/workspace` 可写)

#### 2.2 数据传递方案

**方案 A: 文件映射** (推荐用于快速任务)
```python
# 宿主机: /tmp/code_exec/{session_id}/
#   ├── input/data.csv
#   ├── code.py
#   └── output/

docker.containers.run(
    image="data-analysis:latest",
    command="python /workspace/code.py",
    volumes={
        f"/tmp/code_exec/{session_id}": {
            "bind": "/workspace",
            "mode": "rw"
        }
    },
    remove=True
)
```

**方案 B: 数据库中转** (推荐用于安全场景)
```python
# 1. 导入临时表
df.to_sql(f"temp_{session_id}", engine, if_exists="replace")

# 2. Docker 内通过网络访问
code = f"""
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('{DATABASE_URL}')
df = pd.read_sql_table('temp_{session_id}', engine)
# ... 分析代码 ...
"""

# 3. 执行后删除临时表
```

#### 2.3 代码执行流程

```python
LLM 生成代码
    ↓
代码安全检查 (禁止 os, subprocess 等)
    ↓
写入临时文件
    ↓
Docker 容器执行
    ├── 成功 → 提取结果 (文本 + 图片)
    └── 失败 → 提取错误日志
    ↓
Middleware 监控
    ├── 超时 → 终止容器
    ├── 错误 → LLM 自动修复代码
    └── 成功 → 返回结果
    ↓
结果可视化展示
```

#### 2.4 LangChain 1.0 Agent 实现

```python
from langchain.agents import create_agent
from langchain_core.tools import tool

@tool
def execute_python_code(
    code: Annotated[str, "Python 代码"],
    data_path: Annotated[str, "数据文件路径"],
    timeout: Annotated[int, "超时时间(秒)"] = 30
) -> dict:
    """
    在 Docker 沙箱中执行 Python 代码

    返回:
        {
            "success": bool,
            "output": str,
            "images": list[str],  # Base64 编码的图片
            "error": str
        }
    """
    # 实现见下方
    pass

# 创建 Code Execution Agent
code_agent = create_agent(
    model=llm,
    tools=[execute_python_code],
    system_prompt="""你是一个数据分析专家。

    工作流程:
    1. 分析用户的数据分析需求
    2. 生成 Python 代码 (pandas, matplotlib, seaborn, sklearn)
    3. 调用 execute_python_code 工具执行代码
    4. 如果执行失败,根据错误信息修正代码并重试
    5. 将分析结果和可视化图表返回给用户

    注意:
    - 代码中不能使用 os, subprocess, requests 等危险模块
    - 可视化图表保存为 PNG 文件
    - 数据分析要全面,包括描述性统计、相关性分析、可视化等
    """
)
```

#### 2.5 自动代码修复机制 (Middleware)

```python
from langchain_core.runnables import RunnableConfig

def code_execution_middleware(func):
    """Middleware: 自动重试和错误修复"""
    def wrapper(input, config: RunnableConfig):
        max_retries = 3

        for attempt in range(max_retries):
            result = func(input, config)

            # 检查执行结果
            if result.get("success"):
                return result

            # 提取错误信息
            error_msg = result.get("error", "Unknown error")

            # 将错误注入上下文,让 LLM 修正
            input["error_context"] = {
                "attempt": attempt + 1,
                "error": error_msg,
                "previous_code": input.get("code")
            }

            print(f"⚠️  执行失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")

        return {"success": False, "error": "Max retries exceeded"}

    return wrapper
```

---

### 3. 文档预处理模块

#### 3.1 PaddleOCR 集成

**本地部署方案**:
```python
from paddleocr import PaddleOCR

class OCRProcessor:
    def __init__(self):
        # 使用 MPS/GPU 加速
        device = device_manager.get_sentence_transformer_device()

        self.ocr = PaddleOCR(
            use_angle_cls=True,  # 文字方向检测
            lang="ch",           # 中文 + 英文
            use_gpu=True if device == "cuda" else False,
            use_mps=True if device == "mps" else False,
            show_log=False
        )

    def extract_text(self, image_path: str) -> str:
        """提取图片中的文字"""
        result = self.ocr.ocr(image_path, cls=True)

        # 按位置排序并拼接文字
        texts = []
        for line in result[0]:
            text = line[1][0]  # 提取文字
            conf = line[1][1]  # 置信度

            if conf > 0.8:  # 置信度过滤
                texts.append(text)

        return "\n".join(texts)
```

**API 方案** (作为备用):
```python
import requests

class BaiduOCRAPI:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = self._get_access_token()

    def extract_text(self, image_path: str) -> str:
        """调用百度 OCR API"""
        url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"

        with open(image_path, "rb") as f:
            image = base64.b64encode(f.read()).decode()

        response = requests.post(
            url,
            params={"access_token": self.access_token},
            data={"image": image}
        )

        result = response.json()
        texts = [item["words"] for item in result.get("words_result", [])]

        return "\n".join(texts)
```

**混合方案**:
```python
class HybridOCR:
    def __init__(self):
        self.local_ocr = OCRProcessor()
        self.api_ocr = BaiduOCRAPI(api_key, secret_key) if has_api_key else None

    def extract_text(self, image_path: str) -> str:
        try:
            # 优先使用本地 OCR
            return self.local_ocr.extract_text(image_path)
        except Exception as e:
            logger.warning(f"本地 OCR 失败: {e}, 尝试使用 API")

            if self.api_ocr:
                return self.api_ocr.extract_text(image_path)
            else:
                raise Exception("OCR 失败且未配置 API")
```

#### 3.2 文档处理 Tool

```python
@tool
def process_document(
    file_path: Annotated[str, "文档路径"],
    file_type: Annotated[str, "文件类型: pdf/image/excel/csv"]
) -> dict:
    """
    处理上传的文档,提取文字并存入向量数据库

    返回:
        {
            "doc_id": str,
            "chunk_count": int,
            "text_preview": str
        }
    """
    if file_type in ["pdf", "image"]:
        # OCR 提取
        text = ocr.extract_text(file_path)
    elif file_type in ["excel", "csv"]:
        # Pandas 读取
        df = pd.read_excel(file_path) if file_type == "excel" else pd.read_csv(file_path)
        text = df.to_string()
    else:
        # 直接读取
        with open(file_path) as f:
            text = f.read()

    # 分块
    chunks = text_splitter.split_text(text)

    # 向量化并存储
    embeddings = embed_texts(chunks)
    doc_id = vectorstore.store_document_with_chunks(
        filename=os.path.basename(file_path),
        filepath=file_path,
        chunks=chunks,
        embeddings=embeddings
    )

    return {
        "doc_id": doc_id,
        "chunk_count": len(chunks),
        "text_preview": text[:500]
    }
```

---

### 4. Multi-Agent 协作

#### 4.1 Orchestrator Agent (任务路由)

```python
orchestrator_agent = create_agent(
    model=llm,
    tools=[
        process_document,      # 文档处理
        hybrid_retrieval_tool, # RAG 检索
        execute_python_code,   # 代码执行
    ],
    system_prompt="""你是一个智能任务路由器。

    根据用户请求,决定调用哪些工具:

    1. 文档上传/处理 → process_document
    2. 知识问答 → hybrid_retrieval_tool
    3. 数据分析 → execute_python_code

    可以组合多个工具:
    - 先 process_document 处理文档,再 hybrid_retrieval_tool 检索
    - 先 process_document 读取数据,再 execute_python_code 分析

    示例:
    用户: "帮我分析这个 Excel 文件,生成销售趋势图"
    → 1. process_document(file.xlsx)
    → 2. execute_python_code(生成 pandas 代码分析数据)
    """
)
```

#### 4.2 工作流示例

**场景 1: 纯 RAG 问答**
```
用户: "什么是 LangChain 1.0?"
    ↓
Orchestrator → RAG Agent
    ↓
hybrid_retrieval_tool → 检索文档
    ↓
LLM 生成答案
```

**场景 2: 数据分析**
```
用户: "分析这个销售数据,生成可视化报告"
    ↓
Orchestrator → Code Execution Agent
    ↓
process_document → 读取 Excel
    ↓
execute_python_code → 生成分析代码
    ↓
Docker 执行 → 返回图表
```

**场景 3: 混合任务**
```
用户: "根据文档中的销售策略,分析实际销售数据是否符合预期"
    ↓
Orchestrator → RAG Agent + Code Execution Agent
    ↓
1. hybrid_retrieval_tool → 检索销售策略文档
2. execute_python_code → 分析销售数据
    ↓
LLM 综合两者生成报告
```

---

## 🧪 测试策略

### 1. 单元测试

**OCR 测试**:
```python
def test_ocr_extraction():
    ocr = OCRProcessor()
    text = ocr.extract_text("test_image.png")
    assert "预期文字" in text
    assert len(text) > 100
```

**代码执行测试**:
```python
def test_code_execution():
    code = """
import pandas as pd
df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})
print(df.describe())
"""
    result = execute_python_code(code, data_path=None)
    assert result["success"] == True
    assert "mean" in result["output"]
```

### 2. 集成测试

**端到端测试**:
```python
def test_end_to_end_data_analysis():
    # 1. 上传文档
    result1 = process_document("sales.xlsx", "excel")
    assert result1["chunk_count"] > 0

    # 2. 数据分析
    result2 = orchestrator_agent.invoke({
        "messages": [HumanMessage(content="分析销售数据并生成趋势图")]
    })

    # 3. 验证输出
    assert "图表" in result2["messages"][-1].content
```

### 3. 性能测试

```python
def test_code_execution_timeout():
    # 测试超时控制
    code = "import time; time.sleep(100)"
    result = execute_python_code(code, timeout=5)
    assert result["success"] == False
    assert "timeout" in result["error"].lower()
```

---

## 📊 性能优化

### 1. OCR 优化
- ✅ 使用 MPS/GPU 加速
- ✅ 批量处理多张图片
- ✅ 缓存 OCR 结果
- ✅ 并行处理 PDF 页面

### 2. Docker 优化
- ✅ 预构建镜像,避免重复拉取
- ✅ 容器池复用
- ✅ 资源限制 (CPU/内存)
- ✅ 网络隔离

### 3. 数据传递优化
- ✅ 小数据 (<10MB): 文件映射
- ✅ 大数据 (>10MB): 数据库中转
- ✅ 结果压缩 (图片 Base64)

---

## 🔐 安全考虑

### 1. 代码沙箱
- ❌ 禁止: `os`, `subprocess`, `eval`, `exec`, `__import__`
- ❌ 禁止: 网络访问 (requests, urllib, socket)
- ❌ 禁止: 文件系统操作 (除 `/workspace`)
- ✅ 允许: pandas, numpy, matplotlib, sklearn

### 2. 输入验证
```python
def validate_code(code: str) -> bool:
    """验证代码安全性"""
    forbidden = [
        "os.", "subprocess", "eval(", "exec(",
        "__import__", "open(", "requests.", "urllib"
    ]

    for pattern in forbidden:
        if pattern in code:
            raise ValueError(f"禁止使用: {pattern}")

    return True
```

### 3. 资源限制
- CPU: 1 核心
- 内存: 512MB
- 超时: 30 秒
- 磁盘: 100MB

---

## 📁 目录结构

```
Industry-AI-Flow/
├── backend/
│   ├── agents/
│   │   ├── code_agent.py           # Code Execution Agent
│   │   ├── document_agent.py       # Document Processing Agent
│   │   └── orchestrator_agent.py   # 任务路由 Agent
│   ├── services/
│   │   ├── ocr/
│   │   │   ├── paddle_ocr.py       # PaddleOCR 本地
│   │   │   ├── baidu_ocr_api.py    # 百度 API
│   │   │   └── hybrid_ocr.py       # 混合方案
│   │   ├── code_executor/
│   │   │   ├── docker_executor.py  # Docker 执行器
│   │   │   ├── validator.py        # 代码验证
│   │   │   └── result_parser.py    # 结果解析
│   │   └── document_processor/
│   │       ├── pdf_processor.py    # PDF 处理
│   │       ├── excel_processor.py  # Excel 处理
│   │       └── text_splitter.py    # 文本分块
│   └── tools/
│       ├── code_execution.py       # 代码执行工具
│       └── document_processing.py  # 文档处理工具
├── docker/
│   └── data-analysis/
│       └── Dockerfile              # 数据分析镜像
└── tests/
    ├── test_ocr.py
    ├── test_code_execution.py
    └── test_orchestrator.py
```

---

**下一步实现顺序**:
1. ✅ 设计完成
2. ⏳ 实现 Docker 沙箱执行器
3. ⏳ 实现 PaddleOCR 集成
4. ⏳ 创建 Code Execution Agent
5. ⏳ 创建 Document Processing Agent
6. ⏳ 创建 Orchestrator Agent
7. ⏳ 端到端测试

---

**文档版本**: 1.0.0
**最后更新**: 2025-11-07
**维护者**: Claude Code (Anthropic)
