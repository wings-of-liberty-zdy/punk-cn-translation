import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, struct, collections
import pefile, dnfile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

pe = pefile.PE(DLL, fast_load=True)
RAW = bytes(pe.__data__)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]])
cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
cli_off = pe.get_offset_from_rva(cli.VirtualAddress)
meta_rva, meta_size = struct.unpack_from("<II", RAW, cli_off + 8)
m = pe.get_offset_from_rva(meta_rva)
sig, a, b, c, vlen = struct.unpack_from("<IHHII", RAW, m)
p = m + 16 + vlen
p = (p + 3) & ~3
flags, nstreams = struct.unpack_from("<HH", RAW, p)
p += 4
print("metadata version len", vlen, "streams", nstreams)
heaps = {}
for _ in range(nstreams):
    off, size = struct.unpack_from("<II", RAW, p)
    p += 8
    end = RAW.index(b"\x00", p)
    name = RAW[p:end].decode("ascii")
    p = (end + 4) & ~3
    heaps[name] = (m + off, size)
    print(f"  stream {name!r} offset={off} size={size}")
print("streams:", list(heaps))

us_off, us_size = heaps["#US"]
data = RAW[us_off:us_off + us_size]


def cint(b, i):
    x = b[i]
    if x & 0x80 == 0:
        return x, i + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[i + 1], i + 2
    return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4


strings = {}
i = 1
consumed = 0
while i < len(data):
    start = i
    ln, i = cint(data, i)
    if ln == 0:
        continue
    blob = data[i:i + ln]
    i += ln
    consumed += ln
    if len(blob) < 2:
        continue
    body = blob[1:]
    if body.endswith(b"\x00"):
        body = body[:-1]
    if len(body) % 2:
        body = body[:-1]
    strings[start] = body.decode("utf-16-le", errors="replace")
print(f"#US heap size={us_size} consumed={consumed} cursor={i} entries={len(strings)}")

# cross-check with dnfile
dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
try:
    dfstr = [str(x) for x in dn.net.user_strings.get_us_list()]
    print("dnfile user_strings count:", len(dfstr))
    mine = {v for v in strings.values() if v}
    theirs = {s for s in dfstr if s}
    print("  mine only:", len(mine - theirs), " theirs only:", len(theirs - mine), " both:", len(mine & theirs))
    for s in list(theirs - mine)[:15]:
        print("    THEIRS-ONLY", repr(s))
except Exception as e:
    print("dnfile cross-check failed:", repr(e))

print("\n=== all #US strings (sorted by length desc, top 120) ===")
for s in sorted({v for v in strings.values() if v.strip()}, key=lambda x: -len(x))[:120]:
    print(f"  {len(s):4d}  {s!r}")
