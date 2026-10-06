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
  tests/                      pytest（178 条）

scripts/     ★ 启动脚本的 ASCII 核心（`start-*.bat`）；根目录中文名 `.bat` 只是薄壳
docs/        文档
  PROGRESS.md                           进度台账：已修 / 仍缺 / 下一步（**先看这份**）
  IMPROVEMENT_PLAN.md                   协作者的原始改进台账（阶段记录与设计口径）
  技术可行性与开发路线图.md               九阶段路线图 + QRA2 模型定义 + 设计规范
  分享说明.md                            工程分享包说明
  LEGACY_IMPLEMENTATION_ASSESSMENT.md   旧实现的独立评审（历史参考）

legacy/      旧实现归档（已退出主线，仅供数据/代码参考）
  data/seed/                          旧数据资产（71 条致敏原 / 21 款香水），待评估
  apps/ services/ scripts/            旧前后端与数据管线

数据层/      ★ 上游 9 个 xlsx/docx，数据管线的输入；不随仓库分发，需单独提供
            常见位置是**仓库上一级**（`../数据层/`）；不在那里时见 §二
```

> **旧实现完整可回溯**：tag `archive/legacy-impl-7f4070b`。

---

## 二、快速开始

### Windows：一键启动

仓库根目录**双击 `一键启动.bat`**：自动起后端（检测到 Python 时，另开一个窗口）
+ 前端（本窗口 → http://localhost:3000）。也可单独用 `启动前端.bat` / `启动后端.bat`。
`数据重生成.bat` 重跑数据管线。

> **为什么根目录的中文名 `.bat` 只有三行**：`cmd.exe` 按系统 OEM 代码页（中文系统
> 为 GBK）解码脚本字节，脚本内容里出现 UTF-8 中文会被误解码、甚至吞掉整行。
> 因此**逻辑全部写在 `scripts\` 下的 ASCII 名文件里**
> （`start-frontend.bat` / `start-backend.bat` / `regenerate-data.bat`），
> 中文名文件只按 ASCII 路径 `call` 它们——这样任何 `.bat` 都不必写出中文文件名。
> 两条硬约束由 `web/src/lib/launchers.test.ts` 守着：
> **`.bat` 必须 CRLF + ASCII-only**，**端口必须与 `vite.config.ts` / `api.ts` 一致**。

**前端**（也可手动起；**不依赖后端**）：

```bash
cd web
npm install
npm run dev        # http://localhost:3000
npm run test       # vitest，88 条
npm run build
```

**后端**（可选；不启动则前端自动回退本地引擎，报告页徽章显示「本地引擎」）：

```bash
cd api
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt        # macOS / Linux
.venv/Scripts/python -m uvicorn app.main:app --port 8001
.venv/Scripts/python -m pytest tests/ -q           # 181 条
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

> 三条易踩的坑：
> 1. `数据层/` **不入库**：脚本按锚点文件在**仓库上一级**、仓库内等几个位置自动查找，
>    找不到时会把查过的路径全部打印出来；也可用环境变量 `AURA_DATA_DIR` 直接指路。
> 2. 数据管线产出固定为 **LF + UTF-8 无 BOM**，所以重跑后 `git status` 应为空——
>    否则会变成「假 diff」，让人误以为数据变了。
> 3. 端口是 **前端 3000 / 后端 8001**（不是旧实现的 5173 / 8000）。

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
- **可降级**：前端自带本地引擎。后端请求超时**按模式区分**（normal / sensitive 13 s、
  anosmia 19 s），推导是「引擎实测 4.4–5.0 s + 后端 LLM 总预算」；
  超时或失败即回退本地引擎，报告页徽章标注实际引擎来源。

---

## 四、测试与质量现状

| 层 | 命令 | 规模 | 覆盖 |
| --- | --- | --- | --- |
| 前端 | `cd web && npm run test` | **88** | QRA2 引擎 / 可视化映射 / 数据层整合 / IFRA 与毒理匹配 / 启动脚本守卫 / 模式接线与超时 / 词典自探测 |
| 后端 | `cd api && pytest -q` | **181** | 端点与信封 / 分布基元 / 双引擎对齐 / 匹配正确性 / LLM 预算不变式 / 网络隔离 |
| 跨引擎 | 同上 | 内含 | 分布基元、闸门 19 用例×14 字段、人群策略、氧化 24 项、毒理与 IFRA 查找 |

> 改动 `web/src/lib/qra2/*` 或 `api/app/modules/qra2.py` 中**任何一侧**，
> 都必须同步另一侧并重跑两端测试——这是唯一的两份实现同步机制，没有自动校验。

---

## 五、任务分工：两条线并行

> 本仓库**只跟踪程序本身的工作**——功能、正确性、工程质量、数据质量。
> 演示、路演、彩排、会场准备等事项不在本仓库管理范围内。
>
> 切分原则：**按"能不能同时动同一批文件"分**，而不是按"前后端"。
> 两条线各自可独立验证，交汇点只有几处（见 §五.3）。
> 带 ✅ 的是已完成项。

### 线 A —— 数据 · 引擎 · 工程

**负责目录**：`api/`、`web/scripts/`、`web/src/data/`、`web/src/lib/qra2/`、`数据层/`

| # | 任务 | 状态 |
| --- | --- | --- |
| A-1 | 百炼 Key 真实冒烟（qwen-max / qwen-vl-max） | ✅ 已完成 |
| A-2 | 毒理表 19 条 `documented` 补逐条文献出处 | 待做 |
| A-3 | per-product 浓度（现为文献典型值，非逐款实测） | 待做 |
| A-4 | 成分级氧化速率（`tox.json` 已预留 `k25`） | 待做 |
| A-5 | 测试提速 + lint/CI | 待做 |
| A-6 | `数据层/` 入库决策（现位于仓库外一层） | 待做 |
| A-7 | 双重实现同步机制（`web/src/lib/qra2/` ↔ `api/app/modules/qra2.py`） | 待做 |

### 线 B —— 前端 · 可视化 · 数据质量

**负责目录**：`web/src/pages/`、`web/src/components/`、`web/src/lib/`（除 `qra2/`）、`web/index.html`

| # | 任务 | 状态 |
| --- | --- | --- |
| B-1 | 启动脚本（`.bat`/`.sh`/`.command`）可正常使用 | ✅ 已完成 |
| B-2 | 清理仓库根冗余文件（3 个 zip，3.3 MB） | ✅ 已完成 |
| B-3 | ~~失嗅模式 AI 文案未走后端~~（`AnalyzeFlow` 写死 `mode:'normal'`） | ✅ 已完成 |
| B-4 | ~~前端超时按模式区分~~（与 B-3 同批） | ✅ 已完成 |
| B-5 | 前端包名与 `index.html` 元信息（现仍为脚手架残留 `my-app`） | 待做 |
| B-6 | ~~词典类查找逐条验证（EU26 / IgE / 香材 / CAS 四类）~~ | ✅ 已完成 |
| B-7 | IFRA 禁用清单解析根因（现靠人工修正表兜住已知错位） | 待做 |
| B-8 | 聚合暴露开关 UI（引擎已支持 `aggregateFactor`） | 待做 |
| B-9 | 响应式与无障碍（`prefers-reduced-motion`、aria、对比度） | 待做 |

> 读光 OCR 通道（需阿里云凭证）与移动端专项不列入本轮。

### 五.3　两条线的交汇点（改动时必须互相同步）

| 交汇点 | 谁产出 | 规则 |
| --- | --- | --- |
| `web/src/data/*.json` | 线 A 跑 `build_data.py` | **不要手改**；要改数据找线 A 改 `数据层/` 后重跑 |
| `web/src/lib/api-types.ts` | 线 A 跑 `gen_api_types.py`（由 `api/app/schemas.py` 生成） | **自动生成，不要手改** |
| `web/src/lib/qra2/*` ↔ `api/app/modules/qra2.py` | 线 A | 两份实现必须**同改同测**（有跨引擎对齐测试兜底） |
| `docs/*` 口径说明 | 两条线共同 | 改口径先改文档再改代码 |

---

## 六、协作流程

### 分支

```
main                      保护分支，只接受合并（当前已包含全部已完成工作）
feat/wanxiang-aura-v2     集成分支
```

若两条线开始互相干扰，建议拆成 `dev/engine` 与 `dev/web`——
线 A 动 `api/` 与 `web/src/lib/qra2/`，线 B 动 `web/src/pages/` 与 `web/src/components/`，
路径已基本隔离；但 `docs/` 与根目录配置文件仍会撞。

### 收工检查（每次提交前）

```bash
cd web && npm run test && npm run build     # 88 条 + 构建
cd api && .venv/Scripts/python -m pytest -q # 181 条
```

改了 `web/src/lib/qra2/` 或 `api/app/modules/qra2.py` 时，**必须同步另一侧并重跑两端测试**。

### 提交约定

```
<type>(<scope>): <说明>
type: feat | fix | test | docs | refactor | chore
scope: qra2 | tox | ifra | data | engine | web | docs
```

提交信息里写清**改了什么、为什么、怎么验证的**。

---

## 七、文档索引

| 想了解什么 | 看哪份 |
| --- | --- |
| **待办清单（给队友，纯文本）** | `docs/TODO_FOR_TEAM.txt` |
| 进度与已修问题 | `docs/PROGRESS.md` |
| 设计口径的红线/黄线职责分离 | `docs/IMPROVEMENT_PLAN.md` |
| 技术方案与阶段规划 | `docs/技术可行性与开发路线图.md` |
| 旧实现的问题清单（历史） | `docs/LEGACY_IMPLEMENTATION_ASSESSMENT.md` |

---

## 八、免责声明

本系统风险结论不构成医学建议。皮肤敏感者请以斑贴试验与医嘱为准；
香水成分与法规限量可能变化，请以官方最新标准为准。
