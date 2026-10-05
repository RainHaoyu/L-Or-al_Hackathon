"""QRA2 核心判定：人群策略 / 四闸门 / 氧化 —— 跨引擎对齐与不变量。

本文件对应台账 B1。此前只有分布基元、毒理查找、IFRA 匹配有跨引擎对齐测试，
**闸门判定、人群策略、氧化这三块（QRA2 的核心逻辑）完全没有**。
在已知存在「96% 抽样区间失真」「漏检禁用物」这类问题的代码库里，
核心判定没有对齐验证是明确的风险敞口。

基准值来源：vitest 实跑 web/src/lib/qra2/（seed=20261005, n=10000），
与 Python 侧逐字段比对通过（19 个闸门用例 × 14 字段 + 24 项氧化值）。

同时固化两条**判据的数学性质**（不是缺陷，是设计后果，防止被误当 bug 修掉）：
  - 黄灯窗口可达性：见 test_yellow_reachability_is_bounded_by_tpop
"""
from __future__ import annotations

import pytest

from app.modules.qra2 import (
    K25_TERPENE,
    POP_POLICY,
    Q10,
    STORAGE_ENV,
    T_REF,
    analyze_ingredient,
    compute_d,
    sample_cel,
)

SEED = 20261005

# ---------------------------------------------------------------- 常量与人群策略
# (alpha, beta, policy, T_pop) —— 与 TS POP_POLICY 逐字段一致
POP_TABLE = {
    "healthy": (1.0, 1.0, "P90", 1.0),
    "sensitive": (3.0, 1.0, "P99", 3.0),
    "pregnant": (1.0, 1.0, "P99", 1.0),
    "rhinitis": (1.2, 1.0, "P99", 1.2),
    "anosmic": (1.0, 1.0, "P99", 1.0),
}


@pytest.mark.parametrize("pop,expected", sorted(POP_TABLE.items()))
def test_population_policy_matches_ts(pop: str, expected: tuple):
    cfg = POP_POLICY[pop]
    alpha, beta, policy, tp = expected
    assert cfg["alpha"] == alpha
    assert cfg["beta"] == beta
    assert cfg["policy"] == policy
    assert cfg["alpha"] * cfg["beta"] == pytest.approx(tp)


def test_oxidation_constants_match_ts():
    assert K25_TERPENE == 0.00178
    assert Q10 == 1.8
    assert T_REF == 25
    assert STORAGE_ENV == {"cool": {"T": 15, "L": 0.0},
                           "room": {"T": 25, "L": 0.3},
                           "hot": {"T": 35, "L": 0.8}}


# ---------------------------------------------------------------- 四闸门
# (name, concPct, population, ifraLimitPct, banned) -> 期望字段
# 字段顺序：matched, ael, evidence, level, gate, ifraLevel, qra2Level, bannedLevel,
#           p50, p90, p99, marginPoint, marginP99, marginPolicy
GATE_CASES = [
    # 0 QRA2 绿：健康 × 柠檬烯 5%
    (("d-Limonene", 5, "healthy", None, False),
     (True, 100.0, "documented", "low", "四道闸门均未触发", None, "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 11.084119832798121)),
    # 1 QRA2 绿：健康 × 20%（高浓度仍绿，红需 P99 超 AEL）
    (("d-Limonene", 20, "healthy", None, False),
     (True, 100.0, "documented", "low", "四道闸门均未触发", None, "low", None,
      15.024782113042711, 36.087664698138, 67.90529406159723, 5.0,
      1.4726392305920875, 2.7710299581995304)),
    # 2 人群分化：敏感肌 × 20% 出黄灯（T_pop=3 生效）
    (("d-Limonene", 20, "sensitive", None, False),
     (True, 100.0, "documented", "mid", "QRA2 分位", None, "mid", None,
      15.024782113042711, 36.087664698138, 67.90529406159723, 5.0,
      1.4726392305920875, 0.4908797435306958)),
    # 3 QRA2 红：40% 时 P99 超过 AEL
    (("d-Limonene", 40, "healthy", None, False),
     (True, 100.0, "documented", "high", "QRA2 分位", None, "high", None,
      30.049564226085423, 72.175329396276, 135.81058812319446, 2.5,
      0.7363196152960437, 1.3855149790997652)),
    # 4 IFRA 红：浓度 ≥ 上限
    (("d-Limonene", 5, "healthy", 4.0, False),
     (True, 100.0, "documented", "high", "IFRA 闸门", "high", "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 11.084119832798121)),
    # 5 IFRA 黄：浓度达上限八成（QRA2 本身绿）—— 证明 IFRA 能压过 QRA2
    (("d-Limonene", 5, "healthy", 5.5, False),
     (True, 100.0, "documented", "mid", "IFRA 闸门", "mid", "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 11.084119832798121)),
    # 6-8 丁香酚：低/八成黄/超限红
    (("Eugenol", 0.3, "healthy", 0.5, False),
     (True, 59.0, "documented", "low", "四道闸门均未触发", "low", "low", None,
      0.22537173169564068, 0.5413149704720699, 1.0185794109239583,
      196.66666666666669, 57.92380973662212, 108.99384502251488)),
    (("Eugenol", 0.45, "healthy", 0.5, False),
     (True, 59.0, "documented", "mid", "IFRA 闸门", "mid", "low", None,
      0.3380575975434611, 0.811972455708105, 1.527869116385938,
      131.1111111111111, 38.61587315774807, 72.66256334834324)),
    (("Eugenol", 0.6, "healthy", 0.5, False),
     (True, 59.0, "documented", "high", "IFRA 闸门", "high", "low", None,
      0.45074346339128135, 1.0826299409441398, 2.0371588218479166,
      98.33333333333334, 28.96190486831106, 54.49692251125744)),
    # 9-10 异丁香酚：0.04 绿 / 0.05 恰好触限判红
    (("Isoeugenol", 0.04, "healthy", 0.05, False),
     (True, 2.5, "documented", "low", "四道闸门均未触发", "low", "low", None,
      0.030049564226085422, 0.072175329396276, 0.13581058812319446,
      62.5, 18.407990382401096, 34.63787447749413)),
    (("Isoeugenol", 0.05, "healthy", 0.05, False),
     (True, 2.5, "documented", "high", "IFRA 闸门", "high", "low", None,
      0.03756195528260678, 0.09021916174534497, 0.16976323515399305,
      50.0, 14.726392305920879, 27.710299581995308)),
    # 11 柠檬醛低浓度绿
    (("Citral", 0.3, "healthy", 0.6, False),
     (True, 14.0, "documented", "low", "四道闸门均未触发", "low", "low", None,
      0.22537173169564068, 0.5413149704720699, 1.0185794109239583,
      46.66666666666667, 13.744632818859486, 25.86294627652895)),
    # 12 柠檬醛 5%：IFRA 红 与 QRA2 红 同时命中
    (("Citral", 5, "healthy", 0.6, False),
     (True, 14.0, "documented", "high", "IFRA 闸门", "high", "high", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308,
      2.8, 0.824677969131569, 1.551776776591737)),
    # 13 禁用闸门：任何浓度直判红
    (("Lilial", 0.01, "pregnant", None, True),
     (True, None, "insufficient", "high", "禁用闸门", None, None, "high",
      None, None, None, None, None, None)),
    # 14 无 NESIL 文献值 → 保守黄，不编造 AEL
    (("乙酸苄酯", 5, "healthy", None, False),
     (True, None, "insufficient", "mid", "数据不足", None, "mid", None,
      None, None, None, None, None, None)),
    # 15 库中无此成分 → 同样保守黄，不判绿
    (("UnknownXYZ", 5, "healthy", None, False),
     (False, None, "insufficient", "mid", "数据不足", None, None, None,
      None, None, None, None, None, None)),
    # 16-18 pregnant / anosmic / rhinitis 同输入（T_pop 不同 → marginPolicy 不同）
    (("d-Limonene", 5, "pregnant", None, False),
     (True, 100.0, "documented", "low", "四道闸门均未触发", None, "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 5.89055692236835)),
    (("d-Limonene", 5, "anosmic", None, False),
     (True, 100.0, "documented", "low", "四道闸门均未触发", None, "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 5.89055692236835)),
    (("d-Limonene", 5, "rhinitis", None, False),
     (True, 100.0, "documented", "low", "四道闸门均未触发", None, "low", None,
      3.756195528260678, 9.0219161745345, 16.976323515399308, 20.0,
      5.89055692236835, 4.908797435306958)),
]

GATE_FIELDS = ["matched", "ael", "evidence", "level", "gate", "ifra_level", "qra2_level",
               "banned_level", "p50", "p90", "p99", "margin_point", "margin_p99",
               "margin_policy"]


def _run_gate(case):
    name, conc, pop, ifra, banned = case
    return analyze_ingredient(name, conc, pop, ifra_limit_pct=ifra, banned=banned, seed=SEED)


@pytest.mark.parametrize("case,expected", GATE_CASES, ids=[str(c[0]) for c, _ in GATE_CASES])
def test_gate_matches_ts(case, expected):
    """19 个闸门用例 × 14 字段与 TS 引擎逐字段一致。"""
    r = _run_gate(case)
    actual = (
        r["matched"], r["ael"], r["aelEvidence"], r["level"], r["dominantGate"],
        r["ifraLevel"], r["qra2Level"], r["bannedLevel"],
        r["p50"], r["p90"], r["p99"], r["marginPoint"], r["marginP99"], r["marginPolicy"],
    )
    assert len(actual) == len(GATE_FIELDS)
    for field, got, want in zip(GATE_FIELDS, actual, expected):
        if isinstance(want, float) or isinstance(got, float):
            if want is None or got is None:
                assert got == want, f"{field}: 得到 {got}，期望 {want}"
            else:
                assert got == pytest.approx(want, rel=1e-12), f"{field}: 得到 {got}，期望 {want}"
        else:
            assert got == want, f"{field}: 得到 {got}，期望 {want}"


# ---------------------------------------------------------------- 闸门不变量
def test_most_strict_gate_wins():
    """禁用 > IFRA > QRA2：高浓度时 IFRA 红必须压过 QRA2 绿。"""
    r = _run_gate(("d-Limonene", 5, "healthy", 4.0, False))
    assert r["qra2Level"] == "low" and r["ifraLevel"] == "high"
    assert r["level"] == "high" and r["dominantGate"] == "IFRA 闸门"

    r2 = _run_gate(("Citral", 5, "healthy", 0.6, False))
    assert r2["qra2Level"] == "high" and r2["ifraLevel"] == "high"  # 双红
    assert r2["level"] == "high"


def test_banned_overrides_everything():
    r = _run_gate(("Lilial", 0.01, "pregnant", None, True))
    assert r["level"] == "high" and r["dominantGate"] == "禁用闸门"
    assert r["bannedLevel"] == "high"


def test_data_insufficient_is_never_green():
    """数据不足 ≠ 安全：无 NESIL 或库中无此成分都不得判绿。"""
    assert _run_gate(("乙酸苄酯", 5, "healthy", None, False))["level"] == "mid"
    assert _run_gate(("UnknownXYZ", 5, "healthy", None, False))["level"] == "mid"


def test_clean_ingredient_under_limit_is_green():
    """反向守卫：不该把所有东西都判成非绿。"""
    assert _run_gate(("d-Limonene", 5, "healthy", None, False))["level"] == "low"
    assert _run_gate(("Eugenol", 0.3, "healthy", 0.5, False))["level"] == "low"


# ---------------------------------------------------------------- 黄灯可达性
def test_yellow_reachability_is_bounded_by_tpop():
    """固化黄灯窗口的数学条件（设计后果，不是缺陷；防止被误当 bug 改掉）。

    判据（见 docs/IMPROVEMENT_PLAN.md P0-3）：
        红 = AEL / P99 < 1
        黄 = AEL / CEL[policy] / T_pop < 1（在非红前提下）

    CEL 分布固定（LHS + 固定种子），故 P99/P90 是与浓度无关的常数
    （实测 1.8816760416503429，两引擎一致；两者同分布线性缩放）。由此：

      - P90-policy 且 T_pop=1（healthy）：黄需 P90 > AEL 且 P99 <= AEL，
        而 P99/P90 = 1.88 > 1 ⟹ AEL < P90 < P99 <= AEL 自相矛盾 ⟹ **不可达**
      - P99-policy 且 T_pop=1（pregnant / anosmic）：黄判据与红判据同式 ⟹ **不可达**
      - P99-policy 且 T_pop>1（sensitive 3.0 / rhinitis 1.2）：窗口 A < P99 <= A×T_pop
        ⟹ **可达**，且 T_pop 越大窗口越宽
    故 QRA2 这条路径的黄灯只对 sensitive / rhinitis 可达；
    另两条黄灯路径（IFRA 八成上限、数据不足）对全人群可用。
    """
    # 1) P99/P90 与浓度无关（固定种子下为常数）
    ratios = []
    for conc in (1.0, 5.0, 20.0, 80.0):
        s = sample_cel(conc, seed=SEED)
        ratios.append(s["p99"] / s["p90"])
    assert max(ratios) - min(ratios) < 1e-9, "P99/P90 应恒定"
    ratio = ratios[0]
    assert ratio == pytest.approx(1.8816760416503429, rel=1e-9)
    assert ratio > 1.0, "P99 > P90 恒成立 → P90-policy 且 T_pop=1 的黄灯窗口为空"

    # 2) T_pop=1 的人群：黄判据与红判据重合（P99 policy）或窗口为空（P90 policy）
    for pop in ("healthy", "pregnant", "anosmic"):
        cfg = POP_POLICY[pop]
        assert cfg["alpha"] * cfg["beta"] == 1.0
    assert POP_POLICY["healthy"]["policy"] == "P90"
    assert POP_POLICY["pregnant"]["policy"] == POP_POLICY["anosmic"]["policy"] == "P99"

    # 3) sensitive / rhinitis 的黄灯窗口非空
    for pop in ("sensitive", "rhinitis"):
        assert POP_POLICY[pop]["policy"] == "P99"
        assert POP_POLICY[pop]["alpha"] > 1.0, f"{pop} 需 T_pop>1 才有黄灯窗口"

    # 实证：20% 柠檬烯健康绿、敏感肌黄
    assert _run_gate(("d-Limonene", 20, "healthy", None, False))["level"] == "low"
    assert _run_gate(("d-Limonene", 20, "sensitive", None, False))["level"] == "mid"


def test_population_divergence_on_same_input():
    """同一输入，人群必须产生分歧（否则「人群差异化」是空话）。"""
    levels = {p: _run_gate(("d-Limonene", 20, p, None, False))["level"]
              for p in ("healthy", "sensitive", "pregnant", "rhinitis", "anosmic")}
    assert levels["healthy"] == "low"
    assert levels["sensitive"] == "mid", f"敏感肌应出黄灯，实得 {levels['sensitive']}"
    assert len(set(levels.values())) > 1, "人群结论不应完全一致"


# ---------------------------------------------------------------- 氧化
OXID_LEVEL = {"低": "low", "中": "mid", "高": "high"}
OXID_CASES = [
    # (months, env, D, 中文 label)
    (0, "cool", 0.0, "低"), (1, "cool", 0.029230930687343948, "低"),
    (3, "cool", 0.08515442642554805, "低"), (6, "cool", 0.16305757651123198, "低"),
    (12, "cool", 0.29952737976474764, "中"), (14, "cool", 0.3398797960404235, "中"),
    (24, "cool", 0.50933810830076, "高"), (36, "cool", 0.6563047790718477, "高"),
    (0, "room", 0.0, "低"), (1, "room", 0.06706523481954119, "低"),
    (3, "room", 0.18800410966738734, "低"), (6, "room", 0.3406626740829476, "中"),
    (12, "room", 0.5652742906525507, "高"), (14, "room", 0.6216289685123071, "高"),
    (24, "room", 0.811013557632357, "高"), (36, "room", 0.9178427347846756, "高"),
    (0, "hot", 0.0, "低"), (1, "hot", 0.1588758432495493, "低"),
    (3, "hot", 0.4049131989744501, "中"), (6, "hot", 0.6458716992451776, "高"),
    (12, "hot", 0.874593146604502, "高"), (14, "hot", 0.911275924469795, "高"),
    (24, "hot", 0.98427312112144, "高"), (36, "hot", 0.9980277416061076, "高"),
]


@pytest.mark.parametrize("months,env,expected_d,label", OXID_CASES,
                         ids=[f"{m}m-{e}" for m, e, _, _ in OXID_CASES])
def test_oxidation_matches_ts(months: float, env: str, expected_d: float, label: str):
    """24 项氧化值（8 时间点 × 3 储存环境）与 TS 引擎一致，含分级标签。"""
    d = compute_d(months, env)
    assert d == pytest.approx(expected_d, abs=1e-12)
    level = "low" if d < 0.2 else ("mid" if d < 0.5 else "high")
    assert level == OXID_LEVEL[label]


def test_oxidation_monotonic_and_bounded():
    """单调性：时间递增 D 递增且 < 1；环境严苛度 阴凉 < 室温 < 高温。"""
    for env in ("cool", "room", "hot"):
        prev = -1.0
        for m in range(0, 49, 3):
            d = compute_d(m, env)
            assert d > prev and d < 1.0, f"{env} {m}月"
            prev = d
    for m in (1, 3, 14, 36):
        assert compute_d(m, "cool") < compute_d(m, "room") < compute_d(m, "hot")


def test_oxidation_thresholds():
    """阈值 0.2 / 0.5 三档边界。"""
    assert compute_d(0, "cool") < 0.2
    assert compute_d(6, "hot") > 0.5
    assert compute_d(36, "cool") > 0.5
