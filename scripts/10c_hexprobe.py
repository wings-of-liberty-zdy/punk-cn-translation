import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import struct
import pefile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
pe = pefile.PE(DLL, fast_load=True)
RAW = bytes(pe.__data__)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]])
cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
cli_off = pe.get_offset_from_rva(cli.VirtualAddress)
meta_rva, meta_size = struct.unpack_from("<II", RAW, cli_off + 8)
m = pe.get_offset_from_rva(meta_rva)
print("meta_rva", hex(meta_rva), "meta file off", m, "align4", m % 4, "size", meta_size)
sig, a, b, c, vlen = struct.unpack_from("<IHHII", RAW, m)
p = m + 16 + vlen
p = (p + 3) & ~3
flags, nstreams = struct.unpack_from("<HH", RAW, p)
p += 4
heaps = {}
for _ in range(nstreams):
    off, size = struct.unpack_from("<II", RAW, p)
    p += 8
    end = RAW.index(b"\x00", p)
    name = RAW[p:end].decode("ascii")
    p = (end + 4) & ~3
    heaps[name] = (m + off, size)

us_off, us_size = heaps["#US"]
print("us_off", us_off, "us_size", us_size)
chunk = RAW[us_off:us_off + 96]
print("first 96 raw bytes:")
print(" ", chunk.hex(" "))
print("  as bytes:", chunk)


def cint(b, i):
    x = b[i]
    if x & 0x80 == 0:
        return x, i + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[i + 1], i + 2
    return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4


data = RAW[us_off:us_off + us_size]
for variant in ("withflag", "noflag"):
    i = 1
    out = []
    while i < len(data) and len(out) < 6:
        start = i
        ln, i = cint(data, i)
        if ln == 0:
            continue
        blob = data[i:i + ln]
        i += ln
        if variant == "withflag":
            body = blob[1:]
        else:
            body = blob
        if body.endswith(b"\x00"):
            body = body[:-1]
        if len(body) % 2:
            body = body[:-1]
        out.append((start, ln, body.decode("utf-16-le", errors="replace")))
    print(f"\n--- variant={variant} ---")
    for s in out:
        print("   off=%-6d len=%-4d %r" % s)
    print("   final cursor:", i, "of", len(data))
