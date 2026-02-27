"""
Enhanced query API routes
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import settings
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.language_policy import ensure_rag_english_query

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(secure_endpoint)])

# RAG singleton
rag_instance = None


def get_rag_instance():
    """RAG singleton"""
    global rag_instance
    if rag_instance is None:
        from backend.services.rag_engine import SimpleRAG

        rag_instance = SimpleRAG(
            use_hybrid_search=True,
            use_reranker=True,
            enable_feedback=settings.enable_feedback_system,
        )
    return rag_instance


class QueryRequest(BaseModel):
    """Query schema."""

    question: str
    top_k: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None


class QueryResponse(BaseModel):
    """Query schema."""

    query_id: str
    question: str
    answer: str
    sources: List[str]
    retrieved_chunks: List[Dict]
    search_weights: Dict[str, float]
    provider_used: Optional[str] = None
    route_mode: Optional[str] = None
    latency_ms: Optional[int] = None
    usage: Optional[Dict[str, int]] = None
    cost: Optional[Dict[str, float]] = None
    trace_id: Optional[str] = None


class LLMConfigUpdateRequest(BaseModel):
    """LLM"""

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None


@router.post("/query", response_model=QueryResponse)
async def enhanced_query(
    request: QueryRequest, tenant: TenantContext = Depends(get_current_tenant)
):
    """
    RAG singleton,EN

    Args:
        request: EN

    Returns:
        EN
    """
    try:
        ensure_rag_english_query(request.question, field="question")

        rag = get_rag_instance()

        # EN
        if request.temperature is not None and not (0.0 <= request.temperature <= 1.0):
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0.0 and 1.0"
            )

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise HTTPException(status_code=400, detail="Max tokens must be positive")

        if request.top_p is not None and not (0.0 <= request.top_p <= 1.0):
            raise HTTPException(
                status_code=400, detail="Top_p must be between 0.0 and 1.0"
            )

        # EN legacy /query EN RAG EN + EN,EN
        try:
            result = rag.query(
                question=request.question,
                top_k=request.top_k,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                session_id=tenant.tenant_id if tenant else settings.default_tenant_id,
                user_id=tenant.user_id if tenant else None,
            )
        except TypeError:
            # Backward-compatible call path for legacy or test double signatures.
            result = rag.query(
                question=request.question,
                top_k=request.top_k,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

        logger.info(f"Query processed successfully: {request.question[:100]}...")
        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/query/config")
async def get_current_llm_config():
    """
    ENLLM

    Returns:
        ENLLM
    """
    try:
        rag = get_rag_instance()
        config = rag.llm_client.get_current_config()

        return {
            "current_config": config,
            "default_config": {
                "temperature": settings.default_temperature,
                "max_tokens": settings.default_max_tokens,
                "top_p": settings.default_top_p,
            },
            "model_info": rag.llm_client.get_model_info(),
        }

    except Exception as e:
        logger.error(f"Error getting LLM config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/query/config")
async def update_llm_config(request: LLMConfigUpdateRequest, raw_request: Request):
    """
    ENLLM

    Args:
        request: EN

    Returns:
        EN
    """
    # TODO: admin role check required
    admin_key = raw_request.headers.get("X-Admin-Key", "")
    if not admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # EN
        if request.temperature is not None and not (0.0 <= request.temperature <= 1.0):
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0.0 and 1.0"
            )

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise HTTPException(status_code=400, detail="Max tokens must be positive")

        if request.top_p is not None and not (0.0 <= request.top_p <= 1.0):
            raise HTTPException(
                status_code=400, detail="Top_p must be between 0.0 and 1.0"
            )

        rag = get_rag_instance()

        # EN
        update_params = {}
        if request.temperature is not None:
            update_params["default_temperature"] = request.temperature
        if request.max_tokens is not None:
            update_params["default_max_tokens"] = request.max_tokens
        if request.top_p is not None:
            update_params["default_top_p"] = request.top_p

        # EN
        rag.llm_client.update_config(**update_params)

        # EN
        new_config = rag.llm_client.get_current_config()

        logger.info(f"LLM config updated: {update_params}")
        return {
            "success": True,
            "message": "LLM configuration updated successfully",
            "updated_params": update_params,
            "new_config": new_config,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating LLM config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/query/models")
async def list_available_models():
    """
    ENLLM

    Returns:
        EN
    """
    try:
        rag = get_rag_instance()
        models = rag.llm_client.list_models()

        return {
            "models": models,
            "current_model": rag.llm_client.model,
            "count": len(models),
        }

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/query/switch-model")
async def switch_model(model_name: str = Body(..., embed=True), request: Request = None):
    """
    ENLLM

    Args:
        model_name: EN

    Returns:
        EN
    """
    # TODO: admin role check required
    admin_key = request.headers.get("X-Admin-Key", "") if request else ""
    if not admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        rag = get_rag_instance()

        # EN
        available_models = rag.llm_client.list_models()
        model_names = [model.get("name", "") for model in available_models]

        if model_name not in model_names:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' not available. Available models: {model_names}",
            )

        # EN
        old_model = rag.llm_client.model
        rag.llm_client.model = model_name

        logger.info(f"Model switched from {old_model} to {model_name}")

        return {
            "success": True,
            "message": "Model switched successfully",
            "old_model": old_model,
            "new_model": model_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/query/search-weights")
async def get_adaptive_search_weights():
    """
    EN

    Returns:
        EN
    """
    try:
        rag = get_rag_instance()

        # EN
        vector_weight, bm25_weight = rag._get_adaptive_search_weights()

        return {
            "current_weights": {
                "vector_weight": vector_weight,
                "bm25_weight": bm25_weight,
            },
            "default_weights": {"vector_weight": 0.7, "bm25_weight": 0.3},
            "feedback_enabled": rag.enable_feedback,
            "adaptive_adjustment": rag.enable_feedback and True,  # EN
        }

    except Exception as e:
        logger.error(f"Error getting search weights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/query/chat")
async def chat_completion(
    messages: List[Dict[str, str]] = Body(...),
    temperature: Optional[float] = Body(None),
    max_tokens: Optional[int] = Body(None),
    top_p: Optional[float] = Body(None),
):
    """
    EN

    Args:
        messages: EN [{"role": "user", "content": "..."}]
        temperature: EN
        max_tokens: ENtokenEN
        top_p: EN

    Returns:
        EN
    """
    try:
        rag = get_rag_instance()

        # EN
        if temperature is not None and not (0.0 <= temperature <= 1.0):
            raise HTTPException(
                status_code=400, detail="Temperature must be between 0.0 and 1.0"
            )

        if max_tokens is not None and max_tokens <= 0:
            raise HTTPException(status_code=400, detail="Max tokens must be positive")

        if top_p is not None and not (0.0 <= top_p <= 1.0):
            raise HTTPException(
                status_code=400, detail="Top_p must be between 0.0 and 1.0"
            )

        # EN
        for message in messages:
            if (
                not isinstance(message, dict)
                or "role" not in message
                or "content" not in message
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Each message must have 'role' and 'content' fields",
                )

            if message["role"] not in ["user", "assistant", "system"]:
                raise HTTPException(
                    status_code=400,
                    detail="Message role must be 'user', 'assistant', or 'system'",
                )

        # EN
        response = rag.llm_client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

        logger.info(
            f"Chat completion processed successfully with {len(messages)} messages"
        )
        return {
            "response": response,
            "model": rag.llm_client.model,
            "message_count": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat completion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/query/health")
async def query_health_check():
    """
    EN

    Returns:
        EN
    """
    try:
        rag = get_rag_instance()

        # EN
        health_status = {
            "rag_system": "healthy",
            "vectorstore": "healthy",
            "llm_client": "healthy",
            "feedback_system": "enabled" if rag.enable_feedback else "disabled",
            "hybrid_search": "enabled" if rag.use_hybrid_search else "disabled",
            "reranker": "enabled" if rag.use_reranker else "disabled",
        }

        # ENLLM
        try:
            models = rag.llm_client.list_models()
            health_status["llm_connection"] = "healthy"
            health_status["available_models"] = len(models)
        except Exception as e:
            health_status["llm_connection"] = f"unhealthy: {str(e)}"

        # EN
        try:
            doc_count = rag.vectorstore.get_document_count()
            health_status["vectorstore_connection"] = "healthy"
            health_status["document_count"] = doc_count
        except Exception as e:
            health_status["vectorstore_connection"] = f"unhealthy: {str(e)}"

        return health_status

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
