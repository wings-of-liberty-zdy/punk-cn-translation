import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, collections
import UnityPy
DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Resources"
for fn in ["unity default resources", "unity_builtin_extra"]:
    p = os.path.join(DATA, fn)
    env = UnityPy.load(p)
    c = collections.Counter(o.type.name for o in env.objects)
    print(f"== {fn}: {sum(c.values())} objects")
    for k, v in c.most_common(12):
        print(f"     {v:5d}  {k}")
    mb = [o for o in env.objects if o.type.name == "MonoBehaviour"]
    print("   MonoBehaviours:", len(mb))
    # any string assets with readable text?
    for o in env.objects:
        if o.type.name in ("TextAsset",):
            d = o.read()
            print("   TextAsset:", d.m_Name)
