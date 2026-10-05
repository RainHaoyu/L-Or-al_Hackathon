# -*- coding: utf-8 -*-
"""perfumes.json v2 构建：20 款欧莱雅真实香水 + 黄金算例

输入：data/raw/perfumes_batch{1,2,3}.json（INCI+金字塔双源采集）
处理：
1) INCI 归一化 → allergens.json 的 129 个 INCI 匹配名命中致敏原
2) 金字塔香材 → ingredients.json 家族锚点 → families 占比（层权重 top1.0/heart1.2/base1.5）
3) families 占比 × families.json radar_prior → 五维雷达
4) 致敏原典型浓度：Lim 2018 女香均值（文献实测口径，标 estimate）
输出：data/seed/perfumes.json
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SEED = ROOT / "data" / "seed"
RETRIEVED = "2026-09-17"

LAYER_WEIGHT = {"top": 1.0, "heart": 1.2, "base": 1.5}

# 香材名归一化（Fragrantica 命名 → ingredients.json 键）
NOTE_ALIAS = {
    "black currant": "Blackcurrant", "blackcurrant": "Blackcurrant", "cassis": "Blackcurrant",
    "mandarin orange": "Mandarin", "tangerine": "Mandarin", "green mandarin": "Mandarin",
    "madagascar vanilla": "Vanilla", "vanilla bean": "Vanilla", "bourbon vanilla": "Vanilla",
    "cashmere wood": "Cashmeran", "java vetiver oil": "Vetiver", "tahitian vetiver": "Vetiver",
    "african orange blossom": "Orange Blossom", "may rose": "Rose",
    "jasmine (grandiflorum)": "Jasmine", "jasmine tea": "Jasmine",
    "bitter almond": "Almond", "dark chocolate": "Chocolate", "red berries": "Raspberry",
    "melOn": "Coconut", "cassia": "Cinnamon", "white amber": "Amber",
    "tobacco leaf": "Tobacco", "peru balsam": "Benzoin", "styrax": "Benzoin",
    "amberwood": "Amber", "ambergris": "Ambergris", "white ambergris": "Ambergris",
    "woody notes": "Cedarwood", "woodsy notes": "Cedarwood", "mineral notes": "Sea Notes",
    "aquozone": "Sea Notes", "red seaweed": "Sea Notes", "seaweed": "Sea Notes",
    "cucumber": "Sea Notes", "suede": "Leather", "leather": "Leather",
    "cypress": "Pine", "mastic or lentisque": "Pine", "juniper": "Juniper",
    "chestnut": "Praline", "cloves": "Clove", "ciste labdanum": "Labdanum",
    "pink pepper": "Pink Pepper", "red pepper": "Pink Pepper", "white pepper": "Pepper",
    "spices": "Cinnamon", "violet leaf": "Violet", "petitgrain": "Orange Blossom",
    "cotton candy": "Cotton Candy", "aldehydes": "Aldehydes", "calone": "Calone",
    "orchid": "Jasmine", "freesia": "Freesia", "cyclamen": "Lily-of-the-Valley",
    "neroli essence": "Orange Blossom", "neroli": "Orange Blossom",
    "neroli bud": "Orange Blossom", "sage": "Clary Sage", "salt": "Salt",
    "ambrette": "White Musk", "ambrofix": "Ambroxan", "ambroxan": "Ambroxan",
    "musky notes": "Musk", "musk": "Musk",
}

# IgE 原料扫描词（金字塔/INCI → IgE 风险材料）
IGE_HINTS = {
    "Peru Balsam": "秘鲁香脂", "Balsam of Peru": "秘鲁香脂", "Myroxylon": "秘鲁香脂",
    "Oakmoss": "橡苔提取物", "Evernia Prunastri": "橡苔提取物",
    "Jasmine": "茉莉净油", "Jasminum": "茉莉净油",
    "Rose": "玫瑰净油（金字塔层面为玫瑰香材，仅净油工艺才具 IgE 风险）",
    "Ylang": "依兰净油", "Cananga": "依兰净油",
    "Tuberose": "晚香玉净油", "Benzoin": "安息香树脂", "Styrax": "苏合香",
}


def norm_inci(s: str) -> list[str]:
    """一个标签项拆出一个或多个规范 INCI 候选名（小写）。"""
    s = s.split("(")[0]
    parts = [p.strip(" .") for p in re.split(r"[/,]", s)]
    return [p.lower() for p in parts if p and not p.lower().startswith(("ci ", "ci1", "ci 1"))]


def norm_note(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def note_families(note: str, ing_index: dict) -> list[str]:
    n = norm_note(note)
    key = NOTE_ALIAS.get(n, note.strip())
    hit = ing_index.get(norm_note(key))
    if hit is None:
        hit = ing_index.get(n)
    return hit["families"] if hit else []


def main() -> None:
    batches = []
    for i in (1, 2, 3):
        batches += json.loads((RAW / f"perfumes_batch{i}.json").read_text(encoding="utf-8"))

    allergens = json.loads((SEED / "allergens.json").read_text(encoding="utf-8"))["items"]
    ing = json.loads((SEED / "ingredients.json").read_text(encoding="utf-8"))["items"]
    ing_index = {norm_note(x["key"]): x for x in ing}
    fam_data = json.loads((SEED / "families.json").read_text(encoding="utf-8"))

    # INCI 名 → 致敏原条目（含别名面）
    inci_to_allergen: dict[str, dict] = {}
    for a in allergens:
        for name in [a["inci"]] + a.get("inci_names", []) + ([a["name_zh"]] if a.get("name_zh") else []):
            inci_to_allergen[norm_note(name)] = a
    inci_to_allergen["limonene"] = next(a for a in allergens if a["inci"] == "d-Limonene")

    # Lim 2018 女香均值（%）
    lim_mean = {}
    for a in allergens:
        m = a.get("measured_conc_pct", {}).get("women_n76", {}).get("mean")
        if m is not None:
            lim_mean[a["inci"]] = m
    jfda_mean = {a["inci"]: a["typical_conc_pct"]["mean"] for a in allergens
                 if a.get("typical_conc_pct", {}).get("mean") is not None}

    out_perfumes = []
    for p in batches:
        # --- 致敏原命中
        hits, matched_inci = {}, []
        for raw in p.get("inci_full", []):
            for cand in norm_inci(raw):
                a = inci_to_allergen.get(cand)
                if a:
                    matched_inci.append(raw.strip())
                    label = a["inci"]
                    if label not in hits:
                        if label in lim_mean:
                            val, basis = lim_mean[label], "lim2018_107perfumes_women_mean"
                        elif label in jfda_mean:
                            val, basis = jfda_mean[label], "lu2021_jfda_perfume_mean"
                        else:
                            val, basis = None, "unknown_conc"
                        hits[label] = {"typical_pct": val, "basis": basis,
                                       "ifra_cat4_limit_pct": a.get("ifra_limit_pct"),
                                       "banned_eu": a.get("banned_eu", False),
                                       "oxidation_prone": a.get("oxidation_prone", False)}
        # --- IgE 原料提示（金字塔 + INCI 扫描）
        ige_hits = set()
        blob = " | ".join(sum(p["pyramid"].values(), [])) + " | " + ", ".join(p.get("inci_full", []))
        for kw, zh in IGE_HINTS.items():
            if kw.lower() in blob.lower():
                ige_hits.add(zh)

        # --- 家族占比（金字塔加权；海洋/标志性香材 ×1.6 加成以免被基础香材稀释）
        score: dict[str, float] = defaultdict(float)
        for layer, notes in p["pyramid"].items():
            for nt in notes:
                key = NOTE_ALIAS.get(norm_note(nt), nt.strip())
                hit = ing_index.get(norm_note(key)) or ing_index.get(norm_note(nt))
                boost = 1.6 if (hit and hit.get("category") in ("fresh_marine", "synthetic_marine")) else 1.0
                for f in (hit["families"] if hit else []):
                    score[f] += LAYER_WEIGHT[layer] * boost
        total = sum(score.values()) or 1.0
        ranked = sorted(score.items(), key=lambda x: -x[1])
        fams_pct = {f: round(v / total * 100, 1) for f, v in ranked[:5] if v / total >= 0.08}
        # 归一化到 100
        s = sum(fams_pct.values())
        fams_pct = {f: round(v / s * 100, 1) for f, v in fams_pct.items()}

        # --- 五维雷达（家族先验加权混合，0-1 先验 → 0-10 展示刻度）
        radar = defaultdict(float)
        for f, pct in fams_pct.items():
            prior = fam_data[f].get("radar_prior", {})
            for dim, v in prior.items():
                radar[dim] += v * pct
        radar = {k: round(min(v / 10.0, 10.0), 1) for k, v in radar.items()}

        out_perfumes.append({
            "id": p["id"], "brand": p["brand"], "name": p["name"],
            "concentration_type": p["concentration_type"],
            "year": p.get("year"), "perfumer": p.get("perfumer", []),
            "fragrantica_family": p.get("fragrantica_family"),
            "pyramid": p["pyramid"],
            "families": fams_pct,
            "radar": dict(radar),
            "inci_full": p.get("inci_full", []),
            "inci_source": p.get("inci_source"), "pyramid_source": p.get("pyramid_source"),
            "allergen_concentrations": hits,
            "ige_materials_hint": sorted(ige_hits),
            "barcode": None,
            "evidence_level": "inci_documented" if p.get("inci_full") else "data_gap_inci",
            "conc_note": ("Parfum 内部配比属商业机密：typical_pct 为文献实测均值（Lim 2018 n=107 / Lu 2021 n=14），"
                          "仅作 CEL 点估计输入，非该产品实测值"),
            "notes_on_data": p.get("notes_on_data", ""),
            "retrieved": RETRIEVED,
        })

    # 保留黄金算例（兼容旧 products / 新 perfumes 两种键名）
    old = json.loads((SEED / "perfumes.json").read_text(encoding="utf-8"))
    old_list = old.get("products") or old.get("perfumes") or []
    golden = next(x for x in old_list if x.get("is_golden"))
    final = [golden] + out_perfumes

    meta = {
        "$comment": (
            "香水库 v2：1 款黄金算例（柠檬烯标样，复现 v3 报告 CEL=5.0/AEL=100/比值=20）+ 20 款欧莱雅集团真实香水"
            "（YSL/Lancôme/Viktor&Rolf/Mugler/Margiela REPLICA/Armani/Valentino/Prada/Azzaro/Ralph Lauren）。"
            "INCI 全表与香调金字塔均带来源链接（官网/官方零售商/inkeedecoder/Ulta + Fragrantica）。"
            "allergen_concentrations 为 INCI 命中致敏原清单，typical_pct 为文献均值估计（非该产品实测）。"
            "families 占比由金字塔香材×层权重聚合，雷达五维由家族先验混合而来。"
        ),
        "built_at": RETRIEVED,
        "count": len(final),
        "brands": sorted({p["brand"] for p in out_perfumes}),
        "perfumes": final,
    }
    (SEED / "perfumes.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"perfumes.json v2: {len(final)} 款 | 品牌 {len(meta['brands'])} 个")
    for p in out_perfumes:
        print(f"  {p['id']:38s} {str(p['families']):52s} 致敏原{len(p['allergen_concentrations']):2d}项 "
              f"{'inci✓' if p['evidence_level']=='inci_documented' else 'INCI缺失'}")


if __name__ == "__main__":
    main()
