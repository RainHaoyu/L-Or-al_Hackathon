/**
 * 香味可视化 · 映射规则引擎（阶段 3 核心交付）
 *
 * 金字塔组成 → VisualSpec（纯函数、与预警引擎零依赖、可独立测试）：
 *   palette（主色/辅色/香调渐变）｜分层数据｜全局组成｜五维雷达（复用 aura 生成值）
 *   ｜情绪效价｜通感文案（分模式）。
 * 数据诚实与降级：构建失败 → degraded 置位并给出原因，调用方渲染降级卡，
 * 预警链路不受影响（错误隔离，对应改进清单第 1 批 P0-1 的教训）。
 *
 * 情绪效价词表来自 v3 报告 1.2.2「香调类型→视觉三要素」映射规则
 * （花香=温柔浪漫 / 木质=沉稳温暖 / 柑橘=清新活力 / 东方=浓郁神秘 /
 *   水生=清新辽阔 / 美食=甜美温暖 / 馥奇=经典平衡），其余五族为同源扩展。
 */

import {
  FAMILIES,
  compositionMix,
  familyOf,
  type FamilyKey,
  type PerfumeEntry,
} from '../aura'

export const FAMILY_MOOD: Record<FamilyKey, string> = {
  floral: '温柔、浪漫',
  woody: '沉稳、温暖',
  citrus: '清新、活力',
  oriental: '浓郁、神秘',
  aquatic: '清新、辽阔',
  gourmand: '甜美、温暖',
  fougere: '经典、平衡',
  leather: '醇厚、不羁',
  chypre: '优雅、克制',
  fruity: '鲜活、明快',
  green: '自然、清爽',
  aromatic: '干爽、草本',
}

/** 粒形标签（粒子形状 → 文字，供图例与读屏） */
export const FAMILY_SHAPE_LABEL: Record<FamilyKey, string> = {
  floral: '花瓣',
  oriental: '花瓣',
  woody: '叶片',
  chypre: '叶片',
  green: '叶片',
  citrus: '光珠',
  aquatic: '水珠',
  fruity: '果实',
  gourmand: '果实',
  leather: '果实',
  fougere: '针叶',
  aromatic: '针叶',
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

export function rgba(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${a})`
}

export interface SpecLayer {
  layer: string
  weight: number
  /** 该层混合色（香材色等权混合） */
  color: string
  notes: { name: string; family: FamilyKey; color: string; pct: number }[]
}

export interface SpecMixItem {
  family: FamilyKey
  share: number
  color: string
  mood: string
  scene: string
  shape: string
}

export interface VisualSpec {
  degraded: false
  /** 主色 = 主导香型 */
  primary: string
  /** 辅色 = 次主导香型（无次主导时取主导点缀色） */
  secondary: string
  /** 前中后调渐变（用于情绪板与背景） */
  gradient: string
  layers: SpecLayer[]
  mix: SpecMixItem[]
  moodWords: string
  radar: { dim: string; v: number }[]
}

export interface DegradedSpec {
  degraded: true
  degradeReason: string
}

export type VisualSpecResult = VisualSpec | DegradedSpec

function mixHex(list: { color: string; w: number }[]): string {
  let r = 0
  let g = 0
  let b = 0
  let tw = 0
  for (const e of list) {
    const [cr, cg, cb] = hexToRgb(e.color)
    r += cr * e.w
    g += cg * e.w
    b += cb * e.w
    tw += e.w
  }
  if (!tw) return '#888888'
  return `rgb(${Math.round(r / tw)}, ${Math.round(g / tw)}, ${Math.round(b / tw)})`
}

/** 金字塔组成 → VisualSpec（纯函数；任何形状异常 → degraded，不抛出） */
export function buildVisualSpec(perfume: PerfumeEntry): VisualSpecResult {
  try {
    if (!perfume?.pyramid || !Array.isArray(perfume.pyramid) || perfume.pyramid.length === 0) {
      return { degraded: true, degradeReason: '香调金字塔数据为空，无法生成可视化' }
    }
    const mixRaw = compositionMix(perfume)
    if (mixRaw.length === 0) {
      return { degraded: true, degradeReason: '金字塔香材为空，无法计算香型组成' }
    }

    const mix: SpecMixItem[] = mixRaw.map((m) => {
      const fam = familyOf(m.family)
      return {
        family: m.family,
        share: m.share,
        color: fam.main,
        mood: FAMILY_MOOD[m.family],
        scene: fam.scene,
        shape: FAMILY_SHAPE_LABEL[m.family],
      }
    })

    const layers: SpecLayer[] = perfume.pyramid.map((layer) => ({
      layer: layer.layer,
      weight: layer.weight,
      color: mixHex(layer.notes.map((n) => ({ color: familyOf(n.family).main, w: 1 }))),
      notes: layer.notes.map((n) => ({
        name: n.name,
        family: n.family,
        color: familyOf(n.family).main,
        pct: Math.round(100 / Math.max(layer.notes.length, 1)),
      })),
    }))

    // 主色 = 文档声明的香调类型（v3 映射规则：香调类型 → 主色系）；
    // 辅色 = 组成占比最高的族（与声明不同时）或次主导
    const declared = familyOf(perfume.familyKey)
    const primary = declared.main
    const secondary =
      mix[0] && mix[0].family !== perfume.familyKey
        ? mix[0].color
        : mix[1]
          ? mix[1].color
          : declared.accents[0] ?? primary
    const gradient = `linear-gradient(90deg, ${layers.map((l) => l.color).join(', ')})`
    const moodWords = mix
      .slice(0, 3)
      .map((m) => `${familyOf(m.family).name}（${m.mood}）`)
      .join('、')

    return {
      degraded: false,
      primary,
      secondary,
      gradient,
      layers,
      mix,
      moodWords,
      radar: perfume.radar,
    }
  } catch (err) {
    return {
      degraded: true,
      degradeReason: `可视化构建失败：${err instanceof Error ? err.message : String(err)}`,
    }
  }
}

/** 分模式通感文案：失嗅模式为加长叙事（嗅觉替代通道），其余用基础版 */
export function buildSynesthesia(
  perfume: PerfumeEntry,
  mode: 'normal' | 'anosmia' | 'sensitive',
): string {
  if (mode !== 'anosmia' || !perfume?.pyramid?.length) {
    return perfume?.synesthesia ?? ''
  }
  try {
    const [top, heart, base] = perfume.pyramid
    const seg = (lyr?: { layer: string; notes: { name: string }[] }) =>
      lyr && lyr.notes.length ? lyr.notes.map((n) => n.name).join('、') : ''
    const mixRaw = compositionMix(perfume)
    const dom = familyOf(mixRaw[0]?.family ?? 'floral')
    const second = mixRaw[1] ? familyOf(mixRaw[1].family) : null
    const layerLine = (label: string, notes: string, fam?: { name: string; main: string }) =>
      notes ? `${label}由${notes}铺开${fam ? `，渲染${fam.name}的底色` : ''}` : ''
    return [
      `这是一支以${dom.name}为主导${second ? `、${second.name}为辅` : ''}的作品：${dom.scene}。`,
      [layerLine('开场', seg(top)), layerLine('中段', seg(heart)), layerLine('尾韵', seg(base))]
        .filter(Boolean)
        .join('；')
        .concat('。'),
      `整体情绪偏向${FAMILY_MOOD[dom.key]}${second ? `，兼有${FAMILY_MOOD[second.key]}` : ''}。${perfume.keywords ? `品鉴关键词：${perfume.keywords}。` : ''}`,
    ]
      .filter(Boolean)
      .join('')
  } catch {
    return perfume?.synesthesia ?? ''
  }
}

/** 全库香型枚举（图例用） */
export const ALL_FAMILIES = FAMILIES
