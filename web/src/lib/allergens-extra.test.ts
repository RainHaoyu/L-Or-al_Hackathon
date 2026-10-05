/**
 * 三份原始数据层整合验收：EU26 标注清单 / IgE 速发材料 / 香材词典
 */
import { describe, expect, it } from 'vitest'
import {
  EU26,
  IGE,
  MATERIALS,
  buildIngredients,
  evaluate,
  matchManualIngredient,
  parseManualIngredients,
} from './aura'

describe('数据层完整性', () => {
  it('EU26 = 26 条且 CAS 已归一（不含不换行连字符）', () => {
    expect(EU26.length).toBe(26)
    expect(EU26.every((a) => !a.cas.includes('\u2011'))).toBe(true)
    expect(EU26.some((a) => a.zh === '大茴香醇')).toBe(true)
  })
  it('IgE = 10 条且无表头污染行', () => {
    expect(IGE.length).toBe(10)
    expect(IGE.every((g) => g.zh !== '原料类型' && g.zh !== '原料中文名')).toBe(true)
    expect(IGE.some((g) => g.zh === '安息香树脂')).toBe(true)
  })
  it('香材词典：天然 72 + 合成 76（8 类）', () => {
    expect(MATERIALS.natural.length).toBe(72)
    expect(MATERIALS.syntheticCount).toBe(76)
    expect(Object.keys(MATERIALS.synthetic).length).toBe(8)
    expect(MATERIALS.natural).toContain('鸢尾')
  })
})

describe('手动通道新匹配分支', () => {
  const m = (s: string) => matchManualIngredient(parseManualIngredients(s)[0], 'healthy')
  it('大茴香醇 → EU 26 标注清单（黄）', () => {
    const r = m('Anisyl alcohol')
    expect(r.kind).toBe('eu26')
    expect(r.level).toBe('mid')
    expect(r.note).toContain('0.01%')
  })
  it('安息香 → IgE Ⅰ 型速发（树脂类）', () => {
    const r = m('安息香')
    expect(r.kind).toBe('ige')
    expect(r.zh).toBe('安息香树脂')
  })
  it('鸢尾 → 天然香材词典', () => {
    const r = m('鸢尾')
    expect(r.kind).toBe('material')
    expect(r.gate).toBe('天然香材')
  })
  it('IFRA 限值优先级高于 EU26（苯甲醇走限值分支）', () => {
    const r = m('Benzyl Alcohol')
    expect(r.kind).toBe('limit')
  })
})

describe('判定与报告 IgE 集成', () => {
  it('一千零一夜 × 鼻炎 → IgE 速发理由 + 报告 IgE 行', () => {
    const v = evaluate('rhinitis', 'shalimar', 0)
    expect(v.reasons.some((x) => x.includes('IgE') && x.includes('安息香'))).toBe(true)
    const rows = buildIngredients('shalimar', 0, 'rhinitis')
    const igeRows = rows.filter((r) => r.gate === 'IgE Ⅰ 型速发')
    expect(igeRows.length).toBeGreaterThanOrEqual(2)
  })
})
