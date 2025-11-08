# 文档整理计划

## 🎯 整理目标
1. 简化文档结构，保留核心内容
2. 归档过时和临时文档
3. 建立清晰的目录层级
4. 提高文档维护性和可读性

## 📁 建议的新目录结构

```
Industry-AI-Flow/
├── README.md                           # 项目主页（保留并优化）
├── QUICK_START_GUIDE.md                # 快速开始（保留）
├── INSTALLATION_GUIDE.md               # 安装指南（保留）
│
├── docs/                              # 核心文档目录
│   ├── README.md                      # 文档索引
│   ├── architecture/                  # 架构设计
│   │   ├── system-overview.md         # 系统概览
│   │   ├── rag-design.md              # RAG系统设计
│   │   └── integration-design.md      # 集成设计
│   ├── implementation/                # 实现文档
│   │   ├── setup-guide.md             # 设置指南
│   │   ├── configuration.md           # 配置说明
│   │   ├── api-reference.md           # API参考
│   │   └── deployment.md              # 部署指南
│   ├── development/                   # 开发文档
│   │   ├── contributing.md            # 贡献指南
│   │   ├── testing.md                 # 测试指南
│   │   ├── code-style.md              # 代码规范
│   │   └── debugging.md               # 调试指南
│   └── user-guide/                    # 用户指南
│       ├── basic-usage.md             # 基础使用
│       ├── advanced-features.md       # 高级功能
│       ├── troubleshooting.md         # 故障排除
│       └── faq.md                     # 常见问题
│
├── archive/                           # 归档目录（.globalignore忽略）
│   ├── research/                      # 研究文档归档
│   ├── migration/                     # 迁移文档归档
│   ├── test-reports/                  # 测试报告归档
│   └── old-docs/                      # 旧版本文档归档
│
└── tmp/                              # 临时文档（.globalignore忽略）
    ├── draft/                         # 草稿文档
    └── work-in-progress/              # 进行中的工作
```

## 📋 文档分类和处置方案

### ✅ 保留并优化的文档（根目录）
- `README.md` - 项目主页，需要更新和优化
- `QUICK_START_GUIDE.md` - 快速开始指南
- `INSTALLATION_GUIDE.md` - 安装指南

### 📁 迁移到 docs/ 目录的文档

#### docs/architecture/
- `docs/design/intent-classifier.md` → `docs/architecture/intent-classifier.md`
- `docs/research/METADATA_RETRIEVAL_PROPOSAL.md` → `docs/architecture/metadata-retrieval.md`

#### docs/implementation/
- `docs/implementation/ocr-optimization.md` - 保留
- `docs/implementation/zhipu-integration.md` - 保留
- `docs/implementation/prompt-management.md` - 保留

#### docs/guides/
- `docs/guides/setup.md` → `docs/implementation/setup-guide.md`

### 📦 归档到 archive/ 的文档

#### archive/research/（过时的研究文档）
- `docs/research/chatgpt.archive.md`
- `docs/research/gemini.archive.md`
- `docs/research/glm.archive.md`
- `docs/research/qwen3.archive.md`
- `docs/research/best-ai-workflow.plan.md`
- `docs/research/best-document-archiving.plan.md`
- `docs/research/chatgpt.plan.md`
- `docs/research/claude.plan.md`
- `docs/research/gemini.plan.md`
- `docs/research/glm4.plan.md`
- `docs/research/perplexity.plan.md`
- `docs/research/qwen3.plan.md`
- `docs/research/local-development-feasibility.*`
- `docs/research/LangChain-1.0.md`

#### archive/migration/（迁移相关文档）
- `docs/implementation/migration-guides/` 整个目录
- `LLAMACPP_MIGRATION_SUMMARY.md`
- `PADDLEOCR_INSTALLATION_SUMMARY.md`
- `PROJECT_RESTRUCTURE_SUMMARY.md`

#### archive/test-reports/（测试报告）
- `COMPREHENSIVE_TEST_REPORT.md`
- `LLAMACPP_COMPREHENSIVE_TEST_REPORT.md`
- `REALISTIC_RAG_TEST_ANALYSIS.md`
- `test_results/` 整个目录

#### archive/old-docs/（其他临时文档）
- `CODE_EXECUTION_AND_DOCUMENT_PROCESSING_SUMMARY.md`
- `CODE_EXECUTION_DESIGN.md`
- `PADDLEOCR_V5_UPDATE.md`
- `RAG_ENHANCEMENT_GUIDE.md`
- `SYSTEM_IMPROVEMENTS.md`
- `temp/` 整个目录

### ✂️ 需要整合或删除的文档

#### 整合内容：
- 将多个模型计划文档整合为一个 `llm-models-guide.md`
- 将多个迁移文档的精华提取到实现指南中
- 将 llama.cpp 相关内容整合到架构文档中

#### 删除内容：
- 纯提示文件（`.prompt.md`）
- 重复的安装和配置文档
- 空或内容过少的文档

## 🔧 实施步骤

### 第一阶段：创建新结构
1. 创建新的目录结构
2. 设置 .globalignore 忽略归档目录
3. 创建新的文档索引

### 第二阶段：迁移核心文档
1. 移动和重命名重要文档
2. 更新文档内容和链接
3. 创建缺失的核心文档

### 第三阶段：归档处理
1. 移动过时文档到 archive/
2. 删除不需要的文档
3. 清理空目录

### 第四阶段：优化和验证
1. 更新 README.md 和文档索引
2. 验证所有链接的有效性
3. 检查文档内容的完整性

## 📝 .globalignore 更新

需要在 .globalignore 中添加：
```
# 归档目录
archive/
tmp/

# 测试结果
test_results/

# 临时文件
*.tmp
*.draft
*~
```

## 🎯 预期效果

整理后的文档结构将具有：
- **清晰的层次**: 核心-实现-开发-用户四个层级
- **易于维护**: 减少重复，及时更新
- **便于查找**: 逻辑分类，完善的索引
- **版本控制**: 归档和临时文件分离

这样可以让用户和开发者更容易找到需要的信息，同时保持项目的整洁性。