import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, traceback
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
DATA = os.path.join(GAME, "Punk_Data")
MANAGED = os.path.join(DATA, "Managed")

env = UnityPy.load(os.path.join(DATA, "resources.assets"))
sf = list(env.files.values())[0]
print("unity:", sf.unity_version)
print("num types in SerializedFile:", len(sf.types))
# do any MonoBehaviour types carry embedded nodes?
print("SerializedType attrs:", [a for a in dir(sf.types[0]) if not a.startswith("_")])
_t0 = sf.types[0]
print(" sample type:", {a: str(getattr(_t0, a))[:80] for a in ("class_id", "m_Type", "nodes", "script_type_index", "m_Script") if hasattr(_t0, a)})
for t in sf.types:
    nm = getattr(t, "m_Type", None)
    if nm in ("MonoBehaviour", "MonoScript") or getattr(t, "class_id", 0) == 114:
        print(" type", t.class_id, nm, "nodes:", len(t.nodes) if t.nodes else 0)

print("\n-- building TypeTreeGenerator --")
gen = TypeTreeGenerator(sf.unity_version)
try:
    gen.load_local_game(DATA)   # folder containing Managed/
    print("load_local_game(DATA) OK")
except BaseException as e:
    traceback.print_exc()
    print("load_local_game(DATA) failed:", repr(e))
    try:
        gen.load_local_dll_folder(MANAGED)
        print("load_local_dll_folder OK")
    except BaseException as e2:
        traceback.print_exc()
        print("load_local_dll_folder failed:", repr(e2))

# try Punk.Main.dll explicitly
try:
    gen.load_dll(os.path.join(MANAGED, "Punk.Main.dll"))
    print("load_dll(Punk.Main.dll) OK")
except Exception as e:
    print("load_dll failed:", repr(e))

env.typetree_generator = gen
print("assigned typetree_generator")

# now try reading a MonoBehaviour
ok = 0
fail = 0
sample = []
errs = collections.Counter()
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        d = obj.read()
        ok += 1
        if ok <= 3:
            sample.append({k: (str(v)[:200]) for k, v in d.__dict__.items()})
    except Exception as e:
        fail += 1
        errs[type(e).__name__ + ": " + str(e)[:120]] += 1
    if ok + fail > 400:
        break
print("MonoBehaviour read ok:", ok, "fail:", fail)
for k, v in errs.most_common(10):
    print("   ", v, k)
for s in sample:
    print(json.dumps(s, ensure_ascii=False)[:600])
