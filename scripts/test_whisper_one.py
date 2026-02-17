"""测试 Whisper 识别一集 - 台湾口音中文"""

import os
import glob
import time
import whisper

DOWNLOAD_DIR = r"c:\Projects\wechat-course-dl\downloads"
TRANSCRIPT_DIR = r"c:\Projects\wechat-course-dl\transcripts"
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# 找第一集 (序号最大的是 108，文件名排序后最小序号的 mp4)
videos = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4")))

# 找一个短的视频测试 (001 阴阳 约 2:58)
test_video = None
for v in videos:
    name = os.path.basename(v)
    if "001" in name:
        test_video = v
        break

if not test_video:
    # 用最小的文件
    videos_with_size = [(v, os.path.getsize(v)) for v in videos]
    videos_with_size.sort(key=lambda x: x[1])
    test_video = videos_with_size[0][0]

name = os.path.basename(test_video)
size_mb = os.path.getsize(test_video) / 1024 / 1024

print(f"测试视频: {name}")
print(f"文件大小: {size_mb:.1f}MB")

# 使用 small 模型 (CPU 上速度合理，中文识别质量不错)
# 台湾口音中文设置 language="zh" 即可
MODEL = "small"
print(f"\n加载 Whisper {MODEL} 模型...")
t0 = time.time()
model = whisper.load_model(MODEL)
print(f"模型加载: {time.time()-t0:.1f}秒")

print(f"\n开始转录...")
t1 = time.time()
result = model.transcribe(
    test_video,
    language="zh",       # 指定中文
    verbose=False,
    fp16=False,          # CPU 模式
    initial_prompt="以下是中医课程讲座内容，讲师为台湾口音。",  # 提示词帮助识别
)
elapsed = time.time() - t1

text = result["text"]
print(f"\n转录完成! 耗时: {elapsed:.1f}秒")
print(f"识别文字: {len(text)} 字")
print(f"\n{'='*60}")
print("转录结果预览 (前 1000 字):")
print("=" * 60)
print(text[:1000])
print("=" * 60)

# 保存
out_name = os.path.splitext(name)[0]
out_path = os.path.join(TRANSCRIPT_DIR, f"{out_name}.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

# 保存带时间戳的版本
import json
segments = []
for seg in result["segments"]:
    segments.append({
        "start": round(seg["start"], 2),
        "end": round(seg["end"], 2),
        "text": seg["text"].strip(),
    })
detail_path = os.path.join(TRANSCRIPT_DIR, f"{out_name}_detail.json")
with open(detail_path, "w", encoding="utf-8") as f:
    json.dump({"text": text, "segments": segments}, f, ensure_ascii=False, indent=2)

print(f"\n保存到: {out_path}")
print(f"详细版: {detail_path}")
