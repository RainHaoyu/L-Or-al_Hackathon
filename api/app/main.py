"""FastAPI 入口：/api/v1（统一信封 data + meta；CORS 全开便于前端本地联调）"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import data as D
from .modules import analyzer, recognition
from . import schemas as S

app = FastAPI(title="万象 Aura API", version="1.0.0",
              description="赛道三「无界体验家」双核心：QRA2 预警 + 香味可视化（数据层与前端共享）")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/v1/health", response_model=S.HealthResponse)
def health() -> dict:
    return {"data": {"status": "ok", "engine": analyzer.ENGINE_VERSION,
                     "perfumes": len(D.PERFUMES), "ifra_limits": len(D.IFRA["limits"]),
                     "ifra_banned": len(D.IFRA["banned"]), "dictEntries": len(D.DICT_ENTRIES)},
            "meta": {"engine": analyzer.ENGINE_VERSION}}


@app.get("/api/v1/products", response_model=S.ProductsResponse)
def products(q: str = "", limit: int = 8) -> dict:
    items = recognition._fuzzy_search(q, limit)
    return {"data": [{"id": p["id"], "brand": p["brand"], "name": p["name"], "en": p.get("en", ""),
                      "familyZh": p.get("familyZh", ""), "concentration": p.get("concentration", "")}
                     for p in items],
            "meta": {"engine": analyzer.ENGINE_VERSION}}


@app.post("/api/v1/recognition/image", response_model=S.ImageRecognitionResponse)
def recognize_image(req: S.ImageRequest) -> dict:
    b64, filename = recognition.normalize_image(req.image)
    result = recognition.get_vision_provider().recognize_image(b64, filename)
    return {"data": result, "meta": {"engine": analyzer.ENGINE_VERSION}}


@app.post("/api/v1/recognition/barcode", response_model=S.ImageRecognitionResponse)
def recognize_barcode(req: S.BarcodeRequest) -> dict:
    result = recognition.recognize_barcode(req.code)
    return {"data": result, "meta": {"engine": analyzer.ENGINE_VERSION}}


@app.post("/api/v1/analyze", response_model=S.AnalyzeResponse)
def analyze(req: S.AnalyzeRequest) -> dict:
    return analyzer.analyze(req.model_dump())
