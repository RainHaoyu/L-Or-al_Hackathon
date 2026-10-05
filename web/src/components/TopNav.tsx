import { Link, NavLink } from 'react-router'
import { useApp } from '../lib/state'
import { cn } from '../lib/utils'

const NAV = [
  { to: '/', label: '首页' },
  { to: '/report', label: '预警报告' },
  { to: '/vision', label: '香气显影' },
]

const MODES = [
  { key: 'normal', label: '普通' },
  { key: 'anosmia', label: '失嗅' },
  { key: 'sensitive', label: '敏感' },
] as const

/** 顶栏：品名 + 光谱带签名 + 导航 + 三模式切换 + A+ 字号 */
export function TopNav() {
  const { mode, setMode, textSize, cycleTextSize } = useApp()
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link to="/" className="focus-visible-strong font-display text-xl tracking-wide">
          万象 <span className="text-gold">AURA</span>
        </Link>

        <nav aria-label="主导航" className="ml-2 hidden items-center gap-1 sm:flex">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                cn(
                  'focus-visible-strong rounded-sm px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'text-foreground underline decoration-gold decoration-2 underline-offset-8'
                    : 'text-muted-foreground hover:text-foreground',
                )
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <div
            role="group"
            aria-label="模式（与身份画像联动）"
            title="与第一步身份画像双向联动：敏感 ⇄ 敏感肌，失嗅 ⇄ 失嗅人群"
            className="flex rounded-full border border-border p-0.5"
          >
            {MODES.map((m) => (
              <button
                key={m.key}
                onClick={() => setMode(m.key)}
                aria-pressed={mode === m.key}
                className={cn(
                  'focus-visible-strong min-h-9 rounded-full px-3 text-sm transition-colors',
                  mode === m.key
                    ? 'bg-ink text-paper'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
          <button
            onClick={cycleTextSize}
            aria-label={`字号调节，当前${textSize === 'md' ? '标准' : textSize === 'lg' ? '大' : '特大'}，点击切换`}
            aria-pressed={textSize !== 'md'}
            className={cn(
              'focus-visible-strong min-h-11 min-w-11 rounded-full border text-sm font-semibold',
              textSize === 'md' ? 'border-border hover:bg-secondary' : 'border-ink bg-ink text-paper',
            )}
          >
            A+
          </button>
        </div>
      </div>
      {/* 光谱带：七族色谱签名，贯穿全站 */}
      <div aria-hidden className="spectrum-band h-[3px] w-full animate-spectrum-draw" />
    </header>
  )
}
