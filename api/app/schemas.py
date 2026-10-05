"""对外契约（Pydantic）：openapi 唯一真源，前端类型由 scripts/gen_api_types.py 自动生成"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MetaModels(BaseModel):
    synesthesia: str = "template"
    recognition: str = "n/a"


class MetaDegraded(BaseModel):
    vision: bool = False
    reason: str = ""


class Meta(BaseModel):
    request_id: str = ""
    engine: str = ""
    models: MetaModels = MetaModels()
    degraded: MetaDegraded = MetaDegraded()
    error: str | None = None
    seed: int | None = None


class HealthData(BaseModel):
    status: str
    engine: str
    perfumes: int
    ifra_limits: int
    ifra_banned: int
    dictEntries: int


class HealthResponse(BaseModel):
    data: HealthData
    meta: Meta


class ProductBrief(BaseModel):
    id: str
    brand: str
    name: str
    en: str = ""
    familyZh: str = ""
    concentration: str = ""


class ProductsResponse(BaseModel):
    data: list[ProductBrief]
    meta: Meta


class Candidate(BaseModel):
    id: str
    brand: str
    name: str
    tag: str = ""


class RecognitionResult(BaseModel):
    status: Literal["ok", "confirm", "error"]
    confidence: float = 0.0
    product: ProductBrief | None = None
    candidates: list[Candidate] = []
    provider: str = ""
    note: str = ""
    error: str = ""


class ImageRecognitionResponse(BaseModel):
    data: RecognitionResult
    meta: Meta


class ImageRequest(BaseModel):
    image: str = Field(..., description="dataURL 或纯 base64")
    filename: str = Field("upload.jpg", description="文件名（mock 确定性哈希用）")


class BarcodeRequest(BaseModel):
    code: str


class AnalyzeRequest(BaseModel):
    product_id: str
    population: Literal["healthy", "sensitive", "pregnant", "rhinitis", "anosmic"] = "healthy"
    opened_months: float = 0
    storage: Literal["cool", "room", "hot"] = "room"
    mode: Literal["normal", "anosmia", "sensitive"] = "normal"


class Verdict(BaseModel):
    level: Literal["low", "mid", "high"]
    headline: str
    reasons: list[str]
    advice: str
    dominantGate: str
    hits: str


class IngredientRow(BaseModel):
    inci: str
    zh: str
    conc: str
    level: Literal["low", "mid", "high"]
    gate: str
    evidence: Literal["documented", "indicative", "insufficient"]
    note: str
    limitPct: float | None = None


class Oxidation(BaseModel):
    d: float
    months: float
    storage: str


class Panel(BaseModel):
    label: str
    name: str
    concPct: float
    ael: float | None
    p50: float | None
    p90: float | None
    p99: float | None
    marginPoint: float | None
    marginP99: float | None
    marginPolicy: float | None
    policy: str
    tPop: float


class SpecNote(BaseModel):
    name: str
    family: str
    color: str
    pct: int


class SpecLayer(BaseModel):
    layer: str
    weight: float
    color: str
    notes: list[SpecNote]


class SpecMixItem(BaseModel):
    family: str
    share: float
    color: str
    mood: str
    scene: str
    shape: str


class RadarPoint(BaseModel):
    dim: str
    v: float


class VisionSpec(BaseModel):
    degraded: bool
    degradeReason: str = ""
    primary: str = ""
    secondary: str = ""
    gradient: str = ""
    layers: list[SpecLayer] = []
    mix: list[SpecMixItem] = []
    moodWords: str = ""
    radar: list[RadarPoint] = []


class Synesthesia(BaseModel):
    text: str
    model: str
    isLlm: bool


class AnalyzeData(BaseModel):
    product: ProductBrief
    oxidation: Oxidation
    verdict: Verdict
    ingredients: list[IngredientRow]
    panel: Panel
    vision: VisionSpec
    synesthesia: Synesthesia


class AnalyzeResponse(BaseModel):
    data: AnalyzeData | None = None
    meta: Meta
