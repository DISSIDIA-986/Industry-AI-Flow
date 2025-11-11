"""Centralized audit logging utilities."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.config import settings


class AuditLogger:
    """Writes JSONL audit logs for sensitive operations."""

    def __init__(self) -> None:
        self.log_path = settings.audit_log_file
        self._logger = logging.getLogger("audit")
        if not self._logger.handlers:
            handler = logging.FileHandler(self.log_path)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def log_event(
        self,
        *,
        action: str,
        tenant_id: str,
        status: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "tenant_id": tenant_id,
            "status": status,
            "user_id": user_id,
            "ip": ip_address,
            "detail": detail or {},
        }
        self._logger.info(json.dumps(payload, ensure_ascii=False))


audit_logger = AuditLogger()
