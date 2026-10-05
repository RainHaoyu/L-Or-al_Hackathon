# 万象Aura

> 2026 欧莱雅美妆科技黑客松 · 赛道三「无界体验家——用爱(AI)让美触手可及」
> 双核心：**QRA2 致敏预警** + **香味可视化**，面向失嗅 / 敏感肌 / 孕期 / 鼻炎人群

---

## 一、仓库结构

```
web/         前端（React 19 + Vite 7 + Tailwind v4 + shadcn/ui）
  src/lib/qra2/      QRA2 引擎（TS，浏览器内运行：LHS 蒙特卡洛 / 四闸门 / 氧化 Q10）
  src/lib/vision/    可视化映射引擎（VisualSpec / 情绪效价 / 降级隔离）
  src/lib/aura.ts    数据层入口（真实数据消费 + 迷你闸门 + 手动成分解析）
  src/data/*.json    数据产物（12 款香水 / IFRA 51st Cat4 / 160 条 CAS 词典）
  scripts/build_data.py   数据管线（构建期 xlsx/docx → src/data/*.json）
  src/pages|components/   首页三步流 / 预警报告 / 香气显影 / 顶栏与模式联动

api/         后端（FastAPI + Pydantic，可选）
  app/modules/qra2.py         QRA2 引擎 Python 版
  app/modules/recognition.py  识别层：qwen-vl-max（需 Key）/ mock 兜底 / 条码 / 搜索
  app/modules/llm.py          通感文案：qwen-max → qwen-plus → 模板（三级兜底）
  app/modules/analyzer.py     编排：双核心错误隔离 + meta 信封
  app/schemas.py              对外契约（openapi 唯一真源）
  scripts/gen_api_types.py    openapi → web/src/lib/api-types.ts
  tests/                      pytest

docs/        文档
  IMPROVEMENT_PLAN.md                   改进台账（含进度总览与未完成清单）
  技术可行性与开发路线图.md               九阶段路线图 + QRA2 模型定义 + 设计规范
  分享说明.md                            工程分享包说明
  LEGACY_IMPLEMENTATION_ASSESSMENT.md   旧实现的独立评审与改进清单（历史参考）

legacy/      旧实现归档（已退出主线，仅供数据/代码参考）
  data/seed/                          旧数据资产（71 条致敏原 / 21 款香水），待迁移评估
  apps/ services/ scripts/            旧前后端与数据管线
  package.json / package-lock.json / 无界体验家-项目包.zip
```

> **旧实现完整可回溯**：tag `archive/legacy-impl-7f4070b`（提交 `7f4070b`）。

---

## 二、启动指南

**前端**（先启动；**不依赖后端也能完整演示**）：

```bash
cd web
npm install
npm run dev        # http://localhost:3000
npm run test       # vitest
npm run build
```

**后端**（可选；不启动则前端自动回退本地引擎，报告页徽章显示「本地引擎」）：

```bash
cd api
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# .venv/bin/pip install -r requirements.txt        # macOS / Linux
.venv/Scripts/python -m uvicorn app.main:app --port 8001
.venv/Scripts/python -m pytest tests/ -q
```

**接入阿里云百炼（可选）**：

```bash
export DASHSCOPE_API_KEY=sk-xxx    # 再启动 uvicorn
# 图像识别自动切 qwen-vl-max（否则 mock）；通感文案自动切 qwen-max（否则模板）
```

**重新生成数据 / 前端类型**：

```bash
python3 web/scripts/build_data.py                        # 数据层 → web/src/data/*.json
cd api && .venv/bin/python scripts/gen_api_types.py      # openapi → web/src/lib/api-types.ts
```

> ⚠️ `web/scripts/build_data.py` 读取**仓库上一级**的 `数据层/` 目录
> （即 `../数据层/`，含 xlsx/docx 原始文件）。该目录**当前不在仓库内、不随包分发**，
> 若缺失则数据管线无法重跑，只能使用已生成的 `web/src/data/*.json`。

---

## 三、关键设计口径

- **风险方向**：`safety_ratio = AEL / CEL`，越大越安全。
  红线 = P99 余量 < 1（全人群一致）；黄线 = 人群判定线 `AEL / CEL[policy] / T_pop < 1`
  （健康人群 P90，脆弱人群 P99 × T_pop）。
- **数据诚实**：文献 NESIL 标 `documented`；demo 估计值 ÷3 惩罚标 `indicative`；
  无数据显式黄灯——**「数据不足 ≠ 安全」**。
- **可复算**：LHS 固定种子，`meta.seed` 上报。
- **演示韧性**：前端本地引擎 + 后端 2 秒短超时静默回退。

---

## 四、文档索引

| 想了解什么 | 看哪份 |
| --- | --- |
| 待办与进度 | `docs/IMPROVEMENT_PLAN.md` |
| 技术方案与阶段规划 | `docs/技术可行性与开发路线图.md` |
| 如何启动与分享 | `docs/分享说明.md` |
| 旧实现的问题清单（历史） | `docs/LEGACY_IMPLEMENTATION_ASSESSMENT.md` |

---

## 五、免责声明

本系统为黑客松演示用途，风险结论不构成医学建议。
皮肤敏感者请以斑贴试验与医嘱为准；香水成分与法规限量可能变化，请以官方最新标准为准。
