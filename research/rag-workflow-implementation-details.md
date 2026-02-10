# RAG + Workflow 关键实现细节与代码建议（可直接改）

> 目的：把“怎么改”写清楚，包含关键代码片段、原因、验证点。

## 1. P0 修复清单（先做）

### 1.1 提供数据库连接池工厂（修复 Prompt API 断链）
涉及文件：`backend/config.py`

建议新增：
```python
# backend/config.py
import asyncpg

_db_pool = None

async def get_database_pool() -> asyncpg.Pool:
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _db_pool
```

原因：`prompt_routes` 与 `intent_classification_routes` 都依赖该函数。
验证：启动后调用 `/api/prompts/categories/list` 不报 ImportError。

---

### 1.2 主服务注册 Prompt 路由
涉及文件：`backend/main.py`

建议改动：
```python
from backend.api.prompt_routes import router as prompt_router

app.include_router(prompt_router, tags=["prompts"])
```

原因：当前 Prompt API 实现未暴露到主服务。
验证：`GET /api/prompts/categories/list` 可访问。

---

### 1.3 修复 PromptUpdate 模型字段契约
涉及文件：`backend/api/prompt_routes.py`

建议改动：
```python
class PromptUpdate(BaseModel):
    content: Optional[str] = None
    variables: Optional[List[PromptVariableCreate]] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    tags: Optional[List[str]] = None
    change_description: Optional[str] = None
    updated_by: Optional[str] = None
    create_new_version: bool = True

# 调用端
updated_by=prompt_data.updated_by
```

原因：当前 handler 使用了模型中不存在字段。
验证：`PUT /api/prompts/{id}` 不再抛字段错误。

---

### 1.4 修复 list/search/performance 三处 SQL 问题
涉及文件：`backend/api/prompt_routes.py`

#### A) `list_prompts` 响应契约统一
建议：新增 `PromptListResponse` 模型，避免 response_model 与真实返回不一致。

#### B) `search_prompts` 参数绑定
建议改动：
```python
params = [f"%{q}%"]
conditions = ["(p.name ILIKE $1 OR p.content ILIKE $1 OR COALESCE(p.subcategory, '') ILIKE $1)"]

if category:
    conditions.append(f"p.category = ${len(params)+1}")
    params.append(category)

limit_idx = len(params) + 1
query = f"""
... WHERE {' AND '.join(conditions)} AND p.is_active = true
... LIMIT ${limit_idx}
"""
params.append(limit)
rows = await conn.fetch(query, *params)
```

#### C) `performance(days)` 参数化
建议改动：
```python
detailed_query = """
SELECT ...
FROM prompt_usage_logs
WHERE prompt_id = $1
  AND created_at >= NOW() - ($2::text || ' days')::interval
GROUP BY DATE(created_at)
ORDER BY date DESC
"""
daily_stats = await conn.fetch(detailed_query, prompt_id, days)
```

验证：`search` 在 category 有/无时都返回正确；`days=1/7/30` 数据正确变化。

---

### 1.5 修复 PromptManager 统计字段别名
涉及文件：`backend/services/prompt_manager.py`

建议改动：
```python
stats = {
    ...
    "min_execution_time_ms": row["min_execution_time"],
    "max_execution_time_ms": row["max_execution_time"],
    ...
}
```

原因：当前读取不存在 key，会在运行时抛异常。
验证：`GET /api/prompts/{id}/performance` 返回完整统计。

---

## 2. Schema 收敛建议（init_database 主线）
涉及文件：`backend/init_database.py`

### 2.1 统一创建 Prompt 表
目标：把以下表纳入主启动初始化：
1. `prompts`
2. `prompt_versions`
3. `prompt_usage_logs`
4. `prompt_experiments`
5. `prompt_tags`
6. `prompt_tag_relations`

### 2.2 `prompt_usage_logs` 一期字段建议（非分区）
```sql
CREATE TABLE IF NOT EXISTS prompt_usage_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_id UUID REFERENCES prompts(id) ON DELETE SET NULL,
  session_id VARCHAR(255),
  context JSONB DEFAULT '{}'::jsonb,
  variables_used JSONB DEFAULT '{}'::jsonb,
  execution_time_ms INTEGER,
  success BOOLEAN,
  error_message TEXT,
  user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
  llm_response JSONB,
  tokens_used INTEGER DEFAULT 0,
  model_name VARCHAR(100),
  temperature NUMERIC(3,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 索引建议
```sql
CREATE INDEX IF NOT EXISTS idx_prompt_usage_prompt_created
ON prompt_usage_logs(prompt_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompt_usage_session_created
ON prompt_usage_logs(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompts_name_category_latest
ON prompts(name, category, is_latest)
WHERE is_active = true;
```

验证：写入/查询 latency 与 explain plan 达标。

---

## 3. Workflow 集成关键点（Prompt Node）
涉及文件：`backend/services/workflows/nodes/prompt_node.py`

建议节点逻辑：
```python
async def prompt_node(state: WorkflowState) -> WorkflowState:
    manager = state.services.prompt_manager
    selector = state.services.template_selector

    template_name, template_category = selector.select(state)
    prompt_info, rendered = await manager.get_prompt(
        name=template_name,
        category=template_category,
        context=state.metadata,
        variables={
            "query": state.query,
            "context": state.retrieved_context,
            "intent": state.intent,
        },
        enable_experiments=state.flags.prompt_experiments_enabled,
    )

    state.system_prompt = rendered
    state.prompt_meta = {
        "prompt_id": str(prompt_info.id),
        "name": prompt_info.name,
        "version": prompt_info.version,
    }
    return state
```

关键解释：
1. prompt 选择与渲染必须在路由前完成，保证 local/cloud 一致输入。
2. `prompt_meta` 必须写入 trace，便于 A/B 归因。

---

## 4. Executor Provider 抽象（Docker + PPIO）
涉及文件：
- `backend/services/code_executor/providers/base.py`
- `backend/services/code_executor/providers/docker_provider.py`
- `backend/services/code_executor/providers/ppio_provider.py`
- `backend/services/code_executor/manager.py`

接口建议：
```python
class ExecutionProvider(Protocol):
    async def execute(self, code: str, files: dict[str, bytes] | None, timeout_s: int) -> ExecutionResult: ...
    async def health(self) -> dict: ...
```

Manager 选择策略：
1. `docker`：默认。
2. `auto`：docker 失败或超时后 fallback 到 ppio。
3. `ppio`：显式启用云执行。

验证：故障注入时 fallback 成功且响应结构一致。

---

## 5. Streamlit 管理端从 Mock 到真实 API
涉及文件：`tools/data-generator/streamlit_prompt_manager.py`（后续迁移到 `tools/prompt-admin/`）

建议 API 客户端骨架：
```python
import requests

class PromptApiClient:
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {"X-API-Key": api_key} if api_key else {}

    def list_prompts(self, page=1, size=20):
        r = requests.get(f"{self.base_url}/api/prompts/", params={"page": page, "size": size}, headers=self.headers, timeout=20)
        r.raise_for_status()
        return r.json()

    def test_prompt(self, prompt_id: str, variables: dict):
        r = requests.post(f"{self.base_url}/api/prompts/{prompt_id}/test", json={"variables": variables}, headers=self.headers, timeout=20)
        r.raise_for_status()
        return r.json()
```

验证：UI 完成真实 CRUD、渲染测试、实验配置和性能查询。

---

## 6. 最小测试清单（按变更项）
1. `tests/unit/test_prompt_routes_contract.py`
2. `tests/unit/test_prompt_manager_stats_alias.py`
3. `tests/unit/test_prompt_search_sql_params.py`
4. `tests/integration/test_prompt_api_end_to_end.py`
5. `tests/integration/test_workflow_prompt_node.py`
6. `tests/integration/test_executor_provider_fallback.py`

建议执行：
```bash
.venv_uv/bin/pytest -q tests/unit/test_prompt_* tests/integration/test_prompt_*
```
