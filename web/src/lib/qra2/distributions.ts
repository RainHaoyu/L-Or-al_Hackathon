/**
 * QRA2 · CEL 概率化（五参数分布 + 拉丁超立方抽样）
 *
 * 点估计（黄金算例口径）：CEL = 浓度 × 0.5 mg/cm² × 100 cm² × 2 次/天 × 1.0
 * 概率化参数（对应 v3 路线图 Step 2）：
 *   用量 LogNormal（中位 0.5，CV 0.4）｜面积 Tri(50,100,200)｜频率 {1:.5,2:.35,3:.15}
 *   浓度 U(0.8c₀,1.2c₀)｜吸收 Beta(20,2)
 * 抽样：Latin Hypercube，N 默认 10000，固定种子可复算（任何人重算逐位一致）。
 */

/** 确定性伪随机（mulberry32） */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/* ---------- 正态分位函数（Acklam 有理逼近，|误差| < 1.15e-9） ---------- */
const A = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239]
const B = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1]
const C = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783]
const D = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416]

export function normalInv(u: number): number {
  if (u <= 0 || u >= 1) throw new Error(`normalInv: u 必须在 (0,1)，收到 ${u}`)
  const pl = 0.02425
  if (u < pl) {
    const q = Math.sqrt(-2 * Math.log(u))
    return (((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5]) / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1)
  }
  if (u > 1 - pl) {
    const q = Math.sqrt(-2 * Math.log(1 - u))
    return -(((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5]) / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1)
  }
  const q = u - 0.5
  const r = q * q
  return (((((A[0] * r + A[1]) * r + A[2]) * r + A[3]) * r + A[4]) * r + A[5]) * q / (((((B[0] * r + B[1]) * r + B[2]) * r + B[3]) * r + B[4]) * r + 1)
}

/* ---------- Beta 分布分位函数（正则不完全 Beta + 二分求逆） ---------- */

function logGamma(z: number): number {
  const g = [676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - logGamma(1 - z)
  z -= 1
  let x = 0.99999999999980993
  for (let i = 0; i < g.length; i++) x += g[i] / (z + i + 1)
  const t = z + g.length - 0.5
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x)
}

function betacf(a: number, b: number, x: number): number {
  const FPMIN = 1e-300
  const qab = a + b
  const qap = a + 1
  const qam = a - 1
  let c = 1
  let d = 1 - (qab * x) / qap
  if (Math.abs(d) < FPMIN) d = FPMIN
  d = 1 / d
  let h = d
  for (let m = 1; m <= 200; m++) {
    const m2 = 2 * m
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2))
    d = 1 + aa * d
    if (Math.abs(d) < FPMIN) d = FPMIN
    c = 1 + aa / c
    if (Math.abs(c) < FPMIN) c = FPMIN
    d = 1 / d
    h *= d * c
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2))
    d = 1 + aa * d
    if (Math.abs(d) < FPMIN) d = FPMIN
    c = 1 + aa / c
    if (Math.abs(c) < FPMIN) c = FPMIN
    d = 1 / d
    const del = d * c
    h *= del
    if (Math.abs(del - 1) < 3e-12) break
  }
  return h
}

/** 正则不完全 Beta I_x(a,b) */
export function incompleteBeta(a: number, b: number, x: number): number {
  if (x <= 0) return 0
  if (x >= 1) return 1
  const lnBeta = logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x)
  const bt = Math.exp(lnBeta)
  if (x < (a + 1) / (a + b + 2)) return (bt * betacf(a, b, x)) / a
  return 1 - (bt * betacf(b, a, 1 - x)) / b
}

export function betaInv(u: number, a: number, b: number): number {
  if (u <= 0) return 0
  if (u >= 1) return 1
  let lo = 0
  let hi = 1
  for (let i = 0; i < 80; i++) {
    const mid = (lo + hi) / 2
    if (incompleteBeta(a, b, mid) < u) lo = mid
    else hi = mid
  }
  return (lo + hi) / 2
}

/* ---------- 三角分布分位 ---------- */
function triInv(u: number, a: number, c: number, b: number): number {
  const fc = (c - a) / (b - a)
  if (u < fc) return a + Math.sqrt(u * (c - a) * (b - a))
  return b - Math.sqrt((1 - u) * (b - c) * (b - a))
}

/* ---------- LHS 与 CEL 抽样 ---------- */

export const CEL_PARAMS = {
  medianAmount: 0.5,
  cvAmount: 0.4,
  area: { min: 50, mode: 100, max: 200 },
  freq: [
    { v: 1, p: 0.5 },
    { v: 2, p: 0.35 },
    { v: 3, p: 0.15 },
  ],
  concBand: 0.2,
  absorption: { alpha: 20, beta: 2 },
} as const

/** 黄金算例点估计：CEL = 浓度 × 0.5 × 100 × 2 × 1.0（浓度以分数计） */
export function pointCEL(concPct: number, aggregateFactor = 1): number {
  return (concPct / 100) * CEL_PARAMS.medianAmount * 100 * 2 * 1.0 * aggregateFactor
}

export interface CelSample {
  samples: Float64Array
  p50: number
  p90: number
  p99: number
  mean: number
}

function percentileOf(sorted: Float64Array | number[], q: number): number {
  const n = sorted.length
  const idx = (n - 1) * q
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  if (lo === hi) return sorted[lo]
  return sorted[lo] + (idx - lo) * (sorted[hi] - sorted[lo])
}

/** Fisher-Yates 置换（用同一个随机流） */
function permutation(n: number, rand: () => number): number[] {
  const a = Array.from({ length: n }, (_, i) => i)
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/**
 * CEL 概率化抽样（LHS + 固定种子）。
 * aggregateFactor：聚合暴露系数（单产品 1.0；共使用场景按 1+Σw·ratio 配置，演示默认 1.25 可选）。
 */
export function sampleCEL(opts: { concPct: number; n?: number; seed?: number; aggregateFactor?: number }): CelSample {
  const n = opts.n ?? 10000
  const seed = opts.seed ?? 20261005
  const agg = opts.aggregateFactor ?? 1
  const rand = mulberry32(seed)
  const permA = permutation(n, rand)
  const permB = permutation(n, rand)
  const permF = permutation(n, rand)
  const permC = permutation(n, rand)
  const permS = permutation(n, rand)

  const { medianAmount, cvAmount, area, freq, concBand, absorption } = CEL_PARAMS
  const sigma = Math.sqrt(Math.log(1 + cvAmount * cvAmount))
  const f1 = freq[0].p
  const f2 = f1 + freq[1].p
  const c0 = opts.concPct / 100

  const out = new Float64Array(n)
  let sum = 0
  for (let i = 0; i < n; i++) {
    const amount = medianAmount * Math.exp(sigma * normalInv((permA[i] + rand()) / n))
    const uB = (permB[i] + rand()) / n
    const areaV = triInv(uB, area.min, area.mode, area.max)
    const uF = (permF[i] + rand()) / n
    const freqV = uF < f1 ? 1 : uF < f2 ? 2 : 3
    const concV = c0 * (1 - concBand) + 2 * concBand * c0 * ((permC[i] + rand()) / n)
    const absorb = betaInv((permS[i] + rand()) / n, absorption.alpha, absorption.beta)
    const v = concV * amount * areaV * freqV * absorb * agg
    out[i] = v
    sum += v
  }
  out.sort()
  return {
    samples: out,
    p50: percentileOf(out, 0.5),
    p90: percentileOf(out, 0.9),
    p99: percentileOf(out, 0.99),
    mean: sum / n,
  }
}
