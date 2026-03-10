"""
Organize transcripts folder: move _detail.json to whisper_detail/, sort .txt by course.
Run after transcribe.py to declutter and group by course.
"""

import os
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT_DIR = PROJECT_ROOT / "transcripts"
WHISPER_DETAIL_DIR = TRANSCRIPT_DIR / "whisper_detail"

# Course name extraction: match first known course prefix in filename (after XXX_YYY)
COURSE_PATTERNS = [
    (r"中医辨证学", "中医辨证学"),
    (r"实用经络针灸学", "实用经络针灸学"),
    (r"实用本草学", "实用本草学"),
    (r"解析本草学", "解析本草学"),
    (r"解析方剂学|经方|方剂|汤$|散$|丸$|饮$", "方剂学"),
]


def infer_course(basename: str) -> str:
    """Infer course name from transcript filename. Format: XXX_YYY标题.txt"""
    # Remove extension
    name = re.sub(r"\.(txt|json)$", "", basename)
    # Remove leading serial (e.g. 053_226 or 170_0109)
    title = re.sub(r"^\d+_\d+", "", name)
    for pattern, course in COURSE_PATTERNS:
        if re.search(pattern, title):
            return course
    return "其他"


def _collect_files():
    """Collect .txt and _detail.json from transcripts/ root and all subdirs."""
    txt_files = []
    json_files = []
    for f in TRANSCRIPT_DIR.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix == ".json" and "_detail" in f.stem:
            json_files.append(f)
        elif f.suffix == ".txt":
            txt_files.append(f)
    return txt_files, json_files


def main():
    if not TRANSCRIPT_DIR.exists():
        print("Error: transcripts/ not found")
        sys.exit(1)

    WHISPER_DETAIL_DIR.mkdir(parents=True, exist_ok=True)

    moved_json = 0
    moved_txt = 0
    course_dirs = {}

    txt_files, json_files = _collect_files()

    # Move _detail.json to whisper_detail/
    for f in json_files:
        dest = WHISPER_DETAIL_DIR / f.name
        if dest != f:
            shutil.move(str(f), str(dest))
            moved_json += 1

    # Group .txt by course and move to transcripts/<course>/
    for f in txt_files:
        course = infer_course(f.name)
        if course not in course_dirs:
            course_dir = TRANSCRIPT_DIR / course
            course_dir.mkdir(parents=True, exist_ok=True)
            course_dirs[course] = course_dir
        dest = course_dirs[course] / f.name
        if dest.resolve() != f.resolve():
            shutil.move(str(f), str(dest))
            moved_txt += 1

    print(f"Organized transcripts:")
    print(f"  _detail.json -> whisper_detail/: {moved_json}")
    print(f"  .txt by course: {moved_txt}")
    for course, d in sorted(course_dirs.items()):
        count = len(list(d.glob("*.txt")))
        print(f"    {course}: {count} files")


if __name__ == "__main__":
    main()
