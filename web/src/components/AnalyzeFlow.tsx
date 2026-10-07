import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Camera, Keyboard, ScanBarcode, Search } from 'lucide-react'
import { useApp } from '../lib/state'
import { ANALYZE_TIMEOUT, ENGINE_BUDGET_MS, api } from '../lib/api'
import type { Candidate } from '../lib/api-types'
import {
  IFRA,
  INGREDIENT_DICT,
  PERFUMES,
  POPULATIONS,
  STORAGE_OPTIONS,
  dLevel,
  matchManualIngredient,
  parseManualIngredients,
  type ManualMatch,
} from '../lib/aura'
import { EvidenceTag, RiskMark } from './RiskMark'
import { cn } from '../lib/utils'

const CHANNELS = [
  { key: 'search', name: '搜索', Icon: Search },
  { key: 'photo', name: '拍照', Icon: Camera },
  { key: 'barcode', name: '条码', Icon: ScanBarcode },
  { key: 'manual', name: '手动', Icon: Keyboard },
] as const

type Channel = (typeof CHANNELS)[number]['key']

function StepHead({ n, title, picked }: { n: string; title: string; picked?: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-3">
      <span className="font-display text-3xl text-gold">{n}</span>
      <h3 className="text-lg font-semibold">{title}</h3>
      {picked && (
        <span className="rounded-full bg-secondary px-3 py-1 text-sm text-foreground">
          已选：{picked}
        </span>
      )}
    </div>
  )
}

function PerfumeOption({
  id,
  onPick,
  active,
}: {
  id: string
  onPick: () => void
  active: boolean
}) {
  const p = PERFUMES.find((x) => x.id === id)!
  return (
    <button
      onClick={onPick}
      aria-pressed={active}
      className={cn(
        'focus-visible-strong flex min-h-14 w-full flex-col items-start rounded-md border px-4 py-2.5 text-left transition-colors',
        active ? 'border-ink bg-ink text-paper' : 'border-border hover:bg-secondary',
      )}
    >
      <span className="text-sm opacity-70">{p.brand}</span>
      <span className="text-base font-medium">
        {p.name}
        <span className={cn('ml-2 text-xs font-normal', active ? 'opacity-70' : 'text-muted-foreground')}>
          {p.tag}
        </span>
      </span>
    </button>
  )
}

/** 首页三步引导流：身份画像 → 识别香水 → 使用情境 → 报告 */
export function AnalyzeFlow() {
  const navigate = useNavigate()
  const {
    population,
    setPopulation,
    mode,
    perfumeId,
    setPerfumeId,
    openedMonths,
    setOpenedMonths,
    storage,
    setStorage,
    oxidationD,
    setEngineMeta,
    setBackendText,
  } = useApp()
  const [channel, setChannel] = useState<Channel>('search')
  const [query, setQuery] = useState('')
  const [barcode, setBarcode] = useState('')
  const [manualParsed, setManualParsed] = useState<ManualMatch[] | null>(null)
  const [reportBusy, setReportBusy] = useState(false)
  /** 等待期间的阶段性提示（有 Key 时 /analyze 实测需 9–11 s，须给用户进度感） */
  const [reportStage, setReportStage] = useState('')
  const [photoBusy, setPhotoBusy] = useState(false)
  const [photoResult, setPhotoResult] = useState<{
    status: 'ok' | 'confirm' | 'error'
    confidence: number
    note: string
    candidates: Candidate[]
  } | null>(null)

  /**
   * 生成报告：后端引擎优先（版本信封），超时/断网自动回退本地引擎。
   *
   * mode 必须传真实模式：后端按 mode 选 prompt，写死 'normal' 会让失嗅模式的
   * AI 文案静默失效（那段长文案其实是前端本地拼的）。
   * 超时也按模式取（见 lib/api.ts 的 ANALYZE_TIMEOUT）：引擎约 5 s，
   * 失嗅模式文案长约 3 倍、耗时也约 3 倍，所以它的预算比另两种模式高。
   */
  const generateReport = async () => {
    if (reportBusy) return
    setReportBusy(true)
    const timeoutMs = ANALYZE_TIMEOUT[mode]
    const llmBudgetS = Math.round((timeoutMs - ENGINE_BUDGET_MS) / 1000)
    // 阶段提示按实测耗时切分：0s 连接 → 2s 计算闸门 → 5s 生成文案
    // （引擎实测 4.4–5.0 s，之后才是 LLM；anosmia 的 LLM 预算更长）
    const stages: [number, string][] = [
      [0, '正在连接后端引擎…'],
      [2000, '正在计算暴露量与四道闸门…（引擎约需 5 秒）'],
      [
        5000,
        `正在生成通感文案…（${mode === 'anosmia' ? '失嗅模式文案更长' : 'AI 模型响应较慢'}，最长约 ${llmBudgetS} 秒）`,
      ],
    ]
    const timers = stages.map(([ms, text]) => setTimeout(() => setReportStage(text), ms))
    /** 输入快照：后端文案必须与它绑定，Vision 页只在快照仍匹配时才显示 */
    const snapshot = { perfumeId, population, openedMonths, storage, mode }
    try {
      const r = await api.analyze({
        product_id: perfumeId,
        population,
        opened_months: openedMonths,
        storage,
        mode,
      })
      if (r.data) {
        setEngineMeta({ source: 'backend', engine: r.meta.engine ?? 'backend', models: r.data.synesthesia.model })
        // 后端算出的 AI 文案真正接上屏（此前只取了 model 做徽标，正文仍是本地拼的）
        setBackendText({
          ...snapshot,
          text: r.data.synesthesia.text ?? '',
          model: r.data.synesthesia.model ?? 'backend',
          engine: r.meta.engine,
        })
      } else {
        setEngineMeta({ source: 'local', engine: 'aura-web-local/1.0' })
        setBackendText(null)
      }
    } catch {
      setEngineMeta({ source: 'local', engine: 'aura-web-local/1.0' })
      setBackendText(null)
    } finally {
      timers.forEach(clearTimeout)
      setReportStage('')
      setReportBusy(false)
      navigate('/report')
    }
  }

  /** 真实拍照：上传 → 后端识别（qwen-vl-max 或 mock）→ 置信度 <0.7 转人工确认 */
  const onPhoto = async (file: File | undefined) => {
    if (!file || photoBusy) return
    setPhotoBusy(true)
    setPhotoResult(null)
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const fr = new FileReader()
        fr.onload = () => resolve(fr.result as string)
        fr.onerror = () => reject(new Error('read failed'))
        fr.readAsDataURL(file)
      })
      const r = await api.recognizeImage(dataUrl, file.name)
      const d = r.data
      if (d.status === 'ok' && d.product) {
        setPerfumeId(d.product.id)
        setPhotoResult({ status: 'ok', confidence: d.confidence ?? 0, note: `识别成功（${d.provider ?? 'api'}）`, candidates: [] })
      } else if (d.status === 'confirm') {
        setPhotoResult({
          status: 'confirm',
          confidence: d.confidence ?? 0,
          note: `${d.note || '置信度不足'}——请从候选中确认`,
          candidates: d.candidates ?? [],
        })
      } else {
        setPhotoResult({ status: 'error', confidence: 0, note: d.error || '识别失败', candidates: [] })
      }
    } catch {
      setPhotoResult({
        status: 'error',
        confidence: 0,
        note: '后端不可达（演示模式可点「模拟拍一瓶」体验降级策略）',
        candidates: [],
      })
    } finally {
      setPhotoBusy(false)
    }
  }

  /** 断网演示：mock 置信度 0.62 触发人工确认 */
  const simulatePhoto = () => {
    setPhotoResult({
      status: 'confirm',
      confidence: 0.62,
      note: '模拟识别（mock，置信度 0.62 < 0.7）——请从候选中确认',
      candidates: PERFUMES.slice(0, 3).map((p) => ({
        id: p.id,
        brand: p.brand,
        name: p.name,
        tag: p.familyZh,
      })),
    })
  }

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return PERFUMES
    return PERFUMES.filter((p) =>
      `${p.brand} ${p.name} ${p.tag}`.toLowerCase().includes(q),
    )
  }, [query])

  const picked = PERFUMES.find((p) => p.id === perfumeId)
  const popName = POPULATIONS.find((p) => p.key === population)?.name
  const storageName = STORAGE_OPTIONS.find((s) => s.key === storage)?.name
  const dl = dLevel(oxidationD)

  return (
    <section id="analyze" aria-labelledby="analyze-title" className="scroll-mt-24 border-t border-border py-14">
      <h2 id="analyze-title" className="font-display text-3xl">
        开始一次分析
      </h2>

      <div className="mt-10 space-y-12">
        {/* —— 第 1 步：身份画像 —— */}
        <div>
          <StepHead n="1" title="你是谁，决定阈值怎么算" picked={popName} />
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {POPULATIONS.map((p) => (
              <button
                key={p.key}
                onClick={() => setPopulation(p.key)}
                aria-pressed={population === p.key}
                className={cn(
                  'focus-visible-strong flex min-h-24 flex-col items-start justify-center rounded-md border px-4 py-3 text-left transition-colors',
                  population === p.key
                    ? 'border-ink bg-ink text-paper'
                    : 'border-border hover:bg-secondary',
                )}
              >
                <span className="text-base font-semibold">{p.name}</span>
                <span className={cn('mt-1 text-xs leading-snug', population === p.key ? 'text-paper/75' : 'text-muted-foreground')}>
                  {p.note}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* —— 第 2 步：识别香水（四通道） —— */}
        <div>
          <StepHead n="2" title="认出这一瓶香水" picked={picked ? `${picked.brand} ${picked.name}` : undefined} />
          <div role="tablist" aria-label="识别通道" className="mt-5 flex flex-wrap gap-2">
            {CHANNELS.map((c) => (
              <button
                key={c.key}
                role="tab"
                aria-selected={channel === c.key}
                onClick={() => setChannel(c.key)}
                className={cn(
                  'focus-visible-strong inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm transition-colors',
                  channel === c.key ? 'border-ink bg-ink text-paper' : 'border-border hover:bg-secondary',
                )}
              >
                <c.Icon size={15} aria-hidden />
                {c.name}
              </button>
            ))}
          </div>

          <div className="mt-5">
            {channel === 'search' && (
              <div>
                <label htmlFor="perfume-search" className="text-sm text-muted-foreground">
                  输入品牌或名字
                </label>
                <input
                  id="perfume-search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="例如：鸢尾、兰蔻、航海"
                  className="focus-visible-strong mt-2 min-h-12 w-full max-w-md rounded-md border border-input bg-card px-4 text-base outline-none placeholder:text-muted-foreground/70 focus-visible:border-ring"
                />
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {results.map((p) => (
                    <PerfumeOption key={p.id} id={p.id} active={perfumeId === p.id} onPick={() => setPerfumeId(p.id)} />
                  ))}
                  {results.length === 0 && (
                    <p className="text-sm text-muted-foreground">
                      没有匹配。换个关键词，或切到「手动」通道粘贴成分表。
                    </p>
                  )}
                </div>
              </div>
            )}

            {channel === 'photo' && (
              <div className="max-w-2xl rounded-md border border-border bg-card p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <label
                    className={cn(
                      'focus-visible-strong inline-flex min-h-11 cursor-pointer items-center rounded-full border border-border px-4 text-sm hover:bg-secondary',
                      photoBusy && 'pointer-events-none opacity-60',
                    )}
                  >
                    {photoBusy ? '识别中…' : '拍摄 / 上传瓶身照片'}
                    <input
                      type="file"
                      accept="image/*"
                      className="sr-only"
                      onChange={(e) => onPhoto(e.target.files?.[0])}
                      disabled={photoBusy}
                    />
                  </label>
                  <button
                    onClick={simulatePhoto}
                    className="focus-visible-strong inline-flex min-h-11 items-center rounded-full border border-border px-4 text-sm hover:bg-secondary"
                  >
                    模拟拍一瓶（断网演示）
                  </button>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  照片将送至后端识别（已配置 Key 时走 qwen-vl-max，否则 mock）；
                  置信度低于 0.7 一律转人工确认，杜绝误识别直接进入风险判定。
                </p>
                {photoResult && (
                  <div className="mt-4 border-t border-border pt-4">
                    <p
                      className={cn(
                        'text-sm',
                        photoResult.status === 'ok'
                          ? 'text-risk-low'
                          : photoResult.status === 'error'
                            ? 'text-risk-mid'
                            : 'text-muted-foreground',
                      )}
                    >
                      {photoResult.status === 'ok' && '✓ '}
                      {photoResult.note}
                    </p>
                    {photoResult.candidates.length > 0 && (
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        {photoResult.candidates.map((c) => (
                          <PerfumeOption
                            key={c.id}
                            id={c.id}
                            active={perfumeId === c.id}
                            onPick={() => {
                              setPerfumeId(c.id)
                              setPhotoResult(null)
                            }}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {channel === 'barcode' && (
              <div className="max-w-xl rounded-md border border-border bg-card p-5">
                <label htmlFor="barcode-input" className="text-sm text-muted-foreground">
                  输入包装上的条形码（EAN）
                </label>
                <div className="mt-2 flex gap-2">
                  <input
                    id="barcode-input"
                    value={barcode}
                    onChange={(e) => setBarcode(e.target.value)}
                    inputMode="numeric"
                    placeholder="例如：361427333 适配演示样本"
                    className="focus-visible-strong min-h-12 flex-1 rounded-md border border-input bg-card px-4 text-base outline-none placeholder:text-muted-foreground/70 focus-visible:border-ring"
                  />
                  <button
                    onClick={() => setPerfumeId('irriscent-dawn')}
                    className="focus-visible-strong min-h-12 shrink-0 rounded-md bg-ink px-5 text-sm font-medium text-paper"
                  >
                    查询
                  </button>
                </div>
                <p className="mt-3 text-sm text-muted-foreground">
                  演示库按条码直接返回「晨光鸢尾」。正式版接 GTIN 数据库。
                </p>
              </div>
            )}

            {channel === 'manual' && (
              <div className="max-w-2xl rounded-md border border-border bg-card p-5">
                <label htmlFor="manual-input" className="text-sm text-muted-foreground">
                  粘贴成分表——逗号、顿号、换行分隔都可以；浓度可选（如「LIMONENE: 0.8%」，也支持纯名称串）
                </label>
                <textarea
                  id="manual-input"
                  rows={4}
                  placeholder={'Alcohol Denat., Parfum, Aqua, Limonene, Linalool, Citral, Coumarin, Geraniol, Eugenol, Benzyl Salicylate'}
                  onChange={() => setManualParsed(null)}
                  className="focus-visible-strong mt-2 w-full rounded-md border border-input bg-card p-3 text-sm outline-none focus-visible:border-ring"
                />
                <button
                  onClick={() =>
                    setManualParsed(
                      parseManualIngredients(
                        (document.getElementById('manual-input') as HTMLTextAreaElement)?.value ?? '',
                      ).map((x) => matchManualIngredient(x, population)),
                    )
                  }
                  className="focus-visible-strong mt-3 inline-flex min-h-11 items-center rounded-full border border-border px-4 text-sm hover:bg-secondary"
                >
                  解析成分表
                </button>

                {manualParsed && manualParsed.length === 0 && (
                  <p className="mt-4 text-sm text-muted-foreground">没有解析到成分，检查一下格式。</p>
                )}
                {manualParsed && manualParsed.length > 0 && (
                  <div className="mt-4 border-t border-border pt-4">
                    {(() => {
                      const total = manualParsed.length
                      const hits = manualParsed.filter((m) => m.matched)
                      const red = hits.filter((m) => m.level === 'high').length
                      const mid = hits.filter((m) => m.level === 'mid').length
                      return (
                        <>
                          <p className="text-sm">
                            共解析 <span className="font-semibold tabular">{total}</span> 条，命中致敏原库{' '}
                            <span className="font-semibold tabular">{hits.length}</span> 条
                            {hits.length > 0 && (
                              <span className="text-muted-foreground">
                                （红 {red} · 黄 {mid} · 绿 {hits.length - red - mid}）
                              </span>
                            )}
                          </p>
                          <ul className="mt-3 space-y-2">
                            {hits.map((m) => (
                              <li
                                key={m.raw}
                                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-border px-3 py-2 text-sm"
                              >
                                <span className="font-medium">{m.zh}</span>
                                <span className="text-xs text-muted-foreground">
                                  {m.name}
                                  {m.pct !== null && ` · ${m.pct}%`}
                                </span>
                                <RiskMark level={m.level ?? 'low'} />
                                <span className="text-xs text-muted-foreground">{m.gate}</span>
                                <EvidenceTag evidence={m.evidence ?? 'documented'} />
                                {m.note && (
                                  <span className="w-full text-xs leading-relaxed text-muted-foreground">{m.note}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                          {hits.length < total && (
                            <p className="mt-3 text-xs text-muted-foreground">
                              其余 {total - hits.length} 条未命中 IFRA/词典（当前已接入 {IFRA.amendment} Cat4 三表与 {INGREDIENT_DICT.entries.length} 条 CAS 词典；正式版由后端 71 条致敏原库与模糊匹配接管，未命中按「数据不足」黄灯处理，不静默放行）。
                            </p>
                          )}
                        </>
                      )
                    })()}
                  </div>
                )}
                <p className="mt-3 text-sm text-muted-foreground">
                  手动通道是四通道的兜底：成分保密或识别失败时，预警链路依然可用。
                </p>
              </div>
            )}
          </div>
        </div>

        {/* —— 第 3 步：使用情境 —— */}
        <div>
          <StepHead
            n="3"
            title="这瓶用了多久、放在哪里"
            picked={`开封 ${openedMonths} 个月 · ${storageName}`}
          />
          <div className="mt-5 grid gap-6 lg:grid-cols-2">
            <div>
              <label htmlFor="opened-range" className="text-sm text-muted-foreground">
                开封时长：{openedMonths} 个月
              </label>
              <input
                id="opened-range"
                type="range"
                min={0}
                max={24}
                value={openedMonths}
                onChange={(e) => setOpenedMonths(Number(e.target.value))}
                className="mt-3 h-11 w-full accent-[var(--gold)]"
              />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">储存条件</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {STORAGE_OPTIONS.map((s) => (
                  <button
                    key={s.key}
                    onClick={() => setStorage(s.key)}
                    aria-pressed={storage === s.key}
                    className={cn(
                      'focus-visible-strong inline-flex min-h-11 items-center rounded-full border px-5 text-sm transition-colors',
                      storage === s.key ? 'border-ink bg-ink text-paper' : 'border-border hover:bg-secondary',
                    )}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
              <p className="mt-4 inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm">
                氧化程度 D =
                <span className="font-semibold tabular" style={{ color: dl.color }}>
                  {oxidationD.toFixed(2)} {dl.label}
                </span>
                <span className="text-muted-foreground">（对失嗅人群即变质预警）</span>
              </p>
            </div>
          </div>
        </div>

        {/* —— 生成（后端引擎优先，断网回退本地） —— */}
        <div className="flex flex-wrap items-center gap-4 border-t border-border pt-8">
          <button
            onClick={generateReport}
            disabled={reportBusy}
            aria-busy={reportBusy}
            className={cn(
              'focus-visible-strong inline-flex min-h-12 items-center rounded-full bg-ink px-7 font-medium text-paper transition-transform',
              !reportBusy && 'hover:scale-[1.03]',
              reportBusy && 'pointer-events-none opacity-60',
            )}
          >
            {reportBusy ? '引擎计算中…' : '生成预警报告'}
          </button>
          <Link
            to="/vision"
            className="focus-visible-strong inline-flex min-h-12 items-center rounded-full border border-border px-6 hover:bg-secondary"
          >
            查看香气显影
          </Link>
          {reportBusy && (
            <p role="status" aria-live="polite"
              className="flex items-center gap-2 text-sm text-muted-foreground">
              <span aria-hidden className="inline-block h-2 w-2 animate-pulse rounded-full bg-ink" />
              {reportStage || '正在准备…'}
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
