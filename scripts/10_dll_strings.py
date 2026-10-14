import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, struct, traceback
import dnfile

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

# ---------- raw #US heap reader (independent of dnfile's blob quirks) ----------
def read_us_heap(dll_path):
    import pefile
    pe = pefile.PE(dll_path, fast_load=True)
    RAW = bytes(pe.__data__) if not isinstance(pe.__data__, (bytes, bytearray)) else pe.__data__
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]])
    cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
    cli_off = pe.get_offset_from_rva(cli.VirtualAddress)
    meta_rva, meta_size = struct.unpack_from("<II", RAW, cli_off + 8)
    m = pe.get_offset_from_rva(meta_rva)
    sig, major, minor, res, vlen = struct.unpack_from("<IHHII", RAW, m)
    assert sig == 0x424A5342, hex(sig)
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
    data = RAW[us_off:us_off + us_size]

    def cint(b, i):
        x = b[i]
        if x & 0x80 == 0:
            return x, i + 1
        if x & 0xC0 == 0x80:
            return ((x & 0x3F) << 8) | b[i + 1], i + 2
        return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4

    strings = {}
    i = 1 if len(data) > 0 else 0
    while i < len(data):
        start = i
        try:
            ln, i = cint(data, i)
        except IndexError:
            break
        if ln == 0:
            continue
        blob = data[i:i + ln]
        i += ln
        if len(blob) < 1:
            continue
        # NOTE: empirically verified against this assembly's raw heap bytes --
        # the blob content starts directly with UTF-16LE chars (no leading flag
        # byte); the compressed length already includes the terminal 0x00.
        body = blob
        if body.endswith(b"\x00"):
            body = body[:-1]
        if len(body) % 2:
            body = body[:-1]
        try:
            s = body.decode("utf-16-le", errors="replace")
        except Exception:
            continue
        strings[start] = s
    pe.close()
    return strings


def ldstr_attribute(dll_path, us):
    """Blind-scan method bodies for 0x72 <token> to attribute strings to (type, method)."""
    import pefile
    pe = pefile.PE(dll_path, fast_load=True)
    dn = dnfile.dnPE(dll_path, fast_load=True)
    dn.parse_data_directories()
    md = dn.net.mdtables
    att = collections.defaultdict(list)
    RAW = bytes(pe.__data__) if not isinstance(pe.__data__, (bytes, bytearray)) else pe.__data__
    for t in (md.TypeDef or []):
        try:
            owner[t.TypeDefOrRef.row_index] = str(t.TypeNamespace) + "." + str(t.TypeName) if t.TypeNamespace else str(t.TypeName)
        except Exception:
            pass
    data = RAW
    tdef_name = {}
    for i, t in enumerate(md.TypeDef or [], start=1):
        ns = str(t.TypeNamespace or "")
        nm = str(t.TypeName or "")
        tdef_name[i] = (ns + "." + nm) if ns else nm
    for m in (md.MethodDef or []):
        rva = m.Rva
        if not rva:
            continue
        try:
            off = pe.get_offset_from_rva(rva)
        except Exception:
            continue
        if off <= 0 or off + 1 >= len(data):
            continue
        hdr = data[off]
        if hdr & 3 == 2:
            size = hdr >> 2
            code = data[off + 1:off + 1 + size]
        elif hdr & 3 == 3:
            size = struct.unpack_from("<I", data, off + 4)[0]
            code = data[off + 12:off + 12 + size]
        else:
            continue
        owner_name = ""
        try:
            ci = m.class_
            if getattr(ci, "table", None) is not None and ci.table.name == "TypeDef":
                owner_name = tdef_name.get(ci.row_index, "")
        except Exception:
            owner_name = ""
        mname = str(m.Name)
        # find 0x72 tokens
        j = 0
        base = None
        while j < len(code) - 4:
            if code[j] == 0x72:
                tok = struct.unpack_from("<I", code, j + 1)[0]
                if tok >> 24 == 0x70:
                    idx = tok & 0x00FFFFFF
                    if idx in us:
                        att[us[idx]].append((owner_name, mname, j))
            j += 1
    pe.close()
    return att


target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(MANAGED, "Punk.Main.dll")
base = os.path.basename(target)
print("== parsing", base, os.path.getsize(target))
us = read_us_heap(target)
print("   #US entries:", len(us), " non-empty:", sum(1 for v in us.values() if v.strip()),
      " distinct non-empty:", len({v for v in us.values() if v.strip()}))
try:
    att = ldstr_attribute(target, us)
    print("   attributed:", len(att))
except Exception:
    traceback.print_exc()
    att = {}

rows = []
for k, v in us.items():
    if not v:
        continue
    rows.append({"heap_offset": k, "text": v})
rows.sort(key=lambda r: r["heap_offset"])
out = {"dll": base,
       "total_us": len(us),
       "rows": rows,
       "attribution": {k: [list(x) for x in v] for k, v in att.items()}}
with open(os.path.join(OUT, f"us_{base}.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("   wrote", f"us_{base}.json", "rows:", len(rows))

