import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

import psutil
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.api.document_management_routes import router as document_management_router
from backend.api.enhanced_query_routes import router as enhanced_query_router

# 导入新的API路由
from backend.api.feedback_routes import router as feedback_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 检查环境变量
try:
    from backend.config import settings
except ImportError:
    settings = None

# 延迟导入服务模块，避免启动时的循环依赖
rag_engine = None
unified_orchestrator = None
code_executor = None


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
)

# 注册新的API路由
app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
app.include_router(
    document_management_router, prefix="/api/v1", tags=["document-management"]
)
app.include_router(enhanced_query_router, prefix="/api/v1", tags=["enhanced-query"])

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
    question: str
    top_k: int = 3
    data_file: Optional[str] = None


class CodeExecutionRequest(BaseModel):
    code: str
    data_files: Optional[List[str]] = None
    timeout: Optional[int] = None


class DataAnalysisRequest(BaseModel):
    data_file: str
    analysis_type: str = "eda"
    target_column: Optional[str] = None
    columns: Optional[List[str]] = None


class VisualizationRequest(BaseModel):
    data_file: str
    chart_type: str = "line"
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: Optional[str] = None
    save_format: str = "png"
    interactive: bool = False


def get_memory_usage() -> float:
    """获取当前进程内存使用(MB)"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "memory_usage_mb": get_memory_usage(),
        "docker_available": code_executor is not None,
        "version": "1.0.0",
    }


@app.get("/environment")
async def get_environment():
    """获取执行环境信息"""
    try:
        from backend.tools.code_execution import get_execution_environment_info

        return get_execution_environment_info.invoke({})
    except Exception as e:
        return {"error": str(e), "docker_available": False}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档文件"""
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="luncheon_docs_")
        file_path = os.path.join(temp_dir, file.filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "success",
            "filename": file.filename,
            "file_path": file_path,
            "size": os.path.getsize(file_path),
            "message": "文件上传成功",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.post("/data/upload")
async def upload_data_file(file: UploadFile = File(...)):
    """上传数据文件（CSV、Excel等）"""
    try:
        # 检查文件类型
        allowed_extensions = [".csv", ".xlsx", ".xls", ".json", ".txt"]
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}",
            )

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="luncheon_data_")
        file_path = os.path.join(temp_dir, file.filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "status": "success",
            "filename": file.filename,
            "file_path": file_path,
            "size": os.path.getsize(file_path),
            "file_type": file_ext,
            "message": "数据文件上传成功",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据文件上传失败: {str(e)}")


@app.post("/rag/query")
async def rag_query(request: QueryRequest):
    """RAG查询接口"""
    try:
        rag = get_rag_engine()  # 使用lazy loading获取RAG引擎
        result = rag.query(request.question, request.top_k)
        return result
    except Exception as e:
        return {"error": str(e), "question": request.question, "answer": "系统错误，请查看日志"}


@app.post("/unified/query")
async def unified_query(request: QueryRequest):
    """统一查询接口 - 融合RAG和代码分析"""
    try:
        result = unified_orchestrator.process_request(
            question=request.question, data_file=request.data_file
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "question": request.question,
            "intent": "unknown",
        }


@app.post("/code/execute")
async def execute_code(request: CodeExecutionRequest):
    """代码执行接口"""
    try:
        from backend.tools.code_execution import code_execution_tool

        result = code_execution_tool.invoke(
            {
                "code": request.code,
                "data_files": request.data_files,
                "timeout": request.timeout,
            }
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": str(e)}


@app.post("/code/validate")
async def validate_code(request: Dict[str, str]):
    """代码验证接口"""
    try:
        from backend.tools.code_execution import code_validation_tool

        result = code_validation_tool.invoke(request)
        return result
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "syntax_errors": [str(e)],
            "security_errors": [],
        }


@app.post("/data/analyze")
async def analyze_data(request: DataAnalysisRequest):
    """数据分析接口"""
    try:
        from backend.tools.data_analysis import data_analysis_tool

        result = data_analysis_tool.invoke(
            {
                "data_file": request.data_file,
                "analysis_type": request.analysis_type,
                "target_column": request.target_column,
                "columns": request.columns,
            }
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "analysis_type": request.analysis_type,
        }


@app.post("/data/preprocess")
async def preprocess_data(request: Dict[str, Any]):
    """数据预处理接口"""
    try:
        from backend.tools.data_analysis import data_preprocessing_tool

        result = data_preprocessing_tool.invoke(request)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operations_applied": request.get("operations", []),
        }


@app.post("/visualization/generate")
async def generate_visualization(request: VisualizationRequest):
    """可视化生成接口"""
    try:
        from backend.tools.visualization import visualization_tool

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
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "chart_type": request.chart_type}


@app.post("/visualization/advanced")
async def generate_advanced_visualization(request: Dict[str, Any]):
    """高级可视化接口"""
    try:
        from backend.tools.visualization import advanced_visualization_tool

        result = advanced_visualization_tool.invoke(request)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "viz_type": request.get("viz_type", "unknown"),
        }


@app.post("/dashboard/generate")
async def generate_dashboard(request: Dict[str, Any]):
    """仪表板生成接口"""
    try:
        from backend.tools.visualization import dashboard_generation_tool

        result = dashboard_generation_tool.invoke(request)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "dashboard_type": request.get("dashboard_type", "unknown"),
        }


@app.get("/files/visualizations/{filename}")
async def get_visualization_file(filename: str):
    """获取可视化文件"""
    try:
        # 在实际实现中，这里应该从安全的位置提供文件
        file_path = f"/tmp/luncheon_data/{filename}"
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件获取失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
