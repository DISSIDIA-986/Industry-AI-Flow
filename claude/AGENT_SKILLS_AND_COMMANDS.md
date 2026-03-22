# Industry-AI-Flow - Claude Agent Skills & Slash Commands

## 📋 目录

- [Slash Commands](#slash-commands)
- [Agent Skills](#agent-skills)
- [使用指南](#使用指南)

## 🚀 Slash Commands

### 1. `/page-e2e-gate` - 页面端到端测试门禁

**功能**：运行基于截图的页面结果驱动E2E测试，支持多个模块的门禁验证

**描述**：
Run screenshot-first page result-driven E2E gate for data_dashboard, cost_estimation, or rag.

**参数**：
- `module` - 测试模块：`data_dashboard | cost_estimation | rag` (默认: data_dashboard)
- `cycles` - 最大重试次数 (默认: 1)
- `frontend_url` - 前端URL (默认: http://127.0.0.1:3001)
- `repair` - 修复命令 (可选)
- `rag_questions` - RAG问题数量 (默认: 30)

**使用示例**：
```bash
# 基本用法
/page-e2e-gate module=cost_estimation cycles=3

# 完整参数
/page-e2e-gate module=rag cycles=2 frontend_url=http://localhost:3123 rag_questions=50

# 带修复命令
/page-e2e-gate module=data_dashboard cycles=5 repair='pytest tests/unit -q'
```

**输出**：
- 门禁报告路径
- 最新周期报告详情
- 未解决的故障 (P0/P1优先)
- 截图/报告工件路径

---

### 2. `/rag-e2e` - RAG端到端多轮验证

**功能**：从向量化文档运行RAG多轮E2E验证，包括问题生成、基准测试和agent-browser验证

**描述**：
Run RAG multi-turn E2E validation from vectorized docs (question generation + benchmark + agent-browser).

**参数**：
- `mode` - 运行模式：`smoke | full` (默认: full)
- `max_questions` - 最大问题数 (默认: 180)
- `parallel` - 并发数 (默认: 2)
- `nothink` - 禁用思考模式：`on | off` (默认: on)
- `frontend_url` - 前端URL (默认: http://localhost:3123)

**使用示例**：
```bash
# 快速烟雾测试
/rag-e2e mode=smoke

# 完整测试
/rag-e2e mode=full max_questions=180 parallel=2

# 自定义参数
/rag-e2e mode=smoke max_questions=30 parallel=1 nothink=off frontend_url=http://localhost:3001
```

---

## 🤖 Agent Skills

### 1. `page-result-driven-e2e` - 页面结果驱动端到端测试

**功能**：标准化基于截图的浏览器E2E循环，用于Industry-AI-Flow模块

**描述**：
Standardized screenshot-first browser E2E loop for Industry-AI-Flow modules. Uses agent-browser automation, compares page evidence against expected behavior, prioritizes P0/P1 defects, applies fixes, and reruns until gate conditions are met.

**支持的模块**：
- `data_dashboard` - 数据仪表板
- `cost_estimation` - 成本估算
- `rag` - RAG系统

**核心循环流程**：
1. 执行模块E2E脚本
2. 基于证据的评估
3. 缺陷分类（P0/P1优先）
4. 修复和回归
5. 输出交付

**门禁标准**：
- `data_dashboard`: 所有案例通过
- `cost_estimation`: 所有案例通过 + 清空队列验证通过
- `rag`: 成功率达到阈值 (默认0.7)

---

### 2. `rag-e2e-multiturn` - RAG多轮端到端验证

**功能**：从向量化文档运行可重复的RAG端到端多轮质量验证

**描述**：
Run reusable RAG end-to-end multi-turn validation from vectorized documents: generate 180-question CSV (20 per doc), execute browser-based workflow-chat checks with agent-browser, compute retrieval and conversation quality metrics, and produce triage-ready reports.

**核心工作流**：
1. 生成或刷新问题库CSV
2. 运行检索/工作流基线基准测试
3. 从CSV运行浏览器E2E（完整链验证）
4. 写入总结 + 分类结论

**覆盖检查清单**：
- ✅ 检索流程
- ✅ 多轮对话行为
- ✅ 意图识别信号
- ✅ 查询重写路径
- ✅ 会话/上下文连续性
- ✅ 前端渲染正确性
- ✅ 异常/回退处理

---

## 📝 总结

**2个Slash Commands**：
1. `/page-e2e-gate` - 页面端到端测试门禁
2. `/rag-e2e` - RAG端到端多轮验证

**2个Agent Skills**：
1. `page-result-driven-e2e` - 页面结果驱动端到端测试
2. `rag-e2e-multiturn` - RAG多轮端到端验证

**主要特点**：
- ✅ 标准化测试流程
- ✅ 自动化循环和重试
- ✅ 基于证据的评估
- ✅ P0/P1优先级分类
- ✅ 多模块支持

---

*文档更新时间: 2026-03-04 11:45 MST*
*项目: Industry-AI-Flow*