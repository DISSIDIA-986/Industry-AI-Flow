# PaddleOCR 最新特征总结
## PaddleOCR最新版本为3.3.1，发布于2025年10月29日。
## 主要特性
- **PP-OCRv5 全场景识别**
    - 单模型支持五种文字类型：简体、繁体、英文、日文、拼音，并改进复杂手写体识别。
    - 识别精度较上一代提升约 13 个百分点，英文场景再提升约 11%。

- **PP-StructureV3 文档解析**
    - 支持多场景、多版式 PDF 高精度解析。
    - 智能还原原始文档结构并导出为 Markdown / JSON。

- **PP-ChatOCRv4 多模态集成**
    - 原生支持文心大模型 4.5，融合多模型与优化 Prompt，关键信息提取精度提升约 15%。

- **PaddleOCR‑VL 视觉语言模型**
    - 开源 0.9B 轻量 VLM，支持 109 种语言，擅长复杂版面、表格、公式和手写内容提取。

- **部署能力升级**
    - 支持 PaddlePaddle 3.0/3.1、C++ 本地部署（Linux/Windows）。
    - 新增 CUDA 12、高性能推理、ONNX Runtime 后端和国产硬件（昆仑芯、昇腾）适配。
    - 服务化部署方案开源且可定制。

## macOS 本地运行 — 核心步骤与注意点

### 1. MPS 加速后端支持
- PaddlePaddle 通过 PaddleCustomDevice 提供 Apple MPS 后端，允许在 M 系列芯片上启用 GPU 加速。
- 检查已注册的自定义设备类型：
```bash
python -c "import paddle; print(paddle.device.get_all_custom_device_type())"
```

### 2. 启用 MPS 加速方式
- 在 PaddleOCR 中设置 `use_gpu=True` 并确保已安装 PaddleCustomDevice 的 MPS 支持包。
- 系统会通过 Metal Performance Shaders 调用 Apple GPU，加速推理（相较纯 CPU 有显著提升）。

### 3. 安装与配置
- 单独安装 PaddleCustomDevice MPS 支持包。
- 创建 PaddleOCR 实例时启用 GPU（`use_gpu=True`），并配合轻量模型（例如 PP-OCRv3）和多线程优化参数以获得最佳性能。

### 4. 性能预期
- MPS 加速在 M1/M2/M3 芯片上通常可带来约 2–5× 推理速度提升，M1 Max 在某些场景可达约 4.7×。

### 5. 注意事项
- 确保 PaddlePaddle 版本 ≥ 2.6.0（包含相关漏洞修复）。
- 注意 NumPy 兼容性（建议 NumPy < 2.0）。
- 首次运行需预留模型下载时间。
- 在生产或 CI 环境测试时验证硬件与后端兼容性及稳定性。

## PaddleOCR 最新版配合 LangChain 1.0 使用的正确方法总结

**PaddleOCR 3.x 与 LangChain 1.0 的集成主要用于构建 RAG 系统，先用 PaddleOCR 的文档解析能力（PP-StructureV3 或 PaddleOCR-VL）提取结构化文本、表格、公式等信息，然后通过 LangChain 的文本分割、向量存储和检索链条进行处理**。**推荐流程是：使用 `PaddleOCR()` 或 `PPStructureV3()` 从 PDF/图像中提取文本并转换为 Markdown/JSON，然后将提取结果转换为 LangChain 的 `Document` 对象，并用 `RecursiveCharacterTextSplitter` 进行分块处理**。**最后使用 LangChain 1.0 的向量存储（如 FAISS）+ 嵌入模型（HuggingFace BGE 或其他）+ LLM（如 ChatOpenAI 或本地 llama.cpp）构建 `RetrievalQA` 链进行问答**。**对于复杂文档结构识别，建议优先使用 PaddleOCR-VL（0.9B 参数的视觉语言模型，支持 109 语言）而非纯 OCR，以获得更精准的布局理解和元素识别**。**关键是确保 Python 环境支持 PaddleOCR 的依赖（paddlepaddle、paddleocr）以及 LangChain 1.0 的核心包和社区集成包（langchain、langchain-community）的兼容性**。