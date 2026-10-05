/**
 * QRA2 · 氧化动态风险（Step 7）
 * D = 1 − exp(−k_eff · t)，k_eff = k25 · Q10^((T − 25)/10) · (1 + L)
 * t 为开封天数；L 为光照暴露 0-1；阈值 0.2 / 0.5 三档（失嗅人群的嗅觉替代预警）。
 * k25/Q10 已标定：3 个月阴凉 D≈0.09（低），14 个月室温 D≈0.62（高），14 个月高温光照 D≈0.91。
 */

export type StorageEnvKey = 'cool' | 'room' | 'hot'

export interface StorageEnv {
  T: number
  L: number
}

export const STORAGE_ENV: Record<StorageEnvKey, StorageEnv> = {
  cool: { T: 15, L: 0 },
  room: { T: 25, L: 0.3 },
  hot: { T: 35, L: 0.8 },
}

export const K25_TERPENE = 0.00178
export const Q10 = 1.8
export const T_REF = 25

export function computeD(months: number, env: StorageEnv, k25 = K25_TERPENE, q10 = Q10): number {
  const kEff = k25 * Math.pow(q10, (env.T - T_REF) / 10) * (1 + env.L)
  return 1 - Math.exp(-kEff * months * 30)
}

export function dLevel(d: number): { label: string; color: string } {
  if (d < 0.2) return { label: '低', color: 'var(--risk-low)' }
  if (d < 0.5) return { label: '中', color: 'var(--risk-mid)' }
  return { label: '高', color: 'var(--risk-high)' }
}
