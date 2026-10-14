import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections, re
ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
D = os.path.join(ROOT, "data", "dump")
kept = json.load(open(os.path.join(ROOT, "data", "strings_raw.json"), encoding="utf-8"))
cl = [json.loads(l) for l in open(os.path.join(D, "strings_all_classified.jsonl"), encoding="utf-8")]

def fs(k):
    return set(k.split("flag=")[1].split(",")) if "flag=" in k else set()

NOTRANS = {"key_label", "credits"}
DEV = {"debug_menu", "perf_overlay", "test_canvas", "local_config"}
core = [r for r in kept if not (fs(r["key_or_context"]) & (NOTRANS | DEV)) and "placeholder" not in fs(r["key_or_context"])]

print("SOURCE BREAKDOWN (kept):")
s = collections.Counter(r["source"].split(":")[0] for r in kept)
for k, v in s.most_common():
    print(f"   {v:5d}  {k}")
print("\nFIELD BREAKDOWN (kept):")
f = collections.Counter(r["key_or_context"].split("|")[1] for r in kept)
for k, v in f.most_common(30):
    print(f"   {v:5d}  {k}")
print("\nCORE per category: entries/distinct/chars")
for c in ["ui_menu", "tutorial_hint", "item_module_desc", "dialogue_story", "other"]:
    rs = [r for r in core if r["category"] == c]
    u = {r["text"] for r in rs}
    print(f"   {c:18s} {len(rs):4d} / {len(u):4d} / {sum(len(t) for t in u)}")
print("\nCORE 3 reps per category (shortest-typical, exact source text):")
for c in ["ui_menu", "tutorial_hint", "item_module_desc", "dialogue_story", "other"]:
    rs = sorted({r["text"]: r for r in core if r["category"] == c}.values(), key=lambda x: -len(x["text"]))
    print(f"  -- {c}")
    for r in rs[:3]:
        print(f"       {r['text']!r}")
print("\nCORE totals: entries=%d distinct=%d chars_distinct=%d" % (
    len(core), len({r["text"] for r in core}), sum(len(t) for t in {r["text"] for r in core})))
print("\nTOP SOURCES for CORE:")
sc = collections.Counter(r["source"] for r in core)
for k, v in sc.most_common(15):
    print(f"   {v:5d}  {k}")
