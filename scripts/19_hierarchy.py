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

rows = []
shopcfg = []
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    go_name = {}
    tr_go = {}       # transform pid -> gameobject pid
    tr_father = {}   # transform pid -> father pid (same file only)
    go_tr = {}       # gameobject pid -> transform pid
    for obj in env.objects:
        tn = obj.type.name
        if tn == "GameObject":
            try:
                go_name[obj.path_id] = obj.read_typetree().get("m_Name", "")
            except Exception:
                pass
        elif tn in ("Transform", "RectTransform"):
            try:
                d = obj.read_typetree()
                g = d.get("m_GameObject") or {}
                gid = g.get("m_PathID") if isinstance(g, dict) else getattr(g, "m_PathID", None)
                tr_go[obj.path_id] = gid
                if gid:
                    go_tr[gid] = obj.path_id
                f = d.get("m_Father") or {}
                fid = f.get("m_PathID") if isinstance(f, dict) else getattr(f, "m_PathID", None)
                ff = f.get("m_FileID") if isinstance(f, dict) else getattr(f, "m_FileID", None)
                tr_father[obj.path_id] = fid if (fid and not ff) else None
            except Exception:
                pass

    def path_of(gid):
        t = go_tr.get(gid)
        parts = []
        seen = set()
        while t and t not in seen and len(parts) < 24:
            seen.add(t)
            g = tr_go.get(t)
            if g:
                parts.append(go_name.get(g, "?"))
            t = tr_father.get(t)
        parts.reverse()
        return "/".join(parts)

    for obj in env.objects:
        tn = obj.type.name
        if tn != "MonoBehaviour":
            continue
        try:
            node = obj._get_typetree_node()
        except Exception:
            continue
        cn = node.m_Type
        if cn not in ("TextMeshProUGUI", "Text", "ShopItemsConfig"):
            continue
        try:
            d = obj.read_typetree(nodes=node)
        except Exception:
            continue
        if cn == "ShopItemsConfig":
            shopcfg.append({"file": fn, "pid": obj.path_id, "path": path_of((d.get("m_GameObject") or {}).get("m_PathID") or 0),
                            "d": {k: v for k, v in d.items() if isinstance(v, (str, int, float, bool))},
                            "keys": sorted(d.keys())})
            continue
        go = d.get("m_GameObject") or {}
        gid = go.get("m_PathID") if isinstance(go, dict) else getattr(go, "m_PathID", None)
        txt = d.get("m_text") if cn == "TextMeshProUGUI" else d.get("m_Text")
        rows.append({"source": fn, "cls": cn, "pid": obj.path_id,
                     "go": go_name.get(gid, ""), "path": path_of(gid),
                     "text": txt if isinstance(txt, str) else ""})

with open(os.path.join(OUT, "ui_text_paths.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=1)
print("ui text rows:", len(rows))
print("\n=== ShopItemsConfig ===")
for s in shopcfg:
    print(json.dumps(s, ensure_ascii=False)[:1500])

# root-category histogram
root = collections.Counter(r["path"].split("/")[0] or "(none)" for r in rows)
print("\n=== root GameObject of each UI text component ===")
for k, v in root.most_common(40):
    print(f"   {v:5d}  {k}")

print("\n=== paths containing Debug (case-insens) ===")
for r in rows:
    if "debug" in r["path"].lower():
        print(f"   {r['path']}  ->  {r['text']!r}")
