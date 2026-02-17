"""从捕获数据中提取完整的 Cookie"""

import json

with open("captured/capture_20260217_145959.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Find the fullest cookie from youzan requests
all_cookies = {}
for a in data["apis"]:
    headers = a.get("request_headers", {})
    cookie_str = headers.get("Cookie", "")
    if cookie_str and "youzan" in a.get("url", ""):
        # Parse cookie string
        for pair in cookie_str.split("; "):
            if "=" in pair:
                key, val = pair.split("=", 1)
                all_cookies[key] = val

# Save cookies
cookie_str = "; ".join(f"{k}={v}" for k, v in all_cookies.items())
print(f"Found {len(all_cookies)} cookies")
print(f"\nCookie string:\n{cookie_str}")

# Save to file
with open("cookies.txt", "w", encoding="utf-8") as f:
    f.write(cookie_str)

# Also save individual cookies
with open("cookies.json", "w", encoding="utf-8") as f:
    json.dump(all_cookies, f, ensure_ascii=False, indent=2)

print(f"\nSaved to cookies.txt and cookies.json")
