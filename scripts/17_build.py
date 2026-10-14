import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, re, collections

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
D = os.path.join(ROOT, "data", "dump")

mb = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]
us = json.load(open(os.path.join(D, "us_Punk.Main.dll.json"), encoding="utf-8"))
us_att = us["attribution"]

# ============================ classification rules ============================
NOISE_LEAF = {
    "m_name",             # Unity object / asset name (internal identifier)
    "m_script",
    "m_id", "id", "guid", "entityid",
    "m_path", "m_groups", "m_processors", "m_interactions", "m_expectedcontroltype",
    "m_action", "m_bindinggroup",
    "paramname", "namedoverride", "hudanimparamname", "debugicon",
    "type",
    "m_targetassemblytypename", "m_methodname", "m_objectargumentassemblytypename",
    "m_stringargument",
    "m_normaltrigger", "m_highlightedtrigger", "m_pressedtrigger",
    "m_selectedtrigger", "m_disabledtrigger",
    "m_openingdefinition", "m_closingdefinition",
    "m_version", "m_familyname", "m_stylename", "charactersequence", "name",
    "m_keys",
}
ENDS_NOISE = ("sfx", "id", "guid", "path", "filename", "rifftypeid", "bytesstring",
              "prefabmodifications")

# fields we DO translate, with a fixed category
FIELD_CATEGORY = {
    "displayname": "item_module_desc",
    "description": "item_module_desc",
    "inputhintmessage": "tutorial_hint",
    "itemwheelhintmessagekbm": "tutorial_hint",
    "itemwheelhintmessagegamepad": "tutorial_hint",
    "format": "other",
    "messageformat": "other",
}

# Unity built-in Debug UI / inspector placeholder text (not shipped to players)
UNITY_DEBUG_TEXT = {
    "new text", "foldout", "foldout\n", "message text\n", "panel title", "bitfield\n",
    "vector2\n", "vector4\n", "color\n", "enum", "allocated", "reserved", "button",
    "wibble", "reset", "audio", "mono", "test", "avg", "fps", "ram", ">>>", "<<<",
    "0.000\n", "0 %\n", "0\n", "-", "+", "<", ">", "a", "b", "g", "r", "w", "x", "y", "z",
    "#####", "< 0 >", "##.#", "###", "-##", ".1%", "1%", "mb", "db", "ms",
    "vram: ####mb. max texture size: ####px. shader level: ##",
    "graphics api: graphics api version [level ##]",
    "cpu: processor model [# cores]",
    "window: ####x####@##hz[###dpi]",
    "os: os version [platform]",
    "gpu: graphics card name",
    "screen: ####x####@##hz",
    "ram: #### mb",
}

DEVLOG_PAT = re.compile(
    r"(failed|could not|couldn't|can't|cannot|unable|not found|not set|not defined|"
    r"not suitable|not implemented|trying to|tried to|invalid|error|exception|missing|"
    r"is null|are null|no animator|no barrel|no camera|no damage|no end poi|no cues|"
    r"should have|must be|wrong |unknown error|clusters cannot|values must|value must|"
    r"collider iteration|display not implemented|power core has invalid|"
    r"steamworks\.net|singleton of type|memento type|entity id missing|"
    r"destroyed entity were saved|save destroyedobject|no gamecontroller|"
    r"cancelled infinite loop|only extensions|only works while|"
    r"can only be used on|not in the correct|bug report from user|"
    r"reference the readme|refer to the|here is the description|"
    r"generated in |finished in |generated in\{|loaded in |setting for layer|"
    r"connection type not defined|damage type not found|biom not found|"
    r"trying to unpack|trying to unload|trying to select|trying to assign|"
    r"trying to add impact|trying to shoot|trying to apply loadout|"
    r"trying to initialize|no damage set up|is not initialized|"
    r"wrong indexing|no resource|not in the dictionary|"
    r"https?://|www\.|discord\.gg|C:\\\\Projects|"
    r"^\.|\.cs$|\.tiff$|\.txt$|\.json$|\.wav$|\.bwf$|"
    r"^_|^m_|^[A-Za-z]+Volume$|^[a-z]+[A-Z][A-Za-z]*$)",
    re.I,
)

ALLOWLIST_US = {
    "Success! {0}", "Upload failed", "Unknown error", "Failed to load",
    "Score uplaoded", "Uploading score to ", "Loading leaderboard: ",
    "Failed to load leaderboard", "Leaderboard entries downloaded",
    "SCANNING AREA", "NEW LOCATION ADDED", "COST PER PROJECTILE",
    "MAX POWER CORES: {0}", "ATTACHED POWER CORES: {0} / {1}",
    "Fuel low", "Fuel critical", "Incompatible slot", "Incompatible connections",
    "Incompatible augmentation", "Cannot apply {0} to {1}", "Game does not work",
    "Ship loadout unlocked: ", "Stations unlocked: {0}\n", "Enemies killed: {0}\n",
    "Total deaths: {0}\n", "Final bosses killed: {0}/4\n", "Final bosses killed: {0}/{1}",
    "Run duration: {0:hh':'mm':'ss}\n", "Respawn on next station unlock",
    "Biome: ", "Difficulty: {0}\n", "Seed: {0}\nGame version: {1}",
    "Effectiveness: {0}%", "Burn level: {0}\n", "Interest: {0}\n", "Distance: {0}\n",
    "Explosion damage", "Explosion radius", "Explosion dmg", "Contact Damage",
    "Discharge damage", "Discharge chain length", "Knockback Force", "Fire Rate",
    "Burst Size", "Burst Delay", "Projectile Count", "Angle Variance", "Angle Offset",
    "Spread", "Damage", "Range", "Speed", "Headlights", "Duration: ", "Cost", "COST",
    "Select", "Cancel", "Activate", "Unequip", "Shop", "Station", "Consumable",
    "Discharge", "Offline", "Powered", "Navigate", "Interact", "Highlighted",
    "Selection", "Connected", "FirstOpen", "Visible",
}

records = []
classified = []


def add(source, category, key, text, decision, reason):
    rec = {"source": source, "category": category, "key_or_context": key, "text": text}
    records.append(rec)
    classified.append({**rec, "decision": decision, "reason": reason})


# ---------------------------- asset side ----------------------------
for r in mb:
    t = r["text"]
    leaf = r["field"].split(".")[-1].split("[")[0]
    ll = leaf.lower()
    key = f"{r['source']}|{r['cls']}|{r['field']}|go={r['go']}|pid={r['pid']}"
    src = f"{r['source']}:{r['cls']}"

    if not t.strip():
        classified.append({"source": src, "category": "not_translatable",
                           "key_or_context": key, "text": t, "decision": "reject",
                           "reason": "empty"})
        continue
    if r["field"].startswith("serializationData"):
        classified.append({"source": src, "category": "not_translatable",
                           "key_or_context": key, "text": t, "decision": "reject",
                           "reason": "serializationData blob"})
        continue
    if ll in NOISE_LEAF or any(ll.endswith(e) for e in ENDS_NOISE):
        classified.append({"source": src, "category": "not_translatable",
                           "key_or_context": key, "text": t, "decision": "reject",
                           "reason": f"non-text field '{leaf}'"})
        continue
    if t.startswith("UnityEngine.") and ", Version=" in t:
        classified.append({"source": src, "category": "not_translatable",
                           "key_or_context": key, "text": t, "decision": "reject",
                           "reason": "assembly-qualified type name"})
        continue
    if r["field"].startswith("prefabs[") or r["field"].startswith("m_OnClick"):
        classified.append({"source": src, "category": "not_translatable",
                           "key_or_context": key, "text": t, "decision": "reject",
                           "reason": "UnityEvent / debug-UI wiring"})
        continue

    if ll in FIELD_CATEGORY:
        add(src, FIELD_CATEGORY[ll], key, t, "keep", f"data field '{leaf}'")
        continue

    if r["cls"] in ("TextMeshProUGUI", "Text") and ll in ("m_text", "m_Text".lower()):
        v = t.strip()
        if v.lower() in UNITY_DEBUG_TEXT:
            classified.append({"source": src, "category": "not_translatable",
                               "key_or_context": key, "text": t, "decision": "reject",
                               "reason": "Unity built-in DebugUI placeholder"})
            continue
        if re.fullmatch(r"[\d\s/%+.,:x-]*", v):
            classified.append({"source": src, "category": "not_translatable",
                               "key_or_context": key, "text": t, "decision": "reject",
                               "reason": "numeric / punctuation only (runtime value)"})
            continue
        if re.search(r"^(PRESS|HOLD|USE|MOVE|OPEN|SELECT|TAP|CLICK)\b", v) and len(v) > 8:
            add(src, "tutorial_hint", key, t, "keep", "imperative input prompt")
            continue
        if len(v) >= 60 or (len(v) > 15 and "?" in v) or re.search(r"THANK|WELCOME|GOOD LUCK", v, re.I):
            add(src, "dialogue_story", key, t, "keep", "prose / narrative / confirmation dialog")
            continue
        if v.upper() == v or len(v) <= 24:
            add(src, "ui_menu", key, t, "keep", "short UI label (menu/button/HUD)")
            continue
        add(src, "other", key, t, "keep", "residual UI string")
        continue

    classified.append({"source": src, "category": "not_translatable",
                       "key_or_context": key, "text": t, "decision": "reject",
                       "reason": f"unclassified field '{leaf}'"})

# ---------------------------- DLL side ----------------------------
for r in us["rows"]:
    t = r["text"]
    a = us_att.get(t) or []
    ctx = ";".join(sorted({f"{x[0]}.{x[1]}" for x in a if x[0]})) or "unattributed"
    key = f"Punk.Main.dll#US@{r['heap_offset']}|{ctx}"
    src = "Punk.Main.dll"
    v = t.strip()

    if not v:
        classified.append({"source": src, "category": "not_translatable", "key_or_context": key,
                           "text": t, "decision": "reject", "reason": "empty"})
        continue
    if t in ALLOWLIST_US:
        cat = "ui_menu"
        if any(k in t for k in ("SCANNING", "PICK UP", "Respawn")):
            cat = "tutorial_hint"
        add(src, cat, key, t, "keep", "manual allowlist (verified player-facing)")
        continue
    if re.fullmatch(r"[_A-Za-z][A-Za-z0-9_]*(\.(wav|bwf|json|txt|tiff|cs))?", v) and " " not in v \
            and not v.isupper():
        classified.append({"source": src, "category": "not_translatable", "key_or_context": key,
                           "text": t, "decision": "reject", "reason": "identifier / file name / shader prop"})
        continue
    if re.fullmatch(r"[\W\d\s{}:.,/&#;<>=\"'\[\]\\-]*", v):
        classified.append({"source": src, "category": "not_translatable", "key_or_context": key,
                           "text": t, "decision": "reject", "reason": "format spec / punctuation only"})
        continue
    if DEVLOG_PAT.search(v):
        classified.append({"source": src, "category": "dev_log", "key_or_context": key,
                           "text": t, "decision": "reject", "reason": "dev log / exception / diagnostic"})
        continue
    if v.isupper() and len(v) >= 4:
        add(src, "ui_menu", key, t, "keep", "ALL-CAPS UI label")
        continue
    add(src, "other", key, t, "keep", "residual DLL literal (human review needed)")

# ---------------------------- write ----------------------------
with open(os.path.join(ROOT, "data", "strings_raw.json"), "w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)
with open(os.path.join(D, "strings_all_classified.jsonl"), "w", encoding="utf-8") as fh:
    for c in classified:
        fh.write(json.dumps(c, ensure_ascii=False) + "\n")

kept = records
texts = [r["text"] for r in kept]
uniq = sorted(set(texts))
cat = collections.Counter(r["category"] for r in kept)
rej = collections.Counter(c["reason"].split("'")[0].strip() for c in classified if c["decision"] == "reject")

print("=== KEPT ===")
print("total entries        :", len(kept))
print("distinct texts       :", len(uniq))
print("total chars (all)    :", sum(len(t) for t in texts))
print("total chars (distinct):", sum(len(t) for t in uniq))
print("\ncategory counts:")
for k, v in cat.most_common():
    print(f"   {v:5d}  {k}")
print("\nrejection reasons:")
for k, v in rej.most_common(12):
    print(f"   {v:6d}  {k}")
print("\n--- longest 5 ---")
for t in sorted(uniq, key=len, reverse=True)[:5]:
    print(f"  len={len(t)} {t[:120]!r}")
print("\n--- length distribution (distinct) ---")
buckets = collections.Counter()
for t in uniq:
    L = len(t)
    b = "01-05" if L <= 5 else "06-10" if L <= 10 else "11-20" if L <= 20 else \
        "21-40" if L <= 40 else "41-80" if L <= 80 else "81-160" if L <= 160 else "161+"
    buckets[b] += 1
for b in ["01-05", "06-10", "11-20", "21-40", "41-80", "81-160", "161+"]:
    print(f"   {b:8s} {buckets[b]}")

json.dump({"kept_total": len(kept), "kept_distinct": len(uniq),
           "chars_all": sum(len(t) for t in texts), "chars_distinct": sum(len(t) for t in uniq),
           "categories": dict(cat), "rejections": dict(rej),
           "buckets": dict(buckets),
           "longest": sorted(uniq, key=len, reverse=True)[:10]},
          open(os.path.join(D, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nWROTE data/strings_raw.json + dump/strings_all_classified.jsonl + dump/stats.json")
