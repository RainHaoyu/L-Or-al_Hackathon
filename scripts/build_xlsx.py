# -*- coding: utf-8 -*-
"""导出 Excel 三表（与 seed JSON 内容一致，供人工核对与路演）

表1 致敏原总表：EU 2023/1545 全量 71 条目（NESIL/EC3/IFRA Cat4/实测浓度）
表2 香水成分总表：21 款（1 黄金 + 20 欧莱雅真实款）INCI 命中致敏原与典型浓度
表3 共性统计表：全品类家族分布/高频香材/欧莱雅 lift
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
OUT = Path(__file__).resolve().parent.parent / "data" / "xlsx"
HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(color="FFFFFF", bold=True)
WARN_FILL = PatternFill("solid", fgColor="FDE9D9")


def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"


def autowidth(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def sheet_allergens(wb):
    ws = wb.create_sheet("致敏原总表")
    items = json.loads((SEED / "allergens.json").read_text(encoding="utf-8"))["items"]
    hdr = ["INCI 标注名", "中文名", "CAS", "EU组", "Annex III 条目", "NESIL(μg/cm²)", "NESIL依据",
           "LLNA EC3", "WoE分级", "IFRA Cat4限量%", "香水实测均值%(女)", "香水实测最大%(女)",
           "氧化倾向", "欧盟禁用", "香调家族", "备注"]
    ws.append(hdr)
    for a in sorted(items, key=lambda x: (x["eu_2023_1545_group"], x.get("eu_annex_iii_entry") or 0)):
        m = a.get("measured_conc_pct", {}).get("women_n76", {})
        ws.append([
            a["inci"], a.get("name_zh", ""), a.get("cas", ""),
            "旧26" if a["eu_2023_1545_group"] == "existing" else "新增56",
            a.get("eu_annex_iii_entry"), a.get("nesil"), a.get("nesil_basis"),
            a.get("llna_ec3"), a.get("woe_potency", ""), a.get("ifra_limit_pct"),
            m.get("mean"), m.get("max"),
            "是" if a.get("oxidation_prone") else "",
            "禁用" if a.get("banned_eu") else "",
            ",".join(a.get("families", [])), a.get("note", ""),
        ])
    style_header(ws, len(hdr))
    autowidth(ws, [30, 16, 14, 7, 11, 13, 18, 10, 10, 13, 14, 14, 8, 8, 18, 40])
    # 禁用行高亮
    for row in ws.iter_rows(min_row=2):
        if row[13].value == "禁用":
            for c in row:
                c.fill = WARN_FILL
    return ws


def sheet_perfumes(wb):
    ws = wb.create_sheet("香水成分总表")
    d = json.loads((SEED / "perfumes.json").read_text(encoding="utf-8"))
    hdr = ["ID", "品牌", "品名", "浓度", "年份", "Fragrantica家族", "家族占比(7体系)", "前调", "中调", "后调",
           "INCI 命中致敏原（典型% | IFRA限%）", "INCI 项数", "IgE 提示", "INCI 来源", "金字塔来源", "证据级"]
    ws.append(hdr)
    for p in d["perfumes"]:
        parts = []
        for k, v in p.get("allergen_concentrations", {}).items():
            if isinstance(v, dict):  # v2 真实款格式
                parts.append(f"{k} {v.get('typical_pct')}%|限{v.get('ifra_cat4_limit_pct')}")
            else:                    # 黄金算例旧格式（纯数值）
                parts.append(f"{k} {v}%")
        alg = "; ".join(parts)
        def fmt_layer(notes):
            return ", ".join(n["name"] if isinstance(n, dict) else n for n in notes)
        ws.append([
            p["id"], p["brand"], p["name"], p.get("concentration_type"), p.get("year"),
            p.get("fragrantica_family") or ("黄金算例" if p.get("is_golden") else ""),
            json.dumps(p.get("families", {}), ensure_ascii=False),
            fmt_layer(p["pyramid"]["top"]), fmt_layer(p["pyramid"]["heart"]), fmt_layer(p["pyramid"]["base"]),
            alg, len(p.get("inci_full", [])), ", ".join(p.get("ige_materials_hint", [])),
            p.get("inci_source"), p.get("pyramid_source"), p.get("evidence_level"),
        ])
    style_header(ws, len(hdr))
    autowidth(ws, [34, 18, 22, 6, 6, 16, 44, 30, 30, 30, 60, 9, 26, 44, 44, 14])
    return ws


def sheet_commons(wb):
    ws = wb.create_sheet("共性统计")
    c = json.loads((SEED / "industry_commons.json").read_text(encoding="utf-8"))
    ws.append(["—— 全品类香调家族分布（26,319 款）——"])
    ws.append(["家族", "占比%"])
    for k, v in c["industry"]["family_distribution_pct"].items():
        ws.append([k, v])
    ws.append([])
    ws.append(["—— 欧莱雅子集家族分布（823 款）——"])
    ws.append(["家族", "占比%"])
    for k, v in c["loreal"]["family_distribution_pct"].items():
        ws.append([k, v])
    ws.append([])
    ws.append(["—— 全品类高频香材 Top40（按款出现率）——"])
    ws.append(["香材", "出现率%", "出现次数"])
    for x in c["industry"]["top_notes"]:
        ws.append([x["note"], x["pct_of_perfumes"], x["count"]])
    ws.append([])
    ws.append(["—— 欧莱雅特异性香材（相对全品类的 lift>1.2）——"])
    ws.append(["香材", "欧莱雅出现率%", "全品类出现率%", "Lift"])
    for x in c["loreal"]["distinctive_notes_lift"]:
        if x["lift"] >= 1.2:
            ws.append([x["note"], x["loreal_pct"], x["industry_pct"], x["lift"]])
    ws.append([])
    ws.append(["数据源", c["source"]["dataset"], f"解析行数 {c['source']['rows_parsed']}"])
    style_header(ws, 4)
    autowidth(ws, [36, 14, 14, 10])
    return ws


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    wb.remove(wb.active)
    sheet_allergens(wb)
    sheet_perfumes(wb)
    sheet_commons(wb)
    path = OUT / "无界体验家_数据层三表.xlsx"
    wb.save(path)
    print("saved:", path)


if __name__ == "__main__":
    main()
