/**
 * 失嗅模式要真的走后端 AI（待办 1-1）+ 超时按模式取值（待办 1-2）。
 *
 * 缺陷原状：AnalyzeFlow 调 /analyze 时把 mode 写死 'normal'
 * ⟹ 顶栏切「失嗅模式」时，后端仍按 normal 生成文案；用户看到的那段长文案
 *   其实是前端本地拼的，**「失嗅模式走 AI」从未生效**。
 *
 * 修 1-1 会立刻暴露 1-2：失嗅模式的 prompt 要求四五句具体意象，输出长约 3 倍、
 * 耗时也约 3 倍（实测 7.7–9.6 s），若超时还是 normal 那一档就必然落回模板。
 * 所以两条一起改、一起测。
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ANALYZE_TIMEOUT, ENGINE_BUDGET_MS, api } from './api'

const HERE = path.dirname(fileURLToPath(import.meta.url))

/** 与 api/app/modules/llm.py::_BUDGET 对齐；Python 侧有反向断言读 api.ts */
const BACKEND_BUDGET_MS = { normal: 6_000, sensitive: 6_000, anosmia: 12_000 } as const

type Seen = { url: string; body: { mode?: string }; aborted: boolean }

/** 用一个永不 resolve 的 fetch 替身：只会因 AbortController 而 reject */
function stubFetch(): Seen[] {
  const seen: Seen[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init: RequestInit) => {
      const rec: Seen = { url, body: JSON.parse(String(init.body)), aborted: false }
      seen.push(rec)
      return new Promise((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => {
          rec.aborted = true
          reject(new Error('aborted'))
        })
      })
    }),
  )
  return seen
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('ANALYZE_TIMEOUT', () => {
  it('三种模式都有值，且失嗅模式最宽松', () => {
    expect(Object.keys(ANALYZE_TIMEOUT).sort()).toEqual(['anosmia', 'normal', 'sensitive'])
    expect(ANALYZE_TIMEOUT.anosmia).toBeGreaterThan(ANALYZE_TIMEOUT.normal)
    expect(ANALYZE_TIMEOUT.anosmia).toBeGreaterThan(ANALYZE_TIMEOUT.sensitive)
  })

  it('每种模式都覆盖「引擎开销 + 后端 LLM 预算」', () => {
    for (const mode of ['normal', 'sensitive', 'anosmia'] as const) {
      expect(ANALYZE_TIMEOUT[mode]).toBeGreaterThan(ENGINE_BUDGET_MS + BACKEND_BUDGET_MS[mode])
    }
  })
})

describe('api.analyze', () => {
  it('把真实模式传给后端（不能写死 normal）', async () => {
    const seen = stubFetch()
    vi.useFakeTimers()

    const p = api.analyze({ product_id: 'eau-sauvage', mode: 'anosmia' }).catch((e) => e as Error)
    await vi.advanceTimersByTimeAsync(100)
    expect(seen[0].url).toContain('/analyze')
    expect(seen[0].body.mode).toBe('anosmia')

    await vi.advanceTimersByTimeAsync(ANALYZE_TIMEOUT.anosmia + 100)
    expect(await p).toBeInstanceOf(Error)
  })

  it('超时按模式区分：同一时刻 normal 已 abort，anosmia 仍在等', async () => {
    const seen = stubFetch()
    vi.useFakeTimers()

    const normal = api.analyze({ product_id: 'x', mode: 'normal' }).catch((e) => e as Error)
    await vi.advanceTimersByTimeAsync(ANALYZE_TIMEOUT.normal - 100)
    expect(seen[0].aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(200)
    expect(seen[0].aborted).toBe(true)
    await normal

    const anosmia = api.analyze({ product_id: 'x', mode: 'anosmia' }).catch((e) => e as Error)
    await vi.advanceTimersByTimeAsync(ANALYZE_TIMEOUT.normal - 100)
    expect(seen[1].aborted, '失嗅模式在 normal 的超时点上不应该已经被打断').toBe(false)
    await vi.advanceTimersByTimeAsync(ANALYZE_TIMEOUT.anosmia - ANALYZE_TIMEOUT.normal + 200)
    expect(seen[1].aborted).toBe(true)
    await anosmia
  })
})

describe('AnalyzeFlow 的接线', () => {
  const src = readFileSync(path.join(HERE, '..', 'components', 'AnalyzeFlow.tsx'), 'utf8')

  it('从 useApp 取出真实 mode，且不再写死 mode: normal', () => {
    expect(src, 'useApp() 解构里应包含 mode').toMatch(/^\s*mode,$/m)
    expect(src, "不要再出现 mode: 'normal'").not.toMatch(/mode:\s*'normal'/)
    expect(src, '应把 mode 传给 api.analyze').toMatch(/api\.analyze\(\{[\s\S]{0,200}?\bmode,/)
  })

  it('阶段提示用的是按模式推导的超时', () => {
    expect(src).toContain('ANALYZE_TIMEOUT[mode]')
    expect(src).toContain('ENGINE_BUDGET_MS')
  })
})
