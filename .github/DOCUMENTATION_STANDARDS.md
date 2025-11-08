# Documentation Management Standards

**Version**: 1.0.0
**Last Updated**: 2025-11-08
**Enforced**: ✅ **Strict**
**Compliance**: **Mandatory**

---

## 🚨 核心原则

### 禁止生成的内容
**❌ 禁止AI生成以下类型文档**:
- 临时笔记、思维导图、草稿内容
- 未经验证的概念文档或假设性分析
- 重复或冗余的内容
- 个人观点或推测性内容
- 无明确目标或行动项的文档
- 实时聊天记录或对话摘要
- 代码注释或内联文档（应直接写入代码）

### 允许生成的文档类型
**✅ 仅允许生成以下类型文档**:
- **技术设计文档** (`TECH_DESIGN`)
- **API说明文档** (`API_DOC`)
- **测试报告** (`TEST_REPORT`)
- **实施指南** (`IMPLEMENTATION_GUIDE`)
- **部署文档** (`DEPLOYMENT`)
- **架构文档** (`ARCHITECTURE`)
- **用户手册** (`USER_MANUAL`)
- **维护指南** (`MAINTENANCE_GUIDE`)

---

## 📁 强制目录结构

```
docs/
├── architecture/              # 🏗️ 架构设计文档
│   ├── system-overview.md
│   ├── component-design.md
│   ├── data-flow.md
│   ├── security.md
│   └── performance.md
│
├── implementation/            # 🔧 实施文档
│   ├── api/
│   │   ├── user-service-api.md
│   │   ├── auth-service-api.md
│   │   └── data-service-api.md
│   ├── database/
│   │   ├── schema-design.md
│   │   └── migration-guide.md
│   └── algorithms/
│       ├── search-algorithm.md
│       └── recommendation-engine.md
│
├── user-guide/               # 📚 用户指南
│   ├── getting-started.md
│   ├── features-overview.md
│   ├── tutorials/
│   │   ├── basic-usage.md
│   │   ├── advanced-features.md
│   │   └── troubleshooting.md
│   └── faq.md
│
├── api/                      # 📡 API文档
│   ├── v1/
│   │   ├── authentication.md
│   │   ├── documents.md
│   │   └── prompts.md
│   └── openapi.yaml
│
├── deployment/               # 🚀 部署文档
│   ├── docker/
│   ├── kubernetes/
│   ├── cloud-providers/
│   └── monitoring.md
│
├── testing/                  # 🧪 测试文档
│   ├── unit-tests/
│   ├── integration-tests/
│   ├── e2e-tests/
│   └── performance-tests/
│       └── load-testing.md
│
└── maintenance/               # 🔧 维护文档
    ├── backup-procedures.md
    ├── troubleshooting.md
    ├── update-procedures.md
    └── security-patches.md
```

---

## 🏷️ 文件命名规范

### 强制命名格式
```
{功能描述}-{文档类型}.md
```

### 命名示例
```
✅ 允许示例:
- user-authentication-api.md (API文档)
- microservices-architecture.md (技术设计)
- load-testing-report.md (测试报告)
- docker-deployment-guide.md (部署指南)
- search-algorithm-implementation.md (实施文档)

❌ 禁止示例:
- notes.md (临时笔记)
- thoughts.md (思维导图)
- draft-api-doc.md (草稿)
- my-analysis.md (个人观点)
- conversation-summary.md (对话摘要)
- README-COPY.md (重复内容)
- concept-paper.md (未经验证的概念)
```

### 特殊命名规则
- **技术设计**: `feature-design-{version}.md`
- **API文档**: `{service}-api.md`
- **测试报告**: `{test-type}-report-{date}.md`
- **部署指南**: `{platform}-deployment-guide.md`

---

## 📋 文档内容标准

### 技术设计文档要求
```markdown
# 功能标题 - 技术设计文档

## 概述
- 功能目标和范围
- 技术约束
- 设计原则

## 架构设计
- 系统架构图
- 组件关系
- 数据流设计

## 技术方案
- 核心算法
- 数据结构
- 接口设计

## 实现计划
- 开发阶段
- 里程碑
- 风险评估

## 性能考虑
- 性能指标
- 扩展性方案
- 监控策略
```

### API文档要求
```markdown
# API名称 - API文档

## 概述
- API用途
- 版本信息
- 基础URL

## 认证与授权
- 认证方式
- 权限模型
- 安全措施

## 端点列表
### [方法] {路径}
- 请求格式
- 响应格式
- 错误处理

## 数据模型
- 请求对象
- 响应对象
- 验证规则

## 使用示例
- 请求示例
- 响应示例
- 错误示例
```

### 测试报告要求
```markdown
# 测试名称 - 测试报告

## 测试概览
- 测试目标
- 测试范围
- 测试环境
- 执行时间

## 测试结果
- 通过率
- 关键指标
- 问题发现

## 详细结果
### 测试用例1: {描述}
- 状态: [通过/失败]
- 执行时间
- 详细日志

### 性能指标
- 响应时间
- 吞吐量
- 资源使用

## 结论与建议
- 总体评估
- 改进建议
- 后续计划
```

---

## 🔍 自动化检查机制

### Git Pre-commit Hooks
**强制检查项目**:
1. **文件路径验证**: 检查文档是否位于正确的目录
2. **文件命名验证**: 验证文件命名格式
3. **文件类型验证**: 确保只允许的文档类型
4. **内容质量检查**: 验证文档结构和内容完整性
5. **重复内容检测**: 防止生成重复文档

### 检查脚本实现

#### `.github/hooks/pre-commit`
```bash
#!/bin/bash
# 文档规范强制检查脚本

set -e

echo "🔍 执行文档规范检查..."

# 1. 检查新增的Markdown文件
STAGED_MD_FILES=$(git diff --cached --name-only "*.md" --diff-filter=A)

if [ -z "$STAGED_MD_FILES" ]; then
    echo "✅ 没有Markdown文件需要检查"
    exit 0
fi

# 2. 检查文件路径
for file in $STAGED_MD_FILES; do
    # 检查是否在允许的目录中
    if [[ ! "$file" =~ ^(docs/architecture/|docs/implementation/|docs/user-guide/|docs/api/|docs/deployment/|docs/testing/|docs/maintenance/) ]]; then
        echo "❌ 错误: 文件 '$file' 不在允许的文档目录中"
        echo "允许的目录: docs/architecture/, docs/implementation/, docs/user-guide/, docs/api/, docs/deployment/, docs/testing/, docs/maintenance/"
        exit 1
    fi

    # 检查文件命名格式
    filename=$(basename "$file")
    if [[ ! "$filename" =~ ^[a-zA-Z0-9_-]+-[a-zA-Z0-9_-]+\.md$ ]]; then
        echo "❌ 错误: 文件 '$filename' 不符合命名格式"
        echo "正确格式: 功能描述-文档类型.md (例如: user-authentication-api.md)"
        exit 1
    fi

    # 检查文档类型是否允许
    if [[ "$file" =~ ^(设计|架构|计划|概念|草稿|笔记|思考|总结|分析)(.*)\.md$ ]] || [[ "$filename" =~ ^(draft|temp|notes|thoughts|conversation|chat)(.*)\.md$ ]]; then
        echo "❌ 错误: 禁止生成临时或概念性文档 '$file'"
        exit 1
    fi
done

echo "✅ 文档规范检查通过"
exit 0
```

#### `.github/hooks/validate-docs.py`
```python
#!/usr/bin/env python3
"""
文档内容质量验证脚本
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class DocumentValidator:
    def __init__(self, docs_path: str = "docs"):
        self.docs_path = Path(docs_path)
        self.errors = []
        self.warnings = []

    def validate_all(self) -> bool:
        """验证所有文档"""
        md_files = list(self.docs_path.rglob("*.md"))

        for file_path in md_files:
            self.validate_single(file_path)

        self.print_results()
        return len(self.errors) == 0

    def validate_single(self, file_path: Path) -> None:
        """验证单个文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查文档结构
            self.check_document_structure(file_path, content)

            # 检查内容质量
            self.check_content_quality(file_path, content)

        except Exception as e:
            self.errors.append(f"文件 {file_path}: 无法读取 - {e}")

    def check_document_structure(self, file_path: Path, content: str) -> None:
        """检查文档结构"""
        lines = content.split('\n')

        # 检查是否有标题
        has_title = any(line.strip().startswith('#') for line in lines)
        if not has_title:
            self.errors.append(f"{file_path}: 缺少文档标题")

        # 检查是否描述
        has_description = any("## 概述" in line or "## 简介" in line for line in lines)
        if not has_description:
            self.warnings.append(f"{file_path}: 建议添加概述部分")

    def check_content_quality(self, file_path: Path, content: str) -> None:
        """检查内容质量"""
        # 检查是否包含模板或占位符
        if "TODO:" in content or "[待填充]" in content:
            self.errors.append(f"{file_path}: 包含未完成的内容标记")

        # 检查内容长度
        if len(content.strip()) < 500:
            self.errors.append(f"{file_path}: 内容过于简短 (少于500字符)")

        # 检查是否有实际价值
        if not self.has_substantial_content(content):
            self.errors.append(f"{file_path}: 缺乏实质性的技术内容")

    def has_substantial_content(self, content: str) -> bool:
        """检查是否有实质性内容"""
        # 检查是否包含技术性内容
        technical_patterns = [
            r'```',  # 代码块
            r'![\w+]',  # 图片
            r'https?://',  # 链接
            r'## 功能|## 接口|## 方法', # 章节标题
            r'CREATE TABLE|SELECT \*',  # SQL
            r'function\s+\w+\s*\(',  # 函数定义
            r'class\s+\w+\s*:',  # 类定义
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in technical_patterns)

    def print_results(self) -> None:
        """打印验证结果"""
        if self.errors:
            print("\n❌ 文档验证失败:")
            for error in self.errors:
                print(f"  - {error}")
            print(f"\n发现 {len(self.errors)} 个错误，请修复后重新提交")
            exit(1)

        if self.warnings:
            print("\n⚠️ 文档建议:")
            for warning in self.warnings:
                print(f"  - {warning}")

        print("\n✅ 文档验证通过")

if __name__ == "__main__":
    validator = DocumentValidator()
    success = validator.validate_all()
    exit(0 if success else 1)
```

### CI/CD Pipeline集成

#### `.github/workflows/docs-validation.yml`
```yaml
name: Documentation Validation

on:
  push:
    paths:
      - 'docs/**.md'
  pull_request:
    paths:
      - 'docs/**.md'

jobs:
  validate-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Validate documentation standards
        run: |
          # 安装Python依赖
          python -m pip install pyyaml

          # 执行文档验证
          python .github/hooks/validate-docs.py

          # 检查文件路径和命名
          .github/hooks/pre-commit
```

---

## 📊 文档质量指标

### 强制质量标准
- **最小长度**: 技术文档不少于500字符
- **结构要求**: 必须包含标题、描述
- **内容价值**: 必须包含技术性内容
- **原创性**: 禁止复制或重复内容

### 质量评估指标
- **结构完整性**: 100% 必须通过
- **内容准确性**: 100% 必须验证
- **命名规范性**: 100% 必须合规
- **目录结构**: 100% 必须正确

### 违规处理
- **🚫 Pre-commit拒绝**: 自动阻止不符合规范的提交
- **⚠️ PR评论**: 自动添加合规性检查结果评论
- **📋 问题追踪**: 记录文档问题和改进状态
- **📈 趋势报告**: 定期生成文档质量报告

---

## 🎯 实施计划

### 阶段1: 立即实施 (P0)
1. **✅ 创建文档标准文件** - 已完成
2. **✅ 实现Git Hooks** - 已完成
3. **✅ 配置CI/CD验证** - 已完成
4. **培训团队成员** - 待完成

### 阶段2: 短期优化 (P1)
1. **实现智能内容检测**
2. **添加文档质量评分**
3. **建立文档模板库**
4. **实现自动文档更新**

### 阶段3: 长期规划 (P2)
1. **集成AI辅助文档编写**
2. **实现多语言文档支持**
3. **建立文档版本管理**
4. **实现文档搜索引擎优化**

---

## 🔧 配置和使用

### 1. 安装Git Hooks
```bash
# 安装pre-commit
pip install pre-commit

# 安装钩子
pre-commit install
```

### 2. 配置Pre-commit
创建 `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-docs
        name: Validate Documentation Standards
        entry: .github/hooks/pre-commit
        language: script
        files: '^docs/.*\\.md$'
```

### 3. 测试验证
```bash
# 测试文档验证
python .github/hooks/validate-docs.py

# 预提交测试
pre-commit run --all files
```

---

## 📚 支持资源

### 模板库
- 技术设计模板
- API文档模板
- 测试报告模板
- 用户指南模板

### 工具脚本
- 文档生成工具
- 格式化工具
- 质量检查工具
- 自动化验证工具

### 培训材料
- 文档编写最佳实践
- 技术写作指南
- 质量评估标准
- 案例和模板

---

## 🚨 违规后果

### 自动阻止
- **❌ 提交被拒绝**: Pre-commit自动阻止不符合规范的提交
- **❌ CI/CD失败**: Pipeline因文档验证失败而中断
- **❌ 代码审查受阻**: PR被标记为需要修复文档问题

### 手动处理
- **📋 问题记录**: 违规问题被记录和追踪
- **📈 趋势报告**: 定期报告文档质量状况
- **🎯 改进要求**: 明确的改进建议和时间表

### 团队影响
- **🏆 效率提升**: 减少低质量文档，提升整体效率
- **📚 知识管理**: 建立高质量的技术知识库
- **🔄 可维护性**: 确保文档的长期价值和可维护性

---

**最后更新**: 2025-11-08
**下次审查**: 2025-12-08
**版本**: 1.0.0
**状态**: ✅ **强制执行**

---

**⚠️ 重要提醒**: 此规范为强制执行标准，所有团队成员必须严格遵守。违反规范的提交将被自动拒绝，直到问题得到解决。