import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]

status = {}
for r in rows:
    if r["source"] == "Punk.Main.dll":
        status[r["text"]] = (r["decision"], r["reason"])

TEXT = re.compile(r"TMP_Text::set_text|UI\.Text::set_text|ShipLogOutput::Log|LogOutput::Log|TMP_InputField::set_text")

# ---- group every literal by the method that ldstr's it ----
by_method = collections.defaultdict(set)
for m in methods:
    key = f"{m['type']}::{m['name']}"
    for s in m["strings"]:
        if s in status:
            by_method[key].add(s)

lines = []
def w(s=""):
    lines.append(s)

HIGH, MED, LOW = [], [], []

for key, lits in sorted(by_method.items()):
    keeps = sorted(s for s in lits if status[s][0] == "keep")
    rejs = sorted(s for s in lits if status[s][0] == "reject")
    if not rejs:
        continue
    mm = [m for m in methods if f"{m['type']}::{m['name']}" == key]
    direct = any(TEXT.search(c) for m in mm for c in m["calls"])
    if keeps and direct:
        HIGH.append((key, keeps, rejs, direct))
    elif keeps:
        MED.append((key, keeps, rejs, direct))
    elif direct:
        MED.append((key, keeps, rejs, direct))
    else:
        LOW.append((key, keeps, rejs, direct))

def emit(title, bucket, note):
    w("=" * 96)
    w(f"### {title}  ({sum(len(r) for _, _, r, _ in bucket)} rejected literals in {len(bucket)} methods)")
    w(f"### {note}")
    w("=" * 96)
    for key, keeps, rejs, direct in bucket:
        w(f"\n  {key}   directTMP={direct}")
        w(f"    KEPT siblings (human-verified player-facing):")
        for k in keeps[:10]:
            w(f"        + {k!r}")
        w(f"    REJECTED siblings (same method -> same code path):")
        for r in rejs[:12]:
            w(f"        - {r!r}   [{status[r][1][:40]}]")
    w("")

emit("HIGH CONFIDENCE — method has KEPT player-facing siblings AND a direct TMP/ship-log sink",
     HIGH, "same method, same return path; if the kept ones are UI, these are too")
emit("MEDIUM — method has KEPT siblings but no direct sink (goes through a helper)",
     MED, "needs one more hop to confirm")
emit("LOW — only a direct sink, no kept sibling to calibrate against",
     LOW, "weakest of the three")

allhigh = sorted({r for _, _, rejs, _ in HIGH for r in rejs})
allmed = sorted({r for _, _, rejs, _ in MED for r in rejs})
w("=" * 96)
w(f"SUMMARY: HIGH={len(allhigh)}  MEDIUM={len(allmed)}  "
  f"LOW={len({r for _,_,rejs,_ in LOW for r in rejs})}")
w("=" * 96)
w("\n### HIGH list (flat) ###")
for r in allhigh:
    w(f"  {r!r}")
w("\n### MEDIUM list (flat) ###")
for r in allmed:
    w(f"  {r!r}")

open(os.path.join(OUT, "q3_sibling_analysis.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
json.dump({"high": allhigh, "medium": allmed,
           "low": sorted({r for _, _, rejs, _ in LOW for r in rejs}),
           "by_method": {k: {"kept": v[1], "rejected": v[2], "direct_tmp": v[3]} for k, v in
                         [(x[0], x) for x in HIGH + MED + LOW]}},
          open(os.path.join(OUT, "q3_sibling_analysis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"HIGH={len(allhigh)} MEDIUM={len(allmed)} LOW={len({r for _,_,rejs,_ in LOW for r in rejs})}")
print("wrote q3_sibling_analysis.txt / .json")
