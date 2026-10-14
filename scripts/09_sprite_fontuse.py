import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
FILES = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
         "sharedassets2.assets", "sharedassets3.assets", "globalgamemanagers.assets",
         "level0", "level1", "level2", "level3"]
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)

# which font assets do TMP components reference + TMP_Settings
font_use = collections.Counter()
tem_texts = []
sprites = []
textures = []
settings = []
tmp_sprite_assets = []
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    for obj in env.objects:
        t = obj.type.name
        if t == "Sprite":
            try:
                d = obj.read_typetree()
                r = d.get("m_Rect") or {}
                sprites.append({"file": fn, "name": d.get("m_Name"),
                                "w": r.get("width"), "h": r.get("height")})
            except Exception:
                pass
        elif t == "Texture2D":
            try:
                d = obj.read_typetree()
                textures.append({"file": fn, "name": d.get("m_Name"),
                                 "w": d.get("m_Width"), "h": d.get("m_Height"),
                                 "fmt": d.get("m_TextureFormat")})
            except Exception:
                pass
        elif t == "MonoBehaviour":
            try:
                node = obj._get_typetree_node()
            except Exception:
                continue
            cn = node.m_Type
            if cn in ("TextMeshProUGUI", "Text"):
                try:
                    d = obj.read_typetree(nodes=node)
                except Exception:
                    continue
                fa = d.get("m_fontAsset")
                fid = fa.get("m_PathID") if isinstance(fa, dict) else getattr(fa, "m_PathID", None)
                font_use[(cn, fn, fid)] += 1
            elif cn == "TMP_Settings":
                try:
                    settings.append({"file": fn, "pid": obj.path_id, "d": json.loads(json.dumps(obj.read_typetree(nodes=node), default=str))})
                except Exception as e:
                    settings.append({"file": fn, "err": repr(e)})
            elif cn == "TMP_SpriteAsset":
                try:
                    d = obj.read_typetree(nodes=node)
                    tmp_sprite_assets.append({"file": fn, "name": d.get("m_Name"),
                                              "spriteCount": len(d.get("m_SpriteGlyphTable") or [])})
                except Exception:
                    pass

json.dump(sprites, open(os.path.join(OUT, "sprites.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(textures, open(os.path.join(OUT, "textures.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"font_use": {f"{a}|{b}|{c}": n for (a, b, c), n in font_use.items()},
           "tmp_settings": settings, "tmp_sprite_assets": tmp_sprite_assets},
          open(os.path.join(OUT, "font_use.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("=== font usage by UI text components ===")
for (cn, fn, fid), n in font_use.most_common(30):
    print(f"  {n:5d}  {cn}  file={fn}  fontAssetPathID={fid}")
print("\n=== TMP_Settings ===")
for s in settings:
    print(json.dumps(s, ensure_ascii=False)[:2500])
print("\n=== TMP_SpriteAsset ===", tmp_sprite_assets)
print("\n=== sprite/texture counts ===", len(sprites), len(textures))
print("\n=== sprites whose name suggests baked text/logo/title/menu/button ===")
KW = ("text", "title", "logo", "menu", "button", "label", "hud", "prompt", "font", "letter",
      "word", "banner", "sign", "key", "tutorial", "hint", "tile", "card")
for s in sprites:
    nm = (s["name"] or "").lower()
    if any(k in nm for k in KW):
        print(f"   {s['file']:24s} {s['name']!r} {s['w']}x{s['h']}")
