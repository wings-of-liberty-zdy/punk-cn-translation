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

CJK = [(0x4E00, 0x9FFF), (0x3000, 0x303F), (0xFF00, 0xFFEF), (0x3400, 0x4DBF)]


def has_cjk(cp):
    return any(a <= cp <= b for a, b in CJK)


fonts = []
legacy = []
textures = []
for fn in FILES:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    for obj in env.objects:
        tn = obj.type.name
        if tn == "MonoBehaviour":
            try:
                node = obj._get_typetree_node()
            except Exception:
                continue
            if node.m_Type not in ("TMP_FontAsset", "TMP_SpriteAsset", "TMP_StyleSheet", "TMP_Settings"):
                continue
            try:
                d = obj.read_typetree(nodes=node)
            except Exception as e:
                print("ERR", node.m_Type, e)
                continue
            if node.m_Type == "TMP_FontAsset":
              try:
                fi = d.get("m_FaceInfo") or {}
                chars = d.get("m_CharacterTable") or []
                glyphs = d.get("m_GlyphTable") or []
                cps = []
                for c in chars:
                    try:
                        cps.append(int(c.get("m_Unicode", -1)))
                    except Exception:
                        pass
                cjk_n = sum(1 for c in cps if has_cjk(c))
                atlas = d.get("m_AtlasTextures") or []
                atlas_ids = [a.get("m_PathID") if isinstance(a, dict) else getattr(a, "m_PathID", None) for a in atlas]
                fonts.append({
                    "file": fn, "pid": obj.path_id if hasattr(obj, "path_id") else obj.m_PathID,
                    "m_Name": d.get("m_Name"),
                    "Name": d.get("Name"),
                    "m_Version": d.get("m_Version"),
                    "familyName": fi.get("m_FamilyName"),
                    "styleName": fi.get("m_StyleName"),
                    "pointSize": fi.get("m_PointSize"),
                    "scale": fi.get("m_Scale"),
                    "lineHeight": fi.get("m_LineHeight"),
                    "faceFlags": fi.get("m_FaceFlags"),
                    "atlasPopulationMode": d.get("m_AtlasPopulationMode"),
                    "atlasWidth": d.get("m_AtlasWidth"), "atlasHeight": d.get("m_AtlasHeight"),
                    "atlasTextureIds": atlas_ids,
                    "atlasTextureCount": d.get("m_AtlasTextureIndex"),
                    "glyphCount": len(glyphs), "charCount": len(chars),
                    "cjkCharCount": cjk_n,
                    "charSample": [chr(c) for c in cps[:40]],
                    "unicodeMin": min(cps) if cps else None, "unicodeMax": max(cps) if cps else None,
                    "isMultiAtlas": d.get("m_IsMultiAtlasTexturesEnabled"),
                    "fallbackCount": len(d.get("m_FallbackFontAssetTable") or []),
                    "sourceFontFile": (d.get("m_SourceFontFile") or {}).get("m_PathID") if isinstance(d.get("m_SourceFontFile"), dict) else None,
                    "rawKeys": sorted(d.keys()),
                })
              except Exception as e:
                print("FONTERR", repr(e))
        elif tn in ("Texture2D",):
            try:
                d = obj.read_typetree()
                textures.append({"file": fn, "pid": obj.path_id, "name": d.get("m_Name"),
                                 "w": d.get("m_Width"), "h": d.get("m_Height")})
            except Exception:
                pass
        elif tn == "Font":
            try:
                d = obj.read_typetree()
                legacy.append({"file": fn, "pid": obj.path_id, "m_Name": d.get("m_Name"),
                               "fontNames": d.get("m_FontNames"), "keys": sorted(d.keys())})
            except Exception as e:
                print("LEGACYERR", repr(e))

with open(os.path.join(OUT, "fonts.json"), "w", encoding="utf-8") as fh:
    json.dump({"tmp": fonts, "legacy": legacy}, fh, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "textures.json"), "w", encoding="utf-8") as fh:
    json.dump(textures, fh, ensure_ascii=False, indent=1)

print(f"=== TMP_FontAsset: {len(fonts)} ===")
for f in fonts:
    print(json.dumps({k: v for k, v in f.items() if k not in ("charSample", "rawKeys")}, ensure_ascii=False))
    print("     sample chars:", "".join(f["charSample"])[:80].replace("\n", "\\n"))
print(f"\n=== legacy Font: {len(legacy)} ===")
for f in legacy:
    print(json.dumps(f, ensure_ascii=False)[:400])
print(f"\n=== Texture2D: {len(textures)} ===")
