@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 万象 Aura - 一键启动
cd /d %~dp0
echo ============================================
echo   万象 Aura 一键启动（首次运行自动安装依赖）
echo ============================================
echo.
rem ---- 可选：后端（有 Python 就起，失败不影响前端）----
where py >nul 2>nul && (start "万象Aura后端" cmd /c call "%~dp0启动后端.bat")
if errorlevel 1 where python >nul 2>nul && (start "万象Aura后端" cmd /c call "%~dp0启动后端.bat")
rem ---- 必起：前端 ----
call "%~dp0启动前端.bat"
