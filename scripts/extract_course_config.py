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
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE_DIR = os.path.join(PROJECT_ROOT, "captured")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "course_config.json")


def find_latest_capture():
    files = sorted(glob.glob(os.path.join(CAPTURE_DIR, "capture_*.json")))
    if not files:
        return None
    return files[-1]


def _extract_alias_from_detail_path(url):
    m = re.search(r"/wscvis/course/detail/([a-z0-9]+)", url)
    if not m:
        return None
    alias = m.group(1)
    # reportViewProcess.json is not a real course alias.
    if alias.lower().startswith("report"):
        return None
    return alias


def extract_from_urls(urls):
    """Extract course params from a list of URLs."""
    config = {}
    detail_alias_candidates = []
    from_column_candidates = []

    for url in urls:
        if not url:
            continue

        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if "kdt_id" in query and query["kdt_id"]:
            config["kdt_id"] = query["kdt_id"][0]

        if "chapterId" in query and query["chapterId"]:
            config["chapter_id"] = query["chapterId"][0]

        if "fromColumn" in query and query["fromColumn"]:
            from_column_candidates.append(query["fromColumn"][0])

        if "columnAlias" in query and query["columnAlias"]:
            from_column_candidates.append(query["columnAlias"][0])

        if parsed.scheme and parsed.netloc:
            config["base_url"] = f"{parsed.scheme}://{parsed.netloc}"

        detail_alias = _extract_alias_from_detail_path(url)
        if detail_alias:
            detail_alias_candidates.append(detail_alias)

    # Prefer fromColumn/columnAlias because that's the real course list alias.
    if from_column_candidates:
        config["column_alias"] = from_column_candidates[0]
    elif detail_alias_candidates:
        config["column_alias"] = detail_alias_candidates[0]

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
        referer = api.get("request_headers", {}).get("Referer", "")
        if referer:
            all_urls.append(referer)
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
