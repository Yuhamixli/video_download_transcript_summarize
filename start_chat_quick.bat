@echo off
chcp 65001 >nul
title 中医知识助手 - TCM RAG Chat
color 0A

echo ===========================================
echo    中医知识助手 - 快速启动
echo ===========================================
echo.

cd /d "%~dp0"

:: Check if uv is available
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 uv 命令
    pause
    exit /b 1
)

:: Quick start without checking (assume already indexed)
uv run python rag_chat.py

if %errorlevel% neq 0 (
    echo.
    pause
)
