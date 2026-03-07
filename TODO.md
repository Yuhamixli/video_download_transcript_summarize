# TODO — wechat-course-dl

## 当前状态（2026-02-25）

### 课程 1：中医入门（108集）✅
- [x] 视频下载：107 集全部完成（4.03GB），存于 `downloads/`
- [x] 语音识别：107/107 集已用 faster-whisper large-v3 GPU 加速转录
- [x] LLM 术语纠错：107/107 集已完成，共 913 处修改
- [x] 大纲提炼：107/107 集已生成结构化 Markdown 大纲
- [x] Word 导出：108 个 .docx 文件，18pt 大字版

### 课程 2：本草/方剂（130集）🔄 进行中
- [x] 视频下载：130/130 集完成，存于 `downloads/`
- [x] 语音识别：（faster-whisper large-v3, GPU）
- [x] LLM 术语纠错
- [x] 大纲提炼
- [ ] Word 导出

### 通用
- [ ] 人工审核 `manual_corrections.json` 中 LLM 自动发现的纠错规则

---

## 持续改进流程

### 手动纠错反馈循环
1. 阅读 `transcripts_corrected/` 中的文本，发现错误
2. 在 `manual_corrections.json` 中添加新的纠错规则
3. 重新运行 `python fix_terminology.py --force` 应用新规则
4. LLM 会自动将新发现的错误合并回 `manual_corrections.json`

### 当前纠错规则统计
- 初始手动规则：27 条
- LLM 自动发现并合并：~453 条（标记为"待人工审核"）
- 总计：~480 条

---

## 详细任务清单

### 阶段 1：语音识别 ✅
- [x] 安装 Python 3.11 + uv 环境管理
- [x] 安装 PyTorch CUDA 12.6 + faster-whisper
- [x] GPU 加速验证（GTX 1660 Ti, float16）
- [x] 全量转录 107 集（large-v3, ~4.5小时）
- [x] 零失败，全部输出 .txt + _detail.json

### 阶段 2：LLM 后处理 ✅
- [x] 构建中医术语词典（方剂、穴位、脏腑、病证、经络等）
- [x] 编写 LLM 纠错脚本（`fix_terminology.py`）
- [x] 创建手动纠错反馈机制（`manual_corrections.json`）
- [x] 全量纠错 107 集（913 处修改，~70分钟）
- [x] LLM 自动学习新纠错规则

### 阶段 3：大纲生成 ✅
- [x] 更新 `generate_outline.py` 优先使用纠错版转录
- [x] 为 107 集逐一生成结构化 Markdown 大纲
- [ ] 生成完整课程知识体系（总大纲）

### 阶段 4：多课程支持 ✅
- [x] `course_config.json` 自动提取课程参数
- [x] `batch_download.py` 支持从配置文件加载（不再硬编码）
- [x] `get_cookies.py` 自动使用最新捕获文件
- [x] `scripts/extract_course_config.py` 从捕获数据自动提取 column_alias / kdt_id
- [x] `scripts/md_to_docx.py` 批量转 Word（大字版）
- [x] `run_pipeline.bat` 一键全流程

### 阶段 5：优化与扩展（可选）
- [ ] 人工审核 LLM 自动发现的纠错规则，提升质量
- [ ] 支持增量更新（新增视频自动处理）
- [ ] Web UI 展示课程大纲
- [ ] 导出为 PDF/Notion 格式

---

## 问题排查记录（2026-02-25）

### 问题 1：mitmproxy CA 证书生成失败

**现象**：运行 `start_capture.py` 时报 `[ERROR] CA 证书生成失败`

**根因**：`start_capture.py` 使用了错误的 mitmdump 调用方式：
```python
# 旧代码（mitmproxy <10 可用，11.x 不可用）
[sys.executable, "-m", "mitmproxy.tools.main", "mitmdump", ...]
```
mitmproxy 11 移除了 `mitmproxy.tools.main` 的统一入口，mitmdump 应直接作为命令调用或使用 `mitmproxy.tools.dump` 模块。

**修复**：
```python
# 新代码：优先使用 mitmdump 可执行文件，回退到 python -m
def _mitmdump_cmd():
    mitmdump = shutil.which("mitmdump")
    if mitmdump:
        return [mitmdump]
    return [sys.executable, "-m", "mitmproxy.tools.dump"]
```

**涉及文件**：`start_capture.py`

---

### 问题 2：mitmproxy 11 HTTP/2 头部校验导致 502 Bad Gateway

**现象**：代理启动后，微信中打开课程页面显示 `502 Bad Gateway`，日志大量报错：
```
HTTP/2 protocol error: Received header value surrounded by whitespace b'bj7-prod-httpgw11, '
```

**根因**：有赞（youzan.com）服务器返回的 HTTP/2 响应头中包含尾随空格（如 `bj7-prod-httpgw11, `），违反 HTTP/2 RFC 规范。mitmproxy 11 比旧版本更严格地校验 HTTP/2 头部，拒绝了这些响应并向客户端返回 502。

**排查过程**：
1. 初始怀疑是防嗅探机制，但分析日志发现 `mps-trans.yzcdn.cn`（视频 CDN）的 .ts 文件正常返回 200
2. 仅 `*.youzan.com` 的 API 请求失败
3. 错误信息 `Received header value surrounded by whitespace` 指向 HTTP/2 头部校验
4. 尝试 `--set upstream_http2=false`，但该选项在 mitmproxy 11 中不存在
5. 运行 `mitmdump --options | grep http2` 发现只有 `http2` 选项（控制全局 HTTP/2）
6. 使用 `--set http2=false` 强制所有连接使用 HTTP/1.1，测试通过

**修复**：在 `start_capture.py` 的 mitmdump 启动参数中添加 `--set http2=false`

**涉及文件**：`start_capture.py`

---

### 问题 3：batch_download.py 使用错误的 chapterId 导致返回空列表

**现象**：`batch_download.py` 从 API 获取课程列表返回 0 个项目

**根因**：`course_config.json` 中没有 `chapter_id`（新课程不需要），但代码的回退逻辑 `_cfg.get("chapter_id", "") or CHAPTER_ID` 导致使用了旧课程的 `CHAPTER_ID = "100611207"`，该 chapter_id 在新课程中无效。

**修复**：
1. 将回退逻辑改为 `_cfg.get("chapter_id", "")`（配置文件缺失时不使用默认值）
2. 在 API URL 构建中将 `chapterId` 参数改为条件拼接：
```python
+ (f"&chapterId={CHAPTER_ID}" if CHAPTER_ID else "")
```

**涉及文件**：`batch_download.py`

---

### 问题 4：mitmproxy 未安装在虚拟环境中

**现象**：`uv run python start_capture.py` 报 `ModuleNotFoundError: No module named 'mitmproxy'`

**根因**：项目 `.venv` 中未安装 mitmproxy。`requirements.txt` 中有 `mitmproxy>=10.0.0`，但用户之前可能是全局安装或手动安装的。

**修复**：`uv pip install mitmproxy`（安装了 v11.0.2）

---

### 问题 5：run_pipeline.bat 日志刷屏

**现象**：.bat 文件运行时 mitmproxy 日志疯狂刷屏，无法操作

**根因**：mitmdump 默认输出所有请求日志，有赞页面有大量轮询请求（probe.youzan.com、tj1.youzan.com 每秒多次）

**修复**：在直接运行时使用 `-q`（quiet）模式减少日志输出
