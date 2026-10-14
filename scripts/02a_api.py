import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, inspect
import UnityPy
from UnityPy import environment as envmod

GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
DATA = os.path.join(GAME, "Punk_Data")

print("UnityPy", UnityPy.__version__)
print("Environment attrs:", [a for a in dir(UnityPy.Environment) if not a.startswith("__")])
print()
import UnityPy.helpers.TypeTreeGenerator as tg
print("TypeTreeGenerator module:", [a for a in dir(tg) if not a.startswith("_")])
print(inspect.signature(tg.TypeTreeGenerator.__init__))
print([a for a in dir(tg.TypeTreeGenerator) if not a.startswith("_")])
print()
env = UnityPy.load(os.path.join(DATA, "resources.assets"))
print("env.files:", type(env.files), len(env.files))
for k, f in list(env.files.items())[:3]:
    print("  key:", k, type(f))
    print("  attrs:", [a for a in dir(f) if not a.startswith("_")][:40])
    print("  version:", getattr(f, "version", None), "unity_version:", getattr(f, "unity_version", None), "big_id_enabled:", getattr(f, "big_id_enabled", None))
    print("  header:", getattr(f, "header", None))
    break
