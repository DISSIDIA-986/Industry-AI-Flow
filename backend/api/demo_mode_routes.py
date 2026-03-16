"""Demo mode management API routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.security.context import TenantContext
from backend.security.dependencies import get_current_tenant, secure_endpoint
from backend.services.demo_mode_service import ALLOWED_DEMO_MODES, get_demo_mode_service

router = APIRouter(
    prefix="/api/v1/demo", tags=["demo-mode"], dependencies=[Depends(secure_endpoint)]
)


def _can_manage_demo_mode(tenant: TenantContext) -> bool:
    role_set = set(tenant.roles or [])
    return bool({"admin", "ops", "platform_admin"} & role_set)


class DemoModeUpdateRequest(BaseModel):
    mode: str = Field(..., min_length=1, max_length=64)
    allow_cloud_override: Optional[bool] = None


@router.get("/mode")
async def get_demo_mode(
    tenant: TenantContext = Depends(get_current_tenant),
) -> Dict[str, Any]:
    del tenant
    service = get_demo_mode_service()
    return {
        "success": True,
        **service.get_state(),
    }


@router.post("/mode")
async def update_demo_mode(
    request: DemoModeUpdateRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> Dict[str, Any]:
    if not _can_manage_demo_mode(tenant):
        raise HTTPException(
            status_code=403, detail="Forbidden demo mode management scope"
        )

    mode = (request.mode or "").strip().lower()
    if mode not in ALLOWED_DEMO_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"mode must be one of: {sorted(ALLOWED_DEMO_MODES)}",
        )

    service = get_demo_mode_service()
    state = service.set_mode(mode)
    if request.allow_cloud_override is not None:
        state = service.set_cloud_override(request.allow_cloud_override)

    return {
        "success": True,
        **state,
    }


@router.get("/replay/health")
async def get_scripted_replay_health(
    tenant: TenantContext = Depends(get_current_tenant),
) -> Dict[str, Any]:
    del tenant
    service = get_demo_mode_service()
    state = service.get_state()
    return {
        "success": True,
        "mode": state["mode"],
        "scripted_replay_enabled": state["profile"]["scripted_replay_enabled"],
        "scenario_count": state["replay_scenarios"],
    }
