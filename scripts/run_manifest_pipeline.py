#!/usr/bin/env python3
"""Run a targeted pipeline for manifest entries with per-file isolation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def load_manifest(manifest_path: Path) -> list[str]:
    entries = []
    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries.append(line.replace("\\", "/"))
    return entries


def build_transcript_lookup(transcripts_root: Path) -> dict[str, str]:
    lookup = {}
    for txt_path in transcripts_root.rglob("*.txt"):
        lookup[txt_path.name] = txt_path.relative_to(transcripts_root).as_posix()
    return lookup


def write_single_manifest(entry: str) -> Path:
    fd, path = tempfile.mkstemp(prefix="one_manifest_", suffix=".txt")
    os.close(fd)
    tmp = Path(path)
    tmp.write_text(f"{entry}\n", encoding="utf-8")
    return tmp


def run_step(command: list[str], timeout: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, check=False, text=True, timeout=timeout)
        return result.returncode == 0, f"exit={result.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"timeout={timeout}s"


def fallback_copy_to_corrected(project_root: Path, resolved_entry: str) -> bool:
    """Copy source transcript into transcripts_corrected/ as a passthrough fallback."""
    transcripts_root = project_root / "transcripts"
    corrected_root = project_root / "transcripts_corrected"

    source_path = transcripts_root / resolved_entry
    corrected_path = corrected_root / resolved_entry
    corrected_path.parent.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        return False

    text = source_path.read_text(encoding="utf-8")
    corrected_path.write_text(text, encoding="utf-8")

    detail_name = f"{Path(resolved_entry).stem}_detail.json"
    detail_src_candidates = [
        source_path.with_name(detail_name),
        transcripts_root / "whisper_detail" / detail_name,
    ]
    detail_src = next((p for p in detail_src_candidates if p.exists()), None)
    if detail_src:
        detail = json.loads(detail_src.read_text(encoding="utf-8"))
        detail["text"] = text
        detail["corrections"] = []
        detail["correction_model"] = "passthrough-fallback"
        detail["correction_status"] = "fallback_copy"
        detail_dst = corrected_path.with_name(detail_name)
        detail_dst.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run targeted pipeline from transcript manifest")
    parser.add_argument("--manifest", required=True, help="Manifest path relative to project root or absolute")
    parser.add_argument("--fix-timeout", type=int, default=900, help="Per-file fix timeout in seconds")
    parser.add_argument("--outline-timeout", type=int, default=900, help="Per-file outline timeout in seconds")
    parser.add_argument("--font-size", type=int, default=18, help="DOCX body font size")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = project_root / manifest_path

    entries = load_manifest(manifest_path)
    transcripts_root = project_root / "transcripts"
    corrected_root = project_root / "transcripts_corrected"
    outlines_root = project_root / "outlines"
    transcript_lookup = build_transcript_lookup(transcripts_root)

    print(f"Manifest entries: {len(entries)}")

    fix_ok = 0
    fix_fail = 0
    fix_fallback = 0
    for idx, entry in enumerate(entries, start=1):
        resolved_entry = transcript_lookup.get(Path(entry).name)
        if not resolved_entry:
            fix_fail += 1
            print(f"[fix {idx}/{len(entries)}] missing {entry}")
            continue

        corrected_path = corrected_root / resolved_entry
        if corrected_path.exists() and corrected_path.stat().st_size > 10:
            print(f"[fix {idx}/{len(entries)}] skip {resolved_entry}")
            continue

        one_manifest = write_single_manifest(resolved_entry)
        print(f"[fix {idx}/{len(entries)}] run {resolved_entry}")
        ok, status = run_step(
            [sys.executable, str(project_root / "fix_terminology.py"), "--manifest", str(one_manifest)],
            args.fix_timeout,
        )
        one_manifest.unlink(missing_ok=True)
        if ok:
            fix_ok += 1
        else:
            if fallback_copy_to_corrected(project_root, resolved_entry):
                fix_fallback += 1
                print(f"  [fix-fallback] {resolved_entry}: {status}")
            else:
                fix_fail += 1
                print(f"  [fix-error] {resolved_entry}: {status}")

    outline_ok = 0
    outline_fail = 0
    for idx, entry in enumerate(entries, start=1):
        resolved_entry = transcript_lookup.get(Path(entry).name)
        if not resolved_entry:
            outline_fail += 1
            print(f"[outline {idx}/{len(entries)}] missing {entry}")
            continue

        outline_path = outlines_root / Path(resolved_entry).with_suffix(".md")
        if outline_path.exists() and outline_path.stat().st_size > 10:
            print(f"[outline {idx}/{len(entries)}] skip {resolved_entry}")
            continue

        one_manifest = write_single_manifest(resolved_entry)
        print(f"[outline {idx}/{len(entries)}] run {resolved_entry}")
        ok, status = run_step(
            [
                sys.executable,
                str(project_root / "generate_outline.py"),
                "--manifest",
                str(one_manifest),
                "--no-summary",
            ],
            args.outline_timeout,
        )
        one_manifest.unlink(missing_ok=True)
        if ok:
            outline_ok += 1
        else:
            outline_fail += 1
            print(f"  [outline-error] {resolved_entry}: {status}")

    print("[sync] knowledge_sync --index")
    sync_ok, sync_status = run_step(
        [sys.executable, str(project_root / "scripts" / "knowledge_sync.py"), "--index"],
        7200,
    )
    print(f"[sync] {sync_status}")

    print("[docx] md_to_docx --manifest")
    docx_ok, docx_status = run_step(
        [
            sys.executable,
            str(project_root / "scripts" / "md_to_docx.py"),
            "--manifest",
            str(manifest_path),
            "--font-size",
            str(args.font_size),
        ],
        7200,
    )
    print(f"[docx] {docx_status}")

    print("=" * 60)
    print(f"fix newly completed: {fix_ok}, failed: {fix_fail}")
    print(f"fix fallback copied: {fix_fallback}")
    print(f"outline newly completed: {outline_ok}, failed: {outline_fail}")
    print(f"sync ok: {sync_ok}")
    print(f"docx ok: {docx_ok}")
    print("=" * 60)

    return 0 if sync_ok and docx_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
