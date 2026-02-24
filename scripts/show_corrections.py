"""显示纠错报告中的修改列表"""
import json

rpt = json.load(open("fix_terminology_report.json", encoding="utf-8"))
for r in rpt["results"]:
    if r["status"] != "success":
        continue
    name = r["file"]
    print(f"=== {name} ===")
    print(f"Total corrections: {r['num_corrections']}")
    print(f"Original: {r['original_chars']} chars → Corrected: {r['corrected_chars']} chars")
    print()
    for i, c in enumerate(r["corrections"], 1):
        print(f"  {i:2d}. {c}")
    print()
