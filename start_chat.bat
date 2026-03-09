@echo off
chcp 65001 >nul
title 中医知识助手 - TCM RAG Chat
color 0A

:: Enable delayed expansion for variables inside if blocks
setlocal EnableDelayedExpansion

echo ===========================================
echo    中医知识助手 - 启动中
echo ===========================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "TOKENIZERS_PARALLELISM=false"

:: Check .env exists
if not exist "%PROJECT_DIR%\.env" (
    echo [错误] 未找到 .env 文件
    echo 请复制 .env.example 为 .env 并配置 API Key
    pause
    exit /b 1
)

:: Check if uv is available
where uv >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 uv 命令
    echo 请先安装 uv: irm https://astral.sh/uv/install.ps1 ^| iex
    pause
    exit /b 1
)

:: Check if vector database exists and has content
set "VECTOR_DB=%PROJECT_DIR%vector_db"
set "NEED_INDEX=0"

:: Check ChromaDB SQLite file (newer versions use SQLite)
if not exist "%VECTOR_DB%" (
    echo [提示] 向量数据库不存在，需要构建索引...
    set "NEED_INDEX=1"
) else (
    :: Check for ChromaDB files (.sqlite3 or .parquet)
    set "HAS_CHROMA=0"
    if exist "%VECTOR_DB%\chroma.sqlite3" set "HAS_CHROMA=1"
    if exist "%VECTOR_DB%\*.parquet" set "HAS_CHROMA=1"
    
    if !HAS_CHROMA! equ 0 (
        echo [提示] 向量数据库为空，需要构建索引...
        set "NEED_INDEX=1"
    ) else (
        echo [OK] 向量数据库已存在
    )
)

:: Also check knowledge folder exists and has content
set "KNOWLEDGE_DIR=%PROJECT_DIR%knowledge"
if not exist "%KNOWLEDGE_DIR%\outlines" (
    echo [提示] 知识库大纲不存在，需要同步...
    set "NEED_INDEX=1"
) else (
    :: Check if outlines folder has any .md files
    dir /s /b "%KNOWLEDGE_DIR%\outlines\*.md" >nul 2>nul
    if errorlevel 1 (
        echo [提示] 知识库大纲为空，需要同步...
        set "NEED_INDEX=1"
    )
)

if not exist "%KNOWLEDGE_DIR%\transcripts" (
    echo [提示] 知识库转录不存在，需要同步...
    set "NEED_INDEX=1"
) else (
    :: Check if transcripts folder has any .txt files
    dir /s /b "%KNOWLEDGE_DIR%\transcripts\*.txt" >nul 2>nul
    if errorlevel 1 (
        echo [提示] 知识库转录为空，需要同步...
        set "NEED_INDEX=1"
    )
)

:: Build index if needed
if !NEED_INDEX! equ 1 (
    echo.
    echo ===========================================
    echo    正在构建知识库索引...
    echo    首次运行需要 2-5 分钟
    echo ===========================================
    echo.
    
    uv run python scripts/knowledge_sync.py --index
    
    if errorlevel 1 (
        echo.
        echo [错误] 索引构建失败
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] 索引构建完成
    timeout /t 2 /nobreak >nul
)

:: Clear screen and start chat
cls
echo ===========================================
echo    正在启动中医知识助手...
echo ===========================================
echo.
echo 可用命令:
echo   /help      - 显示帮助
echo   /courses   - 列出课程
echo   /search    - 搜索文档
echo   /course    - 设置课程范围
echo   /clear     - 清空历史
echo   /quit      - 退出
echo.
echo ===========================================
echo.

:: Start the chat
uv run python rag_chat.py

:: Pause if chat exits with error
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出 (code: %errorlevel%)
    pause
)
