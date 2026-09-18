"""QRA2 风险评估引擎（三闸门 Take-the-Most-Strict）。

闸门1 QRA2 概率化模型（AEL/CEL_P90 或 P99）—— 前瞻定量预测，覆盖无临床数据成分；
闸门2 临床激发阈值（LOEL/NOEL）—— 真实人体数据兜底；
闸门3 IFRA 强制限量 —— 合规硬约束。
最终风险等级 = 三闸门输出中的最严等级；任一闸门缺失时以 evidence_level 诚实呈现。

人群差异化（v3 §1.1.3）：判定余量 margin = AEL/CEL 需 ≥ T_pop = α×β；
分位线策略（策划案V1）：健康成人 P90，敏感肌/孕妇/失嗅/鼻炎自动升至 P99。
"""
from __future__ import annotations

from typing import Protocol

from app.modules.qra2.distributions import CelSampler, ExposureSpecs, point_estimate_cel
from app.modules.qra2.oxidation import compute_oxidation, oxidation_advice
from app.schemas.api import (
    EvidenceLevel,
    IngredientFinding,
    OxidationFinding,
    OxidationInput,
    PopulationFinding,
    PopulationKey,
    RiskLevel,
    RiskReport,
)

_SEVERITY = {RiskLevel.green: 0, RiskLevel.yellow: 1, RiskLevel.red: 2}
_GATE_PRIORITY = {"banned": 0, "ifra": 1, "clinical": 2, "qra2": 3}


def _margin(ael: float, cel_q: float, t_pop: float) -> float:
    """余量 = AEL / CEL分位 / T_pop；CEL=0（未检出/零暴露）时余量为无穷（安全）。"""
    return ael / cel_q / t_pop if cel_q > 0 else float("inf")


def _round_margin(m: float) -> float | None:
    return None if m == float("inf") else round(m, 4)  # Infinity 非法 JSON，输出 null


class IngRef(tuple):
    """(成分记录 dict | None, 浓度%, 原始输入名)。record 为 None 表示库中无此成分。"""


class RiskEngine(Protocol):
    """引擎协议：后续 QRA2 精细化/换引擎只需新增实现并配置切换（后台可升级）。"""

    def assess(self, ingredients: list[IngRef], profile: PopulationKey,
               oxidation: OxidationInput, co_use: dict[str, float]) -> RiskReport: ...


def strictest(levels: list[tuple[RiskLevel, str]]) -> tuple[RiskLevel, str]:
    best_level, best_gate = RiskLevel.green, "qra2"
    for lv, gate in levels:
        if _SEVERITY[lv] > _SEVERITY[best_level] or (
                _SEVERITY[lv] == _SEVERITY[best_level] and _GATE_PRIORITY[gate] < _GATE_PRIORITY[best_gate]):
            best_level, best_gate = lv, gate
    return best_level, best_gate


class QRA2Engine:
    """简化版 IFRA QRA 2.0：概率化 CEL + 聚合暴露 + 分位数判定 + 三闸门。"""

    def __init__(self, config: dict):
        self.cfg = config
        self.specs = ExposureSpecs.from_config(config)
        self.sampler = CelSampler(self.specs)

    # —— 单成分评估 ——
    def assess_ingredient(self, rec: dict, conc_pct: float, profile: PopulationKey,
                          agg_factor: float, force_reproductive: bool) -> IngredientFinding:
        pop_cfg = self.cfg["populations"][profile.value]
        policy = self.cfg["percentile_policy"][profile.value]
        t_pop = float(pop_cfg["alpha"]) * float(pop_cfg["beta"])

        saf = float(self.cfg["saf"]["default_leave_on"])
        evidence = EvidenceLevel.insufficient
        if rec.get("nesil") is None:
            return IngredientFinding(
                inci=rec.get("inci", ""), name_zh=rec.get("name_zh", rec.get("inci", "")),
                cas=rec.get("cas"), concentration_pct=conc_pct, tier=rec.get("tier"),
                banned_eu=bool(rec.get("banned_eu")), note=rec.get("note"),
                evidence_level=EvidenceLevel.insufficient,
                data_note="致敏原数据库暂缺该成分的 NESIL/限量数据，已显式标注「数据不足」",
            )
        if rec.get("nesil_source") == "documented":
            evidence = EvidenceLevel.documented
        else:
            saf *= float(self.cfg["saf"]["demo_estimate_penalty"])
            evidence = EvidenceLevel.indicative

        ael = float(rec["nesil"]) / saf

        n = int(self.cfg["simulation"]["n_iterations"])
        seed = int(self.cfg["simulation"]["seed"])
        cel = self.sampler.sample(n, seed, conc_pct) * agg_factor
        q = self.sampler.quantiles(cel)

        m50 = _margin(ael, q["P50"], t_pop)
        m90 = _margin(ael, q["P90"], t_pop)
        m99 = _margin(ael, q["P99"], t_pop)

        # 闸门1：QRA2 分位判定（红=极端尾部 / 黄=约10%超标 / 绿=安全）
        if m99 < 1.0:
            g1 = (RiskLevel.red, "qra2")
        elif m90 < 1.0:
            g1 = (RiskLevel.yellow, "qra2")
        else:
            g1 = (RiskLevel.green, "qra2")
        gates: list[tuple[RiskLevel, str]] = [g1]

        # 闸门2：临床激发阈值（v2 数据的 human_noel 为 RIFM 人体 CNIH NOEL）
        noel = rec.get("clinical_noel") or rec.get("human_noel")
        if noel is not None and q["P90"] > 0:
            noel = float(noel)
            if noel / q["P99"] < 1.0:
                gates.append((RiskLevel.red, "clinical"))
            elif noel / q["P90"] < 1.0:
                gates.append((RiskLevel.yellow, "clinical"))

        # 闸门3：IFRA 限量
        if rec.get("ifra_limit_pct") is not None:
            limit = float(rec["ifra_limit_pct"])
            near = self.cfg["ifra_gate"]["near_limit_factor"] * limit
            if conc_pct >= limit:
                gates.append((RiskLevel.red, "ifra"))
            elif conc_pct >= near:
                gates.append((RiskLevel.yellow, "ifra"))

        # 欧盟禁用 / 生殖毒性（孕妇强制）
        if rec.get("banned_eu") or force_reproductive:
            gates.append((RiskLevel.red, "banned"))

        level, gate = strictest(gates)

        notes: list[str] = []
        if evidence == EvidenceLevel.indicative:
            notes.append("NESIL 为演示估计值，引擎已叠加 ×3 保守惩罚")
        if level == RiskLevel.yellow:
            notes.append("约10%高用量消费者暴露超标：建议减半用量/隔日使用")
        if level == RiskLevel.green and g1[0] == RiskLevel.green and m90 < 1.5:
            notes.append("接近阈值：建议控制单次用量")

        return IngredientFinding(
            inci=rec.get("inci", ""), name_zh=rec.get("name_zh", ""),
            cas=rec.get("cas"), concentration_pct=conc_pct,
            tier=rec.get("tier"), high_frequency=bool(rec.get("high_frequency")),
            banned_eu=bool(rec.get("banned_eu")),
            oxidation_prone=bool(rec.get("oxidation_prone")), note=rec.get("note"),
            nesil=float(rec["nesil"]), saf=saf, ael=round(ael, 4),
            cel_p50=round(q["P50"], 4), cel_p90=round(q["P90"], 4), cel_p99=round(q["P99"], 4),
            margin_p50=_round_margin(m50), margin_p90=_round_margin(m90), margin_p99=_round_margin(m99),
            decision_percentile=policy, level=level, gate=gate,
            evidence_level=evidence,
            data_note="；".join(notes) or None,
        )

    # —— 整体评估 ——
    def assess(self, ingredients: list[IngRef], profile: PopulationKey,
               oxidation: OxidationInput, co_use: dict[str, float]) -> RiskReport:
        pop_cfg = self.cfg["populations"][profile.value]
        policy = self.cfg["percentile_policy"][profile.value]
        agg_factor = self._aggregate_factor(co_use)

        findings: list[IngredientFinding] = []
        insufficient: list[str] = []
        for rec, conc, raw_name in ingredients:
            if rec is None:
                insufficient.append(raw_name)
                findings.append(IngredientFinding(
                    inci=raw_name, name_zh=raw_name, concentration_pct=conc,
                    evidence_level=EvidenceLevel.insufficient,
                    data_note="成分库未收录（可能是小众/新成分），已显式标注「数据不足」",
                ))
                continue
            force_rp = profile == PopulationKey.pregnant and bool(rec.get("reproductive_flag"))
            f = self.assess_ingredient(rec, conc, profile, agg_factor, force_rp)
            if f.evidence_level == EvidenceLevel.insufficient and f.nesil is None:
                insufficient.append(f.inci)
            findings.append(f)

        overall, _ = strictest([(f.level or RiskLevel.yellow, f.gate or "qra2") for f in findings]) \
            if findings else (RiskLevel.green, "qra2")

        # 氧化动态评估（取氧化敏感成分的最大 D）
        ox_recs = [r for r, _, _ in ingredients if r and r.get("oxidation_prone") and r.get("k_ox_per_day")]
        if ox_recs:
            results = [compute_oxidation(float(r["k_ox_per_day"]), oxidation, self.cfg) for r in ox_recs]
            d, lv = max(results, key=lambda x: x[0])
            emphasized = bool(pop_cfg.get("oxidation_emphasis"))
            ox_finding = OxidationFinding(
                applicable=True,
                substances=[f"{r.get('name_zh', r.get('inci'))}" for r in ox_recs],
                d_value=round(d, 4), level=lv,
                advice=oxidation_advice(lv, emphasized),
            )
        else:
            ox_finding = OxidationFinding(applicable=False)

        # 人群专属提示
        flags: list[str] = []
        strong_hits = [f.name_zh for f in findings if f.tier == "strong"]
        if pop_cfg.get("cross_reaction_check") and strong_hits:
            flags.append(f"敏感肌交叉反应检查：含强致敏原 {('、'.join(strong_hits[:3]))} 等")
        if pop_cfg.get("reproductive_check"):
            repro = [f.name_zh for f in findings if f.banned_eu]
            if repro:
                flags.append(f"孕期禁用成分检查：{('、'.join(repro))}（欧盟已禁用，直接红灯）")
        if pop_cfg.get("respiratory_flag") and any(f.oxidation_prone for f in findings):
            flags.append("呼吸道提示：含高挥发性成分，鼻炎人群建议通风环境使用")
        if pop_cfg.get("oxidation_emphasis") and ox_finding.applicable:
            flags.append("失嗅人群：氧化变质预警已增强（嗅觉替代通道）")
        if agg_factor > 1.0:
            flags.append(f"聚合暴露（QRA2）：共使用产品使总暴露放大 ×{agg_factor:.2f}")

        summary = self._summary(overall, findings, insufficient, profile)

        return RiskReport(
            overall_level=overall,
            ingredients=findings,
            data_insufficient=sorted(set(insufficient)),
            oxidation=ox_finding,
            population=PopulationFinding(
                population=profile,
                threshold_multiplier=round(float(pop_cfg["alpha"]) * float(pop_cfg["beta"]), 4),
                percentile_policy=policy,
                special_flags=flags,
            ),
            summary=summary,
        )

    def _aggregate_factor(self, co_use: dict[str, float]) -> float:
        """CEL_total = Σ(CEL×w) 的简化实现：主产品 CEL × (1 + Σ w_type·ratio_type)。"""
        weights = self.cfg["aggregate_exposure"]["products"]
        return 1.0 + sum(float(weights.get(pt, 0.5)) * float(ratio) for pt, ratio in co_use.items())

    @staticmethod
    def _summary(overall: RiskLevel, findings: list[IngredientFinding],
                 insufficient: list[str], profile: PopulationKey) -> str:
        zh = {"green": "绿灯：典型与高用量消费者的暴露均低于安全线", 
              "yellow": "黄灯：约10%高用量消费者暴露超标，建议减量使用",
              "red": "红灯：存在极端暴露尾部风险或合规问题，建议避免使用"}[overall.value]
        n_by_level = {lv.value: sum(1 for f in findings if f.level and f.level.value == lv.value)
                      for lv in RiskLevel}
        s = f"综合判定【{overall.value.upper()}】——{zh}。逐成分：红{n_by_level['red']}/黄{n_by_level['yellow']}/绿{n_by_level['green']}；"
        if insufficient:
            s += f"另有 {len(insufficient)} 项数据不足成分已显式标注；"
        s += f"人群策略：{profile.value}。"
        return s


__all__ = ["QRA2Engine", "RiskEngine", "IngRef", "point_estimate_cel", "strictest"]
