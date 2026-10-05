/**
 * 万象 Aura · 数据层（真实数据接入版）
 * - 12 款真实香水 / IFRA 51st Cat4 三表 / 160 条 CAS 词典
 *   全部来自 数据层/ 原始文件，经 scripts/build_data.py 生成 src/data/*.json
 * - 五维雷达由族先验按组成加权生成；风险画像（萜烯/麝香/限值命中）由真实成分清单推导
 */

import rawPerfumes from '../data/perfumes.json'
import rawIfra from '../data/ifra.json'
import rawIngredients from '../data/ingredients.json'
import rawAllergens26 from '../data/allergens26.json'
import rawIge from '../data/ige.json'
import rawMaterials from '../data/materials.json'
import { analyzeIngredient } from './qra2/engine'
import { lookupTox } from './qra2/nesil'

/** 氧化模型统一出口（Q10 + 光照，见 qra2/oxidation.ts） */
export { computeD, dLevel, STORAGE_ENV } from './qra2/oxidation'

export type RiskLevel = 'low' | 'mid' | 'high'
export type Evidence = 'documented' | 'indicative' | 'insufficient'
export type FamilyKey =
  | 'citrus' | 'floral' | 'woody' | 'aquatic' | 'oriental' | 'leather'
  | 'chypre' | 'fougere' | 'fruity' | 'green' | 'gourmand' | 'aromatic'

/* ---------------- 十二香型（HEX 与场景来自《香型HEX色值及对应画面效果》） ---------------- */

export interface FamilyDef {
  key: FamilyKey
  name: string
  main: string
  accents: string[]
  scene: string
  radarPrior: { 清新: number; 甜度: number; 浓郁: number; 温暖: number; 持久: number }
}

export const FAMILIES: FamilyDef[] = [
  { key: 'citrus', name: '柑橘调', main: '#FFA500', accents: ['#FFDD00', '#B4D26A'], scene: '剥开鲜橙的瞬间，精油光点迸溅的果园', radarPrior: { 清新: 9, 甜度: 2, 浓郁: 3, 温暖: 3, 持久: 3 } },
  { key: 'floral', name: '花香调', main: '#FFB6C1', accents: ['#FFBC97', '#C5E0B4'], scene: '春日花园，柔粉花瓣伴着蜜桃果肉', radarPrior: { 清新: 6, 甜度: 7, 浓郁: 6, 温暖: 6, 持久: 6 } },
  { key: 'woody', name: '木质调', main: '#6B4423', accents: ['#8A6F56', '#7A8868'], scene: '幽静森林，原木与树脂的气息', radarPrior: { 清新: 3, 甜度: 3, 浓郁: 7, 温暖: 8, 持久: 9 } },
  { key: 'aquatic', name: '水生调', main: '#A1C8D7', accents: ['#C2D2D9', '#94B8B2'], scene: '薄雾笼罩的平静湖面，淡淡海风', radarPrior: { 清新: 9, 甜度: 3, 浓郁: 3, 温暖: 3, 持久: 4 } },
  { key: 'oriental', name: '东方调', main: '#965327', accents: ['#782C20', '#B87333'], scene: '琥珀、树脂与辛香交织的暖调宫殿', radarPrior: { 清新: 2, 甜度: 6, 浓郁: 9, 温暖: 9, 持久: 9 } },
  { key: 'leather', name: '皮革调', main: '#4A3628', accents: ['#634737', '#A88C7E'], scene: '烟熏气息的复古鞣制工坊', radarPrior: { 清新: 2, 甜度: 2, 浓郁: 9, 温暖: 7, 持久: 8 } },
  { key: 'chypre', name: '西普调', main: '#706C58', accents: ['#506248', '#8C4743'], scene: '秋日山林，青苔与岩石相互缠绕', radarPrior: { 清新: 5, 甜度: 4, 浓郁: 7, 温暖: 5, 持久: 7 } },
  { key: 'fougere', name: '馥奇调', main: '#748C67', accents: ['#9F91C8', '#A08C6D'], scene: '雨后林间草地，薰衣草与苔藓', radarPrior: { 清新: 7, 甜度: 4, 浓郁: 5, 温暖: 6, 持久: 6 } },
  { key: 'fruity', name: '果香调', main: '#D96058', accents: ['#FFB3A0', '#8C4743'], scene: '挂满浆果的果园，水润饱满', radarPrior: { 清新: 7, 甜度: 8, 浓郁: 5, 温暖: 5, 持久: 4 } },
  { key: 'green', name: '绿叶调', main: '#87B36B', accents: ['#597C47', '#B2C997'], scene: '清晨刚采摘的鲜草与青枝叶', radarPrior: { 清新: 9, 甜度: 3, 浓郁: 3, 温暖: 3, 持久: 3 } },
  { key: 'gourmand', name: '美食调', main: '#C87941', accents: ['#F8EAD8', '#5C3317'], scene: '暖烘烘的甜品铺，焦糖与可可', radarPrior: { 清新: 3, 甜度: 9, 浓郁: 8, 温暖: 8, 持久: 8 } },
  { key: 'aromatic', name: '芳香调', main: '#697C57', accents: ['#9484B7', '#A39478'], scene: '阳光晾晒的草本药草，清苦干爽', radarPrior: { 清新: 8, 甜度: 3, 浓郁: 4, 温暖: 4, 持久: 4 } },
]

export function familyOf(key: FamilyKey): FamilyDef {
  return FAMILIES.find((f) => f.key === key) ?? FAMILIES[0]
}

export const RISK_LABEL: Record<RiskLevel, string> = { low: '绿灯', mid: '黄灯', high: '红灯' }
export const EVIDENCE_LABEL: Record<Evidence, string> = {
  documented: '文献值',
  indicative: '演示估计',
  insufficient: '数据不足',
}

/* ---------------- IFRA 真实数据 ---------------- */

export interface IfraLimit {
  cas: string
  zh: string
  en: string
  limitPct: number | null
  note: string
}
export interface IfraBanned {
  cas: string | null
  zh: string
  en: string
  control: string
  reason: string
}
export interface IfraFile {
  source: string
  amendment: string
  limits: IfraLimit[]
  banned: IfraBanned[]
  natural: { zh: string; en: string; limitPct: number | null; note: string }[]
}

export const IFRA = rawIfra as unknown as IfraFile

export interface DictEntry {
  cas: string
  zh: string
  en: string
  formula: string
  source: string
}
export const INGREDIENT_DICT = rawIngredients as unknown as { entries: DictEntry[] }

/* ---------------- EU 26 标注致敏原 / IgE Ⅰ 型速发材料 / 香材词典 ---------------- */

export interface Eu26Item {
  no: number
  inci: string
  zh: string
  cas: string
  note: string
}
export interface IgeItem {
  category: string
  zh: string
  en: string
  type: string
  families: string
  risk: string
  note: string
}
export interface MaterialsFile {
  natural: string[]
  synthetic: Record<string, string[]>
  syntheticCount: number
}

export const EU26 = (rawAllergens26 as unknown as { items: Eu26Item[] }).items
export const IGE = (rawIge as unknown as { items: IgeItem[] }).items
export const MATERIALS = rawMaterials as unknown as MaterialsFile

/* ---------------- 匹配工具（最长键优先） ---------------- */

/** 限量成分的中文别名（成分清单 → IFRA 中文名）；数据自带 aliases 时以数据为准。 */
const LIMIT_ALIASES: Record<string, string[]> = {
  香豆素: ['零陵香豆'],
  香兰素: ['香草'],
}

/** 归一化：小写 + 去掉空白与各类连字符。 */
function norm(s: string): string {
  return s.toLowerCase().replace(/[\s\-–_/]/g, '')
}

/**
 * 归一化后的名字 → 条目索引，按键长降序（最长优先）。
 *
 * 子串匹配（`n.includes(key)`）在长名包含短名时会误命中，且「首个命中」取到的是
 * 数组里更靠前的短名条目。实测 IFRA 限值表的三处错误：
 *   异丁香酚(0.05%)  被判成 丁香酚(0.5%)      → 偏宽松 10×，可能漏判超标
 *   α-己基肉桂醛(4%) 被判成 肉桂醛(0.05%)     → 偏严格 80×，误报红灯
 *   戊基肉桂醛(1%)   被判成 肉桂醛(0.05%)     → 偏严格 20×，误报红灯
 * 按长度降序取首个命中即可让更具体的键优先。
 */
function buildIndex<T>(rows: T[], keysOf: (row: T) => string[]) {
  const idx: { key: string; row: T }[] = []
  for (const row of rows) {
    for (const k of keysOf(row)) {
      const nk = norm(k)
      if (nk) idx.push({ key: nk, row })
    }
  }
  idx.sort((a, b) => b.key.length - a.key.length)
  return idx
}

function longestHit<T>(index: { key: string; row: T }[], n: string): T | null {
  for (const { key, row } of index) if (n.includes(key)) return row
  return null
}

type RowAliases = { zh: string; en?: string | null; aliases?: string[] }

/** 一行的全部匹配键：中文名 + 英文名 + 数据自带 aliases + 代码内别名。 */
const rowKeys = (r: RowAliases) =>
  [r.zh, r.en ?? '', ...(r.aliases ?? []), ...(LIMIT_ALIASES[r.zh] ?? [])]

const EU26_INDEX = buildIndex(EU26, (a) => [a.zh, a.inci ?? ''])
const IGE_INDEX = buildIndex(IGE, (g) => [g.zh, g.en ?? ''])
const DICT_INDEX = buildIndex(INGREDIENT_DICT.entries, (e) => [e.zh ?? '', e.en ?? ''])
const LIMIT_INDEX = buildIndex(IFRA.limits as unknown as RowAliases[], rowKeys)
const BANNED_INDEX = buildIndex(IFRA.banned as unknown as RowAliases[], rowKeys)

/** 解析成分名对应的 IFRA 限值条目（最长键优先）。 */
export function resolveLimit(ingredient: string): IfraLimit | null {
  const n = norm(ingredient)
  if (!n) return null
  return longestHit(LIMIT_INDEX, n) as IfraLimit | null
}

/** 解析成分名对应的 IFRA 禁用条目（最长键优先）。 */
export function resolveBanned(ingredient: string): IfraBanned | null {
  const n = norm(ingredient)
  if (!n) return null
  return longestHit(BANNED_INDEX, n) as IfraBanned | null
}


export function lookupEu26(name: string): Eu26Item | null {
  const n = norm(name)
  if (n.length < 3) return null
  return longestHit(EU26_INDEX, n)
}

export function lookupIge(ingredient: string): IgeItem | null {
  const n = norm(ingredient)
  if (n.length < 2) return null
  const direct = longestHit(IGE_INDEX, n)
  if (direct) return direct
  // 反向：成分名是条目的前缀片段（如清单写作简称）
  const reverse = IGE.find((g) => norm(g.zh).includes(n) && g.zh.length <= n.length + 4)
  return reverse ?? null
}

export function lookupMaterial(name: string): { kind: '天然香材' | '合成单体'; category: string } | null {
  const n = norm(name)
  if (n.length < 2) return null
  const nat = MATERIALS.natural.find((m) => n.includes(norm(m)))
  if (nat) return { kind: '天然香材', category: '天然香料词典' }
  for (const [cat, list] of Object.entries(MATERIALS.synthetic)) {
    if (list.some((m) => n.includes(norm(m)))) return { kind: '合成单体', category: cat }
  }
  return null
}

function hitLimit(ingredient: string, l: IfraLimit): boolean {
  return resolveLimit(ingredient)?.zh === l.zh
}

function hitBanned(ingredient: string, b: IfraBanned): boolean {
  return resolveBanned(ingredient)?.zh === b.zh
}

/* ---------------- 香水（真实 12 款 + 黄金算例） ---------------- */

export interface LayerNote {
  name: string
  family: FamilyKey
}
export interface PyramidLayer {
  layer: '前调' | '中调' | '后调'
  weight: number
  notes: LayerNote[]
}

export interface PerfumeEntry {
  id: string
  brand: string
  name: string
  en: string
  tag: string
  familyZh: string
  /** 文档声明的香调（映射到十二香型族） */
  familyKey: FamilyKey
  concentration: string
  keywords: string
  families: FamilyKey[]
  pyramid: PyramidLayer[]
  ingredients: string[]
  /** 五维雷达（由族先验按组成加权生成） */
  radar: { dim: string; v: number }[]
  synesthesia: string
  /** 由真实成分推导的风险画像 */
  profile: {
    banned: IfraBanned[]
    terpene: boolean
    muskCaution: boolean
    limitHits: IfraLimit[]
    igeHits: IgeItem[]
    load: 'high' | 'mid' | 'low'
  }
  synthetic?: boolean
}

/** 组成占比：层权重 × 层内等分，聚合到香型族 */
export function compositionMix(entry: { pyramid: PyramidLayer[] }): { family: FamilyKey; share: number }[] {
  const agg = new Map<FamilyKey, number>()
  for (const layer of entry.pyramid) {
    const n = Math.max(layer.notes.length, 1)
    for (const nt of layer.notes) {
      agg.set(nt.family, (agg.get(nt.family) ?? 0) + layer.weight / n)
    }
  }
  return [...agg.entries()].map(([family, v]) => ({ family, share: v })).sort((a, b) => b.share - a.share)
}

const RADAR_DIMS = ['清新', '甜度', '浓郁', '温暖', '持久'] as const

function buildRadar(mix: { family: FamilyKey; share: number }[]): { dim: string; v: number }[] {
  const total = mix.reduce((s, m) => s + m.share, 0) || 1
  return RADAR_DIMS.map((dim) => {
    const v = mix.reduce((s, m) => s + (m.share / total) * familyOf(m.family).radarPrior[dim], 0)
    return { dim, v: Math.round(v * 2) / 2 }
  })
}

function buildSynthesis(p: {
  name: string
  mix: { family: FamilyKey; share: number }[]
  keywords: string
  familyZh: string
}): string {
  const d = familyOf(p.mix[0]?.family ?? 'floral')
  const second = p.mix[1] ? familyOf(p.mix[1].family) : null
  const head = second
    ? `以${d.name}为骨、${second.name}为肉。`
    : `一支纯粹的${d.name}。`
  return `${head}${d.scene}${p.keywords ? `；${p.keywords}` : ''}。`
}

function buildProfile(ingredients: string[]): PerfumeEntry['profile'] {
  const banned = IFRA.banned.filter((b) => ingredients.some((i) => hitBanned(i, b)))
  const limitHits = IFRA.limits.filter((l) => ingredients.some((i) => hitLimit(i, l)))
  const igeHits = IGE.filter((g) => ingredients.some((i) => lookupIge(i)?.zh === g.zh))
  const terpene = ingredients.some((i) => /柠檬|香柠檬|佛手柑|柑橘|苦橙|橙皮|橙花|薰衣草/.test(i))
  const muskCaution = ingredients.some((i) => i.includes('麝香'))
  const load = limitHits.length >= 2 ? 'high' : limitHits.length === 1 ? 'mid' : 'low'
  return { banned, terpene, muskCaution, limitHits, igeHits, load }
}

interface RawPerfume {
  id: string
  brand: string
  name: string
  en: string
  familyZh: string
  familyKey: FamilyKey
  concentration: string
  keywords: string
  families: FamilyKey[]
  pyramid: PyramidLayer[]
  ingredients: string[]
}

function toEntry(r: RawPerfume): PerfumeEntry {
  const mix = compositionMix(r)
  return {
    ...r,
    tag: `${r.familyZh} · ${r.concentration}`,
    radar: buildRadar(mix),
    synesthesia: buildSynthesis({ name: r.name, mix, keywords: r.keywords, familyZh: r.familyZh }),
    profile: buildProfile(r.ingredients),
  }
}

const REAL_PERFUMES = (rawPerfumes as unknown as { perfumes: RawPerfume[] }).perfumes.map(toEntry)

/** 黄金算例（教学样本，数据为 v3 报告算例口径） */
const GOLDEN_CASE: PerfumeEntry = {  id: 'golden-case',
  brand: '黄金算例',
  name: '柠檬烯 5% 样本',
  en: 'Limonene 5%',
  tag: '教学算例 · 点估计 CEL=5.0',
  familyZh: '柑橘调',
  familyKey: 'citrus',
  concentration: '教学样本',
  keywords: '柠檬烯、点估计、可复算',
  families: ['citrus', 'green', 'woody'],
  pyramid: [
    { layer: '前调', weight: 40, notes: [{ name: '柠檬烯', family: 'citrus' }] },
    { layer: '中调', weight: 35, notes: [{ name: '柠檬叶', family: 'green' }] },
    { layer: '后调', weight: 25, notes: [{ name: '柠檬木', family: 'woody' }] },
  ],
  ingredients: ['柠檬烯'],
  radar: [
    { dim: '清新', v: 10 },
    { dim: '甜度', v: 2 },
    { dim: '浓郁', v: 3 },
    { dim: '温暖', v: 3 },
    { dim: '持久', v: 4 },
  ],
  synesthesia: '刚剥开的柠檬皮，汁水溅在晨光里，干净得只剩一点木。',
  profile: { banned: [], terpene: true, muskCaution: false, limitHits: [], igeHits: [], load: 'low' },
  synthetic: true,
}

export const PERFUMES: PerfumeEntry[] = [...REAL_PERFUMES, GOLDEN_CASE]

export function getPerfume(id: string): PerfumeEntry {
  return PERFUMES.find((p) => p.id === id) ?? PERFUMES[0]
}

/* ---------------- 身份画像 / 氧化 ---------------- */

export const POPULATIONS = [
  { key: 'healthy', name: '健康成人', note: 'P90 分位线，标准阈值' },
  { key: 'sensitive', name: '敏感肌', note: 'α=3.0 收紧阈值，升 P99，查交叉反应' },
  { key: 'pregnant', name: '孕期', note: '生殖毒性成分直判红灯' },
  { key: 'rhinitis', name: '过敏性鼻炎', note: '高挥发性醛类呼吸道刺激标注' },
  { key: 'anosmic', name: '失嗅人群', note: '氧化预警并入综合判定，视觉替代嗅觉' },
] as const

export type PopulationKey = (typeof POPULATIONS)[number]['key']

export const STORAGE_OPTIONS = [
  { key: 'cool', name: '阴凉避光' },
  { key: 'room', name: '室温' },
  { key: 'hot', name: '高温光照' },
] as const

/* ---------------- 迷你四闸门判定（消费真实 IFRA 数据） ---------------- */

const RANK: Record<RiskLevel, number> = { low: 0, mid: 1, high: 2 }
const VERDICT_HEADLINE: Record<RiskLevel, string> = {
  high: '这一瓶，暂时不建议使用',
  mid: '这一瓶，留意着用',
  low: '这一瓶，可以放心使用',
}
const VERDICT_ADVICE: Record<RiskLevel, string> = {
  high: '停用这一瓶。同香型可换不含禁用成分的新批次；敏感体质换新品前，先在耳后做 48 小时小面积试用。',
  mid: '可以留意着用：减半用量，避开破损皮肤与眼周；开封超过一年的批次建议尽快用完或更换。',
  low: '正常使用即可。避光阴凉保存，开封一年内用完风味与安全性最佳。',
}

export interface Verdict {
  level: RiskLevel
  headline: string
  reasons: string[]
  advice: string
  dominantGate: string
  hits: string
}

export function evaluate(population: PopulationKey, perfumeId: string, d: number): Verdict {
  const p = getPerfume(perfumeId)
  const popName = POPULATIONS.find((x) => x.key === population)?.name ?? ''
  let level: RiskLevel = 'low'
  let gate = '四道闸门均未触发'
  const reasons: string[] = []
  const set = (l: RiskLevel, why: string, g: string) => {
    reasons.push(why)
    if (RANK[l] > RANK[level]) {
      level = l
      gate = g
    }
  }

  if (p.profile.banned.length > 0) {
    const names = p.profile.banned.map((b) => `「${b.zh}」${b.reason ? `（${b.reason}）` : ''}`).join('、')
    set('high', `成分清单命中 ${IFRA.amendment} 完全禁用项：${names}。禁用闸门直接判红。`, '禁用闸门')
  }
  if (population === 'pregnant' && p.profile.muskCaution) {
    set('mid', '成分含麝香类：孕期画像对麝香保持保守，临床闸门给出黄灯提示，建议减频使用。', '临床闸门')
  }
  if (p.profile.terpene && d >= 0.5) {
    const harsh = population === 'sensitive' || population === 'anosmic'
    set(
      harsh ? 'high' : 'mid',
      `开封后氧化程度 D=${d.toFixed(2)} 越过 0.5 高风险线，含萜烯香材（香柠檬/薰衣草类）氧化生成致敏氢过氧化物。${population === 'anosmic' ? '失嗅人群无法靠嗅觉察觉变质，氧化模型即嗅觉替代预警。' : '建议敏感体质减用。'}`,
      '氧化模型',
    )
  } else if (p.profile.terpene && d >= 0.2 && population === 'sensitive') {
    set('mid', `氧化程度 D=${d.toFixed(2)} 进入中风险区间，敏感肌 α=3.0 收紧后建议减用。`, '氧化模型')
  }
  if (population === 'sensitive' && p.profile.load === 'high') {
    set('mid', `成分命中 ${p.profile.limitHits.length} 项 IFRA Cat4 限量（${p.profile.limitHits.map((l) => l.zh).join('、')}），敏感肌分位线升至 P99 后余量偏紧。`, 'QRA2 分位')
  }
  if (population === 'pregnant' && p.profile.load === 'high') {
    set('mid', `孕期画像下致敏原负载偏高（${p.profile.limitHits.map((l) => l.zh).join('、')}），建议降低使用频率。`, 'QRA2 分位')
  }
  if (population === 'rhinitis' && p.profile.load !== 'low') {
    reasons.push('鼻炎画像：高挥发性醛类（柠檬醛、肉桂醛）已加呼吸道刺激标注。')
  }
  if (population === 'rhinitis' && p.profile.igeHits.length > 0) {
    reasons.push(
      `含 IgE Ⅰ 型速发材料（${p.profile.igeHits.map((g) => g.zh).join('、')}）：鼻炎/哮喘人群注意呼吸道速发反应（${p.profile.igeHits[0].risk}）。`,
    )
  }

  if (reasons.length === 0) {
    reasons.push(`四道闸门均未触发：未命中 ${IFRA.amendment} 禁用清单，${popName}画像下分位余量充足，氧化程度 D=${d.toFixed(2)} 处于低风险区间。`)
  }

  const banCount = p.profile.banned.length
  const hits = `${p.profile.limitHits.length + banCount} 项命中 IFRA Cat4 清单${banCount > 0 ? `（含禁用 ${banCount}）` : ''}`
  return { level, headline: VERDICT_HEADLINE[level], reasons, advice: VERDICT_ADVICE[level], dominantGate: gate, hits }
}

/* ---------------- 成分明细（真实限值派生） ---------------- */

export interface IngredientRow {
  inci: string
  zh: string
  conc: string
  level: RiskLevel
  gate: string
  evidence: Evidence
  note: string
  limitPct?: number | null
}

export function buildIngredients(perfumeId: string, d: number, population: PopulationKey): IngredientRow[] {
  const p = getPerfume(perfumeId)
  const rows: IngredientRow[] = []

  if (p.profile.terpene) {
    const linLevel: RiskLevel = d >= 0.5 ? 'high' : d >= 0.2 ? 'mid' : 'low'
    const typicalConc = p.synthetic ? 5 : 0.8
    const qra = analyzeIngredient({ name: 'd-Limonene', concPct: typicalConc, population })
    rows.push({
      inci: 'Limonene / Linalool',
      zh: '柠檬烯 / 芳樟醇（萜烯族）',
      conc: `典型值 ${typicalConc}%`,
      level: linLevel,
      gate: '氧化叠加',
      evidence: 'documented',
      note:
        (d >= 0.5
          ? '氧化程度越过 0.5，生成的氢过氧化物致敏性显著升高。'
          : d >= 0.2
            ? '开封氧化中，敏感肌建议减用。'
            : '氧化程度低，正常使用。') +
        (qra.p99 != null && qra.marginP99 != null
          ? ` QRA2 实算（典型值 ${typicalConc}% 情景）：AEL ${qra.ael?.toFixed(0)}，P99 ${qra.p99.toFixed(1)}，余量 ${qra.marginP99.toFixed(1)}。`
          : ''),
      limitPct: IFRA.limits.find((l) => l.zh.includes('柠檬烯'))?.limitPct ?? null,
    })
  }
  for (const l of p.profile.limitHits) {
    rows.push({
      inci: l.en || l.zh,
      zh: l.zh,
      conc: '未知',
      level: 'low',
      gate: 'IFRA Cat4 限值',
      evidence: 'documented',
      note: `Cat4 成品上限 ${l.limitPct}%（CAS ${l.cas}）。该香水未披露此成分浓度，按文献典型值评估；${l.note}。`,
      limitPct: l.limitPct,
    })
  }
  if (p.profile.muskCaution) {
    rows.push({
      inci: 'Musk',
      zh: '麝香类',
      conc: '未知',
      level: 'low',
      gate: '临床提示',
      evidence: 'documented',
      note: '孕期画像对麝香类保持保守（判定层为孕期黄灯）。',
      limitPct: null,
    })
  }
  for (const g of p.profile.igeHits) {
    rows.push({
      inci: g.en,
      zh: g.zh,
      conc: '未知',
      level: g.risk.replace(/\s/g, '').startsWith('中') ? 'mid' : 'low',
      gate: 'IgE Ⅰ 型速发',
      evidence: 'documented',
      note: `${g.category}｜${g.type}｜${g.risk}：${g.note}`,
      limitPct: null,
    })
  }
  if (rows.length === 0) {
    rows.push({
      inci: '—',
      zh: '未命中限量清单',
      conc: '—',
      level: 'low',
      gate: 'IFRA Cat4',
      evidence: 'documented',
      note: `成分清单未命中 ${IFRA.amendment} 限量/禁用表；天然精油限制项（冷压佛手柑油、芸香油）未出现在该配方。`,
      limitPct: null,
    })
  }
  return rows
}

/* ---------------- 报告固定文案 ---------------- */

/** 概率化暴露面板情景：优先该香水的真实香材（典型值），否则黄金算例教学 */
export function panelScenario(perfumeId: string): { label: string; name: string; concPct: number } {
  const p = getPerfume(perfumeId)
  if (p.synthetic) {
    return { label: '黄金算例：柠檬烯 5%（教学样本，点估计 CEL=5.0）', name: 'd-Limonene', concPct: 5 }
  }
  if (p.profile.terpene) {
    return { label: `文献典型值情景：柠檬烯 0.8%（${p.name} 含萜烯香材，按群体典型值）`, name: 'd-Limonene', concPct: 0.8 }
  }
  const hit = p.profile.limitHits[0]
  if (hit && hit.limitPct) {
    return { label: `限值上限情景：${hit.zh}（假设浓度 = Cat4 上限 ${hit.limitPct}%，最保守）`, name: hit.en || hit.zh, concPct: hit.limitPct }
  }
  return { label: '黄金算例示意：柠檬烯 5%（该香水未命中限量香材，展示方法论）', name: 'd-Limonene', concPct: 5 }
}

export const REPORT = {
  percentiles: {
    ael: 10.0,
    p50: 4.1,
    p90: 8.7,
    p99: 13.2,
    caption:
      '黄金算例示意（柠檬烯 5%：点估计 CEL=5.0 μg/cm²/day，AEL/CEL=20，单位 μg/cm²/day）。CEL 五参数概率化后输出 P50/P90/P99 分位谱；脆弱人群采用 P99 分位线。',
  },
  populationNote:
    '身份画像直接改写判定参数：敏感肌 α=3.0 收紧且分位线升至 P99；孕期触发生殖毒性检查；失嗅人群将氧化等级并入综合判定；鼻炎加注呼吸道刺激。换一个人群，同一瓶香水的结论可能完全不同。',
  disclaimer: `本报告基于公开数据（${IFRA.amendment} Cat4 清单、${(rawPerfumes as unknown as { source: string }).source}）的概率估算，不构成医学建议。QRA 方法仍在国际验证中，系统以 QRA2 分位、临床阈值、IFRA 限值三源交叉校验。`,
}

/* ---------------- 手动成分表通道 ---------------- */

export interface ParsedIngredient {
  raw: string
  name: string
  pct: number | null
}

export function parseManualIngredients(text: string): ParsedIngredient[] {
  return text
    .split(/[\n,，、;；]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      const m = s.match(/^(.+?)\s*[:：]?\s*([\d.]+)\s*%?$/)
      if (m && /\d/.test(m[2])) {
        return { raw: s, name: m[1].trim(), pct: parseFloat(m[2]) }
      }
      return { raw: s, name: s.replace(/[:：]\s*$/, '').trim(), pct: null }
    })
    .filter((p) => p.name.length > 0)
}

export interface ManualMatch extends ParsedIngredient {
  matched: boolean
  kind?: 'banned' | 'limit' | 'eu26' | 'ige' | 'dict' | 'material'
  zh?: string
  level?: RiskLevel
  gate?: string
  evidence?: Evidence
  note?: string
  limitPct?: number | null
}

/** 真实数据匹配：IFRA 禁用 → IFRA 限量（QRA2 引擎实算）→ CAS 词典，均未命中则不静默 */
export function matchManualIngredient(item: ParsedIngredient, population: PopulationKey): ManualMatch {
  // 最长键优先（见 resolveBanned/resolveLimit 的说明）
  const ban = resolveBanned(item.name)
  if (ban) {
    return {
      ...item,
      matched: true,
      kind: 'banned',
      zh: ban.zh,
      level: 'high',
      gate: `${IFRA.amendment} 禁用`,
      evidence: 'documented',
      note: `${ban.reason || ban.control}。任何浓度下均判红。`,
    }
  }

  const lim = resolveLimit(item.name)
  if (lim && lim.limitPct != null) {
    const r = analyzeIngredient({ name: item.name, concPct: item.pct, population, ifraLimitPct: lim.limitPct })
    const parts: string[] = []
    if (r.ifraReason) parts.push(r.ifraReason)
    if (r.qra2Reason) parts.push(r.qra2Reason)
    if (r.p50 != null && r.p90 != null && r.p99 != null) {
      parts.push(`AEL ${r.ael?.toFixed(0)}，CEL P50/P90/P99 = ${r.p50.toFixed(1)}/${r.p90.toFixed(1)}/${r.p99.toFixed(1)}`)
    }
    return {
      ...item,
      matched: true,
      kind: 'limit',
      zh: r.zh || lim.zh,
      level: r.level,
      gate: r.dominantGate === 'QRA2 分位' || r.dominantGate === 'IFRA 闸门' ? r.dominantGate : 'IFRA Cat4 限值',
      evidence: r.aelEvidence === 'indicative' ? 'indicative' : 'documented',
      note: parts.join('；') + '。',
      limitPct: lim.limitPct,
    }
  }

  const dict = longestHit(DICT_INDEX, norm(item.name))
  if (dict) {
    return {
      ...item,
      matched: true,
      kind: 'dict',
      zh: dict.zh,
      level: 'low',
      gate: 'CAS 词典收录',
      evidence: 'documented',
      note: `收录于${dict.source === 'natural' ? '天然' : dict.source === 'synthetic' ? '合成' : '香精'}香料词典（CAS ${dict.cas}），IFRA Cat4 未设限。`,
    }
  }

  // EU 26 标注致敏原（未进上面分支的，如大茴香醇/苯甲酸苄酯等）
  const eu = lookupEu26(item.name)
  if (eu) {
    return {
      ...item,
      matched: true,
      kind: 'eu26',
      zh: eu.zh,
      level: 'mid',
      gate: 'EU 26 标注清单',
      evidence: 'documented',
      note: `${eu.note}。欧盟驻留类产品 >0.01% 需单独标注（CAS ${eu.cas}）；敏感人群留意。`,
    }
  }

  // IgE Ⅰ 型速发材料（树脂/净油类）
  const ige = lookupIge(item.name)
  if (ige) {
    const level: RiskLevel = ige.risk.replace(/\s/g, '').startsWith('中') ? 'mid' : 'low'
    return {
      ...item,
      matched: true,
      kind: 'ige',
      zh: ige.zh,
      level,
      gate: 'IgE Ⅰ 型速发',
      evidence: 'documented',
      note: `${ige.category}｜${ige.type}｜${ige.risk}：${ige.note}`,
    }
  }

  // 香材词典（天然 / 合成单体）
  const mat = lookupMaterial(item.name)
  if (mat) {
    return {
      ...item,
      matched: true,
      kind: 'material',
      zh: item.name,
      level: 'low',
      gate: mat.kind,
      evidence: 'documented',
      note: `收录于${mat.category}（${mat.kind}），无限值与速发记录。`,
    }
  }

  return { ...item, matched: false }
}

/* ---------------- 演示案例（真实香水） ---------------- */

export const DEMO_CASES: { title: string; desc: string; to: string; population: PopulationKey; perfumeId: string }[] = [
  { title: '孕期 × 香奈儿五号', desc: '麝香类临床提示，黄灯', to: '/report', population: 'pregnant', perfumeId: 'chanel-no-5' },
  { title: '敏感肌 × 迪奥清新之水（开封 14 个月）', desc: '柑橘萜烯氧化，红灯', to: '/report', population: 'sensitive', perfumeId: 'eau-sauvage' },
  { title: '失嗅人群 × 鼠尾草与海盐', desc: '把这一瓶翻译成色彩与文字', to: '/vision', population: 'anosmic', perfumeId: 'wood-sage-sea-salt' },
  { title: '健康人群 × 黄金算例', desc: '点估计绿灯，可复算', to: '/report', population: 'healthy', perfumeId: 'golden-case' },
]
