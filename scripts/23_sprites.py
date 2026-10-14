import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = json.load(open(os.path.join(D, "sprites.json"), encoding="utf-8"))
tex = json.load(open(os.path.join(D, "textures.json"), encoding="utf-8"))
out = []
def w(s=""):
    out.append(str(s))

groups = collections.defaultdict(list)
for r in rows:
    n = r["name"] or ""
    pre = n.split("_")[0]
    if n.startswith("Sprites Tiles") or n.startswith("Sprite Plant") or n.startswith("s_Tiles"):
        pre = "(tiles/plants)"
    groups[pre].append(n)

w("=== sprite groups (prefix -> count, sample names) ===")
for k, v in sorted(groups.items(), key=lambda x: -len(x[1])):
    w(f"  {len(v):5d}  {k:28s} {sorted(v)[:4]}")

w()
w("=== ALL sprites under UI-ish prefixes ===")
UIISH = ("MainMenu", "Buttonhints", "Ui_ButtonHints", "HUD_", "Sheet_MapIcons", "LOGO",
         "Sprites_UIShapes", "SplashScreen", "Logo", "Title", "Placeholder", "placeholder")
for r in sorted(rows, key=lambda x: (x["name"] or "")):
    n = r["name"] or ""
    if any(n.startswith(p) for p in UIISH):
        w(f"  {r['file']:22s} {n:45s} {r['w']}x{r['h']}")

w()
w("=== ALL Texture2D names (potential baked text carriers) ===")
for t in sorted(tex, key=lambda x: -(x["w"] or 0) * (x["h"] or 0)):
    w(f"  {t['file']:22s} {str(t['name'])[:58]:60s} {t['w']}x{t['h']}")

w()
w("=== distinct sprite names in level*/Canvas-ish UI files ===")
for r in sorted(rows, key=lambda x: (x["file"], x["name"] or "")):
    if r["file"].startswith("level") or r["file"].startswith("sharedassets2"):
        w(f"  {r['file']:22s} {r['name']}")
with open(os.path.join(D, "23_sprites.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("lines", len(out))
