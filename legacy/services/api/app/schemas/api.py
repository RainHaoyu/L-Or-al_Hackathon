"""API 契约（前后端唯一真源）。

前端 TS 类型在 apps/web/src/modules/shared/api-types.ts 手工镜像，
后续可改为从 /api/v1/openapi.json 自动生成（升级接口文档见 README）。
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# —— 枚举 ——


class PopulationKey(str, Enum):
    healthy = "healthy"
    sensitive = "sensitive"
    pregnant = "pregnant"
    rhinitis = "rhinitis"
    anosmic = "anosmic"


class RiskLevel(str, Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class EvidenceLevel(str, Enum):
    documented = "documented"      # 文档/公开数据支撑
    indicative = "indicative"      # demo 估计值（引擎已加保守惩罚并标注）
    insufficient = "insufficient"  # 数据不足（不静默降级，显式提示）


class RecognitionChannel(str, Enum):
    barcode = "barcode"
    image = "image"
    text = "text"
    manual = "manual"


class VisionMode(str, Enum):
    anosmic = "anosmic"    # 失嗅模式：侧重画面/质地/情绪
    normal = "normal"      # 普通模式
    sensitive = "sensitive"  # 敏感模式：温和提示语气


# —— 请求 ——


class ProductRef(BaseModel):
    """产品引用：四通道任选其一（product_id / barcode / 名称模糊搜索 / 手动成分表）。"""
    product_id: str | None = None
    barcode: str | None = None
    query: str | None = Field(None, description="品牌/品名模糊搜索")
    manual_ingredients: dict[str, float] | None = Field(
        None, description="手动输入成分表 {INCI名: 浓度%}（置信度降级通道）")


class OxidationInput(BaseModel):
    opened_days: float = Field(0, ge=0, description="开封天数")
    temp_c: float = Field(25, ge=-10, le=60, description="储存温度℃")
    light: float = Field(0.3, ge=0, le=1, description="光照 0避光-1强光")


class AnalyzeRequest(BaseModel):
    product: ProductRef
    profile: PopulationKey = PopulationKey.healthy
    oxidation: OxidationInput = OxidationInput()
    co_use: dict[str, float] = Field(
        default_factory=dict,
        description="聚合暴露（QRA2）：共使用产品 {类型: 该成分相对浓度比}，类型见 config.aggregate_exposure")


# —— 结果模型 ——


class IngredientFinding(BaseModel):
    inci: str
    name_zh: str
    cas: str | None = None
    concentration_pct: float | None = None
    tier: str | None = None
    high_frequency: bool = False
    banned_eu: bool = False
    oxidation_prone: bool = False
    note: str | None = None
    # QRA2 计算结果
    nesil: float | None = None
    saf: float | None = None
    ael: float | None = None
    cel_p50: float | None = None
    cel_p90: float | None = None
    cel_p99: float | None = None
    margin_p50: float | None = None
    margin_p90: float | None = None
    margin_p99: float | None = None
    decision_percentile: str | None = Field(None, description="本人群采用的判定分位线 P90/P99")
    level: RiskLevel | None = None
    gate: str | None = Field(None, description="主导闸门：qra2 / ifra / clinical / banned")
    evidence_level: EvidenceLevel | None = None
    data_note: str | None = None


class OxidationFinding(BaseModel):
    applicable: bool = False
    substances: list[str] = Field(default_factory=list, description="受氧化影响的成分")
    d_value: float | None = None
    level: RiskLevel = RiskLevel.green
    advice: str | None = None
    model_note: str = "估算模型（v3 §2.2：概率性提示并明标估算）"


class PopulationFinding(BaseModel):
    population: PopulationKey
    threshold_multiplier: float = Field(1.0, description="T_pop = α×β，判定余量需 ≥ T_pop")
    percentile_policy: str
    special_flags: list[str] = Field(default_factory=list, description="交叉反应/生殖毒性/呼吸道/氧化强调")


class RiskReport(BaseModel):
    overall_level: RiskLevel
    ingredients: list[IngredientFinding] = Field(default_factory=list)
    data_insufficient: list[str] = Field(default_factory=list, description="数据不足成分（显式列出，不静默降级）")
    oxidation: OxidationFinding = OxidationFinding()
    population: PopulationFinding
    summary: str = ""


class PyramidNote(BaseModel):
    name: str
    weight: float = 1.0
    family: str | None = None


class VisionReport(BaseModel):
    mode: VisionMode
    families: list[dict] = Field(default_factory=list, description="[{key,name_zh,weight}]")
    palette: list[str] = Field(default_factory=list, description="色块（宽度=香调权重）")
    gradient_direction: int = 135
    motion: dict = Field(default_factory=dict, description="粒子动画参数（类型/数量/速度/形状）")
    mood_label: str = ""
    radar: dict[str, float] = Field(default_factory=dict, description="五维：清新/甜/浓郁/暖/持久")
    pyramid: dict[str, list[PyramidNote]] = Field(default_factory=dict, description="前中后调图层（时序）")
    synesthesia_text: str = ""
    text_source: Literal["qwen", "template"] = "template"
    # 降级可观测性：可视化构建失败或数据不足时置 True 并给出原因，不静默交付空壳
    degraded: bool = False
    degrade_reason: str | None = None


class ProductInfo(BaseModel):
    product_id: str
    brand: str
    name: str
    concentration_type: str | None = None
    barcode: str | None = None
    is_golden: bool = False


class AnalyzeData(BaseModel):
    product: ProductInfo | None = None
    recognition_channel: RecognitionChannel = RecognitionChannel.manual
    recognition_confidence: float | None = None
    risk: RiskReport
    vision: VisionReport


class Meta(BaseModel):
    request_id: str | None = None
    engine: str = "qra2@1.0.0"
    models: dict[str, str] = Field(default_factory=dict)
    mock_mode: bool = False
    generated_at: str = ""


class Envelope(BaseModel):
    data: AnalyzeData
    meta: Meta


# —— 识别 ——


class RecognitionCandidate(BaseModel):
    product_id: str
    brand: str
    name: str
    confidence: float
    source: RecognitionChannel


class RecognitionData(BaseModel):
    candidates: list[RecognitionCandidate] = Field(default_factory=list)
    best: RecognitionCandidate | None = None
    needs_manual: bool = False
    message: str = ""


# —— 产品搜索 / 成分搜索 ——


class ProductSummary(BaseModel):
    product_id: str
    brand: str
    name: str
    concentration_type: str | None = None
    families: list[str] = Field(default_factory=list)
    is_golden: bool = False


class IngredientSummary(BaseModel):
    inci: str
    name_zh: str
    cas: str | None
    tier: str | None
    banned_eu: bool
    oxidation_prone: bool
    note: str | None
    data_status: str = Field("ok", description="ok / pending_enrichment")


# —— Admin ——


class AdminStats(BaseModel):
    allergens: int
    ige_materials: int
    perfumes: int
    families: int
    config_version: str
    last_reload_at: str
