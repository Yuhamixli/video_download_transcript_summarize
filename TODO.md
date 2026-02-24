# TODO — wechat-course-dl

## 当前状态（2026-02-24）

- [x] 视频下载：107 集全部完成（4.03GB），存于 `downloads/`
- [x] 流量捕获：mitmproxy 代理链路已通，cookies 已提取
- [x] 语音识别：107/107 集已用 faster-whisper large-v3 GPU 加速转录
- [x] LLM 术语纠错：107/107 集已完成，共 913 处修改
- [x] 大纲提炼：107/107 集已生成结构化 Markdown 大纲
- [ ] 完整课程知识体系汇总：待生成（需运行 `generate_outline.py` 不带 `--no-summary`）
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

### 阶段 4：优化与扩展（可选）
- [ ] 人工审核 LLM 自动发现的纠错规则，提升质量
- [ ] 支持增量更新（新增视频自动处理）
- [ ] Web UI 展示课程大纲
- [ ] 导出为 PDF/Notion 格式
