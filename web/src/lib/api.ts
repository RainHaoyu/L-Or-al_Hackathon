/**
 * 后端客户端（aura/api，默认 http://localhost:8001/api/v1）
 * 设计要点：超时后静默回退本地引擎（后端是可选件，见 README §三）。
 *
 * 超时取值依据（实测，2026-10-05）：
 *   - **引擎 + 端点本身就要 4.4–5.0 s**：关掉 Key 走规则模板也测到 4445–5037 ms，
 *     与云端无关，是 QRA2 蒙特卡洛本身的成本。所以前端预算必须「引擎 + LLM」两段相加。
 *   - 单次 qwen-max 文案：normal 2.9–4.5 s｜sensitive 2.8–3.6 s｜anosmia 7.7–9.6 s
 *     （anosmia 的 prompt 要求四五句、每句都要具体意象，输出长约 3 倍，耗时也约 3 倍）
 *   ⇒ 端到端最坏 ≈ 引擎 5 s + 后端 LLM 总预算（api/app/modules/llm.py 的 _BUDGET）：
 *        normal / sensitive：5 + 6  = 11 s → 前端给 13 s
 *        anosmia          ：5 + 12 = 17 s → 前端给 19 s
 *
 * 两个曾经的错值，别再改回去：
 *   - 全局 2000 ms：配了 Key 时文案必被 abort ⟹ 永远只看到规则模板
 *   - 全局 15 s：normal 够用，但 anosmia 实测最坏约 14.6 s，卡在阈值边缘会偶发落回模板
 * 跨语言不变式（前端超时 > 引擎 5 s + 后端预算）由 test_llm_budget.py 读本文件断言。
 */

import type { AnalyzeRequest, AnalyzeResponse, ImageRecognitionResponse, ProductsResponse } from './api-types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001/api/v1'

/** 引擎侧固定开销（毫秒）：QRA2 计算 + 端点，实测 4.4–5.0 s */
export const ENGINE_BUDGET_MS = 5_000

/** 其他端点（health / products / recognition）的超时；识别实测约 1.1 s，取 13 s 余量充足 */
const DEFAULT_TIMEOUT = 13_000

/** /analyze 的前端超时（毫秒），按模式取值；推导见文件头注释 */
export const ANALYZE_TIMEOUT: Record<NonNullable<AnalyzeRequest['mode']>, number> = {
  normal: 13_000,
  sensitive: 13_000,
  anosmia: 19_000,
}

async function req<T>(path: string, init?: RequestInit, timeout = DEFAULT_TIMEOUT): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeout)
  try {
    const r = await fetch(`${BASE}${path}`, { ...init, signal: ctrl.signal })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return (await r.json()) as T
  } finally {
    clearTimeout(timer)
  }
}

export const api = {
  baseUrl: BASE,

  health: () => req<{ data: { status: string; engine: string } }>('/health'),

  products: (q: string, limit = 8) =>
    req<ProductsResponse>(`/products?q=${encodeURIComponent(q)}&limit=${limit}`),

  recognizeImage: (image: string, filename: string) =>
    req<ImageRecognitionResponse>('/recognition/image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image, filename }),
    }),

  /**
   * @param payload.mode 必须传真实模式（normal / anosmia / sensitive）。
   *   写死 'normal' 会让「失嗅模式走 AI」静默失效——失嗅模式的 prompt 与
   *   输出长度都不一样，后端按 mode 选 prompt，前端也必须把 mode 传下去。
   */
  analyze: (payload: AnalyzeRequest) =>
    req<AnalyzeResponse>(
      '/analyze',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
      ANALYZE_TIMEOUT[payload.mode ?? 'normal'],
    ),
}

export async function backendAlive(): Promise<boolean> {
  try {
    const r = await api.health()
    return r.data.status === 'ok'
  } catch {
    return false
  }
}
