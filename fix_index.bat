@echo off
chcp 65001 >nul
title 修复知识库索引
color 0E
setlocal EnableDelayedExpansion

echo ===========================================
echo    修复知识库索引
echo ===========================================
echo.

cd /d "%~dp0"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "TOKENIZERS_PARALLELISM=false"

:: Check uv
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 uv 命令
    pause
    exit /b 1
)

echo [步骤 1/4] 检查源数据...
echo.

:: Check if source data exists
set "HAS_OUTLINES=0"
set "HAS_TRANSCRIPTS=0"

if exist "outlines" (
    dir /s /b "outlines\*.md" >nul 2>nul
    if not errorlevel 1 set "HAS_OUTLINES=1"
)

if exist "transcripts_corrected" (
    dir /s /b "transcripts_corrected\*.txt" >nul 2>nul
    if not errorlevel 1 set "HAS_TRANSCRIPTS=1"
)

if %HAS_OUTLINES% equ 0 (
    echo [错误] 未找到 outlines/ 数据
    echo 请先运行 generate_outline.py 生成大纲
    pause
    exit /b 1
)

if %HAS_TRANSCRIPTS% equ 0 (
    echo [警告] 未找到 transcripts_corrected/ 数据
    echo 将仅同步 outlines
)

echo [OK] 源数据检查完成
echo.

:: Clean old index
echo [步骤 2/4] 清理旧索引...
if exist "knowledge" (
    rmdir /s /q "knowledge"
    echo [OK] 已清理 knowledge/
)
if exist "vector_db" (
    rmdir /s /q "vector_db"
    echo [OK] 已清理 vector_db/
)
echo.

:: Sync knowledge
echo [步骤 3/4] 同步知识库...
uv run python scripts/knowledge_sync.py
if errorlevel 1 (
    echo [错误] 同步失败
    pause
    exit /b 1
)
echo.

:: Build index
echo [步骤 4/4] 构建向量索引...
echo [注意] 首次构建需要下载嵌入模型，约需 2-5 分钟
echo.
uv run python scripts/knowledge_sync.py --index
if errorlevel 1 (
    echo [错误] 索引构建失败
    pause
    exit /b 1
)

echo.
echo ===========================================
echo    索引修复完成!
echo ===========================================
echo.

:: Show stats
call uv run python scripts/show_kb_stats.py

echo.
pause
