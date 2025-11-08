"""
意图分类API路由
提供完整的意图识别和路由功能的RESTful API
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.services.intent_workflow import IntentClassificationWorkflow
from backend.services.intent_classifier import IntentClassifier, QueryContext
from backend.services.context_manager import ContextManager
from backend.services.routing_decision import RoutingDecisionEngine
from backend.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/intent", tags=["Intent Classification"])

# 全局工作流实例（在实际应用中，应该通过依赖注入）
_intent_workflow: Optional[IntentClassificationWorkflow] = None


# 请求/响应模型
class ClassifyRequest(BaseModel):
    """分类请求模型"""
    query: str = Field(..., description="用户查询文本", min_length=1, max_length=2000)
    session_id: str = Field(..., description="会话ID", min_length=1, max_length=100)
    user_id: Optional[str] = Field(None, description="用户ID", max_length=100)
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文信息")
    thread_id: Optional[str] = Field(None, description="线程ID（用于多轮对话）")


class ClassifyResponse(BaseModel):
    """分类响应模型"""
    success: bool = Field(..., description="是否成功")
    intent: Optional[str] = Field(None, description="识别的意图")
    confidence: Optional[float] = Field(None, description="置信度")
    reasoning: Optional[str] = Field(None, description="分类理由")
    routing_decision: Optional[Dict[str, Any]] = Field(None, description="路由决策")
    agent_response: Optional[str] = Field(None, description="Agent响应")
    clarification_needed: bool = Field(False, description="是否需要澄清")
    clarification_message: Optional[str] = Field(None, description="澄清消息")
    processing_time_ms: Optional[int] = Field(None, description="处理时间（毫秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(None, description="错误信息")


class ContinueWorkflowRequest(BaseModel):
    """继续工作流请求模型"""
    user_response: str = Field(..., description="用户回应", min_length=1, max_length=2000)
    session_id: str = Field(..., description="会话ID", min_length=1, max_length=100)
    thread_id: Optional[str] = Field(None, description="线程ID")


class SessionContextResponse(BaseModel):
    """会话上下文响应模型"""
    session_id: str
    user_id: Optional[str]
    query_count: int
    session_topic: str
    session_stage: str
    uploaded_files_count: int
    recent_intents: List[str]
    context_keywords: List[str]
    completion_rate: float
    session_duration_minutes: float


class WorkflowStatsResponse(BaseModel):
    """工作流统计响应模型"""
    total_routes: int
    direct_routing_rate: float
    clarification_rate: float
    fallback_rate: float
    agent_usage_rates: Dict[str, float]
    available_agents: int
    system_load: float


def get_intent_workflow() -> IntentClassificationWorkflow:
    """获取意图分类工作流实例"""
    global _intent_workflow
    if _intent_workflow is None:
        raise HTTPException(status_code=500, detail="意图分类工作流未初始化")
    return _intent_workflow


async def initialize_intent_workflow():
    """初始化意图分类工作流"""
    global _intent_workflow

    try:
        # 这里应该从配置或依赖注入获取服务实例
        # 为了演示，我们创建模拟实例
        from backend.config import get_database_pool, get_llm_client

        pool = await get_database_pool()
        llm_client = get_llm_client()

        # 创建核心服务
        prompt_manager = PromptManager(pool)
        context_manager = ContextManager(storage_backend="memory")
        intent_classifier = IntentClassifier(llm_client, prompt_manager)
        routing_engine = RoutingDecisionEngine()

        # 创建工作流
        _intent_workflow = IntentClassificationWorkflow(
            intent_classifier=intent_classifier,
            context_manager=context_manager,
            routing_engine=routing_engine,
            prompt_manager=prompt_manager
        )

        logger.info("意图分类工作流初始化完成")

    except Exception as e:
        logger.error(f"意图分类工作流初始化失败: {str(e)}")
        raise


@router.post("/classify", response_model=ClassifyResponse)
async def classify_intent(
    request: ClassifyRequest,
    background_tasks: BackgroundTasks,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    意图分类和路由接口

    该接口是核心入口点，接收用户查询并执行完整的意图识别、
    分类、路由决策和Agent调度流程。
    """
    try:
        start_time = datetime.now()

        logger.info(f"收到分类请求，会话ID: {request.session_id}, 查询: {request.query[:100]}...")

        # 执行完整的工作流
        result = await workflow.run_workflow(
            query=request.query,
            session_id=request.session_id,
            user_id=request.user_id,
            thread_id=request.thread_id
        )

        # 计算处理时间
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # 构建响应
        response = ClassifyResponse(
            success=result["success"],
            intent=result.get("intent_result", {}).get("intent"),
            confidence=result.get("intent_result", {}).get("confidence"),
            reasoning=result.get("intent_result", {}).get("reasoning"),
            routing_decision=result.get("routing_decision"),
            agent_response=result.get("agent_response"),
            clarification_needed=result.get("clarification_needed", False),
            clarification_message=result.get("clarification_response"),
            processing_time_ms=processing_time,
            metadata=result.get("metadata", {}),
            error=result.get("error")
        )

        # 在后台记录使用日志
        background_tasks.add_task(
            log_classification_usage,
            request.session_id,
            request.user_id,
            request.query,
            result
        )

        logger.info(f"分类请求处理完成，成功: {result['success']}")
        return response

    except Exception as e:
        logger.error(f"意图分类API错误: {str(e)}")
        return ClassifyResponse(
            success=False,
            error=f"意图分类处理失败: {str(e)}",
            agent_response="抱歉，处理您的请求时遇到了系统错误。请稍后重试。"
        )


@router.post("/continue", response_model=ClassifyResponse)
async def continue_workflow(
    request: ContinueWorkflowRequest,
    background_tasks: BackgroundTasks,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    继续工作流接口

    用于在澄清对话后继续执行工作流，处理用户的澄清回应。
    """
    try:
        logger.info(f"收到继续工作流请求，会话ID: {request.session_id}")

        # 继续执行工作流
        result = await workflow.continue_workflow(
            user_response=request.user_response,
            session_id=request.session_id,
            thread_id=request.thread_id
        )

        # 构建响应
        response = ClassifyResponse(
            success=result["success"],
            intent=result.get("intent_result", {}).get("intent") if result.get("intent_result") else None,
            confidence=result.get("intent_result", {}).get("confidence") if result.get("intent_result") else None,
            reasoning=result.get("intent_result", {}).get("reasoning") if result.get("intent_result") else None,
            routing_decision=result.get("routing_decision"),
            agent_response=result.get("agent_response"),
            clarification_needed=result.get("clarification_needed", False),
            clarification_message=result.get("clarification_response"),
            metadata=result.get("metadata", {}),
            error=result.get("error")
        )

        # 在后台记录使用日志
        background_tasks.add_task(
            log_continuation_usage,
            request.session_id,
            request.user_response,
            result
        )

        logger.info(f"继续工作流请求处理完成，成功: {result['success']}")
        return response

    except Exception as e:
        logger.error(f"继续工作流API错误: {str(e)}")
        return ClassifyResponse(
            success=False,
            error=f"继续工作流处理失败: {str(e)}",
            agent_response="抱歉，处理您的回应时遇到了系统错误。请重新描述您的需求。"
        )


@router.get("/session/{session_id}/context", response_model=SessionContextResponse)
async def get_session_context(
    session_id: str,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    获取会话上下文接口

    返回指定会话的详细上下文信息，包括历史记录、
    用户偏好、文件信息等。
    """
    try:
        logger.info(f"获取会话上下文，会话ID: {session_id}")

        # 获取会话上下文
        session_context = await workflow.context_manager.get_session_context(session_id)

        # 获取增强上下文
        enhanced_context = await workflow.context_manager.get_enhanced_context(
            session_id=session_id,
            max_history=10,
            include_files=True
        )

        # 构建响应
        response = SessionContextResponse(
            session_id=session_context.session_id,
            user_id=session_context.user_id,
            query_count=session_context.query_count,
            session_topic=session_context.session_topic,
            session_stage=session_context.session_stage,
            uploaded_files_count=len(session_context.uploaded_files),
            recent_intents=session_context.get_recent_intents(5),
            context_keywords=enhanced_context.get("context_keywords", []),
            completion_rate=session_context.completion_rate,
            session_duration_minutes=session_context.get_session_duration() / 60
        )

        logger.info(f"会话上下文获取完成，查询数: {response.query_count}")
        return response

    except Exception as e:
        logger.error(f"获取会话上下文错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话上下文失败: {str(e)}")


@router.get("/session/{session_id}/patterns")
async def analyze_session_patterns(
    session_id: str,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    分析会话模式接口

    分析指定会话的行为模式，包括查询模式、意图演化、
    时间分布等，用于用户行为分析和系统优化。
    """
    try:
        logger.info(f"分析会话模式，会话ID: {session_id}")

        # 分析会话模式
        patterns = await workflow.context_manager.analyze_session_patterns(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "patterns": patterns,
            "analysis_timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"分析会话模式错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析会话模式失败: {str(e)}")


@router.get("/stats/workflow", response_model=WorkflowStatsResponse)
async def get_workflow_statistics(
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    获取工作流统计接口

    返回意图分类和路由系统的整体统计信息，
    包括路由成功率、Agent使用情况、系统负载等。
    """
    try:
        logger.info("获取工作流统计信息")

        # 获取工作流统计
        stats = workflow.get_workflow_stats()

        # 获取路由统计
        routing_stats = workflow.routing_engine.get_routing_statistics()

        # 构建响应
        response = WorkflowStatsResponse(
            total_routes=routing_stats.get("total_routes", 0),
            direct_routing_rate=routing_stats.get("direct_routing_rate", 0.0),
            clarification_rate=routing_stats.get("clarification_rate", 0.0),
            fallback_rate=routing_stats.get("fallback_rate", 0.0),
            agent_usage_rates=routing_stats.get("agent_usage_rates", {}),
            available_agents=len(workflow.routing_engine.system_status.get_available_agents()),
            system_load=workflow.routing_engine.system_status.system_load
        )

        logger.info(f"工作流统计获取完成，总路由数: {response.total_routes}")
        return response

    except Exception as e:
        logger.error(f"获取工作流统计错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工作流统计失败: {str(e)}")


@router.post("/test/classification")
async def test_intent_classification(
    query: str,
    session_id: str = "test_session",
    user_id: Optional[str] = None,
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    测试意图分类接口

    专门用于测试意图分类功能，不执行完整的工作流，
    只返回分类结果。
    """
    try:
        logger.info(f"测试意图分类，查询: {query[:50]}...")

        # 构建测试上下文
        test_context = QueryContext(
            session_id=session_id,
            user_id=user_id,
            current_query=query,
            session_history=[],
            recent_intents=[],
            uploaded_files=[],
            user_preferences={},
            context_keywords=[]
        )

        # 执行意图分类
        intent_result = await workflow.intent_classifier.classify_intent(
            query=query,
            context=test_context
        )

        return {
            "success": True,
            "intent_result": intent_result.to_dict(),
            "test_timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"测试意图分类错误: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "test_timestamp": datetime.now().isoformat()
        }


@router.get("/health")
async def health_check(
    workflow: IntentClassificationWorkflow = Depends(get_intent_workflow)
):
    """
    健康检查接口

    检查意图分类系统各组件的健康状态。
    """
    try:
        # 检查各组件健康状态
        classifier_health = await workflow.intent_classifier.health_check()
        context_health = await workflow.context_manager.health_check()
        routing_health = await workflow.routing_engine.health_check()

        overall_health = all([
            classifier_health.get("status") == "healthy",
            context_health.get("status") == "healthy",
            routing_health.get("status") == "healthy"
        ])

        return {
            "status": "healthy" if overall_health else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "intent_classifier": classifier_health,
                "context_manager": context_health,
                "routing_engine": routing_health,
                "prompt_manager": "enabled" if workflow.prompt_manager else "disabled"
            },
            "workflow": workflow.get_workflow_stats()
        }

    except Exception as e:
        logger.error(f"健康检查错误: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


# 后台任务函数
async def log_classification_usage(
    session_id: str,
    user_id: Optional[str],
    query: str,
    result: Dict[str, Any]
):
    """记录分类使用日志"""
    try:
        # 这里可以将使用日志记录到数据库或日志系统
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_id": user_id,
            "query": query,
            "success": result["success"],
            "intent": result.get("intent_result", {}).get("intent"),
            "confidence": result.get("intent_result", {}).get("confidence"),
            "selected_agent": result.get("routing_decision", {}).get("selected_agent"),
            "clarification_needed": result.get("clarification_needed", False)
        }

        logger.info(f"分类使用日志: {json.dumps(log_entry, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"记录分类使用日志失败: {str(e)}")


async def log_continuation_usage(
    session_id: str,
    user_response: str,
    result: Dict[str, Any]
):
    """记录继续工作流使用日志"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_response": user_response,
            "success": result["success"],
            "clarification_needed": result.get("clarification_needed", False)
        }

        logger.info(f"继续工作流使用日志: {json.dumps(log_entry, ensure_ascii=False)}")

    except Exception as e:
        logger.error(f"记录继续工作流使用日志失败: {str(e)}")


# 初始化函数
async def initialize_intent_routes():
    """初始化意图分类路由"""
    await initialize_intent_workflow()
    logger.info("意图分类API路由初始化完成")