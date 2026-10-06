#!/usr/bin/env bash
# 万象 Aura 一键启动（macOS 双击运行）
# 仓库根即包根：web/ 与 api/ 于本文件同级
set -u
cd "$(dirname "$0")"

echo "============================================"
echo "  万象 Aura 一键启动"
echo "============================================"
echo " 前端：http://localhost:3000   （可独立运行，不依赖后端）"
echo " 后端：http://localhost:8001   （可选；提供真实 AI 识别与通感文案）"
echo

if command -v python3 >/dev/null 2>&1; then
  (
    cd api || exit 0
    if [ ! -d .venv ]; then
      echo "[后端] 首次运行：创建虚拟环境并安装依赖（约 1-2 分钟）..."
      python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
    fi
    if [ -n "${DASHSCOPE_API_KEY:-}" ]; then
      echo "[AI] 已检测到 DASHSCOPE_API_KEY：识别走 qwen-vl-max、文案走 qwen-max"
    else
      echo "[AI] 未设置 DASHSCOPE_API_KEY：识别走 mock、文案走规则模板"
      echo "     如需真实 AI：export DASHSCOPE_API_KEY=你的百炼Key 后重跑本脚本"
    fi
    .venv/bin/uvicorn app.main:app --port 8001 >/tmp/aura-api.log 2>&1 &
    echo "[后端] 已启动 http://localhost:8001 （日志 /tmp/aura-api.log）"
  )
else
  echo "[后端] 未检测到 python3：只启动前端，本地引擎功能完整（不走后端 AI）"
fi

cd web || { echo "[错误] 未找到 web/ 目录"; exit 1; }
if ! command -v npm >/dev/null 2>&1; then
  echo "[缺依赖] 未检测到 Node.js，请先安装 LTS 版：https://nodejs.org"
  exit 1
fi
[ -d node_modules ] || npm install --no-audit --no-fund

(sleep 2 && { open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null; } &)
npm run dev -- --port 3000 --strictPort
