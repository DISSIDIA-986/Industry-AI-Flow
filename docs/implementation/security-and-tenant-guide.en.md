# Industry AI Flow — Security & Multi-Tenancy Guide

> 🌐 Language: **English** · [中文](./security-and-tenant-guide.md)

This round of hardening targeted the weak points called out in `temp/summary/to_be_improved.md`:

- Lack of unified dependency injection and security controls (architecture & security)
- Insufficient API rate limiting, authentication, and auditing (security hardening)
- Missing multi-tenant isolation and operation traceability (feature design & data governance)
- No consistent strategy for file uploads and input validation (security & performance)

## Key Changes

1. **Unified security dependency layer**
   - Added the `backend/security` module, which provides API key validation, tenant context parsing, and sliding-window rate limiting.
   - The FastAPI app and core routes inject these via `Depends(secure_endpoint)`, so authentication, rate limiting, and tenant tracking happen automatically.

2. **Multi-tenant context & audit logging**
   - `TenantContext` injects `X-Tenant-ID`, source IP, API key, and similar request metadata into the request context.
   - Introduced `backend/services/audit_logger.py`, which emits JSON Lines security audit logs (path: `logs/audit.log`) covering RAG queries, code execution, data processing, and file operations.

3. **File & resource guardrails**
   - Added `validate_and_buffer_upload` and `persist_temp_file` to centrally validate extension, file size, empty-file risk, and to sanitize filenames.
   - `/documents/upload`, `/data/upload`, and the update/replace operations on the document management API all run through the unified validation and audit path.
   - Introduced `MemoryGuard` (`MEMORY_GUARD_LIMIT_MB`) that performs a memory check before high-load endpoints such as data analysis, visualization, and code execution. Over-threshold requests return a structured error instead of letting the process be OOM-killed.

4. **Sensitive data management**
   - Supports three storage strategies: plaintext (`API_KEYS`), Fernet-encrypted (`SECRET_ENCRYPTION_KEY` + `API_KEYS_ENCRYPTED`), and PBKDF2-hashed (`API_KEY_HASHES` + `SECRET_HASH_SALT`). All comparisons run in constant time.
   - Added `tools/secure_config.py` for quickly generating Fernet keys, encrypting API keys, or producing PBKDF2 hashes:
     ```bash
     python tools/secure_config.py gen-key
     python tools/secure_config.py encrypt --key <FERNET_KEY> --secret "prod-api-key"
     python tools/secure_config.py hash --secret "prod-api-key" --salt "tenant-a"
     ```

5. **Configuration & operability**
   - `backend/config.py` gained a family of security-related settings (`API_KEYS`, `API_KEYS_ENCRYPTED`, `API_KEY_HASHES`, `REQUIRE_API_KEY`, `MAX_UPLOAD_SIZE_BYTES`, `MEMORY_GUARD_LIMIT_MB`, `LOG_FORMAT_JSON`, `ENABLE_PROMETHEUS_METRICS`, ...). Defaults preserve prior behavior.
   - `settings.audit_log_file` creates the log directory automatically — no manual setup required.

6. **User authentication & authorization**
   - Introduced the Bearer Token (JWT) parser at `backend/security/auth.py`. `REQUIRE_USER_AUTH` + `AUTH_JWT_SECRET` control whether a user identity is mandatory.
   - Token claims `sub`/`user_id`, `roles`, and `permissions` are injected into `TenantContext` so downstream middleware or business logic can branch by role.

7. **Observability & alerting**
   - `ENABLE_PROMETHEUS_METRICS=true` exposes `/metrics` (via `prometheus-fastapi-instrumentator`) for Prometheus/Loki scraping.
   - `LOG_FORMAT_JSON=true` emits JSON-structured logs for centralized log platforms; tune with `LOG_LEVEL`/`LOG_FORMAT`.
   - Unified error response: regardless of source, all exceptions return `{success: false, error_code, message, detail}`. `message` is user-friendly, `detail` is for debugging.

## Usage Guide

| Capability | Settings | Default | Notes |
| --- | --- | --- | --- |
| API key validation | `REQUIRE_API_KEY`, `API_KEYS`, `API_KEY_HEADER` | off / empty | Set `REQUIRE_API_KEY=true` and populate `API_KEYS` (comma-separated) to enable |
| Multi-tenant identity | `TENANT_HEADER`, `DEFAULT_TENANT_ID`, `ALLOW_ANONYMOUS_TENANTS` | `X-Tenant-ID` / `public` / `false` | Clients pass the tenant ID in the header; falls back to default when absent |
| Rate limiting | `API_RATE_LIMIT_PER_MINUTE`, `API_RATE_LIMIT_BURST` | `120` / `20` | Enforced per (tenant + IP). Exceeding returns 429 |
| Upload limits | `MAX_UPLOAD_SIZE_BYTES`, `ALLOWED_UPLOAD_EXTENSIONS` | 10MB / multi-format | Expand or tighten allowed types as needed |
| Audit log | `AUDIT_LOG_PATH` | `logs/audit.log` | Emits JSON Lines; scrape with ELK/Splunk |
| Key encryption | `SECRET_ENCRYPTION_KEY`, `API_KEYS_ENCRYPTED` | empty | `SECRET_ENCRYPTION_KEY` must be a Base64 string from `Fernet.generate_key()` |
| Key hashing | `API_KEY_HASHES`, `SECRET_HASH_SALT`, `SECRET_HASH_ITERATIONS` | empty / empty / `120000` | Populate `API_KEY_HASHES` with output from `tools/secure_config.py hash`; multiple values comma-separated |
| Memory guard | `MEMORY_GUARD_LIMIT_MB`, `MEMORY_GUARD_SOFT_LIMIT_MB` | `4096` / `3072` | Soft threshold warns; hard threshold aborts the request with 503 |
| User auth | `REQUIRE_USER_AUTH`, `AUTH_JWT_SECRET`, `AUTH_JWT_ALGORITHM`, `AUTH_JWT_ISSUER`, `AUTH_JWT_AUDIENCE` | false / empty / `HS256` / empty / empty | Once set, Bearer tokens are validated; when `REQUIRE_USER_AUTH=true`, a valid JWT is required |
| Observability | `ENABLE_PROMETHEUS_METRICS`, `LOG_FORMAT_JSON`, `LOG_LEVEL` | true / true / `INFO` | Whether to expose `/metrics` and emit JSON logs |
| Query cache | `QUERY_CACHE_ENABLED`, `QUERY_CACHE_TTL_SECONDS`, `QUERY_CACHE_MAXSIZE` | true / `120` / `256` | Per-tenant in-memory cache for RAG/unified queries; cache hits are audited |

## Example Request

```bash
curl https://api.example.com/api/v1/query \
  -H "X-API-Key: <your-key>" \
  -H "X-Tenant-ID: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{"question": "Parse the latest report", "top_k": 3}'
```

## Follow-up Recommendations

1. **Persistent rate limiter / gateway** — upgrade the in-memory sliding window to Redis/Redis Cluster for horizontal scaling.
2. **Tenant isolation strategy** — combine database schemas or index filtering to further isolate vector and document data.
3. **Audit observability** — pipe `logs/audit.log` into a centralized platform (Loki/ELK) and wire real-time alerts.
4. **Automated security testing** — run API fuzzing and upload fuzzing to continuously validate input validation.
5. **Centralized rate limiting** — replace `SlidingWindowRateLimiter` with Redis/Envoy for greater load resilience.
6. **Role policies** — use `TenantContext.roles` for fine-grained permission decisions or subscription-based isolation.
