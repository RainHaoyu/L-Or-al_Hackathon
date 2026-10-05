/**
 * 毒理查找与数据源回归测试。
 *
 * 背景：
 * 1) 毒理表此前在 web/src/lib/qra2/nesil.ts 与 api/app/data.py 各手写一份，
 *    属重复事实源。现统一为 src/data/tox.json（前端 TS 与后端 Python 共读）。
 * 2) 查找原用「子串包含 + 首个命中」，归一化后长名会包含短名，导致误匹配：
 *      isoeugenol   含 eugenol     → 异丁香酚被判成丁香酚（真实值小 23 倍，危险方向）
 *      hexylcinnamal 含 cinnamal   → 己基肉桂醛被判成肉桂醛（AEL 被压 40 倍）
 *      amylcinnamal  含 cinnamal   → 戊基肉桂醛同上
 *      新铃兰醛       含 铃兰醛      → 被判成铃兰醛
 *      HICC         无匹配         → 漏检禁用物
 *    已改为「最长键优先 + HICC 别名归一」，本文件锁住结果。
 */
import { describe, expect, it } from 'vitest'
import { lookupTox, TOX, SAF, DEMO_PENALTY } from './qra2/nesil'
import toxDoc from '../data/tox.json'

describe('毒理数据源', () => {
  it('tox.json 是唯一来源，条目数 22', () => {
    expect(toxDoc.entries.length).toBe(22)
    expect(TOX.length).toBe(22)
    expect(SAF).toBe(toxDoc.saf)
    expect(DEMO_PENALTY).toBe(toxDoc.demoPenalty)
  })

  it('每条都有 keys / zh / source，且 nesil 为数字或 null', () => {
    for (const e of TOX) {
      expect(e.keys.length, `${e.zh} 缺 keys`).toBeGreaterThan(0)
      expect(e.zh).toBeTruthy()
      expect(['documented', 'demo_estimate']).toContain(e.source)
      expect(e.nesil === null || typeof e.nesil === 'number').toBe(true)
    }
  })

  it('无文献值的条目显式为 null 并标 demo_estimate（不编造）', () => {
    const demo = TOX.filter((e) => e.source !== 'documented')
    expect(demo.map((e) => e.zh).sort()).toEqual(['乙酸苄酯', '乙酸香茅酯', '乙酸香叶酯'].sort())
    for (const e of demo) expect(e.nesil).toBeNull()
  })

  it('SAF=100、惩罚系数=3', () => {
    expect(SAF).toBe(100)
    expect(DEMO_PENALTY).toBe(3)
  })
})

describe('毒理查找：最长键优先（回归守卫）', () => {
  it('异丁香酚不得被判成丁香酚（危险方向）', () => {
    const r = lookupTox('Isoeugenol')
    expect(r?.zh).toBe('异丁香酚')
    expect(r?.nesil).toBe(250)
    expect(r?.nesil).not.toBe(5900) // 丁香酚的值
  })

  it('己基肉桂醛 / 戊基肉桂醛不得被判成肉桂醛', () => {
    expect(lookupTox('Hexyl Cinnamal')?.zh).toBe('己基肉桂醛')
    expect(lookupTox('Hexyl Cinnamal')?.nesil).toBe(23600)
    expect(lookupTox('Amyl Cinnamal')?.zh).toBe('戊基肉桂醛')
    expect(lookupTox('Amyl Cinnamal')?.nesil).toBe(23600)
    // 肉桂醛本身仍须正确
    expect(lookupTox('Cinnamal')?.zh).toBe('肉桂醛')
    expect(lookupTox('Cinnamal')?.nesil).toBe(591)
  })

  it('新铃兰醛不得被判成铃兰醛', () => {
    const hicc = lookupTox('新铃兰醛')
    expect(hicc?.zh).toBe('新铃兰醛（海葵醛）')
    expect(hicc?.nesil).toBe(4000)
    expect(lookupTox('铃兰醛')?.zh).toBe('铃兰醛')
  })

  it('HICC / Lyral 缩写被归一，不漏检禁用物', () => {
    for (const alias of ['HICC', 'Lyral', 'Hydroxyisohexyl 3-Cyclohexene Carboxaldehyde']) {
      const r = lookupTox(alias)
      expect(r?.zh, alias).toBe('新铃兰醛（海葵醛）')
      expect(r?.nesil, alias).toBe(4000)
    }
  })

  it('正常命中不受影响', () => {
    const cases: [string, string, number][] = [
      ['d-Limonene', '柠檬烯', 10000],
      ['Limonene', '柠檬烯', 10000],
      ['柠檬烯', '柠檬烯', 10000],
      ['Linalool', '芳樟醇', 15000],
      ['Citral', '柠檬醛', 1400],
      ['Eugenol', '丁香酚', 5900],
      ['Geraniol', '香叶醇', 11800],
      ['Benzyl Salicylate', '水杨酸苄酯', 17700],
      ['Butylphenyl Methylpropional', '铃兰醛', 4100],
      ['Lilial', '铃兰醛', 4100],
    ]
    for (const [probe, zh, nesil] of cases) {
      expect(lookupTox(probe)?.zh, probe).toBe(zh)
      expect(lookupTox(probe)?.nesil, probe).toBe(nesil)
    }
  })

  it('未知成分返回 null，不猜', () => {
    expect(lookupTox('UnknownIngredientXYZ')).toBeNull()
    expect(lookupTox('')).toBeNull()
  })
})
