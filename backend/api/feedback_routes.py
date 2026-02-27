"""
Feedback API routes
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.rag_engine import SimpleRAG

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(secure_endpoint)])

# Feedback-enabled RAG singleton
rag_instance = None


def get_rag_instance():
    """Feedback-enabled RAG singleton"""
    global rag_instance
    if rag_instance is None:
        rag_instance = SimpleRAG(enable_feedback=settings.enable_feedback_system)
    return rag_instance


class FeedbackRequest(BaseModel):
    """Feedback schema."""

    query_id: str
    question: str
    answer: str
    feedback_type: str  # "helpful", "not_helpful", "partially_helpful"
    user_comment: Optional[str] = None
    retrieved_chunks: Optional[List[Dict]] = None
    feedback_weight: float = Field(default=1.0, ge=0.0, le=10.0)


class FeedbackResponse(BaseModel):
    """Feedback schema."""

    success: bool
    message: str


class FeedbackStatisticsResponse(BaseModel):
    """Feedback schema."""

    total_queries: int
    helpful_count: int
    not_helpful_count: int
    partially_helpful_count: int
    success_rate: float
    avg_feedback_weight: float


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    EN

    Args:
        request: EN

    Returns:
        EN
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
            feedback_weight=request.feedback_weight,
        )

        if success:
            logger.info(f"Feedback submitted successfully for query {request.query_id}")
            return FeedbackResponse(
                success=True, message="Feedback submitted successfully"
            )
        else:
            logger.warning(f"Failed to submit feedback for query {request.query_id}")
            return FeedbackResponse(success=False, message="Failed to submit feedback")

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/feedback/statistics", response_model=FeedbackStatisticsResponse)
async def get_feedback_statistics(days: int = Query(default=7, ge=1, le=365)):
    """
    EN

    Args:
        days: EN(EN7EN)

    Returns:
        EN
    """
    days = max(1, min(days, 365))
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
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/feedback/high-quality-documents")
async def get_high_quality_documents(min_score: float = 0.5, limit: int = 100):
    """
    EN

    Args:
        min_score: EN
        limit: EN

    Returns:
        EN
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
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting high quality documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/feedback/trigger-reranking")
async def trigger_manual_reranking(
    query_id: str = Body(..., embed=True),
    optimization_strategy: str = Body("adjust_weights", embed=True),
):
    """
    EN

    Args:
        query_id: ENID
        optimization_strategy: EN

    Returns:
        EN
    """
    try:
        if not settings.enable_feedback_system:
            raise HTTPException(status_code=403, detail="Feedback system is disabled")

        # EN
        # EN

        logger.info(
            f"Manual reranking triggered for query {query_id} with strategy {optimization_strategy}"
        )

        return {
            "success": True,
            "message": "Reranking optimization triggered successfully",
            "query_id": query_id,
            "strategy": optimization_strategy,
        }

    except Exception as e:
        logger.error(f"Error triggering manual reranking: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
