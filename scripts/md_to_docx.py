#!/usr/bin/env python3
"""
Convert Markdown files in outlines/ to MS Word (.docx) with larger font sizes
for senior readers who have difficulty with small text.

Requires: pandoc (https://pandoc.org/installing.html)
          python-docx (pip install python-docx)

Usage:
    python scripts/md_to_docx.py [--out-dir OUT_DIR] [--font-size 16]
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_BODY_PT = 16


def ensure_pandoc() -> bool:
    return shutil.which("pandoc") is not None


def create_reference_docx(ref_path: Path, body_pt: int) -> bool:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        print("Error: python-docx is required. Run: pip install python-docx")
        return False

    result = subprocess.run(
        ["pandoc", "--print-default-data-file", "reference.docx"],
        capture_output=True, text=False,
    )
    if result.returncode != 0:
        print("Error: Could not get pandoc default reference document.")
        return False

    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_bytes(result.stdout)

    doc = Document(str(ref_path))
    h1_pt = body_pt + 6
    h2_pt = body_pt + 3
    h3_pt = body_pt + 1
    table_pt = body_pt - 1

    style_map = {
        "Normal": body_pt,
        "Body Text": body_pt,
        "Heading 1": h1_pt,
        "Heading 2": h2_pt,
        "Heading 3": h3_pt,
        "Heading 4": body_pt + 1,
        "Heading 5": body_pt,
        "Heading 6": body_pt,
        "Table": table_pt,
        "Table Normal": table_pt,
        "Table Grid": table_pt,
        "Block Text": body_pt,
        "Intense Quote": body_pt,
        "List Paragraph": body_pt,
        "Caption": body_pt - 1,
    }

    for style in doc.styles:
        try:
            if style.font is not None and style.name in style_map:
                style.font.size = Pt(style_map[style.name])
        except Exception:
            pass

    doc.save(str(ref_path))
    return True


def convert_md_to_docx(md_path: Path, docx_path: Path, ref_docx: Path) -> bool:
    """Convert via temp dir to avoid pandoc Windows path encoding issues with Chinese."""
    md_path = md_path.resolve()
    docx_path = docx_path.resolve()
    ref_docx = ref_docx.resolve()
    if not md_path.exists():
        print(f"  Error: File not found: {md_path}")
        return False
    with tempfile.TemporaryDirectory(prefix="md2docx_") as tmp:
        tmp_path = Path(tmp)
        tmp_md = tmp_path / "input.md"
        tmp_docx = tmp_path / "output.docx"
        shutil.copy2(md_path, tmp_md)
        result = subprocess.run(
            [
                "pandoc", str(tmp_md),
                "-o", str(tmp_docx),
                f"--reference-doc={ref_docx}",
                "--from=markdown", "--to=docx",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  Error: {result.stderr.strip()}")
            return False
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_docx, docx_path)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Convert outlines/*.md to MS Word with larger fonts."
    )
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Output directory (default: outlines_docx/)")
    parser.add_argument("--font-size", type=int, default=DEFAULT_BODY_PT,
                        help=f"Body font size in pt (default: {DEFAULT_BODY_PT})")
    parser.add_argument("--single", type=str, default=None,
                        help="Convert only this .md file (relative to outlines/)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    outlines_dir = project_root / "outlines"
    out_dir = args.out_dir or (project_root / "outlines_docx")

    if not outlines_dir.exists():
        print(f"Error: outlines directory not found: {outlines_dir}")
        sys.exit(1)

    if not ensure_pandoc():
        print(
            "Error: pandoc is not installed.\n"
            "  Windows: winget install pandoc\n"
            "  Or: choco install pandoc"
        )
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    ref_docx = out_dir / "_reference.docx"

    print(f"Creating reference document ({args.font_size}pt body)...")
    if not create_reference_docx(ref_docx, args.font_size):
        sys.exit(1)

    if args.single:
        md_files = [outlines_dir / args.single]
        if not md_files[0].exists():
            print(f"Error: File not found: {md_files[0]}")
            sys.exit(1)
    else:
        flat = list(outlines_dir.glob("*.md"))
        nested = list(outlines_dir.rglob("*.md"))
        nested = [p for p in nested if p.parent != outlines_dir]
        md_files = sorted(set(flat + nested))

    print(f"Converting {len(md_files)} file(s) to .docx...")
    ok, fail = 0, 0
    for md_path in md_files:
        rel = md_path.relative_to(outlines_dir)
        docx_path = out_dir / rel.with_suffix(".docx")
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        if convert_md_to_docx(md_path, docx_path, ref_docx):
            print(f"  OK: {md_path.name}")
            ok += 1
        else:
            print(f"  FAIL: {md_path.name}")
            fail += 1

    print(f"\nDone. {ok} converted, {fail} failed. Output: {out_dir}")


if __name__ == "__main__":
    main()
