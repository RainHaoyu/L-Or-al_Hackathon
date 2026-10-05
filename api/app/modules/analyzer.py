"""阶段 5 · 分析编排器

主链路：产品/成分解析 → 风险判定（迷你四闸门 + QRA2 实算面板）
       → 可视化 spec → 通感文案（LLM 三级兜底）
双核心 try/except 错误隔离：可视化/文案失败只置 degraded，预警结论不受影响。
响应统一信封 meta（engine / models / degraded），版本可追溯。
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .. import data as D
from . import llm, qra2

ENGINE_VERSION = "aura-qra2/1.0"

_ADVICE = {
    "high": "停用这一瓶。同香型可换不含禁用成分的新批次；敏感体质换新品前，先在耳后做 48 小时小面积试用。",
    "mid": "可以留意着用：减半用量，避开破损皮肤与眼周；开封超过一年的批次建议尽快用完或更换。",
    "low": "正常使用即可。避光阴凉保存，开封一年内用完风味与安全性最佳。",
}
_HEADLINE = {"high": "这一瓶，暂时不建议使用", "mid": "这一瓶，留意着用", "low": "这一瓶，可以放心使用"}
_RANK = {"low": 0, "mid": 1, "high": 2}
_TERPENE_RE = re.compile(r"柠檬|香柠檬|佛手柑|柑橘|苦橙|橙皮|橙花|薰衣草")


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _profile(perfume: dict[str, Any]) -> dict[str, Any]:
    ingredients = perfume.get("ingredients", [])
    banned = [b for b in D.IFRA["banned"] if any(_norm(b["zh"]) in _norm(i) for i in ingredients)]
    limit_hits = []
    for l in D.IFRA["limits"]:
        aliases = {"香豆素": ["零陵香豆"], "香兰素": ["香草"]}
        hit = any(_norm(l["zh"]) in _norm(i) or any(_norm(a) in _norm(i) for a in aliases.get(l["zh"], [])) for i in ingredients)
        if hit:
            limit_hits.append(l)
    return {
        "banned": banned,
        "limitHits": limit_hits,
        "terpene": any(_TERPENE_RE.search(i or "") for i in ingredients),
        "musk": any("麝香" in (i or "") for i in ingredients),
        "load": "high" if len(limit_hits) >= 2 else ("mid" if len(limit_hits) == 1 else "low"),
    }


def evaluate(population: str, perfume: dict[str, Any], d: float) -> dict[str, Any]:
    prof = _profile(perfume)
    pop_name = next((p["name"] for p in [
        {"key": "healthy", "name": "健康成人"}, {"key": "sensitive", "name": "敏感肌"},
        {"key": "pregnant", "name": "孕期"}, {"key": "rhinitis", "name": "过敏性鼻炎"},
        {"key": "anosmic", "name": "失嗅人群"}] if p["key"] == population), "")
    level, gate = "low", "四道闸门均未触发"
    reasons: list[str] = []

    def set_level(lv: str, why: str, g: str) -> None:
        nonlocal level, gate
        reasons.append(why)
        if _RANK[lv] > _RANK[level]:
            level, gate = lv, g

    if prof["banned"]:
        names = "、".join(f"「{b['zh']}」（{b.get('reason') or b.get('control', '')}）" for b in prof["banned"])
        set_level("high", f"成分清单命中 {D.IFRA['amendment']} 完全禁用项：{names}。禁用闸门直接判红。", "禁用闸门")
    if population == "pregnant" and prof["musk"]:
        set_level("mid", "成分含麝香类：孕期画像对麝香保持保守，临床闸门给出黄灯提示，建议减频使用。", "临床闸门")
    if prof["terpene"] and d >= 0.5:
        harsh = population in ("sensitive", "anosmic")
        extra = "失嗅人群无法靠嗅觉察觉变质，氧化模型即嗅觉替代预警。" if population == "anosmic" else "建议敏感体质减用。"
        set_level("high" if harsh else "mid",
                  f"开封后氧化程度 D={d:.2f} 越过 0.5 高风险线，含萜烯香材氧化生成致敏氢过氧化物。{extra}", "氧化模型")
    elif prof["terpene"] and d >= 0.2 and population == "sensitive":
        set_level("mid", f"氧化程度 D={d:.2f} 进入中风险区间，敏感肌 α=3.0 收紧后建议减用。", "氧化模型")
    if population == "sensitive" and prof["load"] == "high":
        names = "、".join(l["zh"] for l in prof["limitHits"])
        set_level("mid", f"成分命中 {len(prof['limitHits'])} 项 IFRA Cat4 限量（{names}），敏感肌分位线升至 P99 后余量偏紧。", "QRA2 分位")
    if population == "pregnant" and prof["load"] == "high":
        set_level("mid", f"孕期画像下致敏原负载偏高（{'、'.join(l['zh'] for l in prof['limitHits'])}），建议降低使用频率。", "QRA2 分位")
    if population == "rhinitis" and prof["load"] != "low":
        reasons.append("鼻炎画像：高挥发性醛类（柠檬醛、肉桂醛）已加呼吸道刺激标注。")
    if not reasons:
        reasons.append(f"四道闸门均未触发：未命中 {D.IFRA['amendment']} 禁用清单，{pop_name}画像下分位余量充足，氧化程度 D={d:.2f} 处于低风险区间。")

    hits = f"{len(prof['limitHits']) + len(prof['banned'])} 项命中 IFRA Cat4 清单" + (
        f"（含禁用 {len(prof['banned'])}）" if prof["banned"] else "")
    return {"level": level, "headline": _HEADLINE[level], "reasons": reasons,
            "advice": _ADVICE[level], "dominantGate": gate, "hits": hits, "profile": prof}


def _panel_scenario(perfume: dict[str, Any]) -> dict[str, Any]:
    if perfume.get("synthetic"):
        return {"label": "黄金算例：柠檬烯 5%（教学样本，点估计 CEL=5.0）", "name": "d-Limonene", "concPct": 5.0}
    prof = _profile(perfume)
    if prof["terpene"]:
        return {"label": f"文献典型值情景：柠檬烯 0.8%（{perfume['name']} 含萜烯香材，按群体典型值）",
                "name": "d-Limonene", "concPct": 0.8}
    if prof["limitHits"]:
        hit = prof["limitHits"][0]
        if hit.get("limitPct"):
            return {"label": f"限值上限情景：{hit['zh']}（假设浓度 = Cat4 上限 {hit['limitPct']}%，最保守）",
                    "name": hit.get("en") or hit["zh"], "concPct": float(hit["limitPct"])}
    return {"label": "黄金算例示意：柠檬烯 5%（该香水未命中限量香材，展示方法论）", "name": "d-Limonene", "concPct": 5.0}


def build_ingredients(perfume: dict[str, Any], d: float, population: str) -> list[dict[str, Any]]:
    prof = _profile(perfume)
    rows: list[dict[str, Any]] = []
    if prof["terpene"]:
        typical = 5.0 if perfume.get("synthetic") else 0.8
        qra = qra2.analyze_ingredient("d-Limonene", typical, population)
        lin_level = "high" if d >= 0.5 else ("mid" if d >= 0.2 else "low")
        note = ("氧化程度越过 0.5，生成的氢过氧化物致敏性显著升高。" if d >= 0.5
                else "开封氧化中，敏感肌建议减用。" if d >= 0.2 else "氧化程度低，正常使用。")
        if qra["p99"] is not None:
            note += f" QRA2 实算（典型值 {typical:g}% 情景）：AEL {qra['ael']:.0f}，P99 {qra['p99']:.1f}，余量 {qra['marginP99']:.1f}。"
        lim = next((l for l in D.IFRA["limits"] if "柠檬烯" in l["zh"]), None)
        rows.append({"inci": "Limonene / Linalool", "zh": "柠檬烯 / 芳樟醇（萜烯族）",
                     "conc": f"典型值 {typical:g}%", "level": lin_level, "gate": "氧化叠加",
                     "evidence": "documented", "note": note, "limitPct": lim.get("limitPct") if lim else None})
    for l in prof["limitHits"]:
        rows.append({"inci": l.get("en") or l["zh"], "zh": l["zh"], "conc": "未知", "level": "low",
                     "gate": "IFRA Cat4 限值", "evidence": "documented",
                     "note": f"Cat4 成品上限 {l['limitPct']}%（CAS {l.get('cas', '')}）。该香水未披露此成分浓度，按文献典型值评估；{l.get('note', '')}。",
                     "limitPct": l.get("limitPct")})
    if prof["musk"]:
        rows.append({"inci": "Musk", "zh": "麝香类", "conc": "未知", "level": "low",
                     "gate": "临床提示", "evidence": "documented",
                     "note": "孕期画像对麝香类保持保守（判定层为孕期黄灯）。", "limitPct": None})
    if not rows:
        rows.append({"inci": "—", "zh": "未命中限量清单", "conc": "—", "level": "low",
                     "gate": "IFRA Cat4", "evidence": "documented",
                     "note": f"成分清单未命中 {D.IFRA['amendment']} 限量/禁用表。", "limitPct": None})
    return rows


def build_visual_spec(perfume: dict[str, Any]) -> dict[str, Any]:
    """可视化 spec（与前端 vision/engine 同规则；异常由调用方隔离）"""
    def hex2rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[0:6], 16) >> 16 & 255, int(h[0:6], 16) >> 8 & 255, int(h[0:6], 16) & 255

    def mix_hex(items: list[tuple[str, float]]) -> str:
        r = g = b = tw = 0.0
        for color, w in items:
            cr, cg, cb = hex2rgb(color)
            r += cr * w; g += cg * w; b += cb * w; tw += w
        if not tw:
            return "#888888"
        return f"rgb({round(r / tw)}, {round(g / tw)}, {round(b / tw)})"

    agg: dict[str, float] = {}
    layers = []
    for layer in perfume["pyramid"]:
        n = max(len(layer["notes"]), 1)
        for note in layer["notes"]:
            agg[note["family"]] = agg.get(note["family"], 0) + layer["weight"] / n
        layers.append({
            "layer": layer["layer"], "weight": layer["weight"],
            "color": mix_hex([(D.FAMILIES[x["family"]]["main"], 1.0) for x in layer["notes"]]) if layer["notes"] else "#888888",
            "notes": [{"name": x["name"], "family": x["family"], "color": D.FAMILIES[x["family"]]["main"],
                       "pct": round(100 / n)} for x in layer["notes"]],
        })
    mix = sorted(({"family": k, "share": v} for k, v in agg.items()), key=lambda x: -x["share"])
    declared = D.FAMILIES.get(perfume.get("familyKey", "floral"), D.FAMILIES["floral"])
    mix0 = D.FAMILIES[mix[0]["family"]] if mix else declared
    secondary = mix0["main"] if mix and mix[0]["family"] != perfume.get("familyKey") else (
        D.FAMILIES[mix[1]["family"]]["main"] if len(mix) > 1 else declared["accents"][0])
    mood_words = "、".join(f"{D.FAMILIES[m['family']]['name']}（{D.FAMILIES[m['family']]['mood']}）" for m in mix[:3])
    return {
        "degraded": False, "degradeReason": "",
        "primary": declared["main"], "secondary": secondary,
        "gradient": f"linear-gradient(90deg, {', '.join(l['color'] for l in layers)})",
        "layers": layers,
        "mix": [{"family": m["family"], "share": m["share"], "color": D.FAMILIES[m["family"]]["main"],
                 "mood": D.FAMILIES[m["family"]]["mood"], "scene": D.FAMILIES[m["family"]]["scene"],
                 "shape": D.FAMILIES[m["family"]]["shape"]} for m in mix],
        "moodWords": mood_words,
        "radar": perfume.get("radar", []),
    }


def analyze(req: dict[str, Any]) -> dict[str, Any]:
    request_id = uuid.uuid4().hex[:12]
    perfume = D.get_perfume(req.get("product_id") or "")
    if perfume is None:
        return {"data": None, "meta": {"request_id": request_id, "engine": ENGINE_VERSION,
                                       "error": f"未知香水 product_id={req.get('product_id')!r}"}}

    population = req.get("population", "healthy")
    months = float(req.get("opened_months", 0))
    storage = req.get("storage", "room")
    mode = req.get("mode", "normal")
    d = qra2.compute_d(months, storage)

    # 核心①：预警（判定 + 明细 + 面板实算）
    verdict = evaluate(population, perfume, d)
    rows = build_ingredients(perfume, d, population)
    scenario = _panel_scenario(perfume)
    qra_panel = qra2.analyze_ingredient(scenario["name"], scenario["concPct"], population)

    # 核心②：可视化（错误隔离）
    vision_degraded, vision_reason = False, ""
    try:
        spec = build_visual_spec(perfume)
        if not perfume.get("pyramid"):
            raise ValueError("香调金字塔数据为空")
    except Exception as exc:  # noqa: BLE001
        vision_degraded, vision_reason = True, f"可视化构建失败：{exc}"
        spec = {"degraded": True, "degradeReason": vision_reason}

    # 通感文案（三级兜底）
    try:
        text, model, is_llm = llm.synthesize(perfume, mode)
    except Exception as exc:  # noqa: BLE001
        text, model, is_llm = perfume.get("synesthesia", ""), "template", False

    return {
        "data": {
            "product": {"id": perfume["id"], "brand": perfume["brand"], "name": perfume["name"],
                        "en": perfume.get("en", ""), "familyZh": perfume.get("familyZh", ""),
                        "concentration": perfume.get("concentration", "")},
            "oxidation": {"d": round(d, 4), "months": months, "storage": storage},
            "verdict": {k: verdict[k] for k in ("level", "headline", "reasons", "advice", "dominantGate", "hits")},
            "ingredients": rows,
            "panel": {"label": scenario["label"], "name": scenario["name"], "concPct": scenario["concPct"],
                      "ael": qra_panel["ael"], "p50": qra_panel["p50"], "p90": qra_panel["p90"],
                      "p99": qra_panel["p99"], "marginPoint": qra_panel["marginPoint"],
                      "marginP99": qra_panel["marginP99"], "marginPolicy": qra_panel["marginPolicy"],
                      "policy": qra_panel["policy"], "tPop": qra_panel["tPop"]},
            "vision": spec,
            "synesthesia": {"text": text, "model": model, "isLlm": is_llm},
        },
        "meta": {
            "request_id": request_id,
            "engine": ENGINE_VERSION,
            "models": {"synesthesia": model, "recognition": req.get("_recognition_provider", "n/a")},
            "degraded": {"vision": vision_degraded, "reason": vision_reason},
            "seed": qra2.SEED,
        },
    }
