"""阶段 5 · LLM 编排：通感文案

- Prompt 按三种 VisionMode 外置（PROMPTS 常量，调优不改代码）
- 三级兜底：qwen-max → qwen-plus → 规则模板（无 Key / 断网时全链路仍可用）
- LLM 不参与风险判定，只生成通感文字
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .. import data as D

PROMPTS: dict[str, str] = {
    "normal": (
        "你是调香评论家。用两三句中文通感化描述这瓶香水，让普通用户「闻不到也能想象」。\n"
        "香调组成（占比降序）：{mix}\n官方香调：{family_zh}\n品鉴关键词：{keywords}\n"
        "要求：具象、有画面感，不要列数据，不要夸张营销腔。"
    ),
    "anosmia": (
        "你是为嗅觉障碍人群服务的调香描述者。用户闻不到气味，请用加长篇幅（四五句）的中文，"
        "按前调开场、中调主体、后调尾韵的顺序，把气味翻译成视觉与触觉画面。\n"
        "前调：{top}\n中调：{heart}\n后调：{base}\n香调组成：{mix}\n品鉴关键词：{keywords}\n"
        "要求：每句都要有具体意象（颜色/材质/温度/场景），禁止使用「香」字堆砌。"
    ),
    "sensitive": (
        "你是为敏感肌人群服务的香调顾问。用两三句中文客观描述这瓶香水的气味画像，"
        "克制、不营销，如涉及高挥发香材请顺带提醒。\n香调组成：{mix}\n品鉴关键词：{keywords}"
    ),
}

_TIER = ["qwen-max", "qwen-plus"]
_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
# LLM 阶段**总预算**（秒），两档共享；不是「每档各自重来一遍」。
#
# 取值依据（实测 2026-10-05，qwen-max 单次调用）：
#   normal    2.9–4.5 s（输出 85–126 字）
#   sensitive 2.8–3.6 s（84–126 字）
#   anosmia   7.7–9.6 s（296–371 字：prompt 要求四五句具体意象，输出长约 3 倍）
#
# 前端 web/src/lib/api.ts 的 ANALYZE_TIMEOUT 按「引擎约 5 s + 本预算」推导：
#   normal / sensitive：13 s > 5 + 6
#   anosmia           ：19 s > 5 + 12
# 该不变式（前端超时 > 引擎 5 s + 本预算）由 api/tests/test_llm_budget.py 读前端文件断言。
#
# 为什么是「总预算」而不是「每档超时」：两档串行时，若每档各自超时，
# 第一档耗尽超时后第二档还会再来一遍，最坏耗时直接翻倍并超过前端超时
# （旧值 _TIMEOUT=5 就是这个毛病：anosmia 实测 7.7–9.6 s，第一档必被 abort）。
_BUDGET: dict[str, float] = {"normal": 6.0, "sensitive": 6.0, "anosmia": 12.0}
# 剩余预算低于此值就不再尝试下一档：与其发一个几乎注定超时的请求，不如立刻落模板
_MIN_ATTEMPT = 0.4


def _fill_prompt(mode: str, perfume: dict[str, Any]) -> str:
    mix = "、".join(
        f"{D.FAMILIES[m['family']]['name']}{round(m['share'])}%" for m in _composition(perfume)
    )
    pyramid = perfume.get("pyramid", [])
    top = "、".join(n["name"] for n in pyramid[0]["notes"]) if pyramid else ""
    heart = "、".join(n["name"] for n in pyramid[1]["notes"]) if len(pyramid) > 1 else ""
    base = "、".join(n["name"] for n in pyramid[2]["notes"]) if len(pyramid) > 2 else ""
    return PROMPTS.get(mode, PROMPTS["normal"]).format(
        mix=mix, family_zh=perfume.get("familyZh", ""), keywords=perfume.get("keywords", ""),
        top=top, heart=heart, base=base,
    )


def _composition(perfume: dict[str, Any]) -> list[dict[str, Any]]:
    agg: dict[str, float] = {}
    for layer in perfume.get("pyramid", []):
        n = max(len(layer["notes"]), 1)
        for note in layer["notes"]:
            agg[note["family"]] = agg.get(note["family"], 0) + layer["weight"] / n
    return sorted(({"family": k, "share": v} for k, v in agg.items()), key=lambda x: -x["share"])


def _base_synesthesia(perfume: dict[str, Any]) -> str:
    """基础通感文案（与前端 aura.ts buildSynthesis 同规则；JSON 数据不含该字段，两端各自生成）"""
    mix = _composition(perfume)
    if not mix:
        return ""
    dom = D.FAMILIES[mix[0]["family"]]
    second = D.FAMILIES[mix[1]["family"]] if len(mix) > 1 else None
    head = f"以{dom['name']}为骨、{second['name']}为肉。" if second else f"一支纯粹的{dom['name']}。"
    kw = perfume.get("keywords") or ""
    return f"{head}{dom['scene']}{'；' + kw if kw else ''}。"


def _template(perfume: dict[str, Any], mode: str) -> str:
    base = perfume.get("synesthesia") or _base_synesthesia(perfume)
    if mode == "anosmia":
        mix = _composition(perfume)
        fam = D.FAMILIES.get(perfume.get("familyKey", ""), None)
        lead = f"这是一支以{fam['name']}为主导的作品：{fam['scene']}。" if fam else ""
        layers = "；".join(
            f"{l['layer']}由{'、'.join(n['name'] for n in l['notes'])}铺开" for l in perfume.get("pyramid", [])
        )
        return lead + (layers + "。" if layers else "") + base
    return base


def synthesize(perfume: dict[str, Any], mode: str) -> tuple[str, str, bool]:
    """返回 (文案, 实际使用的模型, 是否 LLM)。三级兜底，任何异常都落模板。

    两档模型共享 `_BUDGET[mode]` 的总预算：每档拿到的是**剩余**预算，
    因此无论第一档是快速失败（额度/网络）还是慢到超时，总耗时都被预算封顶。
    """
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not key:
        return _template(perfume, mode), "template", False
    prompt = _fill_prompt(mode, perfume)
    deadline = time.monotonic() + _BUDGET.get(mode, _BUDGET["normal"])
    for model in _TIER:
        left = deadline - time.monotonic()
        if left < _MIN_ATTEMPT:
            break  # 预算已用尽：宁可立刻给模板，也不让前端等到超时
        try:
            r = httpx.post(
                _URL,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8},
                timeout=left,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text, model, True
        except Exception:
            continue
    return _template(perfume, mode), "template", False
