# wechat-course-dl

微信课程视频下载 → 语音识别 → 大纲提炼 全流程工具链。

## 项目目标

将微信（有赞）平台上的付费视频课程：
1. **批量下载** — 通过 MITM 代理捕获 HLS 视频流并合并为 MP4
2. **语音转文字** — 将视频音频转录为文字讲稿（faster-whisper GPU 加速）
3. **大纲提炼** — 用大模型将讲稿整理为结构化知识大纲

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 视频下载 | ✅ 完成 | 107 集 / 4.03GB / 0 失败 |
| 语音识别 | ⚠️ 进行中 | 已切换至 faster-whisper large-v3 + GPU 加速 |
| 大纲提炼 | ⚠️ 进行中 | 18/107 集已生成（基于 Whisper 粗转录，需重做） |

## 项目结构

```
wechat-course-dl/
├── batch_download.py      # 批量下载：获取课程列表 → 提取 m3u8 → 下载 ts → 合并 mp4
├── capture_addon.py       # mitmproxy 插件：拦截微信流量，捕获视频 URL 和 API
├── start_capture.py       # 启动代理：生成 CA 证书、设置系统代理、启动 mitmproxy
├── stop_proxy.py          # 停止代理：关闭系统代理设置
├── get_cookies.py         # 提取 cookies：从捕获数据中提取有赞平台认证信息
├── transcribe.py          # 语音识别：faster-whisper GPU 加速转录
├── generate_outline.py    # 大纲生成：调用 LLM 将讲稿整理为 Markdown 大纲
├── requirements.txt       # Python 依赖
├── scripts/               # 测试/调试脚本归档
│   ├── check_gpu.py       # GPU / CUDA 环境检测
│   ├── test_api.py
│   ├── test_download_one.py
│   ├── test_whisper_one.py
│   ├── decode_video_url.py
│   ├── analyze_capture.py
│   ├── extract_apis.py
│   └── show_transcript.py
├── downloads/             # (gitignore) 下载的 MP4 视频
├── transcripts/           # (gitignore) 转录文本
├── outlines/              # (gitignore) 生成的大纲
├── captured/              # (gitignore) mitmproxy 捕获数据
└── cookies.txt            # (gitignore) 有赞平台 cookies
```

## 环境搭建

### 前置要求
- Windows 10/11
- NVIDIA GPU（推荐 ≥4GB VRAM，支持 CUDA）
- 网络连接（首次下载模型 ~3GB）

### 一键安装

```powershell
# 1. 安装 uv (Python 包管理器)
irm https://astral.sh/uv/install.ps1 | iex
$env:Path = "C:\Users\$env:USERNAME\.local\bin;$env:Path"

# 2. 创建 Python 虚拟环境
uv python install 3.11
uv venv --python 3.11 .venv

# 3. 安装 PyTorch (CUDA GPU 加速)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# 4. 安装其他依赖
uv pip install faster-whisper requests openai imageio-ffmpeg mitmproxy

# 5. 验证 GPU
.venv\Scripts\python.exe scripts\check_gpu.py
```

### 无 GPU 安装（仅 CPU）

```powershell
uv pip install torch torchvision torchaudio
uv pip install faster-whisper requests openai imageio-ffmpeg mitmproxy
```

## 使用方法

### 激活虚拟环境

```powershell
.venv\Scripts\Activate.ps1
```

### 第一步：捕获视频（已完成）

```bash
python start_capture.py   # 启动代理（自动配置系统代理和 CA 证书）
# 在微信中打开课程，浏览视频列表
# 捕获完成后 Ctrl+C 停止
python get_cookies.py      # 提取 cookies
```

### 第二步：批量下载（已完成）

```bash
python batch_download.py
```

### 第三步：语音识别（GPU 加速）

```bash
# 全量转录 (自动检测 GPU，使用 large-v3 模型)
python transcribe.py

# 指定模型和设备
python transcribe.py --model large-v3 --device cuda --compute-type float16

# 只转录某一集
python transcribe.py --file "001"

# 强制重新转录 (覆盖已有文件)
python transcribe.py --force
```

**GPU 性能参考** (GTX 1660 Ti, large-v3, float16):
- 预计速度: 5-10x 实时 (1 分钟音频约 6-12 秒处理)
- 107 集 (约 20 小时音频) 预计总耗时: 2-4 小时

### 第四步：大纲生成

```bash
# 需配置 OPENAI_API_KEY 环境变量（或兼容的 LLM API）
$env:OPENAI_API_KEY = "your-key"
python generate_outline.py
```

## GPU 配置说明

| GPU VRAM | 推荐模型 | 推荐精度 | 预计速度 |
|----------|----------|----------|----------|
| ≥8GB | large-v3 | float16 | 8-15x 实时 |
| 4-8GB | large-v3 | float16/int8 | 5-10x 实时 |
| 2-4GB | medium | int8 | 3-5x 实时 |
| <2GB / CPU | small | float32 | 0.5-1x 实时 |

当前配置: **GTX 1660 Ti (6GB)** → large-v3 + float16

## 技术细节

### 视频下载流程
1. MITM 代理拦截微信流量 → 获取有赞平台 API 和认证信息
2. 调用有赞 `contentAndLive.json` API 获取课程列表（分页）
3. 访问每集详情页 → 从 URL 编码的 JSON 中提取 HLS m3u8 地址
4. 下载全部 .ts 分片 → ffmpeg 合并为 MP4

### 语音识别技术栈
- **引擎**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2)
- **模型**: Whisper large-v3 (多语言，中文精度高)
- **加速**: CUDA float16 半精度推理
- **优化**: VAD 静音过滤、beam search、temperature fallback

### 课程信息
- **平台**: 有赞（youzan.com）
- **内容**: 中医课程（108 集，讲师为台湾口音）
- **视频格式**: HLS (m3u8 + ts)

## 已知问题

1. **中医术语识别** — large-v3 模型显著改善，但仍需 LLM 后处理纠错
2. **部分视频转录为空** — 约 5 集视频内容过短或为片头，属正常现象
3. **旧转录/大纲质量不佳** — 建议用 `--force` 重新转录后重新生成大纲

## License

仅供个人学习使用。
