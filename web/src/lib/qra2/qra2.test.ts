/**
 * QRA2 引擎测试（阶段 2 验收）
 * - 黄金算例点估计精确复现：CEL=5.0、AEL=100、比值 20（v3 报告算例）
 * - 固定种子蒙特卡洛逐位可复算；分位保序；浓度线性
 * - 四道闸门：禁用直红 / IFRA 超限红·八成黄 / QRA2 分位红黄
 * - 人群分化：同一输入健康绿灯、敏感肌非绿（α=3 + P99 双收紧）
 * - 氧化：Q10 模型标定值 + 单调性
 */
import { describe, expect, it } from 'vitest'
import { pointCEL, sampleCEL, normalInv, incompleteBeta, betaInv } from './distributions'
import { computeD, dLevel, STORAGE_ENV } from './oxidation'
import { analyzeIngredient, tPop } from './engine'

const GOLD = { name: 'd-Limonene', concPct: 5, population: 'healthy' } as const
const SEED = 20261005

describe('分布基元', () => {
  it('normalInv 标准正态分位（±1e-6）', () => {
    expect(Math.abs(normalInv(0.5) - 0)).toBeLessThan(1e-9)
    expect(Math.abs(normalInv(0.975) - 1.959964)).toBeLessThan(1e-5)
    expect(Math.abs(normalInv(0.05) + 1.644854)).toBeLessThan(1e-5)
  })
  it('incompleteBeta / betaInv 互逆', () => {
    for (const u of [0.05, 0.3, 0.5, 0.9, 0.99]) {
      const x = betaInv(u, 20, 2)
      expect(Math.abs(incompleteBeta(20, 2, x) - u)).toBeLessThan(1e-6)
    }
  })
})

describe('黄金算例（点估计）', () => {
  it('CEL = 0.05 × 0.5 × 100 × 2 × 1.0 = 5.0', () => {
    expect(pointCEL(5)).toBeCloseTo(5.0, 10)
  })
  it('AEL = NESIL 10000 ÷ SAF 100 = 100；比值 = 20（绿灯）', () => {
    const r = analyzeIngredient({ ...GOLD, concPct: 5 })
    expect(r.matched).toBe(true)
    expect(r.ael).toBeCloseTo(100, 6)
    expect(r.pointCEL).toBeCloseTo(5.0, 10)
    expect(r.marginPoint).toBeCloseTo(20, 6)
    expect(r.level).toBe('low')
  })
})

describe('概率化（LHS 蒙特卡洛）', () => {
  it('固定种子逐位可复算', () => {
    const a = sampleCEL({ concPct: 5, seed: SEED })
    const b = sampleCEL({ concPct: 5, seed: SEED })
    expect(a.p50).toBe(b.p50)
    expect(a.p90).toBe(b.p90)
    expect(a.p99).toBe(b.p99)
    for (let i = 0; i < a.samples.length; i += 997) {
      expect(a.samples[i]).toBe(b.samples[i])
    }
  })
  it('分位保序 P50 < P90 < P99，均值 < P99', () => {
    const s = sampleCEL({ concPct: 5, seed: SEED })
    expect(s.p50).toBeLessThan(s.p90)
    expect(s.p90).toBeLessThan(s.p99)
    expect(s.mean).toBeLessThan(s.p99)
  })
  it('浓度线性：10% 的分位 = 5% 的两倍', () => {
    const a = sampleCEL({ concPct: 5, seed: SEED })
    const b = sampleCEL({ concPct: 10, seed: SEED })
    expect(b.p50 / a.p50).toBeCloseTo(2, 10)
    expect(b.p99 / a.p99).toBeCloseTo(2, 10)
  })
  it('聚合暴露系数线性放大 CEL', () => {
    const a = sampleCEL({ concPct: 5, seed: SEED })
    const b = sampleCEL({ concPct: 5, seed: SEED, aggregateFactor: 1.25 })
    expect(b.p99 / a.p99).toBeCloseTo(1.25, 10)
  })
})

describe('四道闸门', () => {
  it('禁用闸门：铃兰醛任意浓度直判红', () => {
    const r = analyzeIngredient({ name: 'Butylphenyl Methylpropional', concPct: 0.01, population: 'healthy', banned: true })
    expect(r.level).toBe('high')
    expect(r.dominantGate).toBe('禁用闸门')
  })
  it('IFRA 闸门：Eugenol 0.6% ≥ 上限 0.5% 判红', () => {
    const r = analyzeIngredient({ name: 'Eugenol', concPct: 0.6, population: 'healthy', ifraLimitPct: 0.5 })
    expect(r.ifraLevel).toBe('high')
    expect(r.level).toBe('high')
    expect(r.dominantGate).toBe('IFRA 闸门')
  })
  it('IFRA 闸门：Eugenol 0.45% 达八成判黄（QRA2 本身绿）', () => {
    const r = analyzeIngredient({ name: 'Eugenol', concPct: 0.45, population: 'healthy', ifraLimitPct: 0.5 })
    expect(r.qra2Level).toBe('low')
    expect(r.ifraLevel).toBe('mid')
    expect(r.level).toBe('mid')
  })
  it('QRA2 分位红线：P99 余量 < 1（高浓度柠檬烯）', () => {
    const r = analyzeIngredient({ name: 'd-Limonene', concPct: 40, population: 'healthy' })
    expect(r.qra2Level).toBe('high')
    expect(r.level).toBe('high')
  })
  it('数据不足不静默：无 NESIL 或无浓度 → 黄灯而非绿', () => {
    const a = analyzeIngredient({ name: '乙酸苄酯', concPct: 5, population: 'healthy' })
    expect(a.level).not.toBe('low')
    const b = analyzeIngredient({ name: 'Eugenol', concPct: null, population: 'healthy' })
    expect(b.level).not.toBe('low')
    const c = analyzeIngredient({ name: '某未知成分 XYZ', concPct: 5, population: 'healthy' })
    expect(c.matched).toBe(false)
    expect(c.level).not.toBe('low')
  })
  it('demo 估计惩罚：无文献 NESIL 的 AEL ÷3 且标 indicative', () => {
    const r = analyzeIngredient({ name: '乙酸香叶酯', concPct: 5, population: 'healthy' })
    expect(r.aelEvidence).not.toBe('documented')
  })
})

describe('人群分化（阶段 2 硬验收）', () => {
  it('同一输入：健康成人绿灯，敏感肌非绿（α=3 + P99 双收紧）', () => {
    const healthy = analyzeIngredient({ name: 'd-Limonene', concPct: 20, population: 'healthy' })
    const sensitive = analyzeIngredient({ name: 'd-Limonene', concPct: 20, population: 'sensitive' })
    expect(healthy.level).toBe('low')
    expect(sensitive.level).not.toBe('low')
    expect(tPop('sensitive')).toBe(3)
    expect(sensitive.policy).toBe('P99')
    expect(healthy.policy).toBe('P90')
  })
  it('脆弱人群判定线严格于健康人群（marginPolicy 更小）', () => {
    const h = analyzeIngredient({ name: 'Citral', concPct: 0.3, population: 'healthy' })
    const s = analyzeIngredient({ name: 'Citral', concPct: 0.3, population: 'sensitive' })
    expect(s.marginPolicy!).toBeLessThan(h.marginPolicy!)
  })
})

describe('氧化模型（Q10 + 光照）', () => {
  it('标定值：3 个月阴凉 D≈0.09 低；14 个月室温 D≈0.62 高；14 个月高温 D≈0.91', () => {
    expect(computeD(3, STORAGE_ENV.cool)).toBeCloseTo(0.085, 2)
    expect(dLevel(computeD(3, STORAGE_ENV.cool)).label).toBe('低')
    expect(computeD(14, STORAGE_ENV.room)).toBeCloseTo(0.62, 2)
    expect(dLevel(computeD(14, STORAGE_ENV.room)).label).toBe('高')
    expect(computeD(14, STORAGE_ENV.hot)).toBeCloseTo(0.91, 2)
  })
  it('单调性：阴凉 < 室温 < 高温；随月份单调递增且 < 1', () => {
    const a = computeD(12, STORAGE_ENV.cool)
    const b = computeD(12, STORAGE_ENV.room)
    const c = computeD(12, STORAGE_ENV.hot)
    expect(a).toBeLessThan(b)
    expect(b).toBeLessThan(c)
    expect(computeD(24, STORAGE_ENV.hot)).toBeLessThan(1)
  })
})
