@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title 万象 Aura - 前端
cd /d %~dp0aura\web
where node >nul 2>nul || (echo [缺依赖] 未检测到 Node.js，请先安装 LTS 版：https://nodejs.org/zh-cn && pause & exit /b 1)
for /f "tokens=* usebackq" %%v in (`node -v`) do set NODEV=%%v
echo [1/3] Node !NODEV! 检测通过
if not exist node_modules (
  echo [2/3] 首次运行：安装依赖（约 2-5 分钟，如慢可换国内镜像：npm config set registry https://registry.npmmirror.com）...
  call npm install --no-audit --no-fund || (echo 依赖安装失败，请检查网络后重试 & pause & exit /b 1)
) else (
  echo [2/3] 依赖已就绪
)
echo [3/3] 启动开发服务器 http://localhost:5199 （关闭本窗口即停止）
start "" http://localhost:5199
call npm run dev -- --port 5199 --strictPort --host
pause
