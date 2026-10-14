import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, re, collections

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
D = os.path.join(ROOT, "data", "dump")

mb = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]
paths = {(r["source"], r["cls"], r["pid"]): r for r in
         json.load(open(os.path.join(D, "ui_text_paths.json"), encoding="utf-8"))}
us = json.load(open(os.path.join(D, "us_Punk.Main.dll.json"), encoding="utf-8"))
us_att = us["attribution"]

# ------------------------------- field rules -------------------------------
NOISE_LEAF = {
    "m_name", "m_script", "m_id", "id", "guid", "entityid", "m_path", "m_groups",
    "m_processors", "m_interactions", "m_expectedcontroltype", "m_action",
    "m_bindinggroup", "paramname", "namedoverride", "hudanimparamname", "debugicon",
    "type", "m_targetassemblytypename", "m_methodname",
    "m_objectargumentassemblytypename", "m_stringargument", "m_normaltrigger",
    "m_highlightedtrigger", "m_pressedtrigger", "m_selectedtrigger",
    "m_disabledtrigger", "m_openingdefinition", "m_closingdefinition", "m_version",
    "m_familyname", "m_stylename", "charactersequence", "name", "m_keys",
    "animparamname", "animtriggername", "hoveranimparam", "foldername",
    "m_defaultactionmap", "m_defaultcontrolscheme", "assetversion", "url",
    "musictrack", "inputmanuactionmapname",
    "dashactionname", "hoveractionname", "aimactionname", "primaryfireactionname",
    "secodaryfireactionname", "activatecommonactionname",
    "activateactionname", "useactionname", "grapplehookactionname",
    "selfdestructactionname", "activatebmoduleactionname",
    "activatecmoduleactionname", "activatedmoduleactionname",
    "showusprompt", "showuseprompt",
}
NOISE_LEAF |= {f"activate{chr(c)}moduleactionname" for c in range(ord("a"), ord("f"))}
NOISE_LEAF |= {f"dashactionname", "hoveractionname", "aimactionname"}
ENDS_NOISE = ("sfx", "guid", "filename", "rifftypeid", "bytesstring",
              "prefabmodifications", "actionname", "paramname", "triggername",
              "layout", "effectsname")

FIELD_CATEGORY = {
    "displayname": "item_module_desc",
    "description": "item_module_desc",
    "inputhintmessage": "tutorial_hint",
    "itemwheelhintmessagekbm": "tutorial_hint",
    "itemwheelhintmessagegamepad": "tutorial_hint",
    "normallabeltext": "ui_menu",
    "stationlabeltext": "ui_menu",
    "message": "ui_menu",
    "format": "other",
    "messageformat": "other",
}

PLACEHOLDERS = {"new text", "modulename", "consumable", "description", "title\n",
                "module name", "map state name", "option a",
                "item desc",
                "this is a longer description\nit can be multiple lines\nin fact it probably will be\n"
                "it can also contain icons like this 10/232<sprite=5>"}
KEY_LABELS = {"a", "b", "e", "f", "g", "r", "w", "x", "y", "z", "d", "s", "tab",
              "alt", "space", "wasd", "l shift", "fire 1", "fire 2", "fire 1/2",
              "p1", "p2", "fps", "shift", "ctrl", "enter", "esc", "escape",
              "leftjoystick", "rightjoystick", "lmb", "rmb", "mmb", "wpn\n",
              "0/2", "2/2", "2/3", "100", "500", "1000\n", "500\n", "+2\n", "01",
              "24", "2\n", "13:45:59", "1920x1080 60fps", "v0.02", "gdt",
              }
DEVROOT = ("ui/debugmenu", "ui/[graphy]", "ui/pertestcanvas", "debugui",
           "debugsave", "localconfig", "unitdebugtext", "celldebuginfo",
           "secondarydebuggl")

records, classified = [], []


def emit(source, category, key, text, decision, reason, flags=()):
    k = key + (("|flag=" + ",".join(sorted(flags))) if flags else "")
    rec = {"source": source, "category": category, "key_or_context": k, "text": text}
    classified.append({**rec, "decision": decision, "reason": reason})
    if decision == "keep":
        records.append(rec)


def flag_path(p):
    lp = (p or "").lower()
    fl = []
    if lp.startswith("ui/debugmenu") or "debugmenu" in lp:
        fl.append("debug_menu")
    if lp.startswith("ui/[graphy]") or "[graphy]" in lp:
        fl.append("perf_overlay")
    if "pertestcanvas" in lp:
        fl.append("test_canvas")
    if lp.startswith("debugui"):
        fl.append("unity_debugui")
    if "localconfig" in lp:
        fl.append("local_config")
    if lp.startswith("canvas/credits") or "/credits/" in lp:
        fl.append("credits")
    return fl


for r in mb:
    t = r["text"]
    leaf = r["field"].split(".")[-1].split("[")[0]
    ll = leaf.lower()
    pr = paths.get((r["source"], r["cls"], r["pid"]))
    path = pr["path"] if pr else ""
    src = f"{r['source']}:{r['cls']}"
    key = f"{src}|{r['field']}|{path or r['go']}|pid={r['pid']}"
    fl = flag_path(path)

    if not t.strip():
        emit(src, "not_translatable", key, t, "reject", "empty string", fl); continue
    if r["field"].startswith("serializationData"):
        emit(src, "not_translatable", key, t, "reject", "serializationData blob", fl); continue
    if t.startswith("UnityEngine.") and (", Version=" in t or ", Unity." in t):
        emit(src, "not_translatable", key, t, "reject", "assembly-qualified type", fl); continue
    if r["field"].startswith(("prefabs[", "m_OnClick", "OnShoot", "onDamage", "onDeath",
                              "m_AnimationTriggers", "serializationData")):
        emit(src, "not_translatable", key, t, "reject", "UnityEvent / animator trigger wiring", fl); continue
    if ll in NOISE_LEAF or any(ll.endswith(e) for e in ENDS_NOISE):
        emit(src, "not_translatable", key, t, "reject", f"non-text field '{leaf}'", fl); continue

    if ll in FIELD_CATEGORY:
        cat = FIELD_CATEGORY[ll]
        fl2 = list(fl)
        if t.strip().lower() in PLACEHOLDERS:
            fl2.append("placeholder")
            cat = "other"
        emit(src, cat, key, t, "keep", f"data field '{leaf}'", fl2); continue

    if r["cls"] in ("TextMeshProUGUI", "Text"):
        v = t.strip()
        if "unity_debugui" in fl:
            emit(src, "not_translatable", key, t, "reject",
                 "Unity Rendering DebugUI built-in prefab text", fl); continue
        if v.lower() in PLACEHOLDERS:
            emit(src, "other", key, t, "keep", "runtime-replaced placeholder", fl + ["placeholder"]); continue
        if v.lower() in KEY_LABELS or re.fullmatch(r"[\d\s/%+.,:x\-]*", v):
            emit(src, "other", key, t, "keep", "key label / numeric readout", fl + ["key_label"]); continue
        if fl:
            emit(src, "other", key, t, "keep", "dev-only overlay text", fl); continue
        if re.match(r"^(PRESS|HOLD|USE|MOVE|OPEN|SELECT|TAP|CLICK|DASH|AIM)\b", v) and len(v) > 6:
            emit(src, "tutorial_hint", key, t, "keep", "imperative input prompt", fl); continue
        if "tutorial" in (path or "").lower() or "Tutorial" in (r["go"] or ""):
            emit(src, "tutorial_hint", key, t, "keep", "tutorial panel", fl); continue
        if len(v) >= 60 or (len(v) > 15 and "?" in v) or re.search(r"THANK|WELCOME|GOOD LUCK|PLAYING", v, re.I):
            emit(src, "dialogue_story", key, t, "keep", "prose / narrative / confirmation", fl); continue
        emit(src, "ui_menu", key, t, "keep", "UI label (menu/button/HUD)", fl); continue

    emit(src, "not_translatable", key, t, "reject", f"unclassified field '{leaf}'", fl)

# ------------------------------- DLL side -------------------------------
ALLOW = {
    "Success! {0}", "Upload failed", "Unknown error", "Failed to load", "Score uplaoded",
    "Uploading score to ", "Loading leaderboard: ", "Failed to load leaderboard",
    "Leaderboard entries downloaded", "SCANNING AREA", "NEW LOCATION ADDED",
    "COST PER PROJECTILE", "MAX POWER CORES: {0}", "ATTACHED POWER CORES: {0} / {1}",
    "Fuel low", "Fuel critical", "Incompatible slot", "Incompatible connections",
    "Incompatible augmentation", "Cannot apply {0} to {1}", "Game does not work",
    "Ship loadout unlocked: ", "Stations unlocked: {0}\n", "Enemies killed: {0}\n",
    "Total deaths: {0}\n", "Final bosses killed: {0}/4\n", "Final bosses killed: {0}/{1}",
    "Run duration: {0:hh':'mm':'ss}\n", "Respawn on next station unlock", "Biome: ",
    "Difficulty: {0}\n", "Seed: {0}\nGame version: {1}", "Effectiveness: {0}%",
    "Burn level: {0}\n", "Interest: {0}\n", "Distance: {0}\n", "Explosion damage",
    "Explosion radius", "Explosion dmg", "Contact Damage", "Discharge damage",
    "Discharge chain length", "Knockback Force", "Fire Rate", "Burst Size",
    "Burst Delay", "Projectile Count", "Angle Variance", "Angle Offset", "Spread",
    "Damage", "Range", "Speed", "Headlights", "Duration: ", "Cost", "COST",
    "Select", "Cancel", "Activate", "Unequip", "Shop", "Station", "Consumable",
    "Discharge", "Offline", "Powered", "Navigate", "Interact", "Highlighted",
    "Selection", "Connected", "Visible", "Buy", "Menu", "Fuel",
    "PICK UP\n<color=#ffc600>",
}
DEVLOG = re.compile(
    r"(failed|could not|couldn't|can't|cannot|unable|not found|not set|not defined|"
    r"not suitable|not implemented|trying to|tried to|invalid|error|exception|missing|"
    r"is null|no animator|no barrel|no camera|no damage|no end poi|no cues|should have|"
    r"must be|wrong |unknown error|clusters cannot|values must|value must|collider|"
    r"display not implemented|power core has invalid|steamworks\.net|singleton of type|"
    r"memento type|entity id missing|destroyed entity were saved|save destroyedobject|"
    r"no gamecontroller|cancelled infinite loop|only extensions|only works while|"
    r"can only be used on|not in the correct|bug report from user|reference the readme|"
    r"refer to the|here is the description|generated in |finished in |loaded in |"
    r"setting for layer|connection type not defined|damage type not found|biom not found|"
    r"trying to |no damage set up|is not initialized|wrong indexing|no resource|"
    r"not in the dictionary|https?://|www\.|discord\.gg|C:\\\\Projects|"
    r"\.cs$|\.tiff$|\.txt$|\.json$|\.wav$|\.bwf$|^_|^m_|Volume$)",
    re.I)

for r in us["rows"]:
    t = r["text"]; v = t.strip()
    a = us_att.get(t) or []
    ctx = ";".join(sorted({f"{x[0]}.{x[1]}" for x in a if x[0]})) or "unattributed"
    key = f"Punk.Main.dll#US@{r['heap_offset']}|{ctx}"
    if not v:
        emit("Punk.Main.dll", "not_translatable", key, t, "reject", "empty", ("from_dll",)); continue
    if t in ALLOW:
        cat = "tutorial_hint" if ("SCANNING" in t or "PICK UP" in t or "Respawn" in t) else "ui_menu"
        emit("Punk.Main.dll", cat, key, t, "keep", "allowlist (verified player-facing)",
             ("from_dll",)); continue
    if re.fullmatch(r"[_A-Za-z][A-Za-z0-9_]*(\.(wav|bwf|json|txt|tiff|cs))?", v) and " " not in v and not v.isupper():
        emit("Punk.Main.dll", "not_translatable", key, t, "reject",
             "identifier / file name / shader property", ("from_dll",)); continue
    if re.fullmatch(r"[\W\d\s{}:.,/&#;<>=\"'\[\]\\-]*", v):
        emit("Punk.Main.dll", "not_translatable", key, t, "reject",
             "format specifier / punctuation only", ("from_dll",)); continue
    if DEVLOG.search(v):
        emit("Punk.Main.dll", "dev_log", key, t, "reject",
             "dev log / exception / diagnostic", ("from_dll",)); continue
    if v.isupper() and len(v) >= 6 and " " in v and not DEVLOG.search(v) and ":" not in v:
        emit("Punk.Main.dll", "ui_menu", key, t, "keep",
             "ALL-CAPS multi-word UI label (pattern match)", ("from_dll",)); continue
    emit("Punk.Main.dll", "dev_log", key, t, "reject",
         "unattributed DLL literal - no UI shape (default reject)", ("from_dll",))

# ------------------------------- write -------------------------------
with open(os.path.join(ROOT, "data", "strings_raw.json"), "w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)
with open(os.path.join(D, "strings_all_classified.jsonl"), "w", encoding="utf-8") as fh:
    for c in classified:
        fh.write(json.dumps(c, ensure_ascii=False) + "\n")

texts = [r["text"] for r in records]
uniq = sorted(set(texts))
cat = collections.Counter(r["category"] for r in records)
flags = collections.Counter()
for r in records:
    if "flag=" in r["key_or_context"]:
        for f in r["key_or_context"].split("flag=")[1].split(","):
            flags[f] += 1
rej = collections.Counter(c["reason"].split("'")[0].strip() for c in classified if c["decision"] == "reject")
player = [r for r in records if "flag=" not in r["key_or_context"] or not any(
    f in r["key_or_context"] for f in ("debug_menu", "perf_overlay", "test_canvas"))]

buckets = collections.Counter()
for t in uniq:
    L = len(t)
    b = "01-05" if L <= 5 else "06-10" if L <= 10 else "11-20" if L <= 20 else \
        "21-40" if L <= 40 else "41-80" if L <= 80 else "81-160" if L <= 160 else "161+"
    buckets[b] += 1

print("KEPT total            :", len(records))
print("KEPT distinct         :", len(uniq))
print("KEPT chars (all)      :", sum(len(t) for t in texts))
print("KEPT chars (distinct) :", sum(len(t) for t in uniq))
print("player-facing only    :", len(player))
print("\ncategory counts:")
for k, v in cat.most_common():
    print(f"   {v:5d}  {k}")
print("\nflags on kept rows:")
for k, v in flags.most_common():
    print(f"   {v:5d}  {k}")
print("\nrejections:")
for k, v in rej.most_common(14):
    print(f"   {v:6d}  {k}")
print("\nlength buckets (distinct):")
for b in ["01-05", "06-10", "11-20", "21-40", "41-80", "81-160", "161+"]:
    print(f"   {b:8s} {buckets[b]}")
print("\nlongest 3:")
for t in sorted(uniq, key=len, reverse=True)[:3]:
    print(f"   len={len(t)} {t[:90]!r}")
json.dump({"kept_total": len(records), "kept_distinct": len(uniq),
           "chars_all": sum(len(t) for t in texts), "chars_distinct": sum(len(t) for t in uniq),
           "player_facing_entries": len(player), "categories": dict(cat),
           "flags": dict(flags), "rejections": dict(rej), "buckets": dict(buckets),
           "longest": sorted(uniq, key=len, reverse=True)[:5],
           "reps": {c: [r["text"] for r in records if r["category"] == c][:8] for c in cat}},
          open(os.path.join(D, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nWROTE data/strings_raw.json, dump/strings_all_classified.jsonl, dump/stats.json")
