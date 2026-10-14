import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = json.load(open(os.path.join(D, "sprites.json"), encoding="utf-8"))
tex = json.load(open(os.path.join(D, "textures.json"), encoding="utf-8"))
print("sprites:", len(rows), "textures:", len(tex))

# name prefix inventory
pref = collections.Counter()
for r in rows:
    n = r["name"] or ""
    parts = n.split("_")
    pref["_".join(parts[:2]) if len(parts) > 1 else n] += 1
print("\n=== sprite name prefixes (top 60) ===")
for k, v in pref.most_common(60):
    print(f"   {v:5d}  {k}")

print("\n=== EVERY distinct sprite name, sorted (for manual scan) ===")
names = sorted({(r["name"] or "") for r in rows})
for n in names:
    print("   ", n)
print("\n=== EVERY texture name ===")
for t in sorted(tex, key=lambda x: -(x["w"] or 0) * (x["h"] or 0)):
    print(f"   {t['file']:24s} {str(t['name'])[:60]:62s} {t['w']}x{t['h']}")
