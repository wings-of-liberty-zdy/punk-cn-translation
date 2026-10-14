import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json

OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
methods = json.load(open(os.path.join(OUT, "q1_dll_methods.json"), encoding="utf-8"))
by = {(m["type"], m["name"]): m for m in methods}

lines = []
def w(s=""):
    lines.append(s); print(s)

w("=== A. callers of ShopItemsConfig::Parse / ParseLine / ParseCurrencyOrder ===")
for m in methods:
    for c in m["calls"]:
        if "ShopItemsConfig::Parse" in c or c.endswith("::Parse"):
            w(f"  {m['type']}::{m['name']}  ->  {c}   strings={m['strings'][:3]}")

w("\n=== B. every member of type ShopItemsConfig (own methods) ===")
for m in methods:
    if m["type"] == "ShopItemsConfig":
        w(f"  {m['name']}  calls={m['calls']}")
        w(f"      strings={m['strings']}")
        w(f"      fields={m['fields']}  types={m['types']}")

w("\n=== C. any method touching a field/property literally named 'url' (case-insens) ===")
n = 0
for m in methods:
    hits = [f for f in m["fields"] if f.lower() == "url" or f.lower().endswith("url")]
    hits += [c for c in m["calls"] if c.lower().split("::")[-1] in ("get_url", "set_url", "get_url()")]
    if hits:
        n += 1
        w(f"  {m['type']}::{m['name']}  {sorted(set(hits))}")
if n == 0:
    w("  (none)")

w("\n=== D. methods whose owner type name contains 'Shop' (all shop classes) ===")
for m in sorted(methods, key=lambda x: (x["type"], x["name"])):
    if "Shop" in m["type"]:
        w(f"  {m['type']}::{m['name']}  calls={m['calls'][:8]}")

w("\n=== E. is ShopItemsConfig referenced anywhere as a *type* (newobj/cast/ldfld owner)? ===")
n = 0
for m in methods:
    if any("ShopItemsConfig" in t for t in m["types"]) and m["type"] != "ShopItemsConfig":
        n += 1
        w(f"  {m['type']}::{m['name']}  types={[t for t in m['types'] if 'ShopItemsConfig' in t]}")
if n == 0:
    w("  (only its own members reference the type)")

w("\n=== F. UnityEditor references (would indicate editor-only code shipped) ===")
n = 0
for m in methods:
    hits = [t for t in m["types"] if "UnityEditor" in t] + [c for c in m["calls"] if "UnityEditor" in c]
    if hits:
        n += 1
        w(f"  {m['type']}::{m['name']}  {sorted(set(hits))[:4]}")
if n == 0:
    w("  (none)")

w("\n=== G. all methods calling anything with 'Parse' in the name, with their strings ===")
for m in methods:
    hits = [c for c in m["calls"] if "Parse" in c]
    if hits and "ShopItems" not in m["type"]:
        w(f"  {m['type']}::{m['name']} -> {sorted(set(hits))}  strings={m['strings'][:4]}")

open(os.path.join(OUT, "q1_caller_trace.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
