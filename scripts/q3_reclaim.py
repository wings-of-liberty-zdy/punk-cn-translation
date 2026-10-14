import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))

# ------------------------------------------------------------------ sinks
TEXT_SINK = re.compile(
    r"TMP_Text::set_text|TMP_Text::SetText|UI\.Text::set_text|TextMeshProUGUI::set_text|"
    r"TMP_InputField::set_text|TMP_Dropdown::|TextMesh::set_text|"
    r"ShipLogOutput::Log|LogOutput::Log|ShipLogOutput::LogLine|"
    r"InfoPopup::Show|Tooltip|SetTooltip|ShowTooltip|"
    r"Notification|Toast|Popup::Show|Dialog::Show|Prompt::Show|Banner|"
    r"Localization|Localize")
DEV_SINK = re.compile(
    r"Debug::Log|Debug::LogError|Debug::LogWarning|Debug::LogException|Debug::Assert|"
    r"Debug::LogFormat|System\.Exception::\.ctor|System\.ArgumentException::\.ctor|"
    r"System\.InvalidOperationException::\.ctor|System\.NotImplementedException::\.ctor|"
    r"System\.NotSupportedException::\.ctor|System\.FormatException::\.ctor|"
    r"UnityEngine\.Assertions|Assert::That|Assert::IsTrue|Assert::IsNotNull")
NET_SINK = re.compile(r"DiscordWebhook|UnityWebRequest|DownloadHandler|WWW::|HttpClient|WebClient")
UI_CLASS = re.compile(
    r"(Widget|Menu|Screen|Panel|Hud|HUD|Button|Tooltip|Popup|Dialog|Notification|"
    r"Card|Item|Slot|Icon|Label|Text|Bar|Meter|Wheel|Toggler|Selector|Option|"
    r"Window|Overlay|Indicator|Hint|Tutorial|Intro|Outro|Credits|Settings|Loadout)")

# ------------------------------------------------------------------ call graph
by_name = collections.defaultdict(list)
for m in methods:
    by_name[(m["type"], m["name"])].append(m)
all_methods_by_key = {}
for m in methods:
    all_methods_by_key.setdefault((m["type"], m["name"]), m)

name_only = collections.defaultdict(list)
for m in methods:
    name_only[m["name"]].append(m)


def sinks_of(m):
    s = set()
    for c in m["calls"]:
        if TEXT_SINK.search(c):
            s.add("text")
        if DEV_SINK.search(c):
            s.add("dev")
        if NET_SINK.search(c):
            s.add("net")
    return s


for m in methods:
    m["_sinks"] = sinks_of(m)

# call-graph reachability to a 'text' sink (depth-limited BFS over method names)
reach_cache = {}


def reaches_text(m, depth=4, seen=None):
    key = (m["type"], m["name"])
    if key in reach_cache:
        return reach_cache[key]
    if seen is None:
        seen = set()
    if key in seen:
        return False
    seen = seen | {key}
    if "text" in m["_sinks"]:
        reach_cache[key] = 2
        return 2
    if depth <= 0:
        return 0
    best = 0
    for c in m["calls"]:
        short = c.split("::")[-1]
        for callee in name_only.get(short, [])[:6]:
            r = reaches_text(callee, depth - 1, seen)
            if r > best:
                best = r
        if best == 2:
            break
    reach_cache[key] = best
    return best


# ------------------------------------------------------------------ literal -> call sites
lit_sites = collections.defaultdict(list)
for m in methods:
    for s in m["strings"]:
        lit_sites[s].append(m)

# ------------------------------------------------------------------ asset text values (cross-check)
def collect_asset_texts():
    import UnityPy
    import UnityPy.helpers.TypeTreeGenerator as tg
    DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
    gen = tg.TypeTreeGenerator("6000.3.4f1")
    gen.load_local_dll_folder(os.path.join(DATA, "Managed"))
    vals = collections.Counter()
    files = ["resources.assets", "sharedassets0.assets", "sharedassets1.assets",
             "sharedassets2.assets", "sharedassets3.assets", "globalgamemanagers.assets",
             "level0", "level1", "level2", "level3"]
    for fn in files:
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            continue
        e = UnityPy.load(p)
        e.typetree_generator = gen
        for o in e.objects:
            if o.type.name != "MonoBehaviour":
                continue
            try:
                d = o.read_typetree()
            except Exception:
                continue
            try:
                cn = o._get_typetree_node().m_Type
            except Exception:
                cn = None
            if cn not in ("TextMeshProUGUI", "TextMeshPro", "Text", "TMP_Text"):
                continue
            t = d.get("m_text")
            if isinstance(t, str) and t.strip():
                vals[t] += 1
    return vals


try:
    asset_texts = collect_asset_texts()
except Exception as e:
    print("asset text collection failed:", repr(e))
    asset_texts = collections.Counter()
print("distinct asset text values:", len(asset_texts))
json.dump(dict(asset_texts), open(os.path.join(OUT, "q3_asset_texts.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ------------------------------------------------------------------ analyse rejected DLL literals
rows = [json.loads(l) for l in open(os.path.join(OUT, "strings_all_classified.jsonl"), encoding="utf-8")]
dll_rej = [r for r in rows if r["source"] == "Punk.Main.dll" and r["decision"] == "reject"]
dll_keep = [r for r in rows if r["source"] == "Punk.Main.dll" and r["decision"] == "keep"]
print(f"DLL rejects: {len(dll_rej)}  keeps: {len(dll_keep)}")


def analyse(text):
    sites = lit_sites.get(text, [])
    ev = []
    for m in sites:
        ev.append({
            "type": m["type"], "method": m["name"],
            "sinks": sorted(m["_sinks"]),
            "reaches_text": reaches_text(m),
            "ui_class": bool(UI_CLASS.search(m["type"] or "")),
            "n_ins": m["n_ins"],
            "calls": m["calls"][:14],
        })
    return ev


report = []
for r in dll_rej:
    t = r["text"]
    ev = analyse(t)
    v = t.strip()
    has_text = any(e["reaches_text"] == 2 for e in ev)
    direct_text = any("text" in e["sinks"] for e in ev)
    only_dev = bool(ev) and all(set(e["sinks"]) <= {"dev"} and e["reaches_text"] < 2 for e in ev)
    ui_class = any(e["ui_class"] for e in ev)
    in_assets = t in asset_texts or (v and v in asset_texts)
    substr_asset = None
    if not in_assets and len(v) >= 6:
        for at in asset_texts:
            if v and (v in at or at in v):
                substr_asset = at
                break
    score = 0
    if direct_text:
        score += 4
    elif has_text:
        score += 2
    if ui_class:
        score += 2
    if in_assets:
        score += 3
    elif substr_asset:
        score += 1
    if only_dev:
        score -= 3
    if re.fullmatch(r"[\W\d\s{}:.,/&#;<>=\"'\[\]\\-]*", v):
        score -= 4
    if re.fullmatch(r"[_A-Za-z][A-Za-z0-9_]*", v):
        score -= 3
    if re.search(r"^(get_|set_|m_|_)", v):
        score -= 3
    report.append({
        "text": t, "prior_reason": r["reason"], "score": score,
        "direct_text_sink": direct_text, "reaches_text": has_text,
        "ui_class": ui_class, "in_asset_text": in_assets, "asset_substr": substr_asset,
        "only_dev": only_dev, "sites": ev,
    })

report.sort(key=lambda x: -x["score"])
json.dump(report, open(os.path.join(OUT, "q3_reject_analysis.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

lines = []
def w(s=""):
    lines.append(s); print(s)

w("=" * 78)
w("Q3  rejected DLL literals re-scored WITH real call-site attribution")
w("=" * 78)
for thr, label in ((6, "HIGH"), (4, "MEDIUM"), (2, "LOW")):
    pass

w("\n### RECLAIM candidates (score >= 4) ###")
n = 0
for r in report:
    if r["score"] >= 4:
        n += 1
        w(f"[{r['score']:>3}] {r['text']!r}")
        w(f"      prior={r['prior_reason']}  directTMP={r['direct_text_sink']} reachTMP={r['reaches_text']} "
          f"uiClass={r['ui_class']} inAsset={r['in_asset_text']}")
        for e in r["sites"][:4]:
            w(f"      @ {e['type']}::{e['method']}  sinks={e['sinks']} reach={e['reaches_text']} uiClass={e['ui_class']}")
w(f"  -> {n} reclaim candidates")

w("\n### MEDIUM (score 2-3): needs human look ###")
n2 = 0
for r in report:
    if 2 <= r["score"] < 4:
        n2 += 1
        w(f"[{r['score']:>3}] {r['text']!r}   prior={r['prior_reason'][:34]}")
        for e in r["sites"][:3]:
            w(f"      @ {e['type']}::{e['method']}  sinks={e['sinks']} reach={e['reaches_text']}")
w(f"  -> {n2} medium")

w("\n### how many rejects have NO call site at all (dead literals) ###")
noc = [r for r in report if not r["sites"]]
w(f"  {len(noc)} of {len(report)}")
for r in noc[:25]:
    w(f"      {r['text'][:100]!r}")

w("\n### prior reason x new verdict ###")
cnt = collections.Counter()
for r in report:
    verdict = "RECLAIM" if r["score"] >= 4 else ("MAYBE" if r["score"] >= 2 else "KEEP-REJECTED")
    cnt[(r["prior_reason"].split("'")[0].strip()[:40], verdict)] += 1
for (pr, v), c in sorted(cnt.items()):
    w(f"  {c:5d}  {v:14} <- {pr}")

open(os.path.join(OUT, "q3_reject_analysis.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\nwrote q3_reject_analysis.json + q3_reject_analysis.txt")
