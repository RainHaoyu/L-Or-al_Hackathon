/**
 * 四类词典的「用自己名字查自己」交叉探测（待办 1-5）。
 *
 * 背景：项目里「成分名 → 条目」的查找原本都是「归一化后子串包含 + 首个命中」，
 * 长名包含短名时会误判。毒理表与 IFRA 表已经修过并锁住，但 EU26 标注清单、
 * IgE 速发材料、香材词典、CAS 词典这四类**没有逐条验证过**。
 *
 * 本文件的探测方式最便宜也最直接：拿每个条目自己的名字去查，
 * 看是否命中自己。命中别人（被更靠前的短名抢走）或命中 null（被长度守卫跳过）
 * 都要显式暴露，而不是靠人工抽查。
 *
 * 四类都用同一条规则：**最长键优先**（见 aura.ts buildIndex / longestHit）。
 * 香材词典本轮才从"按数组顺序取首个 includes"改成同一套索引——字典顺序
 * 不该决定匹配结果。为此 lookupMaterial 也补上了 `name` 字段，
 * 否则"命中了哪个条目"根本看不出来。
 */
import { describe, expect, it } from 'vitest'
import {
  EU26,
  IGE,
  INGREDIENT_DICT,
  MATERIALS,
  lookupDict,
  lookupEu26,
  lookupIge,
  lookupMaterial,
} from './aura'

/** 探测：返回失败清单，形如 "查询名 → 实际命中（应为 期望）" */
function probe<T>(
  entries: T[],
  casesOf: (e: T) => [query: string, expect: string][],
  hit: (name: string) => string | null,
): { bad: string[]; checked: number } {
  const bad: string[] = []
  let checked = 0
  for (const entry of entries) {
    for (const [query, expect] of casesOf(entry)) {
      if (!query) continue
      checked++
      const got = hit(query)
      if (got !== expect) bad.push(`${query} → ${got ?? 'null'}（应为 ${expect}）`)
    }
  }
  return { bad, checked }
}

const norm = (s: string) => s.toLowerCase().replace(/[\s\-–_/]/g, '')

/** 名字短到会被 lookup 的长度守卫直接跳过的条目（应为空，否则等于静默漏检） */
function tooShort(names: string[], min: number): string[] {
  return names.filter((n) => n && norm(n).length > 0 && norm(n).length < min)
}

describe('数据规模（防"数据集变空导致探测全绿"）', () => {
  it('四类词条数量与 /health 上报一致', () => {
    expect(EU26.length).toBe(26)
    expect(IGE.length).toBe(10)
    expect(INGREDIENT_DICT.entries.length).toBe(158)
    expect(MATERIALS.natural.length + Object.values(MATERIALS.synthetic).flat().length).toBe(148)
  })
})

describe('EU 26 标注致敏原', () => {
  it('每条用中文名与 INCI 名都能查到自己', () => {
    const { bad, checked } = probe(
      EU26,
      (a) => [
        [a.zh, a.zh],
        [a.inci, a.zh],
      ],
      (n) => lookupEu26(n)?.zh ?? null,
    )
    expect(checked).toBeGreaterThanOrEqual(26)
    expect(bad).toEqual([])
  })

  it('没有短于 3 字的名字（长度守卫会直接跳过）', () => {
    expect(tooShort(EU26.flatMap((a) => [a.zh, a.inci]), 3)).toEqual([])
  })
})

describe('IgE Ⅰ 型速发材料', () => {
  it('每条用中文名与英文名都能查到自己', () => {
    const { bad, checked } = probe(
      IGE,
      (g) => [
        [g.zh, g.zh],
        [g.en ?? '', g.zh],
      ],
      (n) => lookupIge(n)?.zh ?? null,
    )
    expect(checked).toBeGreaterThanOrEqual(IGE.length)
    expect(bad).toEqual([])
  })

  it('没有短于 2 字的名字', () => {
    expect(tooShort(IGE.flatMap((g) => [g.zh, g.en ?? '']), 2)).toEqual([])
  })
})

describe('CAS 香料词典', () => {
  /**
   * 归一化后同名的键：源数据里不同 CAS 撞了同一个名字。
   *
   * 实测只有一处：CAS 65442-31-1（仲丁基喹啉，商品名对应的通用品）
   * 与 CAS 93-19-6（6-仲丁基喹啉，具体异构体）在源 xlsx 里**共用同一个英文名**
   * "Butyl quinoline secondary"。归一化后两键完全相同，子串匹配只能命中一条。
   *
   * 这里不去改化学名（无来源可依，编一个名字比留着歧义更糟），
   * 而是把歧义**显式记录**下来，并把确定性结果锁住：
   * 商品名 → 通用品 65442-31-1；具体异构体名 → 93-19-6。
   * 注意 CAS 只出现在说明文字里，不参与限值判定，影响面有限。
   */
  const AMBIGUOUS_KEYS = ['butylquinolinesecondary']

  function ambiguousKeys(): string[] {
    const byKey = new Map<string, Set<string>>()
    for (const e of INGREDIENT_DICT.entries) {
      for (const raw of [e.zh ?? '', e.en ?? '']) {
        const k = norm(raw)
        if (!k) continue
        if (!byKey.has(k)) byKey.set(k, new Set())
        byKey.get(k)!.add(e.zh ?? '')
      }
    }
    return [...byKey.entries()].filter(([, names]) => names.size > 1).map(([k]) => k)
  }

  it('同名撞车只有已记录的这一处（新增撞车会在这里失败）', () => {
    expect(ambiguousKeys()).toEqual(AMBIGUOUS_KEYS)
  })

  it('除同名撞车外，每条用中文名与英文名都能查到自己', () => {
    const skip = new Set(ambiguousKeys())
    const bad: string[] = []
    const missingNames: string[] = []
    let checked = 0
    let skippedAmbiguous = 0
    for (const e of INGREDIENT_DICT.entries) {
      if (!(e.zh ?? '') || !(e.en ?? '')) missingNames.push(e.cas || e.zh || '(无)')
      const cases: [string, string][] = [
        [e.zh ?? '', e.zh ?? ''],
        [e.en ?? '', e.zh ?? ''],
      ]
      for (const [query, expect] of cases) {
        if (!query) continue
        if (skip.has(norm(query))) {
          skippedAmbiguous++
          continue
        }
        checked++
        const got = lookupDict(query)?.zh ?? null
        if (got !== expect) bad.push(`${query} → ${got ?? 'null'}（应为 ${expect}）`)
      }
    }
    expect(bad).toEqual([])
    // 源数据里每条都该有中文名与英文名；缺名会在循环里被跳过，这里显式报出来
    expect(missingNames).toEqual([])
    expect(skippedAmbiguous).toBe(2) // 同名撞车影响的两条
    expect(checked).toBe(INGREDIENT_DICT.entries.length * 2 - skippedAmbiguous)
  })

  it('同名撞车时的结果是确定的（商品名 → 通用品，异构体名 → 异构体）', () => {
    expect(lookupDict('Butyl quinoline secondary')?.cas).toBe('65442-31-1')
    expect(lookupDict('6-仲丁基喹啉')?.cas).toBe('93-19-6')
  })
})

describe('香材词典（天然 + 合成单体）', () => {
  it('每条用自己的名字都能查到自己（不能被更长的条目遮住）', () => {
    const names = [
      ...MATERIALS.natural,
      ...Object.values(MATERIALS.synthetic).flat(),
    ]
    const { bad, checked } = probe(
      names,
      (m) => [[m, m]],
      (n) => lookupMaterial(n)?.name ?? null,
    )
    expect(checked).toBe(148)
    expect(bad).toEqual([])
  })

  it('没有短于 2 字的名字', () => {
    const names = [...MATERIALS.natural, ...Object.values(MATERIALS.synthetic).flat()]
    expect(tooShort(names, 2)).toEqual([])
  })
})
