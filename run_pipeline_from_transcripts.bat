@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo Full pipeline: organize - fix - outline - sync - docx
echo ========================================

echo.
echo [1/5] organize_transcripts.py
uv run python scripts/organize_transcripts.py
if errorlevel 1 (
    echo ERROR: organize_transcripts failed
    exit /b 1
)

echo.
echo [2/5] fix_terminology.py
uv run python fix_terminology.py
if errorlevel 1 (
    echo ERROR: fix_terminology failed
    exit /b 1
)

echo.
echo [3/5] generate_outline.py --no-summary
uv run python generate_outline.py --no-summary
if errorlevel 1 (
    echo ERROR: generate_outline failed
    exit /b 1
)

echo.
echo [4/5] knowledge_sync.py --index
uv run python scripts/knowledge_sync.py --index
if errorlevel 1 (
    echo ERROR: knowledge_sync failed
    exit /b 1
)

echo.
echo [5/5] md_to_docx.py --font-size 18
uv run python scripts/md_to_docx.py --font-size 18
if errorlevel 1 (
    echo ERROR: md_to_docx failed
    exit /b 1
)

echo.
echo ========================================
echo Pipeline complete.
echo ========================================
exit /b 0
