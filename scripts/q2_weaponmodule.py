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

envs = {}
allobj = {}
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    e = UnityPy.load(p)
    e.typetree_generator = gen
    envs[fn] = e
    for o in e.objects:
        allobj[(fn, o.path_id)] = o
print("total objects:", len(allobj))


def clsname(o):
    try:
        return o._get_typetree_node().m_Type
    except Exception:
        return None


# ---------------- 1. every object whose typetree has displayName ----------------
withname = collections.Counter()
weapon = []
for (fn, pid), o in allobj.items():
    if o.type.name != "MonoBehaviour":
        continue
    try:
        d = o.read_typetree()
    except Exception:
        continue
    if "displayName" not in d:
        continue
    cn = clsname(o)
    withname[(fn, cn)] += 1
    if cn == "WeaponModuleData":
        weapon.append({"file": fn, "pid": pid, "d": d})

print("\n=== objects carrying a displayName field (file, class) -> count ===")
for (fn, cn), v in withname.most_common(40):
    print(f"  {v:5d}  {fn}  {cn}")

print(f"\n=== WeaponModuleData instances: {len(weapon)} ===")
if weapon:
    print("--- first instance full typetree ---")
    print(json.dumps(weapon[0]["d"], ensure_ascii=False, indent=1)[:3000])
    print("\n--- all keys seen across instances ---")
    ks = collections.Counter()
    for w in weapon:
        for k in w["d"]:
            ks[k] += 1
    print("   ", dict(ks))

# ---------------- 2. module registry contents ----------------
res = envs["resources.assets"]
res_by_pid = {o.path_id: o for o in res.objects}
shop = res_by_pid[23103].read_typetree()

regs = {}
for rk in ("moduleRegistry", "consumableRegistry", "ingredientRegistry", "resourceRegistry"):
    pid = shop[rk]["m_PathID"]
    o = allobj.get(("resources.assets", pid))
    if o is None:
        regs[rk] = {"pid": pid, "missing": True}
        continue
    rd = o.read_typetree()
    items = rd.get("itemList") or []
    pids = []
    for x in items:
        if isinstance(x, dict) and "m_PathID" in x:
            pids.append(x["m_PathID"])
        elif isinstance(x, dict):
            pids.append(None)
    regs[rk] = {"pid": pid, "cls": clsname(o), "n": len(items), "pids": pids[:80]}
    print(f"\n=== {rk} pid={pid} cls={clsname(o)} n={len(items)}")
    for x in items[:5]:
        print("    ", json.dumps(x, ensure_ascii=False)[:220])

json.dump(regs, open(os.path.join(OUT, "q2_registries.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------------- 3. referrers of each WeaponModuleData ----------------
referrers = collections.defaultdict(set)
for (fn, pid), o in allobj.items():
    if o.type.name != "MonoBehaviour":
        continue
    try:
        d = o.read_typetree()
    except Exception:
        continue
    cn = clsname(o)

    def scan2(v, path):
        if isinstance(v, dict):
            if "m_PathID" in v and set(v.keys()) <= {"m_FileID", "m_PathID"}:
                p = v.get("m_PathID")
                if p:
                    referrers[p].add((cn, fn, pid, path))
                return
            for k, vv in v.items():
                if k != "__node__":
                    scan2(vv, f"{path}.{k}")
        elif isinstance(v, (list, tuple)):
            for i, vv in enumerate(v):
                scan2(vv, f"{path}[{i}]")
    scan2(d, "")

shop_unlock = set()
for it in shop["itemList"]:
    for ur in it.get("unlockRequirements") or []:
        if ur.get("m_PathID"):
            shop_unlock.add(ur["m_PathID"])
reg_pids = set()
for rk, info in regs.items():
    for p in info.get("pids", []):
        if p:
            reg_pids.add(p)

rows = []
for w in weapon:
    pid = w["pid"]
    d = w["d"]
    icon = d.get("icon")
    rows.append({
        "pid": pid,
        "displayName": d.get("displayName"),
        "icon_pid": (icon or {}).get("m_PathID") if isinstance(icon, dict) else None,
        "weapon_pid": (d.get("weapon") or {}).get("m_PathID") if isinstance(d.get("weapon"), dict) else None,
        "keys": sorted(d.keys()),
        "in_moduleRegistry": pid in reg_pids,
        "in_shop_unlock": pid in shop_unlock,
        "referrers": [list(x) for x in sorted(referrers.get(pid, []))],
    })

print(f"\n=== {len(rows)} WeaponModuleData: registry / shop / referrer status ===")
print(f"  in moduleRegistry: {sum(1 for r in rows if r['in_moduleRegistry'])}")
print(f"  in shop unlockRequirements: {sum(1 for r in rows if r['in_shop_unlock'])}")
print(f"  has referrers: {sum(1 for r in rows if r['referrers'])}")
for r in rows:
    print(f"  pid={r['pid']:>7} {r['displayName']!r:32} icon={r['icon_pid']} reg={int(r['in_moduleRegistry'])} shop={int(r['in_shop_unlock'])}")
    for x in r["referrers"][:8]:
        print(f"        <- {x[0]} pid={x[2]} path={x[3]}")

json.dump(rows, open(os.path.join(OUT, "q2_weaponmodule_instances.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote q2_weaponmodule_instances.json + q2_registries.json")
