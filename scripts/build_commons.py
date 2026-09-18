# -*- coding: utf-8 -*-
"""industry_commons.json 构建：香水品类原料共性 + 欧莱雅对比

数据源：doevent/perfume 数据集（HuggingFace，MIT 协议，26,319 款香水，
源自 Fragrantica 公开页面的社区整理数据），下载于 2026-09-17。
方法：香材（note）频率统计 + 香调家族条件分布 + 欧莱雅子集 vs 全品类对比（lift）。
"""
from __future__ import annotations

import ast
import csv
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "doevent_perfumes.csv"
SEED = ROOT / "data" / "seed"

# Fragrantica 大家族 → 本项目 7 家族（与 families.json key 对齐）
FAMILY_MAP = {
    "FLORAL": "floral", "WOODY": "woody", "AMBERY (ORIENTAL)": "oriental",
    "AROMATIC FOUGERE": "fougere", "CITRUS": "citrus", "CHYPRE": "fougere",
    "LEATHER": "oriental",
}

# 欧莱雅集团香水品牌（含授权线，2026 口径）
LOREAL_BRANDS = {
    "yves saint laurent", "lancome", "maison margiela", "giorgio armani",
    "mugler", "valentino", "viktor & rolf", "cacharel", "azzaro",
    "prada", "ralph lauren", "diesel", "paloma picasso", "shu uemura",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def parse_notes(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        v = ast.literal_eval(raw)
        return [str(x).strip() for x in v if str(x).strip()]
    except Exception:
        return [p.strip(" '\"[]") for p in raw.split(",") if p.strip(" '\"[]")]


def main() -> None:
    rows = list(csv.reader(open(RAW, encoding="utf-8", errors="replace"), delimiter="|"))
    hdr = rows[0]
    data = [dict(zip(hdr, (r + [""] * len(hdr))[: len(hdr)])) for r in rows[1:]]

    industry_family = Counter()
    note_freq = Counter()                     # 全品类香材出现次数
    note_in_family = defaultdict(Counter)     # family -> note counter
    note_total_perfumes = 0

    loreal_family = Counter()
    loreal_note_freq = Counter()
    loreal_names = []

    for d in data:
        fam_raw = d.get("family", "").strip()
        fam7 = FAMILY_MAP.get(fam_raw)
        brand = strip_accents(d.get("brand", "")).lower()
        notes = parse_notes(d.get("ingredients", ""))
        if not notes:
            continue
        note_total_perfumes += 1
        is_loreal = any(b in brand or brand in b for b in LOREAL_BRANDS)
        industry_family[fam7 or "unmapped"] += 1
        uniq = set(notes)
        note_freq.update(uniq)
        if fam7:
            note_in_family[fam7].update(uniq)
        if is_loreal:
            loreal_family[fam7 or "unmapped"] += 1
            loreal_note_freq.update(uniq)
            loreal_names.append(f"{d.get('brand','')} / {d.get('name_perfume','')}")

    n_all = sum(industry_family.values())
    n_loreal = sum(loreal_family.values())

    # 家族归一化占比
    industry_family_pct = {k: round(v / n_all * 100, 1) for k, v in industry_family.most_common() if k != "unmapped"}
    loreal_family_pct = {k: round(v / n_loreal * 100, 1) for k, v in loreal_family.most_common() if k != "unmapped"}

    # top 香材：全品类 / 欧莱雅 / lift
    top_all = note_freq.most_common(40)
    top_loreal = loreal_note_freq.most_common(30)
    p_all = {n: c / note_total_perfumes for n, c in note_freq.items()}
    p_lor = {n: c / n_loreal for n, c in loreal_note_freq.items()}
    lift = []
    for n, c in top_loreal:
        if p_all.get(n, 0) > 0.005:
            lift.append({"note": n, "loreal_pct": round(p_lor[n] * 100, 1),
                         "industry_pct": round(p_all[n] * 100, 1),
                         "lift": round(p_lor[n] / p_all[n], 2)})
    lift.sort(key=lambda x: -x["lift"])

    # 每个家族 top 香材（条件分布，用于 ingredients.json 家族锚点校准）
    family_top_notes = {
        fam: [{"note": n, "pct": round(c / sum(cnt.values()) * 100, 1)}
              for n, c in cnt.most_common(15)]
        for fam, cnt in note_in_family.items()
    }

    out = {
        "$comment": (
            "香水品类共性统计：doevent/perfume（HF, MIT, 26,319 款 Fragrantica 社区数据）聚合。"
            "note=香材出现率（按款计，去重）；家族= Fragrantica 大类映射到本项目 7 家族"
            "（CHYPRE→fougere, LEATHER→oriental）。欧莱雅子集含 12 个授权线品牌。"
            "用途：① 香调金字塔→家族占比的先验 ② 高频香材→可视化映射优先级 ③ 欧莱雅特异性（lift）叙事。"
        ),
        "built_at": "2026-09-17",
        "source": {
            "dataset": "https://huggingface.co/datasets/doevent/perfume (perfumes.csv)",
            "rows_parsed": note_total_perfumes,
            "note": "原文件列名错位：'ingredients' 列实为香材列表，'fragrances' 列为家族描述符",
        },
        "industry": {
            "family_distribution_pct": industry_family_pct,
            "top_notes": [{"note": n, "pct_of_perfumes": round(p_all[n] * 100, 1), "count": c} for n, c in top_all],
            "family_top_notes": family_top_notes,
        },
        "loreal": {
            "brands": sorted(set(b.title() for b in LOREAL_BRANDS)),
            "perfumes_in_dataset": n_loreal,
            "family_distribution_pct": loreal_family_pct,
            "top_notes": [{"note": n, "pct_of_perfumes": round(p_lor[n] * 100, 1), "count": c} for n, c in top_loreal],
            "distinctive_notes_lift": lift[:15],
        },
    }
    (SEED / "industry_commons.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"parsed {note_total_perfumes} perfumes | loreal {n_loreal}")
    print("industry family%:", industry_family_pct)
    print("loreal family%:", loreal_family_pct)
    print("top10 all:", [(n, f'{p_all[n]*100:.1f}%') for n, _ in top_all[:10]])
    print("top10 loreal:", [(n, f'{p_lor[n]*100:.1f}%') for n, _ in top_loreal[:10]])
    print("top lift:", [(x['note'], x['lift']) for x in lift[:8]])
    print("floral top:", [x['note'] for x in family_top_notes.get('floral', [])[:8]])
    print("woody top:", [x['note'] for x in family_top_notes.get('woody', [])[:8]])


if __name__ == "__main__":
    main()
