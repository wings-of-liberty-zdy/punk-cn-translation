import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, re

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))

print("=== types whose name suggests localization / string tables ===")
seen = collections.Counter()
for m in methods:
    t = m["type"] or ""
    if re.search(r"Local|Lang|Translat|StringTable|TextTable|Strings|I18n|Locale|ResourceString|Term", t, re.I):
        seen[t] += 1
for t, c in seen.most_common(40):
    print(f"  {c:5d}  {t}")

print("\n=== methods calling anything localization-ish ===")
cnt = collections.Counter()
for m in methods:
    for c in m["calls"]:
        if re.search(r"Local|Lang|Translat|I18n|Locale|GetTerm|GetString|StringTable", c, re.I):
            cnt[c] += 1
for c, n in cnt.most_common(40):
    print(f"  {n:5d}  {c}")

print("\n=== methods with 'missing for' / key-style literals ===")
for m in methods:
    for s in m["strings"]:
        if re.search(r"missing|not implemented yet|META_|PLAYER_PREF", s):
            print(f"  {m['type']}::{m['name']}  {s[:70]!r}")
            print(f"      calls={m['calls'][:10]}")

print("\n=== all string-returning helper methods that build UI text (Get*Text/Get*Message/Get*Name/Get*String/GetDelta/GetProperties) ===")
for m in methods:
    if re.match(r"^(Get|Build|Format|Make)", m["name"]) and re.search(
            r"Text|Message|Name|String|Delta|Propert|Label|Desc|Hint|Title|Step", m["name"]):
        print(f"  {m['type']}::{m['name']}  strings={[s[:60] for s in m['strings']]}  calls={m['calls'][:5]}")
