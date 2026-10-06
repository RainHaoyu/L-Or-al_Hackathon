# 万象Aura

> 2026 欧莱雅美妆科技黑客松 · 赛道三「无界体验家——用爱(AI)让美触手可及」
> 双核心：**QRA2 致敏预警** + **香味可视化**，面向失嗅 / 敏感肌 / 孕期 / 鼻炎人群

**当前分支**：`feat/wanxiang-aura-v2`　|　**状态**：两条线并行推进中（见 §五）

---

## 一、仓库结构

```
web/         前端（React 19 + Vite 7 + Tailwind v4 + shadcn/ui）
  src/lib/qra2/      QRA2 引擎（TS，浏览器内运行：LHS 蒙特卡洛 / 四闸门 / 氧化 Q10）
  src/lib/vision/    可视化映射引擎（VisualSpec / 情绪效价 / 降级隔离）
  src/lib/aura.ts    数据层入口（真实数据消费 + 迷你闸门 + 手动成分解析）
  src/data/*.json    数据产物（tox / ifra / perfumes / ingredients / allergens26 / ige / materials）
  scripts/build_data.py   数据管线（构建期 数据层/ → src/data/*.json，幂等可重跑）
  src/pages|components/   首页三步流 / 预警报告 / 香气显影 / 顶栏与模式联动

api/         后端（FastAPI + Pydantic，**可选**）
  app/modules/qra2.py         QRA2 引擎 Python 版（与 TS 逐位对齐，有测试锁住）
  app/modules/recognition.py  识别层：qwen-vl-max（需 Key）/ mock 兜底 / 条码 / 搜索
  app/modules/llm.py          通感文案：qwen-max → qwen-plus → 模板（三级兜底）
  app/modules/analyzer.py     编排：双核心错误隔离 + meta 信封
  app/schemas.py              对外契约（openapi 唯一真源）
  scripts/gen_api_types.py    openapi → web/src/lib/api-types.ts
  tests/                      pytest（171 条）

docs/        文档
  PROGRESS.md                           进度台账：已修 / 仍缺 / 下一步（**先看这份**）
  IMPROVEMENT_PLAN.md                   协作者的原始改进台账（阶段记录与设计口径）
  技术可行性与开发路线图.md               九阶段路线图 + QRA2 模型定义 + 设计规范
  分享说明.md                            工程分享包说明
  LEGACY_IMPLEMENTATION_ASSESSMENT.md   旧实现的独立评审（历史参考）

legacy/      旧实现归档（已退出主线，仅供数据/代码参考）
  data/seed/                          旧数据资产（71 条致敏原 / 21 款香水），待评估
  apps/ services/ scripts/            旧前后端与数据管线

数据层/      ★ 在**仓库上一级**（`../数据层/`），含 9 个上游 xlsx/docx
            数据管线的输入；不随仓库分发，需单独提供（见 §三）
```

> **旧实现完整可回溯**：tag `archive/legacy-impl-7f4070b`。

---

## 二、快速开始

**前端**（先启动；**不依赖后端也能完整演示**）：

```bash
cd web
npm install
npm run dev        # http://localhost:3000
npm run test       # vitest，65 条
npm run build
```

**后端**（可选；不启动则前端自动回退本地引擎，报告页徽章显示「本地引擎」）：

```bash
cd api
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt        # macOS / Linux
.venv/Scripts/python -m uvicorn app.main:app --port 8001
.venv/Scripts/python -m pytest tests/ -q           # 171 条
```

**接入阿里云百炼（可选，但演示前必须冒烟）**：

```bash
export DASHSCOPE_API_KEY=sk-xxx    # 再启动 uvicorn
# 图像识别自动切 qwen-vl-max（否则 mock）；通感文案自动切 qwen-max（否则模板）
```

**数据管线 / 前端类型再生成**（改了 `数据层/` 或后端契约后）：

```bash
python web/scripts/build_data.py                    # 数据层/ → web/src/data/*.json（幂等）
cd api && .venv/bin/python scripts/gen_api_types.py  # openapi → web/src/lib/api-types.ts
```

> 两条易踩的坑：
> 1. `数据层/` 必须在**仓库上一级**（脚本用 `ROOT.parent.parent` 定位），不是仓库内。
> 2. 端口是 **前端 3000 / 后端 8001**（不是旧实现的 5173 / 8000）。

---

## 三、关键设计口径

- **风险方向**：`safety_ratio = AEL / CEL`，越大越安全。
  - **红线** = P99 余量 < 1（全人群一致）
  - **黄线** = 人群判定线 `AEL / CEL[policy] / T_pop < 1`（healthy→P90，脆弱人群→P99）
  - 因 `P99/P90 = 1.8817`（常数），**QRA2 这条路径的黄灯只对 sensitive / rhinitis 可达**；
    另两条黄灯路径（IFRA 八成上限、数据不足）对全人群可用。详见 `docs/PROGRESS.md` §二.6。
- **数据诚实**：文献 NESIL 标 `documented`；demo 估计值 ÷3 惩罚标 `indicative`；
  无数据显式黄灯——**「数据不足 ≠ 安全」**。
- **匹配规则**：所有名称匹配（毒理 / IFRA 限值 / 禁用 / 词典）统一为**最长键优先**，
  别名落在数据里（`tox.json` / `ifra.json` 的 `aliases` 字段），前端 TS 与后端 Python 共读。
- **可复算**：LHS 固定种子，`meta.seed` 上报。
- **演示韧性**：前端本地引擎 + 后端 2 秒短超时静默回退（断网也能演示）。

---

## 四、测试与质量现状

| 层 | 命令 | 规模 | 覆盖 |
| --- | --- | --- | --- |
| 前端 | `cd web && npm run test` | **65** | QRA2 引擎 / 可视化映射 / 数据层整合 / IFRA 与毒理匹配 |
| 后端 | `cd api && pytest -q` | **171** | 端点与信封 / 分布基元 / 双引擎对齐 / 匹配正确性 |
| 跨引擎 | 同上 | 内含 | 分布基元、闸门 19 用例×14 字段、人群策略、氧化 24 项、毒理与 IFRA 查找 |

> 改动 `web/src/lib/qra2/*` 或 `api/app/modules/qra2.py` 中**任何一侧**，
> 都必须同步另一侧并重跑两端测试——这是唯一的两份实现同步机制，没有自动校验。

---

## 五、任务分工：两条线并行

> 原则：**按"能不能同时动同一批文件"切分**，而不是按"前后端"。
> 两条线各自可独立验证，交汇点只有三处（见 §五.3）。

### 线 A —— 数据 · 引擎 · 工程可复现

**负责目录**：`api/`、`web/scripts/`、`web/src/data/`、`web/src/lib/qra2/`、`数据层/`、`docs/`

| # | 任务 | 说明 | 阻塞项 |
| --- | --- | --- | --- |
| **A-1** | **百炼 Key 真实冒烟**（原 C1） | 当前**全程 mock**：拍照识别与通感文案都从未真实跑过。需验证 qwen-vl-max / qwen-max 的返回、延迟、失败降级 | 🔴 需要 `DASHSCOPE_API_KEY` |
| **A-2** | 毒理表补真实出处（原 A2 延伸） | 22 条 NESIL 中 19 条标 `documented` 但**未逐条标注文献来源**；补齐 RIFM/Api 出处便于答辩 | — |
| **A-3** | per-product 浓度（原 A4） | 香水成分浓度来自 docx/文献典型值，**非逐款实测**。要么找到真实源，要么在文案里显式说明 | — |
| **A-4** | 成分级氧化速率（原 A5） | 现用单一标定系数 + Q10。`tox.json` 已预留 `k25` 字段（目前仅柠檬烯/芳樟醇有值） | — |
| **A-5** | 工程收尾：测试提速、lint/CI（原 B3/B4） | 后端 171 条约 130 秒，主要是 LHS 抽样；可共享 fixture 或降低测试用 n。前端有 eslint 配置未纳入流程 | — |
| **A-6** | `数据层/` 入库决策（原 §六遗留） | 现在仓库外一层 ⟹ clone 不带，他人无法复现管线。需决定：入版本控制，还是随包分发 + 文档说明 | — |

### 线 B —— 前端体验 · 演示保障

**负责目录**：`web/src/pages/`、`web/src/components/`、`web/src/lib/vision/`、`web/src/lib/state.tsx`、`web/index.html`

| # | 任务 | 说明 | 阻塞项 |
| --- | --- | --- | --- |
| **B-1** | **90 秒路演脚本彩排**（原 C2） | 建议链路：敏感肌 × 香奈儿五号黄灯 → 失嗅 × 氧化红灯 + 语音播报 → 香气显影收尾。需实测每步耗时 | 依赖 A-1 完成（否则只能 mock 演示） |
| **B-2** | **会场断网预案实测**（原 C3） | 前端本地引擎回退机制已具备（2 秒短超时），但**未实测**。需杀掉后端跑通全链路 | — |
| **B-3** | 移动端细调 + 无障碍（原 C4） | 响应式、Lighthouse 无障碍 ≥90、`prefers-reduced-motion`、aria 完整性 | — |
| **B-4** | 前端包名与脚手架残留（原 B2） | `web/package.json` 的 `name` 仍是 `my-app`、`version` 为 `0.0.0`；`index.html` 标题与 meta | — |
| **B-5** | 仓库根清理（原 B5） | 3 个冗余 zip 共 3.3MB（`万象Aura-工程包.zip` / `万象Aura-全套包-Windows.zip` / `万象Aura工程包-20261005.zip`），内容均已落盘 | — |
| **B-6** | 聚合暴露开关 UI（原 C6） | 引擎已支持 `aggregateFactor`，缺前端入口 | — |

> 原 C5（读光 OCR 通道）**不列入本轮**：需阿里云凭证，且属 P1 增强，演示前不做。

### 五.3　两条线的交汇点（改动时必须互相同步）

| 交汇点 | 谁产出 | 谁消费 | 规则 |
| --- | --- | --- | --- |
| `web/src/data/*.json` | 线 A（跑 `build_data.py`） | 线 B | **线 B 不手改 JSON**；要改数据找线 A 改 `数据层/` 后重跑 |
| `web/src/lib/api-types.ts` | 线 A（跑 `gen_api_types.py`，由 `api/app/schemas.py` 生成） | 线 B | **该文件为自动生成，不要手改** |
| `web/src/lib/qra2/*` ↔ `api/app/modules/qra2.py` | 线 A | 线 A | 两份实现必须同改同测（有跨引擎对齐测试兜底） |
| `docs/*` 口径说明 | 两条线共同 | 两条线 | 改口径先改文档再改代码 |
| 合并到 `main` | 两条线 | — | 见 §六 |

---

## 六、协作流程建议

### 分支

```
main                      保护分支，只接受合并
feat/wanxiang-aura-v2     当前集成分支（两条线共用）
```

**若两条线改动开始互相干扰，建议拆成**：

```bash
git switch -c dev/engine    # 线 A
git switch -c dev/web       # 线 B（从 feat/wanxiang-aura-v2 切出）
# 每天各合并一次回 feat/wanxiang-aura-v2
```

> 之所以建议拆：线 A 动 `api/` 与 `web/src/lib/qra2/`，线 B 动 `web/src/pages/` 与
> `web/src/components/`，目前**路径已基本隔离**；但 `docs/` 与根目录配置文件仍会撞。

### 每日节奏

| 时间 | 事项 |
| --- | --- |
| 开工 | 先读 `docs/PROGRESS.md`（进度与缺口），确认今天动哪些文件 |
| 开发中 | 只在自己的负责目录内改；要动交汇点（§五.3）先在群里说 |
| 收工 | 跑两端测试（`npm run test` + `pytest -q`）+ `npm run build`，提交并推送 |

### 提交约定

```
<type>(<scope>): <说明>
type: feat | fix | test | docs | refactor | chore
scope: qra2 | tox | ifra | data | engine | web | docs
```

提交信息里写清**改了什么、为什么、怎么验证的**（见近期提交可作为范例）。

---

## 七、文档索引

| 想了解什么 | 看哪份 |
| --- | --- |
| **进度、还缺什么、下一步** | `docs/PROGRESS.md` |
| 设计口径的红线/黄线职责分离 | `docs/IMPROVEMENT_PLAN.md` |
| 技术方案与阶段规划 | `docs/技术可行性与开发路线图.md` |
| 如何启动与分享 | `docs/分享说明.md` |
| 旧实现的问题清单（历史） | `docs/LEGACY_IMPLEMENTATION_ASSESSMENT.md` |

---

## 八、免责声明

本系统为黑客松演示用途，风险结论不构成医学建议。
皮肤敏感者请以斑贴试验与医嘱为准；香水成分与法规限量可能变化，请以官方最新标准为准。
