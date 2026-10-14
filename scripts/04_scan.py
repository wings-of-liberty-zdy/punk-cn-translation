import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, time
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

FILES = [
    "resources.assets",
    "sharedassets0.assets", "sharedassets1.assets", "sharedassets2.assets", "sharedassets3.assets",
    "globalgamemanagers.assets",
    "level0", "level1", "level2", "level3",
]

t0 = time.time()
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)
print("generator ready", time.time() - t0, flush=True)

_node_cache = {}


def node_for(obj):
    """Return (classname, typetree-node) with caching by script identity."""
    try:
        n = obj._get_typetree_node()
        return n.m_Type, n
    except Exception:
        return None, None


def walk(v, path, out):
    if isinstance(v, str):
        out.append((path, v))
    elif isinstance(v, dict):
        for k, vv in v.items():
            if k == "__node__":
                continue
            walk(vv, f"{path}.{k}" if path else k, out)
    elif isinstance(v, (list, tuple)):
        for i, vv in enumerate(v):
            walk(vv, f"{path}[{i}]", out)
    else:
        # PPtr-like or primitive
        pass


allrows = []
stats = {}
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    t1 = time.time()
    env = UnityPy.load(p)
    env.typetree_generator = gen
    sf = list(env.files.values())[0]

    # pathID -> GameObject name, for context
    go_names = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            try:
                d = obj.read_typetree()
                go_names[obj.path_id] = d.get("m_Name", "")
            except Exception:
                pass

    cls_count = collections.Counter()
    fail = collections.Counter()
    n_str = 0
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        cname, node = node_for(obj)
        if node is None:
            cname = "<typeless>"
        try:
            d = obj.read_typetree(nodes=node) if node is not None else obj.read_typetree()
        except Exception as e:
            fail[type(e).__name__ + ":" + str(e)[:110]] += 1
            continue
        cls_count[cname] += 1
        found = []
        walk(d, "", found)
        if not found:
            continue
        go = d.get("m_GameObject")
        gid = None
        if isinstance(go, dict):
            gid = go.get("m_PathID")
        else:
            gid = getattr(go, "m_PathID", None)
        goname = go_names.get(gid, "") if gid else ""
        for path, val in found:
            n_str += 1
            allrows.append({
                "source": fn,
                "cls": cname,
                "go": goname,
                "pid": obj.path_id if hasattr(obj, "path_id") else obj.m_PathID,
                "field": path,
                "text": val,
            })
    stats[fn] = {"mono": sum(cls_count.values()), "strings": n_str,
                 "classes": cls_count.most_common(), "fails": dict(fail.most_common(6)),
                 "secs": round(time.time() - t1, 1)}
    print(f"{fn}: mono={sum(cls_count.values())} strfields={n_str} {time.time()-t1:.1f}s fails={sum(fail.values())}", flush=True)

with open(os.path.join(OUT, "mb_strings.jsonl"), "w", encoding="utf-8") as fh:
    for r in allrows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(os.path.join(OUT, "mb_scan_stats.json"), "w", encoding="utf-8") as fh:
    json.dump(stats, fh, ensure_ascii=False, indent=1)

print("TOTAL string fields:", len(allrows), "elapsed", round(time.time() - t0, 1), flush=True)

# class histogram across everything
tot = collections.Counter()
for fn, s in stats.items():
    for c, n in s["classes"]:
        tot[c] += n
print("\n=== class histogram (top 60) ===")
for c, n in tot.most_common(60):
    print(f"  {n:6d}  {c}")
