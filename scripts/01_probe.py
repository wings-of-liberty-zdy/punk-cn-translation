import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy

GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
DATA = os.path.join(GAME, "Punk_Data")

FILES = [
    "resources.assets",
    "sharedassets0.assets",
    "sharedassets1.assets",
    "sharedassets2.assets",
    "sharedassets3.assets",
    "globalgamemanagers.assets",
    "globalgamemanagers",
    "level0", "level1", "level2", "level3",
]

out = {}
for f in FILES:
    p = os.path.join(DATA, f)
    if not os.path.exists(p):
        out[f] = {"missing": True}
        continue
    try:
        env = UnityPy.load(p)
        c = collections.Counter()
        for obj in env.objects:
            c[obj.type.name] += 1
        out[f] = {
            "size": os.path.getsize(p),
            "unity_version": getattr(env, "unity_version", None) or str(getattr(env.files.get(os.path.basename(p), None), "unity_version", "")),
            "total": sum(c.values()),
            "types": dict(c.most_common()),
        }
        print(f"=== {f} ({os.path.getsize(p)/1e6:.1f} MB) total={sum(c.values())}")
        for t, n in c.most_common(40):
            print(f"    {t:35s} {n}")
    except Exception as e:
        out[f] = {"error": repr(e)}
        print(f"=== {f} ERROR {e!r}")
    print()

with open(r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump\01_probe.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("DONE")
