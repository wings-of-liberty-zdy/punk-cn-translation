import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, collections
ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
D = os.path.join(ROOT, "data", "dump")
cl = [json.loads(l) for l in open(os.path.join(D, "strings_all_classified.jsonl"), encoding="utf-8")]
kept = [c for c in cl if c["decision"] == "keep"]
out = []
def w(s=""):
    out.append(str(s))

def flagset(k):
    if "flag=" in k:
        return set(k.split("flag=")[1].split(","))
    return set()

w("=== kept: category x distinct ===")
for cat in ["ui_menu", "tutorial_hint", "item_module_desc", "dialogue_story", "other"]:
    rs = [c for c in kept if c["category"] == cat]
    u = {c["text"] for c in rs}
    w(f"  {cat:18s} entries={len(rs):5d} distinct={len(u):5d} chars={sum(len(t) for t in u):6d}")
w()
w("=== whole kept set ===")
w(f"  entries={len(kept)} distinct={len({c['text'] for c in kept})} "
  f"chars_all={sum(len(c['text']) for c in kept)} chars_distinct={sum(len(t) for t in {c['text'] for c in kept})}")
w()
w("=== 'other' breakdown by flag ===")
cnt = collections.Counter()
for c in kept:
    if c["category"] != "other":
        continue
    f = flagset(c["key_or_context"])
    tag = ",".join(sorted(f)) if f else ("dll-residual" if c["source"] == "Punk.Main.dll" else "asset-residual")
    cnt[tag] += 1
for k, v in cnt.most_common():
    w(f"  {v:5d}  {k}")
w()
w("=== translatable-subset math ===")
NOTRANS = [c for c in kept if flagset(c["key_or_context"]) & {"key_label", "credits"}]
DEVONLY = [c for c in kept if flagset(c["key_or_context"]) & {"debug_menu", "perf_overlay", "test_canvas", "local_config"}]
PLACE = [c for c in kept if "placeholder" in flagset(c["key_or_context"])]
excl = {id(c) for c in NOTRANS} | {id(c) for c in DEVONLY} | {id(c) for c in PLACE}
core = [c for c in kept if id(c) not in excl]
w(f"  key_label+credits (not translated)      : {len(NOTRANS)}")
w(f"  dev/perf/test overlay                  : {len(DEVONLY)}")
w(f"  runtime placeholders                   : {len(PLACE)}")
w(f"  CORE player-facing to translate        : {len(core)} entries / {len({c['text'] for c in core})} distinct / "
  f"{sum(len(t) for t in {c['text'] for c in core})} chars(distinct)")
w()
w("=== CORE breakdown by category ===")
cc = collections.Counter(c["category"] for c in core)
for k, v in cc.most_common():
    w(f"  {v:5d}  {k}")
w()
w("=== 6 representative per category (CORE only, longest first) ===")
for cat in ["ui_menu", "tutorial_hint", "item_module_desc", "dialogue_story", "other"]:
    rs = sorted({c["text"]: c for c in core if c["category"] == cat}.values(), key=lambda x: -len(x["text"]))
    w(f"-- {cat} ({len(rs)})")
    for r in rs[:6]:
        w(f"     len={len(r['text']):3d} {r['text']!r}")
w()
w("=== CORE longest ===")
for t in sorted({c["text"] for c in core}, key=len, reverse=True)[:5]:
    w(f"  len={len(t)} {t!r}")
w()
w("=== all remaining 'unclassified field' rejects (verify nothing real lost) ===")
for c in cl:
    if c["decision"] == "reject" and "unclassified field" in c["reason"]:
        w(f"  {c['key_or_context']}  ->  {c['text']!r}")
w()
w("=== all rejected with reason containing 'non-text field' but text looks prose-ish ===")
import re
for c in cl:
    if c["decision"] == "reject" and "non-text field" in c["reason"]:
        t = c["text"].strip()
        if len(t) >= 12 and " " in t and not re.fullmatch(r"[\w\.\-]+", t):
            w(f"  [{c['key_or_context']}] -> {t!r}")
with open(os.path.join(D, "22_final_stats.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print("lines", len(out))
