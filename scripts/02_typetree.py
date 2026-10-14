import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
DATA = os.path.join(GAME, "Punk_Data")
MANAGED = os.path.join(DATA, "Managed")

# unity version
env = UnityPy.load(os.path.join(DATA, "globalgamemanagers"))
print("unity_version globalgamemanagers:", env.unity_version)
for f in list(env.files.values()):
    print("  file:", f.name, getattr(f, "unity_version", None), getattr(f, "version", None))
    break

env2 = UnityPy.load(os.path.join(DATA, "resources.assets"))
print("unity_version resources.assets:", env2.unity_version)

gen = TypeTreeGenerator(env2.unity_version if isinstance(env2.unity_version, str) else "2021.3.0f1")
gen.load_local_game(MANAGED)
print("TypeTreeGenerator loaded, unity ver:", gen.unity_version)

# find some MonoBehaviour script names
ms = []
for obj in env2.objects:
    if obj.type.name == "MonoBehaviour":
        try:
            d = obj.read(check_read=False)
            s = getattr(d, "m_Script", None)
            name = None
            if s is not None:
                name = getattr(s, "m_Name", None) or getattr(getattr(s, "read", lambda: None)(), "m_Name", None)
            ms.append(name)
        except Exception:
            ms.append(None)
c = collections.Counter(ms)
print("distinct scripts:", len(c), "none:", c.get(None))
for k, v in c.most_common(60):
    print(f"   {k}: {v}")
