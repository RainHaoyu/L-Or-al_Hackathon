@echo off
rem ============================================================
rem  Wanxiang Aura - frontend dev server (Windows)
rem
rem  WHY THIS FILE IS ASCII-ONLY
rem  cmd.exe decodes .bat bytes with the system OEM codepage
rem  (GBK on zh-CN). Non-ASCII text in a .bat is therefore
rem  mis-decoded, and a mis-decoded quote can swallow a whole
rem  line -- the classic "why is my script broken" failure.
rem  So the Chinese-named files at the repo root are thin
rem  wrappers that CALL this file; this file never has to spell
rem  a Chinese filename, and its own bytes stay 7-bit.
rem
rem  Invoked by: the Chinese-named frontend wrapper at the
rem              repo root, and the one-click launcher.
rem  Invariant : the port here must equal web\vite.config.ts
rem              server.port (3000). Guarded by
rem              web\src\lib\launchers.test.ts.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Frontend

rem Repo root is one level up: this file lives in <repo>\scripts\
cd /d "%~dp0.." || (echo [ERROR] cannot cd to repo root & pause & exit /b 1)

where node >nul 2>nul || (echo [ERROR] Node.js not found. Install LTS: https://nodejs.org/zh-cn & pause & exit /b 1)
for /f "tokens=* usebackq" %%v in (`node -v`) do set NODEV=%%v
echo [1/3] Node !NODEV! OK

cd web
if not exist node_modules (
  echo [2/3] First run: installing dependencies ^(2-5 min^)...
  echo       If slow, use a mirror: npm config set registry https://registry.npmmirror.com
  call npm install --no-audit --no-fund || (echo [ERROR] npm install failed & pause & exit /b 1)
) else (
  echo [2/3] Dependencies ready
)

echo [3/3] Dev server: http://localhost:3000  ^(close this window to stop^)
start "" http://localhost:3000
call npm run dev -- --port 3000 --strictPort
pause
