"""应用工厂：装配错误规范 / 请求链路 ID / CORS / 数据域加载。"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.modules.ingredient.repository import init_repository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repo = init_repository(settings.data_dir)
    logging.getLogger("unbounded").info(
        "seed loaded: %s (mock_mode=%s)", repo.stats(), settings.mock_mode)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="无界体验家 API", version="1.0.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        logging.getLogger("unbounded.access").info(
            "%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code,
            (time.perf_counter() - start) * 1000)
        return response

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                       allow_methods=["*"], allow_headers=["*"])
    install_error_handlers(app)
    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
