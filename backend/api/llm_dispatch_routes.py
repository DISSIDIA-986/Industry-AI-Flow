"""Unified dispatch API routes for local/cloud LLM control-plane."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.config import settings
from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.llm_integration.dispatch_service import get_dispatch_service
from backend.services.llm_integration.types import DispatchRequest

router = APIRouter(dependencies=[Depends(secure_endpoint)])


class DispatchQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    route_mode: Optional[str] = Field(
        default=None, description="local_only | hybrid_auto | cloud_only"
    )
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=8192)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    local_conf_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


@router.post("/query/dispatch")
async def dispatch_query(
    req: DispatchQueryRequest,
    tenant: TenantContext = Depends(get_current_tenant),
):
    trace_id = str(uuid.uuid4())
    route_mode = req.route_mode or settings.resolved_hybrid_mode
    dispatch_service = get_dispatch_service()

    result = dispatch_service.generate(
        DispatchRequest(
            prompt=req.question,
            route_mode=route_mode,  # type: ignore[arg-type]
            tenant_id=tenant.tenant_id,
            trace_id=trace_id,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            top_p=req.top_p,
            local_conf_threshold=req.local_conf_threshold,
        )
    )

    if not result.success:
        raise HTTPException(
            status_code=502,
            detail={
                "trace_id": trace_id,
                "error": result.error or "dispatch_failed",
                "provider_used": result.provider,
                "route_mode": result.route_mode,
                "policy_decision": result.policy_decision,
            },
        )

    return {
        "trace_id": trace_id,
        "answer": result.text,
        "provider_used": result.provider,
        "route_mode": result.route_mode,
        "latency_ms": result.latency_ms,
        "usage": result.usage.to_dict(),
        "cost": result.cost.to_dict(),
        "model": result.model,
        "safety": {
            "redaction_applied": result.redaction_applied,
            "sensitive_hit_count": result.sensitive_hit_count,
            "redaction_categories": result.redaction_categories,
            "policy_decision": result.policy_decision,
        },
    }
