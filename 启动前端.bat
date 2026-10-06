@echo off
rem ============================================================
rem  Wanxiang Aura - frontend (Windows)
rem  NOTE: keep ASCII-only. cmd.exe mis-decodes UTF-8 Chinese
rem  under the system OEM codepage (GBK on zh-CN).
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Frontend
rem Repo root IS the package root: web/ and api/ sit next to this file
cd /d %~dp0web
if errorlevel 1 (echo [ERROR] cannot cd into web\ & pause & exit /b 1)
where node >nul 2>nul || (echo [ERROR] Node.js not found. Install LTS: https://nodejs.org/zh-cn & pause & exit /b 1)
for /f "tokens=* usebackq" %%v in (`node -v`) do set NODEV=%%v
echo [1/3] Node !NODEV! OK
if not exist node_modules (
  echo [2/3] First run: installing dependencies ^(2-5 min^)...
  echo       If slow, use a mirror: npm config set registry https://registry.npmmirror.com
  call npm install --no-audit --no-fund || (echo [ERROR] npm install failed & pause & exit /b 1)
) else (
  echo [2/3] Dependencies ready
)
rem Port must match web/vite.config.ts server.port (3000)
echo [3/3] Dev server: http://localhost:3000  ^(close this window to stop^)
start "" http://localhost:3000
call npm run dev -- --port 3000 --strictPort
pause
