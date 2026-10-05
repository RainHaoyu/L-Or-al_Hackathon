import { useEffect, useRef, useState } from "react";
import type { EvidenceLevel, RiskLevel } from "./api-types";

export function Card({ title, children, className = "", variant = "panel" }: {
  title?: React.ReactNode; children: React.ReactNode; className?: string;
  variant?: "panel" | "ring" | "gold";
}) {
  const ring =
    variant === "ring" ? "grad-ring glow-soft"
      : variant === "gold" ? "grad-ring-gold"
        : "bg-panel ring-1 ring-white/10";
  return (
    <section className={`rounded-2xl p-4 md:p-5 ${ring} ${className}`}>
      {title && <h2 className="mb-3 text-base md:text-lg font-semibold text-ink">{title}</h2>}
      {children}
    </section>
  );
}

const LEVEL_STYLE: Record<RiskLevel, { label: string; cls: string }> = {
  green: { label: "绿灯·安全", cls: "bg-emerald-400/10 text-ok ring-ok/40" },
  yellow: { label: "黄灯·谨慎", cls: "bg-amber-400/10 text-warn ring-warn/40" },
  red: { label: "红灯·避免", cls: "bg-rose-400/10 text-danger ring-danger/40" },
};

export function LevelPill({ level, small = false }: { level: RiskLevel; small?: boolean }) {
  const s = LEVEL_STYLE[level];
  return (
    <span className={`inline-flex items-center rounded-full font-medium ring-1 ${s.cls} ${
      small ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"}`}>
      {s.label}
    </span>
  );
}

const EVIDENCE_LABEL: Record<EvidenceLevel, string> = {
  documented: "公开数据",
  indicative: "演示估计",
  insufficient: "数据不足",
};

export function EvidenceTag({ level }: { level: EvidenceLevel }) {
  const cls =
    level === "documented" ? "bg-gold/10 text-gold ring-1 ring-gold/30"
      : level === "indicative" ? "bg-sky-400/10 text-sky-300 ring-1 ring-sky-400/30"
        : "bg-white/5 text-ink-2 ring-1 ring-white/15";
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs ${cls}`}>
      {EVIDENCE_LABEL[level]}
    </span>
  );
}

export function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded bg-white/5 px-1.5 py-0.5 text-xs text-ink-2 ring-1 ring-white/10">
      {children}
    </span>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center gap-2 rounded-xl bg-rose-400/10 p-3 text-sm text-danger ring-1 ring-danger/30">
      <span aria-hidden>⚠️</span>
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="rounded-lg px-2 py-1 font-medium underline underline-offset-2">
          重试
        </button>
      )}
    </div>
  );
}

/** 三步横向步进器（移动端自动收窄；步骤间渐变连线） */
export function Stepper({ steps }: { steps: { title: string; done: boolean }[] }) {
  return (
    <ol className="mb-3 flex items-center gap-2 overflow-x-auto text-xs md:text-sm" aria-label="使用步骤">
      {steps.map((s, i) => (
        <li key={s.title} className="flex flex-none items-center gap-2 sm:flex-1 sm:last:flex-none">
          <span
            aria-current={s.done ? "step" : undefined}
            className={`flex h-6 w-6 flex-none items-center justify-center rounded-full text-xs font-bold ring-1 ${
              s.done ? "grad-bg text-white ring-transparent" : "bg-panel-2 text-ink-3 ring-white/15"
            }`}
          >
            {s.done ? "✓" : i + 1}
          </span>
          <span className={`whitespace-nowrap ${s.done ? "text-ink" : "text-ink-3"}`}>{s.title}</span>
          {i < steps.length - 1 && <span aria-hidden className="light-band mx-1 hidden flex-1 opacity-50 sm:block" />}
        </li>
      ))}
    </ol>
  );
}

/** 结果区 Tab（role=tablist + aria-selected + 键盘左右键） */
export function TabBar({ tabs, active, onChange, disabled = false }: {
  tabs: { key: string; label: string }[];
  active: string;
  onChange: (key: string) => void;
  disabled?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  return (
    <div
      role="tablist"
      aria-label="结果分区"
      aria-disabled={disabled}
      className="mb-4 flex gap-1 rounded-xl bg-panel p-1 ring-1 ring-white/10"
    >
      {tabs.map((t, i) => {
        const selected = t.key === active;
        return (
          <button
            key={t.key}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            aria-selected={selected}
            disabled={disabled}
            tabIndex={selected || disabled ? 0 : -1}
            onKeyDown={(e) => {
              if (disabled) return;
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
                const dir = e.key === "ArrowRight" ? 1 : -1;
                const next = (i + dir + tabs.length) % tabs.length;
                onChange(tabs[next].key);
                refs.current[next]?.focus();
              }
            }}
            onClick={() => !disabled && onChange(t.key)}
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              selected ? "grad-bg text-white shadow" : "text-ink-2 hover:bg-white/5 hover:text-ink"
            } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

/** Web Speech 语音播报（无障碍：失嗅/视障人群的听觉通道） */
export function SpeechButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;
  if (!supported) return null;
  return (
    <button
      onClick={() => {
        if (speaking) {
          window.speechSynthesis.cancel();
          setSpeaking(false);
          return;
        }
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "zh-CN";
        u.rate = 0.95;
        u.onend = () => setSpeaking(false);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
        setSpeaking(true);
      }}
      aria-label={speaking ? "停止播报" : "语音播报"}
      className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm text-ink ring-1 ring-white/20 hover:bg-white/5"
    >
      <span aria-hidden>{speaking ? "⏹" : "🔊"}</span>
      {speaking ? "停止" : "播报"}
    </button>
  );
}
