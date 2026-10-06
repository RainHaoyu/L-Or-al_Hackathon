@echo off
rem ============================================================
rem  Wanxiang Aura - data pipeline (Windows)
rem
rem  IMPORTANT: this file must stay ASCII-only except the "??"
rem  wildcard below. cmd.exe parses .bat bytes with the system
rem  OEM codepage (GBK on zh-CN); UTF-8 CJK text here gets
rem  mis-decoded and can swallow the rest of a line.
rem ============================================================
setlocal EnableDelayedExpansion
title Wanxiang Aura - Data Pipeline
rem Must run from the repo root: build_data.py resolves the data-layer
rem folder via ROOT.parent.parent, i.e. ONE LEVEL ABOVE the repo.
cd /d %~dp0
set PY=python
where py >nul 2>nul && set PY=py -3
rem The data-layer folder has a CJK name; "??" matches one CJK char.
if not exist "..\??层" (
  echo [ERROR] Missing data source: the data-layer folder ONE LEVEL ABOVE the repo
  echo         It holds the upstream xlsx/docx files and is NOT shipped in the repo.
  echo         Ask the data owner for it, then place it there.
  pause & exit /b 1
)
echo Building web\src\data\*.json from the data-layer folder ...
%PY% web\scripts\build_data.py
if errorlevel 1 (echo [ERROR] build_data.py failed, see output above & pause & exit /b 1)
echo.
echo Done: web\src\data\*.json regenerated ^(idempotent, safe to re-run^)
echo Note: if the backend contract ^(api\app\schemas.py^) changed, also run:
echo       cd api ^&^& .venv\Scripts\python scripts\gen_api_types.py
pause
