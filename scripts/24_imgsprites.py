import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
         "sharedassets2.assets", "sharedassets3.assets", "level0", "level1", "level2", "level3"]
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)
imgs = []

out = []
def w(s=""):
    out.append(str(s))

for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    go_name, tr_go, tr_father, go_tr, sprite_name = {}, {}, {}, {}, {}
    for obj in env.objects:
        tn = obj.type.name
        try:
            if tn == "GameObject":
                go_name[obj.path_id] = obj.read_typetree().get("m_Name", "")
            elif tn in ("Transform", "RectTransform"):
                d = obj.read_typetree()
                g = (d.get("m_GameObject") or {}).get("m_PathID")
                tr_go[obj.path_id] = g
                if g:
                    go_tr[g] = obj.path_id
                f = d.get("m_Father") or {}
                fid, ff = f.get("m_PathID"), f.get("m_FileID")
                tr_father[obj.path_id] = fid if (fid and not ff) else None
            elif tn == "Sprite":
                sprite_name[obj.path_id] = obj.read_typetree().get("m_Name")
        except Exception:
            pass

    def path_of(gid):
        t = go_tr.get(gid); parts = []; seen = set()
        while t and t not in seen and len(parts) < 24:
            seen.add(t)
            g = tr_go.get(t)
            if g:
                parts.append(go_name.get(g, "?"))
            t = tr_father.get(t)
        parts.reverse()
        return "/".join(parts)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            node = obj._get_typetree_node()
        except Exception:
            continue
        if node.m_Type not in ("Image", "SpriteRenderer", "TMP_SubMeshUI", "RawImage"):
            continue
        try:
            d = obj.read_typetree(nodes=node)
        except Exception:
            continue
        g = (d.get("m_GameObject") or {}).get("m_PathID")
        sp = d.get("m_Sprite") or {}
        sid = sp.get("m_PathID") if isinstance(sp, dict) else None
        sname = sprite_name.get(sid, "")
        if not sname:
            continue
        imgs.append({"file": fn, "cls": node.m_Type, "path": path_of(g), "sprite": sname})

for r in imgs:
    w(f"{r['file']:22s} {r['cls']:15s} {r['path']:70s} -> {r['sprite']}")
with open(os.path.join(OUT, "24_image_sprites.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")

print("image components with a sprite:", len(imgs))
print("\n=== main-menu / title / logo / credits sprites ===")
for r in imgs:
    pl = r["path"].lower()
    if any(k in pl for k in ("canvas/logo", "canvas/title", "canvas/playbuttons", "canvas/footer",
                             "credits", "mainmenu", "splash", "scean", "screen/basicbutton",
                             "gamemode", "loadoutselector", "pausemenu", "shipmenu")):
        print(f"   {r['file']:20s} {r['path']:68s} -> {r['sprite']}")
print("\n=== ALL distinct sprites used by UI Image components (top 70 by frequency) ===")
c = collections.Counter(r["sprite"] for r in imgs)
for k, v in c.most_common(70):
    print(f"   {v:4d}  {k}")
