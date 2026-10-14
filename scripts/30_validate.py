import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
p = os.path.join(ROOT, "data", "strings_raw.json")
d = json.load(open(p, encoding="utf-8"))
print("strings_raw.json entries:", len(d))
keys = collections.Counter(tuple(sorted(r.keys())) for r in d)
print("key shapes:", dict(keys))
cats = collections.Counter(r["category"] for r in d)
print("categories:", dict(cats))
bad = [r for r in d if not isinstance(r.get("source"), str) or not isinstance(r.get("text"), str)
       or not isinstance(r.get("category"), str) or not isinstance(r.get("key_or_context"), str)]
print("schema violations:", len(bad))
print("distinct text:", len({r["text"] for r in d}))
print("chars all:", sum(len(r["text"]) for r in d), "chars distinct:", sum(len(t) for t in {r["text"] for r in d}))
print("\nsample records:")
for r in d[:3]:
    print("  ", json.dumps(r, ensure_ascii=False)[:200])

# ---- verify D:\SteamLibrary untouched ----
GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
newest = []
for root, dirs, files in os.walk(GAME):
    for f in files:
        fp = os.path.join(root, f)
        try:
            newest.append((os.path.getmtime(fp), fp))
        except OSError:
            pass
newest.sort(reverse=True)
print(f"\nD:\\...\\PUNK Playtest: {len(newest)} files")
print("newest 6 by mtime (should all predate this session):")
import datetime
for m, f in newest[:6]:
    print("   ", datetime.datetime.fromtimestamp(m).isoformat(), os.path.relpath(f, GAME))
print("\nnow:", datetime.datetime.now().isoformat())
print("\nfiles in Punk_Data (top level) — no new artifacts expected:")
for f in sorted(os.listdir(os.path.join(GAME, "Punk_Data"))):
    print("   ", f)
