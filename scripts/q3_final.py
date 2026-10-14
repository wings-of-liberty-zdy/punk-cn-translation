import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]

status = {}
for r in rows:
    if r["source"] == "Punk.Main.dll":
        status[r["text"]] = (r["decision"], r["reason"])

lit_sites = collections.defaultdict(list)
for m in methods:
    for s in m["strings"]:
        lit_sites[s].append(m)

TEXT = re.compile(r"TMP_Text::set_text|UI\.Text::set_text|ShipLogOutput::Log|LogOutput::Log|TMP_InputField::set_text")
DEV = re.compile(r"Debug::Log|System\.Exception::\.ctor|Debug::Assert")

# ---- reverse call graph ----
callers = collections.defaultdict(list)
for m in methods:
    for c in m["calls"]:
        short = c.split("::")[-1]
        callers[short].append(m)

def ui_callers(m, depth=3):
    """methods that call m (transitively) and directly set text"""
    out = []
    seen = set()
    frontier = [(m, 0)]
    while frontier:
        cur, d = frontier.pop()
        key = (cur["type"], cur["name"])
        if key in seen or d > depth:
            continue
        seen.add(key)
        for c in callers.get(cur["name"], [])[:40]:
            if any(TEXT.search(x) for x in c["calls"]):
                out.append((c, d + 1))
            frontier.append((c, d + 1))
    return out

# ---- candidate set: literals whose own method, or a caller, sets text ----
CAND = []
for r in rows:
    if r["source"] != "Punk.Main.dll" or r["decision"] != "reject":
        continue
    t = r["text"]
    sites = lit_sites.get(t, [])
    direct = [m for m in sites if any(TEXT.search(c) for c in m["calls"])]
    via = []
    for m in sites:
        for (c, d) in ui_callers(m, 3):
            via.append((m, c, d))
    if direct or via:
        CAND.append({"text": t, "prior": r["reason"], "direct": direct, "via": via, "sites": sites})

print(f"literals whose own method or a transitive caller sets TMP text: {len(CAND)}")

lines = []
def w(s=""):
    lines.append(s); print(s)

w("=" * 96)
w("Q3 FINAL: discarded DLL literals that provably reach a TMP text / ship-log sink")
w("=" * 96)
w("")
for c in sorted(CAND, key=lambda x: -len(x["text"])):
    t = c["text"]
    w(f"  {t!r}")
    w(f"      prior_reject_reason = {c['prior']}")
    for m in c["direct"][:3]:
        tc = sorted({x for x in m["calls"] if TEXT.search(x)})
        w(f"      DIRECT  @ {m['type']}::{m['name']}  ->  {tc}")
    for (m, caller, d) in c["via"][:4]:
        tc = sorted({x for x in caller["calls"] if TEXT.search(x)})
        w(f"      VIA({d})  {m['type']}::{m['name']}  <- called by  {caller['type']}::{caller['name']}  ->  {tc}")
    # sibling evidence
    sibs = set()
    for m in c["sites"]:
        for s in m["strings"]:
            if s != t:
                sibs.add(s)
    kept_sibs = [(s, status.get(s, ("?", "?"))) for s in sibs]
    kept = [s for s, st in kept_sibs if st[0] == "keep"]
    rej = [s for s, st in kept_sibs if st[0] == "reject"]
    w(f"      SIBLINGS in same method(s): kept={kept[:8]}  rejected={rej[:8]}")
    w("")

json.dump([{"text": c["text"], "prior": c["prior"],
            "direct": [f"{m['type']}::{m['name']}" for m in c["direct"]],
            "via": [f"{m['type']}::{m['name']}<-{cl['type']}::{cl['name']}" for (m, cl, d) in c["via"]],
            "sites": [f"{m['type']}::{m['name']}" for m in c["sites"]]} for c in CAND],
          open(os.path.join(OUT, "q3_final_reclaim.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

open(os.path.join(OUT, "q3_final_reclaim.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("wrote q3_final_reclaim.txt / .json")
