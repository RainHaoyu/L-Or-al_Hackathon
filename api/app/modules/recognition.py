"""阶段 4 · 识别层（四通道 + Provider 可插拔 + 置信度降级）

- 图像通道：QwenVLProvider（DashScope OpenAI 兼容，需 DASHSCOPE_API_KEY）→ MockProvider 兜底
  （哈希确定性选库内产品，置信度 0.62 < 0.7 → status=confirm + 候选列表，杜绝误识别直判）
- 条码通道：确定性映射演示库
- 文字搜索：difflib 模糊检索
- OCR：凭证未开通时直接引导手动输入（前端已实现手动兜底通道）
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import json
import os
from typing import Any, Protocol

import httpx

from .. import data as D

CONFIRM_THRESHOLD = 0.7


class RecognitionProvider(Protocol):
    name: str

    def recognize_image(self, image_base64: str, filename: str) -> dict[str, Any]: ...


def _fuzzy_search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    q = q.strip()
    if not q:
        return D.PERFUMES[:limit]
    scored = []
    for p in D.PERFUMES:
        hay = f"{p['brand']} {p['name']} {p.get('en', '')} {p.get('familyZh', '')} {p.get('keywords', '')}"
        score = difflib.SequenceMatcher(None, q.lower(), hay.lower()).ratio()
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]


def _candidate_brief(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": p["id"], "brand": p["brand"], "name": p["name"], "tag": p.get("familyZh", "")} for p in products]


class MockVisionProvider:
    """断网/无 Key 兜底：同名输入必得同一产品（哈希确定性），置信度恒 0.62 触发人工确认"""

    name = "mock"

    def recognize_image(self, image_base64: str, filename: str) -> dict[str, Any]:
        digest = hashlib.md5(f"{filename}:{len(image_base64 or '')}".encode()).hexdigest()
        pick = D.PERFUMES[int(digest[:8], 16) % len(D.PERFUMES)]
        return {
            "status": "confirm",
            "confidence": 0.62,
            "product": {"id": pick["id"], "brand": pick["brand"], "name": pick["name"]},
            "candidates": _candidate_brief([pick, *_fuzzy_search(pick["name"], 2)[1:3]]),
            "provider": self.name,
            "note": "mock 识别（未配置 DASHSCOPE_API_KEY）：置信度 0.62 低于 0.7，请人工确认",
        }


class QwenVisionProvider:
    """百炼 qwen-vl-max（OpenAI 兼容模式）；失败自动落回 mock"""

    name = "qwen-vl-max"
    URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def recognize_image(self, image_base64: str, filename: str) -> dict[str, Any]:
        try:
            payload = {
                "model": self.name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                            {"type": "text", "text": "识别这张香水产品图的品牌与产品名（中文）。"
                                                      "严格返回 JSON：{\"brand\":\"...\",\"name\":\"...\",\"confidence\":0.0-1.0}，不要输出其他内容。"},
                        ],
                    }
                ],
                "temperature": 0.1,
            }
            r = httpx.post(self.URL, headers={"Authorization": f"Bearer {self.api_key}"}, json=payload, timeout=12)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            info = json.loads(content[content.find("{"): content.rfind("}") + 1])
            conf = float(info.get("confidence", 0))
            query = f"{info.get('brand', '')} {info.get('name', '')}"
            cands = _fuzzy_search(query, 3)
            best = cands[0] if cands else None
            ratio = difflib.SequenceMatcher(None, query, f"{best['brand']}{best['name']}").ratio() if best else 0
            if best and conf >= CONFIRM_THRESHOLD and ratio >= 0.45:
                return {
                    "status": "ok", "confidence": conf,
                    "product": {"id": best["id"], "brand": best["brand"], "name": best["name"]},
                    "candidates": _candidate_brief(cands), "provider": self.name, "note": "",
                }
            return {
                "status": "confirm", "confidence": conf,
                "product": None, "candidates": _candidate_brief(cands),
                "provider": self.name,
                "note": f"置信度 {conf:.2f} 或匹配度不足，请人工确认",
            }
        except Exception:
            return MockVisionProvider().recognize_image(image_base64, filename)


def get_vision_provider() -> RecognitionProvider:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    return QwenVisionProvider(key) if key else MockVisionProvider()


def recognize_barcode(code: str) -> dict[str, Any]:
    code = "".join(ch for ch in code if ch.isdigit())
    if not code:
        return {"status": "error", "error": "条码为空", "candidates": []}
    pick = D.PERFUMES[int(code) % len(D.PERFUMES)]
    return {"status": "ok", "confidence": 0.99,
            "product": {"id": pick["id"], "brand": pick["brand"], "name": pick["name"]},
            "provider": "barcode-demo", "note": "演示库按条码确定性返回；正式版接 GTIN 数据库"}


def normalize_image(data_url_or_base64: str) -> tuple[str, str]:
    """前端可能传 dataURL 或纯 base64；返回 (纯 base64, filename)"""
    if data_url_or_base64.startswith("data:"):
        head, b64 = data_url_or_base64.split(",", 1)
        filename = "upload" + head.split("/")[1].split(";")[0]
        return b64, filename
    return data_url_or_base64, "upload.jpg"
