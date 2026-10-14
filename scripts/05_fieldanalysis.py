import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, collections, os
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]
print("rows:", len(rows))

# field histogram per class
per = collections.defaultdict(collections.Counter)
for r in rows:
    per[r["cls"]][r["field"]] += 1

TEXTCLASSES = ["TextMeshProUGUI", "Text"]
print("\n=== text-ish classes: field histogram ===")
for c in TEXTCLASSES:
    print(f"-- {c} ({sum(per[c].values())} fields)")
    for f, n in per[c].most_common(12):
        print(f"     {n:5d}  {f}")

print("\n=== classes with notable text fields (description/name/title/label/prompt/tip/hint/message) ===")
KEY = ("description", "desc", "title", "label", "prompt", "tip", "hint", "message", "m_Name", "text",
       "flavor", "caption", "header", "subtitle", "tooltip", "dialogue", "line", "note", "warning", "verb")
hits = collections.Counter()
for c, fc in per.items():
    for f, n in fc.items():
        leaf = f.split(".")[-1].split("[")[0]
        if any(k.lower() in leaf.lower() for k in KEY):
            hits[(c, leaf)] += n
for (c, f), n in hits.most_common(70):
    print(f"   {n:6d}  {c}.{f}")

print("\n=== all distinct classes count ===", len(per))
print("\n=== classes whose total string fields >= 20 ===")
tot = sorted(((sum(fc.values()), c) for c, fc in per.items()), reverse=True)
for n, c in tot[:45]:
    print(f"   {n:6d}  {c}")
