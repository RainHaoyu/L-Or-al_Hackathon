"""分布基元与双引擎对齐的数值回归测试。

背景：此前后端只有「保序」断言（p50<p90<p99），没有任何数值断言，
导致两个真实缺陷长期未被发现：
  1. normal_inv 中心分支漏了分母括号 → u∈(0.025,0.99) 共约 96% 的抽样区间
     返回值被压到 ≈1.0，用量（lognormal）抽样方差被抹平；
  2. _beta_inv_fast 用 2001 点查表插值近似 TS 侧的精确二分，
     使「双引擎逐位对齐」在抽样层面并不成立（相对偏差约 3.5e-5）。

本文件用 scipy 作为独立参照 + TS 引擎实测基准值，锁住这两条。
"""
from __future__ import annotations

import pytest

from app.modules.qra2 import normal_inv, point_cel, sample_cel

try:  # scipy 仅为增强校验，不是运行依赖；缺失时相关用例自动跳过
    from scipy import stats as _scipy_stats
except ImportError:  # pragma: no cover
    _scipy_stats = None

requires_scipy = pytest.mark.skipif(_scipy_stats is None, reason="scipy 未安装（可选增强校验）")

SEED = 20261005

# ---------------------------------------------------------------- 1. 分布基元
# 覆盖三个分支：左尾 (u<0.02425)、中心、右尾 (u>0.97575)
NORMAL_INV_CASES = [
    0.0001, 0.001, 0.01, 0.024, 0.02425, 0.05, 0.1, 0.25, 0.4, 0.5,
    0.6, 0.75, 0.9, 0.95, 0.975, 0.97575, 0.99, 0.999, 0.9999,
]

# 标准正态分位的权威参照值（由 0.5·erfc(-x/√2) 二分反演得到，回代 CDF 误差 ~1e-16）
NORMAL_INV_REFERENCE = {
    0.0001: -3.719016485455681,
    0.001: -3.090232306167814,
    0.01: -2.3263478740408416,
    0.024: -1.9773684281819466,
    0.02425: -1.9729610513118852,
    0.05: -1.6448536269514729,
    0.1: -1.2815515655446004,
    0.25: -0.6744897501960818,
    0.4: -0.2533471031357999,
    0.5: 0.0,
    0.6: 0.25334710313579967,
    0.75: 0.6744897501960816,
    0.9: 1.2815515655446008,
    0.95: 1.6448536269514715,
    0.975: 1.9599639845400545,
    0.97575: 1.9729610513118843,
    0.99: 2.326347874040837,
    0.999: 3.090232306167805,
    0.9999: 3.719016485455498,
}


@pytest.mark.parametrize("u", NORMAL_INV_CASES)
def test_normal_inv_matches_reference(u: float):
    """与标准正态分位权威值对照；Acklam 逼近官方精度 <1.15e-9。"""
    got = normal_inv(u)
    ref = NORMAL_INV_REFERENCE[u]
    assert got == pytest.approx(ref, abs=1e-8), f"u={u}: 得到 {got}，参照 {ref}"


@requires_scipy
@pytest.mark.parametrize("u", NORMAL_INV_CASES)
def test_normal_inv_matches_scipy(u: float):
    """scipy 可用时的独立交叉校验。"""
    assert normal_inv(u) == pytest.approx(float(_scipy_stats.norm.ppf(u)), abs=1e-8)


def test_normal_inv_center_branch_is_not_collapsed():
    """回归守卫：中心分支曾被括号 bug 压成恒 ≈1.0。

    这条断言专门锁死「96% 区间失真」这个缺陷——只要中心分支的输出
    不再随 u 单调变化、或落回 ≈1.0，就会失败。
    """
    xs = [normal_inv(u) for u in (0.1, 0.25, 0.5, 0.75, 0.9)]
    assert xs == pytest.approx([-1.2815515655, -0.6744897502, 0.0, 0.6744897502, 1.2815515655], abs=1e-8)
    assert xs == sorted(xs), "normal_inv 在中心分支必须严格单调递增"
    assert max(abs(x) for x in xs) > 1.0, "中心分支输出被压平（疑似括号 bug 回归）"


def test_normal_inv_symmetric():
    for u in (0.001, 0.1, 0.25, 0.4):
        assert normal_inv(u) == pytest.approx(-normal_inv(1 - u), abs=1e-12)


def test_normal_inv_matches_ts_engine_baseline():
    """与 web/src/lib/qra2/distributions.ts:normalInv 的实测值逐位一致。"""
    ts = {
        0.001: -3.090232304709404,
        0.025: -1.959963986120195,
        0.1: -1.2815515641401563,
        0.25: -0.6744897502234225,
        0.5: 0.0,
        0.75: 0.6744897502234225,
        0.9: 1.2815515641401563,
        0.975: 1.959963986120195,
        0.999: 3.090232304709404,
    }
    for u, expected in ts.items():
        assert normal_inv(u) == pytest.approx(expected, abs=1e-12), f"u={u}"


# ---------------------------------------------------------------- 2. 点估计锚点
def test_point_cel_anchor():
    """黄金算例：CEL = 0.05 × 0.5 × 100 × 2 × 1.0 = 5.0"""
    assert point_cel(5.0) == pytest.approx(5.0, abs=1e-12)
    assert point_cel(5.0, aggregate=1.25) == pytest.approx(6.25, abs=1e-12)


# ---------------------------------------------------------------- 3. 双引擎对齐
# 由 vitest 实跑 web/src/lib/qra2 得到（seed=20261005, n=10000）
TS_SAMPLE_BASELINE = {
    0.3: (0.22537173169564068, 0.5413149704720699, 1.0185794109239583),
    1.0: (0.7512391056521355, 1.8043832349068998, 3.39526470307986),
    5.0: (3.756195528260678, 9.0219161745345, 16.976323515399308),
    20.0: (15.024782113042711, 36.087664698138, 67.90529406159723),
}


@pytest.mark.parametrize("conc", sorted(TS_SAMPLE_BASELINE))
def test_sample_cel_matches_ts_engine(conc: float):
    """双引擎逐位对齐：同种子同输入，Python 分位数须与 TS 一致。

    此前 _beta_inv_fast 用查表插值近似，相对偏差约 3.5e-5，
    本断言（相对容差 1e-9）足以锁住该缺陷。
    """
    p50, p90, p99 = TS_SAMPLE_BASELINE[conc]
    s = sample_cel(conc, seed=SEED)
    assert s["p50"] == pytest.approx(p50, rel=1e-9), f"{conc}% p50"
    assert s["p90"] == pytest.approx(p90, rel=1e-9), f"{conc}% p90"
    assert s["p99"] == pytest.approx(p99, rel=1e-9), f"{conc}% p99"


def test_sample_cel_deterministic_and_ordered():
    a, b = sample_cel(5.0, seed=SEED), sample_cel(5.0, seed=SEED)
    assert a == b, "固定种子必须可复算"
    assert a["p50"] < a["p90"] < a["p99"]


def test_sample_cel_linear_in_concentration():
    a, b = sample_cel(5.0, seed=SEED), sample_cel(10.0, seed=SEED)
    assert b["p50"] == pytest.approx(2 * a["p50"], rel=1e-9)
    assert b["p99"] == pytest.approx(2 * a["p99"], rel=1e-9)


def test_sample_cel_amount_spread_is_not_collapsed():
    """回归守卫：normal_inv 失真的直接后果是「用量」抽样方差被抹平。

    用量 ~ LogNormal(median 0.5, CV 0.4)：P99/P50 应显著大于 1。
    若 normal_inv 再次损坏，该比值会塌缩到接近 1。
    """
    s = sample_cel(5.0, seed=SEED)
    spread = s["p99"] / s["p50"]
    assert spread > 3.0, f"分位离散度异常偏小（{spread:.3f}），疑似抽样方差被抹平"


def test_incomplete_beta_roundtrip():
    """Beta(20,2) 分位与正则不完全 Beta 互逆。"""
    from app.modules.qra2 import _beta_inv_fast, incomplete_beta

    for u in (0.05, 0.3, 0.5, 0.9, 0.99):
        x = _beta_inv_fast(u)
        assert incomplete_beta(20.0, 2.0, x) == pytest.approx(u, abs=1e-9)
