@echo off
rem ============================================================
rem  Wanxiang Aura - backend API (Windows, OPTIONAL)
rem
rem  The frontend runs standalone: it has its own TypeScript
rem  QRA2 engine, so skipping the backend only costs real AI
rem  recognition and AI-written text.
rem
rem  WHY THIS FILE IS ASCII-ONLY
rem  cmd.exe decodes .bat bytes with the system OEM codepage
rem  (GBK on zh-CN); non-ASCII bytes can be mis-decoded and
rem  swallow a line. The Chinese-named root files are thin
rem  wrappers that CALL this file.
rem
rem  Invoked by: the Chinese-named backend wrapper at the
rem              repo root, and the one-click launcher.
rem  Invariant : the port here must stay in sync with
rem              web\src\lib\api.ts (8001). Guarded by
rem              web\src\lib\launchers.test.ts.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Backend

rem Repo root is one level up: this file lives in <repo>\scripts\
cd /d "%~dp0.." || (echo [ERROR] cannot cd to repo root & pause & exit /b 1)

set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo [SKIP] Python not found: frontend runs standalone with its local engine & pause & exit /b 0)

cd api
if not exist .venv (
  echo First run: creating venv and installing deps ^(1-2 min^)...
  %PY% -m venv .venv || (echo [ERROR] venv creation failed & pause & exit /b 1)
  call .venv\Scripts\pip install -q -r requirements.txt || (echo [ERROR] pip install failed & pause & exit /b 1)
)

echo.
if defined DASHSCOPE_API_KEY (
  echo [AI] DASHSCOPE_API_KEY detected: recognition uses qwen-vl-max, text uses qwen-max
  echo      Note: /analyze with AI text takes about 9-11 seconds.
) else (
  echo [AI] DASHSCOPE_API_KEY not set: recognition falls back to mock, text to rule template.
  echo      For real AI, run this first in the same window:
  echo        set DASHSCOPE_API_KEY=your-bailian-key
  echo      then re-run this script.
)
echo.
echo Backend: http://localhost:8001/api/v1/health  ^(close this window to stop^)
call .venv\Scripts\uvicorn app.main:app --port 8001
pause
