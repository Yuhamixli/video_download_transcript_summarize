"""
语音识别: 将视频课程转为文字讲义
使用 OpenAI Whisper (本地运行，无需 API key)
"""

import os
import sys
import json
import glob
import time

# 确保 ffmpeg 可用
ffmpeg_dir = os.path.join(os.path.dirname(sys.executable), "..", "Lib", "site-packages", "imageio_ffmpeg", "binaries")
if os.path.isdir(ffmpeg_dir):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import whisper

# 配置
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# Whisper 模型选择:
#   tiny   - 最快，精度较低 (~1GB VRAM)
#   base   - 快速，精度一般 (~1GB VRAM)
#   small  - 均衡，推荐 (~2GB VRAM)
#   medium - 较慢，精度高 (~5GB VRAM)
#   large  - 最慢，精度最高 (~10GB VRAM)
MODEL_NAME = "small"  # small 对台湾口音中文识别效果已很好，CPU 速度快 5 倍


def transcribe_video(model, video_path, output_path):
    """转录单个视频"""
    print(f"  转录中...")
    start_time = time.time()

    result = model.transcribe(
        video_path,
        language="zh",
        verbose=False,
        fp16=False,
        initial_prompt="以下是中医课程讲座内容，讲师为台湾口音。涉及阴阳、五行、脏腑、经络、气血、津液、病因、诊断等中医术语。",
    )

    elapsed = time.time() - start_time
    text = result["text"]

    # 保存纯文本
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    # 保存带时间戳的详细版本
    detail_path = output_path.replace(".txt", "_detail.json")
    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump({
            "text": text,
            "language": result.get("language", "zh"),
            "segments": segments,
        }, f, ensure_ascii=False, indent=2)

    char_count = len(text)
    print(f"  完成! {elapsed:.1f}秒, {char_count} 字")
    return text


def main():
    print("=" * 60)
    print(" 语音识别 - Whisper")
    print(f" 模型: {MODEL_NAME}")
    print("=" * 60)

    # 加载模型
    print(f"\n加载 Whisper {MODEL_NAME} 模型...")
    model = whisper.load_model(MODEL_NAME)
    print("模型加载完成")

    # 获取所有视频文件
    videos = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4")))
    if not videos:
        print(f"\n没有找到视频文件: {DOWNLOAD_DIR}")
        return

    print(f"\n共 {len(videos)} 个视频待转录")

    success = 0
    skip = 0

    for i, video_path in enumerate(videos):
        filename = os.path.basename(video_path)
        name = os.path.splitext(filename)[0]
        output_path = os.path.join(TRANSCRIPT_DIR, f"{name}.txt")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 10:
            print(f"\n[{i+1}/{len(videos)}] 跳过 (已存在): {name}")
            skip += 1
            continue

        print(f"\n[{i+1}/{len(videos)}] {name}")
        try:
            transcribe_video(model, video_path, output_path)
            success += 1
        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n{'=' * 60}")
    print(f" 转录完成!")
    print(f"   成功: {success}")
    print(f"   跳过: {skip}")
    print(f"   输出: {TRANSCRIPT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
