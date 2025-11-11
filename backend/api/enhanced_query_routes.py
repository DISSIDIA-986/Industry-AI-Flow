"""
增强的查询API路由 - 支持参数配置和反馈集成
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config import settings
from backend.security.dependencies import secure_endpoint
from backend.services.rag_engine import SimpleRAG

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(secure_endpoint)])

# 全局RAG实例
rag_instance = None


def get_rag_instance():
    """获取RAG实例"""
    global rag_instance
    if rag_instance is None:
        rag_instance = SimpleRAG(
            use_hybrid_search=True,
            use_reranker=True,
            enable_feedback=settings.enable_feedback_system,
        )
    return rag_instance


class QueryRequest(BaseModel):
    """查询请求模型"""

    question: str
    top_k: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None


class QueryResponse(BaseModel):
    """查询响应模型"""

    query_id: str
    question: str
    answer: str
    sources: List[str]
    retrieved_chunks: List[Dict]
    search_weights: Dict[str, float]


class LLMConfigUpdateRequest(BaseModel):
    """LLM配置更新请求模型"""

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None


@router.post("/query", response_model=QueryResponse)
async def enhanced_query(request: QueryRequest):
    """
    增强的RAG查询接口，支持参数配置

    Args:
        request: 查询请求

    Returns:
        查询结果
    """
    try:
        rag = get_rag_instance()

        # 参数验证
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

        # 执行查询
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/query/config")
async def get_current_llm_config():
    """
    获取当前LLM配置

    Returns:
        当前LLM配置信息
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/query/config")
async def update_llm_config(request: LLMConfigUpdateRequest):
    """
    更新LLM配置

    Args:
        request: 配置更新请求

    Returns:
        更新结果
    """
    try:
        # 参数验证
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

        # 构建更新参数
        update_params = {}
        if request.temperature is not None:
            update_params["default_temperature"] = request.temperature
        if request.max_tokens is not None:
            update_params["default_max_tokens"] = request.max_tokens
        if request.top_p is not None:
            update_params["default_top_p"] = request.top_p

        # 更新配置
        rag.llm_client.update_config(**update_params)

        # 获取更新后的配置
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/query/models")
async def list_available_models():
    """
    列出可用的LLM模型

    Returns:
        可用模型列表
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/query/switch-model")
async def switch_model(model_name: str = Body(..., embed=True)):
    """
    切换LLM模型

    Args:
        model_name: 模型名称

    Returns:
        切换结果
    """
    try:
        rag = get_rag_instance()

        # 获取可用模型列表
        available_models = rag.llm_client.list_models()
        model_names = [model.get("name", "") for model in available_models]

        if model_name not in model_names:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' not available. Available models: {model_names}",
            )

        # 切换模型
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/query/search-weights")
async def get_adaptive_search_weights():
    """
    获取自适应搜索权重

    Returns:
        当前搜索权重配置
    """
    try:
        rag = get_rag_instance()

        # 获取自适应权重
        vector_weight, bm25_weight = rag._get_adaptive_search_weights()

        return {
            "current_weights": {
                "vector_weight": vector_weight,
                "bm25_weight": bm25_weight,
            },
            "default_weights": {"vector_weight": 0.7, "bm25_weight": 0.3},
            "feedback_enabled": rag.enable_feedback,
            "adaptive_adjustment": rag.enable_feedback and True,  # 如果启用反馈系统则支持自适应调整
        }

    except Exception as e:
        logger.error(f"Error getting search weights: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/query/chat")
async def chat_completion(
    messages: List[Dict[str, str]] = Body(...),
    temperature: Optional[float] = Body(None),
    max_tokens: Optional[int] = Body(None),
    top_p: Optional[float] = Body(None),
):
    """
    对话模式完成接口

    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        temperature: 温度参数
        max_tokens: 最大token数
        top_p: 核采样参数

    Returns:
        对话回复
    """
    try:
        rag = get_rag_instance()

        # 参数验证
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

        # 验证消息格式
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

        # 执行对话
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
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/query/health")
async def query_health_check():
    """
    查询系统健康检查

    Returns:
        系统健康状态
    """
    try:
        rag = get_rag_instance()

        # 检查各个组件状态
        health_status = {
            "rag_system": "healthy",
            "vectorstore": "healthy",
            "llm_client": "healthy",
            "feedback_system": "enabled" if rag.enable_feedback else "disabled",
            "hybrid_search": "enabled" if rag.use_hybrid_search else "disabled",
            "reranker": "enabled" if rag.use_reranker else "disabled",
        }

        # 测试LLM连接
        try:
            models = rag.llm_client.list_models()
            health_status["llm_connection"] = "healthy"
            health_status["available_models"] = len(models)
        except Exception as e:
            health_status["llm_connection"] = f"unhealthy: {str(e)}"

        # 测试向量数据库连接
        try:
            doc_count = rag.vectorstore.get_document_count()
            health_status["vectorstore_connection"] = "healthy"
            health_status["document_count"] = doc_count
        except Exception as e:
            health_status["vectorstore_connection"] = f"unhealthy: {str(e)}"

        return health_status

    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
