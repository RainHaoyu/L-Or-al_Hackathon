/**
 * QRA2 · 判定引擎（四道闸门取最严）
 *
 * Step 1 基线：AEL = NESIL ÷ SAF（demo 估计值 ÷3 惩罚，标 indicative）
 * Step 2 CEL 概率化（distributions.ts，LHS 固定种子）
 * Step 3 聚合暴露：CEL × aggregateFactor（共使用场景）
 * Step 4 分位判定：红线 = P99 余量 < 1（全人群）；黄线 = 人群判定线 m_dec < 1
 * Step 5 四闸门：禁用 > IFRA > 临床(预留) > QRA2，取最严
 * Step 6 人群差异化：T_pop = α×β，policy = P90(健康) / P99(脆弱)
 */

import { pointCEL, sampleCEL } from './distributions'
import { DEMO_PENALTY, SAF, lookupTox } from './nesil'

export type Level = 'low' | 'mid' | 'high'

export type PopulationKey = 'healthy' | 'sensitive' | 'pregnant' | 'rhinitis' | 'anosmic'

export interface PopPolicy {
  alpha: number
  beta: number
  policy: 'P90' | 'P99'
}

export const POP_POLICY: Record<PopulationKey, PopPolicy> = {
  healthy: { alpha: 1, beta: 1, policy: 'P90' },
  sensitive: { alpha: 3, beta: 1, policy: 'P99' },
  pregnant: { alpha: 1, beta: 1, policy: 'P99' },
  rhinitis: { alpha: 1.2, beta: 1, policy: 'P99' },
  anosmic: { alpha: 1, beta: 1, policy: 'P99' },
}

export function tPop(pop: PopulationKey): number {
  const p = POP_POLICY[pop]
  return p.alpha * p.beta
}

const RANK: Record<Level, number> = { low: 0, mid: 1, high: 2 }

export interface AnalyzeOptions {
  /** 成分名（INCI/中文均可，用于 NESIL 查表） */
  name: string
  /** 成品中的浓度（w/w %）；null = 未知 */
  concPct: number | null
  population: PopulationKey
  /** IFRA Cat4 成品上限（%，来自真实清单；null = 无限值） */
  ifraLimitPct?: number | null
  /** 是否命中完全禁用清单 */
  banned?: boolean
  n?: number
  seed?: number
  /** 聚合暴露系数（单产品 1；共使用场景可传 1.25 等） */
  aggregateFactor?: number
}

export interface AnalyzeResult {
  matched: boolean
  zh: string
  ael: number | null
  aelEvidence: 'documented' | 'indicative' | 'insufficient'
  pointCEL: number | null
  p50: number | null
  p90: number | null
  p99: number | null
  marginPoint: number | null
  marginP99: number | null
  /** 人群判定线余量：AEL ÷ CEL[policy] ÷ T_pop */
  marginPolicy: number | null
  tPop: number
  policy: 'P90' | 'P99'
  /** QRA2 分位闸门 */
  qra2Level: Level | null
  qra2Reason: string | null
  /** IFRA 闸门（有浓度且有限值时判定） */
  ifraLevel: Level | null
  ifraReason: string | null
  bannedLevel: Level | null
  level: Level
  dominantGate: string
}

/** 单成分 QRA2 评估（纯函数，固定种子可复算） */
export function analyzeIngredient(opts: AnalyzeOptions): AnalyzeResult {
  const tox = lookupTox(opts.name)
  const pop = POP_POLICY[opts.population]
  const tp = pop.alpha * pop.beta

  const base: AnalyzeResult = {
    matched: false,
    zh: opts.name,
    ael: null,
    aelEvidence: 'insufficient',
    pointCEL: null,
    p50: null,
    p90: null,
    p99: null,
    marginPoint: null,
    marginP99: null,
    marginPolicy: null,
    tPop: tp,
    policy: pop.policy,
    qra2Level: null,
    qra2Reason: null,
    ifraLevel: null,
    ifraReason: null,
    bannedLevel: null,
    level: 'mid',
    dominantGate: '数据不足',
  }

  // 闸门④：完全禁用（任何浓度直判红）
  if (opts.banned) {
    return {
      ...base,
      matched: true,
      bannedLevel: 'high',
      level: 'high',
      dominantGate: '禁用闸门',
    }
  }

  if (!tox) return base

  // Step 1：AEL = NESIL ÷ SAF（demo 估计 ÷3 惩罚）
  let ael: number | null = null
  let evidence: AnalyzeResult['aelEvidence'] = 'insufficient'
  if (tox.nesil != null) {
    ael = tox.nesil / SAF
    evidence = 'documented'
    if (tox.source === 'demo_estimate') {
      ael = ael / DEMO_PENALTY
      evidence = 'indicative'
    }
  }
  base.matched = true
  base.zh = tox.zh
  base.ael = ael
  base.aelEvidence = evidence

  // IFRA 闸门：浓度已知且有限值 → 真实判定
  if (opts.concPct != null && opts.ifraLimitPct != null && opts.ifraLimitPct > 0) {
    if (opts.concPct >= opts.ifraLimitPct) {
      base.ifraLevel = 'high'
      base.ifraReason = `浓度 ${opts.concPct}% ≥ Cat4 上限 ${opts.ifraLimitPct}%`
    } else if (opts.concPct >= opts.ifraLimitPct * 0.8) {
      base.ifraLevel = 'mid'
      base.ifraReason = `浓度 ${opts.concPct}% 达到 Cat4 上限 ${opts.ifraLimitPct}% 的八成以上`
    } else {
      base.ifraLevel = 'low'
      base.ifraReason = `浓度 ${opts.concPct}% 低于 Cat4 上限 ${opts.ifraLimitPct}%`
    }
  }

  if (ael == null || opts.concPct == null) {
    // 有毒理数据但无浓度（或反之）→ 数据不足保守黄
    base.qra2Level = 'mid'
    base.qra2Reason = opts.concPct == null ? '缺少浓度数据，按保守黄灯（数据不足 ≠ 安全）' : '缺少 NESIL 文献值，按保守黄灯'
    base.level = base.ifraLevel && RANK[base.ifraLevel] > 1 ? base.ifraLevel : 'mid'
    base.dominantGate = base.level === 'high' && base.ifraLevel === 'high' ? 'IFRA 闸门' : '数据不足'
    return base
  }

  // Step 2/3：CEL 概率化 + 聚合
  const agg = opts.aggregateFactor ?? 1
  const s = sampleCEL({ concPct: opts.concPct, n: opts.n, seed: opts.seed, aggregateFactor: agg })
  base.pointCEL = pointCEL(opts.concPct, agg)
  base.p50 = s.p50
  base.p90 = s.p90
  base.p99 = s.p99
  base.marginPoint = ael / base.pointCEL
  base.marginP99 = ael / s.p99
  const policyCel = pop.policy === 'P90' ? s.p90 : s.p99
  base.marginPolicy = ael / policyCel / tp

  // Step 4：QRA2 分位闸门（红线全人群一致 = P99 余量；黄线 = 人群判定线）
  if (base.marginP99 < 1) {
    base.qra2Level = 'high'
    base.qra2Reason = `P99 余量 ${base.marginP99.toFixed(2)} < 1（AEL ${ael.toFixed(0)} / CEL_P99 ${s.p99.toFixed(1)}）`
  } else if (base.marginPolicy < 1) {
    base.qra2Level = 'mid'
    base.qra2Reason = `${pop.policy} × T_pop ${tp} 判定线余量 ${base.marginPolicy.toFixed(2)} < 1`
  } else {
    base.qra2Level = 'low'
    base.qra2Reason = `P99 余量 ${base.marginP99.toFixed(2)}，${pop.policy} 判定线余量 ${base.marginPolicy.toFixed(2)}，安全`
  }

  // Step 5：取最严（禁用 > IFRA > 临床 > QRA2）
  const gates: [Level, string][] = []
  if (base.ifraLevel) gates.push([base.ifraLevel, 'IFRA 闸门'])
  gates.push([base.qra2Level, 'QRA2 分位'])
  let level: Level = 'low'
  let dominant = '四道闸门均未触发'
  for (const [lv, g] of gates) {
    if (RANK[lv] > RANK[level]) {
      level = lv
      dominant = g
    }
  }
  base.level = level
  base.dominantGate = dominant
  return base
}
