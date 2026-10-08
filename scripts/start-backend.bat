@echo off
rem ============================================================
rem  Wanxiang Aura - backend + prebuilt frontend (Windows)
rem
rem  This single process serves BOTH the API and the built page
rem  (web\dist), on one port and one origin. That is the delivery
rem  form: no Node needed, and a phone on the same Wi-Fi can open
rem  http://<this-PC-LAN-IP>:8001 and use the whole app.
rem
rem  WHY THIS FILE IS ASCII-ONLY
rem  cmd.exe decodes .bat bytes with the system OEM codepage
rem  (GBK on zh-CN); non-ASCII bytes can be mis-decoded and
rem  swallow a line. The Chinese-named root files are thin
rem  wrappers that CALL this file.
rem
rem  Invoked by: the Chinese-named backend wrapper at the repo
rem              root, and the one-click launcher.
rem  Invariant : the port here must stay in sync with
rem              web\src\lib\api.ts (8001), and the deliverable
rem              build must use a same-origin API base
rem              (web\.env.production). Both are guarded by
rem              web\src\lib\launchers.test.ts.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Backend + Page

rem Repo root is one level up: this file lives in <repo>\scripts\
cd /d "%~dp0.." || (echo [ERROR] cannot cd to repo root & pause & exit /b 1)

set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo [SKIP] Python not found: the frontend can still run on its own ^(see web\README.md^) & pause & exit /b 0)

if not exist "web\dist\index.html" (
  echo [WARN] web\dist is missing: this process will serve the API only.
  echo        Build it once with:  cd web  ^&^&  npm install  ^&^&  npm run build
  echo.
)

cd api
if not exist .venv (
  echo First run: creating venv and installing deps ^(1-2 min^)...
  %PY% -m venv .venv || (echo [ERROR] venv creation failed & pause & exit /b 1)
  call .venv\Scripts\pip install -q -r requirements.txt || (echo [ERROR] pip install failed & pause & exit /b 1)
)

rem LAN address for phones. "IPv4" stays ASCII even on a localized Windows.
set LANIP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do if not defined LANIP set LANIP=%%a
if defined LANIP set LANIP=%LANIP: =%

echo.
if exist ".env" (
  echo [AI] api\.env found: real AI text and photo recognition are enabled.
) else if defined DASHSCOPE_API_KEY (
  echo [AI] DASHSCOPE_API_KEY detected: recognition uses qwen-vl-max, text uses qwen-max.
) else (
  echo [AI] No key: recognition falls back to mock, synesthesia text to the rule template.
  echo      For real AI, create api\.env  ^(copy .env.example .env^)  and put your key in it,
  echo      or run  set DASHSCOPE_API_KEY=your-bailian-key  in this window first.
  echo      The page labels the text source, so you can tell AI text from template text.
)
echo.
echo This PC     : http://localhost:8001
if defined LANIP echo Phone (same Wi-Fi): http://%LANIP%:8001
echo.
echo If the phone cannot open it, Windows Firewall is blocking inbound 8001.
echo Allow it once (needs admin) with:
echo   netsh advfirewall firewall add rule name="WanxiangAura-8001" dir=in action=allow protocol=TCP localport=8001
echo.
echo Close this window to stop.  ^(API health: /api/v1/health^)
call .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8001
pause
