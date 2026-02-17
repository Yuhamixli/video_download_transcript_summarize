"""测试 faster-whisper GPU 加速识别一集 - 台湾口音中文"""

import os
import sys
import glob
import time
import json

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DOWNLOAD_DIR = os.path.join(ROOT_DIR, "downloads")
TRANSCRIPT_DIR = os.path.join(ROOT_DIR, "transcripts")
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

from faster_whisper import WhisperModel

# 找视频文件
videos = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4")))
if not videos:
    print(f"没有找到视频文件: {DOWNLOAD_DIR}")
    sys.exit(1)

# 找一个短的视频测试 (优先 001)
test_video = None
for v in videos:
    if "001" in os.path.basename(v):
        test_video = v
        break

if not test_video:
    videos_with_size = [(v, os.path.getsize(v)) for v in videos]
    videos_with_size.sort(key=lambda x: x[1])
    test_video = videos_with_size[0][0]

name = os.path.basename(test_video)
size_mb = os.path.getsize(test_video) / 1024 / 1024

print(f"测试视频: {name}")
print(f"文件大小: {size_mb:.1f}MB")

# 加载模型 (GPU 加速)
MODEL = "large-v3"
DEVICE = "cuda"
COMPUTE_TYPE = "float16"

print(f"\n加载 faster-whisper {MODEL} 模型 (device={DEVICE}, compute={COMPUTE_TYPE})...")
t0 = time.time()
model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE_TYPE)
print(f"模型加载: {time.time() - t0:.1f}秒")

# 转录
print(f"\n开始转录...")
t1 = time.time()
segments_iter, info = model.transcribe(
    test_video,
    language="zh",
    initial_prompt="以下是中医课程讲座内容，讲师为台湾口音。涉及阴阳五行、脏腑经络、气血津液、辨证论治。",
    vad_filter=True,
    beam_size=5,
)

segments = []
text_parts = []
for seg in segments_iter:
    segments.append({
        "start": round(seg.start, 2),
        "end": round(seg.end, 2),
        "text": seg.text.strip(),
    })
    text_parts.append(seg.text.strip())

text = "".join(text_parts)
elapsed = time.time() - t1
speed = info.duration / elapsed if elapsed > 0 else 0

print(f"\n转录完成! 耗时: {elapsed:.1f}秒 (音频: {info.duration:.0f}秒, {speed:.1f}x 实时)")
print(f"识别文字: {len(text)} 字, {len(segments)} 段")
print(f"\n{'=' * 60}")
print("转录结果预览 (前 1000 字):")
print("=" * 60)
print(text[:1000])
print("=" * 60)

# 保存
out_name = os.path.splitext(name)[0]
out_path = os.path.join(TRANSCRIPT_DIR, f"{out_name}.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

detail_path = os.path.join(TRANSCRIPT_DIR, f"{out_name}_detail.json")
with open(detail_path, "w", encoding="utf-8") as f:
    json.dump({
        "text": text,
        "language": info.language,
        "duration": round(info.duration, 2),
        "transcribe_time": round(elapsed, 2),
        "speed_ratio": round(speed, 1),
        "segments": segments,
    }, f, ensure_ascii=False, indent=2)

print(f"\n保存到: {out_path}")
print(f"详细版: {detail_path}")
