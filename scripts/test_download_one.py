"""测试下载单个视频"""

import json
import os
import re
import time
import requests
import shutil
from urllib.parse import unquote, urljoin

COLUMN_ALIAS = "2oqezgma011w4g9"
KDT_ID = "42145140"
CHAPTER_ID = "100611207"
BASE_URL = "https://shop42337308.youzan.com"
SAVE_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(SAVE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254162e) XWEB/18163 Flue",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{BASE_URL}/wscvis/course/detail/{COLUMN_ALIAS}?kdt_id={KDT_ID}",
    "Origin": BASE_URL,
}

with open("cookies.txt", "r") as f:
    cookie = f.read().strip()
HEADERS["Cookie"] = cookie

session = requests.Session()
session.headers.update(HEADERS)

# Step 1: 获取课程列表第一页
print("[Step 1] 获取课程列表...")
url = (
    f"{BASE_URL}/wscvis/knowledge/contentAndLive.json"
    f"?columnAlias={COLUMN_ALIAS}&pageNumber=1&sortType=asc"
    f"&chapterId={CHAPTER_ID}&goodsType=1&kdt_id={KDT_ID}"
    f"&t_vis_get={int(time.time() * 1000)}"
)
resp = session.get(url)
data = resp.json()
items = data.get("data", {}).get("content", [])
print(f"  获取到 {len(items)} 个")

# 取第一个视频
first = items[0]
alias = first["alias"]
title = first.get("title", "test")
serial = first.get("columnContentDTO", {}).get("columnSerialNo", 0)
print(f"  测试视频: [{serial}] {title} (alias={alias})")

# Step 2: 获取视频页面，提取 m3u8 URL
print(f"\n[Step 2] 获取视频页面...")
page_url = f"{BASE_URL}/wscvis/course/detail/{alias}?kdt_id={KDT_ID}&fromColumn={COLUMN_ALIAS}"
page_headers = dict(HEADERS)
page_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
resp2 = session.get(page_url, headers=page_headers)
html = resp2.text
print(f"  页面大小: {len(html)} bytes")

# 提取 videoUrl
pattern = r"videoUrl%22%3A%22(https%3A[^%]*(?:%[0-9A-Fa-f]{2}[^%]*)*?)%22"
matches = re.findall(pattern, html)
if not matches:
    decoded_html = unquote(html)
    m3u8_matches = re.findall(r'(https?://[^"\s]+\.m3u8[^"\s]*)', decoded_html)
    if m3u8_matches:
        m3u8_url = m3u8_matches[0].split('"')[0]
    else:
        print("  [FAIL] 无法提取视频 URL!")
        exit(1)
else:
    m3u8_url = unquote(matches[0])

print(f"  m3u8 URL: {m3u8_url[:100]}...")

# Step 3: 下载 m3u8 播放列表
print(f"\n[Step 3] 下载 m3u8 播放列表...")
dl_headers = {
    "User-Agent": HEADERS["User-Agent"],
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}
resp3 = session.get(m3u8_url, headers=dl_headers)
m3u8_content = resp3.text
print(f"  m3u8 内容:\n{m3u8_content[:500]}")

# 解析 ts 片段
ts_urls = []
for line in m3u8_content.strip().split("\n"):
    line = line.strip()
    if line and not line.startswith("#"):
        if line.startswith("http"):
            ts_urls.append(line)
        else:
            ts_urls.append(urljoin(m3u8_url, line))

print(f"\n  共 {len(ts_urls)} 个 ts 片段")

# Step 4: 下载所有 ts 片段并合并
filename = re.sub(r'[<>:"/\\|?*]', '', f"{serial:03d}_{title}")[:80]
output_path = os.path.join(SAVE_DIR, f"{filename}.mp4")
ts_dir = output_path + "_ts"
os.makedirs(ts_dir, exist_ok=True)

print(f"\n[Step 4] 下载 ts 片段...")
for i, ts_url in enumerate(ts_urls):
    ts_file = os.path.join(ts_dir, f"{i:04d}.ts")
    for retry in range(3):
        try:
            ts_resp = session.get(ts_url, headers=dl_headers, timeout=30)
            if ts_resp.status_code == 200:
                with open(ts_file, "wb") as f:
                    f.write(ts_resp.content)
                break
        except Exception as e:
            if retry == 2:
                print(f"  [WARN] 片段 {i} 失败: {e}")
            time.sleep(1)

    pct = (i + 1) / len(ts_urls) * 100
    size = os.path.getsize(ts_file) if os.path.exists(ts_file) else 0
    print(f"  [{i+1}/{len(ts_urls)}] {pct:.0f}% - {size/1024:.0f}KB")

# Step 5: 合并
print(f"\n[Step 5] 合并为 MP4...")
with open(output_path, "wb") as outf:
    for i in range(len(ts_urls)):
        ts_file = os.path.join(ts_dir, f"{i:04d}.ts")
        if os.path.exists(ts_file):
            with open(ts_file, "rb") as inf:
                outf.write(inf.read())

shutil.rmtree(ts_dir, ignore_errors=True)

size_mb = os.path.getsize(output_path) / 1024 / 1024
print(f"\n[OK] 下载完成: {output_path}")
print(f"     大小: {size_mb:.1f}MB")
