"""共享数据层：直接消费 aura/web/src/data/*.json（前端构建管线产物，单一数据源）"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]          # aura/api
DATA_DIR = API_ROOT.parent / "web" / "src" / "data"      # aura/web/src/data

FAMILIES: dict[str, dict[str, Any]] = {
    "citrus": {"name": "柑橘调", "main": "#FFA500", "accents": ["#FFDD00", "#B4D26A"], "scene": "剥开鲜橙的瞬间，精油光点迸溅的果园", "mood": "清新、活力", "shape": "光珠"},
    "floral": {"name": "花香调", "main": "#FFB6C1", "accents": ["#FFBC97", "#C5E0B4"], "scene": "春日花园，柔粉花瓣伴着蜜桃果肉", "mood": "温柔、浪漫", "shape": "花瓣"},
    "woody": {"name": "木质调", "main": "#6B4423", "accents": ["#8A6F56", "#7A8868"], "scene": "幽静森林，原木与树脂的气息", "mood": "沉稳、温暖", "shape": "叶片"},
    "aquatic": {"name": "水生调", "main": "#A1C8D7", "accents": ["#C2D2D9", "#94B8B2"], "scene": "薄雾笼罩的平静湖面，淡淡海风", "mood": "清新、辽阔", "shape": "水珠"},
    "oriental": {"name": "东方调", "main": "#965327", "accents": ["#782C20", "#B87333"], "scene": "琥珀、树脂与辛香交织的暖调宫殿", "mood": "浓郁、神秘", "shape": "花瓣"},
    "leather": {"name": "皮革调", "main": "#4A3628", "accents": ["#634737", "#A88C7E"], "scene": "烟熏气息的复古鞣制工坊", "mood": "醇厚、不羁", "shape": "果实"},
    "chypre": {"name": "西普调", "main": "#706C58", "accents": ["#506248", "#8C4743"], "scene": "秋日山林，青苔与岩石相互缠绕", "mood": "优雅、克制", "shape": "叶片"},
    "fougere": {"name": "馥奇调", "main": "#748C67", "accents": ["#9F91C8", "#A08C6D"], "scene": "雨后林间草地，薰衣草与苔藓", "mood": "经典、平衡", "shape": "针叶"},
    "fruity": {"name": "果香调", "main": "#D96058", "accents": ["#FFB3A0", "#8C4743"], "scene": "挂满浆果的果园，水润饱满", "mood": "鲜活、明快", "shape": "果实"},
    "green": {"name": "绿叶调", "main": "#87B36B", "accents": ["#597C47", "#B2C997"], "scene": "清晨刚采摘的鲜草与青枝叶", "mood": "自然、清爽", "shape": "叶片"},
    "gourmand": {"name": "美食调", "main": "#C87941", "accents": ["#F8EAD8", "#5C3317"], "scene": "暖烘烘的甜品铺，焦糖与可可", "mood": "甜美、温暖", "shape": "果实"},
    "aromatic": {"name": "芳香调", "main": "#697C57", "accents": ["#9484B7", "#A39478"], "scene": "阳光晾晒的草本药草，清苦干爽", "mood": "干爽、草本", "shape": "针叶"},
}

def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


# ---- 毒理参数：与前端引擎共用同一份数据文件（web/src/data/tox.json）----
# 此前 TS 侧 nesil.ts 与 Python 侧本文件各手写一份 22 条 NESIL，
# 属重复事实源，任一侧改动都可能静默漂移。现统一为单一来源。
_TOX_DOC: dict[str, Any] = _load("tox.json")

SAF: int = _TOX_DOC["saf"]
DEMO_PENALTY: int = _TOX_DOC["demoPenalty"]
SAF_BASIS: str = _TOX_DOC["safBasis"]


def _to_internal(e: dict[str, Any]) -> dict[str, Any]:
    """转成引擎内部表示：把 source 归一为 demo 布尔（引擎判定用）。"""
    return {
        "keys": e["keys"],
        "zh": e["zh"],
        "nesil": e["nesil"],
        "demo": e["source"] != "documented",
        **({"k25": e["k25"]} if "k25" in e else {}),
    }


TOX: list[dict[str, Any]] = [_to_internal(e) for e in _TOX_DOC["entries"]]


PERFUMES: list[dict[str, Any]] = _load("perfumes.json")["perfumes"]
IFRA: dict[str, Any] = _load("ifra.json")
DICT_ENTRIES: list[dict[str, Any]] = _load("ingredients.json")["entries"]
EU26: list[dict[str, Any]] = _load("allergens26.json")["items"]
IGE: list[dict[str, Any]] = _load("ige.json")["items"]
MATERIALS: dict[str, Any] = _load("materials.json")


# 黄金算例教学样本（与前端 aura.ts GOLDEN_CASE 同源；点估计口径 = v3 报告算例）
PERFUMES.append({
    "id": "golden-case", "no": "13", "brand": "黄金算例", "name": "柠檬烯 5% 样本", "en": "Limonene 5%",
    "familyZh": "柑橘调", "familyKey": "citrus", "concentration": "教学样本",
    "keywords": "柠檬烯、点估计、可复算", "families": ["citrus", "green", "woody"],
    "pyramid": [
        {"layer": "前调", "weight": 40, "notes": [{"name": "柠檬烯", "family": "citrus"}]},
        {"layer": "中调", "weight": 35, "notes": [{"name": "柠檬叶", "family": "green"}]},
        {"layer": "后调", "weight": 25, "notes": [{"name": "柠檬木", "family": "woody"}]},
    ],
    "ingredients": ["柠檬烯"],
    "radar": [{"dim": "清新", "v": 10}, {"dim": "甜度", "v": 2}, {"dim": "浓郁", "v": 3},
              {"dim": "温暖", "v": 3}, {"dim": "持久", "v": 4}],
    "synesthesia": "刚剥开的柠檬皮，汁水溅在晨光里，干净得只剩一点木。",
    "synthetic": True,
})


def get_perfume(pid: str) -> dict[str, Any] | None:
    return next((p for p in PERFUMES if p["id"] == pid), None)


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


# 匹配键按长度降序预排（最长优先），与前端 nesil.ts 的 KEYS 同法。
# 子串匹配在归一化（去掉连字符）后会互相包含，导致误判：
#   - `isoeugenol` 含 `eugenol`      → 异丁香酚被误判成丁香酚（真实值小 23 倍，危险方向）
#   - `hexylcinnamal` 含 `cinnamal`  → 己基肉桂醛被误判成肉桂醛（AEL 被压 40 倍）
#   - `amylcinnamal` 含 `cinnamal`   → 同上
#   - `新铃兰醛` 含 `铃兰醛`          → 被误判成铃兰醛
_KEYS: list[tuple[str, dict[str, Any]]] = sorted(
    ((_norm(k), t) for t in TOX for k in t["keys"]),
    key=lambda kv: -len(kv[0]),
)

_HICC_KEYS = sorted(
    (_norm(k) for k in ("hicc", "lyral", "hydroxyisohexyl", "新铃兰醛", "海葵醛", "新铃兰醛（海葵醛）")),
    key=len, reverse=True,
)
_HICC_ENTRY = next((t for t in TOX if t["zh"].startswith("新铃兰醛")), None)


def lookup_tox(name: str) -> dict[str, Any] | None:
    n = _norm(name)
    if not n:
        return None
    # HICC / Lyral 常以缩写出现，先按别名归一到新铃兰醛条目
    if _HICC_ENTRY and any(k in n for k in _HICC_KEYS):
        return _HICC_ENTRY
    for key, entry in _KEYS:
        if key in n:
            return entry
    return None


def lookup_ifra_limit(name: str) -> dict[str, Any] | None:
    n = _norm(name)
    tox = lookup_tox(name)
    for l in IFRA["limits"]:
        if n and (_norm(l["zh"]) in n or (l.get("en") and _norm(l["en"]) and _norm(l["en"]) in n)):
            return l
        if tox and _norm(tox["zh"]) and _norm(tox["zh"]) in _norm(l["zh"]):
            return l
    return None


def lookup_banned(name: str) -> dict[str, Any] | None:
    n = _norm(name)
    tox = lookup_tox(name)
    for b in IFRA["banned"]:
        if n and _norm(b["zh"]) and _norm(b["zh"]) in n:
            return b
        if b.get("en") and n and _norm(b["en"]) and _norm(b["en"]) in n:
            return b
        if tox and _norm(tox["zh"]) and _norm(tox["zh"]) in _norm(b["zh"]):
            return b
    return None
