import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)
env = UnityPy.load(os.path.join(DATA, "resources.assets"))
env.typetree_generator = gen

by_pid = {o.path_id: o for o in env.objects}
target = by_pid[23103]
d = target.read_typetree()

lines = []
def w(s=""):
    lines.append(s)

w("=== ShopItemsConfig (pid 23103) ===")
w(f"url = {d['url']}")
w(f"itemList len = {len(d['itemList'])}")

# ---- dump first 4 itemList entries in full ----
w("\n=== itemList[0..3] full ===")
for i in range(min(4, len(d["itemList"]))):
    w(json.dumps(d["itemList"][i], ensure_ascii=False, indent=1)[:3000])
    w("-" * 40)

# ---- collect every string leaf across itemList ----
strs = {}
def walk(v, path):
    if isinstance(v, str):
        strs.setdefault(path.split(".")[-1].split("[")[0], []).append(v)
    elif isinstance(v, dict):
        for k, vv in v.items():
            if k != "__node__":
                walk(vv, f"{path}.{k}")
    elif isinstance(v, (list, tuple)):
        for i, vv in enumerate(v):
            walk(vv, f"{path}[{i}]")

walk(d["itemList"], "itemList")
w("\n=== string fields present inside itemList (field -> count, sample 5) ===")
for k in sorted(strs):
    vals = strs[k]
    uniq = list(dict.fromkeys(vals))
    w(f"  {k}: n={len(vals)} uniq={len(uniq)}  sample={uniq[:5]}")

# ---- resolve registries ----
w("\n=== registries ===")
for rk in ("moduleRegistry", "consumableRegistry", "ingredientRegistry", "resourceRegistry"):
    ptr = d[rk]
    pid = ptr.get("m_PathID")
    o = by_pid.get(pid)
    if o is None:
        w(f"  {rk}: pid={pid} NOT FOUND in this file")
        continue
    try:
        rd = o.read_typetree()
        nm = rd.get("m_Name", "?")
        n = len(rd.get("m_Items", rd.get("items", [])) or [])
        w(f"  {rk}: pid={pid} type={o.type.name} name={nm} keys={sorted(rd.keys())[:14]} n_items={n}")
    except Exception as e:
        w(f"  {rk}: pid={pid} type={o.type.name} read failed {e!r}")

# ---- dump full itemList as json for later use ----
with open(os.path.join(OUT, "q1_shop_items.json"), "w", encoding="utf-8") as fh:
    json.dump({"url": d["url"], "itemList": d["itemList"]}, fh, ensure_ascii=False, indent=1)

open(os.path.join(OUT, "q1_shopconfig_summary.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines[:200]))
print("\nwrote q1_shopconfig_summary.txt + q1_shop_items.json")
