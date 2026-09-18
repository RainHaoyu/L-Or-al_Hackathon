# -*- coding: utf-8 -*-
"""ingredients.json 构建：原料词典（气味可视化地基）

来源：
1) 《香水成分数据及过敏香料.docx》三级分类（天然 72 / 合成单体 76 / 功能辅料 10 类）
2) doevent/perfume 26K 数据集香材频率 top 名单（industry_commons.json）
3) families.json 的 7 家族视觉规则（原料→家族→色板/雷达先验）
每个原料：key（英文通用名/Fragrantica 香材名）、zh、category、families（可视化锚点）、
layer 倾向（top/heart/base）、inci（成分表匹配名，可空）。
"""
from __future__ import annotations

import json
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"

# (key, zh, category, families, layer, inci)
I = [
    # ---------------- 天然·花果类 ----------------
    ("Rose", "玫瑰", "natural_floral", ["floral"], "heart", "Rose Oil/Rose Extract"),
    ("Jasmine", "茉莉", "natural_floral", ["floral"], "heart", "Jasminum Officinale Oil"),
    ("Jasmine (Sambac)", "茉莉（沙巴克）", "natural_floral", ["floral"], "heart", None),
    ("Orange Blossom", "橙花", "natural_floral", ["floral", "citrus"], "heart", "Citrus Aurantium Amara Flower Oil"),
    ("Tuberose", "晚香玉", "natural_floral", ["floral", "oriental"], "heart", "Polianthes Tuberosa Extract"),
    ("Ylang-Ylang", "依兰依兰", "natural_floral", ["floral", "oriental"], "heart", "Cananga Odorata Flower Oil"),
    ("Iris", "鸢尾", "natural_floral", ["floral", "woody"], "heart", "Iris Pallida Root Extract"),
    ("Violet", "紫罗兰", "natural_floral", ["floral"], "heart", None),
    ("Lavender", "薰衣草", "natural_herbal", ["fougere"], "top", "Lavandula Angustifolia Oil"),
    ("Magnolia", "木兰", "natural_floral", ["floral"], "heart", None),
    ("Osmanthus", "桂花", "natural_floral", ["floral", "gourmand"], "heart", None),
    ("Narcissus", "水仙", "natural_floral", ["floral"], "heart", "Narcissus Poeticus Extract"),
    ("Geranium", "天竺葵", "natural_herbal", ["floral", "fougere"], "heart", "Pelargonium Graveolens Flower Oil"),
    ("Lily-of-the-Valley", "铃兰", "natural_floral", ["floral"], "heart", None),
    ("Freesia", "小苍兰", "natural_floral", ["floral"], "heart", None),
    ("Peony", "牡丹", "natural_floral", ["floral"], "heart", None),
    ("Carnation", "康乃馨", "natural_floral", ["floral", "oriental"], "heart", None),
    ("Chamomile", "洋甘菊", "natural_herbal", ["fougere"], "top", None),
    # ---------------- 天然·果类 ----------------
    ("Bergamot", "佛手柑", "natural_citrus", ["citrus"], "top", "Citrus Aurantium Bergamia Peel Oil"),
    ("Lemon", "柠檬", "natural_citrus", ["citrus"], "top", "Citrus Limon Peel Oil"),
    ("Mandarin", "橘子", "natural_citrus", ["citrus"], "top", "Citrus Aurantium Dulcis Peel Oil"),
    ("Orange", "甜橙", "natural_citrus", ["citrus"], "top", "Citrus Sinensis Peel Oil"),
    ("Grapefruit", "西柚", "natural_citrus", ["citrus"], "top", None),
    ("Lime", "青柠", "natural_citrus", ["citrus"], "top", None),
    ("Pear", "梨", "natural_fruit", ["floral", "citrus"], "top", None),
    ("Blackcurrant Bud", "黑加仑芽", "natural_fruit", ["citrus", "floral"], "top", None),
    ("Blackcurrant", "黑加仑", "natural_fruit", ["floral", "gourmand"], "top", None),
    ("Peach", "桃子", "natural_fruit", ["floral", "gourmand"], "heart", None),
    ("Apple", "苹果", "natural_fruit", ["floral", "gourmand"], "top", None),
    ("Raspberry", "树莓", "natural_fruit", ["gourmand"], "heart", None),
    ("Coconut", "椰子", "natural_fruit", ["gourmand"], "heart", None),
    ("Plum", "李子", "natural_fruit", ["gourmand"], "heart", None),
    ("Cherry", "樱桃", "natural_fruit", ["gourmand"], "top", None),
    # ---------------- 天然·木质类 ----------------
    ("Sandalwood", "檀香", "natural_woody", ["woody"], "base", "Santalum Album Oil"),
    ("Cedarwood", "雪松", "natural_woody", ["woody"], "base", "Juniperus Virginiana Oil"),
    ("Cedar", "雪松木", "natural_woody", ["woody"], "base", "Cedrus Atlantica Wood Oil"),
    ("Vetiver", "香根草", "natural_woody", ["woody"], "base", None),
    ("Patchouli", "广藿香", "natural_woody", ["woody", "oriental"], "base", "Pogostemon Cablin Oil"),
    ("Oud (Agarwood)", "沉香", "natural_woody", ["woody", "oriental"], "base", None),
    ("Guaiac Wood", "愈创木", "natural_woody", ["woody"], "base", None),
    ("Palo Santo", "圣木", "natural_woody", ["woody"], "base", None),
    ("Pine", "松木", "natural_woody", ["woody", "fougere"], "top", "Pinene"),
    ("Fir", "冷杉", "natural_woody", ["woody", "fougere"], "top", None),
    ("Cashmeran", "卡什米兰（绒木香）", "synthetic_woody", ["woody", "floral"], "base", None),
    # ---------------- 天然·树脂/香脂类 ----------------
    ("Frankincense", "乳香", "natural_resin", ["oriental", "woody"], "base", None),
    ("Myrrh", "没药", "natural_resin", ["oriental"], "base", None),
    ("Benzoin", "安息香", "natural_resin", ["oriental", "gourmand"], "base", None),
    ("Amber", "琥珀（龙涎香调）", "accord_amber", ["oriental", "woody"], "base", None),
    ("Labdanum", "岩玫瑰膏香", "natural_resin", ["oriental"], "base", None),
    ("Opoponax", "甜没药", "natural_resin", ["oriental"], "base", None),
    ("Elemi", "榄香脂", "natural_resin", ["woody", "citrus"], "top", None),
    ("Incense", "焚香", "natural_resin", ["oriental"], "heart", None),
    # ---------------- 天然·草叶/香料类 ----------------
    ("Mint", "薄荷", "natural_herbal", ["fougere", "citrus"], "top", "Mentha Piperita Oil"),
    ("Spearmint", "留兰香", "natural_herbal", ["fougere"], "top", "Mentha Viridis Leaf Oil"),
    ("Basil", "罗勒", "natural_herbal", ["fougere"], "top", None),
    ("Rosemary", "迷迭香", "natural_herbal", ["fougere"], "top", None),
    ("Sage", "鼠尾草", "natural_herbal", ["fougere"], "heart", None),
    ("Clary Sage", "快乐鼠尾草", "natural_herbal", ["fougere"], "heart", None),
    ("Thyme", "百里香", "natural_herbal", ["fougere"], "top", None),
    ("Coriander", "香菜籽", "natural_spice", ["citrus", "fougere"], "top", None),
    ("Cardamom", "小豆蔻", "natural_spice", ["oriental", "citrus"], "top", None),
    ("Cinnamon", "肉桂", "natural_spice", ["oriental"], "heart", "Cinnamomum Cassia Leaf Oil"),
    ("Clove", "丁香", "natural_spice", ["oriental"], "heart", "Eugenia Caryophyllus Bud Oil"),
    ("Pink Pepper", "粉红胡椒", "natural_spice", ["citrus", "floral"], "top", None),
    ("Pepper", "黑胡椒", "natural_spice", ["oriental", "fougere"], "top", None),
    ("Nutmeg", "肉豆蔻", "natural_spice", ["oriental"], "heart", None),
    ("Saffron", "藏红花", "natural_spice", ["oriental"], "heart", None),
    ("Ginger", "生姜", "natural_spice", ["citrus", "oriental"], "top", None),
    ("Juniper", "杜松", "natural_herbal", ["fougere", "citrus"], "top", None),
    ("Eucalyptus", "桉树", "natural_herbal", ["fougere"], "top", "Eucalyptus Globulus Leaf Oil"),
    ("Green Notes", "绿叶香", "natural_green", ["fougere", "aquatic"], "top", None),
    ("Fig Leaf", "无花果叶", "natural_green", ["woody", "aquatic"], "top", None),
    ("Tea", "茶香", "natural_green", ["fougere", "floral"], "top", None),
    ("Tobacco", "烟草", "natural_amber", ["gourmand", "woody"], "base", None),
    # ---------------- 天然·动物类（现均合成/植物替代） ----------------
    ("Musk", "麝香", "animalic_musk", ["woody", "oriental"], "base", None),
    ("White Musk", "白麝香", "synthetic_musk", ["woody", "floral"], "base", None),
    ("Civet", "灵猫香", "animalic", ["oriental"], "base", None),
    ("Castoreum", "海狸香", "animalic", ["oriental", "woody"], "base", None),
    ("Ambergris", "龙涎香", "animalic_amber", ["oriental", "woody"], "base", None),
    # ---------------- 美食调 ----------------
    ("Vanilla", "香草", "gourmand", ["gourmand", "oriental"], "base", "Vanillin"),
    ("Tonka Bean", "零陵香豆", "gourmand", ["gourmand", "woody"], "base", "Coumarin"),
    ("Praline", "果仁糖", "gourmand", ["gourmand"], "base", None),
    ("Caramel", "焦糖", "gourmand", ["gourmand"], "base", None),
    ("Chocolate", "巧克力", "gourmand", ["gourmand"], "base", None),
    ("Coffee", "咖啡", "gourmand", ["gourmand"], "top", None),
    ("Almond", "杏仁", "gourmand", ["gourmand"], "heart", "Benzaldehyde"),
    ("Honey", "蜂蜜", "gourmand", ["gourmand", "floral"], "base", None),
    ("Rum", "朗姆酒", "gourmand", ["gourmand"], "top", None),
    ("Whiskey", "威士忌", "gourmand", ["gourmand"], "top", None),
    ("Cotton Candy", "棉花糖", "gourmand", ["gourmand"], "heart", None),
    ("Licorice", "甘草", "gourmand", ["gourmand", "oriental"], "heart", "Anethole"),
    ("Marshmallow", "棉花软糖", "gourmand", ["gourmand"], "heart", None),
    # ---------------- 水生/清新 ----------------
    ("Sea Notes", "海洋香", "fresh_marine", ["aquatic"], "top", None),
    ("Salt", "海盐", "fresh_marine", ["aquatic"], "top", None),
    ("Marine", "海洋", "fresh_marine", ["aquatic"], "top", None),
    ("Water Notes", "水香", "fresh_marine", ["aquatic"], "top", None),
    ("Calone", "西瓜酮（海洋香）", "synthetic_marine", ["aquatic", "citrus"], "top", None),
    ("Ozonic Notes", "臭氧感", "fresh_marine", ["aquatic"], "top", None),
    # ---------------- 合成单体·醇类 ----------------
    ("Linalool", "芳樟醇", "synthetic_alcohol", ["fougere", "floral"], "top", "Linalool"),
    ("Geraniol", "香叶醇", "synthetic_alcohol", ["floral"], "heart", "Geraniol"),
    ("Citronellol", "香茅醇", "synthetic_alcohol", ["floral"], "heart", "Citronellol"),
    ("Phenylethyl Alcohol", "苯乙醇", "synthetic_alcohol", ["floral"], "heart", None),
    ("Anisyl Alcohol", "大茴香醇", "synthetic_alcohol", ["floral", "gourmand"], "heart", "Anisyl Alcohol"),
    ("Benzyl Alcohol", "苯甲醇", "synthetic_alcohol", ["floral"], "top", "Benzyl Alcohol"),
    ("Cinnamyl Alcohol", "肉桂醇", "synthetic_alcohol", ["oriental"], "heart", "Cinnamyl Alcohol"),
    ("Amylcinnamyl Alcohol", "戊基肉桂醇", "synthetic_alcohol", ["floral"], "heart", "Amylcinnamyl Alcohol"),
    ("Hydroxycitronellol", "羟基香茅醇", "synthetic_alcohol", ["floral"], "heart", None),
    ("Dihydromyrcenol", "二氢月桂烯醇", "synthetic_terpene_alcohol", ["fougere", "citrus"], "top", None),
    ("Menthol", "薄荷脑", "synthetic_alcohol", ["fougere"], "top", "Menthol"),
    ("Terpineol", "松油醇", "synthetic_terpene_alcohol", ["floral", "fougere"], "top", "Terpineol"),
    # ---------------- 合成单体·醛类 ----------------
    ("Citral", "柠檬醛", "synthetic_aldehyde", ["citrus"], "top", "Citral"),
    ("Cinnamal", "肉桂醛", "synthetic_aldehyde", ["oriental"], "heart", "Cinnamal"),
    ("Amyl Cinnamal", "戊基肉桂醛", "synthetic_aldehyde", ["floral"], "heart", "Amyl Cinnamal"),
    ("Hexyl Cinnamal", "己基肉桂醛", "synthetic_aldehyde", ["floral"], "heart", "Hexyl Cinnamal"),
    ("Hydroxycitronellal", "羟基香茅醛", "synthetic_aldehyde", ["floral"], "heart", "Hydroxycitronellal"),
    ("Lilial", "铃兰醛（已禁用）", "synthetic_aldehyde", ["floral"], "heart", "Butylphenyl Methylpropional"),
    ("Lyral", "新铃兰醛（已禁用）", "synthetic_aldehyde", ["floral"], "heart", "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde"),
    ("Aldehydes", "醛香（脂肪醛系列）", "synthetic_aldehyde", ["floral", "oriental"], "top", None),
    ("Vanillin", "香兰素", "synthetic_aldehyde", ["gourmand"], "base", "Vanillin"),
    ("Ethyl Vanillin", "乙基香兰素", "synthetic_aldehyde", ["gourmand"], "base", None),
    ("Floralozone", "花氧醛", "synthetic_aldehyde", ["floral", "aquatic"], "top", None),
    # ---------------- 合成单体·酯类 ----------------
    ("Linalyl Acetate", "乙酸芳樟酯", "synthetic_ester", ["fougere", "citrus"], "top", "Linalyl Acetate"),
    ("Benzyl Salicylate", "水杨酸苄酯", "synthetic_ester", ["floral"], "base", "Benzyl Salicylate"),
    ("Benzyl Benzoate", "苯甲酸苄酯", "synthetic_ester", ["floral", "oriental"], "base", "Benzyl Benzoate"),
    ("Benzyl Acetate", "乙酸苄酯", "synthetic_ester", ["floral"], "top", None),
    ("Geranyl Acetate", "乙酸香叶酯", "synthetic_ester", ["floral", "citrus"], "heart", "Geranyl Acetate"),
    ("Eugenyl Acetate", "乙酸丁香酚酯", "synthetic_ester", ["oriental"], "heart", "Eugenyl Acetate"),
    ("Isoeugenyl Acetate", "乙酸异丁香酚酯", "synthetic_ester", ["oriental"], "heart", "Isoeugenyl Acetate"),
    ("Methyl Salicylate", "水杨酸甲酯", "synthetic_ester", ["fougere"], "top", "Methyl Salicylate"),
    ("Amyl Salicylate", "水杨酸戊酯", "synthetic_ester", ["floral", "fougere"], "heart", "Amyl Salicylate"),
    ("Gamma-Lactones", "内酯类（椰子/桃）", "synthetic_ester", ["gourmand"], "heart", None),
    # ---------------- 合成单体·酮/紫罗兰酮 ----------------
    ("Alpha-Isomethyl Ionone", "α-异甲基紫罗兰酮", "synthetic_ketone", ["floral"], "heart", "Alpha-Isomethyl Ionone"),
    ("Ionones", "紫罗兰酮类", "synthetic_ketone", ["floral"], "heart", None),
    ("Methyl Ionones", "甲基紫罗兰酮类", "synthetic_ketone", ["floral"], "heart", "Methyl Ionones"),
    ("Dihydrojasmonate (Hedione)", "二氢茉莉酮酸甲酯", "synthetic_ester", ["floral", "citrus"], "heart", None),
    ("Methyl Cedryl Ketone (Acetyl Cedrene)", "乙酰柏木烯", "synthetic_ketone", ["woody"], "base", "Acetyl Cedrene"),
    # ---------------- 合成麝香/琥珀 ----------------
    ("Galaxolide (HHCB)", "佳乐麝香", "synthetic_polycyclic_musk", ["woody"], "base", "Hexamethylindanopyran"),
    ("Habanolide", "哈巴麝香", "synthetic_macrocyclic_musk", ["woody"], "base", None),
    ("Ethylene Brassylate", "乙烯基十三烷二酸酯（麝香-T）", "synthetic_macrocyclic_musk", ["woody", "gourmand"], "base", None),
    ("Ambroxan (Ambrox)", "降龙涎香醚", "synthetic_amber", ["woody", "oriental"], "base", None),
    ("Iso E Super (OTNE)", "超级木香（OTNE）", "synthetic_woody_amber", ["woody"], "base", "Tetramethyl Acetyloctahydronaphthalenes"),
    ("Ambrettolide", "黄葵内酯", "synthetic_macrocyclic_musk", ["woody", "floral"], "base", None),
    ("Cetalox", "龙涎醚", "synthetic_amber", ["woody", "oriental"], "base", None),
    ("Sclareol", "硬尾醇", "natural_resin", ["woody", "gourmand"], "base", "Sclareol"),
    ("Sandalore", "檀香醚", "synthetic_sandalwood", ["woody"], "base", "Trimethylcyclopentenyl Methylisopentenol"),
    ("Sulfonyl Musk", "磺酰麝香", "synthetic_musk", ["woody"], "base", None),
    # ---------------- 合成萜类 ----------------
    ("d-Limonene", "柠檬烯", "synthetic_terpene", ["citrus"], "top", "d-Limonene"),
    ("Pinene", "蒎烯", "synthetic_terpene", ["woody", "fougere"], "top", "Pinene"),
    ("Beta-Caryophyllene", "β-石竹烯", "synthetic_terpene", ["woody", "oriental"], "heart", "Beta-Caryophyllene"),
    ("Eucalyptol", "桉叶油素", "synthetic_ether", ["fougere"], "top", None),
    # ---------------- 香豆素/其他经典 ----------------
    ("Coumarin", "香豆素", "synthetic_lactone", ["gourmand", "woody"], "base", "Coumarin"),
    ("Eugenol", "丁香酚", "synthetic_phenol", ["oriental"], "heart", "Eugenol"),
    ("Isoeugenol", "异丁香酚", "synthetic_phenol", ["oriental"], "heart", "Isoeugenol"),
    ("Farnesol", "法尼醇", "synthetic_terpene_alcohol", ["floral"], "heart", "Farnesol"),
    ("Anethole", "茴香脑", "synthetic_phenol_ether", ["fougere", "gourmand"], "top", "Anethole"),
    ("Methyl 2-Octynoate", "甲基辛炔酸酯", "synthetic_ester", ["aquatic", "floral"], "top", "Methyl 2-octynoate"),
    ("Oakmoss", "橡苔", "natural_moss", ["fougere", "woody"], "base", "Evernia Prunastri Extract"),
    ("Treemoss", "树苔", "natural_moss", ["fougere", "woody"], "base", "Evernia Furfuracea Extract"),
    ("Carvone", "香芹酮", "synthetic_ketone", ["fougere", "citrus"], "top", "Carvone"),
    ("Benzaldehyde", "苯甲醛", "synthetic_aldehyde", ["gourmand"], "top", "Benzaldehyde"),
    ("Salicylaldehyde", "水杨醛", "synthetic_aldehyde", ["gourmand"], "top", "Salicylaldehyde"),
    ("Muguet Alcohol (Trimethylbenzenepropanol)", "铃兰醇", "synthetic_alcohol", ["floral", "woody"], "heart", "Trimethylbenzenepropanol"),
    ("Santalol", "檀香醇", "synthetic_terpene_alcohol", ["woody"], "base", "Santalol"),
    ("Camphor", "樟脑", "synthetic_ketone", ["fougere"], "top", "Camphor"),
    ("Vanilla Bourbon", "波本香草", "gourmand", ["gourmand"], "base", None),
    # ---------------- 功能辅料（INCI 解析用） ----------------
    ("Alcohol Denat.", "变性乙醇", "functional_solvent", [], "carrier", "Alcohol Denat."),
    ("Parfum (Fragrance)", "香精（未披露混合物）", "functional_fragrance_blend", [], "core", "Parfum"),
    ("Aqua (Water)", "水", "functional_solvent", [], "carrier", "Aqua"),
    ("Propylene Glycol", "丙二醇", "functional_humectant", [], "carrier", "Propylene Glycol"),
    ("Dipropylene Glycol", "二丙二醇", "functional_solvent", [], "carrier", "Dipropylene Glycol"),
    ("BHT", "二丁基羟基甲苯（抗氧化剂）", "functional_antioxidant", [], "carrier", "BHT"),
    ("Tocopherol", "生育酚（抗氧化剂）", "functional_antioxidant", [], "carrier", "Tocopherol"),
    ("Disodium EDTA", "EDTA 二钠（螯合剂）", "functional_chelator", [], "carrier", "Disodium EDTA"),
    ("Citric Acid", "柠檬酸（pH 调节）", "functional_ph", [], "carrier", "Citric Acid"),
    ("Ethylhexyl Salicylate", "水杨酸乙基己酯（UV 吸收）", "functional_uv", [], "carrier", "Ethylhexyl Salicylate"),
    ("Butyl Methoxydibenzoylmethane", "阿伏苯宗（UVA 防护）", "functional_uv", [], "carrier", "Butyl Methoxydibenzoylmethane"),
    ("Tris(Tetramethylhydroxypiperidinol) Citrate", "柠檬酸三(四甲基羟基哌啶醇)酯（光稳定）", "functional_uv", [], "carrier", None),
    ("Benzophenone-4", "二苯酮-4（UV 吸收）", "functional_uv", [], "carrier", "Benzophenone-4"),
    ("Phenoxyethanol", "苯氧乙醇（防腐）", "functional_preservative", [], "carrier", "Phenoxyethanol"),
    ("Limnanthes Alba Seed Oil", "白芒花籽油（润肤）", "functional_emollient", [], "carrier", None),
    ("Hexyl Cinnamal", "己基肉桂醛", "synthetic_aldehyde", ["floral"], "heart", "Hexyl Cinnamal"),
]


def main() -> None:
    fam_data = json.loads((SEED / "families.json").read_text(encoding="utf-8"))
    fams = {k for k in fam_data if k != "$comment"}
    items = []
    seen = set()
    for key, zh, cat, fam_list, layer, inci in I:
        if key in seen:
            continue
        seen.add(key)
        bad = [f for f in fam_list if f not in fams]
        assert not bad, f"{key}: 未知家族 {bad}"
        items.append({"key": key, "name_zh": zh, "category": cat, "families": fam_list,
                      "layer_hint": layer, "inci": inci,
                      "visual_anchor": f"色板/动效由 families.json 的 {fam_list[0]} 规则驱动" if fam_list else "无香调色彩（辅料）"})
    meta = {
        "$comment": (
            "原料词典：数据层 docx 三级分类（天然/合成单体/功能辅料）+ 26K 数据集高频香材的结构化版本。"
            "families 与 families.json 严格对齐（可视化映射锚点）；layer_hint 为金字塔层倾向（top/heart/base）；"
            "inci 字段用于成分表命中（与 allergens.json 的 INCI 匹配面互补）。"
        ),
        "built_at": "2026-09-17",
        "sources": ["数据层/香水成分数据及过敏香料.docx（分类底稿）", "doevent/perfume 高频香材", "Fragrantica 香材命名惯例"],
        "count": len(items),
        "items": items,
    }
    (SEED / "ingredients.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    by_cat = {}
    for it in items:
        by_cat[it["category"]] = by_cat.get(it["category"], 0) + 1
    print(f"ingredients.json: {len(items)} 条，{len(by_cat)} 类")
    print(dict(sorted(by_cat.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
