"""可视化域：香调→视觉映射（色彩/动态图形/雷达/金字塔图层）。

映射依据 v3 §1.2（Gilbert 1996 / Spence 2020 跨模态研究）：
- 色块宽度 = 香调占比权重；时序 = 前/中/后调图层；强度 = 透明度/粒子数（前端实现）。
本域与预警域（qra2）零依赖，任一失败不影响另一核心输出。
"""
from __future__ import annotations

from app.schemas.api import PyramidNote, VisionMode, VisionReport

NOTE_FAMILY_KEYWORDS: list[tuple[str, str]] = [
    ("玫瑰", "floral"), ("茉莉", "floral"), ("橙花", "floral"), ("牡丹", "floral"), ("铃兰", "floral"),
    ("鸢尾", "floral"), ("紫罗兰", "floral"), ("天竺葵", "floral"), ("睡莲", "floral"), ("花", "floral"),
    ("柑橘", "citrus"), ("柠檬", "citrus"), ("橙", "citrus"), ("青柠", "citrus"), ("柚", "citrus"),
    ("佛手柑", "citrus"), ("果", "citrus"),
    ("雪松", "woody"), ("檀香", "woody"), ("木", "woody"), ("岩兰草", "woody"), ("愈创木", "woody"),
    ("肉桂", "oriental"), ("胡椒", "oriental"), ("琥珀", "oriental"), ("藏红花", "oriental"), ("乌木", "oriental"),
    ("香脂", "oriental"), ("树脂", "oriental"), ("安息香", "oriental"), ("麝香调", "oriental"),
    ("海盐", "aquatic"), ("水", "aquatic"), ("莲", "aquatic"), ("雾", "aquatic"), ("薄荷", "aquatic"),
    ("香草", "gourmand"), ("焦糖", "gourmand"), ("杏仁", "gourmand"), ("奶", "gourmand"), ("荔枝", "gourmand"),
    ("薰衣草", "fougere"), ("苔", "fougere"), ("蕨", "fougere"), ("艾", "fougere"), ("杜松", "fougere"),
    ("麝香", "fougere"),
]

RADAR_DIMS = ["fresh", "sweet", "rich", "warm", "lasting"]
RADAR_ZH = {"fresh": "清新度", "sweet": "甜度", "rich": "浓郁度", "warm": "温暖度", "lasting": "持久度"}


def note_family(note_name: str, repo, default: str) -> str:
    rec = repo.find_allergen(note_name)
    if rec and rec.get("families"):
        return rec["families"][0]
    for kw, fam in NOTE_FAMILY_KEYWORDS:
        if kw in note_name:
            return fam
    return default


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
            out[phase] = [
                PyramidNote(name=n.get("name", ""), weight=float(n.get("weight", 1.0)),
                            family=note_family(n.get("name", ""), repo, default_family))
                for n in notes
            ]
        return out


def synesthesia_template(vision: VisionReport, brand: str, name: str) -> str:
    """无 LLM 时的规则式通感文案兜底（确保断网/无 Key 也能输出）。"""
    fam_str = "、".join(f["name_zh"] for f in vision.families[:2])
    radar = vision.radar
    top_dims = sorted(radar.items(), key=lambda x: -x[1])[:2]
    dims_str = "与".join(f"{RADAR_ZH.get(k, k)}偏高" for k, _ in top_dims)
    motion = vision.motion.get("label", "缓缓展开")
    mode_prefix = {
        VisionMode.anosmic: "【失嗅模式·画面描述】",
        VisionMode.sensitive: "【敏感肌模式·温和描述】",
        VisionMode.normal: "【通感描述】",
    }[vision.mode]
    layer_desc = "、".join(
        f"{'前调' if p == 'top' else '中调' if p == 'heart' else '后调'}·{'、'.join(n.name for n in ns[:2])}"
        for p, ns in vision.pyramid.items())
    return (f"{mode_prefix}「{brand}·{name}」是一支以{fam_str}为主的作品，{dims_str}。"
            f"闭上眼睛想象：色彩像{motion}般呈现——{layer_desc}，如同一幅随时间徐徐展开的画。"
            f"整体情绪：{vision.mood_label}。")
