import { useEffect, useMemo, useRef, useState, type ReactElement } from 'react'
import { Link } from 'react-router'
import { motion, cubicBezier, useReducedMotion } from 'framer-motion'
import { Radar, RadarChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, ResponsiveContainer } from 'recharts'
import { Square, Volume2 } from 'lucide-react'
import { useApp, useRegister } from '../lib/state'
import { POPULATIONS, evaluate, familyOf, getPerfume, type FamilyKey } from '../lib/aura'
import { buildSynesthesia, buildVisualSpec } from '../lib/vision/engine'
import { RiskMark } from '../components/RiskMark'

/* ---------- 颜色工具 ---------- */

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

function rgba(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${a})`
}

/** 变暗（浅底上提升粒子可读性） */
function darken(hex: string, f: number): string {
  const [r, g, b] = hexToRgb(hex)
  const d = (v: number) => Math.round(v * (1 - f))
  return `rgb(${d(r)}, ${d(g)}, ${d(b)})`
}

/** 按权重混合多色（瓶子液体分层用） */
function mixColors(entries: { color: string; w: number }[]): string {
  let r = 0
  let g = 0
  let b = 0
  let tw = 0
  for (const e of entries) {
    const [cr, cg, cb] = hexToRgb(e.color)
    r += cr * e.w
    g += cg * e.w
    b += cb * e.w
    tw += e.w
  }
  if (!tw) return '#888'
  return `rgb(${Math.round(r / tw)}, ${Math.round(g / tw)}, ${Math.round(b / tw)})`
}

/* ---------- 组成驱动的飘落粒子 ---------- */

type Shape = 'petal' | 'leaf' | 'drop' | 'berry' | 'needle'

const SHAPE: Record<FamilyKey, Shape> = {
  floral: 'petal',
  oriental: 'petal',
  woody: 'leaf',
  chypre: 'leaf',
  green: 'leaf',
  citrus: 'drop',
  aquatic: 'drop',
  fruity: 'berry',
  gourmand: 'berry',
  fougere: 'needle',
  aromatic: 'needle',
  leather: 'berry',
}

interface Grain {
  x: number
  y: number
  r: number
  a: number
  va: number
  vy: number
  sway: number
  phase: number
  c: string
  o: number
  shape: Shape
}

/** 确定性伪随机（固定种子，重放一致） */
function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * 香气显影粒子：按香水真实组成生成——每种香材按「层权重 × 香材占比」
 * 分配粒子数量，颜色取其香型色谱，形状随香型族变化，全部缓缓飘落。
 */
function CompositionCanvas({ mix, density = 60 }: { mix: { family: FamilyKey; share: number }[]; density?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let raf = 0
    let w = 0
    let h = 0
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const resize = () => {
      w = canvas.clientWidth
      h = canvas.clientHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const rnd = mulberry32(20261005)
    const grains: Grain[] = []
    for (const m of mix) {
      const fam = familyOf(m.family)
      const count = Math.max(1, Math.round((m.share / 100) * density))
      for (let i = 0; i < count; i++) {
        const shape = SHAPE[m.family]
        const base = shape === 'needle' ? 5 + rnd() * 5 : shape === 'drop' ? 2.2 + rnd() * 2 : 3.5 + rnd() * 5
        const accent = fam.accents[Math.floor(rnd() * Math.max(fam.accents.length, 1))]
        grains.push({
          x: rnd() * Math.max(w, 1),
          y: rnd() * Math.max(h, 1),
          r: base,
          a: rnd() * Math.PI,
          va: (rnd() - 0.5) * 0.02,
          vy: 0.22 + rnd() * 0.5 + base * 0.012,
          sway: 0.35 + rnd() * 0.8,
          phase: rnd() * Math.PI * 2,
          c: rnd() < 0.28 && accent ? accent : darken(fam.main, 0.08),
          o: 0.55 + rnd() * 0.35,
          shape,
        })
      }
    }

    const drawShape = (t: number, g: Grain) => {
      const x = g.x + Math.sin(t / 1500 + g.phase) * 13 * g.sway
      ctx.save()
      ctx.translate(x, g.y)
      ctx.rotate(g.a + Math.sin(t / 2200 + g.phase) * 0.35)
      ctx.globalAlpha = g.o
      ctx.fillStyle = g.c
      if (g.shape === 'petal') {
        ctx.beginPath()
        ctx.ellipse(0, 0, g.r, g.r * 0.55, 0, 0, Math.PI * 2)
        ctx.fill()
      } else if (g.shape === 'leaf') {
        ctx.beginPath()
        ctx.moveTo(0, -g.r)
        ctx.quadraticCurveTo(g.r * 0.75, 0, 0, g.r)
        ctx.quadraticCurveTo(-g.r * 0.75, 0, 0, -g.r)
        ctx.fill()
      } else if (g.shape === 'needle') {
        ctx.strokeStyle = g.c
        ctx.lineWidth = 1.6
        ctx.beginPath()
        ctx.moveTo(0, -g.r)
        ctx.lineTo(0, g.r)
        ctx.stroke()
      } else if (g.shape === 'berry') {
        ctx.beginPath()
        ctx.arc(0, 0, g.r * 0.8, 0, Math.PI * 2)
        ctx.fill()
      } else {
        ctx.beginPath()
        ctx.arc(0, 0, g.r * 0.72, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()
    }

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h)
      for (const g of grains) {
        drawShape(t, g)
        if (!reduced) {
          g.y += g.vy
          g.a += g.va
          if (g.y > h + 14) {
            g.y = -14
            g.x = rnd() * w
          }
        }
      }
      if (!reduced) raf = requestAnimationFrame(draw)
    }
    draw(0)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
    }
  }, [mix, density, reduced])
  return <canvas ref={ref} aria-hidden className="pointer-events-none absolute inset-0 h-full w-full" />
}

/* ---------- 语音播报 ---------- */

function SpeechButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false)
  const toggle = () => {
    if (!('speechSynthesis' in window)) return
    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    u.rate = 0.95
    u.onend = () => setSpeaking(false)
    u.onerror = () => setSpeaking(false)
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
    setSpeaking(true)
  }
  return (
    <button
      onClick={toggle}
      aria-pressed={speaking}
      className="focus-visible-strong inline-flex min-h-11 items-center gap-2 rounded-full border border-border bg-card px-5 text-sm font-medium hover:bg-secondary"
    >
      {speaking ? <Square size={15} aria-hidden /> : <Volume2 size={16} aria-hidden />}
      {speaking ? '停止朗读' : '朗读这段香气'}
    </button>
  )
}

/* ---------- 瓶子直观图（液体按层比例分层） ---------- */

function BottleVisual({ layers }: { layers: { weight: number; color: string }[] }) {
  const total = layers.reduce((s, l) => s + l.weight, 0)
  const BODY_H = 128
  return (
    <svg viewBox="0 0 120 210" className="mx-auto h-64 w-auto" role="img" aria-label="香水瓶示意图：瓶内液体按前中后调占比分层着色">
      {/* 瓶盖 */}
      <rect x="46" y="14" width="28" height="20" rx="4" fill="var(--ink)" />
      {/* 瓶颈 */}
      <rect x="50" y="34" width="20" height="26" fill="rgba(27,31,39,0.08)" stroke="var(--ink)" strokeWidth="1.4" />
      <defs>
        <clipPath id="bottle-body">
          <rect x="18" y="60" width="84" height={BODY_H} rx="16" />
        </clipPath>
      </defs>
      {/* 液体分层（自下而上：后调在下） */}
      <g clipPath="url(#bottle-body)">
        {[...layers].reverse().reduce<{ y: number; els: ReactElement[] }>(
          (acc, l) => {
            const hh = (l.weight / total) * BODY_H
            acc.els.push(<rect key={l.color + acc.y} x="18" y={acc.y} width="84" height={hh + 1} fill={l.color} />)
            acc.y += hh
            return acc
          },
          { y: 60, els: [] },
        ).els}
      </g>
      {/* 瓶身描边与高光 */}
      <rect x="18" y="60" width="84" height={BODY_H} rx="16" fill="none" stroke="var(--ink)" strokeWidth="1.6" />
      <rect x="28" y="70" width="7" height={BODY_H - 22} rx="3.5" fill="rgba(255,255,255,0.35)" />
      {/* 瓶底投影 */}
      <ellipse cx="60" cy="196" rx="40" ry="6" fill="rgba(27,31,39,0.10)" />
    </svg>
  )
}

/* ---------- 页面 ---------- */

export default function Vision() {
  useRegister('light')
  const { population, perfumeId, mode, oxidationD } = useApp()
  const reduced = useReducedMotion()
  const picked = getPerfume(perfumeId)
  const declared = familyOf(picked.familyKey)
  const dominant = familyOf(picked.families[0])
  const popName = POPULATIONS.find((p) => p.key === population)?.name ?? '敏感肌'

  /** 映射规则引擎（纯函数，构建失败 → degraded 降级卡，错误隔离） */
  const spec = buildVisualSpec(picked)
  const degraded = spec.degraded
  const mix = degraded ? [] : spec.mix
  const layerColors = degraded ? [] : spec.layers.map((l) => ({ weight: l.weight, color: l.color }))
  const particleColors = mix.flatMap((m) => {
    const f = familyOf(m.family)
    return [f.main, ...f.accents]
  })

  /** 三模式差异化：失嗅 = 加长叙事（嗅觉替代通道）；敏感 = 风险条前置 */
  const isAnosmic = mode === 'anosmia'
  const synthText = isAnosmic ? buildSynesthesia(picked, 'anosmia') : picked.synesthesia
  const verdict = mode === 'sensitive' ? evaluate(population, perfumeId, oxidationD) : null

  const rise = (delay: number) =>
    reduced
      ? {}
      : {
          initial: { opacity: 0, y: 18 },
          animate: { opacity: 1, y: 0 },
          transition: { delay, duration: 0.7, ease: cubicBezier(0.22, 1, 0.36, 1) },
        }
  const radarLabel = picked.radar.map((r) => `${r.dim} ${r.v}`).join('、')
  const compositionSummary = degraded
    ? `可视化暂不可用：${spec.degradeReason}`
    : `画面描述：主色为${declared.name}色，背景为柔和色晕，${mix
        .map((m) => `${familyOf(m.family).name}约 ${Math.round(m.share)}%（${m.shape}形粒子）`)
        .join('、')}正按配比缓缓飘落。情绪效价：${spec.moodWords}。`

  return (
    <main className="relative overflow-hidden">
      {/* 粒子画面的文字替代（读屏可感知，对应改进清单 P2-1-7） */}
      <p className="sr-only">{compositionSummary}</p>
      {!degraded && (
        <>
          {/* 主导香型色晕（浅场弱化版，主色 = 声明香调） */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background: `radial-gradient(1000px 480px at 24% -6%, ${rgba(spec.primary, 0.14)}, transparent 68%),
                           radial-gradient(760px 420px at 92% 104%, ${rgba(spec.secondary, 0.10)}, transparent 70%)`,
            }}
          />
          <CompositionCanvas mix={mix} />
        </>
      )}
      <div className="relative mx-auto max-w-5xl px-4 pb-24 sm:px-6">
        {/* 标题 */}
        <header className="py-14">
          <motion.p {...rise(0)} className="text-sm text-muted-foreground">
            香气显影 · 为失嗅人群放大呈现 · 当前画像：{popName}
          </motion.p>
          <motion.h1 {...rise(0.12)} className="font-display mt-3 text-5xl leading-tight sm:text-6xl">
            {picked.name}
          </motion.h1>
          <motion.p {...rise(0.2)} className="mt-2 text-xl text-muted-foreground italic">
            {picked.brand}
            {picked.en ? ` · ${picked.en}` : ''} · {picked.concentration}
          </motion.p>
          <motion.p {...rise(0.28)} className="mt-3 text-sm" style={{ color: darken(declared.main, 0.3) }}>
            {declared.name} · {declared.scene}
          </motion.p>
        </header>

        {/* 敏感模式：风险条前置（红黄绿 + 首要原因，三模式差异化之一） */}
        {verdict && (
          <motion.section
            {...rise(0.3)}
            aria-label="风险速览"
            className="mb-10 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card p-5"
            style={{ borderColor: `var(--risk-${verdict.level})` }}
          >
            <RiskMark level={verdict.level} className="text-lg" />
            <p className="min-w-0 flex-1 text-sm leading-relaxed text-muted-foreground">
              {verdict.reasons[0]}
            </p>
            <Link
              to="/report"
              className="focus-visible-strong inline-flex min-h-11 items-center rounded-full border border-border px-4 text-sm hover:bg-secondary"
            >
              查看完整预警报告
            </Link>
          </motion.section>
        )}

        {degraded ? (
          <motion.section {...rise(0.35)} className="rounded-lg border border-border bg-card p-8">
            <h2 className="font-display text-2xl">可视化暂不可用</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              {spec.degradeReason}。预警报告不受影响——可视化与预警为相互隔离的双核心。
            </p>
            <Link
              to="/report"
              className="focus-visible-strong mt-6 inline-flex min-h-12 items-center rounded-full bg-ink px-7 font-medium text-paper"
            >
              查看这瓶的预警报告
            </Link>
          </motion.section>
        ) : (
          <>
        {/* 分层香调 + 瓶子直观图 */}
        <motion.section {...rise(0.35)} aria-label="香调分层" className="grid gap-10 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <h2 className="font-display text-2xl">香调分层</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              层高与色块宽度均按真实配比绘制：层高 = 前中后调权重，色块宽 = 香材占比。
            </p>
            <div className="mt-6 space-y-3">
              {picked.pyramid.map((layer) => (
                <div key={layer.layer} className="flex items-stretch gap-4">
                  <div className="flex w-20 shrink-0 flex-col justify-center text-right">
                    <span className="font-display text-lg">{layer.layer}</span>
                    <span className="text-xs text-muted-foreground tabular">{layer.weight}%</span>
                  </div>
                  <div
                    className="flex flex-1 overflow-hidden rounded-md border border-border"
                    style={{ height: `${Math.max(layer.weight * 1.9, 44)}px` }}
                  >
                    {layer.notes.map((n, i) => {
                      const fam = familyOf(n.family)
                      const pct = Math.round(100 / Math.max(layer.notes.length, 1))
                      return (
                        <div
                          key={`${n.name}-${i}`}
                          title={`${n.name} · ${fam.name} · 约 ${pct}%`}
                          className="flex min-w-0 items-center justify-center px-2"
                          style={{ width: `${100 / Math.max(layer.notes.length, 1)}%`, background: rgba(fam.main, 0.82) }}
                        >
                          <span
                            className={`truncate text-xs font-medium ${pct >= 28 ? '' : 'sr-only'}`}
                            style={{ color: darken(fam.main, 0.55) }}
                          >
                            {n.name}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
            {/* 组成条：全局香型占比 */}
            <div className="mt-8">
              <p className="text-sm text-muted-foreground">全瓶香型组成</p>
              <div className="mt-2 flex h-8 w-full overflow-hidden rounded-full border border-border">
                {mix.map((m) => (
                  <div key={m.family} style={{ width: `${m.share}%`, background: familyOf(m.family).main }} />
                ))}
              </div>
              <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
                {mix.map((m) => (
                  <li key={m.family} className="inline-flex items-center gap-1.5">
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ background: familyOf(m.family).main }}
                    />
                    {familyOf(m.family).name} {Math.round(m.share)}%
                  </li>
                ))}
              </ul>
            </div>

            {/* 色彩情绪板：主色 / 辅色 / 香调渐变 + 情绪效价（v3 四维呈现之「色彩方案」） */}
            <div className="mt-8">
              <p className="text-sm text-muted-foreground">色彩情绪板</p>
              <div className="mt-2 flex h-16 overflow-hidden rounded-lg border border-border">
                <div
                  className="flex-[2]"
                  title={`主色 · ${declared.name}`}
                  style={{ background: spec.primary }}
                />
                <div
                  className="flex-1"
                  title={`辅色 · ${spec.mix[0] ? familyOf(spec.mix[0].family).name : ''}`}
                  style={{ background: spec.secondary }}
                />
                <div className="flex-[3]" title="前中后调渐变" style={{ background: spec.gradient }} />
              </div>
              <p className="mt-2 text-sm leading-relaxed">{spec.moodWords}</p>
            </div>
          </div>

          <div className="lg:col-span-2">
            <h2 className="font-display text-2xl">这瓶的颜色</h2>
            <p className="mt-1 text-sm text-muted-foreground">液体按前中后调配比分层，即是这一瓶在眼中的颜色。</p>
            <div className="mt-4">
              <BottleVisual layers={layerColors} />
            </div>
          </div>
        </motion.section>

        {/* 雷达 + 通感文字 */}
        <section className="mt-14 grid gap-6 lg:grid-cols-5">
          <motion.div {...rise(0.9)} className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
            <h2 className="font-display text-2xl">五维香感</h2>
            <div className="mt-2 h-60" role="img" aria-label={`五维雷达图：${radarLabel}，满分 10`}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={picked.radar} outerRadius="72%">
                  <PolarGrid stroke="rgba(27,31,39,0.16)" />
                  <PolarAngleAxis dataKey="dim" tick={{ fill: 'hsl(228 12% 32%)', fontSize: 13 }} />
                  <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
                  <Radar dataKey="v" stroke={darken(spec.primary, 0.25)} fill={spec.primary} fillOpacity={0.4} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          <motion.div
            {...rise(1.05)}
            className="flex flex-col justify-between rounded-lg border border-border bg-card p-6 lg:col-span-3"
          >
            <div>
              <h2 className="font-display text-2xl">通感描述</h2>
              {isAnosmic && (
                <p className="mt-2 inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                  失嗅模式已启用：加长叙事 + 语音播报，作为嗅觉替代通道
                </p>
              )}
              <p className={`mt-4 leading-loose ${isAnosmic ? 'text-base' : 'text-lg'}`}>{synthText}</p>
              <p className="mt-4 text-sm text-muted-foreground">
                文案由 qwen-max 生成，规则模板兜底；失嗅模式下色彩对比与字号已自动放大。
              </p>
            </div>
            <div className="mt-6">
              <SpeechButton text={`${picked.name}。${synthText}`} />
            </div>
          </motion.div>
        </section>
          </>
        )}

        <motion.div {...rise(1.2)} className="mt-12">
          <Link
            to="/report"
            className="focus-visible-strong inline-flex min-h-12 items-center rounded-full bg-ink px-7 font-medium text-paper transition-transform hover:scale-[1.03]"
          >
            查看这瓶的预警报告
          </Link>
        </motion.div>
      </div>
    </main>
  )
}
