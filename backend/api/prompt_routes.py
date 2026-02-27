"""
Prompt Management API
RESTful API for prompt CRUD, testing, usage logging, and experiments.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.prompt_manager import (
    PromptInfo,
    PromptManager,
    PromptStatus,
    PromptVariable,
    UsageLog,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"], dependencies=[Depends(secure_endpoint)])


# PydanticEN
class PromptVariableCreate(BaseModel):
    name: str = Field(..., description="Description")
    type: str = Field(default="string", description="Description")
    required: bool = Field(default=True, description="Description")
    default_value: Any = Field(default=None, description="Description")
    description: str = Field(default="", description="Description")
    validation_regex: str = Field(default=None, description="Description")
    options: List[Any] = Field(default=None, description="Description")


class PromptListResponse(BaseModel):  # P0EN:EN
    """Prompt"""
    id: UUID
    name: str
    category: str
    subcategory: Optional[str]
    version: str
    content: str
    variables: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    is_active: bool
    is_latest: bool
    priority: int
    performance_score: float
    usage_count: int
    success_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    tags: List[str]


class PaginationInfo(BaseModel):
    page: int
    size: int
    total: int
    pages: int


class PromptListPageResponse(BaseModel):
    data: List[PromptListResponse]
    pagination: PaginationInfo


class PromptCreate(BaseModel):
    name: str = Field(..., description="Prompt")
    category: str = Field(..., description="Prompt")
    subcategory: Optional[str] = Field(None, description="Description")
    version: str = Field(default="1.0.0", description="Description")
    content: str = Field(..., description="Prompt")
    variables: Optional[List[PromptVariableCreate]] = Field(None, description="Description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Description")
    priority: int = Field(default=0, description="Description")
    tags: Optional[List[str]] = Field(None, description="Description")
    created_by: Optional[str] = Field(None, description="Description")


class PromptUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Prompt")
    variables: Optional[List[PromptVariableCreate]] = Field(None, description="Description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Description")
    priority: Optional[int] = Field(None, description="Description")
    tags: Optional[List[str]] = Field(None, description="Description")
    change_description: Optional[str] = Field(None, description="Description")
    updated_by: Optional[str] = Field(None, description="Description")  # P0EN:ENupdated_byEN
    create_new_version: bool = Field(default=True, description="Description")


class PromptTest(BaseModel):
    variables: Dict[str, Any] = Field(..., description="Description")
    context: Optional[Dict[str, Any]] = Field(None, description="Description")


class ExperimentCreate(BaseModel):
    name: str = Field(..., description="Description")
    description: Optional[str] = Field(None, description="Description")
    prompt_a_id: UUID = Field(..., description="Prompt A ID")
    prompt_b_id: UUID = Field(..., description="Prompt B ID")
    traffic_split: float = Field(default=0.5, gt=0, lt=1, description="Traffic split for prompt A")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Description")
    created_by: Optional[str] = Field(None, description="Description")


class ExperimentTrafficUpdate(BaseModel):
    traffic_split: float = Field(..., gt=0, lt=1, description="Traffic split for prompt A")


class ExperimentStatusUpdate(BaseModel):
    status: str = Field(..., description="Experiment status: active/paused/completed/cancelled")


class UsageLogCreate(BaseModel):
    prompt_id: UUID = Field(..., description="Prompt ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Description")
    variables_used: Optional[Dict[str, Any]] = Field(None, description="Description")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    success: bool = Field(..., description="Description")
    error_message: Optional[str] = Field(None, description="Description")
    user_feedback: Optional[int] = Field(None, ge=1, le=5, description="Description")
    llm_response: Optional[Dict[str, Any]] = Field(None, description="LLM response payload")
    tokens_used: int = Field(default=0, description="Token usage")
    model_name: Optional[str] = Field(None, description="Description")
    temperature: Optional[float] = Field(None, description="Description")


# EN:ENPrompt Manager
async def get_prompt_manager() -> PromptManager:
    """Build and return a PromptManager instance."""
    # EN
    from backend.config import get_database_pool

    pool = await get_database_pool()
    return PromptManager(pool)


@router.get("/", response_model=PromptListPageResponse)
async def list_prompts(
    category: Optional[str] = Query(None, description="Description"),
    is_active: Optional[bool] = Query(None, description="Description"),
    is_latest: Optional[bool] = Query(True, description="Description"),
    page: int = Query(1, ge=1, description="Description"),
    size: int = Query(20, ge=1, le=100, description="Description"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    Prompt API endpoint
    """
    try:
        async with prompt_manager.db_pool.acquire() as conn:
            # EN
            conditions = []
            params = []
            param_count = 0

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if is_latest is not None:
                param_count += 1
                conditions.append(f"is_latest = ${param_count}")
                params.append(is_latest)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # EN
            query = f"""
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                {where_clause}
                GROUP BY p.id
                ORDER BY p.priority DESC, p.updated_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """

            params.extend([size, (page - 1) * size])
            rows = await conn.fetch(query, *params)

            # EN
            count_query = f"""
                SELECT COUNT(DISTINCT p.id)
                FROM prompts p
                {where_clause}
            """
            total_count = await conn.fetchval(count_query, *params[:-2])

            prompts = []
            for row in rows:
                prompt_data = dict(row)
                # ENvariables
                if isinstance(prompt_data.get("variables"), str) and prompt_data["variables"]:
                    prompt_data["variables"] = json.loads(prompt_data["variables"])
                if isinstance(prompt_data.get("metadata"), str) and prompt_data["metadata"]:
                    prompt_data["metadata"] = json.loads(prompt_data["metadata"])
                prompts.append(prompt_data)

            return {
                "data": prompts,
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_count,
                    "pages": (total_count + size - 1) // size,
                },
            }

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{prompt_id:uuid}", response_model=Dict[str, Any])
async def get_prompt(
    prompt_id: UUID, prompt_manager: PromptManager = Depends(get_prompt_manager)
):
    """
    Prompt API endpoint
    """
    try:
        prompt_info = await prompt_manager._get_prompt_by_id(prompt_id)
        if not prompt_info:
            raise HTTPException(status_code=404, detail="Prompt not found.")

        # EN
        performance = await prompt_manager.get_prompt_performance(prompt_id)

        # EN
        async with prompt_manager.db_pool.acquire() as conn:
            versions_query = """
                SELECT version, change_description, created_at, created_by
                FROM prompt_versions
                WHERE prompt_id = $1
                ORDER BY version DESC
            """
            versions = await conn.fetch(versions_query, prompt_id)

        response = {
            "prompt": prompt_info.to_dict(),
            "performance": performance,
            "versions": [dict(version) for version in versions],
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=Dict[str, Any])
async def create_prompt(
    prompt_data: PromptCreate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    ENPrompt
    """
    try:
        # EN
        variables = None
        if prompt_data.variables:
            variables = [PromptVariable(**var.dict()) for var in prompt_data.variables]

        # ENPrompt
        prompt_info = await prompt_manager.create_prompt(
            name=prompt_data.name,
            category=prompt_data.category,
            content=prompt_data.content,
            subcategory=prompt_data.subcategory,
            version=prompt_data.version,
            variables=variables,
            metadata=prompt_data.metadata,
            priority=prompt_data.priority,
            tags=prompt_data.tags,
            created_by=prompt_data.created_by,
        )

        return {
            "success": True,
            "prompt": prompt_info.to_dict(),
            "message": "Prompt created successfully.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{prompt_id:uuid}", response_model=Dict[str, Any])
async def update_prompt(
    prompt_id: UUID,
    prompt_data: PromptUpdate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    ENPrompt
    """
    try:
        # EN
        variables = None
        if prompt_data.variables:
            variables = [PromptVariable(**var.dict()) for var in prompt_data.variables]

        # ENPrompt(P0EN:ENupdated_byEN)
        prompt_info = await prompt_manager.update_prompt(
            prompt_id=prompt_id,
            content=prompt_data.content,
            variables=variables,
            metadata=prompt_data.metadata,
            priority=prompt_data.priority,
            tags=prompt_data.tags,
            change_description=prompt_data.change_description,
            updated_by=prompt_data.updated_by,  # EN:ENupdated_byENcreated_by
            create_new_version=prompt_data.create_new_version,
        )

        return {
            "success": True,
            "prompt": prompt_info.to_dict(),
            "message": "Prompt updated successfully.",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{prompt_id:uuid}", response_model=Dict[str, Any])
async def delete_prompt(
    prompt_id: UUID, prompt_manager: PromptManager = Depends(get_prompt_manager)
):
    """
    Soft-delete a prompt.
    """
    try:
        async with prompt_manager.db_pool.acquire() as conn:
            # EN:EN
            await conn.execute(
                "UPDATE prompts SET is_active = false, updated_at = NOW() WHERE id = $1",
                prompt_id,
            )

        return {"success": True, "message": "Prompt archived successfully."}

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{prompt_id:uuid}/test", response_model=Dict[str, Any])
async def test_prompt(
    prompt_id: UUID,
    test_data: PromptTest,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    Prompt API endpoint
    """
    try:
        # ENPrompt
        prompt_info = await prompt_manager._get_prompt_by_id(prompt_id)
        if not prompt_info:
            raise HTTPException(status_code=404, detail="Prompt not found.")

        # EN
        rendered_content = prompt_manager._render_template(
            prompt_info.content, test_data.variables
        )

        # EN
        missing_variables = []
        for var in prompt_info.variables:
            if var.required and var.name not in test_data.variables:
                missing_variables.append(var.name)

        return {
            "success": True,
            "rendered_content": rendered_content,
            "missing_variables": missing_variables,
            "used_variables": list(test_data.variables.keys()),
            "prompt_info": {
                "id": str(prompt_info.id),
                "name": prompt_info.name,
                "version": prompt_info.version,
                "category": prompt_info.category,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{prompt_id:uuid}/performance", response_model=Dict[str, Any])
async def get_prompt_performance(
    prompt_id: UUID,
    days: int = Query(7, ge=1, le=365, description="Description"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    Prompt API endpoint
    """
    try:
        # EN
        performance = await prompt_manager.get_prompt_performance(prompt_id)
        if not performance:
            raise HTTPException(status_code=404, detail="Prompt performance not found.")

        # EN(P0EN:ENdays)
        async with prompt_manager.db_pool.acquire() as conn:
            detailed_query = """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as usage_count,
                    COUNT(CASE WHEN success = true THEN 1 END) as success_count,
                    AVG(execution_time_ms) as avg_execution_time,
                    AVG(user_feedback) as avg_feedback,
                    SUM(tokens_used) as total_tokens
                FROM prompt_usage_logs
                WHERE prompt_id = $1
                  AND created_at >= NOW() - INTERVAL '1 day' * $2
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """

            daily_stats = await conn.fetch(detailed_query, prompt_id, days)

            # EN
            recent_logs_query = """
                SELECT session_id, context, success, execution_time_ms,
                       user_feedback, tokens_used, created_at
                FROM prompt_usage_logs
                WHERE prompt_id = $1
                ORDER BY created_at DESC
                LIMIT 10
            """

            recent_logs = await conn.fetch(recent_logs_query, prompt_id)

        return {
            "summary": performance,
            "daily_stats": [dict(row) for row in daily_stats],
            "recent_logs": [dict(row) for row in recent_logs],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/usage-logs", response_model=Dict[str, Any])
async def record_usage_log(
    log_data: UsageLogCreate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    Prompt API endpoint
    """
    try:
        usage_log = UsageLog(
            prompt_id=log_data.prompt_id,
            session_id=log_data.session_id,
            context=log_data.context or {},
            variables_used=log_data.variables_used or {},
            execution_time_ms=log_data.execution_time_ms,
            success=log_data.success,
            error_message=log_data.error_message,
            user_feedback=log_data.user_feedback,
            llm_response=log_data.llm_response,
            tokens_used=log_data.tokens_used,
            model_name=log_data.model_name,
            temperature=log_data.temperature,
        )

        await prompt_manager.record_usage_log(usage_log)

        return {"success": True, "message": "Usage log recorded successfully."}

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/experiments", response_model=Dict[str, Any])
async def create_experiment(
    experiment: ExperimentCreate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """ENA/BEN."""
    try:
        created = await prompt_manager.create_experiment(
            name=experiment.name,
            description=experiment.description,
            prompt_a_id=experiment.prompt_a_id,
            prompt_b_id=experiment.prompt_b_id,
            traffic_split=experiment.traffic_split,
            metrics=experiment.metrics,
            created_by=experiment.created_by,
        )
        return {"success": True, "experiment": created}
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/experiments", response_model=Dict[str, Any])
async def list_experiments(
    status: Optional[str] = Query(None, description="Description"),
    category: Optional[str] = Query(None, description="Description"),
    page: int = Query(1, ge=1, description="Description"),
    size: int = Query(20, ge=1, le=100, description="Description"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """Prompt API endpoint."""
    try:
        data, total = await prompt_manager.list_experiments(
            status=status,
            category=category,
            limit=size,
            offset=(page - 1) * size,
        )
        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "pages": (total + size - 1) // size,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/experiments/{experiment_id:uuid}", response_model=Dict[str, Any])
async def get_experiment(
    experiment_id: UUID, prompt_manager: PromptManager = Depends(get_prompt_manager)
):
    """Prompt API endpoint."""
    try:
        experiment = await prompt_manager.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found.")
        return {"success": True, "experiment": experiment}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/experiments/{experiment_id:uuid}/traffic", response_model=Dict[str, Any])
async def update_experiment_traffic(
    experiment_id: UUID,
    payload: ExperimentTrafficUpdate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """Prompt API endpoint."""
    try:
        experiment = await prompt_manager.update_experiment_traffic(
            experiment_id=experiment_id,
            traffic_split=payload.traffic_split,
        )
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found.")
        return {"success": True, "experiment": experiment}
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/experiments/{experiment_id:uuid}/status", response_model=Dict[str, Any])
async def update_experiment_status(
    experiment_id: UUID,
    payload: ExperimentStatusUpdate,
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """Prompt API endpoint."""
    try:
        experiment = await prompt_manager.update_experiment_status(
            experiment_id=experiment_id,
            status=payload.status,
        )
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found.")
        return {"success": True, "experiment": experiment}
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid request")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/categories/list", response_model=List[str])
async def list_categories(prompt_manager: PromptManager = Depends(get_prompt_manager)):
    """
    Prompt API endpoint
    """
    try:
        async with prompt_manager.db_pool.acquire() as conn:
            categories = await conn.fetch(
                "SELECT DISTINCT category FROM prompts WHERE is_active = true ORDER BY category"
            )

        return [row["category"] for row in categories]

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tags/list", response_model=List[Dict[str, Any]])
async def list_tags(prompt_manager: PromptManager = Depends(get_prompt_manager)):
    """
    List prompt tags with usage statistics.
    """
    try:
        async with prompt_manager.db_pool.acquire() as conn:
            tags = await conn.fetch(
                """
                SELECT t.name, t.description, t.color,
                       COUNT(ptr.prompt_id) as usage_count
                FROM prompt_tags t
                LEFT JOIN prompt_tag_relations ptr ON t.id = ptr.tag_id
                LEFT JOIN prompts p ON ptr.prompt_id = p.id AND p.is_active = true
                GROUP BY t.id, t.name, t.description, t.color
                ORDER BY usage_count DESC, t.name
                """
            )

        return [dict(row) for row in tags]

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics/summary", response_model=Dict[str, Any])
async def get_prompt_metrics_summary(
    days: int = Query(7, ge=1, le=365, description="Description"),
    category: Optional[str] = Query(None, description="Description"),
    top_limit: int = Query(10, ge=1, le=50, description="Prompt metric limit"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    Return prompt usage summary metrics.
    """
    try:
        return await prompt_manager.get_usage_summary(
            days=days,
            category=category,
            top_limit=top_limit,
        )
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search", response_model=List[PromptListResponse])  # P0EN:EN
async def search_prompts(
    q: str = Query(..., description="Description"),
    category: Optional[str] = Query(None, description="Description"),
    limit: int = Query(10, ge=1, le=50, description="Description"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    ENPrompt
    """
    try:
        async with prompt_manager.db_pool.acquire() as conn:
            # EN(P0EN:EN)
            escaped_q = q.replace('%', r'\%').replace('_', r'\_')
            params = [f"%{escaped_q}%"]  # $1: EN
            conditions = ["(p.name ILIKE $1 OR p.content ILIKE $1 OR COALESCE(p.subcategory, '') ILIKE $1)"]

            if category:
                conditions.append(f"p.category = ${len(params)+1}")
                params.append(category)

            where_clause = " AND ".join(conditions)
            limit_idx = len(params) + 1

            query = f"""
                SELECT p.*,
                       COALESCE(
                           array_agg(t.name ORDER BY t.name) FILTER (WHERE t.name IS NOT NULL),
                           ARRAY[]::VARCHAR[]
                       ) as tags,
                       ts_rank_cd(
                           to_tsvector('english', p.name || ' ' || COALESCE(p.content, '')),
                           plainto_tsquery('english', $1)
                       ) as search_rank
                FROM prompts p
                LEFT JOIN prompt_tag_relations ptr ON p.id = ptr.prompt_id
                LEFT JOIN prompt_tags t ON ptr.tag_id = t.id
                WHERE {where_clause} AND p.is_active = true
                GROUP BY p.id
                ORDER BY search_rank DESC, p.performance_score DESC
                LIMIT ${limit_idx}
            """

            params.append(limit)
            rows = await conn.fetch(query, *params)

            results = []
            for row in rows:
                prompt_data = dict(row)
                if isinstance(prompt_data.get("variables"), str) and prompt_data["variables"]:
                    prompt_data["variables"] = json.loads(prompt_data["variables"])
                if isinstance(prompt_data.get("metadata"), str) and prompt_data["metadata"]:
                    prompt_data["metadata"] = json.loads(prompt_data["metadata"])
                results.append(prompt_data)

            return results

    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{prompt_id:uuid}/clone", response_model=Dict[str, Any])
async def clone_prompt(
    prompt_id: UUID,
    new_name: str = Query(..., description="Prompt metric limit"),
    new_version: str = Query(default="1.0.0", description="Description"),
    prompt_manager: PromptManager = Depends(get_prompt_manager),
):
    """
    ENPrompt
    """
    try:
        # ENPrompt
        original_prompt = await prompt_manager._get_prompt_by_id(prompt_id)
        if not original_prompt:
            raise HTTPException(status_code=404, detail="Prompt not found.")

        # ENPrompt
        cloned_prompt = await prompt_manager.create_prompt(
            name=new_name,
            category=original_prompt.category,
            content=original_prompt.content,
            subcategory=original_prompt.subcategory,
            version=new_version,
            variables=original_prompt.variables,
            metadata={**original_prompt.metadata, "cloned_from": str(prompt_id)},
            priority=original_prompt.priority,
            tags=original_prompt.tags,
            created_by=f"cloned_from_{original_prompt.created_by or 'unknown'}",
        )

        return {
            "success": True,
            "prompt": cloned_prompt.to_dict(),
            "message": "Prompt cloned successfully.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt API error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
