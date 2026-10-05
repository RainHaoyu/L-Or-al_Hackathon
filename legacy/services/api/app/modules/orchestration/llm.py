"""LLM 编排域 · 通感文案生成（qwen-max / 降级 qwen-plus）。

架构原则（v3："规则引擎保精准 + 大模型保灵活"）：
风险数字一律由 QRA2 规则引擎计算，LLM 仅负责自然语言通感文案，不参与任何风险判定。
Prompt 模板外置（后台可调优，见 README 升级接口）。
"""
from __future__ import annotations

import httpx

from app.core.config import Settings
from app.modules.scentmap.service import RADAR_ZH, synesthesia_template
from app.schemas.api import VisionMode, VisionReport

PROMPTS: dict[VisionMode, str] = {
    VisionMode.normal: (
        "你是香水通感文案作者。根据给定的香调构成、五维特征与前后调层次，写一段 80 字以内的中文通感描述，"
        "把气味翻译成颜色、画面与情绪。不要出现「闻起来」「香气」等嗅觉词汇以外的医学或风险表述。"
    ),
    VisionMode.anosmic: (
        "你是面向失嗅（嗅觉障碍）人群的香水体验文案作者。请完全通过视觉、触感、温度与情绪画面来描述这支香水，"
        "禁止使用「闻起来」「气味」等嗅觉词，80 字以内。这是一条「嗅觉替代通道」。"
    ),
    VisionMode.sensitive: (
        "你是面向敏感肌人群的温和香水文案作者。用轻柔、克制的语气描述香水的色彩与画面，80 字以内，"
        "可自然带一句「建议先小面积试用」，不要引起焦虑。"
    ),
}


def _vision_context(vision: VisionReport, brand: str, name: str) -> str:
    radar = "、".join(f"{RADAR_ZH.get(k, k)}{v:.1f}" for k, v in vision.radar.items())
    layers = "；".join(
        f"{'前调' if p == 'top' else '中调' if p == 'heart' else '后调'}：{'、'.join(n.name for n in ns)}"
        for p, ns in vision.pyramid.items())
    return (f"产品：{brand}·{name}\n香调构成：{vision.mood_label}，"
            f"{', '.join(f['name_zh'] + f"{f['weight']:.0%}" for f in vision.families)}\n"
            f"五维特征：{radar}\n层次：{layers}")


class SynesthesiaTexter:
    """qwen-max 优先，失败降级 qwen-plus，再失败降级本地模板（三级兜底）。"""

    def __init__(self, settings: Settings):
        self.s = settings

    async def generate(self, vision: VisionReport, brand: str, name: str) -> tuple[str, str]:
        """返回 (文案, 来源: qwen|template)。"""
        if not self.s.mock_mode:
            ctx = _vision_context(vision, brand, name)
            for model in (self.s.qwen_text_model, self.s.qwen_text_model_fallback):
                try:
                    text = await self._chat(PROMPTS[vision.mode], ctx, model)
                    if text:
                        return text.strip(), "qwen"
                except (httpx.HTTPError, KeyError, ValueError):
                    continue
        return synesthesia_template(vision, brand, name), "template"

    async def _chat(self, system_prompt: str, context: str, model: str) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.s.dashscope_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.s.dashscope_api_key}"},
                json={
                    "model": model, "temperature": 0.7, "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
