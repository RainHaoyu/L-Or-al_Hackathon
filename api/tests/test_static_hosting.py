"""前端静态托管 + SPA 回退（交付形态 / 手机演示的关键路径）。

背景：交付要"一个进程、一个端口、手机能开"。这要求后端把预构建的 `web/dist`
和 `/api/v1` 一起端出来（同源，无跨域），并且：
  - 客户端路由（/report、/vision）刷新不能 404 → 回退 index.html；
  - **未知的 `/api/...` 必须返回 JSON 404**，不能被回退成 HTML——
    否则前端会把 200 HTML 当 JSON 解析，错误变得难以定位；
  - 路径穿越不能被读到 dist 之外；
  - 前端没构建时给出可执行的 503 提示，而不是 500。

用 `AURA_WEB_DIST` 指向临时目录，所以这些用例不依赖仓库里是否构建过 dist。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture()
def dist(tmp_path, monkeypatch):
    d = tmp_path / "dist"
    (d / "assets").mkdir(parents=True)
    (d / "index.html").write_text("<!doctype html><div id=root>SPA-INDEX</div>", "utf-8")
    (d / "assets" / "app.js").write_text("console.log('bundle')", "utf-8")
    (tmp_path / "secret.txt").write_text("TOP-SECRET", "utf-8")  # dist 之外，不许被读到
    monkeypatch.setenv("AURA_WEB_DIST", str(d))
    return d


def test_index_served(dist) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "SPA-INDEX" in r.text
    assert r.headers["content-type"].startswith("text/html")


def test_client_route_falls_back_to_index(dist) -> None:
    """/report 这类客户端路由刷新时必须回退 index.html（否则手机刷新就 404）。"""
    for route in ("/report", "/vision", "/some/deep/client/route"):
        r = client.get(route)
        assert r.status_code == 200, route
        assert "SPA-INDEX" in r.text, route


def test_static_asset_served(dist) -> None:
    r = client.get("/assets/app.js")
    assert r.status_code == 200
    assert "console.log" in r.text


def test_unknown_api_returns_json_404(dist) -> None:
    """未知 /api 路径不能被 SPA 回退吞掉。"""
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["error"]["code"] == "not_found"


def test_real_api_not_shadowed_by_fallback(dist) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ok"


def test_path_traversal_blocked(dist) -> None:
    """`..` 不能读到 dist 之外，只能落到 index.html。"""
    r = client.get("/%2e%2e/secret.txt")
    assert r.status_code == 200
    assert "TOP-SECRET" not in r.text
    assert "SPA-INDEX" in r.text


def test_missing_dist_gives_actionable_503(tmp_path, monkeypatch) -> None:
    """没构建前端时给出可照做的提示（而不是 500 或空白页）。"""
    monkeypatch.setenv("AURA_WEB_DIST", str(tmp_path / "not-built"))
    for route in ("/", "/report"):
        r = client.get(route)
        assert r.status_code == 503, route
        assert r.json()["error"]["code"] == "web_dist_missing"
        assert "npm run build" in r.json()["error"]["message"]
