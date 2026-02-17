"""测试 API 连接和课程列表获取"""

import json
import time
import requests
import re

COLUMN_ALIAS = "2oqezgma011w4g9"
KDT_ID = "42145140"
CHAPTER_ID = "100611207"
BASE_URL = "https://shop42337308.youzan.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254162e) XWEB/18163 Flue",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"https://shop42337308.youzan.com/wscvis/course/detail/{COLUMN_ALIAS}?kdt_id={KDT_ID}",
}

with open("cookies.txt", "r") as f:
    cookie = f.read().strip()
HEADERS["Cookie"] = cookie

session = requests.Session()
session.headers.update(HEADERS)

# Test 1: 获取课程列表
print("=" * 60)
print("Test 1: 获取课程列表 (第1页)")
print("=" * 60)

url = (
    f"{BASE_URL}/wscvis/knowledge/contentAndLive.json"
    f"?columnAlias={COLUMN_ALIAS}"
    f"&pageNumber=1&sortType=asc&chapterId={CHAPTER_ID}"
    f"&goodsType=1&kdt_id={KDT_ID}"
    f"&t_vis_get={int(time.time() * 1000)}"
)

resp = session.get(url)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Code: {data.get('code')}")

content = data.get("data", {}).get("content", [])
total_pages = data.get("data", {}).get("totalPages", 0)
print(f"Items on page 1: {len(content)}")
print(f"Total pages: {total_pages}")

for item in content[:5]:
    alias = item.get("alias", "")
    title = item.get("title", "?")
    serial = item.get("columnContentDTO", {}).get("columnSerialNo", 0)
    media = item.get("mediaType", 0)
    print(f"  [{serial:03d}] {title} (alias={alias}, mediaType={media})")

# Test 2: 获取视频详情页面
if content:
    first = content[0]
    alias = first["alias"]
    title = first.get("title", "?")

    print(f"\n{'=' * 60}")
    print(f"Test 2: 获取视频页面 - {title}")
    print(f"{'=' * 60}")

    page_url = f"{BASE_URL}/wscvis/course/detail/{alias}?kdt_id={KDT_ID}&fromColumn={COLUMN_ALIAS}"
    page_headers = dict(HEADERS)
    page_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

    resp2 = session.get(page_url, headers=page_headers)
    print(f"Status: {resp2.status_code}")
    print(f"Content-Length: {len(resp2.text)}")

    html = resp2.text

    # 查找视频 URL
    patterns = [
        (r'(https?://[^"\'\s\\]+\.m3u8[^"\'\s\\]*)', "m3u8 URL"),
        (r'(https?://mps-video\.yzcdn\.cn/[^"\'\s\\]+)', "mps-video URL"),
        (r'"(https?://[^"]*yzcdn\.cn/[^"]*\.mp4[^"]*)"', "yzcdn mp4 URL"),
        (r'"video_url"\s*:\s*"([^"]+)"', "video_url field"),
        (r'"videoUrl"\s*:\s*"([^"]+)"', "videoUrl field"),
        (r'"playUrl"\s*:\s*"([^"]+)"', "playUrl field"),
        (r'"url"\s*:\s*"(https?://[^"]*(?:m3u8|mp4|video)[^"]*)"', "url with video"),
    ]

    found = False
    for pattern, name in patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"\n  Found ({name}):")
            for m in matches[:3]:
                clean = m.replace("\\u002F", "/").replace("\\/", "/")
                print(f"    {clean[:150]}")
            found = True

    if not found:
        print("\n  未直接找到视频 URL，检查页面中的关键数据...")
        # 查找 JSON 数据块
        json_blocks = re.findall(r'window\.\w+\s*=\s*({.+?});?\s*</script>', html, re.DOTALL)
        for i, block in enumerate(json_blocks[:3]):
            print(f"\n  JSON Block {i+1} (前500字): {block[:500]}")

        # 查找任何含 video 的字段
        video_refs = re.findall(r'"[^"]*video[^"]*"\s*:\s*"([^"]+)"', html, re.IGNORECASE)
        if video_refs:
            print(f"\n  含 'video' 的字段:")
            for v in video_refs[:5]:
                print(f"    {v[:150]}")

        # 查找含 media/play 的字段
        media_refs = re.findall(r'"[^"]*(?:media|play|hls|stream)[^"]*"\s*:\s*"([^"]+)"', html, re.IGNORECASE)
        if media_refs:
            print(f"\n  含 'media/play/hls' 的字段:")
            for v in media_refs[:5]:
                print(f"    {v[:150]}")

    # 保存 HTML 供分析
    with open("test_video_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  页面已保存到 test_video_page.html ({len(html)} bytes)")
