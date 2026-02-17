# wechat-course-dl

微信课程视频下载 → 语音识别 → 大纲提炼 全流程工具链。

## 项目目标

将微信（有赞）平台上的付费视频课程：
1. **批量下载** — 通过 MITM 代理捕获 HLS 视频流并合并为 MP4
2. **语音转文字** — 将视频音频转录为文字讲稿
3. **大纲提炼** — 用大模型将讲稿整理为结构化知识大纲

## 当前进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 视频下载 | ✅ 完成 | 107 集 / 4.03GB / 0 失败 |
| 语音识别 | ⚠️ 进行中 | 23/107 集已转录（Whisper small，精度不足，需改用云端 ASR） |
| 大纲提炼 | ⚠️ 进行中 | 18/107 集已生成（基于 Whisper 粗转录，术语有误） |

## 项目结构

```
wechat-course-dl/
├── batch_download.py      # 批量下载：获取课程列表 → 提取 m3u8 → 下载 ts → 合并 mp4
├── capture_addon.py       # mitmproxy 插件：拦截微信流量，捕获视频 URL 和 API
├── start_capture.py       # 启动代理：生成 CA 证书、设置系统代理、启动 mitmproxy
├── stop_proxy.py          # 停止代理：关闭系统代理设置
├── get_cookies.py         # 提取 cookies：从捕获数据中提取有赞平台认证信息
├── transcribe.py          # 语音识别：Whisper 本地转录（待替换为云端 ASR）
├── generate_outline.py    # 大纲生成：调用 LLM 将讲稿整理为 Markdown 大纲
├── requirements.txt       # Python 依赖
├── scripts/               # 测试/调试脚本归档
│   ├── test_api.py
│   ├── test_download_one.py
│   ├── test_whisper_one.py
│   ├── decode_video_url.py
│   ├── analyze_capture.py
│   ├── extract_apis.py
│   ├── check_gpu.py
│   └── show_transcript.py
├── downloads/             # (gitignore) 下载的 MP4 视频
├── transcripts/           # (gitignore) 转录文本
├── outlines/              # (gitignore) 生成的大纲
├── captured/              # (gitignore) mitmproxy 捕获数据
└── cookies.txt            # (gitignore) 有赞平台 cookies
```

## 使用方法

### 环境要求
- Python 3.10+
- ffmpeg（或通过 `pip install imageio-ffmpeg` 获取）
- mitmproxy

### 第一步：捕获视频（已完成）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动代理（会自动配置系统代理和 CA 证书）
python start_capture.py

# 在微信中打开课程，浏览视频列表
# 捕获完成后 Ctrl+C 停止

# 提取 cookies
python get_cookies.py
```

### 第二步：批量下载（已完成）

```bash
python batch_download.py
```

### 第三步：语音识别（待改进）

```bash
# 当前方案（Whisper 本地，精度不足）
python transcribe.py

# 推荐方案：使用讯飞/阿里云 ASR，详见 TODO.md
```

### 第四步：大纲生成

```bash
# 需配置 OPENAI_API_KEY 环境变量（或兼容的 LLM API）
python generate_outline.py
```

## 技术细节

### 视频下载流程
1. MITM 代理拦截微信流量 → 获取有赞平台 API 和认证信息
2. 调用有赞 `contentAndLive.json` API 获取课程列表（分页）
3. 访问每集详情页 → 从 URL 编码的 JSON 中提取 HLS m3u8 地址
4. 下载全部 .ts 分片 → ffmpeg 合并为 MP4

### 课程信息
- **平台**: 有赞（youzan.com）
- **内容**: 中医课程（108 集，讲师为台湾口音）
- **视频格式**: HLS (m3u8 + ts)

## 已知问题

1. **Whisper 转录精度不足** — small 模型对中医术语识别错误率高（"脉诊"→"卖诊"，"肾阴虚"→"圣音虚"）
2. **部分视频转录为空** — 约 5 集视频内容过短或为片头，Whisper 输出仅为 prompt 重复
3. **大纲基于错误转录** — 当前 18 份大纲系人工阅读转录后生成，已尽量纠正术语，但需在精确转录后重做

## License

仅供个人学习使用。
