"""CEL 概率分布与拉丁超立方抽样（QRA2 核心①②）。

将传统 QRA 的 CEL 五参数标量升级为概率分布（策划案V1 §3.1.1 / IFRA QRA 2.0 思路）：
    CEL = c(浓度%) × m(单次用量密度) × A(涂抹面积) × f(日频率) × η(吸收/驻留因子)

抽样采用拉丁超立方（LHS）以稳定尾部估计，固定随机种子保证可复算。
单位沿用文档算例口径：μg/cm²/day。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats

EPS = 1e-9


@dataclass(frozen=True)
class ExposureSpecs:
    m_median: float
    m_cv: float
    area_min: float
    area_mode: float
    area_max: float
    freq_values: tuple[float, ...]
    freq_probs: tuple[float, ...]
    conc_rel_lo: float
    conc_rel_hi: float
    eta_alpha: float
    eta_beta: float

    @classmethod
    def from_config(cls, cfg: dict) -> "ExposureSpecs":
        d = cfg["exposure_distributions"]
        return cls(
            m_median=d["amount_density_m"]["median"],
            m_cv=d["amount_density_m"]["cv"],
            area_min=d["application_area_A"]["min"],
            area_mode=d["application_area_A"]["mode"],
            area_max=d["application_area_A"]["max"],
            freq_values=tuple(float(v) for v in d["daily_frequency_f"]["values"]),
            freq_probs=tuple(float(p) for p in d["daily_frequency_f"]["probs"]),
            conc_rel_lo=d["concentration_c"]["lo"],
            conc_rel_hi=d["concentration_c"]["hi"],
            eta_alpha=d["retention_eta"]["alpha"],
            eta_beta=d["retention_eta"]["beta_param"],
        )


def point_estimate_cel(concentration_pct: float, *, m: float = 0.5, area: float = 100.0,
                       freq: float = 2.0, eta: float = 1.0) -> float:
    """传统 QRA 点估计（v3 §1.1.1 算例：5%×0.5×100×2×1.0 = 5.0）。"""
    return concentration_pct / 100.0 * m * area * freq * eta


class CelSampler:
    """对单一成分抽取 CEL 的蒙特卡洛样本（N=10000 量级，毫秒级）。"""

    def __init__(self, specs: ExposureSpecs):
        self.s = specs
        self._sigma_ln = float(np.sqrt(np.log1p(specs.m_cv ** 2)))
        c_rel = (specs.area_mode - specs.area_min) / (specs.area_max - specs.area_min)
        self._triang_c = c_rel
        self._freq_cum = np.cumsum(specs.freq_probs)

    def sample(self, n: int, seed: int, concentration_pct: float) -> np.ndarray:
        """返回长度 n 的 CEL 样本（μg/cm²/day）。"""
        u = np.clip(stats.qmc.LatinHypercube(d=5, seed=seed).random(n), EPS, 1 - EPS)
        u_m, u_a, u_f, u_c, u_e = u.T

        m = self.s.m_median * np.exp(self._sigma_ln * stats.norm.ppf(u_m))
        area = stats.triang.ppf(u_a, self._triang_c, loc=self.s.area_min,
                                scale=self.s.area_max - self.s.area_min)
        freq = np.interp(u_f, self._freq_cum, self.s.freq_values)
        conc = concentration_pct / 100.0 * (self.s.conc_rel_lo
                                            + u_c * (self.s.conc_rel_hi - self.s.conc_rel_lo))
        eta = stats.beta.ppf(u_e, self.s.eta_alpha, self.s.eta_beta)

        return conc * m * area * freq * eta

    @staticmethod
    def quantiles(cel: np.ndarray) -> dict[str, float]:
        """提取 P50/P90/P99（QRA2 判定分位线）。"""
        p50, p90, p99 = np.percentile(cel, [50, 90, 99])
        return {"P50": float(p50), "P90": float(p90), "P99": float(p99)}
