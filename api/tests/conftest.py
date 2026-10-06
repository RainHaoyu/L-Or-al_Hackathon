"""测试全局约定（api/tests）。

## 待办 1-3：测试默认不得访问外网

背景：`/analyze` 与 `/recognition/image` 会走到 `llm.synthesize` / `QwenVLProvider`，
两者都读进程环境变量 `DASHSCOPE_API_KEY`。开发机上只要设了这个变量，跑测试就会
**真的请求百炼**——实测 171 条从约 130 秒变成 511 秒，并且真实消耗额度、
结果依赖网络（换台机器/CI 上不可复现）。

两层防护：
  1. autouse fixture 删掉 `DASHSCOPE_API_KEY`，让代码走本地兜底分支；
  2. 同时把 `httpx.post` 换成守卫：一旦有人真的发起外部请求，
     既立刻抛错，也把 URL 记下来，session 结束时用断言报出来（不静默放过）。

需要真实联网的验证请显式打开：`AURA_ALLOW_LLM_TESTS=1 pytest tests/ -q`。

注意：只替换模块级 `httpx.post`（`llm.py` 与 `recognition.py` 用的就是它）。
**不要**去替换 `httpx.Client.request`——starlette 的 `TestClient` 继承自
`httpx.Client`，替换它会把整个测试客户端也一起打掉。
"""

from __future__ import annotations

import os

import httpx
import pytest

ALLOW_ENV = "AURA_ALLOW_LLM_TESTS"

# 守卫记录到的外部请求；正常情况下测试跑完应保持为空
EXTERNAL_CALLS: list[str] = []


def allow_network() -> bool:
    return os.environ.get(ALLOW_ENV) == "1"


def external_calls() -> list[str]:
    return list(EXTERNAL_CALLS)


def clear_external_calls() -> None:
    EXTERNAL_CALLS.clear()


@pytest.fixture()
def guard_log() -> list[str]:
    """把守卫的记录列表交给用例（可直接 clear）。

    tests/ 不是包，`import conftest` 会失败，所以用 fixture 暴露而不是 import。
    """
    return EXTERNAL_CALLS


@pytest.fixture(autouse=True)
def _offline_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """每条用例默认离线：删 Key + 拦截模块级 httpx.post。"""
    if allow_network():
        return
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    def guard_post(url, *args, **kwargs):
        EXTERNAL_CALLS.append(str(url))
        raise RuntimeError(f"测试禁止访问外网：{url}（确需联网请设 {ALLOW_ENV}=1）")

    monkeypatch.setattr(httpx, "post", guard_post)


@pytest.fixture(scope="session", autouse=True)
def _assert_no_external_calls():
    """兜底：整个 session 里出现过任何外部请求就报出来。"""
    clear_external_calls()
    yield
    calls = external_calls()
    assert not calls, f"测试期间发生了 {len(calls)} 次外部请求：{calls[:3]}"
