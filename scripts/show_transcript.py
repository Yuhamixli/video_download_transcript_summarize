"""显示转录结果"""
import glob
import json
import os

transcript_dir = r"c:\Projects\wechat-course-dl\transcripts"

# 找 txt 文件
for f in sorted(glob.glob(os.path.join(transcript_dir, "*.txt"))):
    print(f"=== {os.path.basename(f)} ===")
    with open(f, "r", encoding="utf-8") as fh:
        text = fh.read()
    print(text)
    print(f"\n字数: {len(text)}")

# 找 detail json
for f in sorted(glob.glob(os.path.join(transcript_dir, "*_detail.json"))):
    print(f"\n=== 带时间戳版本 (前5段) ===")
    with open(f, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    for seg in data["segments"][:5]:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]
        print(f"  [{start:.1f}s - {end:.1f}s] {text}")
    print(f"  ... 共 {len(data['segments'])} 段")
