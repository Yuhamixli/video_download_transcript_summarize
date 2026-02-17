"""从 HTML 中提取和解码视频 URL"""

import re
from urllib.parse import unquote

with open("test_video_page.html", "r", encoding="utf-8") as f:
    html = f.read()

# 方法1: 查找 URL 编码的 videoUrl
pattern = r"videoUrl%22%3A%22(https%3A[^%]*(?:%[0-9A-Fa-f]{2}[^%]*)*?)%22"
matches = re.findall(pattern, html)
if matches:
    for m in matches:
        decoded = unquote(m)
        print(f"videoUrl: {decoded}")

# 方法2: 查找 URL 编码的 m3u8
pattern2 = r"(https%3A[^\"'\s]*?\.m3u8[^\"'\s]*?)(?:%22|[\"'\s])"
matches2 = re.findall(pattern2, html)
if matches2:
    for m in matches2:
        decoded = unquote(m)
        print(f"\nm3u8 URL: {decoded}")

# 方法3: 全量 URL decode 后搜索
decoded_html = unquote(html)
m3u8_urls = re.findall(r'(https?://[^"\s]+\.m3u8[^"\s]*)', decoded_html)
if m3u8_urls:
    print(f"\n解码后找到 m3u8 URL:")
    for u in m3u8_urls:
        # Clean up
        u = u.split('"')[0].split("'")[0]
        print(f"  {u}")

# 方法4: 找 videoContentDTO
dto_pattern = r'"videoContentDTO"\s*:\s*\{([^}]+)\}'
dto_matches = re.findall(dto_pattern, decoded_html)
if dto_matches:
    print(f"\nvideoContentDTO:")
    for m in dto_matches:
        print(f"  {m[:300]}")

# 方法5: 查找 decodeURIComponent 调用
decode_calls = re.findall(r'decodeURIComponent\("([^"]+)"\)', html)
if decode_calls:
    print(f"\nDecodeURIComponent 数据块:")
    for d in decode_calls[:3]:
        decoded = unquote(d[:500])
        # Look for video URL in decoded
        vid_urls = re.findall(r'(https?://[^"\s]+\.m3u8[^"\s]*)', decoded)
        if vid_urls:
            print(f"  Found m3u8: {vid_urls[0][:200]}")
        else:
            print(f"  Data preview: {decoded[:200]}")
