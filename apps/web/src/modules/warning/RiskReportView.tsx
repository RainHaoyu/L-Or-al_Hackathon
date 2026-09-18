import type { IngredientFinding, RiskReport } from "../shared/api-types";
import { Card, EvidenceTag, LevelPill, Tag } from "../shared/components";

const GATE_LABEL: Record<string, string> = {
  qra2: "QRA2 概率模型", ifra: "IFRA 限量", clinical: "临床阈值", banned: "禁用成分",
};

const OVERALL_STYLE = {
  green: { bar: "bg-ok", icon: "✅", title: "可以安心使用", tint: "shadow-[0_0_40px_rgba(110,231,183,0.15)]" },
  yellow: { bar: "bg-warn", icon: "⚠️", title: "谨慎使用", tint: "shadow-[0_0_40px_rgba(252,211,77,0.15)]" },
  red: { bar: "bg-danger", icon: "⛔", title: "建议避免使用", tint: "shadow-[0_0_40px_rgba(253,164,175,0.18)]" },
} as const;

export function RiskSummary({ report }: { report: RiskReport }) {
  const s = OVERALL_STYLE[report.overall_level];
  const counts = { red: 0, yellow: 0, green: 0 };
  for (const f of report.ingredients) if (f.level) counts[f.level] += 1;
  return (
    <div className={`grad-ring glow-soft overflow-hidden rounded-2xl ${s.tint}`} role="status" aria-live="polite">
      <div aria-hidden className={`h-1 w-full ${s.bar}`} />
      <div className="p-5">
        <div className="flex items-center gap-3">
          <span aria-hidden className="text-4xl">{s.icon}</span>
          <div className="min-w-0">
            <p className="text-lg font-bold text-ink">综合判定 · {s.title}</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-2">{report.summary}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-rose-400/10 px-3 py-1 text-danger ring-1 ring-danger/30">红 {counts.red}</span>
          <span className="rounded-full bg-amber-400/10 px-3 py-1 text-warn ring-1 ring-warn/30">黄 {counts.yellow}</span>
          <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-ok ring-1 ring-ok/30">绿 {counts.green}</span>
          <span className="rounded-full bg-white/5 px-3 py-1 text-ink-2 ring-1 ring-white/15">
            判定线 {report.population.percentile_policy} × 阈值 ×{report.population.threshold_multiplier}
          </span>
        </div>
      </div>
    </div>
  );
}

export function PopulationFlags({ report }: { report: RiskReport }) {
  if (report.population.special_flags.length === 0) return null;
  return (
    <Card title="人群专属提示">
      <ul className="space-y-2">
        {report.population.special_flags.map((f, i) => (
          <li key={i} className="rounded-lg bg-white/5 px-3 py-2 text-sm text-ink ring-1 ring-white/10">
            {f}
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function OxidationCard({ report }: { report: RiskReport }) {
  const o = report.oxidation;
  if (!o.applicable) return null;
  const d = Math.min(o.d_value ?? 0, 1);
  const barColor = o.level === "green" ? "bg-ok" : o.level === "yellow" ? "bg-warn" : "bg-danger";
  return (
    <Card title="氧化动态风险（估算）· 嗅觉替代预警">
      <div className="mb-2 flex items-center gap-2">
        <LevelPill level={o.level} small />
        <span className="text-sm text-ink-2">影响成分：{o.substances.join("、")}</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-white/10" role="img"
        aria-label={`氧化程度 ${(d * 100).toFixed(0)}%`}>
        <div className={`h-full ${barColor} transition-all`} style={{ width: `${d * 100}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-xs text-ink-3">
        <span>D&lt;0.2 正常</span><span>0.2–0.5 减少</span><span>≥0.5 不再使用</span>
      </div>
      {o.advice && <p className="mt-2 text-sm text-ink">{o.advice}</p>}
      <p className="mt-2 text-xs text-ink-3">{o.model_note}</p>
    </Card>
  );
}

export function IngredientDetails({ report }: { report: RiskReport }) {
  return (
    <Card title={`逐成分预警明细（${report.ingredients.length}）`}>
      <ul className="space-y-3">
        {report.ingredients.map((f) => <IngredientRow key={f.inci} f={f} />)}
      </ul>
      {report.data_insufficient.length > 0 && (
        <div className="mt-4 rounded-xl bg-white/5 p-3 ring-1 ring-white/10">
          <p className="text-sm font-medium text-warn">数据不足成分（显式标注，不静默降级）</p>
          <p className="mt-1 text-sm text-ink-2">{report.data_insufficient.join("、")}</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-1.5">
        <Tag>三闸门：QRA2 / 临床 / IFRA 取最严</Tag>
        <Tag>AEL=NESIL÷SAF</Tag>
        <Tag>CEL 蒙特卡洛 N=10000</Tag>
        <Tag>固定种子可复算</Tag>
      </div>
    </Card>
  );
}

function IngredientRow({ f }: { f: IngredientFinding }) {
  return (
    <li className="rounded-xl bg-panel-2 p-3 ring-1 ring-white/10">
      <div className="flex flex-wrap items-center gap-2">
        {f.level && <LevelPill level={f.level} small />}
        <span className="font-semibold text-ink">{f.name_zh}</span>
        <span className="text-xs text-ink-3">{f.inci}</span>
        {f.banned_eu && <span className="rounded bg-danger/15 px-1.5 py-0.5 text-xs text-danger ring-1 ring-danger/30">欧盟禁用</span>}
        {f.evidence_level && <EvidenceTag level={f.evidence_level} />}
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-2 sm:grid-cols-3">
        {f.concentration_pct != null && <div>浓度 {f.concentration_pct}%</div>}
        {f.ael != null && <div>AEL {f.ael}</div>}
        {f.cel_p99 != null && <div>CEL P50/P90/P99 {f.cel_p50}/{f.cel_p90}/{f.cel_p99}</div>}
        {f.margin_p99 != null && (
          <div>余量 P99 <b className={f.margin_p99 < 1 ? "text-danger" : "text-ok"}>{f.margin_p99}</b></div>
        )}
        {f.gate && <div>主导闸门 {GATE_LABEL[f.gate] ?? f.gate}</div>}
        {f.decision_percentile && <div>判定线 {f.decision_percentile}</div>}
      </dl>
      {f.data_note && <p className="mt-2 text-xs text-ink-2">{f.data_note}</p>}
      {f.note && <p className="mt-1 text-xs text-ink-3">{f.note}</p>}
    </li>
  );
}
