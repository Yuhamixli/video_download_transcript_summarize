#!/usr/bin/env python3
"""Run the processing pipeline directly from a transcript folder."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pipeline from a transcript folder")
    parser.add_argument(
        "--source-dir",
        default="transcripts/高级",
        help="Transcript folder (absolute or relative to project root)",
    )
    parser.add_argument(
        "--manifest-output",
        default="manifests/folder_pipeline.txt",
        help="Manifest output path relative to project root",
    )
    return parser.parse_args()


def run_step(command: list[str]) -> None:
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent

    source_dir = Path(args.source_dir)
    if not source_dir.is_absolute():
        source_dir = project_root / source_dir

    manifest_output = Path(args.manifest_output)
    if not manifest_output.is_absolute():
        manifest_output = project_root / manifest_output

    print(f"Folder pipeline source: {source_dir}")
    print(f"Manifest output: {manifest_output}")

    run_step(
        [
            sys.executable,
            str(project_root / "scripts" / "build_transcript_manifest.py"),
            "--source-dir",
            str(source_dir),
            "--output",
            str(manifest_output),
        ]
    )
    run_step(
        [
            sys.executable,
            str(project_root / "scripts" / "run_manifest_pipeline.py"),
            "--manifest",
            str(manifest_output),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
