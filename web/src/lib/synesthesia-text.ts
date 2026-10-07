/**
 * 通感文案的来源解析：**后端 AI 优先，本地规则兜底**。
 *
 * 背景：后端 `/analyze` 一直会返回 qwen-max 生成的文案（`data.synesthesia.text`），
 * 但前端此前只取了 `model` 字段做徽标，正文仍渲染本地拼的文案
 * ⟹ 结果是「配了 Key 也读不到 AI 写的文案」，而页面还写着"文案由 qwen-max 生成"，
 * 属于界面在说假话。这里把后端文案真正接上屏，同时守住两条边界：
 *
 * 1. **新鲜度边界**：后端文案必须与当前选择（香水 / 人群 / 开封月数 / 存放 / 模式）
 *    逐项一致才允许显示，否则回退本地文案——绝不能让用户看到"上一次那份输入"的文案
 *    （用户改了人群或香水后，报告页显示旧文案会被当成事实）。
 * 2. **只上屏、不参与判定**：AI 文案只走展示与朗读（Vision 页），
 *    不进入 `evaluate()` / `buildIngredients()` 的任何计算路径。
 *    判定与所有数值永远来自引擎（后端或本地同算法），LLM 输出不参与风险结论。
 *    本模块**不 import 任何风险计算模块**，这条边界由 synesthesia-text.test.ts 断言。
 */
import type { PerfumeEntry, PopulationKey } from './aura'
import type { Mode, StorageKey } from './state'
import { buildSynesthesia } from './vision/engine'

/** 后端返回的文案 + 它对应的那次输入快照（快照只用于新鲜度判断，不参与计算） */
export interface BackendText {
  perfumeId: string
  population: PopulationKey
  openedMonths: number
  storage: StorageKey
  mode: Mode
  text: string
  /** 实际产出该文案的模型名；后端给 'template' 表示它自己也没走成 LLM */
  model: string
  engine?: string
}

/** 当前选择（与 BackendText 的快照字段一一对应） */
export interface TextInputs {
  perfumeId: string
  population: PopulationKey
  openedMonths: number
  storage: StorageKey
  mode: Mode
}

export type TextSource = 'backend' | 'local'

export interface ResolvedText {
  text: string
  source: TextSource
  /** 展示用的模型名：后端文案给 qwen-max 等，本地文案给 'local' */
  model: string
}

/** 后端文案是否对应当前输入；任一项不同、或文案为空，都视为不可用 */
export function isBackendTextFresh(
  backend: BackendText | null | undefined,
  current: TextInputs,
): boolean {
  if (!backend) return false
  if (!backend.text || !backend.text.trim()) return false
  if (backend.model === 'template') return false // 后端自己都降级了，本地文案更完整
  return (
    backend.perfumeId === current.perfumeId &&
    backend.population === current.population &&
    backend.storage === current.storage &&
    backend.mode === current.mode &&
    Number(backend.openedMonths) === Number(current.openedMonths)
  )
}

/** 本地规则文案——与接入后端 AI 之前逐字一致，保证降级后观感不变 */
export function localSynesthesiaText(perfume: PerfumeEntry, mode: Mode): string {
  return mode === 'anosmia' ? buildSynesthesia(perfume, 'anosmia') : perfume.synesthesia
}

/**
 * 解析要显示的文案。
 * 返回对象**只有 text / source / model 三个字段**：这条路径不携带任何数值，
 * 也就无法顺带影响报告里的判定与分位数。
 */
export function resolveSynesthesiaText(
  perfume: PerfumeEntry,
  current: TextInputs,
  backend: BackendText | null | undefined,
): ResolvedText {
  if (isBackendTextFresh(backend, current)) {
    const fresh = backend as BackendText
    return { text: fresh.text.trim(), source: 'backend', model: fresh.model || 'backend' }
  }
  return { text: localSynesthesiaText(perfume, current.mode), source: 'local', model: 'local' }
}
