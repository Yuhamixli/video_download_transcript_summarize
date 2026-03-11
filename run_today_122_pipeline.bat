@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "MANIFEST=manifests\today_122.txt"

echo ========================================
echo Targeted pipeline: today's transcripts only
echo ========================================

echo.
echo [1/5] build_transcript_manifest.py
uv run python scripts/build_transcript_manifest.py --output "%MANIFEST%"
if errorlevel 1 (
    echo ERROR: build_transcript_manifest failed
    exit /b 1
)

echo.
echo [2/5] fix_terminology.py --manifest
uv run python fix_terminology.py --manifest "%MANIFEST%"
if errorlevel 1 (
    echo ERROR: fix_terminology failed
    exit /b 1
)

echo.
echo [3/5] generate_outline.py --manifest --no-summary
uv run python generate_outline.py --manifest "%MANIFEST%" --no-summary
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
echo [5/5] md_to_docx.py --manifest --font-size 18
uv run python scripts/md_to_docx.py --manifest "%MANIFEST%" --font-size 18
if errorlevel 1 (
    echo ERROR: md_to_docx failed
    exit /b 1
)

echo.
echo ========================================
echo Targeted pipeline complete.
echo ========================================
exit /b 0
