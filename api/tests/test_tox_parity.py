"""毒理参数：单一数据源 + 双引擎查找一致性。

背景：
- 毒理表原为 TS（web/src/lib/qra2/nesil.ts）与 Python（api/app/data.py）各手写一份，
  现统一为 web/src/data/tox.json，两端共读。
- 查找原用「子串包含 + 首个命中」，归一化后长名包含短名会误匹配
  （isoeugenol 含 eugenol、hexylcinnamal 含 cinnamal、新铃兰醛 含 铃兰醛），
  已改为「最长键优先 + HICC 别名归一」。

本文件同时锁住：数据源一致、Python 端结论正确、与 TS 引擎结果一致。
TS 侧对应守卫见 web/src/lib/tox-match.test.ts。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import data as D

TOX_JSON = Path(__file__).resolve().parents[2] / "web" / "src" / "data" / "tox.json"


def test_tox_json_is_single_source():
    """tox.json 存在、字段完整，且 Python TOX 与之一一对应。"""
    doc = json.loads(TOX_JSON.read_text(encoding="utf-8"))
    assert len(doc["entries"]) == 22
    assert doc["saf"] == D.SAF == 100
    assert doc["demoPenalty"] == D.DEMO_PENALTY == 3
    assert len(D.TOX) == len(doc["entries"])

    by_zh = {e["zh"]: e for e in doc["entries"]}
    for t in D.TOX:
        e = by_zh[t["zh"]]
        assert t["nesil"] == e["nesil"], t["zh"]
        assert t["demo"] == (e["source"] != "documented"), t["zh"]
        assert t["keys"], f"{t['zh']} 缺 keys"


def test_demo_entries_are_null_not_fabricated():
    demo = [t for t in D.TOX if t["demo"]]
    assert sorted(t["zh"] for t in demo) == sorted(["乙酸苄酯", "乙酸香茅酯", "乙酸香叶酯"])
    for t in demo:
        assert t["nesil"] is None, f"{t['zh']} 无文献值却填了数字"


@pytest.mark.parametrize("probe,zh,nesil", [
    # —— 回归：原「子串误匹配」的四个用例 ——
    ("Isoeugenol", "异丁香酚", 250),
    ("Hexyl Cinnamal", "己基肉桂醛", 23600),
    ("Amyl Cinnamal", "戊基肉桂醛", 23600),
    ("新铃兰醛", "新铃兰醛（海葵醛）", 4000),
    # —— HICC / Lyral 缩写归一 ——
    ("HICC", "新铃兰醛（海葵醛）", 4000),
    ("Lyral", "新铃兰醛（海葵醛）", 4000),
    ("Hydroxyisohexyl 3-Cyclohexene Carboxaldehyde", "新铃兰醛（海葵醛）", 4000),
    # —— 原有正常命中不受影响 ——
    ("d-Limonene", "柠檬烯", 10000),
    ("Limonene", "柠檬烯", 10000),
    ("柠檬烯", "柠檬烯", 10000),
    ("Linalool", "芳樟醇", 15000),
    ("Citral", "柠檬醛", 1400),
    ("Eugenol", "丁香酚", 5900),
    ("Geraniol", "香叶醇", 11800),
    ("Benzyl Salicylate", "水杨酸苄酯", 17700),
    ("Cinnamal", "肉桂醛", 591),
    ("Butylphenyl Methylpropional", "铃兰醛", 4100),
    ("Lilial", "铃兰醛", 4100),
    ("铃兰醛", "铃兰醛", 4100),
])
def test_lookup_tox_correct(probe: str, zh: str, nesil: int):
    t = D.lookup_tox(probe)
    assert t is not None, f"{probe} 未命中"
    assert t["zh"] == zh, f"{probe} 命中 {t['zh']}，期望 {zh}"
    assert t["nesil"] == nesil


def test_lookup_tox_unknown_returns_none():
    assert D.lookup_tox("UnknownIngredientXYZ") is None
    assert D.lookup_tox("") is None


def test_hicc_not_matched_as_lilial():
    """新铃兰醛（禁用，49 修正案）不得被判成铃兰醛（另一物质）。"""
    hicc = D.lookup_tox("HICC")
    lilial = D.lookup_tox("Lilial")
    assert hicc is not None and lilial is not None
    assert hicc["zh"] != lilial["zh"]
    assert hicc["nesil"] == 4000 and lilial["nesil"] == 4100


def test_engine_output_uses_demo_penalty_and_insufficient():
    """无文献值的成分必须走 evidence=insufficient 且不编造 AEL。"""
    from app.modules.qra2 import analyze_ingredient

    r = analyze_ingredient("乙酸苄酯", 5.0, "healthy")
    assert r["ael"] is None
    assert r["aelEvidence"] == "insufficient"
    assert r["level"] != "low", "数据不足不得判为安全（数据不足 ≠ 安全）"


def test_engine_ael_matches_documented_nesil():
    """有文献值时 AEL = NESIL / SAF（SAF=100）。"""
    from app.modules.qra2 import analyze_ingredient

    assert analyze_ingredient("d-Limonene", 5.0, "healthy")["ael"] == pytest.approx(100.0)
    assert analyze_ingredient("Linalool", 5.0, "healthy")["ael"] == pytest.approx(150.0)
    assert analyze_ingredient("Isoeugenol", 0.05, "healthy")["ael"] == pytest.approx(2.5)


# ---------------------------------------------------------------- IFRA 限值/禁用匹配
# 与 web/src/lib/ifra-match.test.ts 对应。原匹配为「子串包含 + 首个命中」，
# 实测 6 处错误，其中 3 处会改变判定结论。
@pytest.mark.parametrize("probe,zh,limit", [
    # 回归：三处限值误匹配（会改变判定）
    ("Isoeugenol", "异丁香酚", 0.05),          # 原判成 丁香酚 0.5%（偏宽松 10×）
    ("异丁香酚", "异丁香酚", 0.05),
    ("Hexyl Cinnamal", "α-己基肉桂醛", 4.0),   # 原判成 肉桂醛 0.05%（偏严格 80×）
    ("己基肉桂醛", "α-己基肉桂醛", 4.0),
    ("Amyl Cinnamal", "戊基肉桂醛", 1.0),      # 原判成 肉桂醛 0.05%（偏严格 20×）
    ("戊基肉桂醛", "戊基肉桂醛", 1.0),
    # 原有正常命中不受影响
    ("Limonene", "d-柠檬烯", 15.0), ("d-Limonene", "d-柠檬烯", 15.0),
    ("柠檬烯", "d-柠檬烯", 15.0),
    ("Eugenol", "丁香酚", 0.5), ("Cinnamal", "肉桂醛", 0.05),
    ("Linalool", "芳樟醇", 10.0), ("Citral", "柠檬醛", 0.6),
    ("Coumarin", "香豆素", 1.6), ("零陵香豆", "香豆素", 1.6),
    ("Vanillin", "香兰素", 10.0), ("香草", "香兰素", 10.0),
    ("Geraniol", "香叶醇", 4.0), ("Citronellol", "香茅醇", 4.0),
    ("Benzyl Alcohol", "苯甲醇", 1.0), ("Cinnamyl alcohol", "肉桂醇", 0.4),
    ("Farnesol", "法尼醇", 0.5), ("Benzyl Salicylate", "水杨酸苄酯", 4.0),
    ("Benzyl acetate", "乙酸苄酯", 20.0), ("Geranyl acetate", "乙酸香叶酯", 20.0),
    ("Citronellyl acetate", "乙酸香茅酯", 20.0), ("Benzaldehyde", "苯甲醛", 1.0),
])
def test_lookup_ifra_limit_correct(probe: str, zh: str, limit: float):
    l = D.lookup_ifra_limit(probe)
    assert l is not None, f"{probe} 未命中"
    assert l["zh"] == zh, f"{probe} 命中 {l['zh']}，期望 {zh}"
    assert l["limitPct"] == pytest.approx(limit)


@pytest.mark.parametrize("probe,zh", [
    # 回归：禁用物漏检 / 错配（最严重——漏报禁用）
    ("Lilial", "铃兰醛"),
    ("Butylphenyl Methylpropional", "铃兰醛"),
    ("铃兰醛", "铃兰醛"),
    ("HICC", "海葵醛"),                        # 原为 null（完全漏检）
    ("Lyral", "海葵醛"),                       # 原为 null
    ("新铃兰醛", "海葵醛"),                      # 原判成 铃兰醛（另一物质）
    ("海葵醛", "海葵醛"),
    ("Hydroxyisohexyl 3-Cyclohexene Carboxaldehyde", "海葵醛"),
    # 原有正常命中
    ("葵子麝香", "葵子麝香"), ("二甲苯麝香", "二甲苯麝香"), ("酮麝香", "酮麝香"),
    ("天然麝香", "天然麝香"), ("天然灵猫香", "天然灵猫香"),
    ("当归根油", "当归根油"), ("薄荷内酯", "薄荷内酯"),
])
def test_lookup_banned_correct(probe: str, zh: str):
    b = D.lookup_banned(probe)
    assert b is not None, f"{probe} 未命中（漏检禁用物）"
    assert b["zh"] == zh, f"{probe} 命中 {b['zh']}，期望 {zh}"


def test_ifra_unknown_returns_none():
    assert D.lookup_ifra_limit("UnknownXYZ") is None
    assert D.lookup_ifra_limit("") is None
    assert D.lookup_banned("UnknownXYZ") is None
    assert D.lookup_banned("") is None


def test_hicc_and_lilial_are_distinct_banned_entries():
    """新铃兰醛(海葵醛) 与 铃兰醛 是不同物质、不同禁用原因，不得混淆。"""
    hicc = D.lookup_banned("HICC")
    lilial = D.lookup_banned("Lilial")
    assert hicc is not None and lilial is not None
    assert hicc["zh"] != lilial["zh"]
    assert hicc["cas"] != lilial["cas"]


def test_ifra_aliases_present_in_data():
    """别名属于数据，落在 ifra.json 的 aliases 字段（前端 TS 与后端共读）。"""
    lilial = next(b for b in D.IFRA["banned"] if b["zh"] == "铃兰醛")
    hicc = next(b for b in D.IFRA["banned"] if b["zh"] == "海葵醛")
    hexyl = next(l for l in D.IFRA["limits"] if l["zh"] == "α-己基肉桂醛")
    assert "Lilial" in lilial.get("aliases", [])
    assert "HICC" in hicc.get("aliases", [])
    assert "新铃兰醛" in hicc.get("aliases", [])
    assert "Hexyl Cinnamal" in hexyl.get("aliases", [])

