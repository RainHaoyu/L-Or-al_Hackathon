"""识别域 Provider 适配器（v3 §1.3 四通道：瓶身图像 / 条形码 / 文字搜索 / 成分OCR）。

云端模型统一阿里云百炼：
- 图像通道 qwen-vl-max（DashScope OpenAI 兼容模式）
- 条码/OCR 通道预留阿里云视觉智能 & 读光 OCR 凭证位（未配置时走本地/mock）
所有通道错误被隔离：单通道失败仅降级该通道，不阻断整体识别。
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import Settings

VL_PROMPT = (
    "你是香水瓶身识别助手。请观察图片中的香水产品，返回严格 JSON（不要多余文字）："
    '{"brand": "品牌名（不可辨识填空串）", "name": "产品名（不可辨识填空串）", '
    '"confidence": 0到1的置信度小数}。若图片中不是香水，confidence 设为 0。'
)


class ChannelError(Exception):
    """单通道失败（由 service 捕获降级，不向外扩散）。"""


@dataclass
class RawVisionResult:
    brand: str = ""
    name: str = ""
    confidence: float = 0.0
    provider: str = "mock"


@dataclass
class RecognitionResult:
    candidates: list = field(default_factory=list)
    best: object | None = None
    needs_manual: bool = False
    message: str = ""


class VisionProvider(Protocol):
    async def recognize_image(self, image: bytes) -> RawVisionResult: ...


class QwenVisionProvider:
    """百炼 qwen-vl-max（阿里云统一模型矩阵）。"""

    def __init__(self, settings: Settings):
        self.s = settings

    async def recognize_image(self, image: bytes) -> RawVisionResult:
        if self.s.mock_mode:
            raise ChannelError("未配置 DASHSCOPE_API_KEY，图像通道进入 mock")
        b64 = base64.b64encode(image).decode()
        payload = {
            "model": self.s.qwen_vision_model,
            "temperature": 0,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": VL_PROMPT},
                ],
            }],
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.s.dashscope_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.s.dashscope_api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise ChannelError(f"qwen-vl 调用失败：{e.__class__.__name__}") from e
        try:
            m = re.search(r"\{.*\}", content, re.S)
            data = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError as e:
            raise ChannelError("qwen-vl 返回非 JSON") from e
        conf = float(data.get("confidence", 0) or 0)
        return RawVisionResult(brand=str(data.get("brand", "")), name=str(data.get("name", "")),
                               confidence=min(max(conf, 0.0), 1.0), provider="qwen-vl-max")


class MockVisionProvider:
    """演示兜底：按图片字节哈希确定性挑选库内产品（mock 模式/线上故障时自动启用）。"""

    def __init__(self, product_names: list[tuple[str, str]]):
        self.names = product_names or [("", "未知香水")]

    async def recognize_image(self, image: bytes) -> RawVisionResult:
        h = int(hashlib.sha256(image).hexdigest(), 16)
        brand, name = self.names[h % len(self.names)]
        return RawVisionResult(brand=brand, name=name, confidence=0.62, provider="mock")


def parse_barcode(text: str) -> str:
    digits = re.sub(r"\D", "", text or "")
    return digits


async def ocr_ingredients(image: bytes, settings: Settings) -> list[str]:
    """成分表 OCR（读光 OCR 凭证位预留，未配置时 mock 返回空并提示手动输入）。"""
    if not (settings.aliyun_access_key_id and settings.aliyun_access_key_secret):
        raise ChannelError("读光 OCR 未配置凭证（ALIYUN_ACCESS_KEY_ID/SECRET），请手动输入成分")
    # TODO(读光OCR): 接入 ocr-api.cn-hangzhou.aliyuncs.com 通用+表格识别
    raise ChannelError("读光 OCR 通道尚未上线")
