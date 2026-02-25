# wechat-course-dl

微信课程视频下载 → 语音识别 → 术语纠错 → 大纲提炼 全流程工具链。

## 项目目标

将微信（有赞）平台上的付费视频课程：
1. **批量下载** — 通过 MITM 代理捕获 HLS 视频流并合并为 MP4
2. **语音转文字** — faster-whisper large-v3 GPU 加速转录
3. **术语纠错** — LLM 对中医专业术语进行后处理校对，支持人工反馈持续改进
4. **大纲提炼** — LLM 将讲稿整理为结构化知识大纲

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 视频下载 | ✅ 完成 | 107 集 / 4.03GB / 0 失败 |
| 语音识别 | ✅ 完成 | 107/107 集 (faster-whisper large-v3, GPU, ~4.5h) |
| 术语纠错 | ✅ 完成 | 107/107 集, 913 处修改 (MiniMax-M2.5 via OpenRouter) |
| 大纲提炼 | ✅ 完成 | 107/107 集结构化 Markdown 大纲 |

## 项目结构

```
wechat-course-dl/
├── batch_download.py          # 批量下载：获取课程列表 → 下载 HLS → 合并 MP4
├── capture_addon.py           # mitmproxy 插件：拦截微信流量
├── start_capture.py           # 启动代理
├── stop_proxy.py              # 停止代理
├── get_cookies.py             # 提取 cookies
├── transcribe.py              # 语音识别：faster-whisper GPU 加速转录
├── fix_terminology.py         # 术语纠错：LLM 后处理 + 人工反馈学习
├── generate_outline.py        # 大纲生成：LLM 结构化大纲
├── manual_corrections.json    # 手动纠错学习表（持续积累）
├── requirements.txt           # Python 依赖
├── .env.example               # API 配置模板
├── scripts/                   # 工具脚本
│   ├── check_gpu.py           # GPU / CUDA 环境检测
│   ├── show_diff.py           # 显示纠错前后差异
│   ├── show_corrections.py    # 显示纠错报告
│   ├── check_report.py        # 检查处理状态
│   ├── md_to_docx.py          # 大纲导出 Word（大字版）
│   └── ...
├── downloads/                 # MP4 视频
├── transcripts/               # 原始转录文本 (.txt + _detail.json)
├── transcripts_corrected/     # 纠错后转录文本
└── outlines/                  # 结构化大纲 (.md)
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

# 5. 配置 API (复制 .env.example 为 .env，填入 API Key)
cp .env.example .env

# 6. 验证 GPU
.venv\Scripts\python.exe scripts\check_gpu.py
```

## 使用方法

### 完整流程（4 步）

```bash
# 1. 转录视频 (GPU 加速, ~4.5h for 107 episodes)
python transcribe.py

# 2. 术语纠错 (LLM API, ~70min)
python fix_terminology.py

# 3. 生成大纲 (LLM API, ~60min)
python generate_outline.py

# 4. 生成课程总大纲
python generate_outline.py --force  # 不带 --no-summary
```

### 术语纠错持续改进

```bash
# 查看纠错报告
python scripts/show_corrections.py

# 手动添加纠错规则到 manual_corrections.json，然后重跑
python fix_terminology.py --force

# LLM 会自动将新发现的规则合并回 manual_corrections.json
```

### 常用选项

```bash
# 只处理某一集
python transcribe.py --file "001"
python fix_terminology.py --file "001"
python generate_outline.py --file "001"

# 强制重新处理
python transcribe.py --force
python fix_terminology.py --force
python generate_outline.py --force
```

### 大纲导出为 Word（大字版）

将 `outlines/` 下的 Markdown 大纲转为 MS Word，便于长辈阅读（默认 16pt 正文）：

```bash
# 需先安装 pandoc: winget install pandoc 或 choco install pandoc
pip install python-docx
python scripts/md_to_docx.py
```

输出到 `outlines_docx/`。可选参数：
- `--font-size 18`：正文字号（默认 16pt）
- `--single 00_完整课程大纲.md`：只转换单个文件

## 术语纠错机制

本项目采用 **LLM + 人工反馈** 的持续改进模式：

1. **内置词典** — `fix_terminology.py` 包含完整的中医术语词典（脏腑、经络、穴位、方剂、病证等）
2. **手动纠错表** — `manual_corrections.json` 记录已确认的纠错规则，LLM 会严格遵守
3. **自动学习** — 每次运行后，LLM 发现的新纠错规则自动合并到手动表（标记为待审核）
4. **持续改进** — 人工审核 → 确认/修改 → 重跑 → 更精确的结果

当前积累：**~480 条纠错规则**（27 条初始 + ~453 条 LLM 自动发现）

## GPU 配置说明

| GPU VRAM | 推荐模型 | 推荐精度 | 实测速度 |
|----------|----------|----------|----------|
| ≥8GB | large-v3 | float16 | 8-15x 实时 |
| 4-8GB | large-v3 | float16 | **~2x 实时** (GTX 1660 Ti) |
| 2-4GB | medium | int8 | 3-5x 实时 |
| <2GB / CPU | small | float32 | 0.3-0.5x 实时 |

## 技术栈

| 组件 | 技术 |
|------|------|
| 语音识别 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) + CUDA |
| 术语纠错 | MiniMax-M2.5 via OpenRouter (OpenAI 兼容 API) |
| 大纲生成 | MiniMax-M2.5 via OpenRouter |
| GPU 加速 | PyTorch 2.10 + CUDA 12.6 |
| 包管理 | uv + Python 3.11 |
| 视频下载 | mitmproxy + ffmpeg |

## AI 接手 Prompt
> **角色**：你是一位经验丰富的全栈工程师，正在接手一个微信课程下载与知识提炼项目。
>
> **项目背景**：
> 这是一个从微信（有赞平台）下载中医视频课程并转化为结构化知识大纲的工具链。
> 视频下载阶段已全部完成（107 集 MP4，共 4.03GB）。
> 当前卡在语音识别精度问题上——Whisper small 模型对中医专业术语识别错误率很高。
>
> **你需要完成的任务（按优先级排列）**：
>
> ### 任务 1：高精度语音识别
> - 将 `downloads/` 下 107 个 MP4 视频转录为精确的中文文本
> - **推荐方案**：使用讯飞 ASR 或阿里云语音识别（中文精度远高于 Whisper）
> - **备选方案**：faster-whisper + large-v3 模型（本机有 GPU 可加速）
> - 输出到 `transcripts/` 目录，格式：每集一个 `.txt`（纯文本）+ `_detail.json`（带时间戳）
> - **关键**：本课程是中医课程，讲师有台湾口音，涉及大量专业术语（阴阳、五行、脏腑、经络、方剂名、穴位名等），必须确保术语准确
>
> ### 任务 2：LLM 术语纠错（如果 ASR 仍有错误）
> - 用大模型对 ASR 输出做后处理纠错
> - 提供中医术语词典作为参考上下文
> - 重点纠正：方剂名、穴位名、脏腑名、病证名
> - 示例常见错误：
>   - "卖诊" → "脉诊"
>   - "圣音虚" → "肾阴虚"
>   - "方计" → "方剂"
>   - "血味" → "穴位"
>   - "寸官词" → "寸关尺"
>
> ### 任务 3：重新生成全部大纲
> - 基于纠错后的精确转录，为每集生成结构化 Markdown 大纲
> - 大纲格式参考 `outlines/` 中已有的示例（分层级、含表格对比、方证对应）
> - 最终汇总生成完整的课程知识体系大纲
>
> **项目结构说明**：
> - `batch_download.py` — 批量下载脚本（已完成使命）
> - `transcribe.py` — Whisper 转录脚本（需替换或增强）
> - `generate_outline.py` — LLM 大纲生成脚本（需在精确转录后使用）
> - `scripts/` — 测试调试脚本归档
> - `downloads/` — 107 个 MP4 视频（需从源机器拷贝或重新下载）
> - `transcripts/` — 转录文本（当前 23 份精度不足，建议清空重做）
> - `outlines/` — 大纲（当前 18 份基于粗转录，建议清空重做）
>
> **环境信息**：
> - Python 3.10+
> - GPU 可用（用于 faster-whisper 或本地大模型）
> - 需要配置 ASR 服务 API key（讯飞/阿里云）和 LLM API key
>
> **注意事项**：
> 1. `cookies.txt` 中的有赞 cookies 有时效性，如需重新下载视频需重新捕获
> 2. 已有的 `transcripts/` 和 `outlines/` 质量不佳，建议清空后重新生成
> 3. 部分视频很短（片头/预告），转录可能为空，属正常现象
> 4. 讲师台湾口音明显，"虚"常发"须"，"血"常发"薛"，需注意

## License

仅供个人学习使用。
