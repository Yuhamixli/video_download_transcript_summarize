"""提取和分析课程 API 结构"""

import json

with open("captured/capture_20260217_145959.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 60)
print("关键 API 分析")
print("=" * 60)

for a in data["apis"]:
    url = a.get("url", "")
    body_str = a.get("response_body", "")

    # 跳过进度上报和非关键 API
    if "reportViewProcess" in url or "probe.youzan" in url:
        continue
    if "tj1.youzan" in url:
        continue

    print(f"\nAPI: {url[:250]}")

    if body_str:
        try:
            resp = json.loads(body_str)
            # 格式化输出
            formatted = json.dumps(resp, ensure_ascii=False, indent=2)
            # 只打印前 2000 字符
            if len(formatted) > 2000:
                print(f"Response (truncated): {formatted[:2000]}...")
            else:
                print(f"Response: {formatted}")
        except:
            print(f"Raw: {body_str[:500]}")

print("\n" + "=" * 60)
print("视频 m3u8 URL:")
print("=" * 60)
for v in data["videos"]:
    if ".m3u8" in v["url"]:
        print(f"  {v['url'][:200]}")

print("\n" + "=" * 60)
print("Request headers from video request:")
print("=" * 60)
for v in data["videos"][:1]:
    headers = v.get("request_headers", {})
    for k, v2 in headers.items():
        if k.lower() in ("cookie", "referer", "origin", "user-agent", "authorization"):
            print(f"  {k}: {v2[:200]}")
