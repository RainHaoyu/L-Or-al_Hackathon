@echo off
rem ============================================================
rem  Wanxiang Aura - one-click launcher (Windows)
rem
rem  IMPORTANT: this file must stay ASCII-only except the "??"
rem  wildcards below (see note). cmd.exe parses .bat bytes with
rem  the system OEM codepage (GBK on zh-CN); UTF-8 CJK text here
rem  gets mis-decoded and can swallow the rest of a line.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Launcher
cd /d %~dp0
echo ============================================
echo   Wanxiang Aura - Launcher
echo ============================================
echo.
echo   Frontend: http://localhost:3000   (standalone, backend optional)
echo   Backend : http://localhost:8001   (optional; real AI recognition ^& text)
echo.
where node >nul 2>nul || (echo [ERROR] Node.js not found. Install LTS: https://nodejs.org/zh-cn & pause & exit /b 1)
echo [OK] Node.js detected
set PYFOUND=
where py >nul 2>nul && set PYFOUND=1
if not defined PYFOUND where python >nul 2>nul && set PYFOUND=1
if not defined PYFOUND echo [WARN] Python not found: frontend only. Local engine is fully functional.
echo.
rem The sibling scripts have CJK filenames, so they are referenced via
rem ASCII wildcards: "??" matches one CJK char in Windows path globbing.
if defined PYFOUND start "WanxiangAura-Backend" cmd /c call "%~dp0??后端.bat"
call "%~dp0??前端.bat"
