"""QRA2 引擎（Python 移植，与 aura/web TS 引擎同种子同结果：黄金算例/分位/闸门）"""

from __future__ import annotations

import math
from typing import Any

from .. import data as D

SEED = 20261005
N = 10000

POP_POLICY: dict[str, dict[str, Any]] = {
    "healthy": {"alpha": 1.0, "beta": 1.0, "policy": "P90"},
    "sensitive": {"alpha": 3.0, "beta": 1.0, "policy": "P99"},
    "pregnant": {"alpha": 1.0, "beta": 1.0, "policy": "P99"},
    "rhinitis": {"alpha": 1.2, "beta": 1.0, "policy": "P99"},
    "anosmic": {"alpha": 1.0, "beta": 1.0, "policy": "P99"},
}

STORAGE_ENV = {"cool": {"T": 15, "L": 0.0}, "room": {"T": 25, "L": 0.3}, "hot": {"T": 35, "L": 0.8}}
K25_TERPENE = 0.00178
Q10 = 1.8
T_REF = 25

_RANK = {"low": 0, "mid": 1, "high": 2}


# ---------------- 随机与分布基元 ----------------

def mulberry32(seed: int):
    a = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF))) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


_A = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239]
_B = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1]
_C = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783]
_Dd = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416]


def normal_inv(u: float) -> float:
    pl = 0.02425
    if u < pl:
        q = math.sqrt(-2 * math.log(u))
        return (((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (((( _Dd[0] * q + _Dd[1]) * q + _Dd[2]) * q + _Dd[3]) * q + 1)
    if u > 1 - pl:
        q = math.sqrt(-2 * math.log(1 - u))
        return -(((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]) / (((( _Dd[0] * q + _Dd[1]) * q + _Dd[2]) * q + _Dd[3]) * q + 1)
    q = u - 0.5
    r = q * q
    return (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5]) * q / ((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1


def _betacf(a: float, b: float, x: float) -> float:
    FPMIN = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.0
    d = 1 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1 / d
        dele = d * c
        h *= dele
        if abs(dele - 1) < 3e-12:
            break
    return h


def incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_bt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    bt = math.exp(ln_bt)
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1 - bt * _betacf(b, a, 1 - x) / b


def _beta_inv(u: float, a: float, b: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if incomplete_beta(a, b, mid) < u:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# Beta(20,2) 逆函数查表（启动期 2001 点，LHS 抽样 O(1) 插值）
_BETA_A, _BETA_B = 20.0, 2.0
_BETA_TABLE_N = 2000
_BETA_TABLE = [_beta_inv((i + 0.5) / (_BETA_TABLE_N + 1), _BETA_A, _BETA_B) for i in range(_BETA_TABLE_N + 1)]


def _beta_inv_fast(u: float) -> float:
    x = u * _BETA_TABLE_N
    i = int(x)
    if i >= _BETA_TABLE_N:
        return _BETA_TABLE[_BETA_TABLE_N]
    if i < 0:
        return _BETA_TABLE[0]
    frac = x - i
    return _BETA_TABLE[i] * (1 - frac) + _BETA_TABLE[i + 1] * frac


def _tri_inv(u: float, a: float, c: float, b: float) -> float:
    fc = (c - a) / (b - a)
    if u < fc:
        return a + math.sqrt(u * (c - a) * (b - a))
    return b - math.sqrt((1 - u) * (b - c) * (b - a))


def _permutation(n: int, rand) -> list[int]:
    arr = list(range(n))
    for i in range(n - 1, 0, -1):
        j = int(rand() * (i + 1))
        arr[i], arr[j] = arr[j], arr[i]
    return arr


# ---------------- CEL 概率化 ----------------

def point_cel(conc_pct: float, aggregate: float = 1.0) -> float:
    return conc_pct / 100 * 0.5 * 100 * 2 * 1.0 * aggregate


def sample_cel(conc_pct: float, n: int = N, seed: int = SEED, aggregate: float = 1.0) -> dict[str, float]:
    rand = mulberry32(seed)
    pa = _permutation(n, rand)
    pb = _permutation(n, rand)
    pf = _permutation(n, rand)
    pc = _permutation(n, rand)
    ps = _permutation(n, rand)
    sigma = math.sqrt(math.log(1 + 0.16))
    c0 = conc_pct / 100
    out = []
    for i in range(n):
        amount = 0.5 * math.exp(sigma * normal_inv((pa[i] + rand()) / n))
        area = _tri_inv((pb[i] + rand()) / n, 50, 100, 200)
        uf = (pf[i] + rand()) / n
        freq = 1 if uf < 0.5 else (2 if uf < 0.85 else 3)
        conc = c0 * 0.8 + 0.4 * c0 * ((pc[i] + rand()) / n)
        absorb = _beta_inv_fast((ps[i] + rand()) / n)
        out.append(conc * amount * area * freq * absorb * aggregate)
    out.sort()

    def pct(q: float) -> float:
        idx = (n - 1) * q
        lo, hi = int(math.floor(idx)), int(math.ceil(idx))
        if lo == hi:
            return out[lo]
        return out[lo] + (idx - lo) * (out[hi] - out[lo])

    return {"p50": pct(0.5), "p90": pct(0.9), "p99": pct(0.99)}


# ---------------- 氧化（Q10 模型） ----------------

def compute_d(months: float, env_key: str, k25: float = K25_TERPENE) -> float:
    env = STORAGE_ENV.get(env_key, STORAGE_ENV["room"])
    k_eff = k25 * (Q10 ** ((env["T"] - T_REF) / 10)) * (1 + env["L"])
    return 1 - math.exp(-k_eff * months * 30)


# ---------------- 单成分四闸门 ----------------

def analyze_ingredient(name: str, conc_pct: float | None, population: str,
                       ifra_limit_pct: float | None = None, banned: bool = False,
                       seed: int = SEED) -> dict[str, Any]:
    pop = POP_POLICY[population]
    tp = pop["alpha"] * pop["beta"]
    res: dict[str, Any] = {
        "matched": False, "zh": name, "ael": None, "aelEvidence": "insufficient",
        "pointCEL": None, "p50": None, "p90": None, "p99": None,
        "marginPoint": None, "marginP99": None, "marginPolicy": None,
        "tPop": tp, "policy": pop["policy"], "qra2Level": None, "qra2Reason": None,
        "ifraLevel": None, "ifraReason": None, "bannedLevel": None,
        "level": "mid", "dominantGate": "数据不足",
    }
    if banned:
        res.update(matched=True, bannedLevel="high", level="high", dominantGate="禁用闸门")
        return res
    tox = D.lookup_tox(name)
    if not tox:
        return res
    res["matched"] = True
    res["zh"] = tox["zh"]
    ael = None
    if tox["nesil"] is not None:
        ael = tox["nesil"] / D.SAF
        if tox["demo"]:
            ael /= D.DEMO_PENALTY
            res["aelEvidence"] = "indicative"
        else:
            res["aelEvidence"] = "documented"
    res["ael"] = ael

    if conc_pct is not None and ifra_limit_pct is not None and ifra_limit_pct > 0:
        if conc_pct >= ifra_limit_pct:
            res["ifraLevel"], res["ifraReason"] = "high", f"浓度 {conc_pct}% ≥ Cat4 上限 {ifra_limit_pct}%"
        elif conc_pct >= ifra_limit_pct * 0.8:
            res["ifraLevel"], res["ifraReason"] = "mid", f"浓度 {conc_pct}% 达到 Cat4 上限 {ifra_limit_pct}% 的八成以上"
        else:
            res["ifraLevel"], res["ifraReason"] = "low", f"浓度 {conc_pct}% 低于 Cat4 上限 {ifra_limit_pct}%"

    if ael is None or conc_pct is None:
        res["qra2Level"] = "mid"
        res["qra2Reason"] = "缺少浓度数据，按保守黄灯（数据不足 ≠ 安全）" if conc_pct is None else "缺少 NESIL 文献值，按保守黄灯"
        res["level"] = "high" if res["ifraLevel"] == "high" else "mid"
        res["dominantGate"] = "IFRA 闸门" if res["level"] == "high" else "数据不足"
        return res

    s = sample_cel(conc_pct, seed=seed)
    res["pointCEL"] = point_cel(conc_pct)
    res.update(p50=s["p50"], p90=s["p90"], p99=s["p99"])
    res["marginPoint"] = ael / res["pointCEL"]
    res["marginP99"] = ael / s["p99"]
    policy_cel = s["p90"] if pop["policy"] == "P90" else s["p99"]
    res["marginPolicy"] = ael / policy_cel / tp

    if res["marginP99"] < 1:
        res["qra2Level"] = "high"
        res["qra2Reason"] = f"P99 余量 {res['marginP99']:.2f} < 1（AEL {ael:.0f} / CEL_P99 {s['p99']:.1f}）"
    elif res["marginPolicy"] < 1:
        res["qra2Level"] = "mid"
        res["qra2Reason"] = f"{pop['policy']} × T_pop {tp:g} 判定线余量 {res['marginPolicy']:.2f} < 1"
    else:
        res["qra2Level"] = "low"
        res["qra2Reason"] = f"P99 余量 {res['marginP99']:.2f}，{pop['policy']} 判定线余量 {res['marginPolicy']:.2f}，安全"

    level, dominant = "low", "四道闸门均未触发"
    for lv, gate in [(res["ifraLevel"], "IFRA 闸门"), (res["qra2Level"], "QRA2 分位")]:
        if lv and _RANK[lv] > _RANK[level]:
            level, dominant = lv, gate
    res["level"], res["dominantGate"] = level, dominant
    return res
