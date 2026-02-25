"""
批量下载有赞课程视频
流程: 获取课程列表 → 获取每个视频页面 → 提取 m3u8 → 下载 HLS 流 → 合并为 MP4
"""

import json
import os
import re
import sys
import time
import hashlib
import requests
from urllib.parse import urljoin, quote
from concurrent.futures import ThreadPoolExecutor

# ============ 配置 ============
# Defaults (overridden by course_config.json if present)
COLUMN_ALIAS = "2oqezgma011w4g9"  # 课程 ID
KDT_ID = "42145140"               # 店铺 ID
CHAPTER_ID = "100611207"          # 章节 ID
PAGE_SIZE = 10                     # 每页数量 (有赞默认)
BASE_URL = "https://shop42337308.youzan.com"

# Load from course_config.json if available
_config_path = os.path.join(os.path.dirname(__file__), "course_config.json")
if os.path.exists(_config_path):
    with open(_config_path, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
    COLUMN_ALIAS = _cfg.get("column_alias", COLUMN_ALIAS)
    KDT_ID = _cfg.get("kdt_id", KDT_ID)
    CHAPTER_ID = _cfg.get("chapter_id", CHAPTER_ID)
    BASE_URL = _cfg.get("base_url", BASE_URL)
    print(f"[config] Loaded course_config.json: alias={COLUMN_ALIAS}, kdt={KDT_ID}")

SAVE_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(SAVE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254162e) XWEB/18163 Flue",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{BASE_URL}/wscvis/course/detail/{COLUMN_ALIAS}?kdt_id={KDT_ID}",
    "Origin": BASE_URL,
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 加载 Cookie
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")


def load_cookies():
    """加载 Cookie"""
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def get_session():
    """创建带 Cookie 的 requests session"""
    session = requests.Session()
    session.headers.update(HEADERS)
    cookie_str = load_cookies()
    if cookie_str:
        session.headers["Cookie"] = cookie_str
    return session


def get_course_list(session):
    """获取完整课程内容列表 (分页)"""
    all_items = []
    page = 1

    while True:
        url = (
            f"{BASE_URL}/wscvis/knowledge/contentAndLive.json"
            f"?columnAlias={COLUMN_ALIAS}"
            f"&pageNumber={page}"
            f"&sortType=asc"
            f"&chapterId={CHAPTER_ID}"
            f"&goodsType=1"
            f"&kdt_id={KDT_ID}"
            f"&t_vis_get={int(time.time() * 1000)}"
        )

        print(f"获取课程列表 第 {page} 页...")
        resp = session.get(url)
        data = resp.json()

        if data.get("code") != 0:
            print(f"  API 错误: {data}")
            break

        content = data.get("data", {}).get("content", [])
        if not content:
            break

        for item in content:
            serial_no = item.get("columnContentDTO", {}).get("columnSerialNo", 0)
            title = item.get("title", "未知标题")
            all_items.append({
                "alias": item.get("alias", ""),
                "title": title,
                "cover": item.get("cover", ""),
                "mediaType": item.get("mediaType", 0),
                "summary": item.get("summary", ""),
                "serialNo": serial_no,
                "goodsId": item.get("goodsId", 0),
            })

        total_pages = data.get("data", {}).get("totalPages", 1)
        print(f"  获取到 {len(content)} 个, 共 {total_pages} 页")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)

    # 按序号排序
    all_items.sort(key=lambda x: x.get("serialNo", 0), reverse=True)
    return all_items


def get_video_page(session, alias):
    """获取视频详情页 HTML，提取 m3u8 URL"""
    url = f"{BASE_URL}/wscvis/course/detail/{alias}?kdt_id={KDT_ID}&fromColumn={COLUMN_ALIAS}"
    headers = dict(HEADERS)
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    headers["Referer"] = f"{BASE_URL}/wscvis/course/detail/{COLUMN_ALIAS}?kdt_id={KDT_ID}"

    resp = session.get(url, headers=headers)
    html = resp.text

    # 方法1: 从 URL 编码的 JSON 中提取 videoUrl (有赞特有格式)
    from urllib.parse import unquote
    pattern = r"videoUrl%22%3A%22(https%3A[^%]*(?:%[0-9A-Fa-f]{2}[^%]*)*?)%22"
    matches = re.findall(pattern, html)
    if matches:
        return unquote(matches[0])

    # 方法2: URL decode 整个页面后搜索 m3u8
    decoded_html = unquote(html)
    m3u8_matches = re.findall(r'(https?://[^"\s]+\.m3u8[^"\s]*)', decoded_html)
    if m3u8_matches:
        return m3u8_matches[0].split('"')[0].split("'")[0]

    # 方法3: 直接匹配 m3u8 URL
    m3u8_patterns = [
        r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)',
        r'"videoUrl"\s*:\s*"(https?://[^"]+)"',
        r'"playUrl"\s*:\s*"(https?://[^"]+)"',
        r'"(https?://mps-(?:video|trans)\.yzcdn\.cn/[^"]+)"',
    ]

    for p in m3u8_patterns:
        matches = re.findall(p, html)
        if matches:
            return matches[0].replace("\\u002F", "/").replace("\\/", "/")

    return None


def find_video_url(obj, depth=0):
    """递归在 JSON 中查找视频 URL"""
    if depth > 10:
        return None

    if isinstance(obj, str):
        if ".m3u8" in obj or ("mps-video" in obj and ".mp4" in obj):
            return obj.replace("\\u002F", "/").replace("\\/", "/")
        return None

    if isinstance(obj, dict):
        for key in ["url", "video_url", "videoUrl", "playUrl", "play_url",
                     "src", "media_url", "mediaUrl", "hlsUrl", "hls_url"]:
            if key in obj:
                val = obj[key]
                if isinstance(val, str) and ("m3u8" in val or "mps-video" in val or "yzcdn" in val):
                    return val.replace("\\u002F", "/").replace("\\/", "/")

        for v in obj.values():
            result = find_video_url(v, depth + 1)
            if result:
                return result

    if isinstance(obj, list):
        for item in obj:
            result = find_video_url(item, depth + 1)
            if result:
                return result

    return None


def download_m3u8(session, m3u8_url, output_path, title):
    """下载 HLS 流并合并为单个文件"""
    print(f"  下载 m3u8: {m3u8_url[:80]}...")

    headers = dict(HEADERS)
    headers["Referer"] = f"{BASE_URL}/"

    # 下载 m3u8 播放列表
    resp = session.get(m3u8_url, headers=headers)
    m3u8_content = resp.text

    if not m3u8_content.strip():
        print(f"  [ERROR] m3u8 内容为空")
        return False

    # 解析 m3u8，获取 ts 片段 URL
    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
    ts_urls = []
    for line in m3u8_content.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            if line.startswith("http"):
                ts_urls.append(line)
            else:
                ts_urls.append(urljoin(m3u8_url, line))

    if not ts_urls:
        # 可能是多码率 m3u8，需要选择一个
        for line in m3u8_content.strip().split("\n"):
            line = line.strip()
            if line.endswith(".m3u8"):
                sub_m3u8 = urljoin(m3u8_url, line)
                print(f"  发现子播放列表: {sub_m3u8[:80]}...")
                return download_m3u8(session, sub_m3u8, output_path, title)
        print(f"  [ERROR] m3u8 中没有 ts 片段")
        print(f"  m3u8 内容: {m3u8_content[:500]}")
        return False

    print(f"  共 {len(ts_urls)} 个片段")

    # 下载所有 ts 片段并合并
    ts_dir = output_path + "_ts"
    os.makedirs(ts_dir, exist_ok=True)

    for i, ts_url in enumerate(ts_urls):
        ts_file = os.path.join(ts_dir, f"{i:04d}.ts")
        if os.path.exists(ts_file) and os.path.getsize(ts_file) > 0:
            continue

        for retry in range(3):
            try:
                ts_resp = session.get(ts_url, headers=headers, timeout=30)
                if ts_resp.status_code == 200:
                    with open(ts_file, "wb") as f:
                        f.write(ts_resp.content)
                    break
            except Exception as e:
                if retry == 2:
                    print(f"    [WARN] 片段 {i} 下载失败: {e}")
                time.sleep(1)

        progress = (i + 1) / len(ts_urls) * 100
        print(f"\r  下载进度: {progress:.0f}% ({i + 1}/{len(ts_urls)})", end="", flush=True)

    print()

    # 合并 ts 片段为 mp4
    print(f"  合并片段...")
    with open(output_path, "wb") as outf:
        for i in range(len(ts_urls)):
            ts_file = os.path.join(ts_dir, f"{i:04d}.ts")
            if os.path.exists(ts_file):
                with open(ts_file, "rb") as inf:
                    outf.write(inf.read())

    # 清理 ts 临时文件
    import shutil
    shutil.rmtree(ts_dir, ignore_errors=True)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  [OK] 保存: {output_path} ({size_mb:.1f}MB)")
    return True


def clean_filename(name, max_len=80):
    """清理文件名"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()
    if len(name) > max_len:
        name = name[:max_len]
    return name


def main():
    print("=" * 60)
    print(" 有赞课程视频批量下载器")
    print("=" * 60)

    session = get_session()

    # Step 1: 获取课程列表
    print("\n[Step 1] 获取课程列表...")
    items = get_course_list(session)
    print(f"\n共获取 {len(items)} 个课程内容")

    # 保存课程列表
    with open(os.path.join(SAVE_DIR, "course_list.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # 显示前几个
    for i, item in enumerate(items[:5]):
        print(f"  [{item.get('serialNo', i+1):03d}] {item['title']}")
    if len(items) > 5:
        print(f"  ... 共 {len(items)} 个")

    # Step 2: 逐个获取视频 URL 并下载
    print(f"\n[Step 2] 开始下载视频到: {SAVE_DIR}")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, item in enumerate(items):
        serial = item.get("serialNo", i + 1)
        title = item.get("title", f"video_{serial}")
        alias = item["alias"]
        filename = clean_filename(f"{serial:03d}_{title}")
        output_path = os.path.join(SAVE_DIR, f"{filename}.mp4")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            print(f"\n[{i+1}/{len(items)}] 跳过 (已存在): {filename}")
            skip_count += 1
            continue

        print(f"\n[{i+1}/{len(items)}] {filename}")
        print(f"  alias: {alias}")

        # 获取视频页面，提取 m3u8
        m3u8_url = get_video_page(session, alias)
        if not m3u8_url:
            print(f"  [FAIL] 无法提取视频 URL")
            fail_count += 1
            continue

        # 下载
        try:
            if download_m3u8(session, m3u8_url, output_path, title):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  [ERROR] 下载失败: {e}")
            fail_count += 1

        # 避免请求过快
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f" 下载完成!")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")
    print(f"   跳过: {skip_count}")
    print(f"   保存目录: {SAVE_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
