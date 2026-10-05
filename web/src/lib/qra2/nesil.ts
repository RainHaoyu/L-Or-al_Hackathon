/**
 * QRA2 · NESIL/SAF 毒理参数表
 *
 * 数据源：`src/data/tox.json`（由 数据层/ 上游原始文件核对而来）。
 * **同一份 JSON 也被后端 `api/app/data.py` 读取**，因此前端的 TS 引擎
 * 与后端的 Python 引擎共用一套毒理参数，不再各自手写一份。
 *
 * NESIL（无预期致敏诱导水平，μg/cm²）为文献值，来源：RIFM / Api et al. 2008 系。
 * 无文献值者标 demo_estimate：AEL 施加 ÷3 保守惩罚并标 indicative
 * （数据诚实原则：数据不足 ≠ 安全）。
 * SAF = 种间 ×10 × 个体 ×10 = 100（IFRA leave-on 默认）。
 */

import rawTox from '../../data/tox.json'

export interface ToxEntry {
  /** 匹配键（小写、去空格连字符后包含式匹配） */
  keys: string[]
  zh: string
  /** μg/cm²；null = 无文献值（demo 估计） */
  nesil: number | null
  source: 'documented' | 'demo_estimate'
  /** 氧化速率基准（25°C，每天；Q10 模型用） */
  k25?: number
}

export const SAF: number = rawTox.saf
export const SAF_BASIS: string = rawTox.safBasis
export const DEMO_PENALTY: number = rawTox.demoPenalty
export const TOX_SOURCE: string = rawTox.source

export const TOX: ToxEntry[] = rawTox.entries as ToxEntry[]

const norm = (s: string) => s.toLowerCase().replace(/[\s\-–_/]/g, '')

/**
 * 匹配键按长度降序预排（最长优先）。
 *
 * 子串匹配在归一化（去掉连字符）后会互相包含：
 *   - `isoeugenol` 含 `eugenol`      → 异丁香酚会被误判成丁香酚（真实值小 23 倍，危险方向）
 *   - `hexylcinnamal` 含 `cinnamal`  → 己基肉桂醛会被误判成肉桂醛（AEL 被压 40 倍）
 *   - `amylcinnamal` 含 `cinnamal`   → 同上
 *   - `新铃兰醛` 含 `铃兰醛`          → 会被误判成铃兰醛
 * 按长度降序取首个命中，即可让更具体的键优先，消除上述误匹配。
 */
const KEYS: { key: string; entry: ToxEntry }[] = TOX
  .flatMap((entry) => entry.keys.map((k) => ({ key: norm(k), entry })))
  .sort((a, b) => b.key.length - a.key.length)

const HICC_ALIASES = ['hicc', 'lyral', 'hydroxyisohexyl', '新铃兰醛', '海葵醛', '新铃兰醛（海葵醛）']
const HICC_KEYS = HICC_ALIASES.map(norm).sort((a, b) => b.length - a.length)

export function lookupTox(name: string): ToxEntry | null {
  const n = norm(name)
  if (!n) return null
  // HICC / Lyral 的 INCI 常被写成缩写，先按别名归一到新铃兰醛条目
  const hicc = TOX.find((t) => t.zh.startsWith('新铃兰醛'))
  if (hicc && HICC_KEYS.some((k) => n.includes(k))) return hicc
  for (const { key, entry } of KEYS) {
    if (n.includes(key)) return entry
  }
  return null
}
