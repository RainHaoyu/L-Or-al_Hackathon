import { Link, useNavigate } from 'react-router'
import { DEMO_CASES, FAMILIES } from '../lib/aura'
import { useApp } from '../lib/state'
import { AnalyzeFlow } from '../components/AnalyzeFlow'

/** 演示案例：一键设定人群+香水并直达结果页 */
function DemoCases() {
  const { setPopulation, setPerfumeId } = useApp()
  const navigate = useNavigate()
  return (
    <ul className="mt-8 divide-y divide-border">
      {DEMO_CASES.map((c) => (
        <li key={c.title}>
          <button
            onClick={() => {
              setPopulation(c.population)
              setPerfumeId(c.perfumeId)
              navigate(c.to)
            }}
            className="focus-visible-strong group flex min-h-14 w-full items-baseline justify-between gap-4 rounded-sm py-4 text-left"
          >
            <span className="text-lg">{c.title}</span>
            <span className="text-sm text-muted-foreground transition-colors group-hover:text-foreground">
              {c.desc}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

export default function Home() {
  return (
    <main className="relative mx-auto max-w-6xl px-4 pb-24 sm:px-6">
      {/* 柔光渐变背景层（十二香型色谱取色） */}
      <div aria-hidden className="aurora-bg pointer-events-none absolute inset-0 -z-10" />
      {/* —— 首屏 —— */}
      <section className="flex min-h-[62vh] flex-col justify-center py-16">
        <h1 className="font-display text-5xl leading-[1.12] tracking-wide sm:text-7xl">
          让看不见的香气，
          <br />
          被看见。
        </h1>
        <div aria-hidden className="spectrum-band mt-8 h-1.5 w-56 max-w-full animate-spectrum-draw" />
        <p className="mt-8 max-w-xl text-lg leading-relaxed text-muted-foreground">
          万象 Aura 读出每一瓶香水的两件事：它安不安全，以及它是什么颜色。
          为失嗅、敏感肌、孕期与鼻炎人群而作。
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <a
            href="#analyze"
            className="focus-visible-strong inline-flex min-h-12 items-center rounded-full bg-ink px-7 text-base font-medium text-paper transition-transform hover:scale-[1.03]"
          >
            开始分析
          </a>
          <Link
            to="/vision"
            className="focus-visible-strong inline-flex min-h-12 items-center rounded-full border border-border px-6 text-base hover:bg-secondary"
          >
            先看香气显影
          </Link>
        </div>
      </section>

      {/* —— 介绍：为什么做万象 Aura（内容取自汇报 PPT 初稿） —— */}
      <section aria-labelledby="why" className="border-t border-border py-14">
        <h2 id="why" className="font-display max-w-2xl text-3xl leading-snug">
          香水是「美」的载体，却天然排斥四类人
        </h2>
        <p className="mt-5 max-w-2xl leading-relaxed text-muted-foreground">
          失嗅者闻不到，敏感肌不敢用，孕妇需要规避，鼻炎患者易受刺激。技术向善，
          是把被排除在「体验美」之外的人，重新纳入进来。
        </p>

        <div className="mt-10 grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="font-display text-4xl">
              15.3<span className="text-2xl">%</span>
            </p>
            <p className="mt-1 text-sm">中国成人嗅觉障碍患病率</p>
            <p className="mt-0.5 text-xs text-muted-foreground">T&amp;T 嗅觉计实测 12,153 人</p>
          </div>
          <div>
            <p className="font-display text-4xl">
              36.1<span className="text-2xl">%</span>
            </p>
            <p className="mt-1 text-sm">中国女性敏感性皮肤发生率</p>
            <p className="mt-0.5 text-xs text-muted-foreground">敏感性皮肤诊疗指南 2024 版</p>
          </div>
          <div>
            <p className="font-display text-4xl">
              2.5<span className="text-2xl">亿</span>
            </p>
            <p className="mt-1 text-sm">中国过敏性鼻炎患者总数</p>
            <p className="mt-0.5 text-xs text-muted-foreground">患病率 11.1% 升至 17.6%</p>
          </div>
          <div>
            <p className="font-display text-4xl">
              80<span className="text-2xl">+种</span>
            </p>
            <p className="mt-1 text-sm">欧盟新规需单独标注的致敏原</p>
            <p className="mt-0.5 text-xs text-muted-foreground">EU 2023/1545，由 24 种扩容</p>
          </div>
        </div>

        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          <div>
            <p className="text-sm text-muted-foreground">痛点一 · 信息壁垒</p>
            <p className="mt-2 leading-relaxed">
              香水成分表是一部「天书」：晦涩的 INCI 名称、复杂的香调金字塔，
              普通人无从判断一瓶香水是否适合自己。
            </p>
            <p className="mt-2 leading-relaxed">
              <span className="font-medium text-gold-deep">解法</span>
              <span className="text-muted-foreground">　把化学名词翻译成红黄绿灯与人群差异化指引，风险可读、可理解。</span>
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">痛点二 · 感官缺失</p>
            <p className="mt-2 leading-relaxed">
              香水氧化变质时，正常人能从「变味」察觉异常，失嗅者却完全依赖他人提醒。
            </p>
            <p className="mt-2 leading-relaxed">
              <span className="font-medium text-gold-deep">解法</span>
              <span className="text-muted-foreground">　建立嗅觉替代通道：用色彩、图形、文字与语音，把气味翻译成看得见的画面。</span>
            </p>
          </div>
        </div>

        <blockquote className="mt-12 border-l-2 border-gold pl-6">
          <p className="font-display text-2xl leading-relaxed">
            拍下一瓶香水，选择「我是谁」——万象 Aura 告诉你：这瓶香水对你安不安全，以及它「长什么样」。
          </p>
          <cite className="mt-2 block text-sm not-italic text-muted-foreground">
            感知无界 · 人群无界 · 场景无界
          </cite>
        </blockquote>
      </section>

      {/* —— 三步引导流（可交互） —— */}
      <AnalyzeFlow />

      {/* —— 演示样本入口（路演保险绳） —— */}
      <section aria-labelledby="demo" className="border-t border-border py-14">
        <h2 id="demo" className="font-display text-3xl">
          或直接打开一份演示结果
        </h2>
        <DemoCases />
      </section>

      {/* —— 十二香型色谱注脚（参考《香型HEX色值及对应画面效果》） —— */}
      <section aria-label="十二香型色谱" className="border-t border-border py-10">
        <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
          {FAMILIES.map((f) => (
            <li key={f.key} className="inline-flex items-center gap-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: f.main }}
              />
              {f.name}
            </li>
          ))}
        </ul>
        <p className="mt-10 text-center text-sm text-muted-foreground">
          万象 Aura · 2026 欧莱雅美妆科技黑客松 · 赛道三 无界体验家
        </p>
      </section>
    </main>
  )
}
