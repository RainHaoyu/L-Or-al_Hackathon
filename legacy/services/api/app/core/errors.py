"""统一错误规范：所有错误以同一信封返回，前端零分支处理。

    { "error": { "code": "INGREDIENT_NOT_FOUND", "message": "...", "details": {...} },
      "meta": { "request_id": "...", "engine": "qra2@1.0.0" } }
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings


class AppError(Exception):
    status_code = 400

    def __init__(self, code: str, message: str, details: dict | None = None, status_code: int | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class ProductNotFoundError(AppError):
    status_code = 404

    def __init__(self, message: str = "未匹配到香水产品，请手动确认或输入"):
        super().__init__("PRODUCT_NOT_FOUND", message)


class IngredientDataError(AppError):
    status_code = 422

    def __init__(self, message: str, details: dict | None = None):
        super().__init__("INGREDIENT_DATA_ERROR", message, details)


def install_error_handlers(app: FastAPI) -> None:
    settings = get_settings()

    def envelope(request: Request, code: str, message: str, details: dict, status: int) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message, "details": details},
                "meta": {
                    "request_id": getattr(request.state, "request_id", None),
                    "engine": settings.engine_version,
                },
            },
        )

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return envelope(request, exc.code, exc.message, exc.details, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return envelope(request, "VALIDATION_ERROR", "请求参数校验失败", {"errors": exc.errors()[:10]}, 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return envelope(request, f"HTTP_{exc.status_code}", str(exc.detail), {}, exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        return envelope(request, "INTERNAL_ERROR", f"服务内部错误：{exc.__class__.__name__}", {}, 500)
