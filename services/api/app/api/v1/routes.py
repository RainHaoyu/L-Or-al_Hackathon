"""/api/v1 路由（版本化；破坏性变更走 v2）。"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, UploadFile

from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.ingredient.repository import get_repository
from app.modules.orchestration.analyzer import AnalyzerService
from app.schemas.api import (
    AdminStats,
    AnalyzeRequest,
    Envelope,
    IngredientSummary,
    ProductSummary,
    RecognitionData,
)

logger = logging.getLogger("unbounded.api")
router = APIRouter()


def _meta(request: Request) -> dict:
    s = get_settings()
    return {
        "request_id": getattr(request.state, "request_id", None),
        "engine": s.engine_version,
        "models": {"vision": s.qwen_vision_model, "text": s.qwen_text_model},
        "mock_mode": s.mock_mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
async def health(request: Request):
    s = get_settings()
    return {"data": {"status": "ok", "engine": s.engine_version, "mock_mode": s.mock_mode},
            "meta": _meta(request)}


@router.get("/products")
async def list_products(request: Request, q: str = "", limit: int = 8):
    repo = get_repository()
    items = [ProductSummary(
        product_id=p["id"], brand=p.get("brand", ""), name=p.get("name", ""),
        concentration_type=p.get("concentration_type"),
        families=list(p.get("families", {}).keys()), is_golden=bool(p.get("is_golden")),
    ) for p in repo.search_products(q, limit=limit)] if q else [
        ProductSummary(product_id=p["id"], brand=p.get("brand", ""), name=p.get("name", ""),
                       concentration_type=p.get("concentration_type"),
                       families=list(p.get("families", {}).keys()), is_golden=bool(p.get("is_golden")))
        for p in repo.perfumes[:limit]]
    return {"data": {"items": items}, "meta": _meta(request)}


@router.get("/ingredients")
async def list_ingredients(request: Request, q: str = "", limit: int = 10):
    repo = get_repository()
    items = [IngredientSummary(
        inci=a.get("inci", ""), name_zh=a.get("name_zh", ""), cas=a.get("cas"),
        tier=a.get("tier"), banned_eu=bool(a.get("banned_eu")),
        oxidation_prone=bool(a.get("oxidation_prone")), note=a.get("note"),
        data_status="ok" if a.get("nesil") else "pending_enrichment",
    ) for a in repo.search_allergens(q, limit=limit)]
    return {"data": {"items": items}, "meta": _meta(request)}


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    service = AnalyzerService(get_settings(), get_repository())
    data = await service.analyze(req)
    return {"data": data, "meta": _meta(request)}


@router.post("/recognition/image")
async def recognition_image(file: UploadFile, request: Request):
    service = AnalyzerService(get_settings(), get_repository()).recognition
    image = await file.read()
    if not image:
        raise AppError("EMPTY_IMAGE", "上传图片为空")
    result = await service.by_image(image)
    return {"data": RecognitionData(candidates=result.candidates, best=result.best,
                                    needs_manual=result.needs_manual, message=result.message),
            "meta": _meta(request)}


@router.post("/recognition/barcode")
async def recognition_barcode(body: dict, request: Request):
    service = AnalyzerService(get_settings(), get_repository()).recognition
    result = service.by_barcode(str(body.get("barcode", "")))
    return {"data": RecognitionData(candidates=result.candidates, best=result.best,
                                    needs_manual=result.needs_manual, message=result.message),
            "meta": _meta(request)}


@router.get("/recognition/text")
async def recognition_text(request: Request, q: str, limit: int = 5):
    service = AnalyzerService(get_settings(), get_repository()).recognition
    result = service.by_text(q, limit=limit)
    return {"data": RecognitionData(candidates=result.candidates, best=result.best,
                                    needs_manual=result.needs_manual, message=result.message),
            "meta": _meta(request)}


# —— Admin（后台升级接口） ——
@router.post("/admin/ingredients/import")
async def admin_import_ingredients(body: dict, request: Request):
    """热更新致敏原库：{"items": [ {...allergen records...} ]}，无需重新部署。"""
    items = body.get("items")
    if not isinstance(items, list) or not items:
        raise AppError("INVALID_IMPORT", "body 需包含非空 items 数组")
    repo = get_repository()
    count = repo.reload_allergens(items)
    return {"data": {"imported": count, "stats": AdminStats(**repo.stats()).model_dump()},
            "meta": _meta(request)}


@router.get("/admin/stats")
async def admin_stats(request: Request):
    repo = get_repository()
    return {"data": AdminStats(**repo.stats()).model_dump(), "meta": _meta(request)}
