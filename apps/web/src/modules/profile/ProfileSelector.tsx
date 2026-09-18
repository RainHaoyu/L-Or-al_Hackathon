import type { PopulationKey } from "../shared/api-types";

export const POPULATIONS: {
  key: PopulationKey; label: string; icon: string; desc: string;
}[] = [
  { key: "healthy", label: "健康成人", icon: "🙂", desc: "基线 · P90" },
  { key: "sensitive", label: "敏感肌", icon: "🌱", desc: "阈值×3 · P99" },
  { key: "pregnant", label: "孕期", icon: "🤰", desc: "禁用检查 · P99" },
  { key: "rhinitis", label: "过敏性鼻炎", icon: "🌬️", desc: "呼吸道 · P99" },
  { key: "anosmic", label: "失嗅人群", icon: "🫧", desc: "嗅觉替代 · P99" },
];

export default function ProfileSelector({ value, onChange }: {
  value: PopulationKey; onChange: (p: PopulationKey) => void;
}) {
  return (
    <div role="radiogroup" aria-label="选择你的用户画像"
      className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-5">
      {POPULATIONS.map((p) => (
        <button
          key={p.key}
          role="radio"
          aria-checked={value === p.key}
          onClick={() => onChange(p.key)}
          className={`rounded-xl px-3 py-2.5 text-left transition-all ${
            value === p.key
              ? "grad-ring glow"
              : "bg-panel-2 ring-1 ring-white/10 hover:ring-white/25"
          }`}
        >
          <span aria-hidden className="block text-xl">{p.icon}</span>
          <span className={`mt-1 block whitespace-nowrap text-[13px] font-semibold ${value === p.key ? "text-ink" : "text-ink-2"}`}>
            {p.label}
          </span>
          <span className="block whitespace-nowrap text-[11px] text-ink-3">{p.desc}</span>
        </button>
      ))}
    </div>
  );
}
