"""API 端到端测试（mock 模式：无 DashScope Key 也能全链路跑通）。"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.ingredient.repository import get_repository, init_repository
from app.core.config import get_settings


@pytest.fixture(scope="module")
def client():
    init_repository(get_settings().data_dir)  # 独立于其他 fixture 初始化全局 repo
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "ok"
    assert body["meta"]["engine"] == "qra2@1.0.0"
    assert "vision" in body["meta"]["models"]


def test_products_and_ingredients(client):
    r = client.get("/api/v1/products", params={"limit": 30})
    assert r.status_code == 200 and len(r.json()["data"]["items"]) >= 20
    r2 = client.get("/api/v1/ingredients", params={"q": "柠檬烯"})
    assert r2.json()["data"]["items"][0]["inci"] == "d-Limonene"


def test_analyze_golden_healthy_green(client):
    r = client.post("/api/v1/analyze", json={"product": {"product_id": "golden-limonene"},
                                             "profile": "healthy"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["product"]["is_golden"] is True
    assert d["risk"]["overall_level"] == "green"
    ing = d["risk"]["ingredients"][0]
    assert ing["evidence_level"] == "documented"
    assert ing["margin_p90"] > 1  # AEL=100 / CEL_P90≈9.7 → 余量>10
    assert d["vision"]["families"][0]["key"] == "citrus"
    assert d["vision"]["synesthesia_text"]  # 模板兜底也必有文案
    assert r.json()["meta"]["request_id"]


def test_analyze_sensitive_high_conc_red(client):
    # 真实产品走通条码通道 + 敏感肌 P99 策略 + 氧化 + 模式联动；
    # 红灯路径用确定性的高浓度手动成分验证（18% 柠檬烯，margin99 = 100/49.8/3 < 1）
    r = client.post("/api/v1/analyze", json={"product": {"barcode": "0000000000001"},
                                             "profile": "sensitive",
                                             "oxidation": {"opened_days": 30}})
    d = r.json()["data"]
    assert d["recognition_channel"] == "barcode"
    assert d["risk"]["population"]["percentile_policy"] == "P99"
    assert d["risk"]["oxidation"]["applicable"] is True
    assert d["vision"]["mode"] == "sensitive"

    r2 = client.post("/api/v1/analyze", json={
        "product": {"manual_ingredients": {"d-Limonene": 18.0}},
        "profile": "sensitive"})
    assert r2.json()["data"]["risk"]["overall_level"] == "red"


def test_analyze_real_product_with_v2_concentrations(client):
    """队友 v2 香水库：浓度值为对象 {typical_pct,...}，含 11 种真实致敏原——引擎须可解析。"""
    r = client.post("/api/v1/analyze", json={"product": {"product_id": "lancome-la-vie-est-belle-edp"},
                                             "profile": "sensitive"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert len(d["risk"]["ingredients"]) == 11
    assert all(f["concentration_pct"] is not None for f in d["risk"]["ingredients"])


def test_analyze_pregnant_no_banned_in_clean_product(client):
    r = client.post("/api/v1/analyze", json={"product": {"query": "Sailing Day"},
                                             "profile": "pregnant"})
    d = r.json()["data"]
    # Sailing Day 配方不含禁用成分 → 不应出现孕期禁用红旗
    assert not any("孕期禁用" in f for f in d["risk"]["population"]["special_flags"])


def test_analyze_pregnant_real_lilial_red(client):
    """真实老配方（YSL L'Homme 含 Lilial，欧盟 2022 禁用）→ 孕期红灯。"""
    r = client.post("/api/v1/analyze", json={"product": {"product_id": "ysl-lhomme-edt"},
                                             "profile": "pregnant"})
    d = r.json()["data"]
    assert d["risk"]["overall_level"] == "red"
    assert any("孕期禁用" in f for f in d["risk"]["population"]["special_flags"])
    lilial = next(f for f in d["risk"]["ingredients"] if f["inci"] == "Butylphenyl Methylpropional")
    assert lilial["gate"] == "banned"


def test_analyze_manual_ingredients(client):
    r = client.post("/api/v1/analyze", json={
        "product": {"manual_ingredients": {"d-Limonene": 6.0, "神秘成分XYZ": 1.0}},
        "profile": "healthy"})
    d = r.json()["data"]
    assert d["recognition_channel"] == "manual"
    assert "神秘成分XYZ" in d["risk"]["data_insufficient"]


def test_analyze_co_use_aggregate(client):
    base = client.post("/api/v1/analyze", json={"product": {"product_id": "golden-limonene"}}).json()
    agg = client.post("/api/v1/analyze", json={"product": {"product_id": "golden-limonene"},
                                               "co_use": {"body_lotion": 1.0}}).json()
    b = base["data"]["risk"]["ingredients"][0]["cel_p90"]
    a = agg["data"]["risk"]["ingredients"][0]["cel_p90"]
    assert a == pytest.approx(1.8 * b, abs=0.01)


def test_analyze_product_not_found_envelope(client):
    r = client.post("/api/v1/analyze", json={"product": {"query": "不存在的香水XYZQQ"}})
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "PRODUCT_NOT_FOUND" and "手动" in err["message"]
    assert r.json()["meta"]["request_id"]


def test_recognition_image_endpoint_mock(client):
    r = client.post("/api/v1/recognition/image",
                    files={"file": ("bottle.jpg", b"fake-bytes", "image/jpeg")})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["needs_manual"] is True
    assert "mock" in d["message"] or "降级" in d["message"]


def test_admin_import_and_stats(client):
    repo = get_repository()
    original = repo.allergens
    try:
        r = client.post("/api/v1/admin/ingredients/import",
                        json={"items": original[:5]})  # 热更新：只保留前5条
        assert r.status_code == 200
        assert get_repository().stats()["allergens"] == 5
        stats = client.get("/api/v1/admin/stats").json()["data"]
        assert stats["allergens"] == 5
    finally:
        repo.reload_allergens(original)  # 恢复，避免影响其他测试
    assert get_repository().stats()["allergens"] == len(original)
