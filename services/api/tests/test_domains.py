"""数据域匹配 / 可视化域 / 识别域 单元测试。"""
import pytest

from app.modules.scentmap.service import (
    ScentmapService,
    infer_family_from_name,
    synesthesia_template,
)
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


# —— 回归：金字塔两种数据形状（历史 bug：str 形状整体抛错并被静默兜底） ——
def test_pyramid_accepts_both_str_and_dict_notes(repo):
    svc = ScentmapService(repo.families)
    # 真实香水库的形状：字符串数组
    pyr_str = svc._pyramid({"pyramid": {"top": ["Lavender", "Bergamot"]}}, repo, "woody")
    assert [n.name for n in pyr_str["top"]] == ["Lavender", "Bergamot"]
    assert all(n.weight == 1.0 for n in pyr_str["top"])
    assert pyr_str["top"][0].family == "fougere"
    assert pyr_str["top"][1].family == "citrus"
    # 金标算例的形状：对象数组（显式 weight / name）
    pyr_obj = svc._pyramid(
        {"pyramid": {"top": [{"name": "柠檬烯", "weight": 0.6}, {"name": "柑橘皮", "weight": 0.4}]}},
        repo, "woody")
    assert [n.weight for n in pyr_obj["top"]] == [0.6, 0.4]
    assert pyr_obj["top"][0].family == "citrus"


def test_pyramid_tolerates_malformed_notes(repo):
    """空串 / 未知类型 / 非数字 weight 都不应抛错，只跳过或降级为默认。"""
    svc = ScentmapService(repo.families)
    out = svc._pyramid({"pyramid": {"top": ["", "  ", 123, None, {"name": "Rose", "weight": "x"}]}},
                       repo, "woody")
    assert [n.name for n in out["top"]] == ["Rose"]
    assert out["top"][0].weight == 1.0
    assert out["top"][0].family == "floral"


# —— 回归：英文音符的香调推断（真实香水库音符全为英文） ——
@pytest.mark.parametrize("note,expected", [
    ("Lavender", "fougere"),
    ("Rose", "floral"),
    ("Orange Blossom", "floral"),   # 长词优先，不能被 orange 判成 citrus
    ("Bergamot", "citrus"),
    ("Vetiver", "woody"),
    ("Madagascar Vanilla", "gourmand"),
    ("Sea Notes", "aquatic"),
    ("Pink Pepper", "oriental"),
    ("Oakmoss", "fougere"),
    ("Cedar", "woody"),
])
def test_english_note_family_inference(note, expected):
    assert infer_family_from_name(note) == expected


def test_family_inference_falls_back_to_none_when_unknown():
    assert infer_family_from_name("Zzz Unknown Note") is None
    assert infer_family_from_name("") is None
    assert infer_family_from_name(None) is None


# —— 回归：通感文案在缺维度时不得拼出病句 ——
def test_synesthesia_template_no_broken_sentence_when_pyramid_empty(repo):
    svc = ScentmapService(repo.families)
    product = repo.find_perfume(product_id="golden-limonene")
    vision = svc.build_vision(product, repo, VisionMode.normal)
    vision.pyramid = {}   # 模拟手动输入：无金字塔
    text = synesthesia_template(vision, "B", "N")
    assert "为主的" in text          # 香调来自 families，仍应成立
    assert "——，" not in text        # 不得出现空图层导致的破折号悬挂
    assert "，。" not in text        # 不得出现空分句
    assert "以**" not in text
    assert text.endswith("。")



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
