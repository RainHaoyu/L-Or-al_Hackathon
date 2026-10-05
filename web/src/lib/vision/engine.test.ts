/**
 * 可视化映射引擎测试（阶段 3 验收）
 * - 全库香水（12 真实 + 黄金算例）VisualSpec 非降级且要素齐全
 * - 颜色随主导香型正确变化（不同主导族 → 不同主色）
 * - 情绪效价 / 粒形 / 雷达值域
 * - 降级路径：空金字塔 / 畸形输入 → degraded 置位且不抛异常（错误隔离）
 * - 分模式通感：失嗅模式为加长叙事且包含分层信息
 */
import { describe, expect, it } from 'vitest'
import { buildSynesthesia, buildVisualSpec, FAMILY_MOOD, FAMILY_SHAPE_LABEL } from './engine'
import { FAMILIES, PERFUMES, familyOf, type FamilyKey, type PerfumeEntry } from '../aura'

describe('全库可视化输出（阶段 3 硬验收）', () => {
  it('13 款香水全部非降级、要素齐全', () => {
    for (const p of PERFUMES) {
      const spec = buildVisualSpec(p)
      expect(spec.degraded, `${p.name} 不应降级`).toBe(false)
      if (!spec.degraded) {
        expect(spec.primary).toMatch(/#|rgb/)
        expect(spec.secondary).toMatch(/#|rgb/)
        expect(spec.gradient).toContain('linear-gradient')
        expect(spec.layers.length).toBe(3)
        expect(spec.mix.length).toBeGreaterThanOrEqual(1)
        expect(spec.moodWords.length).toBeGreaterThan(0)
        expect(spec.radar.length).toBe(5)
        for (const layer of spec.layers) {
          expect(layer.notes.length).toBeGreaterThanOrEqual(1)
          for (const n of layer.notes) {
            expect(n.pct).toBeGreaterThan(0)
            expect(n.color).toBe(familyOf(n.family).main)
          }
        }
      }
    }
  })

  it('颜色随主导香型正确变化', () => {
    const byId = (id: string) => PERFUMES.find((p) => p.id === id) as PerfumeEntry
    const citrus = buildVisualSpec(byId('golden-case')) // 柑橘主导
    const leather = buildVisualSpec(byId('tuscan-leather')) // 皮革主导
    const aquatic = buildVisualSpec(byId('wood-sage-sea-salt')) // 水生主导
    if (!citrus.degraded && !leather.degraded && !aquatic.degraded) {
      expect(citrus.primary).toBe(familyOf('citrus').main)
      expect(leather.primary).toBe(familyOf('leather').main)
      expect(aquatic.primary).toBe(familyOf('aquatic').main)
      expect(new Set([citrus.primary, leather.primary, aquatic.primary]).size).toBe(3)
    }
  })

  it('情绪效价与粒形覆盖全部十二香型', () => {
    for (const f of FAMILIES) {
      expect(FAMILY_MOOD[f.key].length).toBeGreaterThan(1)
      expect(FAMILY_SHAPE_LABEL[f.key].length).toBeGreaterThan(1)
    }
    expect(FAMILY_MOOD.floral).toContain('浪漫')
    expect(FAMILY_MOOD.citrus).toContain('活力')
  })

  it('雷达值全部落在 0-10', () => {
    for (const p of PERFUMES) {
      const spec = buildVisualSpec(p)
      if (!spec.degraded) {
        for (const r of spec.radar) {
          expect(r.v).toBeGreaterThanOrEqual(0)
          expect(r.v).toBeLessThanOrEqual(10)
        }
      }
    }
  })
})

describe('降级路径（错误隔离）', () => {
  it('空金字塔 → degraded + 原因，不抛异常', () => {
    const broken = { ...PERFUMES[0], pyramid: [] } as PerfumeEntry
    const spec = buildVisualSpec(broken)
    expect(spec.degraded).toBe(true)
    if (spec.degraded) expect(spec.degradeReason).toContain('金字塔')
  })
  it('金字塔字段缺失 → degraded', () => {
    const broken = { ...PERFUMES[0], pyramid: undefined } as unknown as PerfumeEntry
    expect(buildVisualSpec(broken).degraded).toBe(true)
  })
  it('组成条目异常（全部香材缺失族）→ 降级或不抛异常', () => {
    const broken = {
      ...PERFUMES[0],
      pyramid: [{ layer: '前调', weight: 24, notes: [] }],
    } as unknown as PerfumeEntry
    const spec = buildVisualSpec(broken)
    expect(spec.degraded).toBe(true)
  })
})

describe('分模式通感文案', () => {
  it('失嗅模式为加长叙事且包含分层与情绪信息', () => {
    const p = PERFUMES[0]
    const normal = buildSynesthesia(p, 'normal')
    const anosmic = buildSynesthesia(p, 'anosmia')
    expect(anosmic.length).toBeGreaterThan(normal.length)
    expect(anosmic).toContain('开场')
    expect(anosmic).toContain('情绪')
  })
  it('普通模式返回基础文案', () => {
    expect(buildSynesthesia(PERFUMES[0], 'normal')).toBe(PERFUMES[0].synesthesia)
  })
})
