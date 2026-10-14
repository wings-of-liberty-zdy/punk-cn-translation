import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os

ROOT = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"
NEEDLES = [
    b"docs.google.com",
    b"2PACX-1vTF4s2BdJrSSrwYgrHgye7QDmyF4y73XqnxG1nCCuxnGiHK_Zxo4Q1EFsrvoDoWaEMNsqgRmzK0gaqm",
    b"output=csv",
    b"get_daily_seed",
]
# UTF-16LE variants
for x in list(NEEDLES):
    NEEDLES.append(x.decode("ascii").encode("utf-16-le"))

hits = []
scanned = 0
total_bytes = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        if sz > 400 * 1024 * 1024:
            print("SKIP huge:", p, sz)
            continue
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except Exception as e:
            print("READ FAIL", p, repr(e))
            continue
        scanned += 1
        total_bytes += len(data)
        for nd in NEEDLES:
            idx = data.find(nd)
            if idx >= 0:
                hits.append((p, nd[:40], idx, sz))

print(f"scanned files={scanned} bytes={total_bytes}")
print("=== hits ===")
seen = set()
for p, nd, idx, sz in hits:
    key = (p, nd)
    if key in seen:
        continue
    seen.add(key)
    enc = "utf16le" if b"\x00" in nd else "ascii"
    print(f"  {p}  needle={nd!r} ({enc})  offset={idx}  filesize={sz}")
if not hits:
    print("  (no hits)")
