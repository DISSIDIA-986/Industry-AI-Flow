# Industry AI Flow - 快速开始指南

## 快速测试

### 1. 代码执行系统测试

```bash
# 运行测试套件
python test_code_execution.py

# 预期输出:
# ✅ 环境检测
# ✅ 代码验证
# ✅ 基础执行
# ✅ 数据可视化
# ✅ LangChain工具
# ✅ 机器学习
# 🎉 所有测试通过!
```

### 2. 文档处理系统测试

```bash
# 运行测试套件
python test_document_processing.py

# 预期输出:
# ✅ OCR可用性
# ✅ 文档提取器
# ✅ 文本提取
# ✅ LangChain工具
# ✅ 批量处理
# ⏭️  OCR集成 (需要图像文件)
```

---

## 代码执行示例

### 示例 1: 数据分析

```python
from backend.tools.code_execution import code_execution_tool

code = """
import pandas as pd
import numpy as np

# 创建销售数据
data = pd.DataFrame({
    'product': ['A', 'B', 'C', 'D'],
    'sales': [120, 150, 90, 200],
    'profit': [30, 45, 20, 60]
})

# 计算利润率
data['profit_margin'] = (data['profit'] / data['sales'] * 100).round(2)

print("销售数据分析:")
print(data)
print(f"\\n总销售额: {data['sales'].sum()}")
print(f"总利润: {data['profit'].sum()}")
print(f"平均利润率: {data['profit_margin'].mean():.2f}%")
"""

result = code_execution_tool.invoke({"code": code})

if result['success']:
    print(result['stdout'])
else:
    print(f"错误: {result['error']}")
```

### 示例 2: 数据可视化

```python
code = """
import matplotlib.pyplot as plt
import numpy as np

# 生成数据
categories = ['Q1', 'Q2', 'Q3', 'Q4']
revenue = [120, 150, 180, 200]
costs = [80, 100, 120, 130]

# 创建柱状图
x = np.arange(len(categories))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width/2, revenue, width, label='收入', color='#2ecc71')
ax.bar(x + width/2, costs, width, label='成本', color='#e74c3c')

ax.set_xlabel('季度')
ax.set_ylabel('金额 (万元)')
ax.set_title('2024年季度财务对比')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('financial_comparison.png', dpi=150)
print("✅ 图表已保存: financial_comparison.png")
"""

result = code_execution_tool.invoke({"code": code, "timeout": 30})

if result['success']:
    print(result['stdout'])
    print(f"生成的图表: {result['visualizations']}")
```

### 示例 3: 机器学习

```python
code = """
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import numpy as np

# 生成模拟数据
np.random.seed(42)
X = np.random.randn(200, 5)
y = (X[:, 0] + X[:, 1] > 0).astype(int)

# 分割数据
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 训练随机森林模型
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 评估
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("=== 随机森林分类模型 ===")
print(f"准确率: {accuracy:.4f}")
print("\\n分类报告:")
print(classification_report(y_test, y_pred, target_names=['类别0', '类别1']))
"""

result = code_execution_tool.invoke({"code": code, "timeout": 60})
print(result['stdout'])
```

---

## 文档处理示例

### 示例 1: PDF文本提取

```python
from backend.tools.document_processing import extract_document_text

result = extract_document_text.invoke({
    "file_path": "/path/to/document.pdf",
    "use_ocr": True  # 自动使用OCR处理扫描PDF
})

if result['success']:
    print(f"文档类型: {result['file_type']}")
    print(f"提取方法: {result['method']}")
    print(f"页数: {result['metadata'].get('num_pages', 'N/A')}")
    print(f"\\n文本内容:\\n{result['text'][:500]}...")
else:
    print(f"提取失败: {result['error']}")
```

### 示例 2: 图像OCR识别

```python
from backend.tools.document_processing import ocr_image

# 中文识别
result = ocr_image.invoke({
    "image_path": "/path/to/chinese_document.png",
    "language": "ch"
})

if result['success']:
    print(f"识别方法: {result['method']}")  # local 或 api
    print(f"置信度: {result['confidence']:.2%}")
    print(f"识别文字:\\n{result['text']}")
else:
    print(f"识别失败: {result['error']}")
```

### 示例 3: 批量文档处理

```python
from backend.tools.document_processing import batch_extract_documents

files = [
    "/data/report1.pdf",
    "/data/report2.docx",
    "/data/data.xlsx",
    "/data/scan.png"
]

result = batch_extract_documents.invoke({
    "file_paths": files,
    "use_ocr": True
})

print(f"总文件数: {result['total']}")
print(f"成功: {result['succeeded']}")
print(f"失败: {result['failed']}")

for file_result in result['results']:
    print(f"\\n{file_result['file_path']}:")
    if file_result['success']:
        print(f"  ✅ 提取成功 ({file_result['file_type']})")
        print(f"  文本长度: {len(file_result['text'])} 字符")
    else:
        print(f"  ❌ 失败: {file_result['error']}")
```

---

## 完整工作流示例

### 文档分析 + 代码执行 Pipeline

```python
from backend.tools.document_processing import extract_document_text
from backend.tools.code_execution import code_execution_tool

# 步骤1: 提取Excel数据
doc_result = extract_document_text.invoke({
    "file_path": "/data/sales_data.xlsx",
    "use_ocr": False
})

if not doc_result['success']:
    print(f"文档提取失败: {doc_result['error']}")
    exit(1)

# 步骤2: 生成分析代码 (基于提取的数据)
analysis_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import io

# 注: 实际应用中,这里应该解析提取的Excel数据
# 示例使用模拟数据

data = pd.DataFrame({{
    '月份': ['1月', '2月', '3月', '4月'],
    '销售额': [100, 120, 150, 180],
    '客户数': [50, 60, 75, 90]
}}
)

# 数据分析
print("=== 销售数据分析 ===")
print(data)
print(f"\\n平均销售额: {{data['销售额'].mean():.2f}}")
print(f"总客户数: {{data['客户数'].sum()}}")

# 创建可视化
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# 销售额趋势
ax1.plot(data['月份'], data['销售额'], marker='o', linewidth=2, color='#3498db')
ax1.set_title('月度销售额趋势', fontsize=14, fontweight='bold')
ax1.set_ylabel('销售额 (万元)')
ax1.grid(True, alpha=0.3)

# 客户数增长
ax2.bar(data['月份'], data['客户数'], color='#2ecc71', alpha=0.7)
ax2.set_title('月度客户数', fontsize=14, fontweight='bold')
ax2.set_ylabel('客户数')
ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('sales_analysis.png', dpi=150)
print("\\n✅ 分析图表已生成: sales_analysis.png")
"""

# 步骤3: 执行分析代码
exec_result = code_execution_tool.invoke({
    "code": analysis_code,
    "timeout": 60
})

if exec_result['success']:
    print("\\n" + "="*60)
    print("分析完成!")
    print("="*60)
    print(exec_result['stdout'])
    print(f"\\n生成的可视化文件: {exec_result['visualizations']}")
else:
    print(f"分析失败: {exec_result['error']}")
```

---

## 环境配置

### 必需依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# Docker (用于代码执行)
# 确保Docker Desktop已安装并运行
docker --version
```

### 可选配置

#### 1. 百度OCR API (作为PaddleOCR备份)

在`.env`文件中添加:
```bash
BAIDU_OCR_APP_ID=your_app_id
BAIDU_OCR_API_KEY=your_api_key
BAIDU_OCR_SECRET_KEY=your_secret_key
```

#### 2. PaddleOCR加速 (Apple Silicon)

系统会自动检测并使用MPS加速,无需配置。

---

## 常见问题

### Q1: Docker镜像构建失败?

**A**: 首次运行时会自动构建镜像。如果失败:
```bash
# 手动构建
cd docker/data-analysis
docker build -t industry-ai-flow/data-analysis:latest .
```

### Q2: OCR识别不准确?

**A**: 尝试以下方法:
1. 确保图像清晰,分辨率>=300DPI
2. 切换语言模式: `language="en"` (英文)
3. 使用百度API备份 (配置API密钥)

### Q3: 代码执行超时?

**A**: 增加超时时间:
```python
code_execution_tool.invoke({
    "code": your_code,
    "timeout": 120  # 增加到120秒
})
```

### Q4: 内存不足错误?

**A**: 调整Docker资源限制 (在executor初始化时):
```python
from backend.services.code_executor import DockerExecutor

executor = DockerExecutor(
    mem_limit="1g",      # 增加内存限制
    cpu_quota=100000,    # 1个CPU
    timeout=120
)
```

---

## 下一步

1. ✅ **测试系统**: 运行测试脚本验证功能
2. 📖 **阅读文档**: 查看`CODE_EXECUTION_AND_DOCUMENT_PROCESSING_SUMMARY.md`
3. 🔧 **集成Agent**: 将工具集成到LangChain 1.0 Agent
4. 🚀 **生产部署**: 配置资源限制和监控

---

**帮助**: 如遇问题,请查看详细文档或提交Issue
**版本**: v1.0
**更新时间**: 2025-11-07
