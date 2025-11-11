"""Request-scoped context helpers for multi-tenant support."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TenantContext:
    """Represents the tenant/user making the current API call."""

    tenant_id: str
    api_key: Optional[str] = None
    user_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    ip_address: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    def is_anonymous(self) -> bool:
        return not self.api_key and not self.user_id


_tenant_ctx: ContextVar[Optional[TenantContext]] = ContextVar(
    "tenant_context", default=None
)


def set_tenant_context(context: TenantContext) -> TenantContext:
    """Store the current tenant context."""
    _tenant_ctx.set(context)
    return context


def get_tenant_context() -> Optional[TenantContext]:
    """Return the tenant context for the current coroutine, if any."""
    return _tenant_ctx.get()
