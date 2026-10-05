"""识别服务：通道编排 + 置信度降级策略（v3：置信度<0.7 提示手动确认/输入）。"""
from __future__ import annotations

from app.core.config import Settings
from app.modules.ingredient.repository import IngredientRepository
from app.modules.recognition.providers import (
    ChannelError,
    MockVisionProvider,
    QwenVisionProvider,
    RecognitionResult,
    parse_barcode,
)
from app.schemas.api import RecognitionCandidate, RecognitionChannel

MANUAL_THRESHOLD_DEFAULT = 0.7


class RecognitionService:
    def __init__(self, settings: Settings, repo: IngredientRepository):
        self.s = settings
        self.repo = repo
        self.vision = QwenVisionProvider(settings)
        self.mock_vision = MockVisionProvider(
            [(p.get("brand", ""), p.get("name", "")) for p in repo.perfumes])
        self.manual_threshold = float(
            repo.config.get("confidence", {}).get("recognition_manual_fallback", MANUAL_THRESHOLD_DEFAULT))

    # —— 条码通道（本地库优先） ——
    def by_barcode(self, barcode: str) -> RecognitionResult:
        digits = parse_barcode(barcode)
        p = self.repo.find_perfume(barcode=digits) if digits else None
        if p:
            best = RecognitionCandidate(product_id=p["id"], brand=p.get("brand", ""),
                                        name=p.get("name", ""), confidence=0.99,
                                        source=RecognitionChannel.barcode)
            return RecognitionResult(candidates=[best], best=best, message="条码精确匹配")
        return RecognitionResult(needs_manual=True,
                                 message="条码库未收录该商品，请改用拍照识别或名称搜索")

    # —— 文字搜索通道 ——
    def by_text(self, query: str, limit: int = 5) -> RecognitionResult:
        hits = self.repo.search_products(query, limit=limit)
        candidates = [
            RecognitionCandidate(product_id=p["id"], brand=p.get("brand", ""), name=p.get("name", ""),
                                 confidence=0.9 if i == 0 else 0.7, source=RecognitionChannel.text)
            for i, p in enumerate(hits)
        ]
        result = RecognitionResult(candidates=candidates)
        result.best = candidates[0] if candidates else None
        result.needs_manual = not candidates
        result.message = f"搜索到 {len(candidates)} 个候选" if candidates else "未搜索到产品，请手动输入成分"
        return result

    # —— 图像通道（qwen-vl-max，失败降级 mock 并标注） ——
    async def by_image(self, image: bytes) -> RecognitionResult:
        try:
            raw = await self.vision.recognize_image(image)
            provider_note = ""
        except ChannelError as e:
            raw = await self.mock_vision.recognize_image(image)
            provider_note = f"（线上通道不可用已降级 mock：{e}）"

        if raw.confidence <= 0.05:
            return RecognitionResult(needs_manual=True,
                                     message="未识别出香水产品，请手动确认或输入" + provider_note)

        hits = self.repo.search_products(f"{raw.brand} {raw.name}".strip(), limit=3)
        candidates = [
            RecognitionCandidate(product_id=p["id"], brand=p.get("brand", ""), name=p.get("name", ""),
                                 confidence=round(min(raw.confidence, 0.95), 3),
                                 source=RecognitionChannel.image)
            for p in hits
        ]
        best = candidates[0] if candidates else None
        needs_manual = best is None or best.confidence < self.manual_threshold
        msg = f"视觉识别：{raw.brand} {raw.name}（{raw.provider}, conf={raw.confidence:.2f}）{provider_note}"
        if needs_manual:
            msg += f"；置信度低于 {self.manual_threshold}，请手动确认候选或输入成分"
        return RecognitionResult(candidates=candidates, best=best, needs_manual=needs_manual, message=msg)
