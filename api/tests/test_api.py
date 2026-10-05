"""阶段 4/5 后端验收：黄金算例引擎对齐 / 人群分化 / mock 确定性 / 置信度降级 / 错误隔离 / 信封"""
from fastapi.testclient import TestClient

from app.main import app
from app.modules import qra2

client = TestClient(app)


def test_health_envelope():
    r = client.get("/api/v1/health").json()
    assert r["data"]["status"] == "ok"
    assert r["data"]["perfumes"] == 13 and r["data"]["ifra_banned"] == 9  # 12 真实 + 黄金算例
    assert r["meta"]["engine"].startswith("aura-qra2/")


def test_products_search():
    r = client.get("/api/v1/products", params={"q": "真我"}).json()
    assert r["data"] and r["data"][0]["id"] == "j-adore" or any(p["name"] == "真我" for p in r["data"])


def test_recognition_mock_deterministic_and_confirm():
    a = client.post("/api/v1/recognition/image", json={"image": "abc123", "filename": "bottle.jpg"}).json()
    b = client.post("/api/v1/recognition/image", json={"image": "abc123", "filename": "bottle.jpg"}).json()
    assert a["data"]["product"] == b["data"]["product"]  # 哈希确定性
    assert a["data"]["confidence"] < 0.7                  # 低于阈值
    assert a["data"]["status"] == "confirm" and a["data"]["candidates"]  # 转人工确认 + 候选
    assert a["data"]["provider"] == "mock"


def test_barcode_deterministic():
    r = client.post("/api/v1/recognition/barcode", json={"code": "361427333"}).json()
    assert r["data"]["status"] == "ok" and r["data"]["product"]["id"]


def test_analyze_golden_case_parity():
    r = client.post("/api/v1/analyze", json={"product_id": "golden-case", "population": "healthy"}).json()
    d = r["data"]
    assert d["verdict"]["level"] == "low"
    p = d["panel"]
    assert p["ael"] == 100.0                       # NESIL 10000 / SAF 100
    assert p["marginPoint"] == 20.0                # 100 / 5.0（黄金算例逐位对齐 TS 引擎）
    assert p["p50"] < p["p90"] < p["p99"]
    assert r["meta"]["seed"] == qra2.SEED


def test_seed_reproducibility_backend():
    a = qra2.sample_cel(5)
    b = qra2.sample_cel(5)
    assert a == b


def test_population_divergence_backend():
    h = client.post("/api/v1/analyze", json={"product_id": "eau-sauvage", "population": "healthy",
                                             "opened_months": 0, "storage": "cool"}).json()
    s = client.post("/api/v1/analyze", json={"product_id": "eau-sauvage", "population": "sensitive",
                                             "opened_months": 14, "storage": "room"}).json()
    assert h["data"]["verdict"]["level"] == "low"
    assert s["data"]["verdict"]["level"] != "low"
    assert any("氧化" in x for x in s["data"]["verdict"]["reasons"])


def test_qra2_divergence_unit():
    healthy = qra2.analyze_ingredient("d-Limonene", 20, "healthy")
    sensitive = qra2.analyze_ingredient("d-Limonene", 20, "sensitive")
    assert healthy["level"] == "low" and sensitive["level"] != "low"


def test_vision_error_isolation(monkeypatch):
    """可视化构建失败 → degraded 上报，预警结论不受影响（阶段 5 错误隔离）"""
    import app.modules.analyzer as az

    def boom(_perfume):
        raise RuntimeError("injected")

    monkeypatch.setattr(az, "build_visual_spec", boom)
    r = client.post("/api/v1/analyze", json={"product_id": "j-adore", "population": "healthy"}).json()
    assert r["data"]["verdict"]["level"] in ("low", "mid", "high")   # 预警仍在
    assert r["data"]["vision"]["degraded"] is True
    assert "injected" in r["meta"]["degraded"]["reason"]


def test_llm_fallback_template_without_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)  # 显式无 Key，三级兜底落模板
    r = client.post("/api/v1/analyze", json={"product_id": "j-adore", "population": "healthy"}).json()
    assert r["data"]["synesthesia"]["model"] == "template"           # 无 Key → 模板兜底
    assert r["data"]["synesthesia"]["text"]


def test_unknown_product_reported_in_meta():
    r = client.post("/api/v1/analyze", json={"product_id": "nope"}).json()
    assert r["data"] is None and "未知香水" in r["meta"]["error"]


def test_ige_integration_rhinitis():
    """IgE 数据层整合：一千零一夜（含安息香/乳香/没药）×鼻炎 → 速发理由 + IgE 行"""
    r = client.post("/api/v1/analyze", json={"product_id": "shalimar", "population": "rhinitis"}).json()
    assert any("IgE" in x for x in r["data"]["verdict"]["reasons"])
    ige_rows = [x for x in r["data"]["ingredients"] if x["gate"] == "IgE Ⅰ 型速发"]
    assert ige_rows and "安息香" in "、".join(x["zh"] for x in ige_rows)


def test_health_counts_new_layers():
    r = client.get("/api/v1/health").json()["data"]
    assert r["eu26"] == 26 and r["ige"] == 10 and r["materials"] >= 140
