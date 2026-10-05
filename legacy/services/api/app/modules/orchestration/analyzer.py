"""分析编排：识别解析 → 成分匹配 → QRA2 预警（核心①）+ 可视化（核心②）→ 汇报。

双核心互不依赖：可视化失败不影响预警输出，反之亦然（try/except 各自兜底）。
"""
from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.errors import ProductNotFoundError
from app.modules.ingredient.repository import IngredientRepository
from app.modules.qra2.engine import IngRef, QRA2Engine
from app.modules.orchestration.llm import SynesthesiaTexter
from app.modules.recognition.service import RecognitionService
from app.modules.scentmap.service import ScentmapService
from app.schemas.api import (
    AnalyzeData,
    AnalyzeRequest,
    ProductInfo,
    RecognitionChannel,
    VisionMode,
    VisionReport,
)

logger = logging.getLogger("unbounded.analyzer")


def _norm_conc(conc: float | dict) -> float:
    """浓度归一化：早期数据为 float(%)；v2 为 {typical_pct, basis, ifra_cat4_limit_pct, ...}。"""
    if isinstance(conc, dict):
        return float(conc.get("typical_pct") or 0.0)
    return float(conc)


class AnalyzerService:
    def __init__(self, settings: Settings, repo: IngredientRepository):
        self.s = settings
        self.repo = repo
        self.engine = QRA2Engine(repo.config)
        self.scentmap = ScentmapService(repo.families)
        self.texter = SynesthesiaTexter(settings)
        self.recognition = RecognitionService(settings, repo)

    async def analyze(self, req: AnalyzeRequest) -> AnalyzeData:
        product = self._resolve_product(req)
        channel, confidence = self._channel_of(req, product)

        # v2 香水库：ige_materials_hint 为天然材料名列表（IgE Ⅰ 型提示）
        ige_names = list((product or {}).get("ige_materials")
                         or (product or {}).get("ige_materials_hint") or [])
        ige_hits = [m for m in (self.repo.find_ige(n) for n in ige_names) if m]

        ing_refs: list[IngRef] = []
        for name, conc in (product or {}).get("allergen_concentrations", {}).items():
            ing_refs.append(IngRef((self.repo.find_allergen(name), _norm_conc(conc), name)))
        for name, conc in (req.product.manual_ingredients or {}).items():
            ing_refs.append(IngRef((self.repo.find_allergen(name), float(conc), name)))

        # —— 核心①：致敏预警（QRA2） ——
        risk = self.engine.assess(ing_refs, req.profile, req.oxidation, req.co_use)
        if ige_hits:
            names = "、".join(m.get("name_zh", "") for m in ige_hits)
            if req.profile.value == "rhinitis":
                risk.population.special_flags.append(f"IgE 速发提示：含 {names}，鼻炎人群注意呼吸道反应")
            else:
                risk.population.special_flags.append(f"含天然树脂/净油材料（IgE 潜在风险）：{names}")

        # —— 核心②：香味可视化 ——
        vision = self._build_vision(product, req)
        # 文案对所有输入通道都要生成（含纯手动成分表，此时 product 为 None）：
        # 之前整段被 `if product:` 包住，导致手动输入 families 有值但文案是空串。
        brand = product.get("brand", "") if product else ""
        name = product.get("name", "") if product else "手动输入成分表"
        text, source = await self.texter.generate(vision, brand, name)
        vision.synesthesia_text = text
        vision.text_source = source  # type: ignore[assignment]

        return AnalyzeData(
            product=ProductInfo(**{
                "product_id": product["id"], "brand": product.get("brand", ""),
                "name": product.get("name", ""), "concentration_type": product.get("concentration_type"),
                "barcode": product.get("barcode"), "is_golden": bool(product.get("is_golden")),
            }) if product else None,
            recognition_channel=channel,
            recognition_confidence=confidence,
            risk=risk,
            vision=vision,
        )

    # —— 内部 ——
    def _resolve_product(self, req: AnalyzeRequest) -> dict | None:
        p = self.repo.find_perfume(product_id=req.product.product_id, barcode=req.product.barcode,
                                   query=req.product.query)
        if p is None and not req.product.manual_ingredients:
            raise ProductNotFoundError()
        return p

    @staticmethod
    def _channel_of(req: AnalyzeRequest, product: dict | None) -> tuple[RecognitionChannel, float | None]:
        if req.product.barcode and product:
            return RecognitionChannel.barcode, 0.99
        if req.product.product_id and product:
            return RecognitionChannel.text, 0.95
        if req.product.query and product:
            return RecognitionChannel.text, 0.9
        return RecognitionChannel.manual, None

    def _build_vision(self, product: dict | None, req: AnalyzeRequest) -> VisionReport:
        mode = VisionMode.anosmic if req.profile == "anosmic" else (
            VisionMode.sensitive if req.profile == "sensitive" else VisionMode.normal)
        try:
            if product:
                vision = self.scentmap.build_vision(product, self.repo, mode)
            else:
                # 纯手动成分输入：无香水库信息时退化为按成分香调聚合的极简视图
                pseudo = {"families": self._manual_families(req), "radar": None, "pyramid": {}}
                vision = self.scentmap.build_vision(pseudo, self.repo, mode)
        except Exception as exc:  # 可视化失败不影响预警核心（错误隔离）
            logger.exception("vision build failed")
            # 但降级必须可观测：只隔离影响，不隐藏失败
            return VisionReport(mode=mode, degraded=True,
                                degrade_reason=f"可视化构建失败（{exc.__class__.__name__}）：已跳过色彩/雷达/金字塔")
        # 兜底自检：三要素全空说明上游数据异常，同样要显式标注而不是交一个空壳
        if not vision.families and not vision.palette and not vision.pyramid:
            logger.warning("vision built but empty: product=%s", (product or {}).get("id"))
            vision.degraded = True
            vision.degrade_reason = "可视化数据不足：该产品缺少可用香调构成/金字塔信息"
        return vision

    def _manual_families(self, req: AnalyzeRequest) -> dict[str, float]:
        from collections import Counter
        counter: Counter[str] = Counter()
        for name, conc in (req.product.manual_ingredients or {}).items():
            rec = self.repo.find_allergen(name)
            if rec and rec.get("families"):
                # 用浓度做权重，避免纯计数让微量成分与主成分等权
                counter[rec["families"][0]] += max(float(conc or 0.0), 0.01)
            else:
                counter["floral"] += 0.01
        return dict(counter) if counter else {"floral": 1.0}
