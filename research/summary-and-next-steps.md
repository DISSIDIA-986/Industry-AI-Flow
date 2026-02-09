# research/implementation-plan-corrected.md（细化版草案）

## Summary
本计划是对上一版纠偏方案的工程化细化，重点补齐“可直接开发”的实现细节，尤其是关键代码落点、接口契约、数据库增量策略与测试门槛。  
一期目标不变：在现有基线下交付 `local-first + hybrid fallback + privacy guard + cost control` 的后端闭环。

## Public API / Interface Changes
1. 新增 `POST /api/v1/query/dispatch`
2. 新增 `GET /api/v1/llm/usage`
3. 新增 `GET /api/v1/llm/budget/{tenant_id}`
4. 新增 `POST /api/v1/llm/budget/{tenant_id}`
5. 保留 `POST /api/v1/query`，内部适配至 dispatch，兼容旧调用方
6. 新增统一响应结构字段：`provider_used`、`route_mode`、`latency_ms`、`usage`、`cost`、`trace_id`

## 实施步骤建议（细化）
1. **Step 0: 基线可运行性修复（P0）**
- 先补齐 `backend/services/cache/query_cache.py`，修复 `backend/main.py:24` 依赖缺失问题。
- 校正失效测试入口（例如 `scripts/testing/test_llama_cpp_integration.py:14` 的错误 import）。
- 在 `backend/init_database.py` 补充 `CREATE EXTENSION IF NOT EXISTS pgcrypto` 的显式检查。
- 产出：服务可启动、核心路由可请求、测试入口可执行。

2. **Step 1: LLM 调度控制平面统一（P0）**
- 新增 `backend/services/llm_integration/types.py`，定义统一请求/响应类型。
- 新增 `backend/services/llm_integration/dispatch_service.py`，封装 `local_only` / `hybrid_auto` / `cloud_only`。
- 统一 `llm_backend` 与 `llm_provider` 的优先级解析（`backend/config.py`）。
- 产出：一个入口管理所有 LLM 路由与回退。

3. **Step 2: 隐私脱敏与出站守卫（P1）**
- 新增 `backend/services/security/redaction_service.py`。
- 新增 `backend/services/security/egress_guard.py`，强制云端只接收脱敏文本。
- 扩展审计日志 detail 字段（provider、redaction_applied、sensitive_hit_count、policy_decision）。
- 产出：敏感字段不上云且有审计证据链。

4. **Step 3: 成本与预算治理（P1）**
- 在 `backend/init_database.py` 幂等新增：
- `llm_usage_logs`
- `llm_budget_policies`
- `schema_migrations`（轻量版本记录）
- 新增 `backend/services/llm_integration/cost_tracker.py`。
- 指标落地到 `backend/observability/performance_metrics.py` 或新增 `backend/observability/llm_metrics.py`，包括请求数、token数、成本、fallback次数。
- 产出：租户维度成本归集、预算阈值告警、超限策略（仅本地/拒绝云端）。

5. **Step 4: API 收敛与兼容适配（P1）**
- 实现 `backend/api/llm_dispatch_routes.py`、`backend/api/llm_cost_routes.py` 并在 `backend/main.py` 注册。
- 旧接口透传到新调度接口，保持响应兼容。
- 更新 `README.md` 与运维文档（配置矩阵、回退策略、预算策略、告警说明）。

6. **Step 5: 测试与发布门禁（P0）**
- 新增单元与集成测试（调度、脱敏、预算、兼容接口）。
- 设定发布门槛并固化到 CI 命令。
- 产出：上线前可量化通过标准。

## 关键文件改动点与关键代码片段（最关键）
### 1) `backend/services/cache/query_cache.py`（新增，先修复 P0）
```python
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
        q = " ".join((question or "").strip().split())
        return f"{tenant_id}:{top_k}:{q}"

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

### 2) `backend/config.py`（新增调度配置，避免双控制面冲突）
```python
hybrid_mode: str = os.getenv("HYBRID_MODE", "local_only")
# local_only | hybrid_auto | cloud_only

local_primary_backend: str = os.getenv("LOCAL_PRIMARY_BACKEND", "llama_cpp")
cloud_provider: str = os.getenv("CLOUD_PROVIDER", "zhipu")
fallback_on_error: bool = os.getenv("FALLBACK_ON_ERROR", "true").lower() == "true"
local_confidence_threshold: float = float(os.getenv("LOCAL_CONFIDENCE_THRESHOLD", "0.75"))
max_cloud_calls_per_minute: int = int(os.getenv("MAX_CLOUD_CALLS_PER_MINUTE", "120"))
```

### 3) `backend/services/llm_integration/dispatch_service.py`（新增，统一调度核心）
```python
class DispatchService:
    def __init__(self, local_client, cloud_client, redactor, cost_tracker):
        self.local_client = local_client
        self.cloud_client = cloud_client
        self.redactor = redactor
        self.cost_tracker = cost_tracker

    def generate(self, req):
        route_mode = req.route_mode
        if route_mode == "local_only":
            return self._run_local(req)

        if route_mode == "cloud_only":
            redacted = self.redactor.redact(req.prompt)
            return self._run_cloud(req, redacted_prompt=redacted.text, redaction=redacted)

        # hybrid_auto
        local_res = self._run_local(req, soft_fail=True)
        if local_res.success and local_res.confidence >= req.local_conf_threshold:
            return local_res

        redacted = self.redactor.redact(req.prompt)
        return self._run_cloud(req, redacted_prompt=redacted.text, redaction=redacted)
```

### 4) `backend/services/security/redaction_service.py`（新增，先脱敏后出站）
```python
import re
from dataclasses import dataclass


@dataclass
class RedactionResult:
    text: str
    hit_count: int
    categories: list[str]


class RedactionService:
    PATTERNS = {
        "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
        "phone": re.compile(r"\\b(?:\\+?86[- ]?)?1[3-9]\\d{9}\\b"),
        "id_like": re.compile(r"\\b\\d{15,18}[0-9Xx]?\\b"),
    }

    def redact(self, text: str) -> RedactionResult:
        hit, cats, out = 0, [], text
        for name, pat in self.PATTERNS.items():
            out2, n = pat.subn(f"<REDACTED_{name.upper()}>", out)
            if n > 0:
                hit += n
                cats.append(name)
                out = out2
        return RedactionResult(text=out, hit_count=hit, categories=cats)
```

### 5) `backend/init_database.py`（增量幂等 SQL，避免迁移框架缺位）
```python
# before UUID defaults
cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

cur.execute("""
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
""")
```

### 6) `backend/api/llm_dispatch_routes.py`（新增统一接口）
```python
@router.post("/query/dispatch")
async def dispatch_query(req: DispatchQueryRequest, tenant: TenantContext = Depends(get_current_tenant)):
    trace_id = str(uuid.uuid4())
    result = dispatch_service.generate(
        DispatchRequest(
            prompt=req.question,
            route_mode=req.route_mode or settings.hybrid_mode,
            tenant_id=tenant.tenant_id,
            trace_id=trace_id,
        )
    )
    return {
        "trace_id": trace_id,
        "answer": result.text,
        "provider_used": result.provider,
        "route_mode": result.route_mode,
        "usage": result.usage,
        "cost": result.cost,
    }
```

## 测试与验证计划（开发结束后）
1. 单元测试
- `query_cache`: key 稳定性、TTL 失效、tenant 隔离。
- `dispatch_service`: 三种 route_mode、fallback 条件、错误处理。
- `redaction_service`: 中英文样本、命中统计、误伤控制。
- `cost_tracker`: token 统计、费率映射、预算阈值判定。

2. 集成测试
- API：`/query/dispatch` 三模式行为正确。
- 脱敏链路：审计日志确认“无敏感明文出站”。
- 数据库：`llm_usage_logs`、`llm_budget_policies` 写入与查询通过。

3. 回归与非功能
- 回归现有 RAG/文档管理/代码执行主链路不退化。
- 性能：P95 延迟、fallback率、错误率。
- 安全：注入/越权/租户隔离/上传约束。

4. 验收门槛
- 功能通过率 100%（核心用例）。
- 安全：抽检云端请求敏感泄露 0。
- 性能：本地优先场景 P95 <= 5s。
- 成本：账单估算误差 <= 5%。

## Assumptions / Defaults
- 一期不新增前端。
- 云 provider 首期默认 zhipu（因仓库已有实现），OpenAI 放二期扩展。
- 迁移机制采用幂等 SQL + `schema_migrations`，不引入 Alembic。
