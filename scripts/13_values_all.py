import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, collections, os
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]

out = []
def w(s=""):
    out.append(str(s))

# 1. distinct TMP / Text values
for cls, fld in (("TextMeshProUGUI", "m_text"), ("Text", "m_Text")):
    vals = collections.Counter(r["text"] for r in rows if r["cls"] == cls and r["field"] == fld)
    w(f"##### {cls}.{fld}: {sum(vals.values())} instances, {len(vals)} distinct")
    for v, n in sorted(vals.items(), key=lambda x: (-len(x[0]), x[0])):
        w(f"  {n:4d}x len={len(v):3d} {v!r}")
    w()

# 2. every displayName / description / format / title / prompt field on MonoBehaviours
w("##### ALL displayName/description/format/title/label/prompt/tooltip/flavor values")
per = collections.defaultdict(list)
for r in rows:
    leaf = r["field"].split(".")[-1].split("[")[0]
    if leaf.lower() in ("displayname", "description", "format", "title", "label", "prompt",
                        "tooltip", "flavor", "caption", "subtitle", "header", "m_stringargument",
                        "characterSequence", "m_openingdefinition", "m_closingdefinition"):
        per[(r["cls"], leaf)].append((r["go"], r["text"]))
for (c, f), lst in sorted(per.items()):
    w(f"-- {c}.{f}  ({len(lst)})")
    seen = set()
    for go, t in lst:
        kk = t
        if kk in seen:
            continue
        seen.add(kk)
        w(f"     [{go}] {t!r}")
    w()

# 3. TextAsset contents
w("##### TextAsset / other non-MonoBehaviour string carriers checked separately")
with open(os.path.join(D, "13_values_all.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("wrote 13_values_all.txt lines:", len(out))
print("\n".join(out[:80]))
