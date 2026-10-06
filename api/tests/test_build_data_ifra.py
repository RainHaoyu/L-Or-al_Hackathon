"""待办 1-4：IFRA 禁用清单解析的根因修复。

历史事故：源 xlsx 的禁用清单区里，CAS 被拆成三格（`"120" | "58" | "1"`），
而"无 CAS"的行不拆——同一个逻辑字段在不同行落在不同列。导出时 CAS 分段整体错位，
7 条里 5 条与实际物质不符，其中 1 条校验位非法。当时的兜法是一张人工修正表，
但它只是**盖住**了错误：源文件再变一次（换版本、插行、挪列），产出会重新变错
而且没人知道——因为「校验位合法」并不等于「化合物正确」（`120-58-1` 就是个合法但错误的 CAS）。

现在的机制（本文件逐条锁住）：
  1. 解析**不按列位置、按内容模式**（`classify_ban_row`）：行/列挪动不会静默错位；
  2. 核对表 `BANNED_CAS_VERIFIED` 同时记录「核对时看到的源值」，源值对不上 → 报错中止；
  3. 禁用条目的**名字集合**必须与核对表完全一致 → 新增/丢失条目 → 报错中止；
  4. 校验不通过时**一个 JSON 都不写**（main() 先全量构建、最后统一落盘）。

本文件的端到端用例就是验收条件本身：把源 xlsx 改坏（复现历史错位）后重跑管线，
要么产出仍然正确、要么明确报错——不允许静默产出错误的 CAS。
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "web" / "scripts" / "build_data.py"
SHEET = "xl/worksheets/sheet1.xml"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
IFRA_XLSX = "IFRA 51st Amendment Cat4香水禁用清单.xlsx"


def _load_build_data():
    """按路径加载 web/scripts/build_data.py（它不是包，也没有 __init__.py）。"""
    spec = importlib.util.spec_from_file_location("build_data_under_test", BUILD)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


build_data = _load_build_data()


def _real_data_dir() -> Path | None:
    env = os.environ.get("AURA_DATA_DIR")
    cands = [Path(env)] if env else []
    cands += [REPO.parent / "数据层", REPO / "数据层", REPO.parent.parent / "数据层"]
    for d in cands:
        if d.is_dir() and all((d / a).exists() for a in build_data.DATA_ANCHORS):
            return d
    return None


needs_data = pytest.mark.skipif(
    _real_data_dir() is None, reason="数据层目录不在（不入库，需单独提供；见 README §二）"
)


# ================================================================ 1) 解析器单测
def test_three_piece_cas_and_multiline_tail():
    """源文件的真实形态：CAS 三格 + 中文名 + 多行尾巴（英文名/管控/备注）。"""
    row = {"H": "120", "I": "58", "J": "1", "K": "葵子麝香",
           "L": "Musk\nambrette\n完全禁用\n硝基麝香，光毒性"}
    got = build_data.classify_ban_row(row)
    assert got is not None
    assert got["cas"] == "120-58-1"
    assert got["zh"] == "葵子麝香"
    assert got["en"] == "Musk ambrette", "英文名被拆到多行时必须拼回来，不能只取第一行"
    assert got["control"] == "完全禁用"
    assert got["reason"] == "硝基麝香，光毒性"


def test_whole_cas_in_one_cell():
    """上游若把 CAS 合成一格（正常导出形态），也必须能解析。"""
    row = {"H": "83-66-9", "I": "葵子麝香", "J": "Musk ambrette",
           "K": "完全禁用", "L": "硝基麝香，光毒性"}
    got = build_data.classify_ban_row(row)
    assert got is not None
    assert (got["cas"], got["zh"], got["en"]) == ("83-66-9", "葵子麝香", "Musk ambrette")


def test_row_shifted_left_by_one_column():
    """整行左移一列（CAS 落到 G/H/I）也要解析正确——这是"不按列位置"的意义。"""
    row = {"G": "120", "H": "58", "I": "1", "J": "葵子麝香",
           "K": "Musk ambrette", "L": "完全禁用\n硝基麝香，光毒性"}
    got = build_data.classify_ban_row(row)
    assert got is not None
    assert (got["cas"], got["zh"], got["en"], got["reason"]) == (
        "120-58-1", "葵子麝香", "Musk ambrette", "硝基麝香，光毒性")


def test_row_without_cas_keeps_english_name_and_reason():
    """无 CAS 的行（天然麝香）：名字在最前面，英文名被拆到两格，备注在最后一格。"""
    row = {"I": "天然麝香", "J": "Natural", "K": "musk", "L": "完全禁用\n动物源"}
    got = build_data.classify_ban_row(row)
    assert got is not None
    assert got["cas"] is None
    assert got["zh"] == "天然麝香"
    assert got["en"] == "Natural musk"
    assert got["reason"] == "动物源"


def test_reason_containing_the_word_disabled_is_not_a_control_type():
    """『50修正案起禁用，生殖毒性』是备注，不能被当成管控类型。"""
    row = {"H": "80", "I": "54", "J": "6", "K": "铃兰醛",
           "L": "Butylphenyl\nmethylpropional(Lilial)\n完全禁用\n50修正案起禁用，生殖毒性"}
    got = build_data.classify_ban_row(row)
    assert got is not None
    assert got["control"] == "完全禁用"
    assert got["reason"] == "50修正案起禁用，生殖毒性"


def test_title_header_and_blank_rows_are_not_data():
    assert build_data.classify_ban_row({"H": "Cat4\n香水禁用清单"}) is None
    assert build_data.classify_ban_row({"H": "CAS号", "I": "中文名称", "J": "英文名称",
                                        "K": "管控类型", "L": "备注"}) is None
    assert build_data.classify_ban_row({"G": "", "H": ""}) is None
    assert build_data.classify_ban_row({}) is None


def test_broken_cas_pieces_are_flagged_not_guessed():
    """CAS 只解析出两段：既不是整串也不是三段 → 标记 malformed，绝不猜。"""
    row = {"H": "58", "I": "1", "J": "葵子麝香", "K": "完全禁用"}
    got = build_data.classify_ban_row(row)
    assert got is not None and "malformed" in got


def test_missing_chinese_name_is_rejected():
    """没有真正的中文名（只剩管控词/备注）的行必须被拒，不能拿备注当名字。"""
    row = {"H": "120", "I": "58", "J": "1", "K": "完全禁用\n硝基麝香"}
    got = build_data.classify_ban_row(row)
    with pytest.raises(SystemExit):
        build_data.verify_banned([got] if got else [])


# ================================================================ 2) 端到端：改坏源文件
def _rewrite_sheet(path: Path, mutate) -> None:
    """就地改写 xlsx 里的 sheet1.xml（其余部件原样保留）。

    mutate 收到 (root, refs)：refs 是各 <row> 的 r 属性，顺序与 xlsx_rows 一致。
    注意：源文件的**第一个 row 是 r="2"**（第 1 行没被序列化），所以绝不能假定
    「第 n 个数据行 = r=n」——下面一律按内容找到目标行。
    """
    rows_before = build_data.xlsx_rows(path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        items = {n: z.read(n) for n in names}
    root = ET.fromstring(items[SHEET])
    refs = [r.get("r") for r in root.iter(NS + "row")]
    assert len(refs) == len(rows_before), "行序假设不成立，改坏脚本需要更新"
    mutate(root, refs)
    items[SHEET] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, items[n])


def _cell(root, ref: str):
    for c in root.iter(NS + "c"):
        if c.get("r") == ref:
            return c
    return None


def _row_num(refs: list[str], rows, zh: str) -> str:
    """按中文名定位禁用清单的行号（不依赖固定的 r 值）。"""
    for ref, cells in zip(refs, rows):
        if cells.get("K") == zh:
            return ref
    raise AssertionError(f"源文件里找不到 {zh} 所在行")


def _clear_cas_piece(path: Path) -> None:
    """抹掉葵子麝香那一行的 CAS 首段（H 列）→ CAS 只剩两段，必须被拒。"""

    def mutate(root, refs):
        num = _row_num(refs, build_data.xlsx_rows(path), "葵子麝香")
        c = _cell(root, f"H{num}")
        assert c is not None, "源文件结构与预期不符（找不到 CAS 首段单元格）"
        for child in list(c):
            c.remove(child)

    _rewrite_sheet(path, mutate)


def _swap_cas_rows(path: Path) -> None:
    """把葵子麝香与二甲苯麝香两行的 CAS 分段对调 —— 复现历史「CAS 与名字错位」。"""

    rows_before = build_data.xlsx_rows(path)

    def mutate(root, refs):
        na = _row_num(refs, rows_before, "葵子麝香")
        nb = _row_num(refs, rows_before, "二甲苯麝香")
        for col in "HIJ":
            a, b = _cell(root, f"{col}{na}"), _cell(root, f"{col}{nb}")
            assert a is not None and b is not None
            pa, pb = list(a), list(b)
            for ch in pa:
                a.remove(ch)
            for ch in pb:
                b.remove(ch)
            for ch in pb:
                a.append(ch)
            for ch in pa:
                b.append(ch)

    _rewrite_sheet(path, mutate)


def _prepare(tmp_path: Path, mutate=None) -> tuple[Path, Path]:
    src = _real_data_dir()
    assert src is not None
    dst = tmp_path / "数据层"
    shutil.copytree(src, dst)
    if mutate is not None:
        mutate(dst / IFRA_XLSX)
    return dst, tmp_path / "out"


def _run_pipeline(src: Path, out: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "AURA_DATA_DIR": str(src), "AURA_OUT_DIR": str(out),
           "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    env.pop("DASHSCOPE_API_KEY", None)
    return subprocess.run([sys.executable, str(BUILD)], capture_output=True, text=True,
                          encoding="utf-8", env=env, cwd=str(REPO), timeout=300)


@needs_data
def test_pipeline_accepts_unmodified_source(tmp_path: Path) -> None:
    """基线：源文件没动时，产出必须与核对表逐条一致。"""
    src, out = _prepare(tmp_path)
    r = _run_pipeline(src, out)
    assert r.returncode == 0, r.stdout + r.stderr

    ifra = json.loads((out / "ifra.json").read_text("utf-8"))
    got = {b["zh"]: b["cas"] for b in ifra["banned"]}
    expect = {name: fixed for name, (_src, fixed) in build_data.BANNED_CAS_VERIFIED.items()}
    assert got == expect

    # 修正过的条目要留审计痕迹：源值一定与最终值不同
    corrected = {b["zh"] for b in ifra["banned"] if "casSource" in b}
    assert corrected == {"葵子麝香", "二甲苯麝香", "海葵醛", "当归根油", "薄荷内酯"}
    for b in ifra["banned"]:
        assert "casInvalid" not in b, "不应再有校验位非法的 CAS 落盘"


@needs_data
@pytest.mark.parametrize(
    "mutate, needle, why",
    [
        (_swap_cas_rows, "葵子麝香", "与核对时不一致"),
        (_clear_cas_piece, "葵子麝香", "CAS 分段"),
    ],
    ids=["CAS 分段整体错位一行", "CAS 分段被抹成两段"],
)
def test_pipeline_refuses_broken_source(tmp_path: Path, mutate, needle: str, why: str) -> None:
    """验收条件：源文件被改坏后必须报错中止，不许静默产出错误的 CAS。"""
    src, out = _prepare(tmp_path, mutate)
    r = _run_pipeline(src, out)
    msg = r.stdout + r.stderr
    assert r.returncode != 0, f"源文件被改坏却成功了，产出可能是错的：\n{msg}"
    assert needle in msg, f"报错信息应点名出问题的条目，实际是：\n{msg}"
    assert why in msg, f"报错信息应说明是哪道校验拦下的（期望含「{why}」）：\n{msg}"
    assert not (out / "ifra.json").exists(), "校验失败时不允许落盘任何 JSON"
