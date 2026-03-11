#!/usr/bin/env python3
"""
Build a transcript manifest for targeted pipeline runs.

Examples:
    python scripts/build_transcript_manifest.py
    python scripts/build_transcript_manifest.py --date 2026-03-10
    python scripts/build_transcript_manifest.py --source-dir "transcripts/高级"
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Build transcript manifest from transcripts/ by date")
    parser.add_argument("--source-dir", help="Source transcript directory (absolute or relative to project root)")
    parser.add_argument("--date", default=str(date.today()), help="Date in YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--output",
        default="manifests/today_122.txt",
        help="Output manifest path relative to project root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    transcripts_dir = project_root / "transcripts"
    output_path = project_root / args.output

    manifest_entries = []
    if args.source_dir:
        source_dir = Path(args.source_dir)
        if not source_dir.is_absolute():
            source_dir = project_root / source_dir
        source_dir = source_dir.resolve()

        for txt_path in sorted(source_dir.glob("*.txt")):
            manifest_entries.append(txt_path.relative_to(transcripts_dir).as_posix())
        print(f"Manifest source dir: {source_dir}")
    else:
        day = datetime.strptime(args.date, "%Y-%m-%d")
        next_day = day + timedelta(days=1)

        for txt_path in sorted(transcripts_dir.rglob("*.txt")):
            mtime = datetime.fromtimestamp(txt_path.stat().st_mtime)
            if day <= mtime < next_day:
                manifest_entries.append(txt_path.relative_to(transcripts_dir).as_posix())
        print(f"Manifest date: {args.date}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for entry in manifest_entries:
            f.write(f"{entry}\n")

    print(f"Transcript count: {len(manifest_entries)}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
