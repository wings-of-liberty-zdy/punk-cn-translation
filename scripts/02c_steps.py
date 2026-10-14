import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, traceback
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
step = sys.argv[1] if len(sys.argv) > 1 else "dll"

print("step:", step, flush=True)
gen = tg.TypeTreeGenerator("6000.3.4f1")
print("ctor ok", flush=True)

if step == "dll":
    gen.load_dll(os.path.join(MANAGED, "Punk.Main.dll"))
    print("load_dll ok", flush=True)
elif step == "folder":
    gen.load_local_dll_folder(MANAGED)
    print("load_local_dll_folder ok", flush=True)
elif step == "game":
    gen.load_local_game(DATA)
    print("load_local_game ok", flush=True)
elif step == "nodes":
    gen.load_dll(os.path.join(MANAGED, "Punk.Main.dll"))
    n = gen.get_nodes("Punk.Main", "Punk.Main.WeaponData")
    print("nodes:", n)

print("all done", flush=True)
