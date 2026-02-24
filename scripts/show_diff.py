"""显示原始转录与纠错后的差异"""
import json, os, glob, sys, difflib

report = json.load(open("fix_terminology_report.json", encoding="utf-8"))

for r in report["results"]:
    if r["status"] != "success":
        continue
    name = r["file"]
    print(f"=== {name} ===")
    print(f"Corrections: {r['num_corrections']}")
    for c in r["corrections"]:
        print(f"  {c}")

    orig_path = os.path.join("transcripts", name + ".txt")
    corr_path = os.path.join("transcripts_corrected", name + ".txt")
    if not os.path.exists(orig_path) or not os.path.exists(corr_path):
        continue

    orig = open(orig_path, encoding="utf-8").read()
    corr = open(corr_path, encoding="utf-8").read()

    print(f"\nOriginal:  {len(orig)} chars")
    print(f"Corrected: {len(corr)} chars")

    sm = difflib.SequenceMatcher(None, orig, corr)
    changes = [(tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]

    if not changes:
        print("  (no textual differences found)")
        continue

    print(f"\n--- Changes ({len(changes)}) ---")
    for tag, i1, i2, j1, j2 in changes:
        ctx_s = max(0, i1 - 20)
        ctx_e = min(len(orig), i2 + 20)
        ctx_s2 = max(0, j1 - 20)
        ctx_e2 = min(len(corr), j2 + 20)
        print(f"\n  [{tag}]")
        print(f"  原文: ...{orig[ctx_s:i1]}【{orig[i1:i2]}】{orig[i2:ctx_e]}...")
        print(f"  纠正: ...{corr[ctx_s2:j1]}【{corr[j1:j2]}】{corr[j2:ctx_e2]}...")

    # Show full corrected text
    print(f"\n--- Full corrected text ---")
    print(corr)
