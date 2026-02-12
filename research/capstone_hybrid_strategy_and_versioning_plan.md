# Industry AI Flow Capstone Strategy (SAIT)

## 1. 目标与约束

本项目定位是 SAIT Capstone 展示，不是工业生产系统。
核心目标是：
1. 清晰演示 AI 如何为建筑行业赋能。
2. 在有限预算与学生设备条件下，保证演示稳定、可重复。
3. 关键链路可解释（RAG、成本估算、代码生成执行）。

你的当前资源：
- Mac Studio M1 Max, 32GB unified memory
- Windows Laptop (i7 + RTX 5060, 32GB RAM)

这套资源足够做一个高质量 demonstration，但不适合追求“大模型全本地+全功能并发高压”路线。

## 2. 总体原则（建议采用）

建议采用 `Demo-first Hybrid`：
1. 本地负责“可控、低成本、可离线兜底”的链路。
2. 云端负责“质量敏感、速度敏感”的链路。
3. 任何关键展示功能都要有 fallback（至少一条本地可运行路径）。

优先级排序：
1. 演示稳定性
2. 响应速度
3. 输出质量
4. 成本优化

## 3. 本地/云端取舍建议（按能力分流）

## 3.1 建议的路由策略

1. RAG 常规问答：
- 默认本地模型（低成本）
- 低置信度/复杂问题回退云端（提升质量）

2. 代码生成（动态分析脚本）：
- 建议默认云端商业模型（展示质量和速度更稳）
- 本地模型作为兜底

3. 成本估算（你们新增的模块）：
- 完全本地（结构化特征 + 训练好的回归模型）
- 不需要云端 LLM 参与数值预测本体

4. OCR 与文档解析：
- 本地优先（PaddleOCR + 结构化处理）
- 云端仅用于后续解释生成（可选）

## 3.2 为什么这样分配

1. 本地小模型在“长代码生成/复杂推理”上质量波动较大，演示时容易卡住或结果不稳定。
2. 成本估算本质是结构化预测，使用专门模型比“让 LLM 瞎估算”更稳、更专业。
3. RAG 展示强调“检索 + 依据回答”，本地模型足够展示流程；复杂问题再云端补强。

## 4. 单机部署建议（只用一台机器）

你要求“演示时只运行在一台机器上”，这是正确的。  
Capstone 演示应避免跨机依赖，减少网络、端口、同步问题。

## 4.1 推荐默认：Mac Studio 单机运行

建议在 Mac Studio 上一机跑完整演示链路：
1. FastAPI backend
2. PostgreSQL + pgvector
3. Prompt/Intent/Workflow orchestration
4. 成本估算模型服务
5. 本地轻量 LLM（兜底）+ 云端商业模型（主力质量）

理由：
1. 一体化稳定性更高（答辩现场最关键）。
2. 32GB unified memory 足够支撑 demo 级并发与模型规模。
3. 你当前项目主要开发环境与脚本体系更偏向这一侧，迁移成本低。

## 4.2 备选：Windows + RTX 5060 单机运行

如果你更看重本地推理速度，可改用 Windows 单机，但建议提前做完整彩排。  
注意 Docker/WSL/驱动链路的稳定性验证，否则答辩风险会高于 Mac 单机方案。

结论：只选一台机器时，优先 **Mac Studio 单机**，Windows 作为备用演示环境即可。

## 5. 演示模式设计（强烈建议）

至少准备 3 种模式：

1. `Live Hybrid`（主模式）
- 本地 + 云端都可用
- 展示最佳效果

2. `Local Safe`（保底模式）
- 禁用云端调用
- 演示“可离线运行”

3. `Scripted Replay`（故障保险模式）
- 预置输入与输出样例（含日志/截图）
- 云端或网络故障时仍可完成讲解

建议在 UI 上加一个显式模式切换标签，答辩时能清楚解释 trade-off。  
这三种模式都应在同一台机器上可切换运行。

## 6. PPIO（代码沙箱服务）是否现在集成

建议：
1. Capstone 当前阶段可不强制集成 PPIO。
2. 先确保本地 Docker 隔离执行链路可演示并可控。
3. 把 PPIO 作为“可选增强能力”以 feature flag 方式预留。

理由：
1. 新外部服务会引入联调时间与失败面。
2. 你当前核心风险不是“没有沙箱能力”，而是“演示稳定性和集成复杂度”。
3. 如果时间允许，可在后续加 `provider=ppio` 作为替代执行器，并保留本地 fallback。

## 7. 成本控制建议（云端 API）

不需要先追求最精确预算模型，先上可执行的三层控制：

1. 软阈值（warn）
- 达到日预算 70% 提示

2. 硬阈值（force local）
- 达到日预算 100% 后强制 local_only

3. 管理开关（demo override）
- 演示时允许管理员临时提升阈值

建议指标：
1. 每日 token 使用量
2. 每日费用
3. 云端回退次数
4. 平均响应时延

## 8. 关于“训练较大模型”的取舍

你当前项目并不需要“训练大语言模型”才能完成 Capstone 价值展示。

建议：
1. 成本估算模块继续使用结构化 ML（你们现有方案正确）。
2. 仅在需要做“实验性对比”时使用 Colab（例如小规模 LoRA/QLoRA 试验）。
3. 不把“训练大模型”作为主线里程碑，否则风险高、收益低。

## 9. Python 版本与依赖冻结（重点）

## 9.1 当前状态观察

项目已声明：
- `pyproject.toml` 中 `requires-python = ">=3.13,<3.14"`

但存在配置不一致：
1. `tool.black.target-version` 仍是 py38~py312
2. `tool.mypy.python_version` 仍是 `3.8`
3. `requirements*.txt` 存在多份历史快照，版本口径不统一

这会在后续修 bug / 新增功能时引发环境漂移。

## 9.2 推荐冻结方案（适合 Capstone）

1. 固定 Python 主版本：`3.13.x`
- 不跨 major/minor
- patch 升级可控

2. 单一事实源（single source of truth）：
- 以 `pyproject.toml` 为主
- `requirements` 由它导出（或反向但只能一种）

3. 分层依赖文件：
- `requirements/base.txt`
- `requirements/dev.txt`
- `requirements/demo.txt`
- `requirements/lock/*.txt`（平台锁定）

4. 明确“必需组件版本锁定”：
- FastAPI / pydantic / pandas / numpy / asyncpg / pgvector 相关
- 本地推理栈（ollama client or llama.cpp binding）
- OCR 栈（若演示包含 OCR）

5. CI/gate 前置检查：
- 启动前检查 Python minor version
- 检查 lock 文件与已安装版本一致性

## 9.3 最小可执行动作清单（建议一周内完成）

1. 统一 `pyproject.toml` 工具链版本目标到 Python 3.13
2. 清理重复/冲突依赖文件，只保留一套主流程
3. 提供一键脚本：
- 创建 venv
- 安装锁定依赖
- 运行 gate
4. 在 README 增加“Capstone Demo 环境标准”章节

## 10. 可执行的最终建议（结论）

针对你当前阶段，最佳取舍是：

1. 架构层面：
- 采用本地+云端 hybrid，不追求纯本地大模型。

2. 能力分配：
- 代码生成默认云端
- RAG 本地优先 + 云端回退
- 成本估算本地专用模型

3. 工程治理：
- 立即做 Python 3.13 + 关键依赖冻结
- 减少多版本 requirements 分叉

4. 演示策略：
- 准备 Live/Local/Replay 三模式
- 保证任何网络状态都可完成答辩演示

这套方案最符合 Capstone 成功标准：
- 讲得清楚
- 跑得稳定
- 成本可控
- 后续还能扩展。
