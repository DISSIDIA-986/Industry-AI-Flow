import json as _json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import psutil
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse as _StreamingResponse
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# API route imports
from backend.api.auth_routes import router as auth_router
from backend.api.cost_estimation_routes import router as cost_estimation_router
from backend.api.demo_mode_routes import router as demo_mode_router
from backend.api.document_management_routes import router as document_management_router
from backend.api.enhanced_query_routes import router as enhanced_query_router
from backend.api.feedback_routes import router as feedback_router
from backend.api.llm_cost_routes import router as llm_cost_router
from backend.api.llm_dispatch_routes import router as llm_dispatch_router
from backend.api.prompt_routes import (
    router as prompt_router,  # P0: Prompt management routes
)
from backend.api.intent_classification_routes import router as intent_router
from backend.api.workflow_query_routes import (
    router as workflow_query_router,  # Phase 2 scaffold
)
from backend.middleware.error_handler import register_error_handlers
from backend.observability.logging_config import configure_logging
from backend.observability.metrics import setup_metrics
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.security.memory_guard import memory_guard
from backend.security.sanitizer import sanitize_identifier, sanitize_text
from backend.services.audit_logger import audit_logger
from backend.services.cache.query_cache import query_cache
from backend.services.database.driver_compat import connect as connect_db
from backend.services.database.driver_compat import fetchall_dicts
from backend.services.language_policy import ensure_rag_english_query
from backend.services.security import persist_temp_file, validate_and_buffer_upload

# Initialize logging
configure_logging()
logger = logging.getLogger(__name__)

# Load application settings
try:
    from backend.config import settings
except ImportError:
    settings = None

ALLOWED_UPLOAD_EXTENSIONS = (
    tuple(settings.upload_extension_whitelist)
    if settings
    else (".pdf", ".doc", ".docx", ".txt", ".csv", ".json")
)
MAX_UPLOAD_BYTES = settings.max_upload_size_bytes if settings else 10 * 1024 * 1024
TEMP_DATA_ROOT = settings.temp_data_dir if settings else "/tmp/luncheon_data"

# Global singletons with thread-safe lazy initialization
rag_engine = None
unified_orchestrator = None
code_executor = None
_rag_lock = threading.Lock()
_unified_lock = threading.Lock()
_executor_lock = threading.Lock()
_uploaded_documents_index_ready = False
_uploaded_documents_index_lock = threading.Lock()
_documents_storage_root: Optional[Path] = None
_documents_storage_root_lock = threading.Lock()
_documents_cleanup_lock = threading.Lock()
_last_documents_cleanup_at: Optional[datetime] = None


def log_audit(
    action: str,
    tenant: Optional[TenantContext],
    status: str,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper to record audit events safely."""
    tenant_id = (
        tenant.tenant_id
        if tenant and tenant.tenant_id
        else (settings.default_tenant_id if settings else "public")
    )
    audit_logger.log_event(
        action=action,
        tenant_id=tenant_id,
        status=status,
        user_id=tenant.user_id if tenant else None,
        ip_address=tenant.ip_address if tenant else None,
        detail=detail,
    )


def enforce_memory_guard(label: str) -> float:
    """Ensure current process memory stays within the configured limits."""
    return memory_guard.ensure_within_limit(label)


def _resolve_tenant_id(tenant: Optional[TenantContext]) -> str:
    if tenant and tenant.tenant_id:
        return tenant.tenant_id
    if settings and settings.default_tenant_id:
        return settings.default_tenant_id
    return "public"


def _normalize_file_path(file_path: str) -> Path:
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    return path


def _resolve_documents_storage_root() -> Path:
    global _documents_storage_root
    if _documents_storage_root is not None:
        return _documents_storage_root

    with _documents_storage_root_lock:
        if _documents_storage_root is not None:
            return _documents_storage_root

        configured_root = (
            settings.documents_storage_dir if settings else ""
        ) or "workspace/uploads/documents"
        root = _normalize_file_path(configured_root)
        root.mkdir(parents=True, exist_ok=True)
        _documents_storage_root = root
        return _documents_storage_root


def _persist_uploaded_document_file(
    *,
    content: bytes,
    sanitized_filename: str,
    tenant: Optional[TenantContext],
) -> str:
    tenant_id = _resolve_tenant_id(tenant)
    tenant_slug = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in tenant_id.lower()
    )
    tenant_slug = (tenant_slug.strip("_") or "public")[:64]
    day_bucket = datetime.now(UTC).strftime("%Y%m%d")

    storage_root = _resolve_documents_storage_root()
    target_dir = storage_root / tenant_slug / day_bucket
    target_dir.mkdir(parents=True, exist_ok=True)

    source_name = Path(sanitized_filename or "document")
    stem = source_name.stem[:120] or "document"
    extension = source_name.suffix
    stored_filename = f"{stem}_{uuid4().hex[:12]}{extension}"
    target_file = target_dir / stored_filename
    with open(target_file, "wb") as buffer:
        buffer.write(content)
    return str(target_file)


def _run_documents_cleanup_if_due() -> None:
    if not settings or not settings.documents_cleanup_enabled:
        return

    global _last_documents_cleanup_at
    now = datetime.now(UTC)
    interval_seconds = max(1, settings.documents_cleanup_interval_minutes) * 60

    with _documents_cleanup_lock:
        if _last_documents_cleanup_at is not None:
            elapsed = (now - _last_documents_cleanup_at).total_seconds()
            if elapsed < interval_seconds:
                return
        _last_documents_cleanup_at = now

    try:
        _cleanup_uploaded_documents_metadata(now)
        _cleanup_orphan_document_files(now)
    except Exception as exc:
        logger.warning("Document cleanup skipped due to error: %s", exc)


def _cleanup_uploaded_documents_metadata(now: datetime) -> None:
    _ensure_uploaded_documents_index_table()
    missing_retention = timedelta(
        days=max(1, settings.documents_missing_metadata_retention_days)
    )
    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, file_path, status, created_at
            FROM uploaded_documents_index
            """
        )
        rows = fetchall_dicts(cur)
        missing_ids: List[str] = []
        stale_ids: List[str] = []

        for row in rows:
            row_id = str(row.get("id") or "")
            if not row_id:
                continue

            status = str(row.get("status") or "processed")
            created_at = row.get("created_at")
            created_at_utc = (
                created_at.replace(tzinfo=UTC)
                if hasattr(created_at, "tzinfo") and created_at.tzinfo is None
                else created_at
            )
            if not isinstance(created_at_utc, datetime):
                created_at_utc = now

            file_path = str(row.get("file_path") or "")
            file_exists = False
            if file_path:
                try:
                    file_exists = _normalize_file_path(file_path).exists()
                except Exception:
                    file_exists = False

            if status == "processed" and not file_exists:
                missing_ids.append(row_id)

            if (
                status in {"missing", "deleted"}
                and (now - created_at_utc) >= missing_retention
            ):
                stale_ids.append(row_id)

        if missing_ids:
            cur.executemany(
                """
                UPDATE uploaded_documents_index
                SET status = 'missing', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                [(row_id,) for row_id in missing_ids],
            )

        if stale_ids:
            cur.executemany(
                "DELETE FROM uploaded_documents_index WHERE id = %s",
                [(row_id,) for row_id in stale_ids],
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _cleanup_orphan_document_files(now: datetime) -> None:
    _ensure_uploaded_documents_index_table()
    orphan_retention = timedelta(
        days=max(1, settings.documents_orphan_file_retention_days)
    )
    storage_root = _resolve_documents_storage_root()
    if not storage_root.exists():
        return

    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT file_path FROM uploaded_documents_index")
        referenced_paths = {
            _normalize_file_path(str(row.get("file_path"))).resolve()
            for row in fetchall_dicts(cur)
            if row.get("file_path")
        }
    finally:
        cur.close()
        conn.close()

    for file_path in storage_root.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            resolved_path = file_path.resolve()
        except Exception:
            continue

        if resolved_path in referenced_paths:
            continue

        modified_at = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
        if (now - modified_at) < orphan_retention:
            continue

        try:
            file_path.unlink()
        except OSError:
            continue


def _ensure_uploaded_documents_index_table() -> None:
    global _uploaded_documents_index_ready

    if _uploaded_documents_index_ready:
        return

    with _uploaded_documents_index_lock:
        if _uploaded_documents_index_ready:
            return

        conn = connect_db(settings.database_url)
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_documents_index (
                    id VARCHAR(64) PRIMARY KEY,
                    tenant_id VARCHAR(128) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    sanitized_filename VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    mime_type VARCHAR(255),
                    status VARCHAR(32) NOT NULL DEFAULT 'processed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_uploaded_documents_tenant_created
                ON uploaded_documents_index (tenant_id, created_at DESC)
                """
            )
            conn.commit()
            _uploaded_documents_index_ready = True
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()


def _record_uploaded_document(
    *,
    tenant: Optional[TenantContext],
    original_filename: str,
    sanitized_filename: str,
    file_path: str,
    size_bytes: int,
    mime_type: Optional[str] = None,
    status: str = "processing",
) -> str:
    """Record uploaded document metadata. Returns the generated doc_id."""
    _ensure_uploaded_documents_index_table()

    tenant_id = _resolve_tenant_id(tenant)
    doc_id = f"doc-{uuid4().hex[:16]}"
    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO uploaded_documents_index (
                id,
                tenant_id,
                original_filename,
                sanitized_filename,
                file_path,
                size_bytes,
                mime_type,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc_id,
                tenant_id,
                original_filename,
                sanitized_filename,
                file_path,
                size_bytes,
                mime_type,
                status,
            ),
        )
        conn.commit()
        return doc_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _update_document_status(doc_id: str, status: str) -> None:
    """Update the status of an uploaded document."""
    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE uploaded_documents_index SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, doc_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def _load_uploaded_documents(
    *, tenant: Optional[TenantContext]
) -> List[Dict[str, Any]]:
    _ensure_uploaded_documents_index_table()
    tenant_id = _resolve_tenant_id(tenant)
    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                id,
                original_filename,
                sanitized_filename,
                file_path,
                size_bytes,
                mime_type,
                status,
                created_at
            FROM uploaded_documents_index
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 200
            """,
            (tenant_id,),
        )
        rows = fetchall_dicts(cur)
    finally:
        cur.close()
        conn.close()

    docs: List[Dict[str, Any]] = []
    for row in rows:
        sanitized_name = str(
            row.get("sanitized_filename") or row.get("original_filename") or "document"
        )
        file_path = str(row.get("file_path") or "")
        suffix = Path(sanitized_name).suffix.lstrip(".").upper() or "FILE"
        created_at = row.get("created_at")
        status = str(row.get("status") or "processed")
        size_bytes = int(row.get("size_bytes") or 0)
        if file_path and status != "deleted":
            try:
                if not _normalize_file_path(file_path).exists():
                    status = "missing"
            except Exception:
                status = "missing"

        # Filter out unhealthy documents (missing, deleted, or zero-size)
        if status not in ("processed", "processing") or size_bytes <= 0:
            continue

        docs.append(
            {
                "id": row.get("id"),
                "name": sanitized_name,
                "type": suffix,
                "size": size_bytes,
                "uploaded_at": (
                    created_at.isoformat()
                    if hasattr(created_at, "isoformat")
                    else str(created_at or "")
                ),
                "status": status,
                "original_filename": row.get("original_filename"),
                "file_path": file_path,
                "mime_type": row.get("mime_type"),
                "source": "uploaded_index",
            }
        )

    # Merge with vectorstore-indexed documents so pre-loaded seed docs
    # remain visible even after a user uploads new files.
    default_tenant_id = (
        settings.default_tenant_id
        if settings and settings.default_tenant_id
        else "public"
    )
    if tenant_id == default_tenant_id:
        uploaded_names = {d["name"].lower() for d in docs}
        for indexed_doc in _load_indexed_documents_fallback(limit=200):
            if indexed_doc["name"].lower() not in uploaded_names:
                docs.append(indexed_doc)

    return docs


def _load_indexed_documents_fallback(*, limit: int = 200) -> List[Dict[str, Any]]:
    conn = connect_db(settings.database_url)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, filename, filepath, chunk_count, created_at,
                   COALESCE(size_bytes, 0) AS size_bytes
            FROM documents
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (max(1, int(limit)),),
        )
        rows = fetchall_dicts(cur)
    except Exception as exc:
        logger.warning("Failed to load indexed documents fallback: %s", exc)
        return []
    finally:
        cur.close()
        conn.close()

    docs: List[Dict[str, Any]] = []
    for row in rows:
        filename = str(row.get("filename") or "document")
        file_path = str(row.get("filepath") or "")
        suffix = Path(filename).suffix.lstrip(".").upper() or "FILE"
        created_at = row.get("created_at")

        status = "processed"
        size_bytes = int(row.get("size_bytes") or 0)
        if file_path:
            try:
                normalized = _normalize_file_path(file_path)
                if normalized.exists():
                    disk_size = int(normalized.stat().st_size)
                    if disk_size > 0:
                        size_bytes = disk_size
                else:
                    status = "missing"
            except Exception:
                status = "missing"

        # Filter out unhealthy documents (missing or zero-size)
        if status != "processed" or size_bytes <= 0:
            continue

        docs.append(
            {
                "id": row.get("id"),
                "name": filename,
                "type": suffix,
                "size": size_bytes,
                "uploaded_at": (
                    created_at.isoformat()
                    if hasattr(created_at, "isoformat")
                    else str(created_at or "")
                ),
                "status": status,
                "original_filename": filename,
                "file_path": file_path,
                "chunk_count": int(row.get("chunk_count") or 0),
                "source": "vector_index",
            }
        )

    return docs


def get_rag_engine():
    global rag_engine
    if rag_engine is None:
        with _rag_lock:
            if rag_engine is None:
                from backend.services.rag_engine import SimpleRAG

                rag_engine = SimpleRAG(
                    use_hybrid_search=True,
                    use_reranker=True,
                    enable_feedback=settings.enable_feedback_system,
                )
    return rag_engine


def get_unified_orchestrator():
    global unified_orchestrator
    if unified_orchestrator is None:
        with _unified_lock:
            if unified_orchestrator is None:
                from backend.agents.unified_agent import (
                    get_unified_orchestrator as build_unified_orchestrator,
                )

                unified_orchestrator = build_unified_orchestrator()
    return unified_orchestrator


def get_code_executor():
    global code_executor
    if code_executor is None:
        with _executor_lock:
            if code_executor is None:
                from backend.services.code_executor import get_code_executor

                code_executor = get_code_executor()
    return code_executor


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Security: fail fast if auth is required but JWT secret is missing
    if settings.require_user_auth and not settings.auth_jwt_secret:
        raise RuntimeError(
            "REQUIRE_USER_AUTH is enabled but AUTH_JWT_SECRET is not configured. "
            "Set AUTH_JWT_SECRET in your .env file."
        )

    try:
        from backend.init_database import init_database

        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:  # pragma: no cover - defensive startup guard
        logger.error(f"Failed to initialize database: {e}")

    try:
        from backend.api.intent_classification_routes import initialize_intent_routes

        await initialize_intent_routes()
    except Exception as e:
        logger.error(f"Failed to initialize intent workflow: {e}")

    # Pre-warm OCR model to eliminate cold start on first upload
    try:
        from backend.services.document_processing import get_ocr_processor

        ocr = get_ocr_processor()
        if ocr is not None:
            logger.info("OCR model pre-warmed (lang=%s)", ocr.lang)
    except Exception as e:
        logger.warning("OCR pre-warming failed (non-critical): %s", e)

    # Pre-warm Langfuse client (runs auth_check once, populates singleton)
    try:
        from backend.observability.langfuse_client import is_enabled

        if is_enabled():
            logger.info("Langfuse observability ready")
    except Exception as e:
        logger.warning("Langfuse pre-warm failed (non-critical): %s", e)

    # Pre-warm E2B sandbox to eliminate first-click flakiness.
    # E2BExecutionProvider.health() offloads the sync Sandbox.create() to a
    # worker thread internally (see e2b_provider.py:_health_sync), so awaiting
    # it here does not block the event loop. wait_for enforces a hard 15s
    # budget so a stalled network cannot hang startup.
    #
    # Fires when provider == "e2b" OR when auto mode has E2B wired as the
    # cloud fallback. Auto+E2B is a legitimate deployment shape where the
    # first docker-fail fallback hits a cold E2B sandbox, so the warmup
    # matters there too.
    _provider_setting = (settings.code_execution_provider or "").strip().lower()
    _e2b_prewarm_needed = _provider_setting == "e2b" or (
        _provider_setting == "auto"
        and getattr(settings, "enable_e2b_code_execution", False)
    )
    if _e2b_prewarm_needed:
        try:
            import asyncio as _asyncio

            from backend.services.code_executor import get_code_execution_manager

            manager = get_code_execution_manager()
            if manager is not None and manager.cloud_provider is not None:
                health = await _asyncio.wait_for(
                    manager.cloud_provider.health(), timeout=15.0
                )
                if health.get("healthy"):
                    logger.info("E2B sandbox pre-warmed")
                else:
                    logger.warning(
                        "E2B pre-warm health check unhealthy: %s",
                        health.get("status", "unknown"),
                    )
        except TimeoutError:
            logger.warning(
                "E2B pre-warm timed out after 15s (non-critical); "
                "first request will pay cold-start cost"
            )
        except Exception as e:
            logger.warning("E2B pre-warm failed (non-critical): %s", e)

    yield

    # Flush pending Langfuse traces on shutdown so nothing gets dropped
    try:
        from backend.observability.langfuse_client import shutdown as lf_shutdown

        lf_shutdown()
    except Exception as e:
        logger.debug("Langfuse shutdown error (non-critical): %s", e)


app = FastAPI(
    title="Luncheon AI Flow - Enhanced RAG & Code Analysis",
    description=(
        "Enterprise API for RAG, workflow orchestration, code execution, "
        "and data analysis."
    ),
    version="2.0.0",
    lifespan=lifespan,
    dependencies=[Depends(secure_endpoint)],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3123", "http://127.0.0.1:3123"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
if settings and settings.enable_metrics:
    setup_metrics(app)

# Register API routers
app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
app.include_router(
    document_management_router, prefix="/api/v1", tags=["document-management"]
)
app.include_router(enhanced_query_router, prefix="/api/v1", tags=["enhanced-query"])
app.include_router(auth_router)
app.include_router(cost_estimation_router)
app.include_router(llm_dispatch_router)  # llm_dispatch_routes has no prefix
app.include_router(llm_cost_router)  # llm_cost_routes has no prefix
app.include_router(demo_mode_router)
# prompt_routes already has prefix "/api/prompts", avoid double-prefixing to "/api/v1/api/prompts".
app.include_router(prompt_router, tags=["prompts"])  # P0: Prompt management routes
app.include_router(workflow_query_router)
app.include_router(intent_router)  # Intent classification + capabilities API

# RAG engine uses lazy loading for initialization


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=2048)
    top_k: int = Field(default=3, ge=1, le=20)
    data_file: Optional[str] = Field(default=None, max_length=512)

    @field_validator("question", mode="before")
    @classmethod
    def _sanitize_question(cls, value: str) -> str:
        return sanitize_text(value, field_name="question", max_length=2048)

    @field_validator("data_file", mode="before")
    @classmethod
    def _sanitize_data_file(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "data_file") if value else value


class CodeExecutionRequest(BaseModel):
    code: str
    data_files: Optional[List[str]] = None
    timeout: Optional[int] = Field(default=None, ge=1, le=900)

    @field_validator("data_files", mode="before")
    @classmethod
    def _sanitize_data_files(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return [sanitize_identifier(item, "data_files") for item in value if item]

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("code cannot be empty")
        if len(value) > 20000:
            raise ValueError("code exceeds max length of 20000 characters")
        return value


class DataAnalysisRequest(BaseModel):
    data_file: str
    analysis_type: str = Field(default="eda", max_length=64)
    target_column: Optional[str] = None
    columns: Optional[List[str]] = None
    instruction: Optional[str] = Field(default=None, max_length=2048)
    generate_visualization: bool = False
    chart_type: str = Field(default="line", max_length=64)

    @field_validator("data_file", mode="before")
    @classmethod
    def _sanitize_data_file(cls, value: str) -> str:
        return sanitize_text(value, field_name="data_file", max_length=1024)

    @field_validator("target_column", mode="before")
    @classmethod
    def _sanitize_target_column(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "target_column") if value else value

    @field_validator("columns", mode="before")
    @classmethod
    def _sanitize_columns(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return [sanitize_identifier(item, "columns") for item in value if item]

    @field_validator("analysis_type", mode="before")
    @classmethod
    def _sanitize_analysis_type(cls, value: str) -> str:
        return sanitize_identifier(value, "analysis_type", max_length=64)

    @field_validator("instruction", mode="before")
    @classmethod
    def _sanitize_instruction(cls, value: Optional[str]) -> Optional[str]:
        return (
            sanitize_text(value, field_name="instruction", max_length=2048)
            if value
            else value
        )


class VisualizationRequest(BaseModel):
    data_file: str
    chart_type: str = Field(default="line", max_length=64)
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=256)
    instruction: Optional[str] = Field(default=None, max_length=2048)
    save_format: str = "png"
    interactive: bool = False

    @field_validator("data_file", mode="before")
    @classmethod
    def _sanitize_viz_data_file(cls, value: str) -> str:
        return sanitize_text(value, field_name="data_file", max_length=1024)

    @field_validator("x_column", "y_column", "color_column", mode="before")
    @classmethod
    def _sanitize_viz_columns(
        cls, value: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        return sanitize_identifier(value, info.field_name) if value else value

    @field_validator("save_format", mode="before")
    @classmethod
    def _sanitize_save_format(cls, value: str) -> str:
        return sanitize_identifier(value, "save_format", max_length=16)

    @field_validator("chart_type", mode="before")
    @classmethod
    def _sanitize_chart_type(cls, value: str) -> str:
        return sanitize_identifier(value, "chart_type", max_length=64)

    @field_validator("title", mode="before")
    @classmethod
    def _sanitize_title(cls, value: Optional[str]) -> Optional[str]:
        return (
            sanitize_text(value, field_name="title", max_length=256) if value else value
        )

    @field_validator("instruction", mode="before")
    @classmethod
    def _sanitize_instruction(cls, value: Optional[str]) -> Optional[str]:
        return (
            sanitize_text(value, field_name="instruction", max_length=2048)
            if value
            else value
        )


def get_memory_usage() -> float:
    """Return current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)


def _resolve_data_file_for_analysis(data_file: str) -> str:
    """Resolve uploaded data file path while preventing unsafe filesystem access."""
    candidate = Path(data_file).expanduser()
    tmp_root = Path(os.getenv("TMPDIR", "/tmp")).resolve()
    managed_root = Path(TEMP_DATA_ROOT).resolve()

    if candidate.is_absolute():
        resolved = candidate.resolve()
        in_managed_root = resolved.is_relative_to(managed_root)
        in_uploaded_tmp_dir = resolved.is_relative_to(
            tmp_root
        ) and resolved.parent.name.startswith("luncheon_data_")
        if not (in_managed_root or in_uploaded_tmp_dir):
            raise HTTPException(
                status_code=400,
                detail="data_file path is outside allowed upload locations.",
            )
        if not resolved.exists():
            raise HTTPException(status_code=400, detail="data_file does not exist.")
        return str(resolved)

    file_name = sanitize_identifier(data_file, "data_file")
    candidates = [managed_root / file_name, tmp_root / file_name]
    for path in candidates:
        if path.exists():
            return str(path.resolve())

    uploaded_tmp_candidates = sorted(
        tmp_root.glob(f"luncheon_data_*/{file_name}"),
        key=lambda item: item.stat().st_mtime if item.exists() else 0,
        reverse=True,
    )
    for path in uploaded_tmp_candidates:
        if path.exists():
            return str(path.resolve())

    return file_name


@app.get("/api/v1/health")
@app.get("/health")
async def health(tenant: TenantContext = Depends(get_current_tenant)):
    """Service health check endpoint."""
    execution_health: Dict[str, Any] = {
        "healthy": code_executor is not None,
        "mode": getattr(settings, "code_execution_provider", "docker"),
        "selected_provider": "docker",
        "providers": {"docker": {"healthy": code_executor is not None}},
    }
    try:
        from backend.services.code_executor import get_code_execution_manager

        manager = get_code_execution_manager()
        if manager is not None and hasattr(manager, "health_snapshot"):
            execution_health = manager.health_snapshot(
                mode=getattr(settings, "code_execution_provider", "docker")
            )
    except Exception as exc:
        logger.warning("Unable to inspect code execution health: %s", exc)

    embedding_health: Dict[str, Any] = {
        "ready": False,
        "backend": "unknown",
        "fallback_active": True,
        "reason": "unavailable",
    }
    try:
        from backend.services.core.embedder import embedding_backend_status

        embedding_health = embedding_backend_status()
    except Exception as exc:
        logger.warning("Unable to inspect embedding backend health: %s", exc)

    providers = execution_health.get("providers", {})
    docker_state = providers.get("docker", {}) if isinstance(providers, dict) else {}

    return {
        "status": "ok",
        "memory_usage_mb": get_memory_usage(),
        "docker_available": bool(docker_state.get("healthy", False)),
        "code_execution_available": bool(execution_health.get("healthy", False)),
        "code_execution": execution_health,
        "embedding": embedding_health,
        "version": "1.0.0",
        "tenant": tenant.tenant_id if tenant else None,
    }


@app.get("/api/v1/environment")
@app.get("/environment")
async def get_environment(tenant: TenantContext = Depends(get_current_tenant)):
    """Return execution environment capabilities."""
    try:
        from backend.tools.code_execution import get_execution_environment_info

        info = get_execution_environment_info.invoke({})
        log_audit(
            action="environment.inspect",
            tenant=tenant,
            status="success",
            detail={"keys": list(info.keys())},
        )
        return info
    except Exception as e:
        log_audit(
            action="environment.inspect",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        logger.exception("Environment inspect failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@app.post("/api/v1/documents/upload")
@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """Upload a user document and store a sanitized temporary copy."""
    try:
        content, safe_name = await validate_and_buffer_upload(
            file,
            allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        file_path = _persist_uploaded_document_file(
            content=content,
            sanitized_filename=safe_name,
            tenant=tenant,
        )

        # Record metadata with status='processing', get doc_id immediately
        try:
            doc_id = _record_uploaded_document(
                tenant=tenant,
                original_filename=file.filename or safe_name,
                sanitized_filename=safe_name,
                file_path=file_path,
                size_bytes=len(content),
                mime_type=file.content_type,
                status="processing",
            )
        except Exception as exc:
            try:
                os.unlink(file_path)
            except OSError:
                pass
            logger.error("Failed to persist uploaded document metadata: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Document upload failed: metadata persistence error",
            ) from exc

        # Create progress tracker for SSE streaming
        from backend.services.document_processing.progress_tracker import (
            PipelineProgressTracker,
        )

        tracker = PipelineProgressTracker(doc_id)

        # Auto-vectorize in background: extract → chunk → embed → store
        def _vectorize_sync(
            _file_path: str,
            _safe_name: str,
            _content_len: int,
            _doc_id: str,
            _tracker: PipelineProgressTracker,
        ) -> None:
            """Synchronous vectorization with progress tracking."""
            import time as _time

            from backend.services.core.chunker import chunk_text
            from backend.services.core.embedder import embed_texts
            from backend.services.core.vectorstore import VectorStore
            from backend.services.document_processing.document_extractor import (
                DocumentExtractor,
            )

            try:
                t_total = _time.time()

                # Stage 1: Extract
                _tracker.update("extract", "running", 0.0, "Starting text extraction...")
                t0 = _time.time()
                extractor = DocumentExtractor(use_ocr=True)
                doc_content = extractor.extract(
                    _file_path, progress_callback=_tracker.update
                )
                _tracker.update(
                    "extract", "completed", 1.0,
                    f"Extracted text ({len(doc_content.text)} chars)",
                )

                text = doc_content.text
                if not text or len(text.strip()) <= 10:
                    _tracker.update("chunk", "skipped", 0.0, "Insufficient text")
                    _tracker.update("embed", "skipped", 0.0, "Insufficient text")
                    _tracker.update("store", "skipped", 0.0, "Insufficient text")
                    _update_document_status(_doc_id, "processed")
                    _tracker.complete()
                    return

                # Stage 2: OCR (handled inside extract, report skipped if no OCR)
                ocr_pages = doc_content.metadata.get("ocr_pages")
                if not ocr_pages:
                    _tracker.update("ocr", "skipped", 0.0, "Text PDF — no OCR needed")

                # Stage 3: Chunk
                _tracker.update("chunk", "running", 0.0, "Chunking text...")
                t0 = _time.time()
                chunks = chunk_text(
                    text,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
                chunk_contents = [c["content"] for c in chunks]
                t_chunk = _time.time() - t0

                if not chunk_contents:
                    _tracker.update("chunk", "completed", 1.0, "No chunks generated")
                    _tracker.update("embed", "skipped", 0.0, "No chunks to embed")
                    _tracker.update("store", "skipped", 0.0, "Nothing to store")
                    _update_document_status(_doc_id, "processed")
                    _tracker.complete()
                    return

                _tracker.update(
                    "chunk", "completed", 1.0,
                    f"Created {len(chunk_contents)} chunks ({t_chunk:.1f}s)",
                )

                # Stage 4: Embed
                _tracker.update(
                    "embed", "running", 0.0,
                    f"Embedding {len(chunk_contents)} chunks...",
                )
                t0 = _time.time()
                embeddings = embed_texts(chunk_contents)
                t_embed = _time.time() - t0
                _tracker.update(
                    "embed", "completed", 1.0,
                    f"Embedded {len(chunk_contents)} chunks ({t_embed:.1f}s)",
                )

                # Stage 5: Store
                _tracker.update(
                    "store", "running", 0.0,
                    f"Storing {len(chunk_contents)} chunks in database...",
                )
                vs = VectorStore()
                vector_doc_id = vs.store_document_with_chunks(
                    filename=_safe_name,
                    filepath=_file_path,
                    chunks=chunk_contents,
                    embeddings=embeddings,
                    size_bytes=_content_len,
                )
                _tracker.update(
                    "store", "completed", 1.0,
                    f"Stored {len(chunk_contents)} chunks",
                )

                # Update document status to processed
                _update_document_status(_doc_id, "processed")

                t_total_dur = _time.time() - t_total
                logger.info(
                    "Vectorization complete for %s: total=%.1fs (%d chunks, doc_id=%s)",
                    _safe_name,
                    t_total_dur,
                    len(chunk_contents),
                    vector_doc_id,
                )
                _tracker.complete()

            except Exception as exc:
                logger.warning(
                    "Auto-vectorization failed for %s: %s", _safe_name, exc
                )
                _update_document_status(_doc_id, "failed")
                _tracker.fail("unknown", str(exc))

        # Kick off async vectorization — don't await
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None, _vectorize_sync, file_path, safe_name, len(content), doc_id, tracker
        )

        # Return immediately with doc_id (status=processing)
        payload = {
            "status": "success",
            "filename": file.filename,
            "sanitized_filename": safe_name,
            "file_id": safe_name,
            "doc_id": doc_id,
            "size": len(content),
            "message": "Document uploaded. Processing started.",
        }

        log_audit(
            action="document.upload",
            tenant=tenant,
            status="success",
            detail={
                "filename": safe_name,
                "size": len(content),
                "doc_id": doc_id,
            },
        )
        _run_documents_cleanup_if_due()
        return payload
    except HTTPException:
        log_audit(
            action="document.upload",
            tenant=tenant,
            status="error",
            detail={"filename": file.filename, "reason": "validation_failed"},
        )
        raise
    except Exception as e:
        log_audit(
            action="document.upload",
            tenant=tenant,
            status="error",
            detail={"filename": file.filename, "error": str(e)},
        )
        raise HTTPException(
            status_code=500, detail="Document upload failed. Please try again."
        )


@app.get("/api/v1/documents")
@app.get("/documents")
async def list_documents(tenant: TenantContext = Depends(get_current_tenant)):
    """List uploaded documents for the current tenant from persistent metadata."""
    try:
        _run_documents_cleanup_if_due()
        docs = _load_uploaded_documents(tenant=tenant)
        log_audit(
            action="document.list",
            tenant=tenant,
            status="success",
            detail={"count": len(docs)},
        )
        return docs
    except Exception as exc:
        log_audit(
            action="document.list",
            tenant=tenant,
            status="error",
            detail={"error": str(exc)},
        )
        raise HTTPException(
            status_code=500, detail="Failed to list documents. Please try again."
        ) from exc


@app.post("/api/v1/data/upload")
@app.post("/data/upload")
async def upload_data_file(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """Upload a data file (CSV, Excel, JSON, or TXT)."""
    try:
        allowed_extensions = (".csv", ".xlsx", ".xls", ".json", ".txt")
        content, safe_name = await validate_and_buffer_upload(
            file,
            allowed_extensions=allowed_extensions,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        file_path = persist_temp_file(content, safe_name, prefix="luncheon_data")

        payload = {
            "status": "success",
            "filename": file.filename,
            "file_id": safe_name,
            "sanitized_filename": safe_name,
            "size": len(content),
            "file_type": os.path.splitext(file.filename)[1].lower(),
            "message": "Data file uploaded successfully.",
        }
        log_audit(
            action="data.upload",
            tenant=tenant,
            status="success",
            detail={"filename": safe_name, "size": len(content)},
        )
        return payload
    except HTTPException:
        log_audit(
            action="data.upload",
            tenant=tenant,
            status="error",
            detail={"filename": file.filename, "reason": "validation_failed"},
        )
        raise
    except Exception as e:
        log_audit(
            action="data.upload",
            tenant=tenant,
            status="error",
            detail={"filename": file.filename, "error": str(e)},
        )
        raise HTTPException(
            status_code=500, detail="Data upload failed. Please try again."
        )


@app.post("/api/v1/rag/query")
@app.post("/rag/query")
async def rag_query(
    request: QueryRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """Run a RAG query and return answer plus retrieval metadata."""
    try:
        ensure_rag_english_query(request.question, field="question")

        rag = get_rag_engine()
        cache_hit = query_cache.get(
            tenant.tenant_id if tenant else settings.default_tenant_id,
            request.question,
            request.top_k,
        )
        if cache_hit:
            log_audit(
                action="rag.query",
                tenant=tenant,
                status="success",
                detail={
                    "top_k": request.top_k,
                    "question_preview": request.question[:80],
                    "cache_hit": True,
                },
            )
            cache_hit["cache"] = "hit"
            return cache_hit
        enforce_memory_guard("rag.query")
        result = rag.query(
            request.question,
            request.top_k,
            session_id=tenant.tenant_id if tenant else settings.default_tenant_id,
            user_id=tenant.user_id if tenant else None,
        )
        if isinstance(result, dict):
            cached_payload = dict(result)
            cached_payload.pop("cache", None)
            query_cache.set(
                tenant.tenant_id if tenant else settings.default_tenant_id,
                request.question,
                request.top_k,
                cached_payload,
            )
        log_audit(
            action="rag.query",
            tenant=tenant,
            status="success",
            detail={
                "top_k": request.top_k,
                "question_preview": request.question[:80],
                "cache_hit": False,
            },
        )
        return result
    except HTTPException as exc:
        log_audit(
            action="rag.query",
            tenant=tenant,
            status="error",
            detail={"error": str(exc.detail)},
        )
        raise
    except Exception as e:
        logger.exception("RAG query failed: %s", e)
        log_audit(
            action="rag.query",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/unified/query")
@app.post("/unified/query")
async def unified_query(
    request: QueryRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """Run the unified orchestrator query pipeline."""
    try:
        orchestrator = get_unified_orchestrator()
        enforce_memory_guard("unified.query")
        result = orchestrator.process_request(
            question=request.question, data_file=request.data_file
        )
        is_success = not isinstance(result, dict) or bool(result.get("success", True))
        log_audit(
            action="unified.query",
            tenant=tenant,
            status="success" if is_success else "error",
            detail={
                "question_preview": request.question[:80],
                "success": is_success,
                "error": result.get("error") if isinstance(result, dict) else None,
            },
        )
        return result
    except Exception as e:
        logger.exception("Unified query failed: %s", e)
        log_audit(
            action="unified.query",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/code/execute")
@app.post("/code/execute")
async def execute_code(
    request: CodeExecutionRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """Execute user-provided code in the configured runtime."""
    try:
        from backend.tools.code_execution import code_execution_tool

        enforce_memory_guard("code.execute")
        result = code_execution_tool.invoke(
            {
                "code": request.code,
                "data_files": request.data_files,
                "timeout": request.timeout,
            }
        )
        log_audit(
            action="code.execute",
            tenant=tenant,
            status="success",
            detail={"timeout": request.timeout, "data_files": request.data_files},
        )
        return result
    except Exception as e:
        logger.exception("Code execution failed: %s", e)
        log_audit(
            action="code.execute",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/code/validate")
@app.post("/code/validate")
async def validate_code(
    request: Dict[str, str], tenant: TenantContext = Depends(get_current_tenant)
):
    """Validate code syntax and security constraints."""
    try:
        from backend.tools.code_execution import code_validation_tool

        result = code_validation_tool.invoke(request)
        log_audit(
            action="code.validate",
            tenant=tenant,
            status="success",
            detail={"has_code": "code" in request},
        )
        return result
    except Exception as e:
        logger.exception("Code validation failed: %s", e)
        log_audit(
            action="code.validate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/data/analyze")
@app.post("/data/analyze")
async def analyze_data(
    request: DataAnalysisRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """Run data analysis on an uploaded dataset."""
    try:
        from backend.tools.data_analysis import data_analysis_tool

        enforce_memory_guard("data.analyze")
        resolved_data_file = _resolve_data_file_for_analysis(request.data_file)
        result = data_analysis_tool.invoke(
            {
                "data_file": resolved_data_file,
                "analysis_type": request.analysis_type,
                "target_column": request.target_column,
                "columns": request.columns,
                "instruction": request.instruction,
            }
        )
        is_success = not isinstance(result, dict) or bool(result.get("success", True))

        # Optionally generate visualization alongside analysis
        viz_result = None
        if request.generate_visualization and is_success:
            try:
                from backend.tools.visualization import visualization_tool

                viz_result = visualization_tool.invoke(
                    {
                        "data_file": resolved_data_file,
                        "chart_type": request.chart_type,
                        "instruction": request.instruction,
                    }
                )
            except Exception as viz_err:
                logger.warning("Visualization generation failed: %s", viz_err)
                viz_result = {"error": str(viz_err)}

        log_audit(
            action="data.analyze",
            tenant=tenant,
            status="success" if is_success else "error",
            detail={
                "data_file": resolved_data_file,
                "analysis_type": request.analysis_type,
                "success": is_success,
                "generate_visualization": request.generate_visualization,
                "error": result.get("error") if isinstance(result, dict) else None,
            },
        )

        if viz_result is not None and isinstance(result, dict):
            result["visualization"] = viz_result

        return result
    except HTTPException as exc:
        log_audit(
            action="data.analyze",
            tenant=tenant,
            status="error",
            detail={"error": str(exc.detail)},
        )
        raise
    except Exception as e:
        logger.exception("Data analysis failed: %s", e)
        log_audit(
            action="data.analyze",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


# ---------------------------------------------------------------------------
# Data Analysis — SSE streaming progress
# ---------------------------------------------------------------------------

from backend.services.document_processing.progress_tracker import (
    PipelineProgressTracker,
)

_analysis_job_results: Dict[str, Any] = {}
_analysis_job_timestamps: Dict[str, float] = {}  # job_id → time.monotonic()
_ANALYSIS_JOB_TTL = 300  # 5 minutes — matches PipelineProgressTracker TTL


def _run_analysis_with_progress(
    job_id: str,
    data_file: str,
    analysis_type: str,
    target_column: Optional[str],
    columns: Optional[List[str]],
    instruction: Optional[str],
    generate_visualization: bool,
    chart_type: str,
) -> None:
    """Run unified analysis+viz pipeline, emitting 6-stage SSE progress events."""
    tracker = PipelineProgressTracker.get(job_id)
    if tracker is None:
        return

    current_stage = "file_parse"
    try:
        # Resolve file
        tracker.update("file_parse", "running", 0.05, "Resolving data file...")
        resolved = _resolve_data_file_for_analysis(data_file)
        tracker.update("file_parse", "completed", 0.10, f"File: {resolved}")

        # Use the unified DataAnalysisAgent pipeline with on_progress callback
        from backend.services.data_analysis.data_analysis_agent import (
            get_data_analysis_agent,
        )

        agent = get_data_analysis_agent()

        def on_progress(stage: str, status: str, progress: float, detail: str) -> None:
            nonlocal current_stage
            current_stage = stage
            tracker.update(stage, status, progress, detail)

        question = instruction or f"Run a concise {analysis_type} analysis."
        result = agent.analyze_query(
            question=question,
            data_file_path=resolved,
            on_progress=on_progress,
        )

        _analysis_job_results[job_id] = result
        tracker.update("done", "completed", 1.0, "Analysis complete")
        tracker.complete()
    except Exception as exc:
        logger.exception("Streaming analysis job %s failed: %s", job_id, exc)
        _analysis_job_results[job_id] = {"error": str(exc), "success": False}
        if tracker:
            tracker.fail(current_stage, str(exc))


@app.post("/api/v1/data/analyze/start")
async def start_analysis_job(
    request: DataAnalysisRequest,
    tenant: TenantContext = Depends(get_current_tenant),
):
    """Initiate a data analysis job — returns job_id for SSE streaming."""
    import asyncio as _aio
    import time as _time

    # TTL cleanup: remove stale job results older than 5 minutes
    now = _time.monotonic()
    stale = [k for k, ts in _analysis_job_timestamps.items() if now - ts > _ANALYSIS_JOB_TTL]
    for k in stale:
        _analysis_job_results.pop(k, None)
        _analysis_job_timestamps.pop(k, None)

    job_id = str(uuid4())
    _analysis_job_timestamps[job_id] = now
    PipelineProgressTracker(job_id)
    _aio.get_running_loop().run_in_executor(
        None,
        _run_analysis_with_progress,
        job_id,
        request.data_file,
        request.analysis_type,
        request.target_column,
        request.columns,
        request.instruction,
        request.generate_visualization,
        request.chart_type,
    )
    log_audit(
        action="data.analyze.start",
        tenant=tenant,
        status="accepted",
        detail={"job_id": job_id, "data_file": request.data_file},
    )
    return {"job_id": job_id}


@app.get("/api/v1/data/analyze/stream/{job_id}")
async def stream_analysis_progress(job_id: str):
    """Stream analysis pipeline progress via SSE."""
    import asyncio as _aio

    tracker = PipelineProgressTracker.get(job_id)

    async def event_generator():
        if tracker is None or tracker.async_queue is None:
            yield f"event: error\ndata: {_json.dumps({'error': 'Job not found', 'job_id': job_id})}\n\n"
            return
        try:
            while True:
                try:
                    event = await _aio.wait_for(tracker.async_queue.get(), timeout=30.0)
                except _aio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if event is None:
                    final = _analysis_job_results.pop(job_id, None)
                    if final is not None:
                        yield f"event: result\ndata: {_json.dumps(final, default=str)}\n\n"
                    return
                yield f"event: stage\ndata: {_json.dumps(event.to_dict())}\n\n"
        except _aio.CancelledError:
            return
        finally:
            tracker.close()

    return _StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class DataPreviewRequest(BaseModel):
    data_file: str

    @field_validator("data_file", mode="before")
    @classmethod
    def _sanitize_data_file(cls, value: str) -> str:
        return sanitize_text(value, field_name="data_file", max_length=1024)


@app.post("/api/v1/data/preview")
async def preview_data(
    request: DataPreviewRequest,
    tenant: TenantContext = Depends(get_current_tenant),
):
    """Return dataset metadata + first 5 rows for preview after upload."""
    import pandas as _pd

    resolved = _resolve_data_file_for_analysis(request.data_file)

    if not os.path.exists(resolved):
        raise HTTPException(status_code=404, detail="Data file not found. Upload a file first.")

    file_size = os.path.getsize(resolved)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit for preview.")

    from backend.services.data_analysis.data_analysis_agent import (
        get_data_analysis_agent,
    )

    agent = get_data_analysis_agent()
    metadata = agent._extract_dataset_info(resolved)
    if metadata.get("error"):
        raise HTTPException(status_code=400, detail=metadata["error"])

    # Load sample rows (first 5)
    try:
        if resolved.endswith((".xlsx", ".xls")):
            df = _pd.read_excel(resolved, nrows=5)
        else:
            df = _pd.read_csv(resolved, nrows=5)
        sample_rows = df.fillna("").to_dict(orient="records")
    except Exception as exc:
        logger.warning("Failed to load sample rows: %s", exc)
        sample_rows = []

    preview_columns = []
    for col in metadata.get("columns_info", []):
        pc = {"name": col["name"], "type": col["type"]}
        if sample_rows:
            pc["sample"] = str(sample_rows[0].get(col["name"], ""))
        preview_columns.append(pc)

    return {
        "metadata": metadata,
        "sample_rows": sample_rows,
        "preview_columns": preview_columns,
    }


@app.post("/api/v1/data/preprocess")
@app.post("/data/preprocess")
async def preprocess_data(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """Apply data preprocessing operations."""
    try:
        from backend.tools.data_analysis import data_preprocessing_tool

        enforce_memory_guard("data.preprocess")
        result = data_preprocessing_tool.invoke(request)
        log_audit(
            action="data.preprocess",
            tenant=tenant,
            status="success",
            detail={"operations": request.get("operations")},
        )
        return result
    except Exception as e:
        logger.exception("Data preprocessing failed: %s", e)
        log_audit(
            action="data.preprocess",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/visualization/generate")
@app.post("/visualization/generate")
async def generate_visualization(
    request: VisualizationRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """Generate a visualization from uploaded data."""
    try:
        from backend.tools.visualization import visualization_tool

        enforce_memory_guard("visualization.generate")
        resolved_data_file = _resolve_data_file_for_analysis(request.data_file)
        result = visualization_tool.invoke(
            {
                "data_file": resolved_data_file,
                "chart_type": request.chart_type,
                "x_column": request.x_column,
                "y_column": request.y_column,
                "color_column": request.color_column,
                "title": request.title,
                "instruction": request.instruction,
                "save_format": request.save_format,
                "interactive": request.interactive,
            }
        )
        log_audit(
            action="visualization.generate",
            tenant=tenant,
            status="success",
            detail={"chart_type": request.chart_type, "data_file": resolved_data_file},
        )
        return result
    except Exception as e:
        log_audit(
            action="visualization.generate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        logger.exception("Visualization generation failed: %s", e)
        raise HTTPException(
            status_code=500, detail="An internal error occurred. Please try again."
        )


@app.post("/api/v1/visualization/advanced")
@app.post("/visualization/advanced")
async def generate_advanced_visualization(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """Generate advanced visualizations using composite settings."""
    try:
        from backend.tools.visualization import advanced_visualization_tool

        enforce_memory_guard("visualization.advanced")
        result = advanced_visualization_tool.invoke(request)
        log_audit(
            action="visualization.advanced",
            tenant=tenant,
            status="success",
            detail={"viz_type": request.get("viz_type")},
        )
        return result
    except Exception as e:
        logger.exception("Advanced visualization failed: %s", e)
        log_audit(
            action="visualization.advanced",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.post("/api/v1/dashboard/generate")
@app.post("/dashboard/generate")
async def generate_dashboard(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """Generate dashboard artifacts for uploaded datasets."""
    try:
        from backend.tools.visualization import dashboard_generation_tool

        enforce_memory_guard("dashboard.generate")
        result = dashboard_generation_tool.invoke(request)
        log_audit(
            action="dashboard.generate",
            tenant=tenant,
            status="success",
            detail={"dashboard_type": request.get("dashboard_type")},
        )
        return result
    except Exception as e:
        logger.exception("Dashboard generation failed: %s", e)
        log_audit(
            action="dashboard.generate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again.",
        )


@app.get("/api/v1/files/visualizations/{filename}")
@app.get("/files/visualizations/{filename}")
async def get_visualization_file(
    filename: str, tenant: TenantContext = Depends(get_current_tenant)
):
    """Download a generated visualization file."""
    try:
        safe_name = os.path.basename(filename)
        if safe_name != filename:
            raise HTTPException(status_code=400, detail="Invalid file name.")

        file_path = os.path.join(TEMP_DATA_ROOT, safe_name)
        if os.path.exists(file_path):
            log_audit(
                action="files.retrieve",
                tenant=tenant,
                status="success",
                detail={"filename": safe_name},
            )
            return FileResponse(file_path)

        log_audit(
            action="files.retrieve",
            tenant=tenant,
            status="error",
            detail={"filename": safe_name, "reason": "not_found"},
        )
        raise HTTPException(status_code=404, detail="Visualization file not found.")
    except HTTPException:
        raise
    except Exception as e:
        log_audit(
            action="files.retrieve",
            tenant=tenant,
            status="error",
            detail={"filename": filename, "error": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve visualization. Please try again.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
