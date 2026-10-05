import { CircleAlert, CircleCheck, TriangleAlert } from 'lucide-react'
import type { Evidence, RiskLevel } from '../lib/aura'
import { EVIDENCE_LABEL, RISK_LABEL } from '../lib/aura'
import { cn } from '../lib/utils'

const RISK_STYLE: Record<RiskLevel, { color: string; Icon: typeof CircleCheck }> = {
  low: { color: 'var(--risk-low)', Icon: CircleCheck },
  mid: { color: 'var(--risk-mid)', Icon: TriangleAlert },
  high: { color: 'var(--risk-high)', Icon: CircleAlert },
}

/** 风险三重编码：色点 + 图标 + 文字（不只靠颜色，色盲可辨） */
export function RiskMark({ level, className }: { level: RiskLevel; className?: string }) {
  const { color, Icon } = RISK_STYLE[level]
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 text-sm font-medium', className)}
      style={{ color }}
    >
      <Icon size={17} strokeWidth={2.2} aria-hidden />
      <span
        aria-label={`风险判定：${RISK_LABEL[level]}`}
        className="rounded-full px-0.5"
        style={{ color }}
      >
        {RISK_LABEL[level]}
      </span>
    </span>
  )
}

/** 证据等级标签：文献值 / 演示估计 / 数据不足 */
export function EvidenceTag({ evidence }: { evidence: Evidence }) {
  const insufficient = evidence === 'insufficient'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs whitespace-nowrap',
        insufficient ? 'border-risk-mid text-risk-mid' : 'border-foreground/30 text-foreground/80',
      )}
    >
      {EVIDENCE_LABEL[evidence]}
    </span>
  )
}
