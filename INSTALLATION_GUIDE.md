# Industry AI Flow - 安装指南

## 快速开始

### 1. 基础环境

```bash
# Python版本
python3 --version  # 需要 Python 3.10+

# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
```

### 2. 核心依赖安装

```bash
# 安装主要依赖
pip install -r requirements.txt
```

### 3. PaddleOCR 3.3.1 安装 (文档处理系统)

```bash
# Step 1: 安装PaddlePaddle 2.6.0+ (支持MPS)
pip install paddlepaddle>=2.6.0

# Step 2: 安装PaddleOCR 3.3.0+ (PP-OCRv5)
pip install paddleocr>=3.3.0

# Step 3: NumPy版本兼容 (重要!)
pip install 'numpy>=1.26.4,<2.0'

# Step 4: Apple Silicon MPS加速 (可选,推荐)
pip install paddle-custom-mps
```

### 4. 验证安装

```bash
# 验证PaddleOCR
python3 test_paddleocr_v5.py

# 简化版测试 (不需要LangChain)
python3 test_ocr_simple.py

# 测试中文可视化图片识别
python3 test_ocr_chinese_viz.py
```

---

## 详细安装步骤

### 选项A: 完整安装 (推荐用于生产环境)

```bash
# 1. 克隆项目
git clone <repository-url>
cd Industry-AI-Flow

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 升级pip
pip install --upgrade pip

# 4. 安装所有依赖
pip install -r requirements.txt

# 5. 验证Docker (代码执行系统需要)
docker --version
docker info

# 6. 测试系统
python3 test_code_execution.py      # 代码执行系统
python3 test_document_processing.py # 文档处理系统
python3 test_paddleocr_v5.py        # PaddleOCR专项测试
```

### 选项B: 最小安装 (仅OCR测试)

```bash
# 仅安装PaddleOCR相关依赖
pip install paddlepaddle>=2.6.0
pip install paddleocr>=3.3.0
pip install 'numpy>=1.26.4,<2.0'
pip install pillow>=10.1.0

# 测试
python3 test_ocr_simple.py
```

---

## 平台特定说明

### macOS (Apple Silicon M1/M2/M3)

```bash
# 1. 基础安装
pip install paddlepaddle>=2.6.0
pip install paddleocr>=3.3.0
pip install 'numpy>=1.26.4,<2.0'

# 2. MPS加速支持
pip install paddle-custom-mps

# 3. 验证MPS设备
python3 -c "import paddle; print('MPS设备:', paddle.device.get_all_custom_device_type())"
# 预期输出: MPS设备: ['mps']

# 4. 性能对比
# CPU模式: 基准性能
# MPS模式: 2-5x加速 (M1 Max可达4.7x)
```

### Linux (NVIDIA GPU)

```bash
# CUDA版本PaddlePaddle
pip install paddlepaddle-gpu>=2.6.0

# 其他依赖同上
pip install paddleocr>=3.3.0
pip install 'numpy>=1.26.4,<2.0'

# 验证CUDA
python3 -c "import paddle; print('CUDA可用:', paddle.device.is_compiled_with_cuda())"
```

### Windows

```bash
# 基础安装
pip install paddlepaddle>=2.6.0
pip install paddleocr>=3.3.0
pip install "numpy>=1.26.4,<2.0"

# GPU版本 (如果有NVIDIA显卡)
pip install paddlepaddle-gpu>=2.6.0
```

---

## 常见问题

### Q1: NumPy版本冲突

**现象**:
```
NumPy 2.3.4 (建议<2.0)
```

**解决**:
```bash
pip uninstall numpy -y
pip install 'numpy>=1.26.4,<2.0'
```

### Q2: PaddleOCR初始化失败

**现象**:
```
No module named 'paddleocr'
```

**解决**:
```bash
pip install paddlepaddle>=2.6.0
pip install paddleocr>=3.3.0
```

### Q3: MPS设备未检测到

**现象**:
```
MPS设备: []
```

**解决**:
```bash
# 安装MPS支持
pip install paddle-custom-mps

# 验证
python3 -c "import paddle; print(paddle.device.get_all_custom_device_type())"
```

### Q4: Docker未安装 (代码执行系统)

**现象**:
```
Failed to connect to Docker daemon
```

**解决**:
```bash
# macOS
brew install --cask docker

# 启动Docker Desktop并验证
docker --version
docker info
```

### Q5: LangChain相关错误

**现象**:
```
No module named 'langchain_core'
```

**解决**:
```bash
# 安装LangChain 1.0
pip install langchain>=1.0.0
pip install langchain-core>=0.3.29
pip install langchain-community>=0.3.17
pip install langgraph>=0.2.0
```

---

## 可选组件

### 1. 百度OCR API (备份方案)

在 `.env` 文件中配置:
```bash
BAIDU_OCR_APP_ID=your_app_id
BAIDU_OCR_API_KEY=your_api_key
BAIDU_OCR_SECRET_KEY=your_secret_key
```

安装SDK:
```bash
pip install baidu-aip>=4.16.0
```

### 2. Streamlit Web UI

```bash
pip install streamlit>=1.28.0

# 运行
streamlit run streamlit_app.py
```

### 3. 开发工具

```bash
pip install pytest>=7.4.3
pip install pytest-asyncio>=0.21.0
pip install black>=23.11.0
pip install isort>=5.12.0
pip install flake8>=6.1.0
```

---

## 测试验证

### 系统完整性测试

```bash
# 1. 代码执行系统
python3 test_code_execution.py
# 预期: 6/6 通过

# 2. 文档处理系统
python3 test_document_processing.py
# 预期: 5/6 通过 (OCR集成可选)

# 3. PaddleOCR专项测试
python3 test_paddleocr_v5.py
# 预期: 5/5 通过

# 4. 中文图片OCR测试
python3 test_ocr_simple.py
# 测试chinese_visualization_output/目录下的图片
```

### 性能基准测试

```bash
# OCR性能测试
python3 test_ocr_simple.py

# 查看性能统计:
# - 平均耗时 (秒/张)
# - 平均置信度
# - 识别字符数
```

---

## 卸载

```bash
# 卸载虚拟环境
deactivate
rm -rf venv

# 或卸载特定包
pip uninstall paddlepaddle paddleocr -y
```

---

## 下一步

安装完成后:

1. **阅读文档**:
   - `QUICK_START_GUIDE.md` - 快速开始指南
   - `CODE_EXECUTION_AND_DOCUMENT_PROCESSING_SUMMARY.md` - 完整技术文档
   - `PADDLEOCR_V5_UPDATE.md` - PaddleOCR升级说明

2. **运行测试**:
   - 验证所有功能正常工作
   - 检查性能指标

3. **开始使用**:
   - 集成到您的LangChain Agent
   - 处理文档和执行代码
   - 构建完整RAG系统

---

**版本**: v1.0
**更新**: 2025-11-07
