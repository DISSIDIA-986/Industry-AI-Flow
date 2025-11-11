# Industry AI Flow 安全与多租户改进说明

本轮优化主要针对 `temp/summary/to_be_improved.md` 中指出的以下薄弱点：

- 缺乏统一的依赖注入与安全控制（架构 & 安全）
- API 限流、认证与审计能力不足（安全加固）
- 多租户与操作可追溯性缺失（功能设计 & 数据治理）
- 文件上传与输入验证缺少统一策略（安全 & 性能）

## 关键改动

1. **统一安全依赖层**
   - 新增 `backend/security` 模块，提供 API Key 校验、租户上下文解析、速率限制（滑动窗口）等能力。
   - FastAPI 应用与核心路由通过 `Depends(secure_endpoint)` 注入，自动完成认证、限流与租户追踪。

2. **多租户上下文 & 审计日志**
   - 通过 `TenantContext` 将 `X-Tenant-ID`、来源 IP、API Key 等信息注入到请求上下文。
   - 引入 `backend/services/audit_logger.py`，输出 JSON Lines 格式的安全审计日志（路径：`logs/audit.log`），覆盖 RAG 查询、代码执行、数据处理与文件操作。

3. **文件 & 资源护栏**
   - 新增 `validate_and_buffer_upload` 与 `persist_temp_file`，集中校验扩展名、文件大小、空文件等风险，并对文件名进行消毒处理。
   - 对 `/documents/upload`、`/data/upload` 以及文档管理 API 的更新/替换操作全部启用统一校验及审计。
   - 引入 `MemoryGuard`（`MEMORY_GUARD_LIMIT_MB`），在数据分析、可视化、代码执行等高负载端点执行前做内存巡检，超阈值时返回结构化错误，避免进程被 OOM 回收。

4. **敏感数据管理**
   - 支持三种存储策略：明文 (`API_KEYS`)、Fernet 加密 (`SECRET_ENCRYPTION_KEY` + `API_KEYS_ENCRYPTED`)、PBKDF2 哈希 (`API_KEY_HASHES` + `SECRET_HASH_SALT`) —— 校验全部在常量时间内完成。
   - 新增 `tools/secure_config.py`，可快速生成Fernet密钥、加密API Key或生成PBKDF2哈希：
     ```bash
     python tools/secure_config.py gen-key
     python tools/secure_config.py encrypt --key <FERNET_KEY> --secret "prod-api-key"
     python tools/secure_config.py hash --secret "prod-api-key" --salt "tenant-a"
     ```

5. **配置项与可运维性**
   - `backend/config.py` 新增一组安全相关配置（`API_KEYS`, `API_KEYS_ENCRYPTED`, `API_KEY_HASHES`, `REQUIRE_API_KEY`, `MAX_UPLOAD_SIZE_BYTES`, `MEMORY_GUARD_LIMIT_MB`, `LOG_FORMAT_JSON`, `ENABLE_PROMETHEUS_METRICS` 等）；默认值兼容旧流程。
   - 通过 `settings.audit_log_file` 自动创建日志目录，无需手动初始化。

6. **用户认证与授权**
   - 引入 Bearer Token（JWT）解析模块 `backend/security/auth.py`，通过 `REQUIRE_USER_AUTH` + `AUTH_JWT_SECRET` 等变量控制是否必须提供用户身份。
   - 令牌字段 `sub`/`user_id`、`roles`、`permissions` 会自动注入 `TenantContext`，后续中间件或业务逻辑可按角色做差异化处理。

7. **观测与告警**
   - `ENABLE_PROMETHEUS_METRICS=true` 时自动暴露 `/metrics`（基于 `prometheus-fastapi-instrumentator`），可被 Prometheus/Loki 等采集。
   - `LOG_FORMAT_JSON=true` 以 JSON 结构输出日志，便于集中式日志平台解析；可通过 `LOG_LEVEL`/`LOG_FORMAT` 微调。
   - 统一错误返回格式：无论异常来源，都会返回 `{success: false, error_code, message, detail}` 结构，`message` 为用户友好描述，`detail` 供调试追踪。

## 使用指南

| 能力 | 配置项 | 默认值 | 说明 |
| --- | --- | --- | --- |
| API Key 校验 | `REQUIRE_API_KEY`, `API_KEYS`, `API_KEY_HEADER` | 关闭 / 空 | 设置 `REQUIRE_API_KEY=true` 并配置 `API_KEYS`（逗号分隔）即可启用 |
| 多租户标识 | `TENANT_HEADER`, `DEFAULT_TENANT_ID`, `ALLOW_ANONYMOUS_TENANTS` | `X-Tenant-ID` / `public` / `false` | 客户端需在请求头传入租户 ID，未提供时回退到默认值 |
| 限流 | `API_RATE_LIMIT_PER_MINUTE`, `API_RATE_LIMIT_BURST` | `120` / `20` | 以“租户 + IP”为粒度，超限将返回 429 |
| 上传限制 | `MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_UPLOAD_EXTENSIONS` | 10MB / 多格式 | 可按需扩展或收紧允许的文件类型 |
| 审计日志 | `AUDIT_LOG_PATH` | `logs/audit.log` | 输出 JSON Lines，可由 ELK/Splunk 等平台收集 |
| 密钥加密 | `SECRET_ENCRYPTION_KEY`, `API_KEYS_ENCRYPTED` | 空 | `SECRET_ENCRYPTION_KEY` 需是 `Fernet.generate_key()` 生成的 Base64 字符串 |
| 密钥哈希 | `API_KEY_HASHES`, `SECRET_HASH_SALT`, `SECRET_HASH_ITERATIONS` | 空 / 空 / `120000` | 将 `tools/secure_config.py hash` 生成的值填入 `API_KEY_HASHES`，可多值逗号分隔 |
| 内存护栏 | `MEMORY_GUARD_LIMIT_MB`, `MEMORY_GUARD_SOFT_LIMIT_MB` | `4096` / `3072` | 达到软阈值会告警，超过硬阈值直接中断请求并返回 503 |
| 用户认证 | `REQUIRE_USER_AUTH`, `AUTH_JWT_SECRET`, `AUTH_JWT_ALGORITHM`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE` | false / 空 / `HS256` / 空 / 空 | 设置后即可验证 Bearer Token；当 `REQUIRE_USER_AUTH=true` 时必须提供合法 JWT |
| 观测指标 | `ENABLE_PROMETHEUS_METRICS`, `LOG_FORMAT_JSON`, `LOG_LEVEL` | true / true / `INFO` | 是否开放 `/metrics` 以及是否输出 JSON 日志 |
| 查询缓存 | `QUERY_CACHE_ENABLED`, `QUERY_CACHE_TTL_SECONDS`, `QUERY_CACHE_MAXSIZE` | true / `120` / `256` | 针对 RAG/统一查询的租户级内存缓存；命中结果自动返回并记录审计 |

## 调用示例

```bash
curl https://api.example.com/api/v1/query \
  -H "X-API-Key: <your-key>" \
  -H "X-Tenant-ID: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{"question": "请解析最新报表", "top_k": 3}'
```

## 后续建议

1. **持久化限流或门神**：将当前内存滑动窗口升级为 Redis/Redis Cluster，满足横向扩展。
2. **租户隔离策略**：结合数据库 schema 或索引过滤进一步隔离向量/档案数据。
3. **审计可观测性**：将 `logs/audit.log` 纳入集中式日志（如 Loki/ELK）并建立实时告警。
4. **自动化安全测试**：结合 API Fuzz、上传模糊测试等脚本，持续验证输入验证逻辑。
5. **持久化限流或门神**：将 `SlidingWindowRateLimiter` 换成 Redis/Envoy 等中心化方案，进一步提升抗压能力。
6. **角色策略**：结合 `TenantContext.roles` 快速实现细粒度的权限判定或订阅隔离。
