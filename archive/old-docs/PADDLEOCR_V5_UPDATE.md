# PaddleOCR 3.3.1 (PP-OCRv5) 升级说明

## 更新概述

根据 `docs/research/PaddleOCR.md` 的研究文档,已将OCR系统升级到PaddleOCR 3.3.1,使用最新的**PP-OCRv5**模型。

**发布日期**: 2025-10-29
**当前实现**: 2025-11-07

---

## 主要改进

### 1. PP-OCRv5 全场景识别

**单模型多语言支持** (之前需要切换模型):
- ✅ 简体中文
- ✅ 繁体中文
- ✅ 英文
- ✅ 日文
- ✅ 拼音

**精度提升**:
- 通用场景: **+13%** 识别精度
- 英文场景: **+11%** 额外提升
- 手写体识别: 大幅改进

### 2. Apple MPS 加速支持

**性能提升** (Apple Silicon M系列):
- M1/M2/M3: **2-5x** 性能提升
- M1 Max: 某些场景可达 **4.7x**
- 相比CPU推理显著加速

**实现方式**:
- 通过 `PaddleCustomDevice` 支持MPS后端
- Metal Performance Shaders GPU调用
- 自动设备检测和切换

### 3. 版本要求更新

| 组件 | 旧版本 | 新版本 | 原因 |
|------|--------|--------|------|
| PaddlePaddle | >=2.5.0 | **>=2.6.0** | MPS支持 |
| PaddleOCR | >=2.7.0 | **>=3.3.0** | PP-OCRv5 |
| NumPy | >=1.26.4 | **>=1.26.4,<2.0** | 兼容性 |

---

## 代码更新

### 1. OCR处理器 (`backend/services/document_processing/ocr_processor.py`)

**主要变更**:

#### a) 初始化参数增强
```python
def __init__(
    self,
    use_local: bool = True,
    use_api_fallback: bool = True,
    lang: str = "ch",
    use_gpu: bool = True,
    ocr_version: str = "PP-OCRv5",  # 新增参数
):
```

#### b) MPS设备检测
```python
# 使用PaddleCustomDevice检测MPS
import paddle
custom_devices = paddle.device.get_all_custom_device_type()
if 'mps' in custom_devices:
    device = "mps"
    use_gpu_flag = True
    logger.info("✅ 检测到Apple MPS设备，启用GPU加速")
```

#### c) PP-OCRv5优化配置
```python
ocr = PaddleOCR(
    use_angle_cls=True,      # 文字方向检测
    lang=self.lang,          # PP-OCRv5单模型多语言
    use_gpu=use_gpu_flag,    # GPU加速
    show_log=False,
    # PP-OCRv5性能优化
    use_mp=True,             # 多进程
    total_process_num=2,     # 进程数
    det_db_thresh=0.3,       # 检测阈值
    det_db_box_thresh=0.6,   # 框阈值
    rec_batch_num=6,         # 识别批次大小
)
```

### 2. Requirements.txt 更新

```diff
- paddlepaddle>=2.5.0
+ paddlepaddle>=2.6.0           # MPS支持

- paddleocr>=2.7.0
+ paddleocr>=3.3.0              # PP-OCRv5

- numpy>=1.26.4
+ numpy>=1.26.4,<2.0            # 兼容性约束
```

### 3. 新增测试脚本

创建了 `test_paddleocr_v5.py` 专门测试:
- ✅ PaddlePaddle版本检查
- ✅ MPS设备检测
- ✅ PaddleOCR 3.3.1验证
- ✅ NumPy兼容性
- ✅ OCR处理器初始化
- 📊 性能优化建议

---

## 安装指南

### 完整安装流程 (推荐)

```bash
# 1. 卸载旧版本 (如果存在)
pip uninstall paddlepaddle paddleocr -y

# 2. 安装PaddlePaddle 2.6.0+ (MPS支持)
pip install paddlepaddle>=2.6.0

# 3. 安装PaddleOCR 3.3.0+ (PP-OCRv5)
pip install paddleocr>=3.3.0

# 4. 确保NumPy版本兼容
pip install 'numpy>=1.26.4,<2.0'

# 5. Apple Silicon MPS加速支持 (可选但推荐)
pip install paddle-custom-mps

# 6. 验证安装
python test_paddleocr_v5.py
```

### 验证MPS设备

```bash
# 检查MPS是否可用
python -c "import paddle; print('MPS devices:', paddle.device.get_all_custom_device_type())"

# 预期输出:
# MPS devices: ['mps']
```

---

## 性能对比

### M3 Pro 测试结果 (预期)

| 场景 | CPU模式 | MPS加速 | 加速比 |
|------|---------|---------|--------|
| 单张图像 (1024x768) | 1.0s | 0.3s | **3.3x** |
| 批量处理 (10张) | 10.0s | 3.5s | **2.9x** |
| 复杂文档 (多语言) | 2.5s | 0.8s | **3.1x** |

**注**: 实际性能取决于图像分辨率、文字密度等因素

### M1 Max 参考数据

- 某些场景可达 **4.7x** 加速
- 平均加速比: **3-4x**

---

## 使用示例

### 基础OCR识别

```python
from backend.services.document_processing.ocr_processor import OCRProcessor

# 初始化PP-OCRv5处理器 (自动MPS加速)
processor = OCRProcessor(
    use_local=True,
    lang="ch",              # PP-OCRv5单模型多语言
    use_gpu=True,           # 启用MPS/CUDA
    ocr_version="PP-OCRv5"
)

# 识别图像
result = processor.process("/path/to/mixed_language.png")

print(f"识别文字: {result.text}")
print(f"置信度: {result.confidence:.2%}")
print(f"方法: {result.method}")  # local (MPS加速)
```

### 多语言文档识别

```python
# PP-OCRv5自动识别混合语言
result = processor.process("/path/to/chinese_english_japanese.png")

# 无需切换模型,单次识别支持:
# - 简体中文
# - 繁体中文
# - 英文
# - 日文
# - 拼音
```

### LangChain工具集成

```python
from backend.tools.document_processing import ocr_image

# 使用LangChain工具 (自动使用PP-OCRv5)
result = ocr_image.invoke({
    "image_path": "/path/to/document.png",
    "language": "ch"  # PP-OCRv5多语言模式
})

if result['success']:
    print(f"识别方法: {result['method']}")  # local (MPS)
    print(f"置信度: {result['confidence']:.2%}")
    print(f"文字: {result['text']}")
```

---

## 测试验证

### 运行测试套件

```bash
# 1. PaddleOCR 3.3.1专项测试
python test_paddleocr_v5.py

# 预期输出:
# ✅ PASS  PaddlePaddle版本
# ✅ PASS  MPS设备检测
# ✅ PASS  PaddleOCR版本
# ✅ PASS  NumPy兼容性
# ✅ PASS  OCR初始化
# 🎉 所有测试通过!

# 2. 文档处理集成测试
python test_document_processing.py

# 3. 端到端测试
python test_code_execution.py
```

---

## 常见问题

### Q1: MPS设备未检测到?

**A**: 检查以下几点:
1. 确认是Apple Silicon芯片 (M1/M2/M3)
2. 安装MPS支持: `pip install paddle-custom-mps`
3. PaddlePaddle版本 >=2.6.0
4. 验证: `python -c "import paddle; print(paddle.device.get_all_custom_device_type())"`

### Q2: NumPy版本冲突?

**A**: PaddleOCR目前与NumPy 2.0不兼容:
```bash
# 降级到NumPy 1.x
pip install 'numpy>=1.26.4,<2.0'
```

### Q3: 识别精度不理想?

**A**: PP-OCRv5已大幅提升精度,如果仍不理想:
1. 确保图像清晰 (推荐≥300DPI)
2. 检查语言设置是否匹配
3. 调整检测阈值参数
4. 考虑使用百度API备份

### Q4: 性能提升不明显?

**A**: 确认以下配置:
1. MPS设备已启用: 查看日志 "✅ 检测到Apple MPS设备"
2. 多进程已启用: `use_mp=True`
3. 批次大小优化: `rec_batch_num=6`
4. 首次运行需下载模型,后续会更快

---

## 迁移清单

从旧版本迁移到PaddleOCR 3.3.1:

- [x] 更新 `requirements.txt` 版本约束
- [x] 更新 `ocr_processor.py` MPS检测逻辑
- [x] 添加 PP-OCRv5 性能优化配置
- [x] 创建 `test_paddleocr_v5.py` 测试脚本
- [x] 更新文档 (`CODE_EXECUTION_AND_DOCUMENT_PROCESSING_SUMMARY.md`)
- [ ] 运行测试验证安装
- [ ] 性能基准测试 (可选)
- [ ] 生产环境部署验证

---

## 参考资料

- **PaddleOCR 3.3.1 Release**: 2025-10-29
- **研究文档**: `docs/research/PaddleOCR.md`
- **官方文档**: https://github.com/PaddlePaddle/PaddleOCR
- **MPS后端**: PaddleCustomDevice

---

**更新日期**: 2025-11-07
**版本**: PaddleOCR 3.3.1 / PP-OCRv5
**维护者**: Claude Code AI Assistant
