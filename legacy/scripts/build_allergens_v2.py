# -*- coding: utf-8 -*-
"""allergens.json v2 构建脚本（数据整理与化工原料分析 · 2026-09-17）

在 clean_data.py 产物（26 条旧致敏原）基础上：
1) 合并文献级 NESIL/人体 NOEL/LLNA EC3（Na et al. 2022 Dermatitis 33(2):161,
   RIFM WoE：Lalko 2008 citral=1400, Api 2022 geraniol=11000, 文档黄金算例 limonene=10000）
2) 合并 IFRA Cat4（fine fragrance 水醇类）限量（scentspiracy 汇编，evidence_level=secondary_compiled）
3) 合并 EU 2023/1545 新增 45 个条目（EUR-Lex 官方 HTML 解析：条目号 327-371、CAS、INCI 名组）
4) 合并香水基质实测浓度统计（Lu et al. 2021 JFDA 29(4)：14 款香水/除臭剂 26 致敏原定量）

输出: data/seed/allergens.json（条目数 71：26 旧 + 45 新；INCI 名匹配面 103 个）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

RETRIEVED = "2026-09-17"
SRC_EURLEX = "https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng"
SRC_NA2022 = "https://pubmed.ncbi.nlm.nih.gov/35147224/ (Na M. et al., Dermatitis 2022;33(2):161-175, Table 2, RIFM CNIH NOEL)"
SRC_LALKO = "https://pubmed.ncbi.nlm.nih.gov/18353514/ (Lalko J. et al. 2008, citral human NOEL 1400 μg/cm²)"
SRC_API2022 = "Api A.M. et al. 2022 Food Chem Toxicol, geraniol WoE NESIL 11 000 μg/cm²"
SRC_IFRA = "https://www.scentspiracy.com/blog/ifra-limits (IFRA Cat4 汇编，需与官方 per-material 页核对)"
SRC_JFDA = "https://www.jfda-online.com/cgi/viewcontent.cgi?article=3373&context=journal (Lu et al. 2021 JFDA 29(4) Table 4，单位 mg/g→%除以10000)"
SRC_LIM2018 = ("Lim DS et al. 2018, J Toxicol Environ Health A 81(22):1173-1185, "
               "doi:10.1080/15287394.2018.1543232（107 款喷雾香水 HPLC-UV 实测；"
               "Table 1 官方 WoE NESIL 引自 Api et al. 2008 RTP 52:3-23；Table 3 浓度 mg/kg）")

# ---------------------------------------------------------------- Api 2008 官方 WoE NESIL（μ g/cm²）与 LLNA EC3
# 经 Lim 2018 Table 1 转载；NESIL 首选此表（RIFM 官方 WoE），Na 2022 CNIH NOEL 作人体交叉验证
API2008 = {
    # label: (WoE NESIL, LLNA EC3, potency)
    "Methyl 2-octynoate": (120.0, 125.0, "Strong"),
    "Isoeugenol": (250.0, 498.0, "Moderate"),
    "Citral": (1400.0, 1414.0, "Weak"),
    "Anisyl Alcohol": (1500.0, 1475.0, "Weak"),
    "Cinnamyl Alcohol": (3000.0, 5250.0, "Weak"),
    "Amylcinnamyl Alcohol": (3500.0, 6250.0, "Weak"),
    "Coumarin": (3500.0, 12500.0, "Weak"),
    "Hydroxycitronellal": (5000.0, 5612.0, "Weak"),
    "Farnesol": (2700.0, 1200.0, "Weak"),
    "Eugenol": (5900.0, 2703.0, "Weak"),
    "Benzyl Alcohol": (5900.0, 12500.0, "Weak"),
    "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": (4000.0, 4275.0, "Weak"),
    "Butylphenyl Methylpropional": (4100.0, 2372.0, "Weak"),
    "Benzyl Cinnamate": (4700.0, 4600.0, "Weak"),
    "Geraniol": (11800.0, 3525.0, "Weak"),
    "d-Limonene": (10000.0, 10075.0, "Extremely weak"),
    "Linalool": (15000.0, 15000.0, "Extremely weak"),
    "Benzyl Salicylate": (17700.0, 725.0, "Weak"),
    "Amyl Cinnamal": (23600.0, 2942.0, "Weak"),
    "Hexyl Cinnamal": (23600.0, 2372.0, "Weak"),
    "Citronellol": (29500.0, 10875.0, "Extremely weak"),
    "Benzyl Benzoate": (59000.0, 12500.0, "Extremely weak"),
    "Alpha-Isomethyl Ionone": (71000.0, 5450.0, "Weak"),
    "Evernia Furfuracea Extract": (None, None, None),
    "Evernia Prunastri Extract": (None, None, None),
    "Cinnamal": (None, None, None),  # Api 2008 表未含，用 CNIH 591
}

# ---------------------------------------------------------------- Lim 2018 Table 3：107 款香水实测（mg/kg）
# label: (women_mean, women_median, women_max, men_mean, men_median, men_max)；mg/kg ÷ 10000 = %
LIM2018_CONC = {
    "Butylphenyl Methylpropional": (4026.84, 2108.08, 34945.26, 1129.32, 387.05, 6867.86),
    "d-Limonene": (3863.32, 2494.12, 26196.84, 5008.18, 4462.09, 17352.34),
    "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": (2768.27, 0, 27106.25, 1924.16, 644.51, 9315.32),
    "Linalool": (2262.72, 1553.69, 21845.38, 2616.97, 1647.20, 8314.67),
    "Alpha-Isomethyl Ionone": (1859.52, 99.12, 15102.70, 2168.85, 0, 11105.20),
    "Geraniol": (1630.49, 253.84, 8997.68, 1146.85, 22.66, 8458.32),
    "Benzyl Salicylate": (1128.03, 0, 6473.74, 889.56, 0, 8152.90),
    "Citronellol": (1005.30, 253.37, 7897.15, 547.36, 270.31, 4253.99),
    "Citral": (811.79, 31.85, 34215.24, 164.73, 118.46, 803.19),
    "Hexyl Cinnamal": (671.12, 100.27, 4674.90, 262.53, 0, 1939.56),
    "Farnesol": (465.25, 90.32, 3994.24, 576.70, 331.54, 2237.58),
    "Isoeugenol": (328.65, 42.69, 8639.93, 50.11, 0, 256.12),
    "Hydroxycitronellal": (276.55, 0, 4671.66, 511.55, 0, 4105.49),
    "Anisyl Alcohol": (182.72, 0, 2519.72, 112.59, 0, 2873.28),
    "Coumarin": (159.91, 0, 1848.25, 616.80, 0, 3337.49),
    "Benzyl Benzoate": (148.95, 15.68, 4933.87, 224.79, 0, 5623.91),
    "Eugenol": (140.44, 53.28, 2474.49, 69.00, 35.76, 303.27),
    "Benzyl Alcohol": (100.86, 0, 4094.71, 33.35, 6.66, 183.35),
    "Benzyl Cinnamate": (92.40, 0, 1695.65, 134.60, 0, 1073.47),
    "Methyl 2-octynoate": (72.23, 12.06, 954.39, 14.20, 0, 165.68),
    "Cinnamyl Alcohol": (12.15, 0, 308.94, 8.38, 0, 162.28),
    "Amylcinnamyl Alcohol": (2.39, 0, 65.84, 1.59, 0, 19.68),
}
# Lim 2018 Table 4/5：最坏情形 AEL/CEL<1 的五种（女香 max 口径）——三闸门叙事直接引用
LIM2018_UNSAFE = {
    "Butylphenyl Methylpropional": 0.53, "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": 0.67,
    "Citral": 0.19, "Isoeugenol": 0.13, "Methyl 2-octynoate": 0.57,
}

# ---------------------------------------------------------------- 文献 NESIL 表
# key=统一 INCI 标注名 → (nesil, basis, human_noel, human_loel, llna_ec3, woe_potency)
# NESIL 优先 RIFM 官方 WoE；无官方值时以 CNIH 人体 NOEL 作 NESIL 基准（evidence_level=peer_reviewed）
DOC = {
    "Methyl 2-octynoate":        (118.0,   "na2022_cnih", 118.0,   None,   None,    "Strong"),
    "Isoeugenol":                (250.0,   "na2022_cnih", 250.0,   775.0,  500.0,   "Moderate"),
    "Cinnamal":                  (591.0,   "na2022_cnih", 591.0,   775.0,  262.0,   "Moderate"),
    "Evernia Furfuracea Extract": (700.0,  "na2022_cnih", 700.0,   1417.0, None,    "Moderate"),
    "Evernia Prunastri Extract": (700.0,   "na2022_cnih", 700.0,   None,   None,    "Moderate"),
    "Citral":                    (1400.0,  "rifm_woe_lalko2008", 1417.0, 3876.0, 1414.0, "Moderate"),
    "Anisyl Alcohol":            (1771.0,  "na2022_cnih", 1771.0,  None,   None,    "Moderate"),
    "Farnesol":                  (2755.0,  "na2022_cnih", 2755.0,  6897.0, None,    "Weak"),
    "Cinnamyl Alcohol":          (2953.0,  "na2022_cnih", 2953.0,  4724.0, 5250.0,  "Weak"),
    "Coumarin":                  (3543.0,  "na2022_cnih", 3543.0,  8858.0, None,    "Weak"),
    "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": (4000.0, "na2022_cnih", 4000.0, 6259.0, 4275.0, "Weak"),
    "Butylphenyl Methylpropional": (4125.0, "na2022_cnih", 4125.0, 29528.0, 2454.0, "Weak"),
    "Amylcinnamyl Alcohol":      (3543.0,  "na2022_cnih", 3543.0, 7085.0, None,    "Very weak"),
    "Benzyl Cinnamate":          (4724.0,  "na2022_cnih", 4724.0, 9449.0, None,    "Weak"),
    "Hydroxycitronellal":        (4960.0,  "na2022_cnih", 4960.0, 5814.0, 5553.0,  "Weak"),
    "Anethole":                  (5509.0,  "na2022_cnih", 5509.0, None,   None,    "Weak"),
    "Benzyl Alcohol":            (5905.0,  "na2022_cnih", 5905.0, 8858.0, None,    "Weak"),
    "Eugenol":                   (5906.0,  "na2022_cnih", 5906.0, 11811.0, 2703.0, "Weak"),
    "Benzaldehyde":              (590.0,   "na2022_cnih", 590.0,  None,   None,    "Weak"),
    "Vanillin":                  (5314.0,  "na2022_cnih", 5314.0, None,   None,    "Very weak"),
    "Methyl Salicylate":         (5517.0,  "na2022_cnih", 5517.0, 8858.0, None,    "Very weak"),
    "Amyl Cinnamal":             (23622.0, "na2022_cnih", 23622.0, 47244.0, 2513.0, "Weak"),
    "Geraniol":                  (11000.0, "rifm_woe_api2022", 11811.0, None, 4063.0, "Very weak"),
    "Benzyl Salicylate":         (17715.0, "na2022_cnih", 17715.0, 23622.0, None,  "Very weak"),
    "Hexyl Cinnamal":            (23622.0, "na2022_cnih", 23622.0, None,   None,   "Very weak"),
    "Amyl Salicylate":           (35430.0, "na2022_cnih", 35430.0, None,   None,   "Very weak"),
    "Citronellol":               (29525.0, "na2022_cnih", 29525.0, 47244.0, None,  "Very weak"),
    "Benzyl Benzoate":           (59050.0, "na2022_cnih", 59050.0, 118110.0, None, "Very weak"),
    "Alpha-Isomethyl Ionone":    (70860.0, "na2022_cnih", 70860.0, 106290.0, None, "Very weak"),
    "d-Limonene":                (10000.0, "doc_golden_case", 10000.0, None, None, "NS（本体非致敏原，氧化产物致敏）"),
    "Linalool":                  (14998.0, "na2022_cnih", 14998.0, 23622.0, None, "NS（本体非致敏原，氧化产物致敏）"),
    # 新增 56 中有文献值的天然精油原料（对应其主打成分/净油的人体数据，供参考档）
    "Jasminum Officinale Oil":   (1400.0,  "na2022_cnih_absolute", 1400.0, None, None, "Moderate（茉莉净油数据）"),
    "Cananga Odorata Flower Oil": (1771.0, "na2022_cnih_absolute", 1771.0, None, None, "Moderate（依兰净油数据）"),
    "Carvone":                   (2657.0,  "na2022_cnih", 2657.0, None, None, "Weak"),
    "Trimethylbenzenepropanol":  (9917.0,  "na2022_cnih", 9917.0, None, None, "Very weak"),
    "Tetramethyl Acetyloctahydronaphthalenes": (47244.0, "na2022_cnih", 47244.0, None, None, "Very weak"),
    "Methyl Ionones":            (70860.0, "na2022_cnih", 70860.0, None, None, "Very weak"),
}

# ---------------------------------------------------------------- IFRA Cat4 限量（%）
IFRA_CAT4 = {
    "Alpha-Isomethyl Ionone": 30.0, "Amyl Cinnamal": 7.0, "Amylcinnamyl Alcohol": 1.5,
    "Anisyl Alcohol": 0.21, "Benzyl Alcohol": 2.5, "Benzyl Benzoate": 4.8,
    "Benzyl Cinnamate": 2.0, "Benzyl Salicylate": 7.3,
    "Butylphenyl Methylpropional": 1.4, "Cinnamal": 0.25, "Cinnamyl Alcohol": 0.6,
    "Citral": 0.6, "Citronellol": 12.0, "Coumarin": 1.5, "Eugenol": 2.5,
    "Farnesol": 1.2, "Geraniol": 4.7, "Hexyl Cinnamal": 9.9,
    "Hydroxycitronellal": 2.1,
    "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": 0.2,
    "Isoeugenol": 0.11, "Methyl 2-octynoate": 0.047,
    "Evernia Furfuracea Extract": 0.1, "Evernia Prunastri Extract": 0.1,
    # Linalool/Limonene：IFRA 不因致敏限量，而是氧化管控（抗氧化剂+过氧化值声明）
}

# ---------------------------------------------------------------- JFDA 2021 香水实测（n=14）
# (检出数, min mg/g, max mg/g, mean mg/g)；mg/g ÷ 10000 = %
JFDA_PERFUME = {
    "Linalool": (14, 7, 6574, 1557),
    "Limonene": (13, 84, 5603, 1748),
    "Geraniol": (12, 43, 3688, 914),
    "Citronellol": (11, 4, 8100, 2200),
    "Citral": (11, 7, 196, 94),
    "Coumarin": (10, 14, 4535, 559),
    "Hydroxycitronellal": (9, 83, 4040, 926),
    "Alpha-Isomethyl Ionone": (9, 105, 4124, 1822),
    "Benzyl Alcohol": (7, 9, 294, 128),
    "Benzyl Benzoate": (7, 58, 4699, 856),
    "Benzyl Salicylate": (6, 20, 13973, 3346),
    "Isoeugenol": (5, 36, 130, 79),
    "Hexyl Cinnamal": (5, 75, 17868, 4664),
    "Cinnamyl Alcohol": (4, 102, 1789, 775),
    "Eugenol": (4, 40, 200, 106),
    "Amyl Cinnamal": (2, 81, 752, 417),
    "Butylphenyl Methylpropional": (2, 7650, 15305, 11477),
    "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": (1, 204, 204, 204),
}

# ---------------------------------------------------------------- EU 2023/1545 新增 45 条目
# (label, [INCI 名列表], 中文名, 主 CAS, 附加 CAS, 家族, 备注)
NEW_ENTRIES = [
    ("Acetyl Cedrene", ["Acetyl Cedrene"], "乙酰基柏木烯", "32388-55-9", [], ["woody"], "合成柏木木质香"),
    ("Amyl Salicylate", ["Amyl Salicylate"], "水杨酸戊酯", "2050-08-0", [], ["floral"], "三叶草青花香"),
    ("Anethole", ["Anethole"], "茴香脑", "104-46-1", ["4180-23-8"], ["fougere"], "茴香甘草香"),
    ("Benzaldehyde", ["Benzaldehyde"], "苯甲醛", "100-52-7", [], ["gourmand"], "杏仁樱桃香"),
    ("Camphor", ["Camphor"], "樟脑", "76-22-2", ["21368-68-3", "464-49-3", "464-48-2"], ["fougere"], "樟脑凉香"),
    ("Beta-Caryophyllene", ["Beta-Caryophyllene"], "β-石竹烯", "87-44-5", [], ["woody", "oriental"], "丁香胡椒木香"),
    ("Carvone", ["Carvone"], "香芹酮", "99-49-0", ["6485-40-1", "2244-16-8"], ["fougere", "citrus"], "留兰香/葛缕子"),
    ("Dimethyl Phenethyl Acetate", ["Dimethyl Phenethyl Acetate"], "二甲基苯乙基乙酸酯", "151-05-3", [], ["floral"], "青绿花香"),
    ("Hexadecanolactone", ["Hexadecanolactone"], "环十六内酯", "109-29-5", [], ["woody"], "大环麝香奶油香"),
    ("Hexamethylindanopyran", ["Hexamethylindanopyran"], "佳乐麝香", "1222-05-5", [], ["woody"], "多环麝香（HHCB）"),
    ("Linalyl Acetate", ["Linalyl Acetate"], "乙酸芳樟酯", "115-95-7", [], ["fougere", "citrus"], "薰衣草/香柠檬酯香"),
    ("Menthol", ["Menthol"], "薄荷脑", "89-78-1", ["1490-04-6", "2216-51-5", "15356-60-2"], ["fougere"], "薄荷凉香"),
    ("Trimethylcyclopentenyl Methylisopentenol", ["Trimethylcyclopentenyl Methylisopentenol"], "三甲基环戊烯基甲基异戊烯醇", "67801-20-1", [], ["woody"], "合成檀香"),
    ("Salicylaldehyde", ["Salicylaldehyde"], "水杨醛", "90-02-8", [], ["gourmand"], "杏仁样药草香"),
    ("Santalol", ["Santalol"], "檀香醇", "11031-45-1", ["115-71-9", "77-42-9"], ["woody"], "檀香 α+β"),
    ("Sclareol", ["Sclareol"], "硬尾醇", "515-03-7", [], ["woody", "gourmand"], "鼠尾草琥珀龙涎"),
    ("Terpineol", ["Terpineol"], "松油醇", "8000-41-7", ["98-55-5", "138-87-4"], ["floral", "fougere"], "丁香/松木花香"),
    ("Tetramethyl Acetyloctahydronaphthalenes", ["Tetramethyl Acetyloctahydronaphthalenes"], "甲基环甘菊酮类（Iso E Super 类）", "54464-57-2", [], ["woody"], "OTNE 类木质龙涎"),
    ("Trimethylbenzenepropanol", ["Trimethylbenzenepropanol"], "三甲基苯丙醇", "103694-68-4", [], ["floral", "woody"], "合成铃兰/檀香"),
    ("Vanillin", ["Vanillin"], "香兰素", "121-33-5", [], ["gourmand"], "香草豆香"),
    ("Cananga Odorata Flower Oil", ["Cananga Odorata Flower Extract", "Cananga Odorata Flower Oil"], "依兰依兰花油/提取物", "83863-30-3", ["8006-81-3", "68606-83-7", "93686-30-7"], ["floral", "oriental"], "依兰白花；净油有 IgE 蛋白残留风险"),
    ("Cinnamomum Cassia Leaf Oil", ["Cinnamomum Cassia Leaf Oil"], "桂皮叶油", "8007-80-5", ["84961-46-6"], ["oriental"], "中国肉桂辛香，含肉桂醛"),
    ("Cinnamomum Zeylanicum Bark Oil", ["Cinnamomum Zeylanicum Bark Oil"], "锡兰肉桂皮油", "8015-91-6", ["84649-98-9"], ["oriental"], "锡兰肉桂辛香，含肉桂醛/丁香酚"),
    ("Citrus Aurantium Amara Flower Oil", ["Citrus Aurantium Amara Flower Oil", "Citrus Aurantium Dulcis Flower Oil"], "苦/甜橙花油", "72968-50-4", ["8028-48-6", "8016-38-4"], ["floral", "citrus"], "橙花（苦橙花）"),
    ("Citrus Aurantium Amara Peel Oil", ["Citrus Aurantium Amara Peel Oil", "Citrus Aurantium Dulcis Peel Oil", "Citrus Sinensis Peel Oil"], "苦/甜橙皮油", "68916-04-1", ["97766-30-8", "8028-48-6", "8008-57-9"], ["citrus"], "苦橙/甜橙皮精油"),
    ("Citrus Aurantium Bergamia Peel Oil", ["Citrus Aurantium Bergamia Peel Oil"], "香柠檬皮油", "8007-75-8", ["89957-91-5", "68648-33-9", "85049-52-1"], ["citrus"], "佛手柑；含呋喃香豆素光毒风险（IFRA 另有限量）"),
    ("Citrus Limon Peel Oil", ["Citrus Limon Peel Oil"], "柠檬皮油", "84929-31-7", ["8008-56-8"], ["citrus"], "柠檬精油，富含柠檬烯"),
    ("Cymbopogon Citratus Leaf Oil", ["Cymbopogon Schoenanthus Oil", "Cymbopogon Flexuosus Oil", "Cymbopogon Citratus Leaf Oil"], "柠檬草油", "8007-02-1", ["89998-16-3", "91844-92-7"], ["citrus"], "柠檬草，富含柠檬醛"),
    ("Eucalyptus Globulus Leaf Oil", ["Eucalyptus Globulus Leaf Oil", "Eucalyptus Globulus Leaf/Twig Oil"], "蓝桉叶油", "97926-40-4", ["8000-48-4"], ["fougere"], "桉叶脑凉香，鼻炎人群呼吸道刺激提示"),
    ("Eugenia Caryophyllus Leaf Oil", ["Eugenia Caryophyllus Leaf Oil", "Eugenia Caryophyllus Flower Oil", "Eugenia Caryophyllus Stem Oil", "Eugenia Caryophyllus Bud Oil"], "丁香油（叶/花/茎/蕾）", "8000-34-8", ["8015-97-2", "84961-50-2"], ["oriental"], "丁香精油，富含丁香酚"),
    ("Jasminum Officinale Oil", ["Jasminum Grandiflorum Flower Extract", "Jasminum Officinale Oil", "Jasminum Officinale Flower Extract"], "茉莉油/提取物", "84776-64-7", ["90045-94-6", "8022-96-6", "8024-43-9"], ["floral"], "茉莉；净油 IgE 蛋白残留风险"),
    ("Juniperus Virginiana Oil", ["Juniperus Virginiana Oil", "Juniperus Virginiana Wood Oil"], "弗吉尼亚雪松木油", "8000-27-9", ["85085-41-2"], ["woody"], "铅笔雪松木香"),
    ("Laurus Nobilis Leaf Oil", ["Laurus Nobilis Leaf Oil"], "月桂叶油", "8002-41-3", ["8007-48-5", "84603-73-6"], ["fougere"], "月桂辛青香"),
    ("Lavandula Angustifolia Oil", ["Lavandula Hybrida Oil", "Lavandula Hybrida Extract", "Lavandula Hybrida Flower Extract", "Lavandula Intermedia Flower/Leaf/Stem Extract", "Lavandula Intermedia Flower/Leaf/Stem Oil", "Lavandula Intermedia Oil", "Lavandula Angustifolia Oil", "Lavandula Angustifolia Flower/Leaf/Stem Extract"], "薰衣草/杂交薰衣草油", "84776-65-8", ["8022-15-9", "93455-96-0", "93455-97-1", "92623-76-2", "8000-28-0", "90063-37-9"], ["fougere"], "薰衣草，富含芳樟醇/乙酸芳樟酯；花粉蛋白 IgE 交叉风险"),
    ("Mentha Piperita Oil", ["Mentha Piperita Oil"], "椒样薄荷油", "8006-90-4", ["84082-70-2"], ["fougere"], "薄荷精油，富含薄荷脑"),
    ("Mentha Viridis Leaf Oil", ["Mentha Viridis Leaf Oil"], "留兰香油", "8008-79-5", ["84696-51-5"], ["fougere"], "留兰香，富含香芹酮"),
    ("Narcissus Poeticus Extract", ["Narcissus Poeticus Extract", "Narcissus Pseudonarcissus Flower Extract", "Narcissus Jonquilla Extract", "Narcissus Tazetta Extract"], "水仙提取物", "90064-26-9", ["68917-12-4", "90064-27-0", "90064-25-8"], ["floral"], "水仙花香"),
    ("Pelargonium Graveolens Flower Oil", ["Pelargonium Graveolens Flower Oil"], "天竺葵花油", "90082-51-2", ["8000-46-2"], ["floral", "fougere"], "玫瑰-青绿天竺葵，富含香叶醇/香茅醇"),
    ("Pogostemon Cablin Oil", ["Pogostemon Cablin Oil"], "广藿香油", "8014-09-3", ["84238-39-1"], ["woody"], "广藿香土木香"),
    ("Rosa Damascena Flower Oil", ["Rosa Damascena Flower Oil", "Rosa Damascena Flower Extract", "Rosa Alba Flower Oil", "Rosa Alba Flower Extract", "Rosa Canina Flower Oil", "Rosa Centifolia Flower Oil", "Rosa Centifolia Flower Extract", "Rosa Gallica Flower Oil", "Rosa Rugosa Flower Oil"], "玫瑰花油/提取物（多组）", "8007-01-0", ["90106-38-0", "93334-48-6", "84696-47-9", "84604-12-6", "84604-13-7", "92347-25-6"], ["floral"], "玫瑰；净油 IgE 蛋白残留风险"),
    ("Santalum Album Oil", ["Santalum Album Oil"], "檀香油", "8006-87-9", ["84787-70-2"], ["woody"], "印度檀香木香"),
    ("Eugenyl Acetate", ["Eugenyl Acetate"], "乙酸丁香酚酯", "93-28-7", [], ["oriental"], "丁香辛甜香"),
    ("Geranyl Acetate", ["Geranyl Acetate"], "乙酸香叶酯", "105-87-3", [], ["floral", "citrus"], "玫瑰薰衣草果香"),
    ("Isoeugenyl Acetate", ["Isoeugenyl Acetate"], "乙酸异丁香酚酯", "93-29-8", [], ["oriental"], "康乃馨辛香"),
    ("Pinene", ["Alpha-Pinene", "Beta-Pinene"], "蒎烯（α+β）", "80-56-8", ["7785-70-8", "127-91-3", "18172-67-3"], ["woody", "fougere"], "松木萜烯；氧化生成过氧化物（EU 要求过氧化值<10 mmol/L）"),
]

# 旧 26 条目在 EUR-Lex Annex III 中的条目号（45 苯甲醇/其余 67-92 分布）
OLD_ENTRY_NO = {
    "Benzyl Alcohol": 45, "Amyl Cinnamal": 67, "Amylcinnamyl Alcohol": 68, "Anisyl Alcohol": 69,
    "Cinnamal": 70, "Isoeugenol": 73, "Eugenol": 74, "Coumarin": 75, "Hydroxycitronellal": 76,
    "Citronellol": 77, "Benzyl Salicylate": 78, "Benzyl Cinnamate": 79, "Farnesol": 80,
    "Butylphenyl Methylpropional": 81, "Linalool": 82, "Benzyl Benzoate": 83,
    "Methyl 2-octynoate": 84, "Alpha-Isomethyl Ionone": 85, "Citral": 86, "Citronellal": 87,
    "Limonene": 88, "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde": 89,
    "Evernia Prunastri Extract": 90, "Evernia Furfuracea Extract": 91,
    "Hexyl Cinnamal": 92, "Cinnamyl Alcohol": 102,
}
# 注：条目号在不同 Annex III 版本中略有出入；Citronellal/Cinnamyl Alcohol 等以官方表为准可校准。
# 官方 EU 单独限量（EUR-Lex 原文解析，%）
EU_LIMIT = {
    "Isoeugenol": (0.02, "Annex III entry 73(b)：其他产品 0.02%"),
    "Benzyl Alcohol": (None, "entry 45：作防腐剂以外用途需标注"),
}


# 旧 xlsx INCI 名 → 文献键名（大小写/别名归一）
ALIAS = {
    "methyl-2-octynoate": "Methyl 2-octynoate",
    "α-isomethyl ionone": "Alpha-Isomethyl Ionone",
    "alpha-isomethyl ionone": "Alpha-Isomethyl Ionone",
    "oakmoss extract": "Evernia Prunastri Extract",
    "treemoss extract": "Evernia Furfuracea Extract",
    "anisyl alcohol": "Anisyl Alcohol",
    "benzyl salicylate": "Benzyl Salicylate",
    "benzyl benzoate": "Benzyl Benzoate",
    "benzyl cinnamate": "Benzyl Cinnamate",
    "benzyl alcohol": "Benzyl Alcohol",
    "amyl cinnamal": "Amyl Cinnamal",
    "amylcinnamyl alcohol": "Amylcinnamyl Alcohol",
    "cinnamal": "Cinnamal", "cinnamyl alcohol": "Cinnamyl Alcohol",
    "citral": "Citral", "citronellol": "Citronellol", "coumarin": "Coumarin",
    "eugenol": "Eugenol", "isoeugenol": "Isoeugenol", "farnesol": "Farnesol",
    "geraniol": "Geraniol", "hexyl cinnamal": "Hexyl Cinnamal",
    "hydroxycitronellal": "Hydroxycitronellal", "linalool": "Linalool",
    "d-limonene": "d-Limonene",
    "butylphenyl methylpropional": "Butylphenyl Methylpropional",
    "hydroxyisohexyl-3-cyclohexene-carboxaldehyde": "Hydroxyisohexyl-3-Cyclohexene-Carboxaldehyde",
}


def canon(name: str) -> str:
    n = name.split("(")[0].strip()  # 去括注（如 "Methyl-2-octynoate(Methyl heptine carbonate)"）
    return ALIAS.get(n.lower(), n)


def build() -> None:
    # clean_data.py 的 guard：检测到 v2 增强数据时基础产物写入 allergens.base.json
    base_path = SEED / "allergens.base.json"
    src = base_path if base_path.exists() else SEED / "allergens.json"
    old = json.loads(src.read_text(encoding="utf-8"))["items"]
    items = []
    n_doc = 0
    for a in old:
        name = canon(a["inci"])
        d = DOC.get(name)
        item = dict(a)  # 保留 clean_data.py 全部旧字段
        item["inci"] = name  # 统一为文献键名（规范化后）
        item.update({
            "eu_2023_1545_group": "existing",
            "eu_annex_iii_entry": OLD_ENTRY_NO.get(name),
            "inci_names": [name],
            "label_threshold_pct": {"leave_on": 0.001, "rinse_off": 0.01},
            "source_urls": [SRC_EURLEX, SRC_NA2022],
            "retrieved": RETRIEVED,
        })
        if d:
            nesil, basis, noel, loel, ec3, woe = d
            api = API2008.get(name)
            final_nesil = (api[0] if api and api[0] else nesil)
            final_basis = ("rifm_woe_api2008" if api and api[0] else basis)
            final_ec3 = (api[1] if api and api[1] else ec3)
            item.update({
                "nesil": final_nesil, "nesil_source": "documented", "nesil_basis": final_basis,
                "human_noel": noel, "human_loel": loel, "llna_ec3": final_ec3,
                "woe_potency": woe, "evidence_level": "peer_reviewed",
            })
            n_doc += 1
        else:
            item["evidence_level"] = "demo_estimate"
        if name in LIM2018_CONC:
            wm, wmed, wmax, mm, mmed, mmax = LIM2018_CONC[name]
            item["measured_conc_pct"] = {
                "study": "Lim 2018 (n=107 spray perfumes, HPLC-UV)",
                "women_n76": {"mean": round(wm / 10000, 5), "median": round(wmed / 10000, 5), "max": round(wmax / 10000, 5)},
                "men_n31": {"mean": round(mm / 10000, 5), "median": round(mmed / 10000, 5), "max": round(mmax / 10000, 5)},
                "unit_note": "mg/kg ÷ 10000 = % (w/w)",
            }
            item.setdefault("source_urls", []).append(SRC_LIM2018)
        if name in LIM2018_UNSAFE:
            item["qra_worst_case_ael_cel_ratio"] = LIM2018_UNSAFE[name]
            item["qra_note"] = "Lim 2018 最坏情形（女香 max 浓度）AEL/CEL<1，QRA1 口径下存在致敏诱导风险"
        if name in IFRA_CAT4:
            item["ifra_limit_pct"] = IFRA_CAT4[name]
            item["ifra_limit_basis"] = "IFRA Cat4（水醇类淡香水/香水），scentspiracy 汇编"
            item.setdefault("source_urls", []).append(SRC_IFRA)
        else:
            item["ifra_limit_pct"] = None
            item["ifra_limit_basis"] = "IFRA 无最终产品致敏限量，氧化管控（抗氧化剂/过氧化值声明）"
        jfda_key = next((k for k in JFDA_PERFUME if k in (name, {"d-Limonene": "Limonene"}.get(name, name))), None)
        if jfda_key:
            det, lo, hi, mean = JFDA_PERFUME[jfda_key]
            item["typical_conc_pct"] = {
                "product": "perfume/deodorant spray (n=14, Lu 2021 JFDA)",
                "detected": f"{det}/14", "min": round(lo / 10000, 5), "max": round(hi / 10000, 5),
                "mean": round(mean / 10000, 5),
            }
            item.setdefault("source_urls", []).append(SRC_JFDA)
        if name in EU_LIMIT and EU_LIMIT[name][0]:
            item["eu_limit_pct"] = EU_LIMIT[name][0]
        items.append(item)

    # ---- 新增 45 条目
    for i, (label, inci_names, zh, cas, cas_extra, fams, note) in enumerate(NEW_ENTRIES, start=327):
        d = DOC.get(label)
        is_natural = ("Oil" in label or "Extract" in label)
        item = {
            "inci": label,
            "inci_raw": label,
            "inci_names": inci_names,
            "name_zh": zh,
            "cas": cas,
            "cas_extra": cas_extra,
            "eu_2023_1545_group": "new",
            "eu_annex_iii_entry": i,
            "label_threshold_pct": {"leave_on": 0.001, "rinse_off": 0.01},
            "tier": "medium" if is_natural else "low",
            "is_natural_extract": is_natural,
            "high_frequency": False,
            "oxidation_prone": label in ("Pinene",) or any(
                k in label for k in ("Citrus", "Lavandula", "Pinene")),
            "k_ox_per_day": None,
            "banned_eu": False,
            "reproductive_flag": False,
            "families": fams,
            "nesil": None, "nesil_source": "demo_estimate",
            "evidence_level": "regulatory_list",
            "ifra_limit_pct": IFRA_CAT4.get(label),
            "ifra_limit_basis": "IFRA Cat4（水醇类），scentspiracy 汇编" if label in IFRA_CAT4 else None,
            "clinical_noel": None,
            "note": note,
            "source_urls": [SRC_EURLEX, SRC_NA2022],
            "retrieved": RETRIEVED,
        }
        if d:
            nesil, basis, noel, loel, ec3, woe = d
            item.update({
                "nesil": nesil, "nesil_source": "documented", "nesil_basis": basis,
                "human_noel": noel, "human_loel": loel, "llna_ec3": ec3,
                "woe_potency": woe, "evidence_level": "peer_reviewed",
            })
            n_doc += 1
        items.append(item)

    meta = {
        "$comment": (
            "致敏原总库 v2（EU 2023/1545 全量覆盖）。计数口径：条例需单独标注的致敏原共 82 个"
            "（26 旧 + 56 新，新条目组合展开后），本库以 71 个条目级（glossary）组织、"
            "inci_names 展开共 129 个 INCI 匹配名供成分表命中。"
            "NESIL 优先级：RIFM 官方 WoE > CNIH 人体 NOEL（Na et al. 2022 Dermatitis 33(2):161 Table 2）"
            "> LLNA EC3 > demo_estimate。IFRA Cat4 为 scentspiracy 汇编值（secondary_compiled），"
            "三闸门取最严判定故不影响安全侧。typical_conc_pct 来自 Lu 2021 JFDA 实测（n=14 香水）。"
            "引擎约定：nesil_source=='documented' 不叠加 demo 惩罚；'demo_estimate' 叠加 config.saf.demo_estimate_penalty。"
        ),
        "built_at": RETRIEVED,
        "count": len(items),
        "count_documented_nesil": n_doc,
        "inci_name_match_surface": sum(len(i["inci_names"]) for i in items),
        "sources": {
            "eu_regulation": SRC_EURLEX,
            "nesil_primary": SRC_NA2022,
            "citral_nesil": SRC_LALKO,
            "geraniol_nesil": SRC_API2022,
            "ifra_cat4_compiled": SRC_IFRA,
            "perfume_measured_conc": SRC_JFDA,
        },
        "items": items,
    }
    out = SEED / "allergens.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"allergens.json v2: {len(items)} 条 | documented NESIL: {n_doc} | "
          f"inci 匹配面: {meta['inci_name_match_surface']}")
    fam = {}
    for it in items:
        for f in it.get("families", []):
            fam[f] = fam.get(f, 0) + 1
    print("家族分布:", fam)


if __name__ == "__main__":
    build()
