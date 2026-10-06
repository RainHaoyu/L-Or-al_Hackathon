@echo off
rem ============================================================
rem  Wanxiang Aura - one-click launcher (Windows)
rem  Double-click this file: it starts the backend (optional)
rem  in a new window and the frontend in this one.
rem
rem  WHY THIS FILE IS ASCII-ONLY
rem  cmd.exe decodes .bat bytes with the system OEM codepage
rem  (GBK on zh-CN), so non-ASCII bytes here can be mis-decoded
rem  and swallow a whole line. That is why this launcher never
rem  names the Chinese-named entry points: it calls the
rem  ASCII-named cores in scripts\ instead.
rem
rem  Two cmd.exe traps this design deliberately avoids:
rem    - a "??" wildcard works in `if exist` but NOT in `call`
rem      (call "%~dp0<name with ??>.bat" -> "cannot find the path"),
rem      where ?? is meant to stand for one CJK character
rem    - a glob built from the CJK word for "end" plus .bat matches
rem      BOTH the frontend and the backend script, so globs cannot
rem      tell them apart either
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Launcher

cd /d "%~dp0" || (echo [ERROR] cannot cd to repo root & pause & exit /b 1)
set FRONT=%~dp0scripts\start-frontend.bat
set BACK=%~dp0scripts\start-backend.bat

echo ============================================
echo   Wanxiang Aura - Launcher
echo ============================================
echo.
echo   Frontend: http://localhost:3000   (standalone, backend optional)
echo   Backend : http://localhost:8001   (optional; real AI recognition and text)
echo.

if not exist "%FRONT%" (echo [ERROR] missing scripts\start-frontend.bat & pause & exit /b 1)
if not exist "%BACK%" echo [WARN] missing scripts\start-backend.bat: frontend only.
echo   The Chinese-named wrappers at the repo root just call scripts\*.bat,
echo   so every way of starting the app is equivalent.
echo.

if exist "%BACK%" (
  set PYFOUND=
  where py >nul 2>nul && set PYFOUND=1
  if not defined PYFOUND where python >nul 2>nul && set PYFOUND=1
  if defined PYFOUND (
    echo Starting backend in a new window ...
    start "WanxiangAura-Backend" cmd /c call "%BACK%"
  ) else (
    echo [WARN] Python not found: frontend only. The local engine is fully functional.
  )
)

echo Starting frontend in this window ...
call "%FRONT%"
