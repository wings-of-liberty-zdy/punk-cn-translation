import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]
asset_texts = json.load(open(os.path.join(OUT, "q3_asset_texts.json"), encoding="utf-8"))

lit_sites = collections.defaultdict(list)
for m in methods:
    for s in m["strings"]:
        lit_sites[s].append(m)

TEXT = re.compile(r"TMP_Text::set_text|UI\.Text::set_text|TextMesh::set_text|TMP_InputField::set_text|ShipLogOutput::Log|LogOutput::Log")
DEV = re.compile(r"Debug::Log|System\.Exception::\.ctor|Debug::Assert|System\.ArgumentException::\.ctor")
ANIM = re.compile(r"Animator::SetBool|Animator::SetTrigger|Animator::SetFloat|Animator::SetInteger|Animator::Play")

# pure markup / format-only / identifier detectors
MARKUP = re.compile(r"^[^A-Za-z]*$|^</?[a-z]+(=[^>]*)?>$|^<[a-z]+=#$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PREFKEY = re.compile(r"^(PLAYER_PREF|Pref|KEY)_")
FILENAME = re.compile(r"\.(tiff|png|wav|bwf|json|txt|cs|asset|prefab|mat|shader|mp3|ogg)$", re.I)
WORDS = re.compile(r"[A-Za-z]{3,}")

def verdict_of(t, sites):
    v = t.strip()
    dir_text = any(TEXT.search(c) for m in sites for c in m["calls"])
    only_dev = bool(sites) and all(any(DEV.search(c) for c in m["calls"]) and not TEXT.search(" ".join(m["calls"])) for m in sites)
    anim_only = bool(sites) and all(any(ANIM.search(c) for c in m["calls"]) for m in sites)
    notes = []
    if not sites:
        notes.append("no-ldstr-site")
    if MARKUP.match(v) or not WORDS.search(v):
        notes.append("no-words/markup/format")
    if IDENT.match(v) and "_" not in v and v[0].islower():
        notes.append("camelCase-identifier")
    if PREFKEY.match(v):
        notes.append("pref-key")
    if FILENAME.search(v):
        notes.append("filename")
    if anim_only:
        notes.append("animator-param-only")
    if dir_text:
        notes.append("DIRECT-TMP")
    if only_dev:
        notes.append("devlog-only")
    if t in asset_texts:
        notes.append("in-asset-m_text")
    # final verdict
    if "DIRECT-TMP" in notes and "no-words/markup/format" not in notes and "pref-key" not in notes \
            and "filename" not in notes and "animator-param-only" not in notes:
        return "RECLAIM", notes
    if "no-ldstr-site" in notes or "no-words/markup/format" in notes or "pref-key" in notes \
            or "filename" in notes or "animator-param-only" in notes or "camelCase-identifier" in notes:
        return "REJECT", notes
    if "devlog-only" in notes:
        return "REJECT", notes
    return "MAYBE", notes


buckets = collections.defaultdict(list)
for r in rows:
    if r["source"] != "Punk.Main.dll" or r["decision"] != "reject":
        continue
    t = r["text"]
    sites = lit_sites.get(t, [])
    vd, notes = verdict_of(t, sites)
    buckets[vd].append((t, r["reason"], sites, notes))

lines = []
def w(s=""):
    lines.append(s)

for vd in ("RECLAIM", "MAYBE", "REJECT"):
    w("=" * 90)
    w(f"### {vd}  ({len(buckets[vd])})")
    w("=" * 90)
    for t, reason, sites, notes in sorted(buckets[vd], key=lambda x: -len(x[0])):
        w(f"  {t!r}")
        w(f"      prior={reason[:44]:46} notes={','.join(notes)}")
        for m in sites[:6]:
            tc = [c for c in m["calls"] if TEXT.search(c)]
            dc = [c for c in m["calls"] if DEV.search(c)]
            w(f"      @ {m['type']}::{m['name']}   TMP={tc[:2]} DEV={dc[:2]}")
        if not sites:
            w("      @ <no ldstr call site found>")
    w()

open(os.path.join(OUT, "q3_reject_detail.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"RECLAIM={len(buckets['RECLAIM'])} MAYBE={len(buckets['MAYBE'])} REJECT={len(buckets['REJECT'])}")
json.dump({k: [{"text": t, "prior": r, "notes": n,
                "sites": [f"{m['type']}::{m['name']}" for m in s]} for t, r, s, n in v]
           for k, v in buckets.items()},
          open(os.path.join(OUT, "q3_reject_verdicts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote q3_reject_detail.txt + q3_reject_verdicts.json")
