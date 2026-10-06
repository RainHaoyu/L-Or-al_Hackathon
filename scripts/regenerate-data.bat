@echo off
rem ============================================================
rem  Wanxiang Aura - regenerate web\src\data\*.json (Windows)
rem
rem  WHY THIS FILE IS ASCII-ONLY
rem  cmd.exe decodes .bat bytes with the system OEM codepage
rem  (GBK on zh-CN); non-ASCII bytes can be mis-decoded and
rem  swallow a line. In particular the data-layer folder has a
rem  Chinese name, so locating it is done IN PYTHON
rem  (web\scripts\build_data.py, see find_data_dir) instead of
rem  by scanning directories from here.
rem
rem  Invoked by: the Chinese-named data wrapper at the repo root.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Data Pipeline

rem Repo root is one level up: this file lives in <repo>\scripts\
cd /d "%~dp0.." || (echo [ERROR] cannot cd to repo root & pause & exit /b 1)

set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul || (echo [ERROR] Python not found. Install Python 3.9+ & pause & exit /b 1)

echo Regenerating web\src\data\*.json from the data-layer folder ...
echo If that folder is missing, build_data.py prints every path it searched.
echo.
%PY% web\scripts\build_data.py
if errorlevel 1 (echo. & echo [ERROR] build_data.py failed, see output above & pause & exit /b 1)
echo.
echo Done: web\src\data\*.json regenerated ^(idempotent, safe to re-run^)
echo Note: if the backend contract ^(api\app\schemas.py^) changed, also run:
echo       cd api ^&^& .venv\Scripts\python scripts\gen_api_types.py
pause
