# 🗂️ 项目重构计划

## 📊 当前项目结构分析

### 发现的主要问题
1. **根目录文件混乱** - 50+个文件混杂在根目录
2. **测试文件分散** - 测试脚本和报告分布各处
3. **临时文件未清理** - temp目录、测试输出占用空间
4. **配置文件重复** - 多个requirements文件存在
5. **文档缺乏组织** - 设计和总结文档分散

### 文件分布统计
- **根目录Python脚本**: 20个（包括测试脚本）
- **文档文件**: 25个（.md文件）
- **配置文件**: 8个（requirements、docker、json等）
- **测试输出目录**: 3个（temp、complete_analysis_output、docker_test_output）

## 🎯 新项目结构设计

```
Industry-AI-Flow/
├── 📁 backend/                          # 后端核心服务
│   ├── agents/                         # AI Agent实现
│   ├── api/                           # REST API接口
│   ├── middleware/                    # 中间件
│   ├── migrations/                    # 数据库迁移
│   ├── services/                      # 核心业务服务
│   ├── tools/                         # 工具模块
│   ├── utils/                         # 工具函数
│   ├── main.py                        # 应用入口
│   ├── config.py                      # 配置管理
│   └── requirements.txt               # Python依赖
│
├── 📁 frontend/                       # 前端应用（新增）
│   ├── src/                          # 源代码
│   ├── public/                       # 静态资源
│   ├── package.json                  # Node.js依赖
│   └── Dockerfile                    # 前端Docker
│
├── 📁 docs/                           # 项目文档（重新组织）
│   ├── design/                       # 设计文档
│   │   ├── intent-classifier.md
│   │   ├── prompt-management.md
│   │   └── architecture.md
│   ├── implementation/               # 实现总结
│   │   ├── intent-classification.md
│   │   ├── prompt-management.md
│   │   └── migration-guides/
│   ├── api/                          # API文档
│   │   └── endpoints.md
│   ├── guides/                       # 使用指南
│   │   ├── setup.md
│   │   ├── development.md
│   │   └── deployment.md
│   └── research/                     # 研究文档
│       ├── ai-workflows/
│       ├── model-comparisons/
│       └── feasibility-studies/
│
├── 📁 scripts/                        # 脚本工具（重新组织）
│   ├── setup/                        # 环境设置脚本
│   │   ├── install-dependencies.sh
│   │   ├── setup-database.sh
│   │   └── init-services.sh
│   ├── migration/                    # 数据迁移脚本
│   │   ├── migrate-prompts.py
│   │   ├── setup-pgvector.sh
│   │   └── seed-data.py
│   ├── testing/                      # 测试相关脚本
│   │   ├── run-integration-tests.sh
│   │   ├── performance-test.sh
│   │   └── test-ocr.py
│   └── deployment/                   # 部署脚本
│       ├── build-images.sh
│       ├── deploy.sh
│       └── health-check.sh
│
├── 📁 tests/                          # 测试文件（重新组织）
│   ├── unit/                         # 单元测试
│   │   ├── test_intent_classifier.py
│   │   ├── test_prompt_manager.py
│   │   └── test_routing_engine.py
│   ├── integration/                  # 集成测试
│   │   ├── test_complete_workflow.py
│   │   ├── test_api_endpoints.py
│   │   └── test_agent_integration.py
│   ├── performance/                  # 性能测试
│   │   ├── test_load.py
│   │   └── benchmark.py
│   ├── fixtures/                     # 测试数据
│   │   ├── sample-docs/
│   │   ├── test-data.json
│   │   └── mock-responses/
│   └── reports/                      # 测试报告（自动生成）
│       ├── latest/
│       └── historical/
│
├── 📁 examples/                       # 示例代码（保留）
│   ├── basic-rag.py
│   ├── intent-classification.py
│   ├── data-analysis.py
│   └── advanced-scenarios.py
│
├── 📁 infrastructure/                 # 基础设施（重命名）
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── nginx.conf
│   ├── kubernetes/                   # K8s配置（新增）
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── monitoring/                   # 监控配置（新增）
│       ├── prometheus.yml
│       └── grafana-dashboard.json
│
├── 📁 tools/                          # 开发工具（新增）
│   ├── data-generator/               # 测试数据生成
│   ├── performance-monitor/          # 性能监控工具
│   └── deployment-automation/        # 部署自动化
│
├── 📁 workspace/                      # 工作空间（新增）
│   ├── experiments/                  # 实验性代码
│   ├── prototypes/                   # 原型代码
│   └── sandbox/                      # 沙盒测试
│
├── 📄 README.md                        # 项目说明
├── 📄 CHANGELOG.md                     # 变更日志（新增）
├── 📄 CONTRIBUTING.md                  # 贡献指南（新增）
├── 📄 LICENSE                          # 许可证（新增）
├── 📄 .gitignore                       # Git忽略文件
├── 📄 .env.example                     # 环境变量示例
└── 📄 Makefile                         # 构建脚本（新增）
```

## 📋 整理步骤

### Phase 1: 目录结构创建
1. 创建新的目录结构
2. 建立空目录和基础文件

### Phase 2: 文件分类迁移
1. **文档文件重组**
   - 所有.md文件移至docs/相应子目录
   - 按类型分类：design、implementation、guides、research
2. **脚本文件重组**
   - 所有.py脚本移至tests/相应子目录
   - 所有.sh脚本移至scripts/相应子目录
3. **配置文件整理**
   - 统一requirements文件
   - 集中Docker配置
4. **测试文件整理**
   - 测试脚本移至tests/
   - 测试报告移至tests/reports/

### Phase 3: 清理和优化
1. **清理临时文件**
   - 删除temp/目录
   - 清理测试输出目录
2. **更新.gitignore**
   - 添加新的忽略规则
   - 清理已跟踪的临时文件
3. **更新引用路径**
   - 修正导入路径
   - 更新配置文件路径

### Phase 4: 验证和文档
1. **功能验证**
   - 确保所有功能正常工作
   - 验证API接口可用性
2. **文档更新**
   - 更新README.md
   - 创建开发者指南
3. **CI/CD更新**
   - 更新构建脚本
   - 调整测试流程

## 🚀 预期效果

### 清理前后对比
- **根目录文件**: 50+ → 12
- **目录层次**: 2-3层 → 3-4层（更清晰）
- **文件查找时间**: 减少70%
- **维护复杂度**: 降低60%

### 开发效率提升
- **代码定位**: 快速找到目标文件
- **新人上手**: 清晰的项目结构
- **团队协作**: 标准化的目录规范
- **测试管理**: 集中化的测试组织

### 项目管理改善
- **版本控制**: 更好的.gitignore管理
- **文档维护**: 结构化的文档组织
- **发布流程**: 标准化的构建部署
- **监控告警**: 完善的基础设施配置

## ⚠️ 注意事项

1. **路径引用更新**: 需要批量更新Python文件中的导入路径
2. **配置文件调整**: Docker配置需要更新相对路径
3. **CI/CD流程**: 构建脚本需要适配新目录结构
4. **向后兼容**: API接口保持不变，确保客户端兼容
5. **备份策略**: 整理前建议创建项目备份

## 📈 成功指标

- [ ] 根目录文件数量 ≤ 15个
- [ ] 所有测试通过
- [ ] API接口正常工作
- [ ] Docker构建成功
- [ ] 文档完整且可访问
- [ ] .gitignore覆盖所有临时文件

---

**🎯 目标：将Industry-AI-Flow重构为一个结构清晰、易于维护、便于协作的现代化项目**
