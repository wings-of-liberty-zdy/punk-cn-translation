import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, time
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

TARGET_PID = 23103

gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)

p = os.path.join(DATA, "resources.assets")
env = UnityPy.load(p)
env.typetree_generator = gen
print("loaded", p, "objects:", len(env.objects), flush=True)

result = {"target_pid": TARGET_PID, "found": False}

# ---- 1. locate target + scan every MonoBehaviour for http-ish strings ----
http_hits = []
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        d = obj.read_typetree()
    except Exception:
        continue
    script = d.get("m_Script")
    sname = None
    if script is not None:
        try:
            sname = script.read().m_Name
        except Exception:
            sname = None
    if obj.path_id == TARGET_PID:
        result["found"] = True
        result["script_name"] = sname
        result["keys"] = sorted(d.keys())
        result["typetree"] = d
    # hunt for url-ish strings anywhere in the tree
    stack = [(k, v) for k, v in d.items() if k != "__node__"]
    while stack:
        path, v = stack.pop()
        if isinstance(v, str):
            if "http" in v or ".csv" in v or "docs.google" in v:
                http_hits.append({"pid": obj.path_id, "script": sname, "path": path, "value": v})
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if kk != "__node__":
                    stack.append((f"{path}.{kk}", vv))
        elif isinstance(v, (list, tuple)):
            for i, vv in enumerate(v):
                stack.append((f"{path}[{i}]", vv))

result["http_hits"] = http_hits
print("=== http-ish string hits in resources.assets ===")
for h in http_hits:
    print(f"  pid={h['pid']} script={h['script']} path={h['path']}")
    print(f"     {h['value']}")

with open(os.path.join(OUT, "q1_shopconfig_raw.json"), "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)

if result["found"]:
    d = result["typetree"]
    print("\n=== pid 23103 script:", result["script_name"])
    print("=== top-level keys ===")
    for k in result["keys"]:
        v = d[k]
        if isinstance(v, list):
            print(f"  {k}: list[{len(v)}]")
        elif isinstance(v, dict):
            print(f"  {k}: dict keys={sorted(v.keys())[:12]}")
        else:
            print(f"  {k}: {v!r}"[:400])
else:
    print("!! pid 23103 not found as MonoBehaviour in resources.assets")
print("\nwrote q1_shopconfig_raw.json")
