# Industry AI Flow 调研总结与下一步行动（纠偏版）

## 1. 结论摘要

基于当前仓库现状与新增调研文档（提交 `7371c10`）的交叉复核，一期实施建议采用 **现有技术基线增量落地**：

- 保持现有基线：`Python 3.13 + PostgreSQL/pgvector + llama.cpp/ollama(+zhipu)`
- 一期聚焦后端闭环：`local-first + hybrid fallback + privacy guard + cost control`
- 暂不做高成本迁移：不在一期切换到 `ChromaDB`、不强行降级到 `Python 3.11`

### 为什么需要纠偏

调研文档中的部分建议与仓库当前实现存在差异：

- 文档建议：DeepSeek + ChromaDB + Python 3.11+
- 仓库现状：qwen2.5/llama.cpp/ollama + pgvector + Python 3.13

若直接按文档技术栈迁移，会显著增加风险与周期，不利于一期快速形成可上线能力。

---

## 2. 当前关键发现（影响实施优先级）

### P0 问题（必须先修）

1. `backend/main.py` 依赖 `backend.services.cache.query_cache`，但仓库缺失该模块实现。
2. LLM 路由存在双控制面：`llm_backend` 与 `llm_provider` 并存，若不统一会导致调度行为不可预测。

### P1 问题（一期内必须纳入）

1. 数据库初始化里使用 `gen_random_uuid()`，应显式确保 `pgcrypto` 扩展可用。
2. 当前迁移机制主要依赖 `init_database.py` 幂等建表，不适合直接引入未落地的 Alembic 流程。
3. 测试脚本存在部分失效引用（例如 `scripts/testing/test_llama_cpp_integration.py` 的模块路径）。

---

## 3. 一期目标（4-6 周）

1. 统一 LLM 调度：支持 `local_only` / `hybrid_auto` / `cloud_only`
2. 云端出站数据 100% 脱敏，且具备可审计证据
3. 可观测成本与预算策略：按租户统计 token/cost，预算超阈值触发策略
4. 保持现有接口兼容，避免业务调用方回归

---

## 4. 实施步骤（纠偏后）

## Step 0（Week 1）：基线稳定化（P0）

### 目标

先把“可运行性”与“最小正确性”拉齐，避免后续迭代建立在不稳定底座上。

### 改动点

1. 补齐缓存模块：新增 `backend/services/cache/query_cache.py`
2. 修复失效测试入口：`scripts/testing/test_llama_cpp_integration.py`
3. 增加基线健康检查脚本（启动、核心路由探活）

### 关键验收

- `backend/main.py` 能启动并可访问 `/health`
- `/rag/query` 缓存路径可正常 hit/miss

## Step 1（Week 1-2）：统一 LLM 调度控制平面（P0）

### 目标

建立单一调度入口，解决双控制面冲突。

### 改动点

1. 新增 `backend/services/llm_integration/types.py`
2. 新增 `backend/services/llm_integration/dispatch_service.py`
3. 扩展 `backend/config.py`，新增调度策略配置：
- `HYBRID_MODE`
- `LOCAL_PRIMARY_BACKEND`
- `CLOUD_PROVIDER`
- `FALLBACK_ON_ERROR`
- `LOCAL_CONFIDENCE_THRESHOLD`

### 关键验收

- 三种路由模式可切换
- 本地失败可按策略回退云端

## Step 2（Week 2-3）：隐私脱敏与出站守卫（P1）

### 目标

严格保证“先脱敏，再出站，再审计”。

### 改动点

1. 新增 `backend/services/security/redaction_service.py`
2. 新增 `backend/services/security/egress_guard.py`
3. 扩展审计日志 detail 字段：
- `redaction_applied`
- `sensitive_hit_count`
- `sensitive_categories`
- `provider`

### 关键验收

- 云端请求中不含敏感明文
- 审计日志可追溯脱敏决策

## Step 3（Week 3-4）：成本与预算治理（P1）

### 目标

建立可计量、可告警、可降级的成本闭环。

### 改动点

1. `backend/init_database.py` 幂等新增：
- `CREATE EXTENSION IF NOT EXISTS pgcrypto`
- `llm_usage_logs`
- `llm_budget_policies`
- `schema_migrations`
2. 新增 `backend/services/llm_integration/cost_tracker.py`
3. 增加 LLM 指标（请求量、token、cost、fallback）

### 关键验收

- 每次 LLM 请求可追踪 usage/cost
- 租户预算超阈值能触发策略

## Step 4（Week 4-5）：API 收敛与兼容发布（P1）

### 目标

统一对外接口，同时保证历史接口无破坏。

### 改动点

1. 新增 `backend/api/llm_dispatch_routes.py`
2. 新增 `backend/api/llm_cost_routes.py`
3. 在 `backend/main.py` 注册新路由
4. 现有 `POST /api/v1/query` 内部透传到新 dispatch 服务

### 关键验收

- 新老接口均可用
- 老调用方无改造即可继续工作

## Step 5（Week 5-6）：测试、门禁与发布准备（P0）

### 目标

形成可重复验证的质量门禁。

### 改动点

1. 新增单元测试：调度、脱敏、成本、预算
2. 新增集成测试：dispatch 全链路、审计链路
3. 更新发布前检查清单与回滚清单

### 关键验收

- 核心测试通过率 100%
- 性能、安全、成本指标达到门槛

---

## 5. 关键文件改动建议

1. `backend/main.py`
- 保留现有业务路由
- 新增 dispatch/cost 路由注册
- 将旧查询接口适配到统一调度

2. `backend/config.py`
- 增加混合调度配置项
- 明确 `llm_backend` 与 `llm_provider` 解释优先级

3. `backend/services/llm_integration/llm_client.py`
- 保留工厂能力
- 新增/扩展统一响应结构（文本、usage、latency、provider）

4. `backend/init_database.py`
- 采用幂等 SQL 增量演进
- 增加成本与预算表

5. `backend/services/audit_logger.py`
- 接口保持不破坏
- 在 `detail` 中落地脱敏与路由审计字段

6. `backend/observability/performance_metrics.py`
- 增加 LLM 请求/成本/fallback 指标

---

## 6. 关键代码片段（建议实现）

### 6.1 查询缓存（修复 P0）

```python
# backend/services/cache/query_cache.py
from cachetools import TTLCache
from backend.config import settings


class QueryCache:
    def __init__(self):
        self.enabled = settings.query_cache_enabled
        self.cache = TTLCache(
            maxsize=settings.query_cache_maxsize,
            ttl=settings.query_cache_ttl_seconds,
        )

    def _key(self, tenant_id: str, question: str, top_k: int) -> str:
        normalized = " ".join((question or "").strip().split())
        return f"{tenant_id}:{top_k}:{normalized}"

    def get(self, tenant_id: str, question: str, top_k: int):
        if not self.enabled:
            return None
        return self.cache.get(self._key(tenant_id, question, top_k))

    def set(self, tenant_id: str, question: str, top_k: int, payload: dict):
        if not self.enabled:
            return
        self.cache[self._key(tenant_id, question, top_k)] = payload


query_cache = QueryCache()
```

### 6.2 调度服务（统一控制平面）

```python
# backend/services/llm_integration/dispatch_service.py
class DispatchService:
    def __init__(self, local_client, cloud_client, redactor, cost_tracker):
        self.local_client = local_client
        self.cloud_client = cloud_client
        self.redactor = redactor
        self.cost_tracker = cost_tracker

    def generate(self, req):
        if req.route_mode == "local_only":
            return self._run_local(req)

        if req.route_mode == "cloud_only":
            redacted = self.redactor.redact(req.prompt)
            return self._run_cloud(req, redacted_prompt=redacted.text, redaction=redacted)

        # hybrid_auto
        local_res = self._run_local(req, soft_fail=True)
        if local_res.success and local_res.confidence >= req.local_conf_threshold:
            return local_res

        redacted = self.redactor.redact(req.prompt)
        return self._run_cloud(req, redacted_prompt=redacted.text, redaction=redacted)
```

### 6.3 脱敏服务（先脱敏后出站）

```python
# backend/services/security/redaction_service.py
import re
from dataclasses import dataclass


@dataclass
class RedactionResult:
    text: str
    hit_count: int
    categories: list[str]


class RedactionService:
    PATTERNS = {
        "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "phone": re.compile(r"\b(?:\+?86[- ]?)?1[3-9]\d{9}\b"),
        "id_like": re.compile(r"\b\d{15,18}[0-9Xx]?\b"),
    }

    def redact(self, text: str) -> RedactionResult:
        out = text
        hit_count = 0
        categories = []

        for name, pattern in self.PATTERNS.items():
            out, n = pattern.subn(f"<REDACTED_{name.upper()}>", out)
            if n > 0:
                hit_count += n
                categories.append(name)

        return RedactionResult(text=out, hit_count=hit_count, categories=categories)
```

### 6.4 数据库增量（成本治理）

```python
# backend/init_database.py 中增加
cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS llm_usage_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id VARCHAR(128) NOT NULL,
        provider VARCHAR(64) NOT NULL,
        model VARCHAR(128) NOT NULL,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER DEFAULT 0,
        estimated_cost_usd NUMERIC(12,6) DEFAULT 0,
        latency_ms INTEGER DEFAULT 0,
        status VARCHAR(32) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)
```

---

## 7. 影响范围

### 代码影响

- 核心服务：`backend/services/llm_integration/*`
- 安全链路：`backend/services/security/*`
- API 层：`backend/api/*` 与 `backend/main.py`
- 数据层：`backend/init_database.py`
- 观测层：`backend/observability/*`

### 业务影响

- 接口兼容：保持历史接口可用
- 风险降低：避免一次性底层迁移
- 成本可见：从“估算”升级到“可监控+可告警”

---

## 8. 开发结束后的测试与验证计划

## 8.1 单元测试

1. 调度逻辑测试：三种 route_mode、fallback 条件、错误降级
2. 脱敏测试：中英文样本、边界文本、误杀控制
3. 成本测试：token 统计、费率映射、预算触发
4. 缓存测试：tenant 隔离、TTL、key 稳定性

## 8.2 集成测试

1. `POST /api/v1/query/dispatch` 全链路
2. 审计链路验证（脱敏摘要存在，敏感明文不存在）
3. 数据库写入验证（usage、budget）

## 8.3 回归测试

1. `/rag/query` 与 `/unified/query` 不回归
2. 文档管理、代码执行、意图路由不回归

## 8.4 验收门槛

1. 核心功能通过率：100%
2. 本地优先场景 P95 延迟：`<= 5s`
3. 敏感明文出站：0
4. 成本估算误差：`<= 5%`

---

## 9. 风险与回滚策略

### 主要风险

1. 本地模型质量波动导致 fallback 频率升高
2. 脱敏过严影响回答质量
3. 成本统计与真实账单偏差

### 回滚策略

1. 开关回滚：`HYBRID_MODE=local_only`
2. 路由回滚：关闭新 dispatch，切回旧查询实现
3. 数据回滚：保留旧表结构，新增表不影响旧逻辑

---

## 10. 一期里程碑（建议）

1. M1（Week 1 末）：基线稳定化完成（可启动、可测试）
2. M2（Week 2 末）：调度控制平面统一上线
3. M3（Week 3 末）：脱敏出站守卫生效
4. M4（Week 4 末）：成本与预算可观测
5. M5（Week 5-6）：回归通过并具备发布条件

---

## 11. 默认假设

1. 一期不新增前端管理台
2. 云 provider 一期默认沿用仓库已有能力（zhipu）
3. 迁移方式采用幂等 SQL 增量，不引入 Alembic 作为一期前置
