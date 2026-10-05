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
