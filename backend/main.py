from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import uvicorn
import psutil
import os

from backend.services.rag_engine import SimpleRAG

app = FastAPI(title="RAG Feasibility Test")

# 初始化RAG引擎
rag_engine = SimpleRAG()


class QueryRequest(BaseModel):
    question: str
    top_k: int = 3


def get_memory_usage() -> float:
    """获取当前进程内存使用(MB)"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "memory_usage_mb": get_memory_usage()}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传单个文档（仅PDF和TXT）"""
    # 保存文件 → 返回文档ID
    # Week 1-2: 简单实现，完整实现在Day 5-7
    return {
        "status": "success",
        "filename": file.filename,
        "message": "文件上传功能将在Day 5-7实现"
    }


@app.post("/rag/query")
async def rag_query(request: QueryRequest):
    """RAG查询接口"""
    try:
        result = rag_engine.query(request.question, request.top_k)
        return result
    except Exception as e:
        # Week 1-2阶段：简单错误处理即可
        return {
            "error": str(e),
            "question": request.question,
            "answer": "系统错误，请查看日志"
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
