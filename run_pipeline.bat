@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================================
echo  微信课程全流程工具链
echo  下载 → 转录 → 纠错 → 大纲 → Word
echo ============================================================
echo.

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM Activate venv so mitmdump and other tools are on PATH
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

set "PY=python"

REM ============================================================
REM  Phase 1: 捕获 + 下载
REM ============================================================

echo [Phase 1/2] 捕获微信流量 + 下载视频
echo.
echo  即将启动 MITM 代理...
echo  请在微信中打开课程视频页面（随便播放一集即可）
echo  完成后在此窗口按 Ctrl+C 停止捕获
echo.
pause

%PY% start_capture.py
if errorlevel 1 (
    echo [WARN] 代理退出，确保系统代理已关闭...
    %PY% stop_proxy.py
)

echo.
echo [1/5] 提取 Cookies...
%PY% get_cookies.py
if errorlevel 1 (
    echo [ERROR] Cookie 提取失败，请检查 captured/ 是否有捕获文件
    goto :fail
)

echo.
echo [2/5] 提取课程配置...
%PY% scripts/extract_course_config.py
if errorlevel 1 (
    echo [ERROR] 课程配置提取失败
    echo 请手动检查 captured/ 中的数据，或手动编辑 course_config.json
    goto :fail
)

echo.
echo [3/5] 批量下载视频...
%PY% batch_download.py
if errorlevel 1 (
    echo [WARN] 部分视频下载失败，继续处理已下载的文件
)

REM ============================================================
REM  Phase 2: 转录 + 纠错 + 大纲 + Word
REM ============================================================

echo.
echo ============================================================
echo [Phase 2/2] 转录 + 纠错 + 大纲 + 导出
echo ============================================================

echo.
echo [4/5] 语音转文字 (GPU 加速，耗时较长)...
%PY% transcribe.py
if errorlevel 1 (
    echo [ERROR] 转录失败
    goto :fail
)

echo.
echo [5/5] 术语纠错 (LLM API)...
%PY% fix_terminology.py
if errorlevel 1 (
    echo [WARN] 部分纠错失败，继续生成大纲
)

echo.
echo [6] 生成单集大纲 (LLM API)...
%PY% generate_outline.py --no-summary
if errorlevel 1 (
    echo [WARN] 部分大纲生成失败
)

echo.
echo [7] 生成完整课程大纲 (LLM API)...
%PY% generate_outline.py --force
if errorlevel 1 (
    echo [WARN] 课程总大纲生成失败
)

echo.
echo [8] 导出 Word 大字版 (18pt)...
%PY% scripts/md_to_docx.py --font-size 18
if errorlevel 1 (
    echo [WARN] Word 导出失败，请检查 pandoc 是否已安装
)

echo.
echo ============================================================
echo  全流程完成!
echo.
echo  视频:    downloads\
echo  转录:    transcripts\
echo  纠错:    transcripts_corrected\
echo  大纲:    outlines\
echo  Word:    outlines_docx\
echo ============================================================
goto :end

:fail
echo.
echo [FAILED] 流程中断，请检查上方错误信息
echo.

:end
pause
