@echo off
chcp 65001 >nul
title 重建知识库索引
color 0E

echo ===========================================
echo    重建知识库索引
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

echo 此操作将:
echo  1. 同步 outlines/ 到 knowledge/outlines/
echo  2. 同步 transcripts_corrected/ 到 knowledge/transcripts/
echo  3. 重新构建向量索引 (约需 2-5 分钟)
echo.

:: Confirm
set /p CONFIRM="确认重建? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo ===========================================
echo    开始重建索引...
echo ===========================================
echo.

:: Delete old vector DB to force rebuild
if exist "%~dp0vector_db" (
    echo [步骤 1/3] 清理旧索引...
    rmdir /s /q "%~dp0vector_db"
    echo [OK] 旧索引已清理
)

:: Sync and index
echo.
echo [步骤 2/3] 同步知识库...
uv run python scripts/knowledge_sync.py
if %errorlevel% neq 0 (
    echo [错误] 同步失败
    pause
    exit /b 1
)

echo.
echo [步骤 3/3] 构建向量索引...
uv run python scripts/knowledge_sync.py --index
if %errorlevel% neq 0 (
    echo [错误] 索引构建失败
    pause
    exit /b 1
)

echo.
echo ===========================================
echo    索引重建完成!
echo ===========================================
echo.
echo 现在可以运行 start_chat.bat 开始对话
echo.

pause
