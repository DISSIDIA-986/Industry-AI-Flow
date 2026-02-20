"""Global error handling middleware for consistent responses."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.security.memory_guard import MemoryGuardExceeded

logger = logging.getLogger(__name__)


FRIENDLY_MESSAGES = {
    400: "The request is invalid. Please check your input.",
    401: "Authentication is required to access this resource.",
    403: "You are not allowed to perform this action.",
    404: "The requested resource was not found.",
    422: "Request validation failed. Please review the submitted fields.",
    429: "Too many requests. Please retry later.",
    500: "An internal server error occurred. Please try again later.",
}


def register_error_handlers(app: FastAPI) -> None:
    """Attach middleware for consistent error responses."""

    @app.middleware("http")
    async def _error_middleware(request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except MemoryGuardExceeded as exc:
            logger.warning(
                "Memory guard exceeded",
                extra={"route": request.url.path, "usage_mb": exc.usage_mb},
            )
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error_code": "MEMORY_LIMIT_EXCEEDED",
                    "message": "Service is temporarily unavailable due to high memory usage.",
                    "usage_mb": exc.usage_mb,
                    "limit_mb": exc.limit_mb,
                },
            )
        except HTTPException as exc:
            friendly = FRIENDLY_MESSAGES.get(
                exc.status_code, "An error occurred while processing your request."
            )
            detail = exc.detail if isinstance(exc.detail, str) else exc.detail
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error_code": getattr(exc, "error_code", "HTTP_ERROR"),
                    "message": friendly,
                    "detail": detail,
                },
                headers=exc.headers,
            )
        except Exception as exc:
            logger.exception(
                "Unhandled server error",
                extra={"route": request.url.path, "method": request.method},
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                },
            )
