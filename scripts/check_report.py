"""检查纠错报告中的跳过和失败情况"""
import json, os

rpt = json.load(open("fix_terminology_report.json", encoding="utf-8"))
skipped = [r for r in rpt["results"] if r["status"] == "skipped"]
success = [r for r in rpt["results"] if r["status"] == "success"]
failed = [r for r in rpt["results"] if r["status"] == "failed"]

print(f"Success: {len(success)}")
print(f"Skipped: {len(skipped)}")
print(f"Failed:  {len(failed)}")
print(f"Total corrections: {sum(r.get('num_corrections', 0) for r in success)}")
print()

if skipped:
    print("--- Skipped files ---")
    for s in skipped:
        reason = s.get("reason", "already corrected in previous run")
        print(f"  {s['file'][:60]}  ({reason})")
    print()

if failed:
    print("--- Failed files ---")
    for f in failed:
        print(f"  {f['file'][:60]}  ({f.get('error', '?')})")
    print()

# Also check corrected files vs originals
import glob
corr = sorted(glob.glob("transcripts_corrected/*.txt"))
orig = sorted(glob.glob("transcripts/*.txt"))
corr_names = {os.path.basename(f) for f in corr}
orig_names = {os.path.basename(f) for f in orig}
missing = orig_names - corr_names
if missing:
    print(f"--- Missing corrected files ({len(missing)}) ---")
    for m in sorted(missing):
        print(f"  {m}")
else:
    print(f"All {len(orig_names)} transcripts have corrected versions.")
