import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]

CLASSES = ["TutorialController", "LoadingScreen", "SharedResourceDisplayText",
           "InstrumentDiscoverable", "InstructionWidget", "TutorialStep", "PoI", "CellType"]
per = collections.defaultdict(collections.Counter)
for r in rows:
    per[r["cls"]][r["field"]] += 1

for c in CLASSES:
    if c not in per:
        print(f"-- {c}: NOT PRESENT")
        continue
    print(f"-- {c}  ({sum(per[c].values())} fields)")
    for f, n in per[c].most_common(40):
        print(f"     {n:5d}  {f}")
    print()

# print actual values for text-bearing fields of TutorialController / LoadingScreen
WANT = {"TutorialController", "LoadingScreen", "SharedResourceDisplayText", "InstrumentDiscoverable"}
print("=== values ===")
for r in rows:
    if r["cls"] in WANT and not r["field"].endswith("m_Name"):
        print(f"  [{r['cls']}.{r['field']}] ({r['source']}|{r['go']}) {r['text']!r}")

# also: dump ALL distinct classes whose name contains hint/tut/text/msg/desc/name
print("\n=== classes matching hint/tutor/text/message/desc/display/label ===")
for c in sorted(per):
    cl = c.lower()
    if any(k in cl for k in ("hint", "tutor", "text", "message", "desc", "display", "label", "tooltip", "prompt")):
        print(f"  {c}: {sum(per[c].values())} -> {dict(per[c].most_common(8))}")
