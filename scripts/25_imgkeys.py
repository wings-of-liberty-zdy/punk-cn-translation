import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg
DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)
env = UnityPy.load(os.path.join(DATA, "resources.assets"))
env.typetree_generator = gen
n = 0
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        node = obj._get_typetree_node()
    except Exception:
        continue
    if node.m_Type != "Image":
        continue
    d = obj.read_typetree(nodes=node)
    print("KEYS:", sorted(d.keys()))
    for k, v in d.items():
        print(f"   {k} = {v!r}"[:220])
    n += 1
    if n >= 1:
        break
