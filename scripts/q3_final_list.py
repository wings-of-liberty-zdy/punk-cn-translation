import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]
asset_texts = json.load(open(os.path.join(OUT, "q3_asset_texts.json"), encoding="utf-8"))

status = {}
for r in rows:
    if r["source"] == "Punk.Main.dll":
        status[r["text"]] = (r["decision"], r["reason"])

TEXT = re.compile(r"TMP_Text::set_text|UI\.Text::set_text|TextMesh::set_text|"
                  r"TMP_InputField::set_text|ShipLogOutput::Log|LogOutput::Log")
DEV = re.compile(r"Debug::Log|Debug::Assert|System\.(Exception|ArgumentException|InvalidOperationException|"
                 r"NotImplementedException|NotSupportedException|FormatException)::\.ctor")

by_method = collections.defaultdict(set)
lit_sites = collections.defaultdict(list)
for m in methods:
    key = f"{m['type']}::{m['name']}"
    for s in m["strings"]:
        if s in status:
            by_method[key].add(s)
        lit_sites[s].append(m)

callers = collections.defaultdict(list)
for m in methods:
    for c in m["calls"]:
        callers[c.split("::")[-1]].append(m)

# ---------------- translatability filter ----------------
NOTRANS = [
    (re.compile(r"^(https?://|www\.)", re.I), "URL"),
    (re.compile(r"\.(tiff|png|wav|bwf|json|txt|cs|asset|prefab|mat|shader|mp3|ogg|dll|xml)$", re.I), "filename"),
    (re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$"), "PREF-KEY / CONST"),
    (re.compile(r"^[a-z][A-Za-z0-9]*$"), "camelCase identifier"),
    (re.compile(r"^[a-z][a-z0-9_]*$"), "lowercase identifier"),
    (re.compile(r"^(get_|set_|m_|_)"), "member name"),
    (re.compile(r"^[^A-Za-z]*$"), "no letters at all"),
    (re.compile(r"^(<[^>]*>|\{[0-9:.#n,]*\}|[+*/=|-])+$"), "pure markup / format"),
]


def translatable(t):
    v = t.strip()
    if not re.search(r"[A-Za-z]{3,}", v):
        return False, "no 3+ letter word"
    for rx, why in NOTRANS:
        if rx.match(v):
            return False, why
    # must have a real word (not only inside a {..} placeholder or tag)
    stripped = re.sub(r"<[^>]*>", " ", v)
    stripped = re.sub(r"\{[^}]*\}", " ", stripped)
    if not re.search(r"[A-Za-z]{3,}", stripped):
        return False, "words only inside tags/placeholders"
    return True, ""


# ---------------- reclaim rules ----------------
REC = []
for r in rows:
    if r["source"] != "Punk.Main.dll" or r["decision"] != "reject":
        continue
    t = r["text"]
    ok, why_not = translatable(t)
    if not ok:
        continue
    sites = lit_sites.get(t, [])
    if not sites:
        continue
    rules = []
    for m in sites:
        key = f"{m['type']}::{m['name']}"
        direct = sorted({c for c in m["calls"] if TEXT.search(c)})
        devonly = bool(m["calls"]) and not direct and all(DEV.search(c) for c in m["calls"] if "::" in c)
        sibs_kept = sorted(s for s in by_method.get(key, set()) if status[s][0] == "keep")
        # depth-1 UI caller
        ui_caller = None
        for c in callers.get(m["name"], []):
            if any(TEXT.search(x) for x in c["calls"]):
                ui_caller = f"{c['type']}::{c['name']}"
                break
        if direct:
            rules.append(("R1 same-method text sink", key, direct))
        if sibs_kept:
            rules.append(("R2 kept sibling in same method", key, sibs_kept[:5]))
        if ui_caller and not direct:
            rules.append(("R3 depth-1 UI caller", key, [ui_caller]))
    if rules:
        REC.append({"text": t, "prior": r["reason"], "rules": rules,
                    "in_asset_text": t in asset_texts,
                    "sites": [f"{m['type']}::{m['name']}" for m in sites]})

REC.sort(key=lambda x: (-len(x["rules"]), x["text"]))

lines = []
def w(s=""):
    lines.append(s); print(s)

w("=" * 100)
w(f"Q3 FINAL RECLAIM LIST — {len(REC)} literals (of 429 discarded)")
w("Criterion: translatable English content AND at least one of")
w("  R1 the ldstr'ing method directly calls TMP_Text::set_text / UI.Text::set_text / ShipLogOutput::Log")
w("  R2 another literal in the SAME method is in the human-verified allowlist (same return path)")
w("  R3 the ldstr'ing method is called by a method with a direct text sink (depth-1 only)")
w("=" * 100)
for i, r in enumerate(REC, 1):
    w(f"\n{i:3d}. {r['text']!r}")
    w(f"      prior_reject = {r['prior']}")
    for (rule, key, detail) in r["rules"]:
        w(f"      {rule}")
        w(f"          @ {key}   {detail}")
w("")
w("=" * 100)
w("grouped by rule combination")
w("=" * 100)
g = collections.Counter()
for r in REC:
    g["+".join(sorted(x[0][:2] for x in r["rules"]))] += 1
for k, v in g.most_common():
    w(f"  {v:4d}  {k}")

open(os.path.join(OUT, "q3_reclaim_final.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
json.dump(REC, open(os.path.join(OUT, "q3_reclaim_final.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\nwrote q3_reclaim_final.txt / .json  ({len(REC)} entries)")
