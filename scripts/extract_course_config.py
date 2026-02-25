"""
Auto-extract course config (COLUMN_ALIAS, KDT_ID, CHAPTER_ID, BASE_URL)
from the latest mitmproxy capture file.

Parses captured API URLs for youzan course patterns and writes course_config.json.
"""

import json
import glob
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE_DIR = os.path.join(PROJECT_ROOT, "captured")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "course_config.json")


def find_latest_capture():
    files = sorted(glob.glob(os.path.join(CAPTURE_DIR, "capture_*.json")))
    if not files:
        return None
    return files[-1]


def extract_from_urls(urls):
    """Extract course params from a list of URLs."""
    config = {}

    for url in urls:
        if "columnAlias=" in url:
            m = re.search(r"columnAlias=([^&]+)", url)
            if m:
                config["column_alias"] = m.group(1)

        if "kdt_id=" in url:
            m = re.search(r"kdt_id=([^&]+)", url)
            if m:
                config["kdt_id"] = m.group(1)

        if "chapterId=" in url:
            m = re.search(r"chapterId=([^&]+)", url)
            if m:
                config["chapter_id"] = m.group(1)

        m = re.match(r"(https://shop\d+\.youzan\.com)", url)
        if m:
            config["base_url"] = m.group(1)

        # Also try /wscvis/course/detail/{alias} pattern
        m = re.search(r"/wscvis/course/detail/([a-z0-9]+)", url)
        if m and "column_alias" not in config:
            config["column_alias"] = m.group(1)

    return config


def main():
    capture_file = find_latest_capture()
    if not capture_file:
        print("Error: No capture files found in captured/")
        print("Run start_capture.py first, browse the course, then stop.")
        sys.exit(1)

    print(f"Reading: {os.path.basename(capture_file)}")

    with open(capture_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_urls = []
    for api in data.get("apis", []):
        all_urls.append(api.get("url", ""))
    for video in data.get("videos", []):
        all_urls.append(video.get("url", ""))

    # Also check all_requests file
    all_req_file = capture_file.replace("capture_", "all_requests_")
    if os.path.exists(all_req_file):
        with open(all_req_file, "r", encoding="utf-8") as f:
            all_reqs = json.load(f)
        for req in all_reqs:
            all_urls.append(req.get("url", ""))

    config = extract_from_urls(all_urls)

    required = ["column_alias", "kdt_id", "base_url"]
    missing = [k for k in required if k not in config]
    if missing:
        print(f"Warning: Could not extract: {', '.join(missing)}")
        print("You may need to manually edit course_config.json")
        if "column_alias" not in config:
            sys.exit(1)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"Saved course_config.json:")
    for k, v in config.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
