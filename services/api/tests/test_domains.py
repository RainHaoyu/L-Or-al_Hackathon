"""数据域匹配 / 可视化域 / 识别域 单元测试。"""
import pytest

from app.modules.scentmap.service import ScentmapService, synesthesia_template
from app.schemas.api import PopulationKey, VisionMode


# —— ingredient 匹配 ——
def test_find_allergen_exact_and_alias(repo):
    assert repo.find_allergen("d-Limonene")["cas"] == "5989-27-5"
    assert repo.find_allergen("柠檬烯")["inci"] == "d-Limonene"
    assert repo.find_allergen("Lilial")["inci"] == "Butylphenyl Methylpropional"
    assert repo.find_allergen("5989-27-5")["inci"] == "d-Limonene"
    assert repo.find_allergen("不存在成分阿巴阿巴") is None


def test_find_allergen_fuzzy(repo):
    assert repo.find_allergen("limonen")["inci"] == "d-Limonene"
    assert repo.find_allergen("Linalool ")["inci"] == "Linalool"


def test_perfume_lookup(repo):
    p = repo.find_perfume(barcode="0000000000001")
    assert p and p["id"] == "golden-limonene" and p["is_golden"] is True
    p2 = repo.find_perfume(query="Black Opium")
    assert p2 and p2["id"] == "ysl-black-opium-edp"
    assert repo.search_products("Yves")  # 品牌命中


def test_banned_flags(repo):
    hicc = repo.find_allergen("Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde")
    assert hicc["banned_eu"] and not hicc["reproductive_flag"]  # HICC：致敏禁用，非生殖毒性
    lilial = repo.find_allergen("Butylphenyl Methylpropional")
    assert lilial["banned_eu"] and lilial["reproductive_flag"]  # Lilial：欧盟 2022 禁用（生殖毒性）


# —— scentmap ——
def test_vision_golden_product(repo):
    svc = ScentmapService(repo.families)
    product = repo.find_perfume(product_id="golden-limonene")
    v = svc.build_vision(product, repo, VisionMode.normal)
    assert v.families[0]["key"] == "citrus" and v.families[0]["weight"] == 1.0
    assert v.palette[0] == "#FFE066"  # 柑橘主色
    assert v.motion["type"] == "sparkle"
    assert v.radar["fresh"] == pytest.approx(0.95)
    assert set(v.pyramid.keys()) == {"top", "heart", "base"}


def test_vision_radar_fallback_from_priors(repo):
    svc = ScentmapService(repo.families)
    v = svc.build_vision({"families": {"woody": 0.5, "citrus": 0.5}, "radar": None, "pyramid": {}},
                         repo, VisionMode.normal)
    assert v.radar["lasting"] == pytest.approx((0.9 + 0.2) / 2, abs=0.01)
    assert v.families[0]["key"] in ("citrus", "woody")


def test_synesthesia_template_modes(repo):
    svc = ScentmapService(repo.families)
    product = repo.find_perfume(product_id="golden-limonene")
    v = svc.build_vision(product, repo, VisionMode.anosmic)
    text = synesthesia_template(v, "Golden Case", "柠檬烯标样")
    assert "失嗅模式" in text and "闻" not in text
    normal = synesthesia_template(svc.build_vision(product, repo, VisionMode.normal), "b", "n")
    assert "通感描述" in normal


def test_note_family_mapping(repo):
    svc = ScentmapService(repo.families)
    assert svc._pyramid({"pyramid": {"top": [{"name": "薰衣草", "weight": 1}]}}, repo, "floral")[
        "top"][0].family == "fougere"


# —— recognition ——
def test_recognition_channels(repo):
    from app.core.config import get_settings
    from app.modules.recognition.service import RecognitionService
    svc = RecognitionService(get_settings(), repo)

    bar = svc.by_barcode("0000000000001")
    assert bar.best and bar.best.product_id == "golden-limonene" and not bar.needs_manual

    miss = svc.by_barcode("9999999999")
    assert miss.needs_manual

    text = svc.by_text("Angel")
    assert text.best and text.best.product_id == "mugler-angel-edp"


def test_recognition_image_mock_fallback(repo):
    import asyncio

    from app.core.config import get_settings
    from app.modules.recognition.service import RecognitionService
    svc = RecognitionService(get_settings(), repo)
    result = asyncio.run(svc.by_image(b"fake-image-bytes-123"))
    # mock 通道 conf=0.62 < 0.7 → 触发手动确认降级（v3 置信度策略）
    assert result.needs_manual is True or (result.best and result.best.confidence >= 0.7)
    assert "降级" in result.message or "置信度" in result.message
