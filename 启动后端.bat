@echo off
rem ============================================================
rem  Wanxiang Aura - backend (optional, Windows)
rem  NOTE: keep ASCII-only. cmd.exe mis-decodes UTF-8 Chinese
rem  under the system OEM codepage (GBK on zh-CN).
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Backend
rem Repo root IS the package root: web/ and api/ sit next to this file
cd /d %~dp0api
if errorlevel 1 (echo [ERROR] cannot cd into api\ & pause & exit /b 1)
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo [SKIP] Python not found: frontend runs standalone with local engine & pause & exit /b 0)
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
