"""可视化域：香调→视觉映射（色彩/动态图形/雷达/金字塔图层）。

映射依据 v3 §1.2（Gilbert 1996 / Spence 2020 跨模态研究）：
- 色块宽度 = 香调占比权重；时序 = 前/中/后调图层；强度 = 透明度/粒子数（前端实现）。
本域与预警域（qra2）零依赖，任一失败不影响另一核心输出。
"""
from __future__ import annotations

import re

from app.schemas.api import PyramidNote, VisionMode, VisionReport

# 香调推断关键词表。
# ⚠️ 顺序敏感：同族内**更具体的词必须排在更泛的词之前**
#    （如 天竺葵 先于 花、青柠 先于 橙、雪松木 先于 木），否则会被泛词提前截胡。
# 另：真实香水库的音符名以英文为主（20/21 款），金标算例为中文——
#    因此中英各一组、中文组优先，避免「Rose / Orange Blossom」被 citrus 抢走。
NOTE_FAMILY_KEYWORDS: list[tuple[str, str]] = [
    # —— 中文 ——
    ("玫瑰", "floral"), ("茉莉", "floral"), ("橙花", "floral"), ("牡丹", "floral"), ("铃兰", "floral"),
    ("鸢尾", "floral"), ("紫罗兰", "floral"), ("天竺葵", "floral"), ("睡莲", "floral"), ("水仙", "floral"),
    ("花", "floral"),
    ("佛手柑", "citrus"), ("柑橘", "citrus"), ("柠檬", "citrus"), ("青柠", "citrus"), ("柚", "citrus"),
    ("橙", "citrus"), ("果", "citrus"),
    ("雪松木", "woody"), ("雪松", "woody"), ("檀香", "woody"), ("愈创木", "woody"), ("岩兰草", "woody"),
    ("香根草", "woody"), ("广藿香", "woody"), ("木", "woody"),
    ("肉桂", "oriental"), ("胡椒", "oriental"), ("琥珀", "oriental"), ("藏红花", "oriental"), ("乌木", "oriental"),
    ("香脂", "oriental"), ("树脂", "oriental"), ("安息香", "oriental"), ("辛香", "oriental"), ("麝香", "oriental"),
    ("海盐", "aquatic"), ("海水", "aquatic"), ("水", "aquatic"),
    ("香草", "gourmand"), ("焦糖", "gourmand"), ("杏仁", "gourmand"), ("奶", "gourmand"), ("荔枝", "gourmand"),
    ("香豆素", "gourmand"), ("甜", "gourmand"),
    ("薰衣草", "fougere"), ("蕨", "fougere"), ("苔", "fougere"), ("杜松", "fougere"), ("艾", "fougere"),
    # —— 英文（长词优先，避免 "orange blossom" 被 "orange" 截胡）——
    ("orange blossom", "floral"), ("orange flower", "floral"), ("may rose", "floral"), ("tea rose", "floral"),
    ("jasmine", "floral"), ("rose", "floral"), ("iris", "floral"), ("violet", "floral"), ("peony", "floral"),
    ("geranium", "floral"), ("lily", "floral"), ("magnolia", "floral"), ("osmanthus", "floral"), ("neroli", "floral"),
    ("ylang", "floral"), ("tuberose", "floral"), ("gardenia", "floral"), ("freesia", "floral"),
    ("mandarin", "citrus"), ("tangerine", "citrus"), ("bergamot", "citrus"), ("grapefruit", "citrus"),
    ("petitgrain", "citrus"), ("citron", "citrus"), ("lime", "citrus"), ("lemon", "citrus"), ("orange", "citrus"),
    ("cedarwood", "woody"), ("cedar", "woody"), ("sandalwood", "woody"), ("sandal", "woody"),
    ("vetiver", "woody"), ("patchouli", "woody"), ("guaiac", "woody"), ("oud", "woody"), ("agarwood", "woody"),
    ("cashmeran", "woody"), ("ambroxan", "woody"), ("ambrette", "woody"), ("iso e super", "woody"),
    ("cypress", "woody"), ("pine", "woody"), ("fir", "woody"), ("wood", "woody"),
    ("saffron", "oriental"), ("pepper", "oriental"), ("cinnamon", "oriental"), ("clove", "oriental"),
    ("cardamom", "oriental"), ("incense", "oriental"), ("myrrh", "oriental"), ("benzoin", "oriental"),
    ("labdanum", "oriental"), ("balsam", "oriental"), ("resin", "oriental"), ("spice", "oriental"),
    ("amber", "oriental"), ("musk", "oriental"), ("tonka", "oriental"), ("cistus", "oriental"),
    ("vanilla", "gourmand"), ("caramel", "gourmand"), ("praline", "gourmand"), ("cocoa", "gourmand"),
    ("chocolate", "gourmand"), ("coffee", "gourmand"), ("honey", "gourmand"), ("almond", "gourmand"),
    ("coconut", "gourmand"), ("coumarin", "gourmand"), ("chestnut", "gourmand"), ("melon", "gourmand"),
    ("sea note", "aquatic"), ("seaweed", "aquatic"), ("aquozone", "aquatic"), ("calone", "aquatic"),
    ("water", "aquatic"), ("marine", "aquatic"), ("ozonic", "aquatic"), ("mineral", "aquatic"),
    ("aldehyd", "aquatic"), ("cucumber", "aquatic"),
    ("lavender", "fougere"), ("fougere", "fougere"), ("sage", "fougere"), ("rosemary", "fougere"),
    ("juniper", "fougere"), ("moss", "fougere"), ("basil", "fougere"), ("tarragon", "fougere"),
    ("mint", "fougere"), ("thyme", "fougere"),
]

RADAR_DIMS = ["fresh", "sweet", "rich", "warm", "lasting"]
RADAR_ZH = {"fresh": "清新度", "sweet": "甜度", "rich": "浓郁度", "warm": "温暖度", "lasting": "持久度"}

_NORM_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def _norm_name(value: object) -> str:
    """归一化音符名：小写 + 去所有非中英文数字字符（让 "Sea Notes" 与 "sea-notes" 等价）。"""
    return _NORM_RE.sub("", str(value or "").lower())


def infer_family_from_name(note_name: object) -> str | None:
    """按中文/英文关键词推断香调；无法判断时返回 None，由调用方决定兜底。"""
    norm = _norm_name(note_name)
    if not norm:
        return None
    for keyword, family in NOTE_FAMILY_KEYWORDS:
        if _norm_name(keyword) in norm:
            return family
    return None


def note_family(note_name: str, repo, default: str) -> str:
    """优先用成分库里的 families；其次关键词推断；最后用主香调兜底。"""
    rec = repo.find_allergen(note_name)
    if rec:
        families = rec.get("families")
        if isinstance(families, (list, tuple)) and families:
            return families[0]
        if isinstance(families, str) and families:
            return families
    return infer_family_from_name(note_name) or default



def _pyramid_note(item: object, repo, default_family: str) -> PyramidNote | None:
    """把香调金字塔里的一个音符归一化成 PyramidNote。

    历史数据存在两种形状（迁移时实测：21 款里只有 golden-limonene 是对象数组）：
      - 对象：{"name": "柠檬烯", "weight": 0.6}
      - 字符串："Lavender"（PyramidNote.weight 默认 1.0，family 由关键词/成分库推断）
    之前只支持前者，字符串形状会抛 AttributeError 并被上层静默兜底，
    导致 20/21 款真实香水的可视化整体失效。此处两种都接受。
    """
    if isinstance(item, dict):
        name = str(item.get("name") or "").strip()
        raw_weight = item.get("weight", 1.0)
    elif isinstance(item, str):
        name = item.strip()
        raw_weight = 1.0
    else:
        return None
    if not name:
        return None
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError):
        weight = 1.0
    return PyramidNote(name=name, weight=weight, family=note_family(name, repo, default_family))


class ScentmapService:
    def __init__(self, families_rules: dict):
        self.rules = families_rules

    def build_vision(self, product: dict, repo, mode: VisionMode = VisionMode.normal) -> VisionReport:
        fams = sorted(
            ({"key": k, "name_zh": self.rules[k].get("name_zh", k), "weight": float(w)}
             for k, w in product.get("families", {}).items() if k in self.rules),
            key=lambda x: -x["weight"],
        )
        dominant_key = fams[0]["key"] if fams else "floral"
        dominant = self.rules[dominant_key]

        # 色板：主香调三色 + 次香调主色（宽度由 families.weight 在前端渲染）
        palette = list(dominant["palette"])
        if len(fams) > 1:
            palette.append(self.rules[fams[1]["key"]]["palette"][1])

        radar = self._radar(product, fams)
        pyramid = self._pyramid(product, repo, dominant_key)

        return VisionReport(
            mode=mode,
            families=fams,
            palette=palette,
            gradient_direction=int(dominant.get("gradient_direction", 135)),
            motion=dominant["motion"],
            mood_label=dominant["mood"]["label"],
            radar=radar,
            pyramid=pyramid,
        )

    def _radar(self, product: dict, fams: list[dict]) -> dict[str, float]:
        if product.get("radar"):
            return {k: round(float(v), 3) for k, v in product["radar"].items() if k in RADAR_DIMS}
        total = sum(f["weight"] for f in fams) or 1.0
        out = {}
        for dim in RADAR_DIMS:
            out[dim] = round(
                sum(f["weight"] * self.rules[f["key"]]["radar_prior"].get(dim, 0.5) for f in fams) / total, 3)
        return out

    def _pyramid(self, product: dict, repo, default_family: str) -> dict[str, list[PyramidNote]]:
        out: dict[str, list[PyramidNote]] = {}
        for phase, notes in (product.get("pyramid") or {}).items():
            if isinstance(notes, (str, dict)):  # 容错：单条而非列表
                notes = [notes]
            normalized = (_pyramid_note(n, repo, default_family) for n in notes or [])
            out[phase] = [note for note in normalized if note is not None]
        return out


def synesthesia_template(vision: VisionReport, brand: str, name: str) -> str:
    """无 LLM 时的规则式通感文案兜底（确保断网/无 Key 也能输出）。

    对缺失维度做防御：香调/雷达/金字塔任一为空时不留断句，
    否则会拼出「是一支以**为主的**作品，**。」这类病句
    （实测：手动输入与金标算例缺 pyramid 时会出现）。
    """
    mode_prefix = {
        VisionMode.anosmic: "【失嗅模式·画面描述】",
        VisionMode.sensitive: "【敏感肌模式·温和描述】",
        VisionMode.normal: "【通感描述】",
    }[vision.mode]

    fams = [f.get("name_zh") or f.get("key") or "" for f in vision.families]
    fams = [f for f in fams if f]
    radar = {k: v for k, v in (vision.radar or {}).items() if k in RADAR_ZH}
    top_dims = [k for k, _ in sorted(radar.items(), key=lambda x: -x[1])[:2]]
    motion = (vision.motion or {}).get("label") or "缓缓展开"
    layers = [
        f"{'前调' if p == 'top' else '中调' if p == 'heart' else '后调'}"
        f"·{'、'.join(n.name for n in ns[:2])}"
        for p, ns in (vision.pyramid or {}).items() if ns
    ]

    parts = [f"{mode_prefix}「{brand}·{name}」" if brand else f"{mode_prefix}「{name}」"]
    parts.append(f"是一支以{'、'.join(fams)}为主的作品。" if fams else "是一支香调信息尚不完整的作品。")
    if top_dims:
        parts.append("".join(f"{RADAR_ZH[k]}偏高与" for k in top_dims).rstrip("与") + "。")
    imagery = f"闭上眼睛想象：色彩像{motion}般呈现"
    if layers:
        imagery += f"——{'、'.join(layers)}"
    parts.append(imagery + "，如同一幅随时间徐徐展开的画。")
    if vision.mood_label:
        parts.append(f"整体情绪：{vision.mood_label}。")
    return "".join(parts)
