import { Link } from 'react-router'
import { CircleAlert, CircleCheck, TriangleAlert } from 'lucide-react'
import { useApp, useRegister } from '../lib/state'
import {
  IFRA,
  POPULATIONS,
  REPORT,
  STORAGE_OPTIONS,
  buildIngredients,
  dLevel,
  evaluate,
  getPerfume,
  panelScenario,
} from '../lib/aura'
import { analyzeIngredient } from '../lib/qra2/engine'
import { EvidenceTag, RiskMark } from '../components/RiskMark'

const BANNER_ICON = { high: CircleAlert, mid: TriangleAlert, low: CircleCheck } as const
const BANNER_BG: Record<string, string> = {
  high: 'var(--risk-high)',
  mid: 'var(--risk-mid)',
  low: 'var(--risk-low)',
}

/** 分位条：P50/P90/P99 对 AEL 阈值线（数值来自 QRA2 引擎实算） */
function PercentileBars({
  ael,
  p50,
  p90,
  p99,
  caption,
}: {
  ael: number
  p50: number
  p90: number
  p99: number
  caption: string
}) {
  const max = Math.max(ael, p99) * 1.15
  const rows = [
    { key: 'P50', v: p50, used: false },
    { key: 'P90', v: p90, used: false },
    { key: 'P99', v: p99, used: true },
  ]
  return (
    <div>
      <div className="relative space-y-3">
        <div
          aria-hidden
          className="absolute top-[-6px] bottom-[-6px] z-10 w-px bg-gold"
          style={{ left: `${(ael / max) * 100}%` }}
        />
        <div
          className="absolute top-[-30px] z-10 -translate-x-1/2 text-xs whitespace-nowrap text-gold tabular"
          style={{ left: `${(ael / max) * 100}%` }}
        >
          AEL {ael.toFixed(1)}
        </div>
        {rows.map((r) => (
          <div key={r.key} className="flex items-center gap-3">
            <span className="w-10 text-sm text-muted-foreground tabular">{r.key}</span>
            <div className="h-7 flex-1 rounded-xs bg-muted">
              <div
                className="flex h-7 items-center justify-end rounded-xs pr-2 text-xs font-medium text-white tabular"
                style={{
                  width: `${Math.max((r.v / max) * 100, 12)}%`,
                  background: r.v >= ael ? 'var(--risk-high)' : r.used ? 'var(--risk-mid)' : 'var(--risk-low)',
                }}
              >
                {r.v.toFixed(1)}
              </div>
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{caption}</p>
    </div>
  )
}

/** 氧化 D 值：0→1 进度，0.2 / 0.5 分档标记（数值来自分析流选择） */
function OxidationGauge({ d, months, storageName }: { d: number; months: number; storageName: string }) {
  const dl = dLevel(d)
  return (
    <div>
      <div className="relative h-9 overflow-hidden rounded-full bg-muted">
        <div aria-hidden className="absolute inset-y-0 left-[20%] w-px bg-foreground/25" />
        <div aria-hidden className="absolute inset-y-0 left-[50%] w-px bg-foreground/25" />
        <div
          className="flex h-9 items-center justify-end rounded-full pr-3 text-sm font-semibold text-white tabular"
          style={{ width: `${Math.max(d * 100, 14)}%`, background: dl.color }}
        >
          D = {d.toFixed(2)}
        </div>
      </div>
      <div aria-hidden className="mt-1 flex justify-between text-xs text-muted-foreground tabular">
        <span>0.2 中风险</span>
        <span>0.5 高风险</span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        开封 {months} 个月 · {storageName}。氧化程度越高，萜烯类生成的氢过氧化物越多；
        失嗅人群无法靠嗅觉察觉变质，此项即嗅觉替代预警。
      </p>
    </div>
  )
}

export default function Report() {
  useRegister('light')
  const { population, perfumeId, openedMonths, storage, oxidationD, engineMeta } = useApp()
  const picked = getPerfume(perfumeId)
  const popName = POPULATIONS.find((p) => p.key === population)?.name ?? '敏感肌'
  const storageName = STORAGE_OPTIONS.find((s) => s.key === storage)?.name ?? '室温'
  const verdict = evaluate(population, perfumeId, oxidationD)
  const rows = buildIngredients(perfumeId, oxidationD, population)
  const BannerIcon = BANNER_ICON[verdict.level]

  // QRA2 引擎实算（LHS 一万次，固定种子可复算）
  const scenario = panelScenario(perfumeId)
  const qra = analyzeIngredient({ name: scenario.name, concPct: scenario.concPct, population })
  const panelCaption = `${scenario.label}。蒙特卡洛一万次（拉丁超立方，固定种子，重算逐位一致）；
    当前画像 ${popName} 判定线 ${qra.policy} × T_pop ${qra.tPop}，判定线余量 ${qra.marginPolicy?.toFixed(2) ?? '—'}；
    点估计 AEL/CEL = ${(qra.ael && qra.pointCEL ? qra.ael / qra.pointCEL : 0).toFixed(1)}（单位 μg/cm²/day）。`

  return (
    <main className="mx-auto max-w-5xl px-4 pb-24 sm:px-6">
      {/* 检验单抬头 */}
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border py-10">
        <div>
          <p className="text-sm text-muted-foreground">预警报告 · QRA2</p>
          <h1 className="font-display mt-1 text-4xl">
            {picked.name}
            {picked.en && <span className="ml-3 text-xl text-muted-foreground italic">{picked.en}</span>}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {picked.brand} · {picked.familyZh} · {picked.concentration} · 身份画像：{popName} · 四道闸门取最严
          </p>
          {engineMeta && (
            <p className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
              <span aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: engineMeta.source === 'backend' ? 'var(--risk-low)' : 'var(--risk-mid)' }} />
              引擎 {engineMeta.engine}
              {engineMeta.source === 'backend' ? ' · 后端计算' : ' · 本地引擎（后端不可达）'}
              {engineMeta.models ? ` · 文案 ${engineMeta.models}` : ''}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/#analyze"
            className="focus-visible-strong inline-flex min-h-11 items-center rounded-full border border-border px-5 py-2.5 text-sm hover:bg-secondary"
          >
            重新选择
          </Link>
          <Link
            to="/vision"
            className="focus-visible-strong inline-flex min-h-11 items-center rounded-full border border-border px-5 py-2.5 text-sm hover:bg-secondary"
          >
            查看这瓶的香气显影
          </Link>
        </div>
      </header>

      {/* 判定横幅（随选择实时变化） */}
      <section
        aria-label="综合判定"
        className="mt-8 rounded-lg p-6 text-paper sm:p-8"
        style={{ background: BANNER_BG[verdict.level] }}
      >
        <div className="flex items-start gap-4">
          <BannerIcon size={30} strokeWidth={2.2} aria-hidden className="mt-1 shrink-0" />
          <div>
            <p className="font-display text-3xl">{verdict.headline}</p>
            <ul className="mt-3 max-w-2xl space-y-1.5">
              {verdict.reasons.map((r, i) => (
                <li key={i} className="leading-relaxed text-paper/90">
                  {r}
                </li>
              ))}
            </ul>
            <p className="mt-4 max-w-2xl border-t border-paper/25 pt-3 text-sm leading-relaxed text-paper/85">
              <span className="font-medium">行动建议　</span>
              {verdict.advice}
            </p>
          </div>
        </div>
      </section>

      {/* 读数区：主导闸门 / 命中数 / 判定 */}
      <section
        aria-label="关键读数"
        className="grid border-b border-border py-8 sm:grid-cols-3 sm:divide-x sm:divide-border"
      >
        <div className="pb-6 sm:pb-0 sm:pr-8">
          <p className="text-sm text-muted-foreground">主导闸门</p>
          <p className="font-display mt-1 text-3xl">{verdict.dominantGate}</p>
          <p className="mt-1 text-sm text-muted-foreground">QRA2 分位 ∨ 临床 ∨ 氧化 ∨ 禁用</p>
        </div>
        <div className="py-6 sm:px-8">
          <p className="text-sm text-muted-foreground">致敏原命中</p>
          <p className="font-display mt-1 text-3xl">{verdict.hits}</p>
          <p className="mt-1 text-sm text-muted-foreground">证据等级逐条标注，数据不足不静默</p>
        </div>
        <div className="pt-6 sm:pt-0 sm:pl-8">
          <p className="text-sm text-muted-foreground">综合判定</p>
          <RiskMark level={verdict.level} className="mt-2 text-xl" />
          <p className="mt-1 text-sm text-muted-foreground">换一个人群画像，结论可能不同</p>
        </div>
      </section>

      {/* 两栏：分位判定 + 氧化 */}
      <section className="grid gap-12 border-b border-border py-10 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-2xl">概率化暴露判定</h2>
          <div className="mt-8">
            {qra.p50 != null && qra.p90 != null && qra.p99 != null && qra.ael != null ? (
              <PercentileBars ael={qra.ael} p50={qra.p50} p90={qra.p90} p99={qra.p99} caption={panelCaption} />
            ) : (
              <p className="text-sm text-muted-foreground">{REPORT.percentiles.caption}</p>
            )}
          </div>
        </div>
        <div>
          <h2 className="font-display text-2xl">氧化动态风险</h2>
          <div className="mt-8">
            <OxidationGauge d={oxidationD} months={openedMonths} storageName={storageName} />
          </div>
        </div>
      </section>

      {/* 人群提示 */}
      <section className="border-b border-border py-8">
        <h2 className="font-display text-2xl">身份画像如何影响判定</h2>
        <p className="mt-4 max-w-3xl leading-relaxed text-muted-foreground">{REPORT.populationNote}</p>
      </section>

      {/* 成分明细表 */}
      <section aria-labelledby="ingredients" className="py-10">
        <h2 id="ingredients" className="font-display text-2xl">
          成分明细
        </h2>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th scope="col" className="py-3 pr-4 font-normal">成分</th>
                <th scope="col" className="py-3 pr-4 font-normal">浓度（典型值）</th>
                <th scope="col" className="py-3 pr-4 font-normal">Cat4 限值</th>
                <th scope="col" className="py-3 pr-4 font-normal">判定</th>
                <th scope="col" className="py-3 pr-4 font-normal">主导闸门</th>
                <th scope="col" className="py-3 pr-4 font-normal">证据等级</th>
                <th scope="col" className="py-3 font-normal">说明</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((ing) => (
                <tr key={ing.inci} className="border-b border-border/60 align-top">
                  <td className="py-4 pr-4">
                    <p className="font-medium">{ing.zh}</p>
                    <p className="text-xs text-muted-foreground">{ing.inci}</p>
                  </td>
                  <td className="py-4 pr-4 tabular">{ing.conc}</td>
                  <td className="py-4 pr-4 tabular">{ing.limitPct != null ? `≤ ${ing.limitPct}%` : '—'}</td>
                  <td className="py-4 pr-4">
                    <RiskMark level={ing.level} />
                  </td>
                  <td className="py-4 pr-4 text-muted-foreground">{ing.gate}</td>
                  <td className="py-4 pr-4">
                    <EvidenceTag evidence={ing.evidence} />
                  </td>
                  <td className="py-4 leading-relaxed text-muted-foreground">{ing.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
            真实数据口径：限值来自 {IFRA.amendment} Cat4 清单，成分清单来自 12 款经典香水分析；
            浓度未知项按文献典型值评估并显式标注——正式版将接 per-product 实测浓度（改进清单 P1-1 / P1-2）。
          </p>
        </div>
      </section>

      <footer className="border-t border-border py-8">
        <p className="text-xs leading-relaxed text-muted-foreground">{REPORT.disclaimer}</p>
      </footer>
    </main>
  )
}
