"""分析捕获的数据，提取视频 URL 和课程 API 结构"""

import json
import os
import glob

CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "captured")

def analyze():
    files = sorted(glob.glob(os.path.join(CAPTURE_DIR, "capture_*.json")))
    if not files:
        print("没有找到捕获文件")
        return

    latest = files[-1]
    print(f"分析文件: {latest}")

    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n视频数量: {data['video_count']}")
    print(f"API数量: {data['api_count']}")

    print("\n" + "=" * 60)
    print("捕获到的视频:")
    print("=" * 60)
    for i, v in enumerate(data.get("videos", []), 1):
        url = v.get("url", "")
        ct = v.get("content_type", "")
        size = v.get("content_length", "?")
        print(f"\n[{i}] {url[:150]}")
        print(f"    Content-Type: {ct}")
        print(f"    Size: {size}")

    print("\n" + "=" * 60)
    print("捕获到的 API (含视频引用):")
    print("=" * 60)
    for i, a in enumerate(data.get("apis", []), 1):
        url = a.get("url", "")
        method = a.get("method", "")
        has_video = a.get("has_video_ref", False)
        print(f"\n[{i}] [{method}] {url[:200]}")
        print(f"    含视频引用: {has_video}")

        body = a.get("response_body", "")
        if body and has_video:
            print(f"    响应摘要: {body[:500]}")

        if not has_video and body:
            print(f"    响应摘要: {body[:200]}")

def analyze_all_requests():
    """分析所有请求，查找 m3u8 和关键 API"""
    files = sorted(glob.glob(os.path.join(CAPTURE_DIR, "all_requests_*.json")))
    if not files:
        print("\n没有找到全量请求文件 (需要停止代理后生成)")
        return

    latest = files[-1]
    print(f"\n分析全量请求: {latest}")

    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 找 youzan 相关请求
    youzan_requests = [r for r in data if "youzan" in r.get("url", "") or "yzcdn" in r.get("url", "")]
    print(f"\n有赞相关请求: {len(youzan_requests)}")
    for r in youzan_requests:
        url = r.get("url", "")
        method = r.get("method", "")
        if "m3u8" in url or "course" in url or "video" in url:
            print(f"  [{method}] {url[:200]}")

if __name__ == "__main__":
    analyze()
    analyze_all_requests()
