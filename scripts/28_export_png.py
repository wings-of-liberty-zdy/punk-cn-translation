import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump\png"
os.makedirs(OUT, exist_ok=True)

# (file, sprite name) -> export the sprite (or its texture) as PNG
WANT = [
    ("level1", "MainMenu_placeholders_0"),
    ("level1", "UI_GamepadLayout"),
    ("sharedassets0.assets", "Buttonhints_PC_Space"),
    ("sharedassets0.assets", "Buttonhints_PC_Shift"),
    ("sharedassets0.assets", "Buttonhints_PC_Esc"),
    ("sharedassets3.assets", "Sprite InstrumentIcons_1"),
]

for fn, want in WANT:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        print("missing", fn); continue
    env = UnityPy.load(p)
    for obj in env.objects:
        if obj.type.name != "Sprite":
            continue
        try:
            d = obj.read()
        except Exception:
            continue
        if d.m_Name != want:
            continue
        try:
            img = d.image
            safe = want.replace(" ", "_").replace("/", "_")
            path = os.path.join(OUT, f"{fn}__{safe}.png")
            img.save(path)
            print("saved", path, img.size)
        except Exception as e:
            print("export fail", fn, want, repr(e))
        break
