import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = json.load(open(os.path.join(D, "ui_text_paths.json"), encoding="utf-8"))
out = []
def w(s=""):
    out.append(str(s))

pref = collections.Counter()
for r in rows:
    p = r["path"].split("/")
    pref["/".join(p[:3]) if len(p) > 3 else r["path"]] += 1
w("=== 3-level path prefixes (in-game UI, non DebugUI*) ===")
for k, v in sorted(pref.items()):
    if k.startswith("DebugUI"):
        continue
    w(f"   {v:5d}  {k}")
w()
w("=== all paths whose text is non-placeholder (len>3 and not digits) ===")
for r in sorted(rows, key=lambda x: x["path"]):
    t = (r["text"] or "").strip()
    if not t or t.isdigit():
        continue
    w(f"   {r['source']:22s} {r['path']:75s} -> {r['text']!r}")
with open(os.path.join(D, "19_paths.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("lines", len(out))
