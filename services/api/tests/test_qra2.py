"""QRA2 黄金算例（v3 §1.1.1 点估计 + 策划案V1 §3.1.1 概率化）。

文档口径：
- 点估计：柠檬烯 5%、m=0.5、A=100、f=2、η=1 → CEL=5.0；NESIL=10000、SAF=100 → AEL=100；比值=20 绿灯。
- 概率化：文档示例 P50=4.1 / P90=8.7 / P99=13.2（AEL=10 时 P99 比值 0.76 → 红灯）。
  注：文档三处分位数自身不满足同一对数正态（P90→σ=0.587，P99→σ=0.502），
  为示意值。本引擎按文档规定的分布族实现，P50 复现误差<20%，且保留决策结论（红灯）。
"""
import numpy as np
import pytest

from app.modules.qra2.distributions import CelSampler, ExposureSpecs, point_estimate_cel
from app.modules.qra2.engine import IngRef, QRA2Engine
from app.modules.qra2.oxidation import compute_oxidation
from app.schemas.api import EvidenceLevel, OxidationInput, PopulationKey, RiskLevel

LIMONENE = {"inci": "d-Limonene", "name_zh": "柠檬烯", "nesil": 10000.0,
            "nesil_source": "documented", "oxidation_prone": True, "k_ox_per_day": 0.03,
            "tier": "medium", "families": ["citrus"], "banned_eu": False, "reproductive_flag": False}


def _sampler(engine) -> CelSampler:
    return engine.sampler


# —— 闸门基线：QRA1 点估计（必须精确复现文档算例） ——
def test_point_estimate_golden_case():
    cel = point_estimate_cel(5.0)
    assert cel == pytest.approx(5.0, rel=1e-6)
    ael = 10000.0 / 100.0
    assert ael / cel == pytest.approx(20.0, rel=1e-6)


# —— 概率化：分布抽样 ——
def test_probabilistic_quantiles_match_doc_within_tolerance(engine):
    cel = _sampler(engine).sample(10000, engine.cfg["simulation"]["seed"], 5.0)
    q = CelSampler.quantiles(cel)
    # 文档 P50=4.1/P90=8.7/P99=13.2 为示意值（自身不满足同一分布）；
    # 引擎按文档分布族实现：P99 误差<15%（决策分位线），P50/P90 宽容差但保序。
    assert q["P50"] == pytest.approx(4.1, rel=0.25), f"P50={q['P50']}"
    assert q["P90"] == pytest.approx(8.7, rel=0.25), f"P90={q['P90']}"
    assert q["P99"] == pytest.approx(13.2, rel=0.15), f"P99={q['P99']}"
    assert q["P50"] < q["P90"] < q["P99"]


def test_sampling_deterministic_with_fixed_seed(engine):
    s = engine.cfg["simulation"]
    a = CelSampler.quantiles(_sampler(engine).sample(s["n_iterations"], s["seed"], 5.0))
    b = CelSampler.quantiles(_sampler(engine).sample(s["n_iterations"], s["seed"], 5.0))
    assert a == b  # 固定种子可复算（策划案V1 要求）


def test_concentration_scales_cel_linearly(engine):
    s = engine.cfg["simulation"]
    q5 = CelSampler.quantiles(_sampler(engine).sample(s["n_iterations"], s["seed"], 5.0))
    q10 = CelSampler.quantiles(_sampler(engine).sample(s["n_iterations"], s["seed"], 10.0))
    assert q10["P90"] == pytest.approx(2 * q5["P90"], rel=1e-6)


# —— 引擎判定 ——
def test_healthy_limonene_5pct_green_documented(engine):
    report = engine.assess([IngRef((LIMONENE, 5.0, "d-Limonene"))], PopulationKey.healthy,
                           OxidationInput(), {})
    f = report.ingredients[0]
    assert f.level is RiskLevel.green
    assert f.evidence_level is EvidenceLevel.documented
    assert f.decision_percentile == "P90"
    assert f.nesil == 10000.0 and f.saf == 100.0


def test_low_ael_tail_risk_red(engine):
    """策划案V1 决策增量算例：AEL=10 时 P99 比值<1 → 红灯（看见被平均掉的1%）。"""
    rec = dict(LIMONENE, nesil=1000.0)  # SAF=100 → AEL=10
    report = engine.assess([IngRef((rec, 5.0, "d-Limonene"))], PopulationKey.healthy,
                           OxidationInput(), {})
    f = report.ingredients[0]
    assert f.margin_p99 < 1.0
    assert f.level is RiskLevel.red and f.gate == "qra2"
    assert report.overall_level is RiskLevel.red


def test_sensitive_population_uses_p99_and_stricter_threshold(engine):
    high_conc = IngRef((LIMONENE, 18.0, "d-Limonene"))  # 高浓度柑橘（柠檬烯可达 15-20%）
    linalool = {"inci": "Linalool", "name_zh": "芳樟醇", "nesil": 1000.0,
                "nesil_source": "demo_estimate", "oxidation_prone": False, "tier": "strong",
                "families": ["floral"]}
    report = engine.assess([high_conc, IngRef((linalool, 1.0, "Linalool"))],
                           PopulationKey.sensitive, OxidationInput(), {})
    f = report.ingredients[0]
    assert f.decision_percentile == "P99"
    assert report.population.threshold_multiplier == pytest.approx(3.0)  # α=2.0 × β=1.5
    assert f.level is RiskLevel.red
    assert any("交叉反应" in flag for flag in report.population.special_flags)  # 强致敏原芳樟醇触发


def test_pregnant_reproductive_ban(engine):
    lilial = {"inci": "Butylphenyl Methylpropional", "name_zh": "铃兰醛", "nesil": 1000.0,
              "nesil_source": "demo_estimate", "reproductive_flag": True, "banned_eu": True,
              "oxidation_prone": False, "tier": "low", "families": ["floral"]}
    report = engine.assess([IngRef((lilial, 0.1, "Lilial"))], PopulationKey.pregnant,
                           OxidationInput(), {})
    f = report.ingredients[0]
    assert f.level is RiskLevel.red and f.gate == "banned"
    assert any("孕期禁用" in flag for flag in report.population.special_flags)


def test_demo_estimate_penalty_applied(engine):
    linalool = {"inci": "Linalool", "name_zh": "芳樟醇", "nesil": 1000.0,
                "nesil_source": "demo_estimate", "oxidation_prone": True, "k_ox_per_day": 0.0175,
                "tier": "strong", "families": ["floral"]}
    report = engine.assess([IngRef((linalool, 1.0, "Linalool"))], PopulationKey.healthy,
                           OxidationInput(), {})
    f = report.ingredients[0]
    assert f.saf == pytest.approx(300.0)  # 100 × 演示估计惩罚3
    assert f.evidence_level is EvidenceLevel.indicative
    assert "保守惩罚" in (f.data_note or "")


def test_ifra_gate_takes_stricter(engine):
    rec = dict(LIMONENE, ifra_limit_pct=4.0)  # 浓度 5% ≥ 限值 4%
    report = engine.assess([IngRef((rec, 5.0, "d-Limonene"))], PopulationKey.healthy,
                           OxidationInput(), {})
    f = report.ingredients[0]
    assert f.level is RiskLevel.red and f.gate == "ifra"


def test_unknown_ingredient_marked_insufficient_not_silent(engine):
    report = engine.assess([IngRef((None, 2.0, "神秘新成分 XYZ"))], PopulationKey.healthy,
                           OxidationInput(), {})
    assert "神秘新成分 XYZ" in report.data_insufficient
    assert report.ingredients[0].evidence_level is EvidenceLevel.insufficient
    assert "数据不足" in (report.ingredients[0].data_note or "")


def test_aggregate_exposure_amplifies(engine):
    s = engine.cfg["simulation"]
    base = engine.assess([IngRef((LIMONENE, 5.0, "d-Limonene"))], PopulationKey.healthy,
                         OxidationInput(), {})
    agg = engine.assess([IngRef((LIMONENE, 5.0, "d-Limonene"))], PopulationKey.healthy,
                        OxidationInput(), {"body_lotion": 1.0})  # w=0.8 → ×1.8
    b, a = base.ingredients[0], agg.ingredients[0]
    assert a.cel_p90 == pytest.approx(1.8 * b.cel_p90, abs=0.01)  # 存库值有 4 位小数舍入
    assert any("聚合暴露" in flag for flag in agg.population.special_flags)


# —— 氧化模型（v3 §1.1.2） ——
def test_oxidation_levels(engine):
    cfg = engine.cfg
    d_low, lv_low = compute_oxidation(0.03, OxidationInput(opened_days=7, light=0.0), cfg)
    d_high, lv_high = compute_oxidation(0.03, OxidationInput(opened_days=60, temp_c=35, light=0.8), cfg)
    assert d_low == pytest.approx(1 - np.exp(-0.21), rel=1e-6) and lv_low is RiskLevel.green
    assert d_high > 0.5 and lv_high is RiskLevel.red


def test_oxidation_in_report_with_anosmic_emphasis(engine):
    report = engine.assess([IngRef((LIMONENE, 5.0, "d-Limonene"))], PopulationKey.anosmic,
                           OxidationInput(opened_days=90), {})
    assert report.oxidation.applicable and "柠檬烯" in report.oxidation.substances
    assert report.oxidation.level is RiskLevel.red
    assert "失嗅" in (report.oxidation.advice or "")
