@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo Full pipeline: outline + sync + docx
echo ========================================

echo.
echo [1/3] generate_outline.py --no-summary
uv run python generate_outline.py --no-summary
if errorlevel 1 (
    echo ERROR: generate_outline failed
    exit /b 1
)

echo.
echo [2/3] knowledge_sync.py --index
uv run python scripts/knowledge_sync.py --index
if errorlevel 1 (
    echo ERROR: knowledge_sync failed
    exit /b 1
)

echo.
echo [3/3] md_to_docx.py --font-size 18
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
