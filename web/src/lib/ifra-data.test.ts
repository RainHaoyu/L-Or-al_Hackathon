/**
 * IFRA 数据质量回归测试。
 *
 * 背景：源 xlsx 的禁用清单区（H/I/J 列）在导出时整体错位一行，
 * 按行拼接 CAS 会得到「校验位合法但并非该物质」的错误值（7 条里 5 条），
 * 其中「薄荷内酯」甚至是校验位非法的 223743-5-7。
 * 管线已在 web/scripts/build_data.py 中按中文名修正并保留 casSource 审计痕迹，
 * 本文件锁住结果，避免再次回退。
 */
import { describe, expect, it } from 'vitest'
import IFRA from '../data/ifra.json'

/** CAS 校验位算法：Σ(从右往左第 i 位 × i) mod 10，i 从 1 起（不含校验位）。 */
function casChecksumOk(cas: string): boolean {
  const parts = cas.split('-')
  if (parts.length !== 3) return false
  const [n1, n2, n3] = parts
  if (!/^\d+$/.test(n1) || !/^\d+$/.test(n2) || !/^\d$/.test(n3)) return false
  const digits = (n1 + n2).split('').reverse()
  const total = digits.reduce((s, d, i) => s + Number(d) * (i + 1), 0)
  return total % 10 === Number(n3)
}

const BANNED = IFRA.banned as { zh: string; cas: string | null; casSource?: string | null }[]

describe('IFRA 禁用清单 CAS 质量', () => {
  it('每条 CAS 要么为 null，要么通过校验位', () => {
    const bad = BANNED.filter((b) => b.cas !== null && !casChecksumOk(b.cas))
    expect(bad.map((b) => `${b.zh}=${b.cas}`)).toEqual([])
  })

  it('已修正的 5 条 CAS 与真实物质一致（源文件错位）', () => {
    const expected: Record<string, string> = {
      葵子麝香: '83-66-9',
      二甲苯麝香: '81-15-2',
      海葵醛: '31906-04-4',
      当归根油: '8015-64-3',
      薄荷内酯: '13341-72-5',
    }
    for (const [zh, cas] of Object.entries(expected)) {
      const row = BANNED.find((b) => b.zh === zh)
      expect(row, `缺少条目 ${zh}`).toBeTruthy()
      expect(row!.cas, zh).toBe(cas)
    }
  })

  it('修正过的条目保留 casSource 审计痕迹', () => {
    const fixed = BANNED.filter((b) => b.casSource)
    expect(fixed.length).toBe(5)
    // 源文件里的非法值必须留痕可查
    expect(fixed.find((b) => b.zh === '薄荷内酯')!.casSource).toBe('223743-5-7')
  })

  it('天然原料无单一 CAS，显式置 null 而非编造', () => {
    for (const zh of ['天然麝香', '天然灵猫香']) {
      expect(BANNED.find((b) => b.zh === zh)!.cas).toBeNull()
    }
  })

  it('限量表 CAS 全部通过校验位', () => {
    const limits = IFRA.limits as { zh: string; cas: string }[]
    expect(limits.length).toBe(20)
    const bad = limits.filter((l) => !casChecksumOk(l.cas))
    expect(bad.map((l) => `${l.zh}=${l.cas}`)).toEqual([])
  })

  it('高危禁用项在位（铃兰醛 / 新铃兰醛 / 硝基麝香）', () => {
    const names = BANNED.map((b) => b.zh)
    expect(names).toContain('铃兰醛')
    expect(names).toContain('海葵醛')
    expect(BANNED.find((b) => b.zh === '铃兰醛')!.cas).toBe('80-54-6')
  })
})
