import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os
import UnityPy

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump\png"
os.makedirs(OUT, exist_ok=True)
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
         "sharedassets2.assets", "sharedassets3.assets", "globalgamemanagers.assets",
         "level0", "level1", "level2", "level3"]
WANT = {"MainMenu_placeholders_0", "UI_GamepadLayout", "Buttonhints_PC_MouseLeft"}

for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    for obj in env.objects:
        if obj.type.name != "Sprite":
            continue
        try:
            d = obj.read()
        except Exception:
            continue
        if d.m_Name not in WANT:
            continue
        try:
            img = d.image
            path = os.path.join(OUT, f"{fn}__{d.m_Name.replace(' ', '_')}.png")
            img.save(path)
            print("saved", path, img.size)
        except Exception as e:
            print("fail", fn, d.m_Name, repr(e))
