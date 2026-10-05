@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 万象 Aura - 后端(可选)
cd /d %~dp0aura\api
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo [跳过] 未检测到 Python，前端将以本地引擎独立运行（功能完整，只是不走后端计算）& pause & exit /b 0)
if not exist .venv (
  echo 首次运行：创建虚拟环境并安装 FastAPI（约 1 分钟）...
  %PY% -m venv .venv || (echo venv 创建失败 & pause & exit /b 1)
  call .venv\Scripts\pip install -q fastapi "uvicorn[standard]" httpx pytest || (echo 依赖安装失败 & pause & exit /b 1)
)
echo 后端启动 http://localhost:8001/api/v1/health （关闭本窗口即停止）
call .venv\Scripts\uvicorn app.main:app --port 8001
pause
