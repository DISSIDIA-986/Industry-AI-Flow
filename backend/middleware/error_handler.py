"""Global error handling middleware for consistent responses."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.security.memory_guard import MemoryGuardExceeded

logger = logging.getLogger(__name__)


FRIENDLY_MESSAGES = {
    400: "提交的参数有误，请检查后重试。",
    401: "身份验证失败，请重新登录或检查凭证。",
    403: "您没有执行该操作的权限。",
    404: "资源不存在或已被移除。",
    422: "请求格式不正确，请确认字段是否完整。",
    429: "请求过于频繁，请稍后再试。",
    500: "系统繁忙，请稍后再试。",
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
            friendly = FRIENDLY_MESSAGES.get(exc.status_code, "请求未成功，请稍后重试。")
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
