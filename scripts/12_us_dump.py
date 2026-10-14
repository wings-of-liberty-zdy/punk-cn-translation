import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
d = json.load(open(os.path.join(D, "us_Punk.Main.dll.json"), encoding="utf-8"))
rows = d["rows"]
att = d["attribution"]
print("strings:", len(rows))
out = []
out.append(f"strings: {len(rows)}")
out.append("")
out.append("=== ALL #US strings, shortest->longest ===")
for r in sorted(rows, key=lambda x: len(x["text"])):
    t = r["text"]
    a = att.get(t) or []
    ctx = ";".join(sorted({f"{x[0]}.{x[1]}" for x in a if x[0]}))[:130]
    out.append(f"  {len(t):3d} | {t!r} | {ctx}")
with open(os.path.join(D, "12_us_all.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("wrote 12_us_all.txt lines:", len(out))
