#!/usr/bin/env bash
# 万象 Aura 一键启动（macOS / Linux）
cd "$(dirname "$0")"
command -v python3 >/dev/null && (cd aura/api && { [ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q fastapi 'uvicorn[standard]' httpx pytest; }; (.venv/bin/uvicorn app.main:app --port 8001 >/tmp/aura-api.log 2>&1 &) && echo "后端 http://localhost:8001"; }) || echo "无 Python：前端以本地引擎独立运行"
cd aura/web
command -v npm >/dev/null || { echo "缺 Node.js：https://nodejs.org"; exit 1; }
[ -d node_modules ] || npm install --no-audit --no-fund
(sleep 2 && (open http://localhost:5199 2>/dev/null || xdg-open http://localhost:5199 2>/dev/null) &)
npm run dev -- --port 5199 --strictPort --host
