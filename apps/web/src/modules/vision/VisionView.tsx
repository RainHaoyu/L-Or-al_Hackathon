import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { VisionReport } from "../shared/api-types";
import { Card, SpeechButton, Tag } from "../shared/components";

const FAMILY_COLOR: Record<string, string> = {
  floral: "#E75480", woody: "#8B6F47", citrus: "#FFA500", oriental: "#8A2BE2",
  aquatic: "#00C2FF", gourmand: "#C68E17", fougere: "#7A8B5E",
};
const RADAR_DIMS: [string, string][] = [
  ["fresh", "清新度"], ["sweet", "甜度"], ["rich", "浓郁度"], ["warm", "温暖度"], ["lasting", "持久度"],
];
const PHASE_LABEL: Record<string, string> = { top: "前调", heart: "中调", base: "后调" };

export default function VisionView({ vision, productName }: { vision: VisionReport; productName: string }) {
  return (
    <div className="space-y-4">
      {vision.degraded && (
        <div role="status"
          className="rounded-2xl bg-panel px-4 py-3 text-sm text-warn ring-1 ring-warn/40">
          <p className="font-semibold">⚠️ 香味可视化降级</p>
          <p className="mt-1 text-ink-2">
            {vision.degrade_reason ?? "该产品缺少可用的香调构成信息，色彩/雷达/金字塔暂不可用。"}
          </p>
          <p className="mt-1 text-xs text-ink-3">
            左侧「预警报告」与「成分明细」不受影响，仍为完整结果。
          </p>
        </div>
      )}
      <PaletteBar vision={vision} />

      <div className="grid gap-4 md:grid-cols-2">
        <RadarChart vision={vision} />
        <Card title="香调金字塔（时序图层）">
          <div className="space-y-3">
            {Object.entries(vision.pyramid).map(([phase, notes]) => (
              <div key={phase}>
                <p className="text-xs font-medium text-ink-2">{PHASE_LABEL[phase] ?? phase}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {notes.map((n, i) => (
                    <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-panel-2 px-2.5 py-1 text-sm text-ink ring-1 ring-white/10">
                      <span aria-hidden className="h-2.5 w-2.5 rounded-full"
                        style={{ background: FAMILY_COLOR[n.family ?? "floral"] ?? "#E75480" }} />
                      {n.name}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <div className="flex flex-wrap gap-1.5 pt-1">
              <Tag>宽度=香调权重</Tag>
              <Tag>时序=前中后调图层</Tag>
              <Tag>强度=透明度/粒子数</Tag>
            </div>
          </div>
        </Card>
      </div>
      <ParticleCanvas vision={vision} />
      <SynesthesiaCard vision={vision} productName={productName} />
    </div>
  );
}

function PaletteBar({ vision }: { vision: VisionReport }) {
  const total = vision.families.reduce((s, f) => s + f.weight, 0) || 1;
  return (
    <Card title="色彩情绪板 · 气味→视觉映射">
      <div className="flex h-14 w-full overflow-hidden rounded-xl" role="img"
        aria-label={`香调构成：${vision.families.map((f) => `${f.name_zh} ${(f.weight / total * 100).toFixed(0)}%`).join("，")}`}>
        {vision.families.map((f) => (
          <div key={f.key} className="flex items-center justify-center text-xs font-medium text-white drop-shadow"
            style={{ width: `${(f.weight / total) * 100}%`, background: FAMILY_COLOR[f.key] ?? "#888" }}>
            {f.weight / total > 0.12 && `${f.name_zh} ${((f.weight / total) * 100).toFixed(0)}%`}
          </div>
        ))}
      </div>
      <div className="mt-3 h-8 rounded-lg"
        style={{ background: `linear-gradient(${vision.gradient_direction}deg, ${vision.palette.join(", ")})` }} />
      <p className="mt-2 text-sm text-ink-2">
        情绪画像：<strong className="text-gold">{vision.mood_label}</strong> · 动态图形：{vision.motion.label ?? vision.motion.type}
        （{vision.mode === "anosmic" ? "失嗅模式·嗅觉替代通道" : vision.mode === "sensitive" ? "敏感肌模式" : "普通模式"}）
      </p>
    </Card>
  );
}

function ParticleCanvas({ vision }: { vision: VisionReport }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const count = Math.min(vision.motion.particle_count ?? 60, 120);
    const speed = vision.motion.speed ?? 0.4;
    const colors = vision.palette.length ? vision.palette : ["#E8467C"];
    const parts = Array.from({ length: count }, () => ({
      x: Math.random(), y: Math.random(),
      vx: (Math.random() - 0.5) * speed * 0.001,
      vy: (Math.random() - 0.5) * speed * 0.001,
      r: 1.5 + Math.random() * 3,
      c: colors[Math.floor(Math.random() * colors.length)],
    }));
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of parts) {
        if (!reduced) {
          p.x += p.vx; p.y += p.vy;
          if (p.x < 0 || p.x > 1) p.vx *= -1;
          if (p.y < 0 || p.y > 1) p.vy *= -1;
        }
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.arc(p.x * canvas.width, p.y * canvas.height, p.r * dpr, 0, Math.PI * 2);
        ctx.fill();
      }
      if (!reduced) raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [vision]);
  return (
    <div className="glow-soft relative h-36 overflow-hidden rounded-2xl md:h-44">
      <canvas ref={ref} className="scent-canvas h-full" aria-hidden
        style={{ background: `linear-gradient(${vision.gradient_direction}deg, ${vision.palette.join(", ")})` }} />
      <p className="pointer-events-none absolute bottom-2 right-3 text-xs text-white/90 drop-shadow">
        {vision.motion.label ?? "香味粒子"} · {vision.motion.shape ?? ""}
      </p>
    </div>
  );
}

function RadarChart({ vision }: { vision: VisionReport }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = echarts.init(el);
    chart.setOption({
      backgroundColor: "transparent",
      radar: {
        indicator: RADAR_DIMS.map(([k, zh]) => ({ name: zh, max: 1 })),
        radius: "68%",
        axisName: { color: "#9ca3af", fontSize: 12 },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.14)" } },
        axisLine: { lineStyle: { color: "rgba(255,255,255,0.18)" } },
        splitArea: { areaStyle: { color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.05)"] } },
      },
      series: [{
        type: "radar",
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 1, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(232,70,124,0.45)" },
              { offset: 0.5, color: "rgba(138,43,226,0.38)" },
              { offset: 1, color: "rgba(0,194,255,0.35)" },
            ],
          },
        },
        lineStyle: { color: "#E8467C", width: 2 },
        itemStyle: { color: "#F5D76E", borderColor: "#E8467C", borderWidth: 1.5 },
        data: [{ value: RADAR_DIMS.map(([k]) => vision.radar[k] ?? 0), name: "五维香感" }],
      }],
    });
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
    };
  }, [vision]);
  return (
    <Card title="五维香感雷达">
      <div ref={ref} className="h-64 w-full md:h-72" role="img"
        aria-label={RADAR_DIMS.map(([k, zh]) => `${zh}${(vision.radar[k] ?? 0).toFixed(1)}`).join("，")} />
    </Card>
  );
}

function SynesthesiaCard({ vision, productName }: { vision: VisionReport; productName: string }) {
  return (
    <Card title="通感文字 · 把气味翻译成画面">
      <div className="flex items-start gap-3">
        <span aria-hidden className="grad-text mt-0.5 text-3xl font-serif leading-none">“</span>
        <p className="flex-1 text-[15px] leading-7 text-ink">{vision.synesthesia_text}</p>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <SpeechButton text={`${productName}。${vision.synesthesia_text}`} />
        <Tag>{vision.text_source === "qwen" ? "qwen-max 生成" : "规则模板生成（LLM 未接入时兜底）"}</Tag>
      </div>
    </Card>
  );
}
