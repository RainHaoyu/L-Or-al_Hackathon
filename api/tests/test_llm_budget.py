"""LLM 预算与前端超时的跨语言不变式（待办 1-2）。

背景：失嗅模式的通感文案长约 3 倍、耗时也约 3 倍（实测 7.7–9.6 s），
而前端超时曾写死 15 s、后端每档超时 5 s —— 结果失嗅模式**必然**拿不到 AI 文案，
只能落规则模板（而它看起来"有长文案"，其实是前端本地拼的）。

本文件锁住三件事：
  1. 预算按模式区分，且 anosmia > normal / sensitive；
  2. 两档模型**共享**一个总预算：第一档耗尽预算后不再重来一遍（否则总耗时翻倍）；
  3. 前端 `ANALYZE_TIMEOUT` > 引擎固定开销 + 后端预算（直接读 web/src/lib/api.ts 断言）。

引擎固定开销的实测：关掉 Key 走规则模板时 `/analyze` 仍需 4445–5037 ms，
与云端无关，是 QRA2 蒙特卡洛本身的成本，所以前端预算必须「引擎 + LLM」相加。
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx
import pytest

from app import data as D
from app.modules import llm

API_TS = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "api.ts"


# --------------------------------------------------------------- 测试替身
class _Resp:
    """最小 httpx.Response 替身：只用到 raise_for_status 与 json。"""

    def __init__(self, text: str) -> None:
        self._text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._text}}]}


@pytest.fixture()
def perfume() -> dict:
    return D.PERFUMES[0]


@pytest.fixture()
def fake_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key-not-real")


# --------------------------------------------------------------- 1. 预算本身
def test_budget_covers_all_three_modes() -> None:
    assert set(llm._BUDGET) == {"normal", "sensitive", "anosmia"}
    assert all(v > 0 for v in llm._BUDGET.values())


def test_anosmia_budget_is_larger() -> None:
    """失嗅模式输出长约 3 倍、耗时也约 3 倍，预算必须更大，否则必然落模板。"""
    assert llm._BUDGET["anosmia"] > llm._BUDGET["normal"]
    assert llm._BUDGET["anosmia"] > llm._BUDGET["sensitive"]


def test_no_key_means_no_request(monkeypatch: pytest.MonkeyPatch, perfume: dict) -> None:
    """没有 Key 时不许碰网络，直接模板。"""
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    def boom(*_a, **_kw):
        raise AssertionError("没有 Key 时不应发起请求")

    monkeypatch.setattr(llm.httpx, "post", boom)
    text, model, is_llm = llm.synthesize(perfume, "normal")
    assert model == "template" and is_llm is False and text


# --------------------------------------------------------------- 2. 预算共享
def test_tiers_share_one_budget(monkeypatch: pytest.MonkeyPatch, fake_key: None, perfume: dict) -> None:
    """第一档把预算耗尽后，不得再对第二档重来一遍（否则最坏耗时翻倍、超过前端超时）。"""
    monkeypatch.setitem(llm._BUDGET, "normal", 0.5)
    timeouts: list[float] = []

    def slow_post(_url, **kw):
        timeouts.append(kw["timeout"])
        time.sleep(kw["timeout"])  # 模拟 httpx 按 timeout 抛错
        raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr(llm.httpx, "post", slow_post)
    t0 = time.monotonic()
    text, model, is_llm = llm.synthesize(perfume, "normal")
    elapsed = time.monotonic() - t0

    assert model == "template" and is_llm is False and text
    assert len(timeouts) == 1, f"预算耗尽后不应再尝试下一档，实际尝试了 {len(timeouts)} 档"
    assert elapsed < 0.5 + llm._MIN_ATTEMPT + 0.5, f"总耗时 {elapsed:.2f}s 未被预算封顶"


def test_second_tier_tried_when_first_fails_fast(
    monkeypatch: pytest.MonkeyPatch, fake_key: None, perfume: dict
) -> None:
    """第一档快速失败（额度/网络）时仍有预算，必须继续尝试第二档。"""
    monkeypatch.setitem(llm._BUDGET, "normal", 2.0)
    models: list[str] = []

    def flaky_post(_url, **kw):
        models.append(kw["json"]["model"])
        if len(models) == 1:
            raise httpx.ConnectError("simulated connect error")
        return _Resp("真实文案")

    monkeypatch.setattr(llm.httpx, "post", flaky_post)
    text, model, is_llm = llm.synthesize(perfume, "normal")

    assert models == ["qwen-max", "qwen-plus"]
    assert (text, model, is_llm) == ("真实文案", "qwen-plus", True)


def test_per_request_timeout_never_exceeds_budget(
    monkeypatch: pytest.MonkeyPatch, fake_key: None, perfume: dict
) -> None:
    """传给 httpx 的 timeout 是**剩余**预算，任何一档都不得超过总预算。"""
    monkeypatch.setitem(llm._BUDGET, "normal", 1.0)
    timeouts: list[float] = []

    def spy_post(_url, **kw):
        timeouts.append(kw["timeout"])
        raise httpx.ConnectError("fast fail")

    monkeypatch.setattr(llm.httpx, "post", spy_post)
    llm.synthesize(perfume, "normal")

    assert timeouts, "应该至少尝试一次"
    assert all(t <= 1.0 + 1e-6 for t in timeouts), timeouts
    assert timeouts[0] <= 1.0 + 1e-6


# --------------------------------------------------------------- 3. 跨语言不变式
def _frontend_numbers() -> tuple[dict[str, int], int]:
    """从 web/src/lib/api.ts 读出各模式前端超时与引擎开销常量。"""
    src = API_TS.read_text("utf-8")
    block = re.search(r"ANALYZE_TIMEOUT[^{]*\{(.*?)\}", src, re.S)
    assert block, "api.ts 里找不到 ANALYZE_TIMEOUT"
    fe = {
        m.group(1): int(m.group(2).replace("_", ""))
        for m in re.finditer(r"(\w+):\s*([\d_]+)", block.group(1))
    }
    engine = re.search(r"ENGINE_BUDGET_MS\s*=\s*([\d_]+)", src)
    assert engine, "api.ts 里找不到 ENGINE_BUDGET_MS"
    return fe, int(engine.group(1).replace("_", ""))


def test_frontend_timeout_exceeds_engine_plus_budget() -> None:
    fe, engine_ms = _frontend_numbers()
    assert set(fe) == set(llm._BUDGET), f"前端模式集合 {set(fe)} 与后端预算 {set(llm._BUDGET)} 不一致"
    for mode, budget in llm._BUDGET.items():
        need = engine_ms + budget * 1000
        assert fe[mode] > need, (
            f"{mode}: 前端超时 {fe[mode]} ms 不足以覆盖 引擎 {engine_ms} ms + 后端预算 {budget}s"
            f"（需要 > {need:.0f} ms）——否则后端还在算、前端已回退模板"
        )
