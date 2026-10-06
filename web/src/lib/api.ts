/**
 * 后端客户端（aura/api，默认 http://localhost:8001/api/v1）
 * 设计要点：超时后静默回退本地引擎（演示日断网双保险）。
 *
 * TIMEOUT 取值说明（实测，2026-10-05）：
 *   - 瓶身识别（qwen-vl-max）：约 1.1 s
 *   - /analyze 端到端（含 qwen-max 通感文案）：**实测 8.9–11.0 s**
 *     （后端 llm.py 的 _TIMEOUT=10，且 qwen-max → qwen-plus 两档串行尝试）
 * 早期取 2000 ms 会把有 Key 时的 LLM 文案全部截断 → 永远落规则模板，
 * 即「配了 Key 也看不到效果」。故放宽到 15 s：
 *   有 Key 时能等到真实文案；后端不可用/断网时仍在 15 s 内回退本地引擎。
 */

import type { AnalyzeRequest, AnalyzeResponse, ImageRecognitionResponse, ProductsResponse } from './api-types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001/api/v1'
const TIMEOUT = 15_000

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT)
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

  analyze: (payload: AnalyzeRequest) =>
    req<AnalyzeResponse>('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
}

export async function backendAlive(): Promise<boolean> {
  try {
    const r = await api.health()
    return r.data.status === 'ok'
  } catch {
    return false
  }
}
