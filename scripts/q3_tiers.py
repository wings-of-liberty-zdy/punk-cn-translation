import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re
import dnfile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
md = dn.net.mdtables

# --- resolve the SetBool-ish token seen in Ship::UpdateFuelLevel ---
for tok in (0x0A00003F,):
    idx = tok & 0xFFFFFF
    r = md.MemberRef.rows[idx - 1]
    ci = r.Class
    owner = None
    if ci.table.name == "TypeRef":
        rr = md.TypeRef.rows[ci.row_index - 1]
        owner = f"{rr.TypeNamespace}.{rr.TypeName}" if rr.TypeNamespace else str(rr.TypeName)
    elif ci.table.name == "TypeDef":
        rr = md.TypeDef.rows[ci.row_index - 1]
        owner = f"{rr.TypeNamespace}.{rr.TypeName}" if rr.TypeNamespace else str(rr.TypeName)
    else:
        owner = f"<{ci.table.name}:{ci.row_index}>"
    print(f"token 0x{tok:08X} -> {owner}::{r.Name}")

# ================= final tiered reclaim list =================
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]
asset_texts = json.load(open(os.path.join(OUT, "q3_asset_texts.json"), encoding="utf-8"))

status = {r["text"]: (r["decision"], r["reason"]) for r in rows if r["source"] == "Punk.Main.dll"}

TEXT = re.compile(r"TMP_Text::set_text|UI\.Text::set_text|TextMesh::set_text|"
                  r"TMP_InputField::set_text|ShipLogOutput::Log|LogOutput::Log")
DEV = re.compile(r"Debug::Log|Debug::Assert|System\.(Exception|ArgumentException|InvalidOperationException|"
                 r"NotImplementedException|NotSupportedException|FormatException)::\.ctor")
ANIMPARAM = re.compile(r"Animator::SetBool|Animator::SetTrigger|Animator::SetFloat|Animator::SetInteger|"
                       r"Animator::Play|Animator::SetInteger|PlayableDirector")

by_method = collections.defaultdict(set)
lit_sites = collections.defaultdict(list)
for m in methods:
    key = f"{m['type']}::{m['name']}"
    for s in m["strings"]:
        if s in status:
            by_method[key].add(s)
        lit_sites[s].append(m)

NOTRANS = [
    (re.compile(r"^(https?://|www\.)", re.I), "URL"),
    (re.compile(r"\.(tiff|png|wav|bwf|json|txt|cs|asset|prefab|mat|shader|mp3|ogg|dll|xml)$", re.I), "filename"),
    (re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$"), "PREF-KEY/CONST"),
    (re.compile(r"^[a-z][A-Za-z0-9]*$"), "camelCase identifier"),
    (re.compile(r"^[a-z][a-z0-9_]*$"), "lowercase identifier"),
    (re.compile(r"^(get_|set_|m_|_)"), "member name"),
    (re.compile(r"^[^A-Za-z]*$"), "no letters"),
    (re.compile(r"^(<[^>]*>|\{[0-9:.#n,]*\}|[+*/=|-])+$"), "pure markup/format"),
]


def translatable(t):
    v = t.strip()
    if not re.search(r"[A-Za-z]{3,}", v):
        return False, "no 3+ letter word"
    for rx, why in NOTRANS:
        # match against the RAW literal: a leading/trailing space means it is a
        # sentence fragment concatenated into a larger UI string, not an identifier
        if rx.match(t):
            return False, why
    st = re.sub(r"<[^>]*>", " ", re.sub(r"\{[^}]*\}", " ", v))
    if not re.search(r"[A-Za-z]{3,}", st):
        return False, "words only in tags/placeholders"
    return True, ""


TIER = {"A": [], "B": [], "C": []}
for r in rows:
    if r["source"] != "Punk.Main.dll" or r["decision"] != "reject":
        continue
    t = r["text"]
    ok, _ = translatable(t)
    if not ok:
        continue
    sites = lit_sites.get(t, [])
    if not sites:
        continue
    ev = []
    for m in sites:
        key = f"{m['type']}::{m['name']}"
        direct = sorted({c for c in m["calls"] if TEXT.search(c)})
        anim = sorted({c for c in m["calls"] if ANIMPARAM.search(c)})
        dev = sorted({c for c in m["calls"] if DEV.search(c)})
        sibs = sorted(s for s in by_method.get(key, set()) if status[s][0] == "keep")
        ev.append({"site": key, "direct": direct, "anim": anim, "dev": dev, "sibs": sibs})
    A = [e for e in ev if e["direct"] and not e["anim"]]
    B = [e for e in ev if not e["direct"] and e["sibs"] and not e["anim"] and not e["dev"]]
    C = [e for e in ev if not e["direct"] and not e["sibs"]]
    if A:
        TIER["A"].append((t, r["reason"], ev, A))
    elif B:
        TIER["B"].append((t, r["reason"], ev, B))
    elif C:
        TIER["C"].append((t, r["reason"], ev, C))

lines = []
def w(s=""):
    lines.append(s)

w("# Q3 — discarded #US literals that should be reclaimed")
w("")
w("Tier A: the ldstr'ing method directly calls TMP_Text::set_text / UI.Text::set_text / ShipLogOutput::Log")
w("Tier B: no direct sink, but another literal in the SAME method is in the human-verified allowlist")
w("        (same method, same return path => same UI sink), and the method has no Debug/Exception sink")
w("Tier C: neither; only weak/transitive evidence — NOT counted as reclaimed")
w("")
for tier in ("A", "B", "C"):
    items = TIER[tier]
    w(f"## Tier {tier}  ({len(items)} literals)")
    for t, prior, ev, hits in sorted(items, key=lambda x: x[0]):
        w(f"  {t!r}")
        w(f"      prior_reject = {prior}")
        for h in hits:
            w(f"      @ {h['site']}")
            if h["direct"]:
                w(f"          sink  = {h['direct']}")
            if h["sibs"]:
                w(f"          kept siblings = {h['sibs'][:6]}")
        w("")
    w("")

tot = len(TIER["A"]) + len(TIER["B"])
w(f"TOTAL RECLAIMED (Tier A + B): {tot}   (Tier A={len(TIER['A'])}, Tier B={len(TIER['B'])}, "
  f"Tier C not counted={len(TIER['C'])})")
w("")
w("### Tier A flat list ###")
for t, _, _, _ in sorted(TIER["A"], key=lambda x: x[0]):
    w(f"  {t!r}")
w("")
w("### Tier B flat list ###")
for t, _, _, _ in sorted(TIER["B"], key=lambda x: x[0]):
    w(f"  {t!r}")

open(os.path.join(OUT, "q3_reclaim_tiers.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
json.dump({k: [{"text": t, "prior": p, "evidence": e} for t, p, e, _ in v] for k, v in TIER.items()},
          open(os.path.join(OUT, "q3_reclaim_tiers.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\nTier A={len(TIER['A'])} Tier B={len(TIER['B'])} Tier C={len(TIER['C'])}")
print("wrote q3_reclaim_tiers.txt / .json")
