import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
         "sharedassets2.assets", "sharedassets3.assets", "globalgamemanagers.assets",
         "level0", "level1", "level2", "level3"]
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)

# global sprite pid -> name (note collisions)
gmap = collections.defaultdict(set)
per_file_sprite = {}
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    m = {}
    for obj in env.objects:
        if obj.type.name == "Sprite":
            try:
                m[obj.path_id] = obj.read_typetree().get("m_Name")
            except Exception:
                pass
    per_file_sprite[fn] = m
    for k, v in m.items():
        gmap[k].add(v)
print("global sprite pids:", len(gmap), " colliding pids:", sum(1 for v in gmap.values() if len(v) > 1))

uses = collections.Counter()
detail = []
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    local = per_file_sprite[fn]
    go_name, tr_go, tr_father, go_tr = {}, {}, {}, {}
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
        if node.m_Type not in ("Image", "SpriteRenderer", "RawImage"):
            continue
        try:
            d = obj.read_typetree(nodes=node)
        except Exception:
            continue
        sp = d.get("m_Sprite")
        sid = sp.get("m_PathID") if isinstance(sp, dict) else None
        nm = local.get(sid) or (sorted(gmap[sid])[0] if sid in gmap and len(gmap[sid]) == 1 else None)
        if not nm:
            continue
        g = (d.get("m_GameObject") or {}).get("m_PathID")
        uses[nm] += 1
        detail.append({"file": fn, "cls": node.m_Type, "path": path_of(g), "sprite": nm})

json.dump(detail, open(os.path.join(OUT, "image_sprites_all.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("resolved image->sprite uses:", len(detail), "distinct sprites:", len(uses))
print("\n=== distinct sprites used by Image/SpriteRenderer (all) ===")
for k, v in uses.most_common(80):
    print(f"   {v:5d}  {k}")
print("\n=== usages of suspicious (possible baked text) sprites ===")
SUS = ("mainmenu_placeholder", "buttonhints", "ui_buttonhints", "map_reference", "logo",
       "splash", "instrumenticons", "uimask", "cursor", "2x2_texture", "popuppanel")
for d in detail:
    if any(s in (d["sprite"] or "").lower() for s in SUS):
        print(f"   {d['file']:20s} {d['cls']:15s} {d['path']:65s} -> {d['sprite']}")
