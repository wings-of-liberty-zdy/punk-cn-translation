import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)

FILES = sys.argv[1:] or ["resources.assets"]
for fn in FILES:
    env = UnityPy.load(os.path.join(DATA, fn))
    env.typetree_generator = gen
    cls = collections.Counter()
    withstr = collections.Counter()
    fails = collections.Counter()
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tt = obj.read_typetree()
        except Exception as e:
            fails[type(e).__name__ + ":" + str(e)[:100]] += 1
            continue
        node = tt.get("__node__")
        nm = getattr(node, "m_Name", None) or str(node)
        cls[nm] += 1
        for k, v in tt.items():
            if isinstance(v, str) and v.strip():
                withstr[nm] += 1
                break
    print(f"### {fn}: mono={sum(cls.values())} classes={len(cls)} withstring={sum(withstr.values())}")
    for k, v in withstr.most_common(60):
        print(f"   {v:6d}  {k}")
    if fails:
        print("   FAILS:", dict(fails.most_common(5)))
    print()
