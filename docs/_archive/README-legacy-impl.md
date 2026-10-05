# 无界体验家 · AI 驱动的香水致敏原预警与香味可视化系统

> 2026 欧莱雅美妆科技黑客松 · 赛道三「无界体验家-用爱(AI)让美触手可及」
> 双核心：**致敏预警（QRA2）+ 香味可视化**，面向失嗅 / 敏感肌 / 孕期 / 鼻炎人群

## 一、快速开始

```bash
# 后端（FastAPI，端口 8000；首次会自动创建 .venv）
cd services/api && uv sync && uv run uvicorn app.main:app --reload --port 8000

# 前端（Vite + React + TS + Tailwind，端口 5173，/api 代理到 8000）
cd apps/web && npm install && npm run dev

# 测试（35 个用例：QRA2 黄金算例 / 数据匹配 / 可视化 / API 端到端）
cd services/api && uv run pytest -q

# 数据清洗（数据层 xlsx → seed JSON，可重复执行）
services/api/.venv/bin/python scripts/clean_data.py
```

未配置任何 API Key 时系统自动进入 **mock 演示模式**：识别走本地模拟（置信度 0.62 触发降级策略）、
通感文案走规则模板，全链路可演示、可测试。配置 `DASHSCOPE_API_KEY` 后自动切换阿里云百炼真实模型。

## 二、架构（按功能分模块，便于纠错）

```
┌─────────────────────── apps/web（React H5，三端响应式） ───────────────────────┐
│  modules/profile 人群画像 │ capture 四通道识别入口 │ warning 核心①预警 │ vision 核心②可视化 │
└──────────────────────────────────┬─────────────────────────────────────────────┘
                        REST /api/v1（Pydantic 契约 = 前后端唯一真源）
┌──────────────────────────────────┴─────────────────────────────────────────────┐
│ services/api (FastAPI)                                                          │
│  recognition 识别域：qwen-vl-max 照片 / 条码 / 搜索 / 手动（Provider 可插拔）        │
│  qra2 预警引擎：LHS 蒙特卡洛 N=10000 → P50/P90/P99 → 三闸门取最严 → 人群α/氧化D      │
│  scentmap 可视化域：7 香调→色彩/粒子/雷达规则库（与预警域零依赖）                     │
│  orchestration 编排域：分析主流程 + qwen-max 通感文案（三级兜底）                    │
│  ingredient 数据域：seed 加载 / 别名·CAS·模糊匹配 / admin 热更新                    │
└──────────────────────────────────┬─────────────────────────────────────────────┘
                      data/seed：allergens / ige_materials / perfumes / families / config
```

**纠错设计**：①契约先行（`schemas/api.py` ↔ `api-types.ts`，改契约即暴露所有受影响处）；
②每域独立可测（QRA2 纯函数、识别域 mock 回放）；③错误隔离（单识别通道失败仅降级该通道；
可视化失败不影响预警输出）；④统一错误信封 + request_id 全链路日志。

## 三、QRA2 计算内核（替换 v3 报告经典 QRA）

简化自研实现 IFRA/RIFM **QRA 2.0**（概率化聚合暴露）思路：

1. **闸门基线（QRA1）**：`AEL = NESIL ÷ SAF`（文档算例：柠檬烯 NESIL=10000、SAF=100 → AEL=100）
2. **CEL 概率化**：五参数标量 → 分布（用量 LogNormal CV0.4 / 面积 Tri(50,100,200) /
   频率离散{1:.5,2:.35,3:.15} / 浓度 U(0.8c₀,1.2c₀) / 吸收 Beta(20,2)），
   `scipy.stats.qmc` 拉丁超立方抽样，固定种子可复算
3. **聚合暴露**：`CEL_total = Σ(CEL×w)`（身体乳 w=0.8、洗发水 w=0.3 共使用权重，可配置）
4. **分位判定**：P50/P90/P99 四档红黄绿；敏感肌/孕期/失嗅/鼻炎自动升至 P99 分位线
5. **三闸门取最严**：QRA2 ∨ 临床阈值(LOEL/NOEL) ∨ IFRA 限量；欧盟禁用成分（Lilial/HICC）直判红灯
6. **人群差异化**：`T_pop = α×β`（敏感肌 3.0 / 鼻炎 1.2）；氧化 `D = 1−exp(−k_eff·t)` 嗅觉替代预警

**黄金算例验收**（`tests/test_qra2.py`）：点估计 CEL=5.0、AEL/CEL=20 精确复现；
概率化 P99=13.85（文档示意值 13.2，误差 5%，决策结论一致：AEL=10 时 P99 余量 0.76→红灯）。
> 注：策划案V1 的 P50/P90 示意值自身不满足同一分布（由 P90 推 σ=0.587、由 P99 推 σ=0.502），
> 引擎按文档规定的分布族实现，P99（判定分位线）误差 <15%，P50/P90 宽容差但保序、保决策结论。

**数据诚实原则**：文献级 NESIL（RIFM/人体 CNIH NOEL）标 `documented`；演示估计值叠加 ×3 保守惩罚标 `indicative`；
无数据成分显式标「数据不足」，绝不静默降级。

**数据管线（v2）**：`scripts/clean_data.py`（数据层 xlsx → 26 条基础库，检测到 v2 时自动改写 `*.base.json` 防覆盖）
→ `scripts/build_allergens_v2.py`（队友增强：合并 Na 2022 Dermatitis / Lalko 2008 / Api 2022 文献 NESIL·NOEL·EC3、
IFRA Cat4 限量、EU 2023/1545 新增 45 条目、Lu 2021 JFDA 实测浓度分布 → **71 条**，INCI 匹配面 103 个）。
引擎三闸门已接入 v2 的 `human_noel`（临床闸门）。

## 四、云端模型统一阿里云

| 能力 | 服务/模型 | 降级路径 |
|---|---|---|
| 瓶身识别 | 百炼 `qwen-vl-max`（OpenAI 兼容模式） | mock（哈希确定性选库内产品） |
| 通感文案 | 百炼 `qwen-max` → `qwen-plus` | 规则模板 |
| OCR/条码 | 读光 OCR / 视觉智能（凭证位预留） | 手动输入通道 |

## 五、后台升级接口（前端零改动）

| 机制 | 说明 |
|---|---|
| API 版本化 | `/api/v1/*`，破坏性变更走 v2 |
| 版本信封 | 响应 `meta.engine / meta.models` 携带引擎与模型版本，升级可追溯 |
| 模型配置化 | `settings.models.*` 来自环境变量，换模型不改代码 |
| 引擎协议 | `RiskEngine` / `RecognitionProvider` Protocol，QRA 精细化=新增实现+配置切换 |
| 数据热更新 | `POST /api/v1/admin/ingredients/import`（seed JSON 重载，补数据无需重新部署） |
| Prompt 外置 | 通感文案三分支模板在 `orchestration/llm.py::PROMPTS`，可后台调优 |
| 权重/分位线可配 | `data/seed/config.json`（聚合权重、P90/P99 策略、氧化参数、置信度阈值） |

## 六、赛前待办（P0 清单）

- [x] ~~补齐致敏原 NESIL/限值~~（已由 `build_allergens_v2.py` 完成 71 条文献级数据，2026-09-17）
- [ ] 开通百炼 `DASHSCOPE_API_KEY`，冒烟 `POST /api/v1/recognition/image`
- [ ] 读光 OCR / 视觉智能条码凭证接入（providers.py 内 TODO 位）
- [ ] 黄金案例预缓存（断网演示兜底）、路演脚本、改造 `技术层/tongyi-mermaid*.png` 架构图

## 七、无障碍设计

大字号切换（A+）、Web Speech 中文语音播报（失嗅/视障听觉通道）、触控目标 ≥44px、
`prefers-reduced-motion` 跟随系统、高对比配色、ECharts 图表均带 aria-label。
