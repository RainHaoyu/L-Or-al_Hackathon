"""FastAPI 入口：/api/v1（统一信封 data + meta）。

三种跑法都能用：
1. **单进程交付 / 手机演示**（推荐）：`uvicorn app.main:app --host 0.0.0.0 --port 8001`
   —— 同一进程同时提供 API 与 `web/dist` 的预构建页面（同源，无跨域、无需 Node），
   手机连同一 Wi-Fi 打开 `http://<本机内网IP>:8001` 即可。
2. **开发模式**：前端 `npm run dev`（3000）+ 本服务（8001），CORS 全开便于联调。
3. 纯 API：前端不构建也能用，`/` 返回 503 并提示先 `npm run build`。

密钥只从环境变量或本地 `api/.env` 读（`.env` 已 gitignore，绝不入库）；
AI 不可用时全链路自动降级（模板文案 + mock 识别），不影响判定与数值。
"""

from __future__ import annotations

import os
from pathlib import Path

# .env 要在本地模块之前加载：llm / recognition 都从环境变量读 Key（.env 优先级低于进程环境变量）
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # 缺 python-dotenv 也能跑，只是不读 .env
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

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
                     "ifra_banned": len(D.IFRA["banned"]), "dictEntries": len(D.DICT_ENTRIES),
                     "eu26": len(D.EU26), "ige": len(D.IGE),
                     "materials": len(D.MATERIALS["natural"]) + int(D.MATERIALS.get("syntheticCount", 0))},
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


# ---------------------------------------------------------------- 前端静态托管
# 交付形态的关键：页面与 API 同源同端口，手机/评委只记一个地址，也没有跨域问题。
# 构建要求：`npm run build` 会读 web/.env.production（VITE_API_BASE 留空 → 相对请求）。
# 目录每请求解析一次，便于用 AURA_WEB_DIST 指向别处（测试与自定义部署）。
_DEFAULT_DIST = D.API_ROOT.parent / "web" / "dist"


def _dist_dir() -> Path:
    return Path(os.environ.get("AURA_WEB_DIST") or _DEFAULT_DIST)


def _missing_dist() -> JSONResponse:
    return JSONResponse(status_code=503, content={
        "error": {"code": "web_dist_missing",
                  "message": "前端未构建：先 cd web && npm run build（交付包已带预构建 dist）"}})


@app.get("/", include_in_schema=False)
def index():
    d = _dist_dir()
    if not (d / "index.html").is_file():
        return _missing_dist()
    return FileResponse(d / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """静态资源直出；客户端路由（/report、/vision…）回退 index.html。

    - 未知的 `/api/...` 返回 JSON 404，不能回退成 HTML（否则前端拿到 200 HTML 会解析失败）
    - 路径穿越（`../`）不允许读到 dist 之外
    - 显式注册的 API 路由在上面，不受本兜底影响
    """
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={
            "error": {"code": "not_found", "message": f"未知接口：/{full_path}"}})
    d = _dist_dir()
    index_file = d / "index.html"
    if not index_file.is_file():
        return _missing_dist()
    if full_path:
        root = d.resolve()
        candidate = (d / full_path).resolve()
        if candidate.is_file() and (root == candidate.parent or root in candidate.parents):
            return FileResponse(candidate)
    return FileResponse(index_file)
