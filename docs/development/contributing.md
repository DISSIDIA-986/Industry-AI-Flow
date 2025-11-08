# 贡献指南

感谢您对 Industry AI Flow 项目的关注！我们欢迎各种形式的贡献。

## 🤝 如何贡献

### 报告问题
- 使用 GitHub Issues 报告 bug
- 提供详细的问题描述和复现步骤
- 包含相关的日志和截图

### 提交代码
1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 改进文档
- 修正文档错误
- 添加使用示例
- 翻译文档内容
- 改进文档结构

## 📝 代码规范

### Python 代码风格
- 遵循 PEP 8 规范
- 使用有意义的变量和函数名
- 添加必要的注释和文档字符串
- 保持代码简洁和可读性

### 提交信息规范
```
type(scope): description

[optional body]

[optional footer]
```

类型说明：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构代码
- `test`: 添加测试
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(rag): add support for multiple document formats

- Add PDF, DOCX, TXT file support
- Implement document parsing pipeline
- Add relevant unit tests

Closes #123
```

## 🧪 测试要求

### 运行测试
```bash
# 运行所有测试
python tests/run_comprehensive_tests.py

# 运行特定类别测试
python tests/run_comprehensive_tests.py --categories core_functionality

# 并行运行测试
python tests/run_comprehensive_tests.py --parallel
```

### 测试覆盖率
- 新功能必须包含对应的测试用例
- 测试覆盖率应保持在 80% 以上
- 关键功能测试覆盖率应达到 95% 以上

## 📋 开发流程

### 1. 环境设置
```bash
# 克隆仓库
git clone https://github.com/your-username/Industry-AI-Flow.git
cd Industry-AI-Flow

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 开发前检查
- [ ] 查看现有 Issues 了解项目状态
- [ ] 阅读相关文档了解功能模块
- [ ] 确认功能需求和技术实现方案

### 3. 开发过程
- 遵循项目代码规范
- 添加必要的测试用例
- 更新相关文档
- 确保本地测试通过

### 4. 提交前检查
- [ ] 代码格式化完成
- [ ] 所有测试通过
- [ ] 文档更新完整
- [ ] 提交信息符合规范

## 🏷️ 标签和里程碑

### Issue 标签
- `bug`: 错误报告
- `enhancement`: 功能增强
- `documentation`: 文档相关
- `good first issue`: 适合新手
- `help wanted`: 需要帮助
- `priority/high`: 高优先级
- `priority/medium`: 中等优先级
- `priority/low`: 低优先级

### 里程碑
- `v1.0`: 核心功能完成
- `v1.1`: 功能增强和优化
- `v2.0`: 重大功能更新

## 💬 交流讨论

### GitHub Discussions
- 功能建议和讨论
- 技术问题交流
- 项目方向探讨

### Pull Request 审查
- 所有 PR 需要至少一个审查者批准
- 审查者会检查代码质量、功能正确性、文档完整性
- 及时响应审查意见并进行修改

## 📚 资源链接

- [项目 README](../README.md)
- [API 文档](../implementation/api-reference.md)
- [测试指南](./testing.md)
- [调试指南](./debugging.md)

## 🙏 致谢

感谢所有为项目做出贡献的开发者！

---

如果您有任何问题，欢迎通过 Issue 或 Discussion 与我们交流。
