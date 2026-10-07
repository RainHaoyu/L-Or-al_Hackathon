/**
 * 通感文案接线的边界测试（版本分离后的安全契约）。
 *
 * 要守两件事，都是"会骗到用户"的那类问题：
 *  1. **只显示与当前选择对应的文案**：用户改了人群/香水/开封月数后，
 *     绝不能继续显示上一次那份输入算出来的 AI 文案（会被当成事实）。
 *  2. **AI 只写文字、不参与判定**：这条路径不携带任何数值，也不 import 风险计算模块。
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { PERFUMES, evaluate, buildIngredients } from './aura'
import {
  isBackendTextFresh,
  localSynesthesiaText,
  resolveSynesthesiaText,
  type BackendText,
  type TextInputs,
} from './synesthesia-text'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const perfume = PERFUMES[0]
const current: TextInputs = {
  perfumeId: perfume.id,
  population: 'sensitive',
  openedMonths: 14,
  storage: 'room',
  mode: 'sensitive',
}

const backendOk: BackendText = {
  ...current,
  text: 'AI 写的通感文案（四句式）',
  model: 'qwen-max',
  engine: 'aura-qra2/1.0',
}

describe('文案来源解析', () => {
  it('快照一致时用后端 AI 文案，并标出来源与模型', () => {
    const r = resolveSynesthesiaText(perfume, current, backendOk)
    expect(r.source).toBe('backend')
    expect(r.model).toBe('qwen-max')
    expect(r.text).toBe(backendOk.text)
  })

  it('没有后端结果时回退本地规则文案（观感与接线前逐字一致）', () => {
    const r = resolveSynesthesiaText(perfume, current, null)
    expect(r.source).toBe('local')
    expect(r.model).toBe('local')
    expect(r.text).toBe(localSynesthesiaText(perfume, current.mode))
  })

  it('后端自己降级成 template 时不冒充 AI 文案', () => {
    const r = resolveSynesthesiaText(perfume, current, { ...backendOk, model: 'template' })
    expect(r.source).toBe('local')
    expect(r.text).toBe(localSynesthesiaText(perfume, current.mode))
  })

  it('空文案/纯空白不算有效后端文案', () => {
    for (const text of ['', '   ', '\n']) {
      expect(isBackendTextFresh({ ...backendOk, text }, current)).toBe(false)
      expect(resolveSynesthesiaText(perfume, current, { ...backendOk, text }).source).toBe('local')
    }
  })
})

describe('新鲜度：任一输入变了都必须回退本地文案', () => {
  const cases: [string, Partial<TextInputs>][] = [
    ['换了香水', { perfumeId: 'shalimar' }],
    ['换了人群', { population: 'healthy' }],
    ['改了开封月数', { openedMonths: 3 }],
    ['改了存放环境', { storage: 'hot' }],
    ['切了显示模式', { mode: 'anosmia' }],
  ]
  for (const [label, patch] of cases) {
    it(label, () => {
      const changed = { ...current, ...patch }
      expect(isBackendTextFresh(backendOk, changed)).toBe(false)
      const r = resolveSynesthesiaText(perfume, changed, backendOk)
      expect(r.source).toBe('local')
      expect(r.text).not.toBe(backendOk.text)
    })
  }

  it('开封月数是数字比较，14 与 14 视为一致（不会被字符串化搞坏）', () => {
    expect(isBackendTextFresh({ ...backendOk, openedMonths: 14 }, { ...current, openedMonths: 14 })).toBe(true)
  })
})

describe('AI 只写文字：不参与判定', () => {
  it('解析结果只有 text/source/model 三个字段，不携带任何数值', () => {
    const r = resolveSynesthesiaText(perfume, current, backendOk)
    expect(Object.keys(r).sort()).toEqual(['model', 'source', 'text'])
  })

  it('有无后端文案，判定与成分明细逐字段相同', () => {
    const before = evaluate(current.population, current.perfumeId, 0.42)
    const rowsBefore = buildIngredients(current.perfumeId, 0.42, current.population)
    // 文案只是展示层：这里不存在任何把它喂进判定的入口
    resolveSynesthesiaText(perfume, current, backendOk)
    const after = evaluate(current.population, current.perfumeId, 0.42)
    const rowsAfter = buildIngredients(current.perfumeId, 0.42, current.population)
    expect(after).toEqual(before)
    expect(rowsAfter).toEqual(rowsBefore)
  })

  it('风险计算模块不 import 文案模块（架构上就喂不进去）', () => {
    for (const rel of ['aura.ts', 'qra2/engine.ts', 'qra2/qra2.ts']) {
      const p = path.join(HERE, rel)
      let src = ''
      try {
        src = readFileSync(p, 'utf8')
      } catch {
        continue
      }
      expect(src, `${rel} 不应依赖 synesthesia-text`).not.toContain('synesthesia-text')
    }
  })

  it('页面用文本节点渲染，不走 innerHTML（AI 文案按纯文本处理）', () => {
    const vision = readFileSync(path.join(HERE, '..', 'pages', 'Vision.tsx'), 'utf8')
    expect(vision).toContain('resolveSynesthesiaText(')
    expect(vision).not.toContain('dangerouslySetInnerHTML')
  })

  it('分析流确实把后端文案存了下来（接线断了要在这里变红）', () => {
    // 1-1 的教训：接线写死/漏掉时，类型检查与业务测试都不会报错，只能靠源码守卫
    const flow = readFileSync(path.join(HERE, '..', 'components', 'AnalyzeFlow.tsx'), 'utf8')
    expect(flow).toContain('setBackendText({')
    expect(flow).toMatch(/text:\s*r\.data\.synesthesia\.text/)
    expect(flow).toMatch(/model:\s*r\.data\.synesthesia\.model/)
    // 失败/降级两条路径都要清掉，避免拿旧文案冒充新结果
    expect(flow.match(/setBackendText\(null\)/g)?.length).toBe(2)
  })
})
