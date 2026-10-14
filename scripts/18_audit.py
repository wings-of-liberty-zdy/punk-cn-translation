import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections
ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
D = os.path.join(ROOT, "data", "dump")
cl = [json.loads(l) for l in open(os.path.join(D, "strings_all_classified.jsonl"), encoding="utf-8")]
out = []
def w(s=""):
    out.append(str(s))

w("#### REJECTED with reason 'unclassified field' -- check for missed text")
for c in cl:
    if c["decision"] == "reject" and "unclassified field" in c["reason"]:
        w(f"  {c['key_or_context']}  ->  {c['text']!r}")
w()
w("#### REJECTED 'non-text field' -- distinct fields dropped")
f = collections.Counter()
for c in cl:
    if c["decision"] == "reject" and "non-text field" in c["reason"]:
        f[c["key_or_context"].split("|")[2]] += 1
for k, v in f.most_common(40):
    w(f"  {v:6d}  {k}")
w()
w("#### KEPT ui_menu, sorted by length desc")
for c in sorted([x for x in cl if x["decision"] == "keep" and x["category"] == "ui_menu"],
                key=lambda x: -len(x["text"])):
    parts = c["key_or_context"].split("|")
    fld = parts[2] if len(parts) > 2 else "?"
    w(f"  len={len(c['text']):3d} {c['text']!r}   [{fld}]")
w()
w("#### 'New' occurrences - GameObject names")
for c in cl:
    if c["text"] == "New":
        w(f"  {c['key_or_context']}")
w()
w("#### KEPT other")
for c in cl:
    if c["decision"] == "keep" and c["category"] == "other":
        w(f"  {c['source']} | {c['text']!r}")
w()
w("#### KEPT dialogue_story")
for c in cl:
    if c["decision"] == "keep" and c["category"] == "dialogue_story":
        w(f"  {c['source']} | len={len(c['text'])} {c['text']!r}")
with open(os.path.join(D, "18_audit.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("lines:", len(out))
