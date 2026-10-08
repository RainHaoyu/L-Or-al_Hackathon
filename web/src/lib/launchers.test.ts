/**
 * 启动脚本守卫（Windows .bat）
 *
 * 由来：一键启动曾经整片失效，是三个原因叠加——
 *   1. .bat 被写成裸 LF（cmd.exe 按 CRLF 切行，读错位后每行都截断，
 *      表现为闪退或刷一屏 `'xxx' is not recognized as an internal ...`）；
 *   2. 仓库扁平化后脚本里的路径还是旧的 aura\web / aura\api；
 *   3. 前端端口写的 5199，与 web/vite.config.ts 的 3000 不一致。
 * 这三类问题在 Windows 上都很难当场看出原因，所以在这里变成会失败的测试。
 *
 * 另一个硬约束：**.bat 内容必须 ASCII-only**。cmd.exe 按系统 OEM 代码页
 * （中文系统为 GBK）解码脚本字节，脚本里的 UTF-8 中文会被误解码，甚至
 * 因为引号错位吞掉整行。因此根目录的中文名脚本只是「薄壳」，真正的逻辑
 * 全在 scripts\ 下的 ASCII 名文件里，薄壳只按 ASCII 路径去 call 它们。
 * （文件名本身是中文没有问题：文件名是 UTF-16，不经过代码页。）
 */
import { existsSync, readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.resolve(HERE, "..", "..", "..") // web/src/lib -> 仓库根
const SCRIPTS = path.join(REPO, "scripts")

/** 根目录中文名薄壳 → scripts\ 下 ASCII 名核心 */
const WRAPPERS: Record<string, string> = {
  "启动前端.bat": "start-frontend.bat",
  "启动后端.bat": "start-backend.bat",
  "数据重生成.bat": "regenerate-data.bat",
}

const allBatFiles = (): { rel: string; abs: string }[] => [
  ...readdirSync(REPO)
    .filter((f) => f.toLowerCase().endsWith(".bat"))
    .map((f) => ({ rel: f, abs: path.join(REPO, f) })),
  ...readdirSync(SCRIPTS)
    .filter((f) => f.toLowerCase().endsWith(".bat"))
    .map((f) => ({ rel: `scripts/${f}`, abs: path.join(SCRIPTS, f) })),
]

const text = (p: string) => readFileSync(p, "utf8")

describe("Windows 启动脚本", () => {
  it("每个 .bat 都有文件可查（防止薄壳/核心被误删）", () => {
    const rels = allBatFiles().map((f) => f.rel)
    expect(rels).toContain("一键启动.bat")
    for (const [wrapper, core] of Object.entries(WRAPPERS)) {
      expect(rels).toContain(wrapper)
      expect(rels).toContain(`scripts/${core}`)
    }
  })

  it("每个 .bat 都是 CRLF，且不含裸 LF", () => {
    const bad: string[] = []
    for (const { rel, abs } of allBatFiles()) {
      const buf = readFileSync(abs)
      let bareLf = 0
      for (let i = 0; i < buf.length; i++) {
        if (buf[i] === 0x0a && (i === 0 || buf[i - 1] !== 0x0d)) bareLf++
      }
      if (bareLf > 0) bad.push(`${rel}: ${bareLf} 个裸 LF`)
      // 顺带兜住「整个文件没有换行」的极端情况
      if (!buf.includes(0x0d)) bad.push(`${rel}: 完全没有 CR`)
    }
    expect(bad).toEqual([])
  })

  it("每个 .bat 内容都是 ASCII-only（cmd.exe 按 OEM 代码页解码）", () => {
    const bad: string[] = []
    for (const { rel, abs } of allBatFiles()) {
      const buf = readFileSync(abs)
      const i = buf.findIndex((b) => b > 0x7f)
      if (i >= 0) {
        const line = buf.subarray(0, i).toString("latin1").split("\n").length
        bad.push(`${rel}: 第 ${line} 行附近有非 ASCII 字节（0x${buf[i].toString(16)}）`)
      }
    }
    expect(
      bad,
      "中文名脚本只能做薄壳：逻辑写进 scripts\\*.bat，薄壳用 ASCII 路径 call 它",
    ).toEqual([])
  })

  it("中文名薄壳只 call 对应的 ASCII 核心，自己不重复逻辑", () => {
    for (const [wrapper, core] of Object.entries(WRAPPERS)) {
      const src = text(path.join(REPO, wrapper))
      expect(src, wrapper).toContain(`scripts\\${core}`)
      expect(src, wrapper).toMatch(/^call /m)
      // 薄壳应当只有注释 + 一行 call：出现 npm/uvicorn/python 说明逻辑漏到了薄壳里
      expect(src, wrapper).not.toMatch(/npm |uvicorn|python|node /)
    }
  })

  it("一键启动.bat 直接调用两个 ASCII 核心（不靠中文文件名匹配）", () => {
    const src = text(path.join(REPO, "一键启动.bat"))
    expect(src).toContain("scripts\\start-frontend.bat")
    expect(src).toContain("scripts\\start-backend.bat")
    // cmd.exe 的两个坑：?? 通配符在 call 里无效；*端.bat 会同时匹配前后端
    const cmdLines = src
      .split(/\r?\n/)
      .filter((l) => /^\s*(call|start)\b/i.test(l))
    expect(cmdLines.length, "至少要有一条 call/start").toBeGreaterThan(0)
    for (const l of cmdLines) {
      expect(l, `不能用通配符/子串去认中文文件名：${l}`).not.toMatch(/[*?]/)
    }
  })

  it("前端端口在脚本与 vite.config.ts 之间一致", () => {
    const vite = text(path.join(REPO, "web", "vite.config.ts"))
    const port = /server:\s*\{[^}]*?port:\s*(\d+)/.exec(vite)?.[1]
    expect(port, "vite.config.ts 里应能解析出 server.port").toBeDefined()

    for (const { rel, abs } of allBatFiles()) {
      const src = text(abs)
      if (/npm run dev/.test(src)) {
        expect(src, `${rel} 必须显式钉住端口且 strictPort`).toContain(
          `--port ${port} --strictPort`,
        )
      }
    }
  })

  it("后端端口在脚本与 web/src/lib/api.ts 之间一致", () => {
    const api = text(path.join(REPO, "web", "src", "lib", "api.ts"))
    const port = /localhost:(\d+)/.exec(api)?.[1]
    expect(port, "api.ts 里应能解析出后端端口").toBeDefined()

    const backend = text(path.join(SCRIPTS, "start-backend.bat"))
    expect(backend).toContain(`--port ${port}`)
  })

  it("交付/手机形态：同源 API 前缀 + 监听所有网卡", () => {
    const env = text(path.join(REPO, "web", ".env.production"))
    const value = /^VITE_API_BASE=(.*)$/m.exec(env)?.[1]?.trim()
    expect(value, ".env.production 必须显式设置 VITE_API_BASE").toBeDefined()
    expect(
      value,
      "必须是带 /api/v1 前缀的相对路径：写死 localhost 会让手机上的请求指向手机自己；留空会丢掉 /api/v1 前缀",
    ).toBe("/api/v1")

    const backend = text(path.join(SCRIPTS, "start-backend.bat"))
    expect(backend, "手机要能访问就必须监听 0.0.0.0（只绑 127.0.0.1 时手机连不上）").toContain(
      "--host 0.0.0.0",
    )
  })

  it("构建产物里不得残留 localhost:8001（有 dist 时才检查）", () => {
    const assets = path.join(REPO, "web", "dist", "assets")
    if (!existsSync(assets)) return // 未构建（CI 常见）时跳过
    for (const f of readdirSync(assets).filter((n) => n.endsWith(".js"))) {
      const js = readFileSync(path.join(assets, f), "utf8")
      expect(js, `${f} 里出现了 localhost:8001：手机打开时 API 会指向手机自己`).not.toContain(
        "localhost:8001",
      )
    }
  })
})
