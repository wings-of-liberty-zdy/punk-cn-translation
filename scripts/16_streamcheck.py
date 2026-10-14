import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, re, collections

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
probes = [b"HELLO AND WELCOME", b"Forms a shield", b"CAPS UP", b"CONTINUE", b"MODULENAME"]

for fn in ["resources.resource", "resources.assets.resS", "sharedassets3.resource",
           "sharedassets0.assets.resS", "globalgamemanagers.assets.resS"]:
    p = os.path.join(DATA, fn)
    if not os.path.exists(p):
        continue
    n = os.path.getsize(p)
    hits = {pr: 0 for pr in probes}
    with open(p, "rb") as fh:
        CH = 8 << 20
        prev = b""
        while True:
            b = fh.read(CH)
            if not b:
                break
            buf = prev + b
            for pr in probes:
                hits[pr] += buf.count(pr)
            prev = buf[-64:]
    print(f"{fn} ({n/1e6:.1f} MB): " + ", ".join(f"{pr.decode()}={hits[pr]}" for pr in probes))

# StreamingAssets listing
sa = os.path.join(DATA, "StreamingAssets")
print("\nStreamingAssets exists:", os.path.isdir(sa))
if os.path.isdir(sa):
    for root, dirs, files in os.walk(sa):
        for f in files:
            fp = os.path.join(root, f)
            print(f"   {os.path.relpath(fp, sa)}  {os.path.getsize(fp)}")

# any .txt/.json/.csv/.xml anywhere in Punk_Data that could hold language data
print("\n=== text-ish files anywhere under Punk_Data (excluding Managed) ===")
for root, dirs, files in os.walk(DATA):
    if "Managed" in root or "MonoBleedingEdge" in root:
        continue
    for f in files:
        if f.lower().endswith((".txt", ".json", ".csv", ".xml", ".lang", ".po", ".tsv", ".yaml", ".yml", ".ini", ".bytes")):
            fp = os.path.join(root, f)
            print(f"   {os.path.relpath(fp, DATA)}  {os.path.getsize(fp)}")
