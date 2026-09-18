import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../modules/shared/api";
import type { AnalyzeData, AnalyzeRequest, Meta, PopulationKey, ProductRef } from "../modules/shared/api-types";
import { Card, ErrorBanner, Stepper, TabBar } from "../modules/shared/components";
import ProfileSelector, { POPULATIONS } from "../modules/profile/ProfileSelector";
import CapturePanel from "../modules/capture/CapturePanel";
import {
  IngredientDetails,
  OxidationCard,
  PopulationFlags,
  RiskSummary,
} from "../modules/warning/RiskReportView";
import VisionView from "../modules/vision/VisionView";

const QUICK_CASES: { label: string; req: Partial<AnalyzeRequest> }[] = [
  { label: "🧪 黄金算例 · 柠檬烯5%（健康成人）", req: { product: { product_id: "golden-limonene" }, profile: "healthy" } },
  { label: "🌸 兰蔻「美丽人生」· 敏感肌", req: { product: { product_id: "lancome-la-vie-est-belle-edp" }, profile: "sensitive" } },
  { label: "🌊 Margiela「航海日」· 失嗅人群（开封90天）", req: { product: { product_id: "margiela-sailing-day-edt" }, profile: "anosmic", oxidation: { opened_days: 90, temp_c: 25, light: 0.3 } } },
  { label: "🤰 YSL「先锋男士」· 孕期（含禁用 Lilial 红灯演示）", req: { product: { product_id: "ysl-lhomme-edt" }, profile: "pregnant" } },
];

const RESULT_TABS = [
  { key: "warning", label: "预警报告" },
  { key: "vision", label: "香味可视化" },
  { key: "details", label: "成分明细" },
];

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState<PopulationKey>("healthy");
  const [productRef, setProductRef] = useState<ProductRef | null>(null);
  const [productLabel, setProductLabel] = useState("");
  const [openedDays, setOpenedDays] = useState(0);
  const [tempC, setTempC] = useState(25);
  const [light, setLight] = useState(0.3);
  const [coLotion, setCoLotion] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeData | null>(null);
  const [activeTab, setActiveTab] = useState("warning");
  const [largeFont, setLargeFont] = useState(false);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.health().then(({ data, meta: m }) => {
      if (data.status === "ok") setMeta(m);
    }).catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    document.documentElement.style.fontSize = largeFont ? "18px" : "";
    return () => {
      document.documentElement.style.fontSize = "";
    };
  }, [largeFont]);

  function onSelectProduct(ref: ProductRef | null, lbl?: string) {
    setProductRef(ref);
    setProductLabel(lbl ?? "");
  }

  async function analyze(override?: Partial<AnalyzeRequest>, refOverride?: ProductRef | null) {
    const product = refOverride !== undefined ? refOverride : productRef;
    if (!product) {
      setError("请先通过 搜索/拍照/条码/手动 通道选择一款香水或输入成分表（步骤②）");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const merged: AnalyzeRequest = {
        product,
        profile,
        oxidation: { opened_days: openedDays, temp_c: tempC, light },
        co_use: coLotion ? { body_lotion: 0.5 } : {},
        ...override,
      };
      const { data } = await api.analyze(merged);
      setResult(data);
      setActiveTab("warning");
      // 分析完成 → 平滑滚动至结果画布
      requestAnimationFrame(() => {
        canvasRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "分析失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  function quickCase(qc: { label: string; req: Partial<AnalyzeRequest> }) {
    setProfile(qc.req.profile ?? "healthy");
    const ref = qc.req.product ?? null;
    setProductRef(ref);
    setProductLabel(qc.label.replace(/^[^\s]+\s/, ""));
    if (qc.req.oxidation) {
      setOpenedDays(qc.req.oxidation.opened_days ?? 0);
      setTempC(qc.req.oxidation.temp_c ?? 25);
      setLight(qc.req.oxidation.light ?? 0.3);
    }
    analyze(qc.req, ref);
  }

  const productName = result?.product ? `${result.product.brand} · ${result.product.name}` : productLabel || "手动成分分析";

  return (
    <div className="min-h-screen pb-24 md:pb-10">
      {/* —— Hero —— */}
      <header className="hero-aura border-b border-white/10">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 pb-6 pt-8">
          <div className="min-w-0 flex-1">
            <p className="mb-1 text-xs font-medium uppercase tracking-[0.25em] text-ink-3">
              L'ORÉAL BEAUTY TECH HACKATHON · 无界体验家
            </p>
            <h1 className="grad-text text-2xl font-black tracking-tight sm:text-3xl md:text-4xl">
              用爱(AI)，让美触手可及
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-2">
              致敏原智能预警 <span className="text-gold">QRA2</span> ＋ 香味可视化——为失嗅 / 敏感肌 / 孕期 / 鼻炎人群，
              把实验室的黑科技变成梳妆台前的温度。
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs">
            {meta && (
              <span className="rounded-full bg-white/5 px-3 py-1.5 text-ink-2 ring-1 ring-white/15">
                {meta.engine}{meta.mock_mode ? " · mock 演示" : " · 百炼已接入"}
              </span>
            )}
            <button
              onClick={() => setLargeFont((v) => !v)}
              aria-pressed={largeFont}
              aria-label="切换大字号"
              className="rounded-full bg-white/5 px-3 py-1.5 font-semibold text-ink ring-1 ring-white/15 hover:bg-white/10"
            >
              {largeFont ? "A-" : "A+"}
            </button>
          </div>
        </div>
        <div aria-hidden className="light-band mx-auto max-w-6xl" />
      </header>

      <main className="mx-auto mt-6 max-w-6xl space-y-5 px-4">
        {error && <ErrorBanner message={error} onRetry={() => analyze()} />}

        {/* —— 步进器 —— */}
        <Card>
          <Stepper
            steps={[
              { title: "① 你是谁 · 人群画像", done: true },
              { title: "② 识别香水", done: !!productRef },
              { title: "③ 情境与开始分析", done: !!result },
            ]}
          />
          <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]">
            <section aria-label="步骤1 选择人群画像" className="min-w-0">
              <h2 className="mb-2 text-sm font-semibold text-ink-2 xl:hidden">① 你是谁（人群画像）</h2>
              <ProfileSelector value={profile} onChange={setProfile} />
            </section>
            <section aria-label="步骤2 识别香水" className="min-w-0">
              <CapturePanel selected={productRef} selectedLabel={productLabel} onSelect={onSelectProduct} />
            </section>
            <section aria-label="步骤3 使用情境与开始分析" className="min-w-0">
              <h2 className="mb-2 text-sm font-semibold text-ink-2 xl:hidden">③ 使用情境（可选）</h2>
              <div className="space-y-3 rounded-2xl bg-panel p-4 text-sm ring-1 ring-white/10">
                <label className="block">
                  <span className="flex justify-between text-ink-2">
                    开封天数 <b className="text-ink">{openedDays} 天</b>
                  </span>
                  <input type="range" min={0} max={180} value={openedDays} aria-label="开封天数"
                    onChange={(e) => setOpenedDays(Number(e.target.value))}
                    className="mt-1 w-full accent-grad-b" />
                </label>
                <label className="block">
                  <span className="flex justify-between text-ink-2">
                    储存温度 <b className="text-ink">{tempC}℃</b>
                  </span>
                  <input type="range" min={5} max={40} value={tempC} aria-label="储存温度"
                    onChange={(e) => setTempC(Number(e.target.value))}
                    className="mt-1 w-full accent-grad-b" />
                </label>
                <label className="block">
                  <span className="flex justify-between text-ink-2">
                    光照强度 <b className="text-ink">{light.toFixed(1)}</b>
                  </span>
                  <input type="range" min={0} max={1} step={0.1} value={light} aria-label="光照强度"
                    onChange={(e) => setLight(Number(e.target.value))}
                    className="mt-1 w-full accent-grad-b" />
                </label>
                <label className="flex items-center gap-2 text-ink-2">
                  <input type="checkbox" checked={coLotion} onChange={(e) => setCoLotion(e.target.checked)}
                    className="h-5 w-5 accent-grad-b" />
                  同日使用含同成分身体乳（QRA2 聚合暴露）
                </label>
                {!productRef && (
                  <p className="rounded-lg bg-warn/10 px-3 py-2 text-xs text-warn ring-1 ring-warn/30">
                    请先完成步骤② 选择香水，或使用下方「一键演示案例」
                  </p>
                )}
                <button
                  onClick={() => analyze()}
                  disabled={loading || !productRef}
                  className="grad-bg glow w-full rounded-xl py-3.5 text-base font-bold text-white disabled:opacity-40 disabled:shadow-none"
                >
                  {loading ? "QRA2 计算中…" : productRef ? "开始分析 · 生成预警与可视化" : "选择香水后开始分析"}
                </button>
              </div>
            </section>
          </div>
        </Card>

        {/* —— 结果画布 —— */}
        <div ref={canvasRef} className="scroll-mt-4">
          {loading && (
            <div className="flex items-center justify-center gap-3 rounded-2xl bg-panel p-10 ring-1 ring-white/10">
              <span className="grad-bg h-5 w-5 animate-spin rounded-full" />
              <span className="text-sm text-ink-2">QRA2 蒙特卡洛计算中（N=10000）· 生成通感可视化…</span>
            </div>
          )}
          {!loading && result && (
            <div className="space-y-4">
              <RiskSummary report={result.risk} />
              <TabBar tabs={RESULT_TABS} active={activeTab} onChange={setActiveTab} />
              {activeTab === "warning" && (
                <div className="grid gap-4 md:grid-cols-2">
                  <OxidationCard report={result.risk} />
                  <PopulationFlags report={result.risk} />
                </div>
              )}
              {activeTab === "vision" && <VisionView vision={result.vision} productName={productName} />}
              {activeTab === "details" && <IngredientDetails report={result.risk} />}
              <p className="text-xs text-ink-3">
                {productName} · 识别通道 {result.recognition_channel}
                {result.recognition_confidence != null && `（置信度 ${result.recognition_confidence}）`}
                {result.vision.degraded && (
                  <span className="ml-1 text-warn">· 可视化降级（原因见「香味可视化」页）</span>
                )}
              </p>
            </div>
          )}
          {!loading && !result && (
            <div className="space-y-4">
              {productRef ? (
                /* 已选香水 → 动态就绪面板：一条明确的下一步 */
                <Card variant="ring" className="!p-6">
                  <div className="flex flex-col items-start gap-4 md:flex-row md:items-center">
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold uppercase tracking-widest text-ok">已就绪 · Ready</p>
                      <p className="mt-2 truncate text-lg font-bold text-ink md:text-xl">
                        {productLabel || "已选择香水"}
                        <span className="mx-2 text-ink-3">×</span>
                        {POPULATIONS.find((p) => p.key === profile)?.label}
                      </p>
                      <p className="mt-1 text-sm text-ink-2">
                        点击右侧按钮：QRA2 蒙特卡洛（P50/P90/P99）预警 + 香味可视化一次生成。
                      </p>
                    </div>
                    <button
                      onClick={() => analyze()}
                      className="grad-bg glow flex-none rounded-xl px-8 py-4 text-lg font-bold text-white"
                    >
                      开始分析 →
                    </button>
                  </div>
                </Card>
              ) : (
                /* 未选香水 → 简介 + 一键演示 */
                <Card className="!p-6">
                  <p className="text-4xl" aria-hidden>🧪 → 🌈</p>
                  <h2 className="mt-3 text-lg font-bold text-ink">双核心引擎已就绪</h2>
                  <p className="mt-2 text-sm leading-6 text-ink-2">
                    <span className="text-ink">核心① 致敏预警</span>：IFRA QRA 2.0 简化实现——CEL 概率化 +
                    蒙特卡洛（P50/P90/P99）＋ 聚合暴露 ＋ 三闸门取最严。
                    <span className="text-ink">核心② 香味可视化</span>：香调→色彩 / 粒子 / 雷达 / 通感文字，
                    为失嗅人群提供嗅觉替代通道。
                  </p>
                  <p className="mt-3 text-xs text-ink-3">可从上方步骤② 搜索 / 拍照 / 条码 / 手动选择香水，或直接一键演示：</p>
                </Card>
              )}
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-ink-3">一键演示案例</p>
                <div className="grid gap-2 md:grid-cols-2">
                  {QUICK_CASES.map((qc) => (
                    <button key={qc.label} onClick={() => quickCase(qc)}
                      className="grad-ring-gold rounded-xl px-4 py-3 text-left text-sm font-medium text-ink hover:brightness-110">
                      {qc.label}
                    </button>
                  ))}
                </div>
              </div>
              <details className="rounded-2xl bg-panel p-4 ring-1 ring-white/10">
                <summary className="cursor-pointer text-sm font-semibold text-ink-2 hover:text-ink">
                  QRA2 方法卡 · 这套评分是怎么算的？
                </summary>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-ink-2">
                  <li>CEL 五参数升级为概率分布（LogNormal / Triangular / 离散 / Uniform / Beta）</li>
                  <li>拉丁超立方抽样 N=10000，固定种子可复算</li>
                  <li>聚合暴露 CEL_total = Σ(CEL×w)（同成分身体乳/洗发水共使用）</li>
                  <li>分位判定 P50/P90/P99；脆弱人群自动升至 P99 分位线</li>
                  <li>三闸门取最严：QRA2 ∨ 临床阈值 ∨ IFRA 限量；缺失标注 evidence_level</li>
                  <li>数据不足成分显式标注，绝不静默降级</li>
                </ol>
                <p className="mt-3 text-xs text-ink-3">
                  参考口径：IFRA/RIFM QRA 2.0（概率化聚合暴露）；Api et al. 2008；SCCS 意见回应（三闸门双轨）。
                </p>
              </details>
            </div>
          )}
        </div>
      </main>

      <footer className="mx-auto mt-8 max-w-6xl px-4 pb-6 text-xs leading-5 text-ink-3">
        <p>
          模型说明：QRA2 为 IFRA QRA 2.0 思路的简化自研实现（概率化 CEL + 拉丁超立方抽样 N=10000 固定种子 +
          P50/P90/P99 分位判定 + 三闸门：QRA2/临床阈值/IFRA 限量取最严，缺失标注 evidence_level）。
          数据来源：26 种 EU 致敏原（数据层清洗）、文献级 NESIL（RIFM/Na 2022/Lalko 2008/Api 2022）、EU 2023/1545；
          演示估计值已叠加保守惩罚并标注。
        </p>
        <p className="mt-1">
          本系统为黑客松演示用途，风险结论不构成医学建议；皮肤敏感者请以斑贴试验与医嘱为准。
          云端模型：阿里云百炼 qwen-vl-max / qwen-max。
        </p>
      </footer>

      {/* 手机端吸底主操作 */}
      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-white/10 bg-void/90 p-3 backdrop-blur md:hidden">
        <button
          onClick={() => analyze()}
          disabled={loading}
          className="grad-bg w-full rounded-xl py-3 text-base font-bold text-white shadow disabled:opacity-50"
        >
          {loading ? "分析中…" : "开始分析 · 生成预警与可视化"}
        </button>
      </div>
    </div>
  );
}
