import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
gen = tg.TypeTreeGenerator("6000.3.4f1")
gen.load_local_dll_folder(MANAGED)

# ---- TextAsset contents ----
print("===== TextAsset objects =====")
for fn in ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
           "sharedassets2.assets", "sharedassets3.assets", "globalgamemanagers.assets",
           "level0", "level1", "level2", "level3"]:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    env = UnityPy.load(p)
    env.typetree_generator = gen
    for obj in env.objects:
        if obj.type.name == "TextAsset":
            try:
                d = obj.read()
                raw = bytes(d.m_Script) if hasattr(d, "m_Script") else b""
                txt = raw.decode("utf-8", errors="replace")
                print(f"-- {fn} {d.m_Name!r} size={len(raw)}")
                print("   " + txt[:900].replace("\n", "\n   "))
            except Exception as e:
                print("ERR", fn, repr(e))

# ---- prose sweep over all extracted mb strings ----
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]
print(f"\n===== prose-like strings across all {len(rows)} extracted fields =====")
SKIPLEAF = ("m_name", "bytesstring", "prefabmodifications")
cand = []
for r in rows:
    t = r["text"]
    leaf = r["field"].split(".")[-1].split("[")[0].lower()
    if leaf in SKIPLEAF:
        continue
    s = t.strip()
    if len(s) < 12:
        continue
    letters = sum(c.isalpha() for c in s)
    if letters < 8:
        continue
    if " " not in s and "\n" not in s:
        continue
    # sentence-ish: has a lowercase word of >=3 chars that is a common english word
    words = re.findall(r"[A-Za-z]{3,}", s)
    if not words:
        continue
    low = sum(1 for w in words if w.islower())
    score = low / len(words)
    if score >= 0.3 or len(s) > 60:
        cand.append(r)
seen = set()
uniq = []
for r in cand:
    k = r["text"]
    if k in seen:
        continue
    seen.add(k)
    uniq.append(r)
print("candidates:", len(uniq))
for r in sorted(uniq, key=lambda x: -len(x["text"])):
    print(f"  [{r['cls']}.{r['field']}] ({r['source']}) len={len(r['text'])} {r['text']!r}")
