/**
 * QRA2 · NESIL/SAF 毒理参数表
 * NESIL（无预期致敏诱导水平，μg/cm²）为文献值，来源：RIFM/Api et al. 2008 系
 * （经旧项目 71 条致敏原库提取，35 条 documented 之列）；无文献值者按
 * demo_estimate 处理：AEL 施加 ÷3 保守惩罚并标 indicative（数据诚实原则）。
 * SAF = 种间 ×10 × 个体 ×10 = 100（IFRA leave-on 默认）。
 */

export interface ToxEntry {
  /** 匹配键（小写、去空格连字符后包含式匹配） */
  keys: string[]
  zh: string
  /** μg/cm²；null = 无数据（demo 估计） */
  nesil: number | null
  source: 'documented' | 'demo_estimate'
  /** 氧化速率基准（25°C，每天；Q10 模型用） */
  k25?: number
}

export const SAF = 100
export const SAF_BASIS = '种间 10 × 个体 10（IFRA leave-on 默认）'
export const DEMO_PENALTY = 3

export const TOX: ToxEntry[] = [
  { keys: ['limonene', '柠檬烯'], zh: '柠檬烯', nesil: 10000, source: 'documented', k25: 0.0021 },
  { keys: ['linalool', '芳樟醇'], zh: '芳樟醇', nesil: 15000, source: 'documented', k25: 0.0015 },
  { keys: ['citral', '柠檬醛'], zh: '柠檬醛', nesil: 1400, source: 'documented' },
  { keys: ['coumarin', '香豆素'], zh: '香豆素', nesil: 3500, source: 'documented' },
  { keys: ['eugenol', '丁香酚'], zh: '丁香酚', nesil: 5900, source: 'documented' },
  { keys: ['isoeugenol', '异丁香酚'], zh: '异丁香酚', nesil: 250, source: 'documented' },
  { keys: ['geraniol', '香叶醇'], zh: '香叶醇', nesil: 11800, source: 'documented' },
  { keys: ['citronellol', '香茅醇'], zh: '香茅醇', nesil: 29500, source: 'documented' },
  { keys: ['vanillin', '香兰素'], zh: '香兰素', nesil: 5314, source: 'documented' },
  { keys: ['benzylalcohol', '苯甲醇'], zh: '苯甲醇', nesil: 5900, source: 'documented' },
  { keys: ['cinnamal', '肉桂醛'], zh: '肉桂醛', nesil: 591, source: 'documented' },
  { keys: ['cinnamylalcohol', '肉桂醇'], zh: '肉桂醇', nesil: 3000, source: 'documented' },
  { keys: ['farnesol', '法尼醇'], zh: '法尼醇', nesil: 2700, source: 'documented' },
  { keys: ['benzylsalicylate', '水杨酸苄酯'], zh: '水杨酸苄酯', nesil: 17700, source: 'documented' },
  { keys: ['benzylacetate', '乙酸苄酯'], zh: '乙酸苄酯', nesil: null, source: 'demo_estimate' },
  { keys: ['hexylcinnamal', '己基肉桂醛'], zh: '己基肉桂醛', nesil: 23600, source: 'documented' },
  { keys: ['amylcinnamal', '戊基肉桂醛'], zh: '戊基肉桂醛', nesil: 23600, source: 'documented' },
  { keys: ['citronellylacetate', '乙酸香茅酯'], zh: '乙酸香茅酯', nesil: null, source: 'demo_estimate' },
  { keys: ['geranylacetate', '乙酸香叶酯'], zh: '乙酸香叶酯', nesil: null, source: 'demo_estimate' },
  { keys: ['benzaldehyde', '苯甲醛'], zh: '苯甲醛', nesil: 590, source: 'documented' },
  { keys: ['butylphenylmethylpropional', '铃兰醛', 'lilial'], zh: '铃兰醛', nesil: 4100, source: 'documented' },
  { keys: ['hydroxyisohexyl', '新铃兰醛', 'lyral'], zh: '新铃兰醛（海葵醛）', nesil: 4000, source: 'documented' },
]

const norm = (s: string) => s.toLowerCase().replace(/[\s\-–_/]/g, '')

export function lookupTox(name: string): ToxEntry | null {
  const n = norm(name)
  return TOX.find((t) => t.keys.some((k) => n.includes(norm(k)))) ?? null
}
