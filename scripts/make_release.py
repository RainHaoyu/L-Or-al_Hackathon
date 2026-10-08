#!/usr/bin/env python3
"""打交付包：源码 + 预构建前端 + 数据层 + 使用说明，一个 zip 直接发出去。

用法：
    python scripts/make_release.py                 # 产出到仓库根目录
    python scripts/make_release.py --out D:\\分享    # 指定输出目录

交付包内容（开包即用，**只需 Python**）：
    <包名>/
      一键启动.bat          ← 交付形态入口：装依赖 + 单进程同时提供页面与 API（0.0.0.0:8001）
      使用说明.md            ← 面向使用者的说明（手机访问、配 Key、自检、目录结构）
      api/                  ← FastAPI（含 .env.example 空模板；**不含 .env**）
      web/                  ← 前端源码 + dist 预构建（同源构建，无需 Node）
      scripts/ docs/ ...     ← 源码与文档
      数据层/                ← 上游 9 份原始数据（重跑数据管线才需要）
      api/vendor/            ←（可选）离线 wheel，无网机器也能装依赖

脚本内置硬校验：包内出现 .env / .venv / node_modules / __pycache__ / *.zip 或
任何 `sk-…` 形态的密钥，直接报错中止——避免再出"把 Key 打进交付包"的事故。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATE = dt.date.today().strftime("%Y%m%d")
PKG_NAME = f"万象Aura-交付包-{DATE}"

# 排除清单（交付包不需要、或不该带的东西）
EXCLUDE_PREFIX = (
    "legacy/",            # 旧实现归档（约 9 MB，含 zip），交付不需要
    "web/node_modules/",
    "web/dist/.vite/",
)
EXCLUDE_NAME = {".env", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".DS_Store"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".zip", ".tsbuildinfo", ".log"}
# 密钥判定：只看长度 ≥40 且同时含大写字母与数字的 `sk-...` 串。
# 这样既不会漏掉真实 Key（形如 sk-ws-H.PRYRXER.oESf…，含大写与数字），
# 也不会误伤压缩产物里的 CSS 类名（如 mask-image-linear-gradient，全小写）。
SECRET_RE = re.compile(r"sk-[A-Za-z0-9._\-]{24,}")


def looks_like_secret(text: str) -> str | None:
    for m in SECRET_RE.finditer(text):
        cand = m.group(0)
        if len(cand) >= 40 and re.search(r"[A-Z]", cand) and re.search(r"\d", cand):
            return cand[:12] + "…"       # 只回报前缀，绝不打印完整值
    return None


USAGE = r"""# 万象 Aura · 交付包使用说明

> 双核心：**致敏预警（QRA2 四闸门 + 蒙特卡洛分位）+ 香味可视化（组成驱动显影）**
> 一个进程同时提供页面与接口：**只需要 Python，不需要 Node**。

---

## 一、跑起来（Windows，30 秒）

1. 装 **Python 3.9 或更高**（安装时勾选 **Add python.exe to PATH**）。
2. 解压本包，**双击 `一键启动.bat`**：
   - 首次运行自动建虚拟环境并装依赖（优先用包内 `api/vendor` 离线 wheel，未命中则联网）；
   - 完成后打开 **http://localhost:8001**（页面与接口同端口，没有跨域问题）；
   - **关闭命令行窗口即停止服务**。
3. 再次启动是秒级（依赖只装一次）。

macOS / Linux：`cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001`

## 二、手机访问（同一个 Wi-Fi）

`一键启动.bat` 启动后会打印两行地址：

```
This PC     : http://localhost:8001
Phone (same Wi-Fi): http://<这台电脑的内网IP>:8001
```

手机连同一个 Wi-Fi，用浏览器打开第二行即可（判定、分位谱、香气显影、朗读都能用）。

**打不开时基本都是 Windows 防火墙**（入站 8001 默认被拦；Wi-Fi 为"公用"网络时更严）。
用**管理员**身份跑一次：

```
netsh advfirewall firewall add rule name="WanxiangAura-8001" dir=in action=allow protocol=TCP localport=8001
```

也可以把该 Wi-Fi 的网络配置文件改成「专用」，然后在弹窗里允许 Python。

## 三、AI 文案与拍照识别（可选，不配也能完整演示）

三级兜底：**qwen-max → qwen-plus → 规则模板**；识别：**qwen-vl-max → mock**。
不配 Key 时功能完整、不会报错，页面会**如实标注**文案来源（"后端 AI" 还是 "本地规则模板"）。

配 Key 两种方式（任选其一，**别写进任何要提交或外发的文件**）：

```bat
rem 方式 A：当前窗口临时生效
set DASHSCOPE_API_KEY=你的百炼Key
一键启动.bat
```
```bat
rem 方式 B：写进 api\.env（该文件已在 .gitignore 里，勿随包外发）
copy api\.env.example api\.env
notepad api\.env
```

配好后重启服务；页面上"文案由 qwen-max 生成（后端 AI）"即表示生效。

## 四、自检

```bat
cd api
.venv\Scripts\python.exe -m pytest tests/ -q      rem 后端 199 条，约 3-8 分钟
cd ..\web
npm run test                                      rem 前端 105 条，约 10 秒（需要 Node）
```

只想快速确认服务健康：

```
http://localhost:8001/api/v1/health
```

## 五、目录结构

```
一键启动.bat / 启动后端.bat / 数据重生成.bat / 启动前端.bat   Windows 入口
使用说明.md（本文件）
数据层/                     上游 9 份原始数据（重跑数据管线才需要）
api/                        FastAPI：QRA2 引擎 / 识别层 / LLM 编排 / 静态托管
  app/  tests/  requirements.txt  vendor/（离线 wheel）  .env.example
web/                        前端源码
  dist/                     预构建页面（同源构建，可直接由 api 托管）
  src/data/                 前后端共享的数据层 JSON
  scripts/build_data.py     数据管线：数据层/ → src/data/*.json
docs/                       进度台账、待办清单、设计口径
```

## 六、已知边界

- 报告页每次生成由引擎实算（单次 analyze 含蒙特卡洛，约 4-5 秒）；相同输入重复生成会更快。
- 未配 Key 时：文案为规则模板、拍照识别走 mock（置信度 0.62 会转人工确认）。
- 数据只覆盖 12 款真实香水与 IFRA Cat4 三表 + 158 条 CAS 词典；
  未命中的成分按「数据不足」显式黄灯处理，**不静默放行**。
- 风险结论不构成医学建议；成分与法规限量请以官方最新标准为准。
"""


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True)
    return [p for p in out.stdout.decode("utf-8").split("\0") if p]


def data_layer() -> Path | None:
    for cand in (REPO.parent / "数据层", REPO / "数据层"):
        if cand.is_dir() and (cand / "12款经典香水分析.docx").exists():
            return cand
    return None


def want(rel: str) -> bool:
    if any(rel.startswith(p) for p in EXCLUDE_PREFIX):
        return False
    parts = Path(rel).parts
    if any(p in EXCLUDE_NAME for p in parts):
        return False
    if Path(rel).name == ".env":            # 只允许 .env.example
        return False
    if Path(rel).suffix.lower() in EXCLUDE_SUFFIX:
        return Path(rel).suffix.lower() == ".whl" and "vendor" in parts  # 只放行 vendor 里的 wheel
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO), help="输出目录（默认仓库根目录）")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    dist = REPO / "web" / "dist"
    if not (dist / "index.html").is_file():
        sys.exit("ERROR: web/dist 不存在。先构建同源页面：cd web && npm install && npm run build")

    members: dict[str, Path] = {}
    for rel in tracked_files():
        if want(rel) and (REPO / rel).is_file():
            members[rel] = REPO / rel
    # 离线 wheel 不入库（见 .gitignore），但要在交付包里，无网机器也能装依赖
    vendor = REPO / "api" / "vendor"
    if vendor.is_dir():
        for p in sorted(vendor.glob("*.whl")):
            members[f"api/vendor/{p.name}"] = p
    for p in sorted(dist.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(REPO)).replace("\\", "/")
            if want(rel):
                members[rel] = p
    dl = data_layer()
    if dl:
        prefix = "数据层" if dl.parent != REPO else str(dl.relative_to(REPO))
        for p in sorted(dl.rglob("*")):
            if p.is_file() and not p.name.startswith("~$"):
                members[f"{prefix}/{p.relative_to(dl)}".replace("\\", "/")] = p
    else:
        print("WARN: 未找到 数据层/，交付包将不含上游数据（数据管线需要它）")

    # 交付形态入口：一键启动 = 单进程同时提供页面与 API（不改仓库里开发用的同名文件）
    members["一键启动.bat"] = None  # 占位，稍后写入生成的字节

    # ---- 硬校验：不允许把密钥/依赖/缓存打进包 ----
    problems: list[str] = []
    for rel, path in list(members.items()):
        parts = Path(rel).parts
        if any(p in EXCLUDE_NAME for p in parts) or Path(rel).name == ".env":
            problems.append(f"不该打包: {rel}")
        if Path(rel).suffix.lower() == ".zip":
            problems.append(f"不该打包 zip: {rel}")
        if path and path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".txt", ".bat", ".cmd", ".sh"}:
            try:
                text = path.read_text("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            bad = looks_like_secret(text)
            if bad:
                problems.append(f"疑似密钥 {bad} 出现在: {rel}")
            if Path(rel).name == ".env.example":
                for line in text.splitlines():
                    if line.strip().startswith("DASHSCOPE_API_KEY=") and line.split("=", 1)[1].strip():
                        problems.append(f"{rel} 里 Key 模板被填了值，必须留空")
    if problems:
        sys.exit("ERROR: 交付包校验失败，已中止：\n  - " + "\n  - ".join(problems))

    launcher = (
        "@echo off\r\n"
        "rem Thin entry point for this delivery package (ASCII-only content).\r\n"
        "rem One process serves both the page and the API on port 8001, bound to 0.0.0.0\r\n"
        "rem so a phone on the same Wi-Fi can use it. First run installs dependencies\r\n"
        "rem (offline wheels in api\\vendor first, then online), later runs are seconds.\r\n"
        "call \"%~dp0scripts\\start-backend.bat\" %*\r\n"
    )

    target = out_dir / f"{PKG_NAME}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, path in sorted(members.items()):
            if path is None:
                z.writestr(f"{PKG_NAME}/{rel}", launcher.encode("utf-8"))
            else:
                z.write(path, f"{PKG_NAME}/{rel}")
        z.writestr(f"{PKG_NAME}/使用说明.md", USAGE.encode("utf-8"))

    size = target.stat().st_size
    print(f"OK  {target}")
    print(f"    {len(members) + 1} 个文件，{size / 1024 / 1024:.2f} MB")
    print(f"    含 dist: {'是' if any(k.startswith('web/dist/') for k in members) else '否'}"
          f"｜含数据层: {'是' if dl else '否'}"
          f"｜含离线 wheel: {sum(1 for k in members if k.endswith('.whl'))} 个"
          f"｜含 .env: 否（硬校验保证）")


if __name__ == "__main__":
    main()
