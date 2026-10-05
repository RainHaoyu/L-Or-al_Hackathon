/**
 * IFRA 限值 / 禁用匹配回归测试。
 *
 * 背景：原匹配为「子串包含 + 首个命中」，归一化后长名包含短名会误命中，
 * 且「首个命中」取到数组里更靠前的短名条目。实测 6 处错误（含漏检禁用物）：
 *
 *   限值（会改变判定结论）：
 *     异丁香酚(0.05%)  被判成 丁香酚(0.5%)    → 偏宽松 10×，可能漏判超标
 *     α-己基肉桂醛(4%) 被判成 肉桂醛(0.05%)   → 偏严格 80×，误报红灯
 *     戊基肉桂醛(1%)   被判成 肉桂醛(0.05%)   → 偏严格 20×，误报红灯
 *   禁用（会漏报或错报）：
 *     Lilial / HICC / Lyral 无别名  → 完全匹配不上，漏检禁用物
 *     新铃兰醛（= 海葵醛）           → 被判成 铃兰醛（另一物质）
 *
 * 修复：匹配键（含数据自带 aliases）按长度降序，取首个命中；别名落在
 * web/src/data/ifra.json 的 aliases 字段，由前端与后端共读。
 */
import { describe, expect, it } from 'vitest'
import { resolveLimit, resolveBanned } from './aura'
import IFRA from '../data/ifra.json'

describe('IFRA 限值解析：最长键优先（回归守卫）', () => {
  it('异丁香酚不得被判成丁香酚（否则偏宽松 10×）', () => {
    expect(resolveLimit('Isoeugenol')?.zh).toBe('异丁香酚')
    expect(resolveLimit('Isoeugenol')?.limitPct).toBe(0.05)
    expect(resolveLimit('异丁香酚')?.limitPct).toBe(0.05)
    // 丁香酚本身仍是 0.5%
    expect(resolveLimit('Eugenol')?.zh).toBe('丁香酚')
    expect(resolveLimit('Eugenol')?.limitPct).toBe(0.5)
  })

  it('α-己基肉桂醛不得被判成肉桂醛（否则误报红灯 80×）', () => {
    expect(resolveLimit('Hexyl Cinnamal')?.zh).toBe('α-己基肉桂醛')
    expect(resolveLimit('Hexyl Cinnamal')?.limitPct).toBe(4)
    expect(resolveLimit('己基肉桂醛')?.limitPct).toBe(4)
  })

  it('戊基肉桂醛不得被判成肉桂醛（否则误报红灯 20×）', () => {
    expect(resolveLimit('Amyl Cinnamal')?.zh).toBe('戊基肉桂醛')
    expect(resolveLimit('Amyl Cinnamal')?.limitPct).toBe(1)
  })

  it('肉桂醛本身不受影响', () => {
    expect(resolveLimit('Cinnamal')?.zh).toBe('肉桂醛')
    expect(resolveLimit('Cinnamal')?.limitPct).toBe(0.05)
  })

  it('d-柠檬烯可用 Limonene / 柠檬烯 命中', () => {
    for (const p of ['Limonene', 'd-Limonene', '柠檬烯', 'limonene']) {
      expect(resolveLimit(p)?.zh, p).toBe('d-柠檬烯')
      expect(resolveLimit(p)?.limitPct, p).toBe(15)
    }
  })

  it('中文别名仍生效（零陵香豆→香豆素、香草→香兰素）', () => {
    expect(resolveLimit('零陵香豆')?.zh).toBe('香豆素')
    expect(resolveLimit('香草')?.zh).toBe('香兰素')
  })

  it('未知成分返回 null，不猜', () => {
    expect(resolveLimit('UnknownXYZ')).toBeNull()
    expect(resolveLimit('')).toBeNull()
  })
})

describe('IFRA 禁用解析：最长键优先（回归守卫）', () => {
  it('Lilial 能被识别为铃兰醛（原先完全匹配不上）', () => {
    expect(resolveBanned('Lilial')?.zh).toBe('铃兰醛')
    expect(resolveBanned('Butylphenyl Methylpropional')?.zh).toBe('铃兰醛')
    expect(resolveBanned('铃兰醛')?.zh).toBe('铃兰醛')
  })

  it('HICC / Lyral / 新铃兰醛 均识别为海葵醛（原先漏检或被判成铃兰醛）', () => {
    for (const p of ['HICC', 'Lyral', '新铃兰醛', '海葵醛',
                     'Hydroxyisohexyl 3-Cyclohexene Carboxaldehyde']) {
      expect(resolveBanned(p)?.zh, p).toBe('海葵醛')
    }
  })

  it('新铃兰醛不得被判成铃兰醛（两者是不同物质、不同禁用原因）', () => {
    expect(resolveBanned('新铃兰醛')?.zh).not.toBe('铃兰醛')
    expect(resolveBanned('HICC')?.reason).not.toBe(resolveBanned('Lilial')?.reason)
  })

  it('硝基麝香与天然原料正常命中', () => {
    for (const p of ['葵子麝香', '二甲苯麝香', '酮麝香', '天然麝香', '天然灵猫香',
                     '当归根油', '薄荷内酯']) {
      expect(resolveBanned(p)?.zh, p).toBe(p)
    }
  })

  it('未知成分返回 null', () => {
    expect(resolveBanned('UnknownXYZ')).toBeNull()
    expect(resolveBanned('')).toBeNull()
  })
})

describe('别名数据完整性', () => {
  it('危禁用项在 ifra.json 里带 aliases（供前后端共读）', () => {
    const banned = IFRA.banned as { zh: string; aliases?: string[] }[]
    const lilial = banned.find((b) => b.zh === '铃兰醛')
    const hicc = banned.find((b) => b.zh === '海葵醛')
    expect(lilial?.aliases).toContain('Lilial')
    expect(hicc?.aliases).toContain('HICC')
    expect(hicc?.aliases).toContain('新铃兰醛')
  })

  it('限值表的别名覆盖 Hexyl Cinnamal 与 d-柠檬烯', () => {
    const limits = IFRA.limits as { zh: string; aliases?: string[] }[]
    expect(limits.find((l) => l.zh === 'α-己基肉桂醛')?.aliases).toContain('Hexyl Cinnamal')
    expect(limits.find((l) => l.zh === 'd-柠檬烯')?.aliases).toContain('limonene')
  })
})
