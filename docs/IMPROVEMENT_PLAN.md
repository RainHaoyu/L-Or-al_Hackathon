# 万象Aura · 改进清单

> **本文档的定位**：当前仓库**已有一份独立完成的完整实现**（原有"启动包"脚手架文档与契约已删除，
> 旧说明归档在 `docs/_archive/README-startup-package.md`）。
> 从现在起，**以仓库现有实现为主体，通过改进它来交付万象Aura 的目标能力**。
> 本文档只做一件事：把「现状 → 目标」之间所有待改进项列清楚，作为后续迭代的工作台。
>
> 建立日期：迁移当日｜状态：待开工｜不属于任何已冻结契约

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
| 迁移 | 现有实现入库、旧脚手架清理 | ✅ 已完成 | 提交 `dc9a0ac` |
| **第 1 批** | **P0-1 / P0-2 / 降级上报 / 回归测试** | ✅ **已完成** | 见下「第 1 批交付记录」 |
| 第 2 批 | P0-3 人群分级判据 + P0-4 空集合默认色 | ⬜ 未开始 | 需先验证 5 人群能分化 |
| 第 3 批 | 数据诚实化（P1-1 ~ P1-4） | ⬜ 未开始 | 工作量中心 |
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

### 3.3 P0-3　人群差异化未生效，但文档已把它当成卖点

| 项 | 内容 |
| --- | --- |
| 位置 | `services/api/app/modules/qra2/engine.py:104-109` |
| 根因 | 判据写死 `m99 < 1.0 → red / m90 < 1.0 → yellow`，**判据里没有 `policy` 变量**；`config.json` 的 `percentile_policy`（healthy→P90，其余→P99）只在返回时作为 `decision_percentile` 字段回显，**是死配置** |
| 叠加原因 | `T_pop = α×β` 只能改**黄灯**门槛，改不了红/绿分界；实测 20 款真实香水的最小 m99 为 **9.158**，没有一款落进敏感肌的分化窗口 `(1, 3)` |
| 实测 | 5 人群结论矩阵完全一致；README 承诺的「最脆弱的人用最保守的分位线保护」不成立 |
| 假信心测试 | `tests/test_qra2.py:82-93` 断言的是配置常量 `T_pop == 3.0` 与一个无论怎么改都红的输入，**没有一条断言能验证人群产生了更严的判定** |
| 改进方案 | ① 让判据真的消费 `policy`：按人群选 `m90` 或 `m99` 作为判定分位线；② 明确 `T_pop` 与分位线的职责边界（一个调门槛、一个调分位），避免两者语义重叠；③ **先用真实数据验证 5 人群能产生分歧**，再对外声明该能力 |
| 验收 | 存在至少「健康成人=green / 敏感肌=yellow」的真实香水用例，并有参数化测试固定住它 |

### 3.4 P0-4　`strictest()` 空集合默认返回绿灯

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
| 3 | `data/seed/ige_materials.json` 含 1 行表头污染数据（`name_zh: "原料类型"`） |
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
- [ ] P0-3 让判据真的消费 `percentile_policy`，并用真实数据验证 5 人群能分化
- [ ] P0-4 `strictest()` 空集合不再返回 green
- [ ] 补测试：5 人群分歧、空输入不绿
- [ ] `repository` 加载期 schema 校验（把数据形状问题提前到启动时报错）


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
- [ ] **5 人群在同一香水上能产生分歧**（当前 5 人群结论相同）— 第 2 批
- [ ] 空成分输入的综合结论不是 green（当前是 green）— 第 2 批
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
