"""验证「测试默认不碰外网」这层防护真的生效（待办 1-3）。

只写 fixture 不算数：下次有人把 autouse 删掉、或改用 `httpx.Client`，
这里会直接失败。所以本文件测的是**防护本身**。
"""

from __future__ import annotations

import os

import httpx
import pytest

from app.modules import analyzer


def test_api_key_is_removed_inside_tests() -> None:
    """开发机上设了 DASHSCOPE_API_KEY 也不能漏进测试进程。"""
    assert not os.environ.get("DASHSCOPE_API_KEY"), "测试进程里不该有百炼 Key"


def test_external_http_post_is_blocked(guard_log: list[str]) -> None:
    """守卫必须真的拦住外部请求（不是只删 Key）。"""
    try:
        with pytest.raises(RuntimeError, match="禁止访问外网"):
            httpx.post("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        assert guard_log == [
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        ], "守卫应记录被拦截的 URL"
    finally:
        # 这次调用是上面刻意触发的，不要留给 session 级兜底断言
        guard_log.clear()


def test_analyze_falls_back_to_template() -> None:
    """离线时 /analyze 仍要有结果：走规则模板，且不标记为 LLM。"""
    out = analyzer.analyze(
        {"product_id": "eau-sauvage", "population": "anosmic", "opened_months": 6,
         "storage": "room", "mode": "anosmia"}
    )
    syn = out["data"]["synesthesia"]
    assert syn["model"] == "template"
    assert syn["isLlm"] is False
    assert syn["text"], "模板文案不应为空"
    # 失嗅模式的模板本来就比 normal 长（含前中后三调铺陈）
    assert out["meta"]["models"]["synesthesia"] == "template"
