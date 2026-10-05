"""氧化产物动态风险评估（v3 §1.1.2）。

柠檬烯/芳樟醇等前半抗原自氧化生成强致敏氢过氧化物；失嗅者无法依赖气味
off-note 预警变质，本模块为其提供嗅觉替代预警。

    k_eff = k_ox · Q10^((T - T_ref)/10) · (1 + L)
    D     = 1 - exp(-k_eff · t)

D<0.2 低（正常使用）；0.2≤D<0.5 中（敏感肌/孕妇减少使用）；D≥0.5 高（建议不再使用）。
"""
from __future__ import annotations

from app.schemas.api import OxidationInput, RiskLevel

LEVEL_ADVICE = {
    RiskLevel.green: "氧化程度低，可正常使用",
    RiskLevel.yellow: "氧化程度中等：敏感肌/孕妇建议减少使用，并避光阴凉储存",
    RiskLevel.red: "氧化程度高：萜烯类成分可能已生成致敏性过氧化物，建议不再使用",
}


def compute_oxidation(k_ox: float, ox: OxidationInput, cfg: dict) -> tuple[float, RiskLevel]:
    oc = cfg["oxidation"]
    k_eff = (k_ox
             * oc["q10"] ** ((ox.temp_c - oc["temp_ref_c"]) / 10.0)
             * (1.0 + min(ox.light, oc["light_factor_max"])))
    d = 1.0 - pow(2.718281828459045, -k_eff * max(ox.opened_days, 0.0))
    th = oc["thresholds"]
    if d < th["low"]:
        return d, RiskLevel.green
    if d < th["high"]:
        return d, RiskLevel.yellow
    return d, RiskLevel.red


def oxidation_advice(level: RiskLevel, emphasized: bool) -> str:
    base = LEVEL_ADVICE[level]
    if emphasized and level != RiskLevel.green:
        return "【失嗅人群专属提醒】您无法通过气味察觉变质，请特别关注：" + base
    return base
