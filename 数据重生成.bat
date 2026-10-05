@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 万象 Aura - 数据管线
cd /d %~dp0aura\web
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% scripts/build_data.py
echo 完成：src/data/*.json 已按 数据层/ 最新文件重新生成
pause
