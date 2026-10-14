import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, collections, os
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]

print("=========== TextMeshProUGUI m_text (606) ===========")
tmp = [r for r in rows if r["cls"] == "TextMeshProUGUI" and r["field"] == "m_text"]
for r in tmp[:80]:
    print(f"  [{r['source']}|{r['go']}] {r['text']!r}")
print("   ... total", len(tmp))
print("   nonempty:", sum(1 for r in tmp if r["text"].strip()))
print("   distinct nonempty:", len({r["text"] for r in tmp if r["text"].strip()}))

print("\n=========== legacy Text m_Text (182) ===========")
ut = [r for r in rows if r["cls"] == "Text" and r["field"] == "m_Text"]
for r in ut[:40]:
    print(f"  [{r['source']}|{r['go']}] {r['text']!r}")
print("   nonempty:", sum(1 for r in ut if r["text"].strip()))

print("\n=========== ScriptableObject-ish classes: full field lists ===========")
DATA_CLASSES = ["ModuleData", "WeaponModuleData", "ProjectileWeaponData", "Unit", "Enemy",
                "StatusEffectForUnit", "InputActionAsset", "AudioDatabase", "DropTable",
                "SavablesCollection", "ModuleEffectFieldSegment", "DamagableResource", "Health"]
per = collections.defaultdict(collections.Counter)
for r in rows:
    per[r["cls"]][r["field"]] += 1
for c in DATA_CLASSES:
    if c not in per:
        continue
    print(f"-- {c}")
    for f, n in per[c].most_common(25):
        print(f"     {n:5d}  {f}")

print("\n=========== ModuleData.description values (73) ===========")
md = [r for r in rows if r["cls"] == "ModuleData" and r["field"] == "description"]
for r in md[:40]:
    print(f"  [{r['go']}] {r['text']!r}")
print("   total", len(md))

print("\n=========== WeaponModuleData.description values (60) ===========")
wd = [r for r in rows if r["cls"] == "WeaponModuleData" and r["field"] == "description"]
for r in wd[:25]:
    print(f"  [{r['go']}] {r['text']!r}")
print("   total", len(wd))
