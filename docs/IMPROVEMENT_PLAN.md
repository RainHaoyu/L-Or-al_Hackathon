# 万象Aura · 改进清单

> **本文档的定位**：当前仓库**已有一份独立完成的完整实现**（原有"启动包"脚手架文档与契约已删除，
> 旧说明归档在 `docs/_archive/README-startup-package.md`）。
> 从现在起，**以仓库现有实现为主体，通过改进它来交付万象Aura 的目标能力**。
> 本文档只做一件事：把「现状 → 目标」之间所有待改进项列清楚，作为后续迭代的工作台。
>
> 建立日期：迁移当日｜状态：迭代中｜不属于任何已冻结契约
>
> **仓库状态说明（2026-09-18）**：本文档最初对应另一份带 git 历史的迁移仓库（提交 `dc9a0ac`，
> 第 1 批在该仓库完成）。当前工作区的实际代码副本为 **`unbounded/`**（无 git；
> 其 `services/api`、`apps/web`、`data/seed`、`scripts` 与本文描述的结构一一对应）。
> 自第 2 批起，所有改动直接落地 `unbounded/` 并同步记录于本文档；第 1 批的等价修复已随第 2 批
> 一并落地本副本（后端测试 36 → 70）。另：本工作区**存在** `数据层/` 原始 xlsx（§3.12-6 的
> "已丢失"仅适用于另一仓库），`clean_data.py` 在本副本可复现基线数据。

---

## 0. 本次变更说明

| 项 | 处理 |
| --- | --- |
| 历史实现的 `apps/ data/ scripts/ services/ package.json` 等 | **已平移到仓库根**，成为主体 |
| 遗留目录 `L-Or-al_Hackathon-main/` | 已删除（内容已取出） |
| 启动包脚手架 `contracts/ docs/*.md src/ tests/ fixtures/` | **已删除**（属旧路线产物） |
| 迁移后冒烟 | ✅ 通过：数据域加载正常，`/analyze` 主链路可跑 |

**迁移后顶层结构**

```
apps/web/            React + Vite + TS 前端（模块：capture / profile / warning / vision）
services/api/        FastAPI 后端（qra2 / scentmap / recognition / ingredient / orchestration）
data/seed/           运行时数据（allergens 71 / perfumes 21 / families 7 / ige 11 / config）
data/raw/            原始数据（法规 HTML、SCCS PDF、数据集抽样）
scripts/             数据管线（clean_data / build_allergens_v2 / build_perfumes_v2 …）
docs/                本目录（改进清单 + 归档）
package.json         npm workspaces 根
```

**路径依赖已确认无需改动**：`services/api/app/core/config.py` 的 `parents[4]` 与
`scripts/*.py` 的 `parent.parent` **在原目录与迁移后都指向同一个仓库根**，冒烟验证通过。

---

## 0.1 进度快照

> 每次迭代后更新本节。✅ 已完成 ｜ 🔄 进行中 ｜ ⬜ 未开始

| 批次 | 范围 | 状态 | 结果 |
| --- | --- | --- | --- |
| 迁移 | 现有实现入库、旧脚手架清理 | ✅ 已完成 | 提交 `dc9a0ac`（另一仓库） |
| **第 1 批** | **P0-1 / P0-2 / 降级上报 / 回归测试** | ✅ **已完成** | 见下「第 1 批交付记录」（另一仓库；本副本已等价落地） |
| **第 2 批** | **P0-3 人群分级判据 + P0-4 空集合默认色 + 加载期校验 + ige 污染** | ✅ **已完成（`unbounded/`）** | 见下「第 2 批交付记录」；测试 36 → 70；浓度维分化待第 3 批 P1-1 |
| 第 3 批 | 数据诚实化（P1-1 ~ P1-4） | ⬜ 未开始 | 工作量中心（含 P1-2 幻影解析） |
| 第 4 批 | 对外形状契约收敛（P1-5） | ⬜ 未开始 | 前端类型改自动生成 |
| 第 5 批 | 前端拆页 / 三模式切换 / 免责声明 | ⬜ 未开始 | 依赖第 4 批契约 |
| 第 6 批 | 工程可复现（安装路径、依赖固化、启动文档） | ⬜ 未开始 | 建议提前穿插 |

### 第 1 批交付记录（本次）

**修复内容**

| 编号 | 问题 | 修复 |
| --- | --- | --- |
| P0-1 | `_pyramid` 只认对象数组，字符串数组抛 `AttributeError` 后被静默吞掉 → 20/21 款香水可视化空壳 | 新增 `_pyramid_note()` 归一化函数，同时接受 `str` / `dict`；单条（非列表）也容错；非字符串/字典项与空名跳过 |
| P0-1 附带 | 英文音符香调推断全错（关键词表只有中文）→ `Lavender`→oriental、`Rose`→woody，金字塔色点系统性显示错色 | 关键词表扩到中英两组、中文优先；新增 `_norm_name()` 归一化 + `infer_family_from_name()`；**同族内具体词先于泛词**（保证 `Orange Blossom`→floral 不被 `orange`→citrus 截胡） |
| P0-1 附带 | 文案生成整段被 `if product:` 包住 → 手动输入有 families 但文案是空串；且缺维度时会拼出「以**为主的**作品，**。」 | 文案生成移出条件分支（手动输入也用 `"手动输入成分表"` 作名）；`synesthesia_template` 对香调/雷达/金字塔/情绪逐项做缺失防御；品牌为空时不再留孤立间隔号 |
| P0-2 | `_manual_families` 列表推导引用未定义的 `c` → 手动输入可视化 100% 崩溃 | 改为显式循环取值；并改用浓度加权（避免微量成分与主成分等权） |
| 降级上报 | `except Exception` 静默兜底，故障不可观测 | `VisionReport` 新增 `degraded` / `degrade_reason`；构建失败与"构建成功但三要素全空"两种情况都置位并给出原因 |
| 前端同步 | 前端无法区分"空壳"与"真的没有" | `api-types.ts` 补两字段；`VisionView` 增加降级提示卡；`App` 结果区增加 `· 可视化降级` 标记 |

**验证结果**

| 验收项 | 修复前 | 修复后 |
| --- | --- | --- |
| 可视化完整的香水数 | 1 / 21 | **21 / 21** |
| 手动输入成分表 | 100% 抛 `NameError`（被吞） | 正常出 families / palette / radar / 文案 |
| 手动输入文案 | 空串 / 病句 | 完整通顺（如「是一支以柑橘调、花香调为主的作品」） |
| 金字塔英文音符香调 | 全部错（默认兜底族） | 正确（`Lavender`→fougere、`Orange Blossom`→floral、`Sea Notes`→aquatic） |
| 降级可观测 | 不可观测（HTTP 仍 200） | `degraded=true` + `degrade_reason`，前端可见 |
| 后端测试 | 32 条通过（但漏掉了以上全部问题） | **55 条通过**（新增 23 条针对性回归） |

**新增回归测试（防止复发）**

- `test_pyramid_accepts_both_str_and_dict_notes`、`test_pyramid_tolerates_malformed_notes`
- `test_english_note_family_inference`（10 组参数化）、`test_family_inference_falls_back_to_none_when_unknown`
- `test_synesthesia_template_no_broken_sentence_when_pyramid_empty`
- `test_vision_non_empty_for_every_real_perfume`（全库扫描，不再只测金标算例）
- `test_vision_families_all_have_rules`
- `test_analyze_real_perfume_vision_is_complete`、`test_analyze_manual_ingredients_vision_not_degraded`
- `test_vision_degraded_flag_is_observable`（monkeypatch 注入故障）
- `test_analyze_manual_ingredients` 补 `synesthesia_text` 非空断言

**未纳入本批（仍待办）**：`repository` 加载期 schema 校验（把形状问题提前到启动时报错）、P0-3 人群分级、P0-4 空集合默认色。

---

### 第 2 批交付记录（2026-09-18 · 落地于本工作区 `unbounded/`）

> 第 1 批的等价修复（P0-1/P0-2/降级上报/文案防御 + 前端同步）已随本批在本副本一并落地。
> 本副本验证基线：修复前 36 passed（但含 P0-1/P0-2 全部缺陷），修复后 **70 passed**。

**修复内容**

| 编号 | 问题 | 修复 |
| --- | --- | --- |
| P0-3 | 闸门1 判据不消费 `percentile_policy`（配置死字段） | 判据改为：**红线** = P99 余量 < 1（全人群一致，承袭文档黄金算例）；**黄线** = 人群判定线 `m_dec = AEL / CEL[policy] / T_pop` < 1（healthy→P90，脆弱人群→P99）。职责分离：`T_pop` 管余量阈值、`policy` 管保护到哪条尾部；黄灯话术携带判定线语义 |
| P0-3 附带 | 失嗅人群氧化等级不参与综合判定 | `anosmic` 人群下氧化等级并入 `strictest()`（嗅觉替代预警：无法靠气味发现变质，取最严口径） |
| P0-4 | `strictest()` 空集合返回 green | 空 findings → **yellow** + 摘要「数据不足，无法判定……这不等于安全」；真实用例 `ralph-lauren-polo-blue-edt`（成分表为空）回归 |
| 加载期校验 | 数据形状问题运行时才静默暴露 | `repository._validate_seed()`：allergens/perfumes/pyramid 形状检查 → `data_issues`（`/admin/stats` 暴露计数；`DATA_STRICT=1` 启动即抛错）。默认 warn 不炸（演示日稳健性优先，与原方案"启动即炸"的取舍已注释说明） |
| ige 污染（P2-3-3） | `ige_materials.json` 含表头污染行 `原料类型` | `clean_data.py` 通用表头跳过 + repository 加载期双保险过滤；重生成 11 → **10 条**（已验证无污染） |
| config 注释矛盾（P2-2-4） | 敏感肌注释写"阈值收紧50%"，实际 2.0×1.5=3.0（放大） | 注释改为「判定余量要求 ×3（α=2.0×β=1.5）」 |
| 前端同步 | 空壳不可见 | `api-types.ts` + `degraded/degrade_reason`；`VisionView` 降级提示卡（降级时隐藏情绪板）；`App` 结果页「· 可视化降级」标记；金字塔色点兜底改用主香调色 |

**人群分化实验结果**（`scripts/check_population_divergence.py`，验收前置）

| 情境 | 结果 |
| --- | --- |
| 无氧化输入（21 款 × 5 人群） | QRA 结论**全同**（0 分歧）：成分最小基线 m99 ≈ 27，远离敏感肌分化窗口——受 P1-1 群体均值浓度限制，机制无罪、数据受限 |
| 机制探针（手动 18% 柠檬烯） | healthy **green** / sensitive **red**（m99=0.67 < 1）/ rhinitis green（m99=1.67）→ **policy + T_pop 机制验证通过** |
| 开封 90 天 | **11+ 款真实产品** anosmic 与其他人群真实分化（green vs red）→ 失嗅×氧化并入生效 |
| 孕期 | Lilial 红灯为全人群一致（EU 2022 全面禁用，非孕期专属），孕期仅多专属提示——诚实口径 |

**新发现（重要，已固化进测试注释）**：文档四档判据的「QRA 黄灯窗口」（P90<1 且 P99≥1）在连续分布下
**数学不可达**（CEL_P90 < CEL_P99 恒成立 ⟹ m90<1 必然 m99<1 → 先触红线）。实际黄灯由三条路径提供：
IFRA 接近限值（浓度 ≥ 限值 80%）、NESIL 数据不足（谨慎黄，如 valentino-donna）、空成分表（P0-4）。

**验证**：后端 36 → **70 passed**（新增 34 条回归：金字塔双形状/畸形容错/中英推断 15 组参数化/
全库 21 款可视化非空/手动输入不降级且文案非空/注入故障可观测/判据消费 policy 分化/黄灯两路径/
空表不绿/加载校验）；前端 `npm run build` ✓。

**未纳入本批**：repository 校验目前覆盖形状而非数值语义（如 NESIL 量纲）；浓度维人群分化需第 3 批 P1-1
的 per-product 浓度数据后重跑分化脚本验证。

---

## 1. 现状基线（迁移时实测）

### 1.1 已经能用的部分

| 能力 | 实测状态 |
| --- | --- |
| QRA2 点估计 | ✅ `CEL = 5% × 0.5 × 100 × 2 × 1.0 = 5.0` 精确复现 |
| 蒙特卡洛 P50/P90/P99 | ✅ 固定种子可复算；`P50=3.2695 / P90=7.341 / P99=13.8465`（柠檬烯 5%） |
| 浓度线性缩放 | ✅ `P90(10%) = 2 × P90(5%)` |
| 三闸门取严 | ✅ QRA / IFRA / 禁用成分，`strictest()` 逻辑正确 |
| 数据不足不静默降级 | ✅ 未知成分进 `data_insufficient` |
| 成分匹配 | ✅ INCI / CAS / 中文名 / 别名 / 模糊，归一化处理到位 |
| 香水文本搜索 | ✅ 18/18 真实查询命中（含 `Idole` → `Idôle` 模糊匹配） |
| HTTP 层 | ✅ 统一错误信封 + `request_id` + `meta.engine/models` |
| 后端测试 | ✅ 复现 32/32 条断言通过 |
| 数据真实性 | ✅ 71 条 CAS 全唯一、零 null，抽查 12 条全部准确 |
| 前端诚实性 | ✅ 无写死假数据，`mock_mode` 由后端上报并在 UI 标注 |

### 1.2 实测暴露的问题（下面第 3 节逐条给方案）

**跑一次就能看到的三个致命项**：

| 编号 | 现象 | 实测证据 |
| --- | --- | --- |
| P0-1 | **20/21 款香水的可视化返回空壳** | 除 `golden-limonene` 外，全部 `families=[] palette=[] pyramid={}`，接口仍返回 200 |
| P0-2 | **手动输入成分表必定崩溃** | `{'d-Limonene': 6.0}` → 可视化域 `NameError: name 'c' is not defined`，被静默吞掉 |
| P0-3 | **"人群差异化"未生效** | 5 人群 × 21 款 = 105 次评估，结论矩阵**完全相同**（green 16 / yellow 1 / red 4） |

**再加一条安全默认值问题**：

| 编号 | 现象 |
| --- | --- |
| P0-4 | `strictest()` 在 `findings` 为空时返回 **green** —— 一个成分都没识别出来时，综合结论是"安全" |

---

## 2. 目标状态

以交付 **万象Aura P0 闭环**为目标：

```
输入香水名 / 成分表
  → 匹配致敏原
  → QRA2 点估计（AEL / CEL / safety_ratio）
  → IFRA 限量硬约束闸门
  → 氧化 D
  → 人群差异化分级
  → 输出报告 JSON + VisualSpec
  → 前端输入页 / 结果页展示 + 免责声明
```

**统一风险方向（全系统对外唯一口径）**

```
safety_ratio = AEL / CEL          # 越大越安全
safety_ratio >= 1  安全，< 1 风险
```

> 现有实现的 `margin = AEL / CEL / T_pop` 与上式**方向一致**，属于同一语义的变体，
> 不是"写反了"。改造重点是**拆分与重命名**，不是翻转。

---

## 3. 改进项清单

优先级：**P0 = 不修就无法交付**｜**P1 = 影响可用性与可信度**｜**P2 = 工程债**

### 3.1 P0-1　香调金字塔两种数据形状不兼容，导致可视化整片失效　✅ 已修复（第 1 批）

| 项 | 内容 |
| --- | --- |
| 位置 | `services/api/app/modules/scentmap/service.py:81-89`（`_pyramid`） |
| 根因 | 代码把所有音符当对象读 `n.get("name")`；但 20 款真实香水的 `pyramid` 是**字符串数组** |
| 数据对照 | `golden-limonene`: `[{"name":"柠檬烯","weight":0.6}]` vs `ysl-libre-edp`: `["Lavender","Mandarin Orange"]` |
| 被掩盖的原因 | `services/api/app/modules/orchestration/analyzer.py:114` 的 `except Exception:` 静默兜底，返回空 `VisionReport`，HTTP 仍 200 |
| 测试漏掉的原因 | `tests/test_domains.py:38` 只覆盖 `golden-limonene`；`tests/test_api.py` 中 4 条真实香水用例**只断言 `risk`，不断言 `vision` 内容**；渲染用的 `synesthesia_text` 走独立规则模板，不看 `families`，把空壳遮住了 |
| 改进方案 | ① `_pyramid` 同时接受 `str` 与 `dict`（字符串 → `{name, weight:1.0, family:按关键词推断}`）；② 更彻底的做法：在 `repository` 加载期用 Pydantic 模型校验 `perfumes.json`，把两种形状收敛成一种，**让这类问题在启动时就炸出来而不是运行时静默** |
| 验收 | 21/21 款香水的 `/analyze` 返回非空 `families` / `palette` / `radar` / `pyramid` |

### 3.2 P0-2　手动输入成分表必定崩溃　✅ 已修复（第 1 批）

| 项 | 内容 |
| --- | --- |
| 位置 | `services/api/app/modules/orchestration/analyzer.py:118-127`（`_manual_families`） |
| 根因 | 列表推导里用了未定义的 `c`（第 56 行的 `c` 属于另一个循环作用域） |
| 影响 | 用户"识别不到 → 手动粘贴成分表"这条**最现实的兜底路径**，可视化输出恒为空 |
| 改进方案 | 修正为 `(self.repo.find_allergen(n), req.product.manual_ingredients[n], n)`；并给该方法补一条单元测试 |
| 验收 | `{'d-Limonene': 5.0, 'Linalool': 2.0}` 输入下 `families` 非空、文案含香调信息 |

### 3.3 P0-3　人群差异化未生效，但文档已把它当成卖点　✅ 已修复（第 2 批）

| 项 | 内容 |
| --- | --- |
| 位置 | `services/api/app/modules/qra2/engine.py:104-109` |
| 根因 | 判据写死 `m99 < 1.0 → red / m90 < 1.0 → yellow`，**判据里没有 `policy` 变量**；`config.json` 的 `percentile_policy`（healthy→P90，其余→P99）只在返回时作为 `decision_percentile` 字段回显，**是死配置** |
| 叠加原因 | `T_pop = α×β` 只能改**黄灯**门槛，改不了红/绿分界；实测 20 款真实香水的最小 m99 为 **9.158**，没有一款落进敏感肌的分化窗口 `(1, 3)` |
| 实测 | 5 人群结论矩阵完全一致；README 承诺的「最脆弱的人用最保守的分位线保护」不成立 |
| 假信心测试 | `tests/test_qra2.py:82-93` 断言的是配置常量 `T_pop == 3.0` 与一个无论怎么改都红的输入，**没有一条断言能验证人群产生了更严的判定** |
| 改进方案 | ① 让判据真的消费 `policy`：按人群选 `m90` 或 `m99` 作为判定分位线；② 明确 `T_pop` 与分位线的职责边界（一个调门槛、一个调分位），避免两者语义重叠；③ **先用真实数据验证 5 人群能产生分歧**，再对外声明该能力 |
| 验收 | 存在至少「健康成人=green / 敏感肌=yellow」的真实香水用例，并有参数化测试固定住它 |

### 3.4 P0-4　`strictest()` 空集合默认返回绿灯　✅ 已修复（第 2 批）

| 项 | 内容 |
| --- | --- |
| 位置 | `services/api/app/modules/qra2/engine.py:182-183` |
| 影响 | 一个成分都识别不出来 → 综合结论 `green`（安全） |
| 改进方案 | 空集合返回 `yellow` + `"数据不足，无法判定"`，或返回 `None` 强制调用方显式处理 |
| 验收 | 空成分输入的综合结论不是 green |

### 3.5 P1-1　浓度数据在香水之间是常数，不是实测

| 项 | 内容 |
| --- | --- |
| 实测 | 19 个出现的致敏原中，**18 个在所有香水里是同一个 `typical_pct`**；唯一有区分的是 `d-Limonene` |
| 证据 | `Butylphenyl Methylpropional` 在所有含它的香水里都是 `0.40268`；`Linalool` 恒为 `0.22627` |
| 元数据自证 | `basis` 字段写着 `lim2018_107perfumes_women_mean` —— 那是 **107 款女性香水的群体均值**，被当成每一款具体香水的实测浓度 |
| 后果 | 21 款香水之间的风险差异**只来自"成分清单里有没有这个成分"，不来自含量**；"按产品精确评估"的立论基础不成立 |
| 改进方案 | ① 引入真实 per-product 浓度来源（成分表标注、实测文献、品牌公开数据）替代群体均值；② 无法获得时，**改成"浓度未知 → 走区间/上界假设"并显式标注**，不要用伪精确的单一常数；③ 把 `basis` 的语义在字段名上体现出来（如 `conc_basis: population_mean`） |
| 验收 | 同一成分在不同香水上的浓度要么有真实出处，要么被标为"未知/估计" |

### 3.6 P1-2　毒性数据存在自动化编造机制且未清理

| 项 | 内容 |
| --- | --- |
| 编造机制 | `scripts/clean_data.py:40` 写死 `DEMO_ESTIMATE_NESIL = {"strong":1000.0, "medium":5000.0, "low":10000.0}`，按 tier 发值 |
| 实测 | 71 条中 **36 条 `nesil_source="demo_estimate"`**，只有 35 条有文献出处 |
| 幻影解析 | `scripts/build_allergens_v2.py` docstring 自称"EUR-Lex 官方 HTML 解析"，但 `import re`、`RAW` **两个符号均未被引用**；341 KB 的 `eu_2023_1545.html` 与 4.35 MB 的 `sccs_1459_11.pdf` **没有任何脚本引用**；~560 个毒理数字是手敲字面量 |
| 静默源覆盖 | 产物与自述来源矛盾：**Geraniol 落盘 11800，文件头写的是 11000** |
| `human_noel` 存疑 | 与 NESIL 高度镜像（戊基肉桂醛 23600/23622、香茅醇 29500/29525、肉桂醛 591/591），作为独立"临床闸门"很可能是**自证循环** |
| 改进方案 | ① 把 `demo_estimate` 值**移出判定路径**（只能用于演示，不得进入闸门）；② 逐条补文献出处或显式标 `null`；③ 修正 docstring 与实际行为不符的表述；④ `human_noel` 单独标注来源，若为派生值则不得作为独立闸门 |
| 验收 | 每条 NESIL 都能追到可核验出处，或有明确"无数据"标记；不存在按标签发值的路径 |

### 3.7 P1-3　氧化模块的输入基本是空的

| 项 | 内容 |
| --- | --- |
| 实测 | `oxidation_prone=True` 共 15 条，但 `k_ox_per_day` **只有 2 条有值**（柠檬烯 0.03、芳樟醇 0.0175） |
| 模型疑点 | `D = 1 − exp(−k_eff·t)`，参数量纲是"每天"，**公式却没有初始浓度项** → 7 天避光即 D=0.19（黄灯边缘）、30 天即 D=0.50（红灯） |
| 改进方案 | ① 补齐 15 条氧化速率；② 明确 D 的物理定义（是"已氧化比例"还是别的），据此决定要不要引入初始浓度与阈值重标定 |
| 验收 | 三个月阴凉避光的柠檬烯 D 落在合理区间且等级为低 |

### 3.8 P1-4　IFRA 硬约束无法证实

| 项 | 内容 |
| --- | --- |
| 实测 | `ifra_limit_pct` 仅 24/71 有值；来源为 scentspiracy **二手汇编**；**全库没有 IFRA 修订版号** |
| 改进方案 | 换官方 per-material 页，补修订版号，并区分 `leave_on` / `rinse_off` 分档 |
| 验收 | 每条限量都能追到官方出处与修订版号 |

### 3.9 P1-5　对外报告形状与可视化契约需要收敛

| 项 | 内容 |
| --- | --- |
| 现状 | 对外是 `Envelope{data:{product, recognition_channel, risk, vision}, meta}`；风险字段用 `overall_level / margin_p50..99 / gate`；可视化是 `palette[] / radar{fresh,sweet,rich,warm,lasting} / motion{}` |
| 目标 | 报告 JSON 与 VisualSpec 需要能直接驱动前端输入页/结果页，并包含：主色、辅色、动态图形、五维雷达、文字描述、致敏原明细、氧化 D、行动建议、免责声明 |
| 改进方案 | ① 显式定义一份**对外报告 schema**（建议直接用 Pydantic 模型，并可导出 `/openapi.json`）；② 前端类型改为**从 openapi 生成**，而不是手工镜像 `api-types.ts` |
| 验收 | 前端零手写类型；后端改字段能立刻暴露所有受影响处 |

### 3.10 P2-1　前端工程债

| # | 项 | 位置 |
| --- | --- | --- |
| 1 | `App.tsx` 单组件 13 个 `useState` | `apps/web/src/app/App.tsx` |
| 2 | `quickCase` 连续 `setState` 后立刻 `analyze()`，读到闭包旧值 | 同上 |
| 3 | `ErrorBanner` 的「重试」被接成 `setError("")`，点击不重发 | `apps/web/src/modules/capture/CapturePanel.tsx` |
| 4 | 手动成分输入只支持 `INCI: 浓度%` 逐行格式，无法粘贴真实 INCI 串 | 同上 |
| 5 | 前端零测试；无 ESLint / Prettier | 全仓库 |
| 6 | 加载文案声称「蒙特卡洛 N=10000」，前端无法判断后端是否 mock | `App.tsx` |
| 7 | `README` 称「ECharts 图表均带 aria-label」，实际粒子 canvas 为 `aria-hidden` | `README.md` |
| 8 | `--color-ink-3 #6b7280` 在 `#0a0a0a` 上约 4.4:1，大量用于小字 | `apps/web/src/index.css` |

### 3.11 P2-2　后端工程债

| # | 项 | 位置 |
| --- | --- | --- |
| 1 | `api-types.ts` 手工镜像 Pydantic，双份事实源无校验 | `services/api/app/schemas/api.py:3-4` 自述 |
| 2 | `IngRef` 是 `tuple` 子类，靠位置解包三元组，加字段即静默错位 | `engine.py:41-42` |
| 3 | `clinical_noel` 71 条全 null，字段名存实亡 | `schemas/api.py` / 数据 |
| 4 | `config.json` 注释与代码相互矛盾：注释写"阈值收缩 50%"，实际 `2.0×1.5 = 3.0`（放大） | `data/seed/config.json:42` |
| 5 | 单位多套口径并存：`config.json` 自述 CEL 为 `μg/cm²/day`，同对象 `amount_density_m` 写 `mg/cm²`；雷达概念存在 0–1 / 0–10 / 0–100 三套量纲 | `config.json` |
| 6 | 无 DB / 无鉴权 / 无 CI / 无 lint | 全仓库 |
| 7 | 无 `uv`、无 `fastapi` 的环境**跑不起来**，README 只有 `uv sync` 一条路 | `README.md` |

### 3.12 P2-3　目录与文档债

| # | 项 |
| --- | --- |
| 1 | `data/raw/hf_perfume.json` 实为 HuggingFace 数据集检索列表（含动漫调香师图集），与本项目无关 |
| 2 | `data/raw/fragdb_api.json` / `fragdb_tree.json` 是仓库元数据；`fragdb_*.csv` 各仅 10 行（抽样非全量） |
| 3 | `data/seed/ige_materials.json` 含 1 行表头污染数据（`name_zh: "原料类型"`）→ ✅ 已修复（第 2 批，11→10 条，重生成验证） |
| 4 | `data/seed/families.json` 有 `aquatic` 无 `chypre`（目前无香水用到 chypre，暂不影响，但需明确香调集合口径） |
| 5 | `data/seed/ingredients.json`（180 条香材词典）**无 CAS**，与 `allergens.json` 同名易混 |
| 6 | `scripts/clean_data.py` 依赖的 `数据层/` 目录（`表格26种致敏香料.xlsx`、`IgE致敏原表格.xlsx`）**已丢失** → 26 条基线不可复现 |
| 7 | `docs/` 下原说明文档（`context.md` / `data-format.md` / `workflow.md` / `enums.md`）与 `docs/策划案V1.docx` 已随迁移删除，**如需要请从 git 历史取回** |

---

## 4. 迭代路线（建议）

> 原则：**先让自己能信，再让别人能用**。先把"跑起来 + 不说假话"做扎实，再谈对外形状。

### 第 1 步　工程可复现（半天）

- [ ] 提供不依赖 `uv` 的安装路径，或把 `.venv` 创建纳入脚本
- [ ] 补 `requirements.txt` / 固化依赖，确保 `pytest` 能一条命令跑起来
- [ ] 补 `docs/` 说明：如何启动后端、如何启动前端、如何跑测试、数据从哪来

### 第 2 步　修掉三个致命项 + 一条安全默认值（1 天）

- [x] P0-1 `_pyramid` 兼容 `str` / `dict`（第 1 批已完成；`repository` 加载期 schema 校验仍待办）
- [x] P0-2 修 `_manual_families` 的 `NameError`（第 1 批已完成）
- [x] **把 `except Exception` 的降级上报出来**（`vision.degraded` + `degrade_reason`，第 1 批已完成）
- [x] 补测试：真实香水可视化非空、手动输入非空（第 1 批已完成，测试数 32 → 55）
- [x] P0-3 让判据真的消费 `percentile_policy`，并用真实数据验证 5 人群能分化（第 2 批：机制探针分化 + 失嗅×氧化真实分化 11+ 款；浓度维分化待 P1-1）
- [x] P0-4 `strictest()` 空集合不再返回 green（第 2 批：yellow + 数据不足话术）
- [x] 补测试：5 人群分歧、空输入不绿（第 2 批，累计 70 passed）
- [x] `repository` 加载期 schema 校验（第 2 批：`_validate_seed` → `data_issues`，`DATA_STRICT=1` 可选启动即炸）


### 第 3 步　数据诚实化（1.5 天）

- [ ] `demo_estimate` 的 36 条 NESIL 移出判定路径或补真实出处
- [ ] 核查 `human_noel` 是否 NESIL 镜像；是则降级为"派生值"不得作独立闸门
- [ ] 浓度数据：真实 per-product 来源，或显式改为"未知 + 上界假设"
- [ ] 补 15 条氧化速率；明确 D 的定义与阈值标定
- [ ] 换 IFRA 官方 per-material 页，补修订版号与 `leave_on/rinse_off` 分档

### 第 4 步　对外形状与前端（1.5 天）

- [ ] 定义对外报告 schema（Pydantic 模型），前端类型改为从 openapi 生成
- [ ] 前端拆出输入页 / 结果页；补三种模式切换（普通 / 敏感 / 失嗅）
- [ ] 结果页要素：风险色标、致敏原列表、氧化 D、五维雷达、通感文字、行动建议
- [ ] 免责声明可见
- [ ] 香调 → 视觉映射改成数据驱动（不再组件内硬编码颜色）

### 第 5 步　端到端与验收（1 天）

- [ ] 跑通一个真实香水端到端（输入 → 报告 → 渲染）
- [ ] 固化黄金算例与真实香水回归样例
- [ ] 清理 `data/raw` 噪音文件；`docs/` 补齐口径文档

---

## 5. 验收清单

### 5.1 计算正确性

- [ ] 柠檬烯 5% 点估计 CEL ≈ 5.0
- [ ] `AEL=100` → `safety_ratio = 20`，绿灯
- [ ] `AEL=10`、`CEL_P99=13.2` → `safety_ratio ≈ 0.76`，红灯
- [ ] 氧化 D：柠檬烯 3 个月阴凉避光落在合理区间且等级为低
- [ ] 固定种子下蒙特卡洛结果可复算

### 5.2 功能可用性

- [x] **21/21 款香水可视化非空**（原 1/21）— 第 1 批已修复并回归
- [x] **手动输入成分表可视化非空**（原 100% 崩溃）— 第 1 批已修复并回归
- [x] **降级可观测**（原静默返回空壳）— 第 1 批已修复并回归
- [x] **5 人群在同一香水上能产生分歧** — 第 2 批：两机制已验证（P99×T_pop 判据探针分化；失嗅×氧化 11+ 款真实分化）；QRA 浓度维分化受 P1-1 群体均值浓度限制，待第 3 批
- [x] 空成分输入的综合结论不是 green（当前是 green）— 第 2 批：yellow + 「数据不足，不等于安全」
- [ ] 输入页可输入香水名或粘贴成分表（当前手动输入只支持 `INCI: 浓度%` 逐行格式）
- [ ] 结果页展示色标 / 致敏原 / 氧化 D / 雷达图 / 文字描述
- [ ] 三种模式可切换，失嗅模式描述更详细（当前 mode 仅来自后端，无前端切换）
- [ ] 免责声明可见（已具备）

### 5.3 数据可信度

- [ ] 每条 NESIL / NOEL / IFRA 限量可追到出处
- [ ] 不存在按 tier 发值的毒性数据路径
- [ ] 浓度数据的来源语义在字段名上如实体现
- [ ] 71 条 CAS 保持全唯一（已达标，回归守卫）

### 5.4 第 1 批回归守卫（已固化在测试里）

- [x] 金字塔 `str` / `dict` 两种形状都能解析，畸形输入不抛错
- [x] 英文音符香调推断正确（含 `Orange Blossom` 不被 `orange` 截胡）
- [x] 缺金字塔时文案不出现断句/病句
- [x] 全库 21 款香水可视化非空（不再只测金标算例）
- [x] 手动输入可视化不降级且文案非空
- [x] 注入故障时 `degraded=true` 且原因可读

---

## 6. 已知风险与注意事项

1. **测试全绿 ≠ 功能可用**。迁移时复现 32/32 条断言全过，但 20/21 款香水可视化是空壳、手动输入必崩。原因是测试只覆盖黄金算例与自选极端输入，且大量断言只看 `risk` 不看 `vision`。
   → **后续每条新测试都必须绑定"用户真会输入的东西"**。
2. **静默兜底会掩盖故障**。`except Exception` 的错误隔离设计是对的，但必须把降级上报出来，否则故障不可观测。
3. **不要用"配置里写了"当成"功能实现了"**。`percentile_policy` 就是典型：配置、字段、README 三处都声称有，判据里根本没有。
4. **数据来源丢失不可逆**。`数据层/` 目录已不在，`clean_data.py` 无法重跑，26 条基线只能以现有产物为准。

---

## 7. 参考：迁移时的独立评审结论

历史实现的三句话定性：

> **引擎是真货，管线是坏的，承诺是虚的。**

- **可保留**：QRA2 计算内核（分布 + 分位 + 三闸门）、`Repository` 匹配层、错误信封、21 款真实香水的 INCI 与香调数据、EU 2023/1545 合规字段、35 条有文献出处的毒理值。
- **必须修（小时级）**：3.1 / 3.2 / 3.4 三条 + 降级上报。
- **必须重做（天级）**：3.3 人群分级判据、3.5 浓度数据、3.6 毒性数据清理。

---

## 8. aura/web 新前端逐条落实记录（2026-10-05）

> 背景：演示前端已迁移至新建的 **`aura/web/`**（React 19 + Vite 7 + Tailwind v4，设计系统「墨与光」）。
> 本节把上述清单逐条对照到新前端：适用的当场修（标 ✅ 本轮），设计之初已满足的标 ⭐，
> 属旧后端/数据管线或后续批次的标 ⬜ 并注明去处。旧 `unbounded/apps/web` 保留为后端联调参考。

| 清单条目 | 新前端对应处理 |
| --- | --- |
| P0-1 金字塔双形状 / P0-2 手动输入崩溃 / 降级上报 | ⬜ 属旧后端 scentmap/analyzer（第 1、2 批已修于 `unbounded/`）；新前端接后端时以契约测试覆盖 |
| P0-3 人群差异化判据 | ⭐ 新前端演示引擎 `evaluate()` 即按人群改写判定（敏感肌 α 收紧+P99、孕期禁用直判、失嗅氧化并入、鼻炎加注），端到端用例已验证（健康×航海日=绿 / 敏感×晨光鸢尾=红） |
| P0-4 空集合不绿 | ⭐ 演示引擎无「无理由即绿」路径；手动解析未命中项显式按「数据不足」黄灯处理、不静默放行（本轮在手动通道文案中固化） |
| P1-1 浓度群体均值 | ✅ 本轮：报告成分表头改「浓度（典型值）」+ 表下诚实声明（典型值≠per-product 实测，正式版接实测并标出处）⬜ 实测数据源属后端第 3 批 |
| P1-2 毒性数据出处 | ⭐ 成分明细每行带证据等级标签（文献值/演示估计/数据不足）；免责声明固定展示三源交叉校验 ⬜ 逐条出处属后端第 3 批 |
| P1-3 氧化速率与阈值 | ✅ 本轮（前一轮）：k 重标定 0.0013/0.0023/0.0045，修复「30 天即红灯」量纲问题；验收「3 个月阴凉 D≈0.12 判低」通过 ⬜ 15 条成分级 k_ox 属后端第 3 批 |
| P1-4 IFRA 版号 | ⭐ 免责声明已含「IFRA 第 51 版」口径 ⬜ per-material 官方限量与版号属后端第 3 批 |
| P1-5 契约收敛 / 类型自动生成 | ⬜ 新前端暂无后端调用；接入时直接以 openapi 生成 `api-types`，不再手写镜像 |
| 5.2 输入页粘贴成分表（原只支持逐行 `INCI: 浓度%`） | ✅ 本轮：手动通道支持真实 INCI 串（逗号/顿号/分号/换行分隔均可，浓度可选），内置解析器 + 演示致敏原匹配（10 条）+ 命中统计 |
| 5.2 结果页要素（含**行动建议**） | ✅ 本轮：判定横幅新增逐灯色「行动建议」（停用/减半/正常 + 具体措施），其余要素此前已齐 |
| 5.2 三模式切换 / 免责声明可见 | ⭐ 顶栏三模式（token 覆盖 + 失嗅字号放大）；报告页脚免责声明常驻 |
| 第 4 批「香调→视觉映射数据驱动」 | ⭐ 十二香型色值/场景/粒子形状全部在 `lib/aura.ts` 数据层，组件零硬编码颜色 |
| P2-1-2 quickCase 闭包旧值 | ⭐ 新前端演示案例为纯导航链接，无异步 setState 竞态 |
| P2-1-3 重试按钮不重发 | ⬜ 新前端暂无失败横幅（无 API 调用）；接后端时一并实现 |
| P2-1-6 前端无法判断 mock | ⭐ 报告/显影页均明示「演示样本 / 黄金算例示意」口径 |
| P2-1-7 canvas 无文字替代 | ✅ 本轮：显影页新增 sr-only 粒子画面文字摘要（读屏可感知组成比例与动态） |
| P2-1-8 小字对比度 | ⭐ 新 token `--ink-soft` 对瓷白底 ≈ 8:1 |
| P2-2-5 单位多套口径 | ✅ 本轮：分位条标注 μg/cm²/day；雷达统一 0-10 量纲 |
| P2-3-4 families 缺 chypre | ⭐ 新前端为完整十二香型（含 chypre/leather/fruity/green/aromatic） |
| 第 6 批 工程可复现 | ✅ 本轮：新建 `aura/web/README.md`（启动/构建/页面职责/数据口径/设计系统/目录） |
| 环境备注 | ⚠️ macOS 上 web-replicate `relink-node-modules.sh` 的 `mv -T` 为 GNU 语法会静默失败 → 需先手动 `mv "$T/node_modules" master` 落位再跑 relink（已踩过并记录） |

**本轮代码改动**：`aura.ts`（advice / parseManualIngredients / matchManualIngredient / 分位单位）、`AnalyzeFlow.tsx`（手动通道真实解析）、`Report.tsx`（行动建议 + 典型值标注 + 诚实声明）、`Vision.tsx`（sr-only 摘要）、`README.md`（新建）。

### 8.1 真实数据层接入（2026-10-05 第二轮）

数据层新增三份文件（12款经典香水分析.docx / IFRA 51st Cat4 清单.xlsx / 三个 CAS 词典），已通过
`aura/web/scripts/build_data.py`（纯标准库，幂等）接入前端：

| 产出 | 内容 | 验收 |
| --- | --- | --- |
| `src/data/perfumes.json` | 12 款真实香水（品牌/香调映射/浓度/三层香材含逐材族推断/成分清单/品鉴关键词） | 12/12 款解析，香调映射全对（美食调/水生调等含「调」字后缀已兼容） |
| `src/data/ifra.json` | 限量 20（真 CAS+上限%）/ 禁用 9（CAS 碎片拼接修复）/ 天然精油 2 | 计数 20/9/2；铃兰醛 80-54-6、薄荷内酯（51修正案新增）在列 |
| `src/data/ingredients.json` | 160 条 CAS 词典（三源合并去重） | 160 条 |

**判定层升级为真实数据驱动**：禁用闸门/IFRA 闸门消费真实清单（手动输入带浓度即真实判定：
Eugenol 0.6% > 上限 0.5% 判红、Coumarin 0.3% < 1.6% 判绿、铃兰醛命中禁用直红）；
风险画像（萜烯/麝香/限值命中数）由真实成分清单推导；五维雷达由族先验按组成加权生成。

**管线踩坑记录**（复用价值）：① ElementTree 限定名必须 `{ns}tag` 大括号形式；
② xlsx sharedStrings 需 `t="s"` 索引解析（WPS 文件全部走共享字符串）；③ docx `<w:tab/>`
需替换为合成 `<w:t>\t</w:t>`（直接替换会被 w:t 提取丢弃）；④ 汇总表分隔符逐行混杂
（tab/双空格/单空格），取「首列序号 + 末列关键词」；⑤ 禁用表 CAS 被拆成 3 个数字单元格，按行拼接修复，
疑似笔误（如葵子麝香 120-58-1）按展示处理不做权威校验。

**端到端验收**（浏览器实测）：孕期×香奈儿五号一键直达黄灯（麝香临床理由，真实数据）；
手动输入四成分 红2黄1绿1 且判定理由逐条可见；显影页真我（果香花香）真实组成驱动；构建通过。

## 9. 阶段 2 · QRA2 预警引擎落地（2026-10-05，aura/web）

按路线图阶段 2 完成，落地为**前端 TypeScript 纯函数模块**（纯函数、零框架依赖、vitest 18/18 绿）：

| 模块 | 内容 |
| --- | --- |
| `src/lib/qra2/distributions.ts` | CEL 五参数概率化：用量 LogNormal(中位0.5,CV0.4)/面积 Tri(50,100,200)/频率离散{1:.5,2:.35,3:.15}/浓度 U(0.8c,1.2c)/吸收 Beta(20,2)；**拉丁超立方 N=10000 固定种子**；自实现 Acklam 正态分位、Lentz 不完全 Beta、二分 Beta 逆（无 scipy 依赖） |
| `src/lib/qra2/nesil.ts` | 22 种限值成分 NESIL 文献值表（提取自旧库 35 条 documented 之列，RIFM/Api2008 系）；SAF=100；demo 估计 ÷3 惩罚标 indicative |
| `src/lib/qra2/oxidation.ts` | D = 1−exp(−k25·Q10^((T−25)/10)·(1+L)·t)：Q10=1.8，环境 {阴凉15°C/L0, 室温25°C/L0.3, 高温35°C/L0.8}；标定点 3月阴凉 D≈0.09 / 14月室温 D≈0.62 / 14月高温 D≈0.91 |
| `src/lib/qra2/engine.ts` | 七步流水线：AEL=NESIL÷SAF → CEL 概率化 → 聚合暴露系数 → 分位判定（红线=P99余量<1 全人群；黄线=人群判定线 AEL/CEL[policy]/T_pop<1）→ 四闸门取最严（禁用>IFRA>临床>QRA2）→ 人群 T_pop/P90|P99 策略 |

**测试验收（18/18）**：黄金算例精确复现（CEL=5.0、AEL=100、比值20、绿灯）；固定种子逐位复算；分位保序/浓度线性/聚合系数线性；四闸门（禁用直红、Eugenol 0.6%红/0.45%八成黄、QRA2 P99红线）；数据不足绝不绿；**人群分化**（柠檬烯 20%：健康绿 vs 敏感肌非绿）；氧化标定值与单调性。

**UI 消费**：报告页概率化面板改为引擎实算（情景标注：黄金算例/文献典型值 0.8%/限值上限最保守）；成分明细行附 QRA2 实算余量；手动通道限量命中走引擎全量判定（AEL+P50/P90/P99+判定线余量+IFRA 闸门，如 Limonene 15% 触 Cat4 上限 15% 判红）；首页滑块 D 值由 Q10 模型统一计算。

**匹配桥接修复**：`Limonene` 此前无法命中限值表（表内中文名为 `d-柠檬烯`，单向包含失配）——以 NESIL 毒理表 zh 为桥接键双向匹配。

**下一步（阶段 3 可选）**：可视化引擎与 LLM 文案为纯前端已有；后端 FastAPI 化（openapi 契约、71 条致敏原全库、识别通道）按路线图阶段 4-5 推进。

## 10. 阶段 3 · 香味可视化系统细化（2026-10-05，aura/web）

按路线图阶段 3 完成，映射规则引擎独立为可测试模块（`src/lib/vision/`）：

| 交付 | 内容 |
| --- | --- |
| `vision/engine.ts` | 金字塔 → **VisualSpec** 纯函数：palette（主色=声明香调（v3 映射规则）/辅色=组成最高族/前中后调渐变）、分层数据、全局组成、情绪效价词表（v3 1.2.2 十二族全覆盖）、粒形标签；**降级隔离**（空金字塔/畸形输入 → degraded + 原因，不抛异常，预警链路不受影响）；分模式通感（失嗅=开场/中段/尾韵加长叙事） |
| `vision/engine.test.ts` | 9 条：全库 13 款非降级且要素齐全（对应旧 P0-1 的全库扫描教训）；颜色随主导香型正确变化；情绪/粒形十二族全覆盖；雷达 0-10 值域；降级三路径；失嗅叙事加长且含分层信息 |
| Vision 页消费 | 色彩情绪板（主色/辅色/渐变三段条 + 情绪词）；**三模式差异化**：失嗅=加长叙事+提示徽章+语音（嗅觉替代通道）、敏感=风险条前置（灯色+首要原因+报告直达链接）、普通=现状；sr-only 摘要升级（含粒形与情绪） |

**验收**：vitest 27/27（qra2 18 + vision 9）+ 构建 ✓；浏览器实测：情绪板渲染、敏感模式风险条（红灯+氧化原因）、失嗅模式加长叙事均正常。

**类型修复**：PerfumeEntry 补 `familyKey` 字段声明（JSON 运行时已有、TS 类型遗漏——此前 vitest 无类型检查故测试通过而 tsc 失败，暴露"测试绿 ≠ 类型对"的盲区，已记录）。

**阶段 3 与路线图对照**：映射规则引擎✓ / 情绪板✓ / 粒子动画（组成驱动+reduced-motion 降级，前期已交付）✓ / 雷达 aria✓ / 通感+语音✓ / 三模式前端差异化✓（token 层 + 内容层双实现）/ 降级路径✓。

## 11. 阶段 4/5 · 识别层 + LLM 编排层（2026-10-05，aura/api）

新建轻量 FastAPI 后端 `aura/api/`（与前端共享同一份 `web/src/data/*.json` 数据层）：

| 模块 | 内容 |
| --- | --- |
| `app/modules/qra2.py` | QRA2 引擎 Python 移植：与 TS 引擎**同种子同结果**（黄金算例 AEL=100/比值=20 逐位对齐）；Beta(20,2) 逆函数启动期建 2001 点查表，LHS 万次抽样 <100ms |
| `app/modules/recognition.py` | 阶段 4 四通道：QwenVLProvider（qwen-vl-max，OpenAI 兼容）→ MockProvider 兜底（同名输入哈希确定性同产品）；**置信度 <0.7 → confirm + 候选列表**（杜绝误识别直判）；条码确定性映射；difflib 文字模糊搜索；OCR 未开通直接引导手动通道 |
| `app/modules/llm.py` | 阶段 5：**PROMPTS 按三模式外置**；三级兜底 qwen-max → qwen-plus → 规则模板（无 Key 全链路可演示）；LLM 只写文案不碰判定 |
| `app/modules/analyzer.py` | 编排：产品解析 → 预警判定（迷你闸门+面板实算）→ 可视化 spec → 文案；**双核心 try/except 错误隔离**（vision 失败 → meta.degraded 上报，预警不受影响）；统一信封 meta（engine/models/degraded/seed） |
| `app/schemas.py` | Pydantic 对外契约（openapi 唯一真源）→ `scripts/gen_api_types.py` 自动生成前端 `api-types.ts`（27 接口，**前端零手写类型，P1-5 完成**） |

**验收**：后端 pytest 11/11（信封/搜索/mock 确定性+确认降级/条码/黄金算例对齐/固定种子复算/人群分化×2/注入故障错误隔离/LLM 兜底/未知产品上报）；前端 27/27 + 构建 ✓。
**浏览器端到端**：后端在线 → 报告页「引擎 aura-qra2/1.0 · 后端计算」徽章 ✓；杀掉后端 → 2s 超时自动回退「本地引擎」且报告完整渲染 ✓（演示日断网双保险）。

**启动**：`cd aura/api && .venv/bin/uvicorn app.main:app --port 8001`（前端 `VITE_API_BASE` 可覆盖地址）

---

## 12. 分享包同步 · 进度总览与未完成清单（2026-10-05）

> 本节为对外同步口径：当前演示主体已迁移至 `aura/`（web 前端 + api 后端，共享数据层），
> 旧 `unbounded/` 保留为后端联调参考。**测试基线：前端 vitest 27/27，后端 pytest 11/11，构建全绿。**

### 12.1 已完成（按路线图阶段）

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 0 设计先行 | 「墨与光」设计系统（Tailwind v4 token/十二香型光谱带/柔光背景）、三页基调稿、frontend-design skill 反俗套自查 | ✅ |
| 1 数据层 | `web/scripts/build_data.py` 管线：12 款真实香水（含金字塔逐材族推断/品鉴关键词）+ IFRA 51st Cat4 三表（限量 20/禁用 9/天然 2，CAS 碎片修复）+ 160 条 CAS 词典 → `web/src/data/*.json` | ✅ |
| 2 QRA2 引擎 | TS 版（`web/src/lib/qra2/`，LHS 万次固定种子/Acklam+Lentz 自实现）与 Python 版（`api/app/modules/qra2.py`）**双实现逐位对齐**；黄金算例 CEL=5.0/AEL=100/比值 20；四闸门（禁用>IFRA>临床>QRA2）；人群分化（柠檬烯 20%：健康绿 vs 敏感肌黄）；氧化 Q10 模型标定 | ✅ |
| 3 可视化系统 | `web/src/lib/vision/engine.ts` 映射规则引擎（VisualSpec：主色=声明香调/辅色/渐变/情绪效价）；组成驱动飘落粒子；分层金字塔+组成条+分层液体瓶；色彩情绪板；三模式差异化（失嗅加长叙事/敏感风险条前置）；降级隔离；读屏摘要 | ✅ |
| 4 识别层 | 四通道：搜索（实时过滤）/ 拍照（真实上传→后端 qwen-vl-max 或 mock，置信度<0.7 转人工确认+候选）/ 条码（确定性映射）/ 手动（任意分隔符 INCI 串解析+真实限值判定）；OCR 未开通引导手动 | ✅ |
| 5 LLM 编排 | `api/app/modules/llm.py`：Prompt 三模式外置、qwen-max→qwen-plus→规则模板三级兜底；编排器双核心 try/except 错误隔离；统一 meta 信封（engine/models/degraded/seed）；openapi 生成前端类型（P1-5 完成，27 接口零手写） | ✅ |
| 附加 | 身份画像 ↔ 顶栏模式双向联动；报告页行动建议/典型值诚实标注；断网自动回退本地引擎（浏览器实测）；首页介绍区（PPT 初稿数据）+ 柔光渐变背景 | ✅ |

### 12.2 未完成清单（按优先级）

**P0（演示保障，赛前必做）**
- [ ] 百炼真实 Key 冒烟：`export DASHSCOPE_API_KEY=sk-xxx` 后验证图像识别（meta.provider=qwen-vl-max）与通感文案（qwen-max），并评估延迟/限流
- [ ] 90 秒路演脚本彩排（演示链路已可用：敏感肌×香奈儿五号黄灯 → 失嗅×氧化红灯+语音 → 显影）
- [ ] 断网预缓存演练（杀后端→本地引擎回退已验证；会场 WiFi 备案）

**P1（可信度，时间盒内尽量）**
- [ ] P1-1 浓度数据真实源：per-product 实测/标注浓度替代群体典型值（当前诚实标注"典型值/未知"）
- [ ] P1-2 NESIL 逐条出处核验（22 条已标 documented，需补 RIFM 报告编号）
- [ ] P1-3 氧化 k_ox：当前单系数标定（Q10=1.8），15 条成分级速率待补
- [ ] P1-4 IFRA 官方 per-material 版号核对（现用队友整理表，含 51st Amendment 口径）
- [ ] 后端接入旧库 71 条致敏原全量（当前前端/后端消费 IFRA 29 + 词典 160）
- [ ] 读光 OCR 成分表通道（`recognition.py` 加 OcrProvider）

**P2（工程与体验）**
- [ ] 移动端细调 + Lighthouse 无障碍分 ≥90 验证
- [ ] 聚合暴露开关（引擎已支持 aggregateFactor，UI 未暴露）
- [ ] 临床闸门 human NOEL 数据源（现为孕期麝香保守规则）
- [ ] 云部署叙事（OSS/FC，路线图阶段 7）；前端拆页重构（当前三路由已够用）

### 12.3 分享包说明

打包内容：`web/`（前端源码+数据管线）、`api/`（后端源码+测试）、`requirements.txt`、
`IMPROVEMENT_PLAN.md`、`技术可行性与开发路线图.md`、`分享说明.md`。
排除 `node_modules / dist / .venv / __pycache__ / .pytest_cache`。
注意：数据管线 `web/scripts/build_data.py` 依赖仓库根 `数据层/` 原始文件（xlsx/docx 未随包分发，队友本地已有）。

## 12. 三份原始数据层文件整合（2026-10-05，数据层 → 前后端共享）

数据层最早的三份文件（2026-08-30）已通过管线并入共享数据层（`build_data.py` 新增三个解析器，输出 `src/data/*.json`，前后端同时消费）：

| 文件 | 产出 | 解析要点 |
| --- | --- | --- |
| 表格26种致敏香料.xlsx | `allergens26.json`（26 条：INCI/中文/CAS/Ⅳ型致敏备注） | CAS 不换行连字符 U+2011 归一为 `-` |
| IgE致敏原表格.xlsx | `ige.json`（10 条：树脂类 5 + 净油类 4 + 植物提取物 1，含 IgE 风险分级与临床备注） | 「XX类:」分节标题驱动归类；表头污染行双保险过滤（旧 P2-3-3 教训） |
| 香水成分数据及过敏香料.docx | `materials.json`（天然 72 + 合成 76/8 类香材词典，与文档自述「天然72+合成76」精确对齐） | 状态机解析「天然香料：/合成单体香料：」两节；过滤「XX类香料」6 个分组头；合成按 8 大类归档 |

**消费链路**：
- 手动通道匹配优先级：禁用 > IFRA 限值（QRA2 实算）> **EU 26 标注清单**（黄灯+标注阈值提示）> **IgE Ⅰ 型速发**（按风险分级）> CAS 词典 > **香材词典**（天然/合成）
- 判定集成：成分含 IgE 材料（如一千零一夜的安息香/乳香/没药）× 鼻炎画像 → 横幅速发理由 + 报告「IgE Ⅰ 型速发」行（前后端同规则）
- 后端 health 计数：eu26=26 / ige=10 / materials=154

**验收**：前端 vitest 35/35（新增 8 条：数据完整性/新匹配分支/IgE 判定集成）、后端 pytest 13/13（新增 2 条）、构建 ✓、浏览器实测：手动输入 `Anisyl alcohol, 安息香, 鸢尾` 分别命中 EU26/IgE/天然香材三个新分支；一千零一夜×鼻炎报告含 IgE 理由与明细行。

**踩坑**：`norm` 工具从 const 改为函数声明——模块加载期 `toEntry → buildProfile → lookupIge` 调用链会触发 const 的 TDZ。
