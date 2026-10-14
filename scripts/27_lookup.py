import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
d = json.load(open(r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump\image_sprites_all.json", encoding="utf-8"))
WANT = ("MainMenu_placeholders_0", "MainMenu_placeholders_1", "UI_GamepadLayout",
        "Sprite InstrumentIcons_1", "Ui_ButtonHints_0", "Ui_ButtonHints_1", "Ui_ButtonHints_6",
        "Buttonhints_PC_Space", "Buttonhints_PC_Shift", "Buttonhints_PC_Esc",
        "Buttonhints_PC_MouseLeft", "Buttonhints_PC_MouseRight", "Cursor",
        "Sprite PopupPanel", "Sprite Vignette", "AllAxis_Outline", "MAP_Reference")
for x in d:
    if x["sprite"] in WANT:
        print(f"{x['file']:20s} {x['cls']:14s} {x['path']:62s} -> {x['sprite']}")
