#!/usr/bin/env python3
"""万象 Aura · 数据层 → 前端 JSON 管线（纯标准库，幂等可重跑）

输入：数据层/ 下 5 个真实数据文件（目录不入库，见 find_data_dir）
  - 12款经典香水分析.docx      → src/data/perfumes.json（12 款真实香水）
  - IFRA 51st Amendment Cat4香水禁用清单.xlsx → src/data/ifra.json（限量20/禁用9/天然2）
  - 天然香料cas.xlsx / 合成香料CAS.xlsx / 香精 水溶性及油溶性香精CAS.xlsx → src/data/ingredients.json

用法：python3 scripts/build_data.py
      数据层不在默认位置时：set AURA_DATA_DIR=D:\\path\\to\\数据层
"""

import html
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent            # <仓库>/web
REPO = ROOT.parent                                       # <仓库>
WS = REPO.parent                                         # 欧莱雅黑客松（数据层常在这一层）
OUT_DIR = ROOT / "src" / "data"

# 数据层目录名是中文，且不入库（体积大、含内部资料），所以不写死单一路径，
# 而是按锚点文件去找。这段逻辑刻意留在 Python 而不是 .bat 里：.bat 必须
# ASCII-only（cmd.exe 按系统 OEM 代码页解码脚本字节），中文目录名只有
# Python 能安全处理。
DATA_ANCHORS = ("12款经典香水分析.docx", "IFRA 51st Amendment Cat4香水禁用清单.xlsx")
DATA_DIR: "Path | None" = None                            # 由 ensure_data_dir() 填充


def ensure_data_dir() -> Path:
    """定位并缓存数据层目录：先看 AURA_DATA_DIR，再按锚点文件在候选位置找。"""
    global DATA_DIR
    if DATA_DIR is not None:
        return DATA_DIR
    env = os.environ.get("AURA_DATA_DIR")
    roots = ([Path(env)] if env else []) + [WS, REPO, WS.parent, REPO.parent]
    seen: set[str] = set()
    tried: list[Path] = []
    for r in roots:
        try:
            cands = [r] + sorted(p for p in r.iterdir() if p.is_dir())
        except OSError:
            continue
        for d in cands:
            key = str(d).lower()
            if key in seen:
                continue
            seen.add(key)
            tried.append(d)
            if all((d / a).exists() for a in DATA_ANCHORS):
                DATA_DIR = d
                return d
    listing = "\n".join(f"  - {p}" for p in tried) or "  （无）"
    die(
        "找不到数据层目录：需要同时包含以下锚点文件的目录\n"
        f"  {'、'.join(DATA_ANCHORS)}\n"
        f"已查找：\n{listing}\n"
        "数据层不入库（体积大、含内部资料）。请向数据负责人索取后放到 <仓库同级>/数据层/，\n"
        "或指定环境变量后重跑：set AURA_DATA_DIR=D:\\path\\to\\数据层"
    )
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


# ---------------------------------------------------------------- CAS 校验与修正
def cas_checksum_ok(cas: str) -> bool:
    """校验 CAS 号的校验位（最后一位）。格式 N1-N2-N3。

    校验位 = (Σ 从右往左第 i 位数字 × i) mod 10，i 从 1 开始，不含校验位本身。
    """
    parts = (cas or "").split("-")
    if len(parts) != 3:
        return False
    n1, n2, n3 = parts
    if not (n1.isdigit() and n2.isdigit() and len(n3) == 1 and n3.isdigit()):
        return False
    total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(n1 + n2)))
    return total % 10 == int(n3)


# 源 xlsx 的禁用清单区（H/I/J 列）在导出时整体错位一行：
# H 列的分段其实属于「上一行」的化合物，导致按行拼接出的 CAS 全部张冠李戴
# （7 条里 5 条与实际物质不符，其中 1 条校验位非法）。
# 以下为按中文名逐一核对后的正确值；值为 None 表示该物质无单一 CAS（天然原料等）。
BANNED_CAS_CORRECTIONS: dict[str, str | None] = {
    "葵子麝香": "83-66-9",        # 源写 120-58-1
    "二甲苯麝香": "81-15-2",       # 源写 116-66-5
    "酮麝香": "81-14-1",          # 源正确
    "铃兰醛": "80-54-6",          # 源正确（Lilial / Butylphenyl methylpropional）
    "海葵醛": "31906-04-4",       # 源写 10599-70-9（HICC / Lyral）
    "天然麝香": None,             # 天然动物源原料，无单一 CAS
    "天然灵猫香": None,
    "当归根油": "8015-64-3",       # 源写 471-28-3（精油，CAS 为 EINECS 群组号）
    "薄荷内酯": "13341-72-5",      # 源写 223743-5-7（非法校验位；源文件将 57 误敲为 5）
}


# ---------------------------------------------------------------- IFRA 别名表
# 源 xlsx 只给「中文名 + 英文名」，但成分清单里常写别的名字或缩写。
# 缺别名会导致两类后果：
#   漏检禁用物：Lilial / HICC / Lyral 是业内最通用的叫法，匹配不上就会漏报禁用；
#   用错限值：α-己基肉桂醛 的 en 写作 "Alpha-hexyl cinnamaldehyde"，
#             而清单常写 "Hexyl Cinnamal"，匹配不上就会退到「肉桂醛」的 0.05% 上限（实际 4%）。
# 别名属于数据，落在 ifra.json 里由前端 TS 与后端 Python 共读。
IFRA_LIMIT_ALIASES: dict[str, list[str]] = {
    "d-柠檬烯": ["柠檬烯", "limonene"],
    "香豆素": ["零陵香豆"],
    "香兰素": ["香草"],
    "α-己基肉桂醛": ["己基肉桂醛", "Hexyl Cinnamal", "hexyl cinnamal"],
}

IFRA_BANNED_ALIASES: dict[str, list[str]] = {
    "铃兰醛": ["Lilial", "lilial", "p-BMHCA", "Butylphenyl methylpropional"],
    "海葵醛": ["HICC", "Lyral", "新铃兰醛",
               "hydroxyisohexyl", "hydroxyisohexyl 3-cyclohexene carboxaldehyde"],
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

    # —— CAS 修正与校验 ——
    # 禁用清单的 CAS 在源文件里错位，必须按中文名替换；并标记修正痕迹以便审计。
    for b in banned:
        fixed = BANNED_CAS_CORRECTIONS.get(b["zh"], b["cas"])
        if fixed != b["cas"]:
            b["casSource"] = b["cas"] or None      # 保留源值备查
            b["cas"] = fixed
        if b["cas"] and not cas_checksum_ok(b["cas"]):
            b["casInvalid"] = True                 # 双重保险：仍非法则显式标记
        alias = IFRA_BANNED_ALIASES.get(b["zh"])
        if alias:
            b["aliases"] = alias
    for l in limits:
        alias = IFRA_LIMIT_ALIASES.get(l["zh"])
        if alias:
            l["aliases"] = alias
    # 限量与天然表的 CAS 一并做校验位体检（只报告，不改动）
    bad_limits = [l["cas"] for l in limits if l["cas"] and not cas_checksum_ok(l["cas"])]
    if bad_limits:
        print(f"  !! 限量表 CAS 校验位异常 {len(bad_limits)} 条：{bad_limits}")
    n_fixed = sum(1 for b in banned if "casSource" in b)
    n_alias = sum(1 for b in banned if "aliases" in b) + sum(1 for l in limits if "aliases" in l)
    print(f"  禁用清单 CAS 修正 {n_fixed} 条（源文件错位）；写入别名 {n_alias} 条")

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


# ---------------------------------------------------------------- 4) 26 种致敏香料（EU 标注清单）
def build_allergens26():
    rows = xlsx_rows(DATA_DIR / "表格26种致敏香料.xlsx")
    items = []
    for cells in rows:
        if not cells.get("B") or not cells.get("C"):
            continue
        if cells["B"] in ("INCI 英文名",) or cells["C"] in ("中文通用名",):
            continue
        cas = re.sub(r"[‒‑–—\u2010-\u2015]+", "-", cells.get("D", "").strip())
        items.append({
            "no": int(cells.get("A", "0") or 0),
            "inci": cells["B"].strip(),
            "zh": cells["C"].strip(),
            "cas": cas,
            "note": cells.get("E", "").strip(),
        })
    return {"source": "数据层/表格26种致敏香料.xlsx", "items": items[:26]}


# ---------------------------------------------------------------- 5) IgE Ⅰ 型速发材料
def build_ige():
    rows = xlsx_rows(DATA_DIR / "IgE致敏原表格.xlsx")
    items = []
    category = ""
    for cells in rows:
        only_b = [k for k in cells if k != "A"]
        if only_b == ["B"] and cells.get("B", "").strip().endswith(("类:", "类：", "类")):
            category = cells["B"].strip().rstrip(":：")
            continue
        if not cells.get("B") or not cells.get("C"):
            continue
        if cells["B"].strip() in ("原料中文名", "原料类型"):
            continue
        items.append({
            "category": category,
            "zh": cells["B"].strip(),
            "en": cells.get("C", "").strip(),
            "type": cells.get("D", "").strip(),
            "families": cells.get("E", "").strip(),
            "risk": cells.get("F", "").strip(),
            "note": cells.get("G", "").strip(),
        })
    return {"source": "数据层/IgE致敏原表格.xlsx", "items": items}


# ---------------------------------------------------------------- 6) 香材词典（天然 + 合成单体）
def build_materials():
    paras = [t for _s, t in docx_paragraphs(DATA_DIR / "香水成分数据及过敏香料.docx")]
    natural: list[str] = []
    synthetic: dict[str, list[str]] = {}
    state = None
    category = ""
    for t in paras:
        t = t.strip()
        if not t:
            continue
        if t.startswith("天然香料"):
            state = "natural"
            continue
        if t.startswith("合成单体香料"):
            state = "synthetic"
            continue
        if t.startswith(("辅料分类", "微量添加物", "防腐剂", "螯合剂", "光稳定剂")):
            state = None
            continue
        if state == "natural" and len(t) <= 8 and not re.search(r"[：:（）()]", t) and not re.match(r"^.{1,3}类(香料|)$", t):
            natural.append(t)
        elif state == "synthetic":
            if t.endswith("单体") and len(t) <= 14:
                category = t
                synthetic.setdefault(category, [])
            elif category and re.search(r"[、,，]", t):
                synthetic[category].extend(x.strip() for x in re.split(r"[、,，]\s*", t) if x.strip())
    return {
        "source": "数据层/香水成分数据及过敏香料.docx",
        "natural": natural,
        "synthetic": synthetic,
        "syntheticCount": sum(len(v) for v in synthetic.values()),
    }


def write_json(name: str, obj: object) -> None:
    """写 JSON：UTF-8 无 BOM、强制 LF。

    强制 LF 是必要的：Windows 上默认的文本模式会把 \\n 翻成 CRLF，于是
    每次重跑都会让 6 个 JSON 在 git 里显示为改动（.gitattributes 里
     `*.json text eol=lf`），队友会误以为数据变了。
    """
    with (OUT_DIR / name).open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    data_dir = ensure_data_dir()
    print(f"数据层：{data_dir}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    perfumes = build_perfumes()
    ifra = build_ifra()
    ingredients = build_ingredients()
    allergens26 = build_allergens26()
    ige = build_ige()
    materials = build_materials()

    write_json("perfumes.json", perfumes)
    write_json("ifra.json", ifra)
    write_json("ingredients.json", ingredients)
    write_json("allergens26.json", allergens26)
    write_json("ige.json", ige)
    write_json("materials.json", materials)

    print(f"perfumes: {len(perfumes['perfumes'])} 款")
    for p in perfumes["perfumes"][:3]:
        print(f"  - {p['brand']} {p['name']} ({p['familyZh']}/{p['familyKey']}) 前中后 {tuple(len(l['notes']) for l in p['pyramid'])} 关键词={p['keywords'][:20]}")
    print(f"ifra: limits={len(ifra['limits'])} banned={len(ifra['banned'])} natural={len(ifra['natural'])}")
    for b in ifra["banned"]:
        print(f"  禁 {b['zh']} cas={b['cas']} {b['control']} {b['reason'][:24]}")
    print(f"ingredients: {len(ingredients['entries'])} 条")
    print(f"allergens26: {len(allergens26['items'])} 条（EU 标注清单）")
    print(f"ige: {len(ige['items'])} 条（Ⅰ 型速发材料）")
    for it in ige["items"][:3]:
        print(f"  IgE {it['zh']} [{it['category']}] {it['risk']}")
    print(f"materials: 天然 {len(materials['natural'])} + 合成 {materials['syntheticCount']}（{len(materials['synthetic'])} 类）")
    if len(perfumes["perfumes"]) != 12:
        print(f"WARN: 期望 12 款，实际 {len(perfumes['perfumes'])}")
    if len(ifra["limits"]) != 20 or len(ifra["banned"]) != 9:
        print(f"WARN: IFRA 期望 20/9/2，实际 {len(ifra['limits'])}/{len(ifra['banned'])}/{len(ifra['natural'])}")


if __name__ == "__main__":
    main()
