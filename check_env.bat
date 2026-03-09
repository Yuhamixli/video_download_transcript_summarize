@echo off
chcp 65001 >nul
title 检查环境配置
color 0B

echo ===========================================
echo    环境配置检查
echo ===========================================
echo.

cd /d "%~dp0"

:: 1. Check uv
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] uv 已安装
    uv --version
) else (
    echo [错误] uv 未安装
    echo 请运行: irm https://astral.sh/uv/install.ps1 ^| iex
)
echo.

:: 2. Check .env
if exist ".env" (
    echo [OK] .env 文件存在
    
    :: Parse and check API key
    for /f "tokens=1,2 delims==" %%a in (.env) do (
        if "%%a"=="OPENAI_API_KEY" (
            set "API_KEY=%%b"
            if "%%b"=="" (
                echo [错误] OPENAI_API_KEY 为空
            ) else (
                if "%%b"=="your-api-key-here" (
                    echo [错误] OPENAI_API_KEY 未修改 (还是 your-api-key-here)
                ) else (
                    echo [OK] OPENAI_API_KEY 已设置
                    echo       Key: %%b
                )
            )
        )
        if "%%a"=="OPENAI_API_BASE" (
            echo [OK] API_BASE: %%b
        )
        if "%%a"=="LLM_MODEL" (
            echo [OK] LLM_MODEL: %%b
        )
    )
) else (
    echo [错误] 未找到 .env 文件
    echo 请复制 .env.example 为 .env 并配置
)
echo.

:: 3. Check Python dependencies
echo [检查] Python 依赖...
uv run python -c "import chromadb; print('[OK] chromadb 已安装')" 2>nul || echo [缺少] chromadb - pip install chromadb
uv run python -c "import sentence_transformers; print('[OK] sentence-transformers 已安装')" 2>nul || echo [缺少] sentence-transformers - pip install sentence-transformers
uv run python -c "import openai; print('[OK] openai 已安装')" 2>nul || echo [缺少] openai - pip install openai
echo.

:: 4. Check data folders
echo [检查] 数据文件夹...
if exist "outlines" (
    for /f %%i in ('dir /s /b "outlines\*.md" 2^>nul ^| find /c /v ""') do echo [OK] outlines/: %%i 个 .md 文件
) else (
    echo [缺少] outlines/ 文件夹
)

if exist "transcripts_corrected" (
    for /f %%i in ('dir /s /b "transcripts_corrected\*.txt" 2^>nul ^| find /c /v ""') do echo [OK] transcripts_corrected/: %%i 个 .txt 文件
) else (
    echo [缺少] transcripts_corrected/ 文件夹
)

if exist "knowledge" (
    echo [OK] knowledge/ 文件夹存在
) else (
    echo [提示] knowledge/ 尚未创建 (运行索引构建后将自动创建)
)

if exist "vector_db" (
    echo [OK] vector_db/ 文件夹存在
) else (
    echo [提示] vector_db/ 尚未创建 (运行索引构建后将自动创建)
)
echo.

:: 5. Test API
echo [测试] API 连接...
uv run python -c "
import os
from openai import OpenAI

api_key = os.environ.get('OPENAI_API_KEY', '')
if not api_key or api_key == 'your-api-key-here':
    print('[跳过] API Key 未配置')
else:
    try:
        client = OpenAI(api_key=api_key, base_url=os.environ.get('OPENAI_API_BASE', 'https://openrouter.ai/api/v1'), timeout=10)
        # Try a simple models list call
        models = client.models.list()
        print('[OK] API 连接成功')
    except Exception as e:
        print(f'[错误] API 连接失败: {e}')
" 2>&1

echo.
echo ===========================================
echo    检查完成
echo ===========================================
pause
