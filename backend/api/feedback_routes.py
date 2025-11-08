"""
反馈系统API路由
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.services.rag_engine import SimpleRAG
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# 全局RAG实例
rag_instance = None

def get_rag_instance():
    """获取RAG实例"""
    global rag_instance
    if rag_instance is None:
        rag_instance = SimpleRAG(enable_feedback=settings.enable_feedback_system)
    return rag_instance


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    query_id: str
    question: str
    answer: str
    feedback_type: str  # "helpful", "not_helpful", "partially_helpful"
    user_comment: Optional[str] = None
    retrieved_chunks: Optional[List[Dict]] = None
    feedback_weight: float = 1.0


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    success: bool
    message: str


class FeedbackStatisticsResponse(BaseModel):
    """反馈统计响应模型"""
    total_queries: int
    helpful_count: int
    not_helpful_count: int
    partially_helpful_count: int
    success_rate: float
    avg_feedback_weight: float


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    提交用户反馈

    Args:
        request: 反馈请求

    Returns:
        反馈提交结果
    """
    try:
        if not settings.enable_feedback_system:
            raise HTTPException(status_code=403, detail="Feedback system is disabled")

        rag = get_rag_instance()
        success = rag.submit_feedback(
            query_id=request.query_id,
            question=request.question,
            answer=request.answer,
            feedback_type=request.feedback_type,
            user_comment=request.user_comment,
            retrieved_chunks=request.retrieved_chunks,
            feedback_weight=request.feedback_weight
        )

        if success:
            logger.info(f"Feedback submitted successfully for query {request.query_id}")
            return FeedbackResponse(success=True, message="Feedback submitted successfully")
        else:
            logger.warning(f"Failed to submit feedback for query {request.query_id}")
            return FeedbackResponse(success=False, message="Failed to submit feedback")

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/feedback/statistics", response_model=FeedbackStatisticsResponse)
async def get_feedback_statistics(days: int = 7):
    """
    获取反馈统计信息

    Args:
        days: 统计天数（默认7天）

    Returns:
        反馈统计信息
    """
    try:
        if not settings.enable_feedback_system:
            raise HTTPException(status_code=403, detail="Feedback system is disabled")

        rag = get_rag_instance()
        stats = rag.get_feedback_statistics(days=days)

        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])

        if "message" in stats:
            raise HTTPException(status_code=404, detail=stats["message"])

        return FeedbackStatisticsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/feedback/high-quality-documents")
async def get_high_quality_documents(min_score: float = 0.5, limit: int = 100):
    """
    获取高质量文档列表

    Args:
        min_score: 最低质量分数
        limit: 返回数量限制

    Returns:
        高质量文档列表
    """
    try:
        if not settings.enable_feedback_system:
            raise HTTPException(status_code=403, detail="Feedback system is disabled")

        rag = get_rag_instance()
        documents = rag.get_high_quality_documents(min_score=min_score, limit=limit)

        return {
            "documents": documents,
            "count": len(documents),
            "min_score": min_score,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting high quality documents: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/feedback/trigger-reranking")
async def trigger_manual_reranking(
    query_id: str = Body(..., embed=True),
    optimization_strategy: str = Body("adjust_weights", embed=True)
):
    """
    手动触发重排序优化

    Args:
        query_id: 查询ID
        optimization_strategy: 优化策略

    Returns:
        优化结果
    """
    try:
        if not settings.enable_feedback_system:
            raise HTTPException(status_code=403, detail="Feedback system is disabled")

        # 这里可以实现手动触发重排序的逻辑
        # 实际应用中可能需要异步任务队列

        logger.info(f"Manual reranking triggered for query {query_id} with strategy {optimization_strategy}")

        return {
            "success": True,
            "message": "Reranking optimization triggered successfully",
            "query_id": query_id,
            "strategy": optimization_strategy
        }

    except Exception as e:
        logger.error(f"Error triggering manual reranking: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")