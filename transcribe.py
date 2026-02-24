"""
语音识别: 将视频课程转为文字讲义
使用 faster-whisper (CTranslate2) 实现 GPU 加速转录
支持自动 GPU/CPU 检测，优先使用 CUDA 加速
"""

import os
import sys
import json
import glob
import time
import argparse
import logging
import traceback
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 确保 ffmpeg 可用 (imageio-ffmpeg 内置)
ffmpeg_dir = os.path.join(
    os.path.dirname(sys.executable), "..", "Lib", "site-packages", "imageio_ffmpeg", "binaries"
)
if os.path.isdir(ffmpeg_dir):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

from faster_whisper import WhisperModel

# ============ 配置 ============
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), "transcripts")
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# Whisper 模型选择:
#   tiny     - 最快，精度低     (~1GB VRAM)
#   base     - 快速，精度一般   (~1GB VRAM)
#   small    - 均衡            (~2GB VRAM)
#   medium   - 较慢，精度高     (~5GB VRAM)
#   large-v3 - 最慢，精度最高   (~3-4GB VRAM with float16, 推荐 GPU)
MODEL_NAME = "large-v3"

# GPU 配置
# GTX 1660 Ti (6GB VRAM) 可以运行 large-v3 with float16
DEVICE = "auto"  # auto / cuda / cpu
COMPUTE_TYPE = "float16"  # float16 (GPU推荐) / int8 (节省VRAM) / float32 (CPU回退)

# 中医术语提示词 - 帮助模型识别专业术语
INITIAL_PROMPT = (
    "以下是中医课程讲座内容，讲师为台湾口音。涉及阴阳五行、脏腑经络、气血津液、"
    "病因病机、辨证论治、方剂学、针灸穴位等中医基础理论。"
    "常见术语：脉诊、舌诊、望闻问切、肝肾阴虚、脾胃虚弱、气滞血瘀、"
    "六经辨证、卫气营血、三焦、命门、丹田、任督二脉、寸关尺、"
    "桂枝汤、麻黄汤、小柴胡汤、四逆汤、理中汤、补中益气汤、"
    "足三里、合谷、太冲、百会、关元、气海。"
)


def detect_device():
    """自动检测最优运算设备"""
    if DEVICE != "auto":
        return DEVICE, COMPUTE_TYPE

    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types("cuda")
        if "float16" in supported:
            log.info("检测到 CUDA GPU，使用 float16 加速")
            return "cuda", "float16"
        elif "int8" in supported:
            log.info("检测到 CUDA GPU，使用 int8 加速")
            return "cuda", "int8"
    except Exception:
        pass

    log.info("未检测到 GPU，使用 CPU (float32)")
    return "cpu", "float32"


def load_model(model_name, device, compute_type):
    """加载 Whisper 模型"""
    log.info(f"加载模型: {model_name} (device={device}, compute={compute_type})")
    t0 = time.time()
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    log.info(f"模型加载完成 ({time.time() - t0:.1f}秒)")
    return model


def transcribe_video(model, video_path, output_path):
    """转录单个视频，输出纯文本和带时间戳的 JSON"""
    start_time = time.time()

    segments_iter, info = model.transcribe(
        video_path,
        language="zh",
        initial_prompt=INITIAL_PROMPT,
        vad_filter=True,  # 过滤静音段，提升速度和质量
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
        beam_size=5,
        best_of=5,
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        condition_on_previous_text=True,
    )

    # 收集所有段落
    segments = []
    full_text_parts = []
    for seg in segments_iter:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text_parts.append(seg.text.strip())

    full_text = "".join(full_text_parts)
    elapsed = time.time() - start_time
    duration = info.duration
    speed_ratio = duration / elapsed if elapsed > 0 else 0

    # 保存纯文本
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    # 保存带时间戳的详细 JSON
    detail_path = output_path.replace(".txt", "_detail.json")
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump({
            "text": full_text,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration": round(duration, 2),
            "transcribe_time": round(elapsed, 2),
            "speed_ratio": round(speed_ratio, 1),
            "segments": segments,
        }, f, ensure_ascii=False, indent=2)

    log.info(
        f"  完成! {elapsed:.1f}秒 (音频{duration:.0f}秒, {speed_ratio:.1f}x实时), "
        f"{len(full_text)}字, {len(segments)}段"
    )
    return full_text


def main():
    parser = argparse.ArgumentParser(description="视频课程语音识别 (faster-whisper GPU 加速)")
    parser.add_argument("--model", default=MODEL_NAME, help=f"Whisper 模型 (默认: {MODEL_NAME})")
    parser.add_argument("--device", default=DEVICE, choices=["auto", "cuda", "cpu"], help="运算设备")
    parser.add_argument("--compute-type", default=COMPUTE_TYPE, help="计算精度 (float16/int8/float32)")
    parser.add_argument("--force", action="store_true", help="强制重新转录已存在的文件")
    parser.add_argument("--file", help="只转录指定文件 (文件名或路径)")
    args = parser.parse_args()

    device, compute_type = detect_device() if args.device == "auto" else (args.device, args.compute_type)

    print("=" * 60)
    print(" 语音识别 - faster-whisper (GPU 加速)")
    print(f" 模型: {args.model}")
    print(f" 设备: {device} ({compute_type})")
    print("=" * 60)

    model = load_model(args.model, device, compute_type)

    # 获取视频列表
    if args.file:
        if os.path.isabs(args.file):
            videos = [args.file]
        else:
            videos = [os.path.join(DOWNLOAD_DIR, args.file)]
        if not os.path.exists(videos[0]):
            pattern = os.path.join(DOWNLOAD_DIR, f"*{args.file}*")
            videos = sorted(glob.glob(pattern))
    else:
        videos = sorted(glob.glob(os.path.join(DOWNLOAD_DIR, "*.mp4")))

    if not videos:
        print(f"\n没有找到视频文件: {DOWNLOAD_DIR}")
        return

    print(f"\n共 {len(videos)} 个视频待处理")

    success = 0
    skip = 0
    errors = 0
    failed_files = []
    results = []
    total_start = time.time()

    for i, video_path in enumerate(videos):
        filename = os.path.basename(video_path)
        name = os.path.splitext(filename)[0]
        output_path = os.path.join(TRANSCRIPT_DIR, f"{name}.txt")

        if not args.force and os.path.exists(output_path) and os.path.getsize(output_path) > 10:
            log.info(f"[{i+1}/{len(videos)}] 跳过 (已存在): {name}")
            skip += 1
            results.append({"file": filename, "status": "skipped"})
            continue

        log.info(f"[{i+1}/{len(videos)}] 转录: {name}")
        try:
            text = transcribe_video(model, video_path, output_path)
            success += 1
            results.append({
                "file": filename,
                "status": "success",
                "chars": len(text),
            })
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            log.error(f"  转录失败: {err_msg}")
            log.debug(traceback.format_exc())
            errors += 1
            failed_files.append({"file": filename, "error": err_msg})
            results.append({"file": filename, "status": "failed", "error": err_msg})

    total_elapsed = time.time() - total_start

    # 保存运行报告 (含失败列表，便于重跑)
    report_path = os.path.join(os.path.dirname(__file__), "transcribe_report.json")
    report = {
        "run_time": datetime.now().isoformat(),
        "model": args.model,
        "device": device,
        "compute_type": compute_type,
        "total_videos": len(videos),
        "success": success,
        "skipped": skip,
        "failed": errors,
        "total_seconds": round(total_elapsed, 1),
        "failed_files": failed_files,
        "results": results,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f" 转录完成! 总耗时: {total_elapsed/3600:.1f}小时 ({total_elapsed:.0f}秒)")
    print(f"   成功: {success}")
    print(f"   跳过: {skip}")
    print(f"   失败: {errors}")
    if failed_files:
        print(f"\n   ❌ 失败文件:")
        for f_item in failed_files:
            print(f"      - {f_item['file']}: {f_item['error']}")
    print(f"\n   报告: {report_path}")
    print(f"   输出: {TRANSCRIPT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
