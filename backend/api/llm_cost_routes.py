"""LLM usage and budget governance API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.llm_integration.cost_tracker import BudgetPolicy, cost_tracker

router = APIRouter(dependencies=[Depends(secure_endpoint)])


def _can_manage_target_tenant(actor: TenantContext, target_tenant_id: str) -> bool:
    if actor.tenant_id == target_tenant_id:
        return True
    role_set = set(actor.roles or [])
    return bool({"admin", "ops", "platform_admin"} & role_set)


class BudgetPolicyRequest(BaseModel):
    monthly_budget_usd: float = Field(..., ge=0)
    soft_limit_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    hard_limit_ratio: float = Field(default=1.0, ge=0.0, le=2.0)
    policy_mode: str = Field(default="local_only")


@router.get("/llm/usage")
async def get_llm_usage(
    days: int = Query(default=30, ge=1, le=365),
    provider: str | None = Query(default=None),
    tenant_id: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_current_tenant),
):
    target_tenant_id = tenant_id or tenant.tenant_id
    if not _can_manage_target_tenant(tenant, target_tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden tenant scope")
    return cost_tracker.get_usage_summary(
        tenant_id=target_tenant_id, days=days, provider=provider
    )


@router.get("/llm/budget/{tenant_id}")
async def get_budget_policy(
    tenant_id: str,
    tenant: TenantContext = Depends(get_current_tenant),
):
    if not _can_manage_target_tenant(tenant, tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden tenant scope")

    policy = cost_tracker.get_budget_policy(tenant_id)
    monthly_spend = cost_tracker.get_monthly_spend(tenant_id)
    budget_eval = cost_tracker.evaluate_budget(tenant_id)

    return {
        "tenant_id": tenant_id,
        "policy": policy.__dict__ if policy else None,
        "current_month_spend_usd": round(monthly_spend, 6),
        "budget_evaluation": budget_eval,
    }


@router.post("/llm/budget/{tenant_id}")
async def upsert_budget_policy(
    tenant_id: str,
    req: BudgetPolicyRequest,
    tenant: TenantContext = Depends(get_current_tenant),
):
    if not _can_manage_target_tenant(tenant, tenant_id):
        raise HTTPException(status_code=403, detail="Forbidden tenant scope")
    if req.hard_limit_ratio < req.soft_limit_ratio:
        raise HTTPException(
            status_code=400, detail="hard_limit_ratio must be >= soft_limit_ratio"
        )
    if req.policy_mode not in {"local_only", "block"}:
        raise HTTPException(
            status_code=400, detail="policy_mode must be local_only or block"
        )

    policy = BudgetPolicy(
        tenant_id=tenant_id,
        monthly_budget_usd=req.monthly_budget_usd,
        soft_limit_ratio=req.soft_limit_ratio,
        hard_limit_ratio=req.hard_limit_ratio,
        policy_mode=req.policy_mode,
    )
    saved = cost_tracker.upsert_budget_policy(policy)
    return {"success": True, "policy": saved.__dict__}
