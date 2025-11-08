# 代码执行与文档处理系统实现总结

## 概述

本文档总结了Industry AI Flow项目中代码执行和文档处理系统的实现。这两个关键模块为RAG系统提供了强大的数据分析和文档预处理能力。

## 系统架构

```
Industry AI Flow
├── 代码执行系统 (Code Execution)
│   ├── Docker沙箱 (安全隔离)
│   ├── 代码验证器 (安全检查)
│   └── LangChain工具 (Agent集成)
│
└── 文档处理系统 (Document Processing)
    ├── OCR处理器 (PaddleOCR + 百度API)
    ├── 文档提取器 (多格式支持)
    └── LangChain工具 (Agent集成)
```

---

## 一、代码执行系统

### 1.1 核心组件

#### Docker沙箱 (`backend/services/code_executor/docker_executor.py`)

**功能**: 在隔离的Docker容器中安全执行Python代码

**关键特性**:
- ✅ **网络隔离**: 默认禁用网络访问
- ✅ **资源限制**: CPU (50%), 内存 (512MB), 超时 (60s)
- ✅ **非root用户**: UID 1000执行,防止权限提升
- ✅ **文件系统隔离**: 仅/workspace可写
- ✅ **自动清理**: 容器执行后自动删除

**Docker镜像** (`docker/data-analysis/Dockerfile`):
```dockerfile
FROM python:3.12-slim

# 预装数据分析库
RUN pip install pandas numpy scipy scikit-learn \
    xgboost lightgbm matplotlib seaborn plotly \
    openpyxl psycopg2-binary

# 非root用户
USER sandbox (UID 1000)
```

**核心方法**:
```python
class DockerExecutor:
    def execute(code: str, input_files: dict) -> ExecutionResult
    def execute_code(code: str, data_files: list, timeout: int) -> dict  # 兼容接口
    def _validate_code(code: str) -> list[str]  # 安全验证
```

#### 代码验证器 (`backend/services/code_executor/validator.py`)

**功能**: 执行前进行安全检查

**验证规则**:
1. **黑名单检查**: 禁止导入os, subprocess, sys, socket等危险模块
2. **白名单模式**: 仅允许pandas, numpy, sklearn等数据分析库
3. **模式匹配**: 检测`__import__`, `eval`, `exec`等危险调用
4. **语法检查**: 使用AST解析验证Python语法
5. **循环检测**: 检测潜在的无限循环(`while True`, 大范围range)

**示例**:
```python
from backend.services.code_executor.validator import validate_code

result = validate_code("import pandas as pd\nprint('OK')")
# ✅ result.is_valid = True

result = validate_code("import os\nos.system('ls')")
# ❌ result.is_valid = False, error = "Blacklisted import: os"
```

#### LangChain工具 (`backend/tools/code_execution.py`)

**工具列表**:

1. **`code_execution_tool`** - 执行Python代码
```python
result = code_execution_tool.invoke({
    "code": "import pandas as pd\nprint(pd.__version__)",
    "timeout": 60
})
# → {"success": True, "stdout": "2.1.0", "execution_time": 0.5}
```

2. **`code_validation_tool`** - 验证代码安全性
```python
result = code_validation_tool.invoke({
    "code": "import numpy as np"
})
# → {"valid": True, "syntax_errors": [], "security_errors": []}
```

3. **`get_execution_environment_info`** - 获取环境信息
```python
info = get_execution_environment_info.invoke({})
# → {"docker_available": True, "resource_limits": {...}, "available_libraries": [...]}
```

### 1.2 使用示例

#### 基础数据分析
```python
code = """
import pandas as pd
import numpy as np

data = pd.DataFrame({
    'sales': [100, 200, 150, 300],
    'cost': [60, 120, 90, 180]
})

data['profit'] = data['sales'] - data['cost']
print(data.describe())
"""

result = code_execution_tool.invoke({"code": code})
print(result['stdout'])
```

#### 数据可视化
```python
code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.savefig('output.png', dpi=300)
print("Plot saved")
"""

result = code_execution_tool.invoke({"code": code})
# result['visualizations'] = ['output.png']
# result['output_files'] = {'output.png': <binary data>}
```

#### 机器学习模型
```python
code = """
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import numpy as np

X = np.random.randn(100, 3)
y = X @ np.array([2, -1, 0.5]) + np.random.randn(100) * 0.1

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = LinearRegression()
model.fit(X_train, y_train)
score = model.score(X_test, y_test)

print(f"R² Score: {score:.4f}")
"""

result = code_execution_tool.invoke({"code": code, "timeout": 60})
```

### 1.3 安全特性总结

| 特性 | 实现方式 | 保护级别 |
|------|----------|----------|
| 代码验证 | AST解析 + 黑名单 | 高 |
| 网络隔离 | Docker `network_disabled=True` | 高 |
| 资源限制 | Docker `mem_limit`, `cpu_quota` | 中 |
| 文件系统 | 临时目录 + 自动清理 | 中 |
| 执行超时 | Docker `wait(timeout)` | 高 |
| 用户权限 | 非root (UID 1000) | 高 |

---

## 二、文档处理系统

### 2.1 核心组件

#### OCR处理器 (`backend/services/document_processing/ocr_processor.py`)

**功能**: 从图像中提取文字,支持PaddleOCR 3.3.1 (PP-OCRv5)和百度API

**核心特性 (PaddleOCR 3.3.1 / 2025-10-29)**:
- ✅ **PP-OCRv5全场景识别**: 单模型支持5种文字类型 (简体/繁体/英文/日文/拼音)
- ✅ **精度大幅提升**: 识别精度提升约13个百分点,英文场景再提升约11%
- ✅ **手写体改进**: 复杂手写体识别能力增强
- ✅ **MPS加速**: Apple Silicon M系列芯片GPU加速 (2-5x性能提升,M1 Max可达4.7x)
- ✅ **API降级**: 失败时自动切换到百度OCR API
- ✅ **批量处理**: 支持批量图像OCR

**版本要求**:
- PaddlePaddle >= 2.6.0 (MPS支持)
- PaddleOCR >= 3.3.0
- NumPy < 2.0 (兼容性)

**初始化流程**:
```python
from backend.services.document_processing.ocr_processor import OCRProcessor

processor = OCRProcessor(
    use_local=True,        # 使用本地PaddleOCR 3.3.1
    use_api_fallback=True, # API备份
    lang="ch",             # PP-OCRv5混合语言 (简/繁/英/日/拼音)
    use_gpu=True,          # MPS/CUDA加速
    ocr_version="PP-OCRv5" # 使用最新版本
)
```

**核心方法**:
```python
class OCRProcessor:
    def process(image_path: Path) -> OCRResult
    def batch_process(image_paths: list) -> list[OCRResult]
    def _init_local_ocr() -> PaddleOCR  # 本地OCR初始化
    def _init_api_client() -> AipOcr    # API客户端初始化
```

**OCRResult数据结构**:
```python
@dataclass
class OCRResult:
    text: str              # 提取的文本
    confidence: float      # 平均置信度 (0-1)
    boxes: list           # 文本框坐标
    method: str           # 使用的方法 (local/api)
    language: str         # 语言
```

#### 文档提取器 (`backend/services/document_processing/document_extractor.py`)

**功能**: 从多种文档格式提取文本内容

**支持格式**:

| 格式 | 扩展名 | 提取方法 | 库依赖 |
|------|--------|----------|--------|
| PDF | .pdf | PyPDF2 + OCR | PyPDF2, PaddleOCR |
| Word | .docx, .doc | python-docx | python-docx |
| Excel | .xlsx, .xls | openpyxl | openpyxl, xlrd |
| 文本 | .txt, .md | 文件读取 | 无 |
| 图像 | .png, .jpg, .jpeg, .bmp, .tiff | OCR | PaddleOCR |

**核心方法**:
```python
class DocumentExtractor:
    def extract(file_path: Path) -> DocumentContent
    def _extract_pdf(file_path: Path) -> DocumentContent
    def _extract_word(file_path: Path) -> DocumentContent
    def _extract_excel(file_path: Path) -> DocumentContent
    def _extract_text(file_path: Path) -> DocumentContent
    def _extract_image(file_path: Path) -> DocumentContent
```

**DocumentContent数据结构**:
```python
@dataclass
class DocumentContent:
    text: str         # 提取的文本
    metadata: dict    # 元数据 (页数, 作者, etc.)
    method: str       # 提取方法
    file_type: str    # 文件类型
```

#### LangChain工具 (`backend/tools/document_processing.py`)

**工具列表**:

1. **`extract_document_text`** - 提取文档文本
```python
result = extract_document_text.invoke({
    "file_path": "/path/to/document.pdf",
    "use_ocr": True
})
# → {"success": True, "text": "...", "file_type": "pdf", "method": "pypdf2"}
```

2. **`ocr_image`** - OCR图像识别
```python
result = ocr_image.invoke({
    "image_path": "/path/to/image.png",
    "language": "ch"
})
# → {"success": True, "text": "...", "confidence": 0.95, "method": "local"}
```

3. **`batch_extract_documents`** - 批量文档提取
```python
result = batch_extract_documents.invoke({
    "file_paths": ["/doc1.pdf", "/doc2.docx", "/doc3.xlsx"],
    "use_ocr": True
})
# → {"success": True, "total": 3, "succeeded": 3, "failed": 0, "results": [...]}
```

### 2.2 使用示例

#### PDF文档处理
```python
from backend.services.document_processing import process_document

# 提取PDF文本
content = process_document("/path/to/report.pdf", use_ocr=True)

print(f"文本内容: {content.text[:200]}...")
print(f"页数: {content.metadata['num_pages']}")
print(f"作者: {content.metadata['author']}")
```

#### OCR图像识别
```python
from backend.services.document_processing.ocr_processor import OCRProcessor

processor = OCRProcessor(lang="ch")
result = processor.process("/path/to/chinese_doc.png")

print(f"识别文字: {result.text}")
print(f"置信度: {result.confidence:.2%}")
print(f"方法: {result.method}")  # local 或 api
```

#### Word文档提取
```python
content = process_document("/path/to/report.docx")

print(f"段落数: {content.metadata['num_paragraphs']}")
print(f"表格数: {content.metadata['num_tables']}")
print(content.text)
```

#### Excel数据提取
```python
content = process_document("/path/to/data.xlsx")

print(f"工作表: {content.metadata['sheet_names']}")
print(content.text)  # 所有工作表的数据,按表格格式显示
```

### 2.3 OCR配置

#### 环境变量配置 (可选 - 百度API备份)
```bash
# .env 文件
BAIDU_OCR_APP_ID=your_app_id
BAIDU_OCR_API_KEY=your_api_key
BAIDU_OCR_SECRET_KEY=your_secret_key
```

#### 本地PaddleOCR 3.3.1安装 (推荐配置)
```bash
# 1. 安装PaddlePaddle 2.6.0+ (支持MPS)
pip install paddlepaddle>=2.6.0

# 2. 安装PaddleOCR 3.3.0+ (PP-OCRv5)
pip install paddleocr>=3.3.0

# 3. 确保NumPy版本兼容
pip install 'numpy>=1.26.4,<2.0'

# 4. Apple Silicon MPS加速支持 (可选)
pip install paddle-custom-mps

# 5. 验证MPS设备
python -c "import paddle; print(paddle.device.get_all_custom_device_type())"
# 预期输出: ['mps'] (如果MPS可用)

# 6. 百度AI SDK (可选 - API备份)
pip install baidu-aip>=4.16.0
```

**性能对比** (Apple Silicon):
- CPU模式: 基准性能
- MPS加速: 2-5x性能提升
- M1 Max: 某些场景可达4.7x加速

---

## 三、集成测试

### 3.1 代码执行测试

**运行测试**:
```bash
python test_code_execution.py
```

**测试覆盖**:
- ✅ 环境检测 - Docker可用性, 资源配置
- ✅ 代码验证 - 语法检查, 安全检查, 黑名单过滤
- ✅ 基础执行 - pandas数据分析
- ✅ 数据可视化 - matplotlib图表生成
- ✅ LangChain工具 - 工具调用和集成
- ✅ 机器学习 - scikit-learn模型训练

### 3.2 文档处理测试

**运行测试**:
```bash
# 基础文档处理测试
python test_document_processing.py

# PaddleOCR 3.3.1专项测试
python test_paddleocr_v5.py
```

**test_document_processing.py 测试覆盖**:
- ✅ OCR可用性 - PaddleOCR初始化
- ✅ 文档提取器 - 支持格式检查
- ✅ 文本提取 - .txt文件处理
- ✅ LangChain工具 - 工具调用
- ✅ 批量处理 - 多文件并行处理
- ⏭️  OCR集成 - 图像识别 (可选,需要真实图像)

**test_paddleocr_v5.py 测试覆盖**:
- ✅ PaddlePaddle版本检查 (>=2.6.0)
- ✅ Apple MPS设备检测
- ✅ PaddleOCR 3.3.1版本验证
- ✅ NumPy兼容性检查 (<2.0)
- ✅ OCR处理器初始化 (PP-OCRv5)
- 📊 性能优化建议

---

## 四、完整工作流示例

### 文档 → RAG → 代码分析 完整流程

```python
from backend.tools.document_processing import extract_document_text
from backend.tools.retrieval import hybrid_retrieval_tool
from backend.tools.code_execution import code_execution_tool

# 步骤1: 文档预处理 (OCR + 提取)
doc_result = extract_document_text.invoke({
    "file_path": "/data/sales_report.pdf",
    "use_ocr": True
})

# 步骤2: 存入向量数据库
# (假设已存储,使用现有RAG系统)

# 步骤3: 混合检索相关信息
query = "2024年第一季度销售数据"
docs = hybrid_retrieval_tool.invoke({
    "query": query,
    "top_k": 5
})

# 步骤4: 基于检索结果生成数据分析代码
analysis_code = """
import pandas as pd
import matplotlib.pyplot as plt

# 提取销售数据 (模拟)
data = pd.DataFrame({
    '月份': ['1月', '2月', '3月'],
    '销售额': [120000, 150000, 180000],
    '利润': [30000, 40000, 50000]
})

# 数据分析
print("=== 2024 Q1 销售分析 ===")
print(data)
print(f"\\n总销售额: {data['销售额'].sum():,} 元")
print(f"总利润: {data['利润'].sum():,} 元")
print(f"利润率: {data['利润'].sum() / data['销售额'].sum() * 100:.2f}%")

# 可视化
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# 销售额趋势
ax1.plot(data['月份'], data['销售额'], marker='o', linewidth=2)
ax1.set_title('销售额趋势')
ax1.set_ylabel('销售额 (元)')
ax1.grid(True, alpha=0.3)

# 利润趋势
ax2.plot(data['月份'], data['利润'], marker='s', color='green', linewidth=2)
ax2.set_title('利润趋势')
ax2.set_ylabel('利润 (元)')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('sales_analysis.png', dpi=150)
print("\\n✅ 分析图表已保存: sales_analysis.png")
"""

# 步骤5: 在Docker沙箱中执行分析代码
exec_result = code_execution_tool.invoke({
    "code": analysis_code,
    "timeout": 60
})

if exec_result['success']:
    print("=== 分析结果 ===")
    print(exec_result['stdout'])
    print(f"\n生成图表: {exec_result['visualizations']}")
else:
    print(f"执行失败: {exec_result['error']}")
```

---

## 五、架构优势

### 5.1 安全性
- ✅ **多层防护**: 代码验证 + Docker隔离 + 资源限制
- ✅ **沙箱执行**: 无法访问宿主机系统
- ✅ **自动清理**: 临时文件和容器自动删除

### 5.2 可扩展性
- ✅ **模块化设计**: 独立的服务和工具层
- ✅ **LangChain集成**: 轻松接入Agent工作流
- ✅ **多格式支持**: 易于添加新文档格式

### 5.3 性能优化
- ✅ **设备自适应**: MPS/CUDA/CPU自动选择
- ✅ **本地优先**: 本地OCR + API备份策略
- ✅ **批量处理**: 支持并行文档处理

### 5.4 用户体验
- ✅ **零配置启动**: Docker自动构建镜像
- ✅ **清晰反馈**: 详细的错误信息和执行状态
- ✅ **灵活控制**: 超时、资源限制可配置

---

## 六、部署指南

### 6.1 依赖安装

```bash
# 安装Python依赖
pip install -r requirements.txt

# 关键依赖:
# - docker>=6.1.0           (Docker SDK)
# - paddlepaddle>=2.5.0     (深度学习框架)
# - paddleocr>=2.7.0        (OCR引擎)
# - PyPDF2>=3.0.1           (PDF处理)
# - python-docx>=1.1.0      (Word文档)
# - openpyxl>=3.1.2         (Excel文件)
```

### 6.2 Docker环境

```bash
# 确保Docker运行
docker info

# 构建数据分析镜像 (首次运行时自动构建)
# 镜像名称: industry-ai-flow/data-analysis:latest
```

### 6.3 OCR配置 (可选)

```bash
# 配置百度OCR API (可选 - 作为备份)
export BAIDU_OCR_APP_ID=your_app_id
export BAIDU_OCR_API_KEY=your_api_key
export BAIDU_OCR_SECRET_KEY=your_secret_key
```

### 6.4 测试验证

```bash
# 测试代码执行
python test_code_execution.py

# 测试文档处理
python test_document_processing.py

# 预期输出:
# ✅ 所有测试通过 (除OCR集成可选)
```

---

## 七、下一步工作

### 7.1 优化方向
- [ ] **性能优化**: Docker镜像预热,减少首次启动时间
- [ ] **OCR增强**: 支持更多语言,表格识别优化
- [ ] **缓存机制**: 代码执行结果缓存,避免重复计算
- [ ] **监控告警**: 资源使用监控,异常检测

### 7.2 功能扩展
- [ ] **Orchestrator Agent**: 智能任务路由 (RAG + Code + OCR)
- [ ] **流式输出**: 代码执行进度实时反馈
- [ ] **多语言支持**: 支持R, Julia等数据分析语言
- [ ] **协同编辑**: 多轮对话式代码优化

### 7.3 集成目标
- [ ] **完整RAG Pipeline**: 文档预处理 → 向量化 → 检索 → 分析
- [ ] **Agent工作流**: 自动决策使用OCR还是代码执行
- [ ] **Web UI**: Streamlit仪表板展示分析结果

---

## 八、文件清单

### 代码执行系统
```
docker/data-analysis/Dockerfile                     # Docker镜像定义
backend/services/code_executor/
    ├── __init__.py                                 # 包初始化
    ├── docker_executor.py                          # Docker执行器
    └── validator.py                                # 代码验证器
backend/tools/code_execution.py                     # LangChain工具
test_code_execution.py                              # 测试脚本
```

### 文档处理系统
```
backend/services/document_processing/
    ├── __init__.py                                 # 包初始化
    ├── ocr_processor.py                            # OCR处理器
    └── document_extractor.py                       # 文档提取器
backend/tools/document_processing.py                # LangChain工具
test_document_processing.py                         # 测试脚本
```

### 文档
```
CODE_EXECUTION_DESIGN.md                           # 设计文档
CODE_EXECUTION_AND_DOCUMENT_PROCESSING_SUMMARY.md  # 本文档
requirements.txt                                    # 依赖清单
```

---

## 九、总结

我们成功实现了两个关键系统:

1. **代码执行系统**: 提供安全、隔离的Python代码执行环境,支持高级数据分析、可视化和机器学习任务。

2. **文档处理系统**: 支持多种文档格式的文本提取,集成了本地PaddleOCR和百度API,实现了智能文档预处理。

这两个系统与现有的LangChain 1.0 RAG系统完美集成,形成了完整的文档处理 → 知识检索 → 数据分析工作流,为Industry AI Flow项目提供了强大的AI驱动数据分析能力。

**核心价值**:
- 🔒 **安全可靠**: 多层安全防护,生产环境可用
- ⚡ **性能优化**: MPS/CUDA加速,本地优先策略
- 🔧 **易于集成**: LangChain 1.0工具,即插即用
- 📊 **功能完整**: 覆盖文档处理到数据分析全流程

---

**生成时间**: 2025-11-07
**版本**: v1.0
**维护者**: Claude Code AI Assistant
