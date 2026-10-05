/**
 * 后端客户端（aura/api，默认 http://localhost:8001/api/v1）
 * 设计要点：短超时 + 任何失败静默回退本地引擎（演示日断网双保险）。
 * 类型全部来自 api-types.ts（openapi 自动生成，勿手写）。
 */

import type { AnalyzeRequest, AnalyzeResponse, ImageRecognitionResponse, ProductsResponse } from './api-types'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8001/api/v1'
const TIMEOUT = 2000

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
