@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "SOURCE_DIR=%~1"
if "%SOURCE_DIR%"=="" set "SOURCE_DIR=transcripts\高级"
set "MANIFEST=manifests\folder_pipeline.txt"

echo ========================================
echo Folder pipeline: %SOURCE_DIR%
echo ========================================

echo.
echo [1/2] build_transcript_manifest.py --source-dir
uv run python scripts/build_transcript_manifest.py --source-dir "%SOURCE_DIR%" --output "%MANIFEST%"
if errorlevel 1 (
    echo ERROR: build_transcript_manifest failed
    exit /b 1
)

echo.
echo [2/2] run_manifest_pipeline.py
uv run python scripts/run_manifest_pipeline.py --manifest "%MANIFEST%"
if errorlevel 1 (
    echo ERROR: run_manifest_pipeline failed
    exit /b 1
)

echo.
echo ========================================
echo Folder pipeline complete.
echo ========================================
exit /b 0
