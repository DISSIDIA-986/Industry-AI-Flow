import logging
import os
from typing import Any, Dict, List, Optional

import psutil
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, validator

from backend.api.document_management_routes import router as document_management_router
from backend.api.enhanced_query_routes import router as enhanced_query_router

# 导入新的API路由
from backend.api.feedback_routes import router as feedback_router
from backend.api.llm_cost_routes import router as llm_cost_router
from backend.api.llm_dispatch_routes import router as llm_dispatch_router
from backend.api.prompt_routes import router as prompt_router  # P0修复：注册Prompt路由
from backend.middleware.error_handler import register_error_handlers
from backend.observability.logging_config import configure_logging
from backend.observability.metrics import setup_metrics
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.security.memory_guard import memory_guard
from backend.security.sanitizer import sanitize_identifier, sanitize_text
from backend.services.audit_logger import audit_logger
from backend.services.cache.query_cache import query_cache
from backend.services.security import persist_temp_file, validate_and_buffer_upload

# 配置日志
configure_logging()
logger = logging.getLogger(__name__)

# 检查环境变量
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

# 延迟导入服务模块，避免启动时的循环依赖
rag_engine = None
unified_orchestrator = None
code_executor = None


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


def get_rag_engine():
    global rag_engine
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
        from backend.agents.unified_agent import unified_orchestrator

        unified_orchestrator = unified_orchestrator()
    return unified_orchestrator


def get_code_executor():
    global code_executor
    if code_executor is None:
        from backend.services.code_executor import code_executor

        code_executor = code_executor()
    return code_executor


app = FastAPI(
    title="Luncheon AI Flow - Enhanced RAG & Code Analysis",
    description="融合知识问答、用户反馈、文档管理和数据分析能力的智能系统",
    version="2.0.0",
    dependencies=[Depends(secure_endpoint)],
)
register_error_handlers(app)
if settings and settings.enable_metrics:
    setup_metrics(app)

# 注册新的API路由
app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
app.include_router(
    document_management_router, prefix="/api/v1", tags=["document-management"]
)
app.include_router(enhanced_query_router, prefix="/api/v1", tags=["enhanced-query"])
app.include_router(llm_dispatch_router)  # llm_dispatch_routes已包含prefix
app.include_router(llm_cost_router)  # llm_cost_routes已包含prefix
app.include_router(prompt_router, prefix="/api/v1", tags=["prompts"])  # P0修复：注册Prompt路由

# RAG引擎将通过lazy loading初始化
# rag_engine = SimpleRAG()  # 移除直接初始化，使用lazy loading


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        # 初始化数据库
        from backend.init_database import init_database

        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # 不阻止应用启动，但记录错误


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=2048)
    top_k: int = Field(default=3, ge=1, le=20)
    data_file: Optional[str] = Field(default=None, max_length=512)

    @validator("question", pre=True, allow_reuse=True)
    def _sanitize_question(cls, value: str) -> str:
        return sanitize_text(value, field_name="question", max_length=2048)

    @validator("data_file", pre=True, allow_reuse=True)
    def _sanitize_data_file(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "data_file") if value else value


class CodeExecutionRequest(BaseModel):
    code: str
    data_files: Optional[List[str]] = None
    timeout: Optional[int] = Field(default=None, ge=1, le=900)

    @validator("data_files", each_item=True, pre=True, allow_reuse=True)
    def _sanitize_data_files(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "data_files") if value else value

    @validator("code", pre=True, allow_reuse=True)
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

    @validator("data_file", pre=True, allow_reuse=True)
    def _sanitize_data_file(cls, value: str) -> str:
        return sanitize_identifier(value, "data_file")

    @validator("target_column", pre=True, allow_reuse=True)
    def _sanitize_target_column(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "target_column") if value else value

    @validator("columns", each_item=True, pre=True, allow_reuse=True)
    def _sanitize_columns(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_identifier(value, "columns") if value else value

    @validator("analysis_type", pre=True, allow_reuse=True)
    def _sanitize_analysis_type(cls, value: str) -> str:
        return sanitize_identifier(value, "analysis_type", max_length=64)


class VisualizationRequest(BaseModel):
    data_file: str
    chart_type: str = Field(default="line", max_length=64)
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=256)
    save_format: str = "png"
    interactive: bool = False

    @validator("data_file", pre=True, allow_reuse=True)
    def _sanitize_viz_data_file(cls, value: str) -> str:
        return sanitize_identifier(value, "data_file")

    @validator("x_column", "y_column", "color_column", pre=True, allow_reuse=True)
    def _sanitize_viz_columns(cls, value: Optional[str], field) -> Optional[str]:
        return sanitize_identifier(value, field.name) if value else value

    @validator("save_format", pre=True, allow_reuse=True)
    def _sanitize_save_format(cls, value: str) -> str:
        return sanitize_identifier(value, "save_format", max_length=16)

    @validator("chart_type", pre=True, allow_reuse=True)
    def _sanitize_chart_type(cls, value: str) -> str:
        return sanitize_identifier(value, "chart_type", max_length=64)

    @validator("title", pre=True, allow_reuse=True)
    def _sanitize_title(cls, value: Optional[str]) -> Optional[str]:
        return (
            sanitize_text(value, field_name="title", max_length=256) if value else value
        )


def get_memory_usage() -> float:
    """获取当前进程内存使用(MB)"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)


@app.get("/health")
async def health(tenant: TenantContext = Depends(get_current_tenant)):
    """健康检查"""
    return {
        "status": "ok",
        "memory_usage_mb": get_memory_usage(),
        "docker_available": code_executor is not None,
        "version": "1.0.0",
        "tenant": tenant.tenant_id if tenant else None,
    }


@app.get("/environment")
async def get_environment(tenant: TenantContext = Depends(get_current_tenant)):
    """获取执行环境信息"""
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
        return {"error": str(e), "docker_available": False}


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """上传文档文件"""
    try:
        content, safe_name = await validate_and_buffer_upload(
            file,
            allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS,
            max_bytes=MAX_UPLOAD_BYTES,
        )
        file_path = persist_temp_file(content, safe_name, prefix="luncheon_docs")

        payload = {
            "status": "success",
            "filename": file.filename,
            "sanitized_filename": safe_name,
            "file_path": file_path,
            "size": len(content),
            "message": "文件上传成功",
        }
        log_audit(
            action="document.upload",
            tenant=tenant,
            status="success",
            detail={"filename": safe_name, "size": len(content)},
        )
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
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.post("/data/upload")
async def upload_data_file(
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(get_current_tenant),
):
    """上传数据文件（CSV、Excel等）"""
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
            "file_path": file_path,
            "sanitized_filename": safe_name,
            "size": len(content),
            "file_type": os.path.splitext(file.filename)[1].lower(),
            "message": "数据文件上传成功",
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
        raise HTTPException(status_code=500, detail=f"数据文件上传失败: {str(e)}")


@app.post("/rag/query")
async def rag_query(
    request: QueryRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """RAG查询接口"""
    try:
        rag = get_rag_engine()  # 使用lazy loading获取RAG引擎
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
        result = rag.query(request.question, request.top_k)
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
    except Exception as e:
        log_audit(
            action="rag.query",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {"error": str(e), "question": request.question, "answer": "系统错误，请查看日志"}


@app.post("/unified/query")
async def unified_query(
    request: QueryRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """统一查询接口 - 融合RAG和代码分析"""
    try:
        orchestrator = get_unified_orchestrator()
        enforce_memory_guard("unified.query")
        result = orchestrator.process_request(
            question=request.question, data_file=request.data_file
        )
        log_audit(
            action="unified.query",
            tenant=tenant,
            status="success",
            detail={"question_preview": request.question[:80]},
        )
        return result
    except Exception as e:
        log_audit(
            action="unified.query",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "success": False,
            "error": str(e),
            "question": request.question,
            "intent": "unknown",
        }


@app.post("/code/execute")
async def execute_code(
    request: CodeExecutionRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """代码执行接口"""
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
        log_audit(
            action="code.execute",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {"success": False, "error": str(e), "stdout": "", "stderr": str(e)}


@app.post("/code/validate")
async def validate_code(
    request: Dict[str, str], tenant: TenantContext = Depends(get_current_tenant)
):
    """代码验证接口"""
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
        log_audit(
            action="code.validate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "valid": False,
            "error": str(e),
            "syntax_errors": [str(e)],
            "security_errors": [],
        }


@app.post("/data/analyze")
async def analyze_data(
    request: DataAnalysisRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """数据分析接口"""
    try:
        from backend.tools.data_analysis import data_analysis_tool

        enforce_memory_guard("data.analyze")
        result = data_analysis_tool.invoke(
            {
                "data_file": request.data_file,
                "analysis_type": request.analysis_type,
                "target_column": request.target_column,
                "columns": request.columns,
            }
        )
        log_audit(
            action="data.analyze",
            tenant=tenant,
            status="success",
            detail={
                "data_file": request.data_file,
                "analysis_type": request.analysis_type,
            },
        )
        return result
    except Exception as e:
        log_audit(
            action="data.analyze",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "success": False,
            "error": str(e),
            "analysis_type": request.analysis_type,
        }


@app.post("/data/preprocess")
async def preprocess_data(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """数据预处理接口"""
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
        log_audit(
            action="data.preprocess",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "success": False,
            "error": str(e),
            "operations_applied": request.get("operations", []),
        }


@app.post("/visualization/generate")
async def generate_visualization(
    request: VisualizationRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """可视化生成接口"""
    try:
        from backend.tools.visualization import visualization_tool

        enforce_memory_guard("visualization.generate")
        result = visualization_tool.invoke(
            {
                "data_file": request.data_file,
                "chart_type": request.chart_type,
                "x_column": request.x_column,
                "y_column": request.y_column,
                "color_column": request.color_column,
                "title": request.title,
                "save_format": request.save_format,
                "interactive": request.interactive,
            }
        )
        log_audit(
            action="visualization.generate",
            tenant=tenant,
            status="success",
            detail={"chart_type": request.chart_type, "data_file": request.data_file},
        )
        return result
    except Exception as e:
        log_audit(
            action="visualization.generate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {"success": False, "error": str(e), "chart_type": request.chart_type}


@app.post("/visualization/advanced")
async def generate_advanced_visualization(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """高级可视化接口"""
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
        log_audit(
            action="visualization.advanced",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "success": False,
            "error": str(e),
            "viz_type": request.get("viz_type", "unknown"),
        }


@app.post("/dashboard/generate")
async def generate_dashboard(
    request: Dict[str, Any], tenant: TenantContext = Depends(get_current_tenant)
):
    """仪表板生成接口"""
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
        log_audit(
            action="dashboard.generate",
            tenant=tenant,
            status="error",
            detail={"error": str(e)},
        )
        return {
            "success": False,
            "error": str(e),
            "dashboard_type": request.get("dashboard_type", "unknown"),
        }


@app.get("/files/visualizations/{filename}")
async def get_visualization_file(
    filename: str, tenant: TenantContext = Depends(get_current_tenant)
):
    """获取可视化文件"""
    try:
        safe_name = os.path.basename(filename)
        if safe_name != filename:
            raise HTTPException(status_code=400, detail="非法的文件名")

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
        raise HTTPException(status_code=404, detail="文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        log_audit(
            action="files.retrieve",
            tenant=tenant,
            status="error",
            detail={"filename": filename, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"文件获取失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
