#!/usr/bin/env python3
"""万象 Aura · 数据层 → 前端 JSON 管线（纯标准库，幂等可重跑）

输入：数据层/ 下 5 个真实数据文件
  - 12款经典香水分析.docx      → src/data/perfumes.json（12 款真实香水）
  - IFRA 51st Amendment Cat4香水禁用清单.xlsx → src/data/ifra.json（限量20/禁用9/天然2）
  - 天然香料cas.xlsx / 合成香料CAS.xlsx / 香精 水溶性及油溶性香精CAS.xlsx → src/data/ingredients.json

用法：python3 scripts/build_data.py
"""

import html
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent            # aura/web
WS = ROOT.parent.parent                                   # 欧莱雅黑客松
DATA_DIR = WS / "数据层"
OUT_DIR = ROOT / "src" / "data"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- docx 段落
def docx_paragraphs(path: Path):
    """返回 [(style, text)]，style 为标题样式 id 或 ''（正文）；<w:tab/> 转为 \\t"""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"<w:tab\b[^>]*/>", "<w:t>\t</w:t>", xml)
    out = []
    for p in re.split(r"</w:p>", xml):
        m = re.search(r'<w:pStyle w:val="([^"]+)"', p)
        style = m.group(1) if m else ""
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        if text.strip():
            out.append((style, text.strip()))
    return out


# ---------------------------------------------------------------- xlsx 读取
def xlsx_rows(path: Path):
    """返回 [{列字母: 文本}] 列表（合并 sharedStrings / inlineStr / 数字）"""
    z = zipfile.ZipFile(path)
    ss: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter(M + "t")))
    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter(M + "row"):
        cells = {}
        for c in row.findall(M + "c"):
            ref = c.get("r", "")
            cm = re.match(r"([A-Z]+)", ref)
            if not cm:
                continue
            col = cm.group(1)
            t = c.get("t")
            if t == "inlineStr":
                is_el = c.find(M + "is")
                val = "".join(x.text or "" for x in is_el.iter(M + "t")) if is_el is not None else ""
            else:
                v = c.find(M + "v")
                val = v.text if v is not None else ""
                if val and t == "s":
                    iv = int(val)
                    val = ss[iv] if 0 <= iv < len(ss) else val
            if val:
                cells[col] = val
        rows.append(cells)
    return rows


def docx_tables(path: Path):
    """返回 [[cell文本, ...], ...]（按行展平的表格）"""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    tables = []
    for tbl in re.findall(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        rows_out = []
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S):
            cells = []
            for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S):
                text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc))
                cells.append(text.strip())
            if any(cells):
                rows_out.append(cells)
        if rows_out:
            tables.append(rows_out)
    return tables


# ---------------------------------------------------------------- 香材 → 香型族推断
FAMILY_RULES = [  # (familyKey, 关键词列表)——顺序即优先级：具体先于泛化
    ("leather", ["皮革"]),
    ("chypre", ["橡木苔", "苔藓", "橡苔"]),
    ("aquatic", ["海盐", "海藻", "海洋", "水生", "黄葵"]),
    ("citrus", ["香柠檬", "佛手柑", "柠檬", "柑橘", "苦橙叶", "苦橙", "橙皮", "西柚", "葡萄柚", "橙子"]),
    ("fruity", ["桃", "梨", "甜瓜", "香瓜", "浆果", "苹果", "李子", "杏仁", "果"]),
    ("gourmand", ["香草", "可可", "巧克力", "零陵香豆", "香豆素", "干果", "焦糖", "美食"]),
    ("floral", ["玫瑰", "茉莉", "依兰", "鸢尾", "橙花", "晚香玉", "铃兰", "紫罗兰", "天竺葵", "乙醛", "醛", "花"]),
    ("woody", ["雪松", "檀香", "香根草", "广藿香", "柏木", "愈创木", "乌木", "木"]),
    ("oriental", ["琥珀", "安息香", "乳香", "没药", "树脂", "辛香", "藏红花", "龙涎", "小豆蔻", "香荚兰"]),
    ("fougere", ["薰衣草", "馥奇"]),
    ("aromatic", ["麝香", "烟草", "茶", "鼠尾草", "迷迭香", "草本", "药草", "薄荷", "樟"]),
    ("green", ["青草", "绿叶", "叶子", "叶"]),
]

# 文档 12 类香调 → 前端 12 香型族（键两侧统一去掉「调」字后匹配）
FAMILY_MAP = {
    "柑橘馥奇": "fougere", "醛香花香": "floral", "西普": "chypre", "东方琥珀": "oriental",
    "美食": "gourmand", "木质馥奇": "fougere", "水生": "aquatic", "皮革": "leather",
    "白花香": "floral", "木质乌木": "woody", "芳香草本": "aromatic", "果香花香": "fruity",
}


def fam_key(zh: str) -> str:
    return zh[:-1] if zh.endswith("调") else zh


def infer_note_family(note: str, fallback: str) -> str:
    for fam, kws in FAMILY_RULES:
        if any(k in note for k in kws):
            return fam
    return fallback


def slugify(en: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", en.lower()).strip("-")
    return s or "perfume"


# ---------------------------------------------------------------- 1) 12 款香水
def build_perfumes():
    paras = [(s, html.unescape(t)) for s, t in docx_paragraphs(DATA_DIR / "12款经典香水分析.docx")]
    # 末尾「香调家族汇总表」为制表符段落（或表格）→ {序号: 关键词}
    keywords = {}
    for _s, text in paras:
        if "\t" in text:
            # 分隔符逐行混杂（tab/双空格/单空格），首列为序号、末列为关键词
            cols = [c.strip() for c in re.split(r"\t+|\s{2,}", text) if c.strip()]
            if len(cols) >= 4 and cols[0].isdigit():
                keywords[cols[0]] = cols[-1]
    for table in docx_tables(DATA_DIR / "12款经典香水分析.docx"):
        for cells in table:
            if len(cells) >= 5 and cells[0].strip().isdigit():
                keywords[cells[0].strip()] = cells[4].strip()

    perfumes = []
    cur = None
    for style, text in paras:
        m = re.match(r"^(\d+)\s*[｜|]\s*(.+?)\s*[（(]\s*(.+?)\s*[｜|]\s*(.+?)\s*[）)]$", text)
        if m:
            no, name_part, fam_zh, fam_en = m.groups()
            brand = next((b for b in ["香奈儿", "蒂普提克", "祖玛珑", "莱俪", "迪奥", "娇兰", "MFK", "TF", "欧珑"]
                          if name_part.startswith(b)), name_part.split(" ")[0])
            rest = name_part[len(brand):].strip()
            tokens = rest.split()
            en_tokens, zh_tokens = [], []
            for tk in tokens:
                if re.match(r"^[A-Za-z]", tk) and not en_tokens and zh_tokens:
                    en_tokens.append(tk)
                elif en_tokens:
                    en_tokens.append(tk)
                else:
                    zh_tokens.append(tk)
            zh_name = " ".join(zh_tokens) or rest
            en_name = " ".join(en_tokens)
            fallback = FAMILY_MAP.get(fam_key(fam_zh), "floral")
            cur = {
                "id": slugify(en_name or zh_name), "no": no, "brand": brand,
                "name": zh_name, "en": en_name,
                "familyZh": fam_zh, "familyEn": fam_en,
                "familyKey": fallback,
                "concentration": "", "pyramidRaw": {}, "ingredients": [],
                "keywords": keywords.get(no, ""), "demoNote": "",
            }
            perfumes.append(cur)
            continue
        if cur is None:
            continue
        for field in ("浓度", "前调", "中调", "后调", "成分清单", "成分"):
            if text.startswith(field):
                val = text[len(field):].lstrip("：: ").strip()
                if field == "浓度":
                    cur["concentration"] = val
                elif field in ("前调", "中调", "后调"):
                    cur["pyramidRaw"][field] = [n.strip() for n in re.split(r"[、,，]", val) if n.strip()]
                else:
                    cur["ingredients"] = [n.strip() for n in re.split(r"[、,，;；]", val) if n.strip()]
                break
        else:
            if text.startswith(("Demo", "demo", "备注")):
                cur["demoNote"] = text.lstrip("Demo备注：: demo ").strip()
            elif not cur["demoNote"] and not any(text.startswith(x) for x in ("香调家族", "浓度标准")):
                if cur.get("ingredients") and not cur["demoNote"] and len(text) > 12:
                    cur["demoNote"] = text

    # pyramid → 带族推断的结构化输出
    out = []
    for p in perfumes:
        layers = []
        for i, layer in enumerate(("前调", "中调", "后调")):
            notes = p["pyramidRaw"].get(layer, [])
            n = len(notes) or 1
            layers.append({
                "layer": layer,
                "weight": [24, 46, 30][i],
                "notes": [{"name": x, "family": infer_note_family(x, p["familyKey"])} for x in notes],
            })
        fam_counts = {}
        for ly in layers:
            for nt in ly["notes"]:
                key = f"{ly['layer']}|{nt['family']}"
                fam_counts[nt["family"]] = fam_counts.get(nt["family"], 0) + ly["weight"] / max(len(ly["notes"]), 1)
        families = [k for k, _ in sorted(fam_counts.items(), key=lambda kv: -kv[1])]
        out.append({
            "id": p["id"], "no": p["no"], "brand": p["brand"], "name": p["name"], "en": p["en"],
            "familyZh": p["familyZh"], "familyEn": p["familyEn"],
            "familyKey": p["familyKey"], "families": families[:4] or [p["familyKey"]],
            "concentration": p["concentration"], "pyramid": layers,
            "ingredients": p["ingredients"], "keywords": p["keywords"], "demoNote": p["demoNote"],
        })
    return {
        "source": "数据层/12款经典香水分析.docx",
        "concentrationStandards": {"Parfum": "20–40%", "EDP": "15–20%", "EDT": "5–15%", "EDC": "2–5%"},
        "perfumes": out,
    }


# ---------------------------------------------------------------- 2) IFRA 三表
def build_ifra():
    rows = xlsx_rows(DATA_DIR / "IFRA 51st Amendment Cat4香水禁用清单.xlsx")
    limits, banned, natural = [], [], []
    for cells in rows:
        # 表1 限量（B–F）
        if cells.get("B") and cells.get("C"):
            zh_en = cells["C"]
            zh, en = zh_en, cells.get("D", "")
            m = re.match(r"^(.*?)\s{2,}(.+)$", zh_en)  # d-柠檬烯：中英挤在一格
            if m and not cells.get("D"):
                zh, en = m.group(1).strip(), m.group(2).strip()
            try:
                limit = float(cells.get("E", ""))
            except ValueError:
                limit = None
            limits.append({"cas": cells.get("B", "").strip(), "zh": zh.strip(), "en": en.strip(),
                           "limitPct": limit, "note": cells.get("F", "").strip()})
        # 表2 禁用（H–L）：CAS 碎片修复
        raw = [cells.get(c, "") for c in ("H", "I", "J", "K", "L")]
        vals = [v.strip() for v in raw if v.strip()]
        if vals:
            cas, idx = None, 0
            pieces = []
            while idx < len(vals) and re.fullmatch(r"\d{1,7}", vals[idx]):
                pieces.append(vals[idx]); idx += 1
            if pieces:
                cas = "-".join(pieces)
            rest = vals[idx:]
            if rest:
                zh2 = rest[0]
                tail = rest[1] if len(rest) > 1 else ""
                segs = [s.strip() for s in re.split(r"[\n\r]+", tail) if s.strip()]
                en2 = segs[0] if segs else ""
                kind = next((s for s in segs if "禁" in s), "完全禁用")
                reason = segs[-1] if len(segs) > 1 else ""
                if zh2 and not zh2.isdigit():
                    banned.append({"cas": cas, "zh": zh2, "en": en2, "control": kind, "reason": reason})
        # 表3 天然精油（N–Q）
        if cells.get("N") and cells.get("O"):
            try:
                lim = float(cells.get("P", ""))
            except ValueError:
                lim = None
            natural.append({"zh": cells["N"].strip(), "en": cells.get("O", "").strip(),
                            "limitPct": lim, "note": cells.get("Q", "").strip()})
    # 过滤误入的表头/空行 + 去重
    limits = [l for l in limits if l["zh"] and "名称" not in l["zh"] and "CAS" not in l["zh"]][:20]
    banned = [b for b in banned if b["zh"] and "名称" not in b["zh"] and "CAS" not in b["zh"]
              and "Cat4" not in b["zh"] and "清单" not in b["zh"]][:9]
    natural = [x for x in natural if "原料" not in x["zh"] and "CAS" not in x["zh"]][:2]
    return {"source": "数据层/IFRA 51st Amendment Cat4香水禁用清单.xlsx", "amendment": "IFRA 51st Amendment",
            "limits": limits, "banned": banned, "natural": natural}


# ---------------------------------------------------------------- 3) CAS 词典
def norm_cas(cas: str) -> str:
    c = re.sub(r"\s+", "", cas or "")
    return c


def build_ingredients():
    specs = [("天然香料cas.xlsx", "natural"), ("合成香料CAS.xlsx", "synthetic"), ("香精 水溶性及油溶性香精CAS.xlsx", "fragrance")]
    entries, seen = [], set()
    for fname, src in specs:
        rows = xlsx_rows(DATA_DIR / fname)
        for cells in rows[1:]:
            vals = [cells.get(c, "") for c in ("A", "B", "C", "D")]
            cas = norm_cas(vals[0])
            zh = vals[1].strip()
            if not cas and not zh:
                continue
            if zh in ("中文名", "CAS") or cas in ("CAS",):
                continue
            key = (cas, zh)
            if key in seen:
                continue
            seen.add(key)
            entries.append({"cas": cas, "zh": zh, "en": vals[2].strip(), "formula": vals[3].strip(), "source": src})
    return {"source": "数据层/天然香料cas.xlsx + 合成香料CAS.xlsx + 香精CAS.xlsx", "entries": entries}


def main():
    if not DATA_DIR.exists():
        die(f"数据层目录不存在：{DATA_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    perfumes = build_perfumes()
    ifra = build_ifra()
    ingredients = build_ingredients()

    (OUT_DIR / "perfumes.json").write_text(json.dumps(perfumes, ensure_ascii=False, indent=2), "utf-8")
    (OUT_DIR / "fra.json").write_text("placeholder", "utf-8")  # 防呆占位（下两行立即覆盖）
    (OUT_DIR / "ifra.json").write_text(json.dumps(ifra, ensure_ascii=False, indent=2), "utf-8")
    (OUT_DIR / "ingredients.json").write_text(json.dumps(ingredients, ensure_ascii=False, indent=2), "utf-8")
    (OUT_DIR / "fra.json").unlink()

    print(f"perfumes: {len(perfumes['perfumes'])} 款")
    for p in perfumes["perfumes"][:3]:
        print(f"  - {p['brand']} {p['name']} ({p['familyZh']}/{p['familyKey']}) 前中后 {tuple(len(l['notes']) for l in p['pyramid'])} 关键词={p['keywords'][:20]}")
    print(f"ifra: limits={len(ifra['limits'])} banned={len(ifra['banned'])} natural={len(ifra['natural'])}")
    for b in ifra["banned"]:
        print(f"  禁 {b['zh']} cas={b['cas']} {b['control']} {b['reason'][:24]}")
    print(f"ingredients: {len(ingredients['entries'])} 条")
    if len(perfumes["perfumes"]) != 12:
        print(f"WARN: 期望 12 款，实际 {len(perfumes['perfumes'])}")
    if len(ifra["limits"]) != 20 or len(ifra["banned"]) != 9:
        print(f"WARN: IFRA 期望 20/9/2，实际 {len(ifra['limits'])}/{len(ifra['banned'])}/{len(ifra['natural'])}")


if __name__ == "__main__":
    main()
