import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, collections
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg
DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)
env = UnityPy.load(os.path.join(DATA, "resources.assets"))
env.typetree_generator = gen

sprite_name = {}
sp_fail = 0
for obj in env.objects:
    if obj.type.name == "Sprite":
        try:
            sprite_name[obj.path_id] = obj.read_typetree().get("m_Name")
        except Exception as e:
            sp_fail += 1
print("sprites indexed:", len(sprite_name), "fail:", sp_fail)
print("sample:", list(sprite_name.items())[:3])
print("has 1186:", sprite_name.get(1186))

cnt = 0
hit = 0
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        node = obj._get_typetree_node()
    except Exception:
        continue
    if node.m_Type != "Image":
        continue
    cnt += 1
    d = obj.read_typetree(nodes=node)
    sp = d.get("m_Sprite")
    sid = sp.get("m_PathID") if isinstance(sp, dict) else None
    nm = sprite_name.get(sid)
    if nm:
        hit += 1
        if hit <= 5:
            print("HIT", sid, nm)
print("Image components:", cnt, "with resolved sprite:", hit)
