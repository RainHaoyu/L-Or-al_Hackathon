import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { STORAGE_ENV, computeD } from './qra2/oxidation'
import type { PopulationKey } from './aura'

export type Mode = 'normal' | 'anosmia' | 'sensitive'
export type TextSize = 'md' | 'lg' | 'xl'
export type Register = 'light' | 'dark'
export type StorageKey = 'cool' | 'room' | 'hot'

/** 引擎来源标记：后端计算（含版本）或本地引擎兜底 */
export interface EngineMeta {
  source: 'backend' | 'local'
  engine: string
  models?: string
}

/** 分析流选择状态：首页三步收集，报告/显影页消费 */
export interface Analysis {
  population: PopulationKey
  setPopulation: (p: PopulationKey) => void
  perfumeId: string
  setPerfumeId: (id: string) => void
  openedMonths: number
  setOpenedMonths: (m: number) => void
  storage: StorageKey
  setStorage: (s: StorageKey) => void
  oxidationD: number
  engineMeta: EngineMeta | null
  setEngineMeta: (m: EngineMeta | null) => void
}

interface AppState extends Analysis {
  mode: Mode
  setMode: (m: Mode) => void
  textSize: TextSize
  cycleTextSize: () => void
}

const Ctx = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>('normal')
  const [textSize, setTextSize] = useState<TextSize>('md')
  const [population, setPopulation] = useState<PopulationKey>('sensitive')
  const [perfumeId, setPerfumeId] = useState('eau-sauvage')
  const [openedMonths, setOpenedMonths] = useState(14)
  const [storage, setStorage] = useState<StorageKey>('room')
  const [engineMeta, setEngineMeta] = useState<EngineMeta | null>(null)

  useEffect(() => {
    document.documentElement.dataset.mode = mode
  }, [mode])
  useEffect(() => {
    document.documentElement.dataset.textsize = textSize
  }, [textSize])

  const cycleTextSize = () =>
    setTextSize((s) => (s === 'md' ? 'lg' : s === 'lg' ? 'xl' : 'md'))

  /**
   * 双向联动（用户反馈）：身份画像 ↔ 顶栏模式
   * - 选身份：敏感肌→敏感模式、失嗅人群→失嗅模式、其余（健康/孕期/鼻炎）→普通模式
   * - 切模式：敏感→敏感肌、失嗅→失嗅人群；切回普通仅当当前是特殊身份时重置为健康成人
   *   （孕期/鼻炎等画像不因显示模式切回普通而丢失）
   */
  const setPopulationLinked: Analysis['setPopulation'] = (p) => {
    setPopulation(p)
    setMode(p === 'sensitive' ? 'sensitive' : p === 'anosmic' ? 'anosmia' : 'normal')
  }
  const setModeLinked: AppState['setMode'] = (m) => {
    setMode(m)
    if (m === 'sensitive') {
      setPopulation('sensitive')
    } else if (m === 'anosmia') {
      setPopulation('anosmic')
    } else if (population === 'sensitive' || population === 'anosmic') {
      setPopulation('healthy')
    }
  }

  /** 氧化 D 值由 QRA2 模块统一计算（Q10 + 光照模型） */
  const oxidationD = computeD(openedMonths, STORAGE_ENV[storage])

  return (
    <Ctx.Provider
      value={{
        mode,
        setMode: setModeLinked,
        textSize,
        cycleTextSize,
        population,
        setPopulation: setPopulationLinked,
        perfumeId,
        setPerfumeId,
        openedMonths,
        setOpenedMonths,
        storage,
        setStorage,
        oxidationD,
        engineMeta,
        setEngineMeta,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}

export function useApp(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useApp must be used inside AppProvider')
  return v
}

/** 按路由切换双注册，作用于 html 上的 CSS 变量作用域 */
export function useRegister(register: Register) {
  useEffect(() => {
    document.documentElement.dataset.register = register
    return () => {
      document.documentElement.dataset.register = 'light'
    }
  }, [register])
}
