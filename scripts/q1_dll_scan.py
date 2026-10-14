import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, struct, collections
import dnfile, pefile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

# ---------------------------------------------------------------- opcode table
# operand kinds
NONE, I1, I4, I8, R4, R8, METH, FIELD, TYPE, STR, SIG, TOK, SWITCH, VAR1, VAR2, BR1, BR4 = range(17)
SIZE = {NONE: 0, I1: 1, I4: 4, I8: 8, R4: 4, R8: 8, METH: 4, FIELD: 4, TYPE: 4,
        STR: 4, SIG: 4, TOK: 4, VAR1: 1, VAR2: 2, BR1: 1, BR4: 4}

OP1 = {}
for c in range(0x00, 0xFF):
    OP1[c] = NONE
# explicit operand-carrying opcodes (ECMA-335 III.1.2)
for c, k in [
    (0x0E, VAR1), (0x0F, VAR1), (0x10, VAR1), (0x11, VAR1), (0x12, VAR1), (0x13, VAR1),
    (0x1F, I1), (0x20, I4), (0x21, I8), (0x22, R4), (0x23, R8),
    (0x27, METH), (0x28, METH), (0x29, SIG), (0x2B, BR1), (0x2C, BR1), (0x2D, BR1),
    (0x2E, BR1), (0x2F, BR1), (0x30, BR1), (0x31, BR1), (0x32, BR1), (0x33, BR1),
    (0x34, BR1), (0x35, BR1), (0x36, BR1), (0x37, BR1),
    (0x38, BR4), (0x39, BR4), (0x3A, BR4), (0x3B, BR4), (0x3C, BR4), (0x3D, BR4),
    (0x3E, BR4), (0x3F, BR4), (0x40, BR4), (0x41, BR4), (0x42, BR4), (0x43, BR4), (0x44, BR4),
    (0x45, SWITCH),
    (0x6F, METH), (0x70, TYPE), (0x71, TYPE), (0x72, STR), (0x73, METH), (0x74, TYPE),
    (0x75, TYPE), (0x79, TYPE),
    (0x7B, FIELD), (0x7C, FIELD), (0x7D, FIELD), (0x7E, FIELD), (0x7F, FIELD), (0x80, FIELD),
    (0x81, TYPE), (0x8C, TYPE), (0x8D, TYPE), (0x8F, TYPE),
    (0xA3, TYPE), (0xA4, TYPE), (0xA5, TYPE),
    (0xC2, TYPE), (0xC6, TYPE),
    (0xD0, TOK),
    (0xDD, BR4), (0xDE, BR1),
]:
    OP1[c] = k

OP2 = {}
for c in range(0x00, 0x20):
    OP2[c] = NONE
for c, k in [
    (0x06, METH), (0x07, METH), (0x09, VAR2), (0x0A, VAR2), (0x0B, VAR2),
    (0x0C, VAR2), (0x0D, VAR2), (0x0E, VAR2),
    (0x12, I1), (0x15, TYPE), (0x16, TYPE), (0x19, I1), (0x1C, TYPE),
]:
    OP2[c] = k


def decode(code):
    """Yield (offset, opcode_byte, kind, operand_int). Returns None on failure."""
    out = []
    i = 0
    n = len(code)
    while i < n:
        op = code[i]
        start = i
        i += 1
        if op == 0xFE:
            if i >= n:
                return None
            op2 = code[i]
            i += 1
            kind = OP2.get(op2)
            if kind is None:
                return None
            key = 0xFE00 | op2
        else:
            kind = OP1.get(op)
            if kind is None:
                return None
            key = op
        operand = None
        if kind == SWITCH:
            if i + 4 > n:
                return None
            cnt = struct.unpack_from("<I", code, i)[0]
            i += 4 + 4 * cnt
            if i > n:
                return None
        elif kind != NONE:
            sz = SIZE[kind]
            if i + sz > n:
                return None
            if sz == 1:
                operand = code[i]
            elif sz == 2:
                operand = struct.unpack_from("<H", code, i)[0]
            elif sz == 4:
                operand = struct.unpack_from("<i", code, i)[0]
            elif sz == 8:
                operand = struct.unpack_from("<q", code, i)[0]
            i += sz
        out.append((start, key, kind, operand))
    return out


# ---------------------------------------------------------------- metadata load
pe = pefile.PE(DLL, fast_load=True)
RAW = bytes(pe.__data__)
dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
md = dn.net.mdtables

# --- typedef ranges -> owning type of each MethodDef row
tdefs = md.TypeDef.rows
NestedClass = {}
try:
    for nc in md.NestedClass.rows:
        NestedClass[nc.NestedClass.row_index] = nc.EnclosingClass.row_index
except Exception:
    pass

method_owner = {}
type_names = {}
for ti, t in enumerate(tdefs, start=1):
    ns = str(t.TypeNamespace or "")
    nm = str(t.TypeName or "")
    full = (ns + "." + nm) if ns else nm
    type_names[ti] = full
    ml = t.MethodList
    if ml is None:
        continue
    if not isinstance(ml, list):
        ml = [ml]
    for x in ml:
        ri = getattr(x, "row_index", None)
        if ri:
            method_owner[ri] = full

# --- resolve coded token helpers
def resolve_type_token(tok):
    t = tok >> 24
    idx = tok & 0xFFFFFF
    try:
        if t == 0x01:
            r = md.TypeRef.rows[idx - 1]
            ns, nm = str(r.TypeNamespace or ""), str(r.TypeName or "")
            return (ns + "." + nm) if ns else nm
        if t == 0x02:
            r = md.TypeDef.rows[idx - 1]
            ns, nm = str(r.TypeNamespace or ""), str(r.TypeName or "")
            return (ns + "." + nm) if ns else nm
        if t == 0x1B:
            return "<TypeSpec:%d>" % idx
    except Exception:
        return None
    return None


def resolve_method_token(tok):
    """-> (declaring_type_or_None, method_name)"""
    t = tok >> 24
    idx = tok & 0xFFFFFF
    try:
        if t == 0x06:  # MethodDef
            r = md.MethodDef.rows[idx - 1]
            return method_owner.get(idx), str(r.Name)
        if t == 0x0A:  # MemberRef
            r = md.MemberRef.rows[idx - 1]
            owner = None
            try:
                ci = r.Class
                if ci.table is not None:
                    if ci.table.name == "TypeRef":
                        rr = md.TypeRef.rows[ci.row_index - 1]
                        ns, nm = str(rr.TypeNamespace or ""), str(rr.TypeName or "")
                        owner = (ns + "." + nm) if ns else nm
                    elif ci.table.name == "TypeDef":
                        rr = md.TypeDef.rows[ci.row_index - 1]
                        ns, nm = str(rr.TypeNamespace or ""), str(rr.TypeName or "")
                        owner = (ns + "." + nm) if ns else nm
                    elif ci.table.name == "TypeSpec":
                        owner = "<TypeSpec:%d>" % ci.row_index
            except Exception:
                pass
            return owner, str(r.Name)
        if t == 0x2B:  # MethodSpec (generic instantiation)
            r = md.MethodSpec.rows[idx - 1]
            try:
                inner = r.Method
                if inner.table is not None and inner.table.name == "MethodDef":
                    rr = md.MethodDef.rows[inner.row_index - 1]
                    return method_owner.get(inner.row_index), str(rr.Name)
                if inner.table is not None and inner.table.name == "MemberRef":
                    rr = md.MemberRef.rows[inner.row_index - 1]
                    return None, str(rr.Name)
            except Exception:
                pass
            return None, "<MethodSpec:%d>" % idx
    except Exception:
        return None, None
    return None, None


# --- #US heap (no leading flag byte in this assembly)
def read_us_heap():
    cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
    cli_off = pe.get_offset_from_rva(cli.VirtualAddress)
    meta_rva, _ = struct.unpack_from("<II", RAW, cli_off + 8)
    m = pe.get_offset_from_rva(meta_rva)
    sig, a, b, c, vlen = struct.unpack_from("<IHHII", RAW, m)
    p = (m + 16 + vlen + 3) & ~3
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

    def cint(bb, i):
        x = bb[i]
        if x & 0x80 == 0:
            return x, i + 1
        if x & 0xC0 == 0x80:
            return ((x & 0x3F) << 8) | bb[i + 1], i + 2
        return ((x & 0x1F) << 24) | (bb[i + 1] << 16) | (bb[i + 2] << 8) | bb[i + 3], i + 4

    strings = {}
    i = 1
    while i < len(data):
        start = i
        ln, i = cint(data, i)
        if ln == 0:
            continue
        blob = data[i:i + ln]
        i += ln
        body = blob
        if body.endswith(b"\x00"):
            body = body[:-1]
        if len(body) % 2:
            body = body[:-1]
        strings[start] = body.decode("utf-16-le", errors="replace")
    return strings


us = read_us_heap()
print("#US entries:", len(us))

# ---------------------------------------------------------------- walk methods
methods = []
decode_fail = 0
for mi, m in enumerate(md.MethodDef.rows, start=1):
    rva = m.Rva
    if not rva:
        continue
    try:
        off = pe.get_offset_from_rva(rva)
    except Exception:
        continue
    if off <= 0 or off + 1 >= len(RAW):
        continue
    hdr = RAW[off]
    if hdr & 3 == 2:
        size = hdr >> 2
        code = RAW[off + 1:off + 1 + size]
    elif hdr & 3 == 3:
        size = struct.unpack_from("<I", RAW, off + 4)[0]
        code = RAW[off + 12:off + 12 + size]
    else:
        continue
    ins = decode(code)
    if ins is None:
        decode_fail += 1
        continue
    owner = method_owner.get(mi, "?")
    name = str(m.Name)
    calls, strs, types, fields = [], [], [], []
    for (o, key, kind, operand) in ins:
        if kind == STR and operand is not None and (operand & 0xFFFFFF) in us:
            strs.append(us[operand & 0xFFFFFF])
        elif kind == METH and operand is not None:
            ot, mn = resolve_method_token(operand)
            if mn:
                calls.append(f"{ot}::{mn}" if ot else mn)
        elif kind == TYPE and operand is not None:
            tn = resolve_type_token(operand)
            if tn:
                types.append(tn)
        elif kind == FIELD and operand is not None:
            t = operand >> 24
            idx = operand & 0xFFFFFF
            try:
                if t == 0x04:
                    fr = md.Field.rows[idx - 1]
                    fields.append(str(fr.Name))
                elif t == 0x0A:
                    fr = md.MemberRef.rows[idx - 1]
                    fields.append(str(fr.Name))
            except Exception:
                pass
    methods.append({"row": mi, "type": owner, "name": name,
                    "calls": calls, "strings": strs, "types": types, "fields": fields,
                    "n_ins": len(ins)})

print("methods decoded:", len(methods), " decode_failed:", decode_fail)

with open(os.path.join(OUT, "q1_dll_methods.json"), "w", encoding="utf-8") as fh:
    json.dump(methods, fh, ensure_ascii=False)

# ---------------------------------------------------------------- queries
print("\n" + "=" * 70)
print("QUERY 1: any method mentioning ShopItemsConfig (as owner, called type, or string)")
for m in methods:
    blob = " ".join([m["type"]] + m["calls"] + m["types"] + m["fields"])
    if "ShopItems" in blob or any("ShopItems" in s for s in m["strings"]):
        print(f"  {m['type']}::{m['name']}")
        print(f"     types={m['types'][:6]}")
        print(f"     calls={m['calls'][:10]}")
        print(f"     strings={m['strings'][:6]}")

print("\n" + "=" * 70)
print("QUERY 2: methods calling get_url / url-ish members")
for m in methods:
    hits = [c for c in m["calls"] if "get_url" in c or "set_url" in c or c.endswith("::url")]
    if hits:
        print(f"  {m['type']}::{m['name']}  -> {sorted(set(hits))}")

print("\n" + "=" * 70)
print("QUERY 3: methods using UnityWebRequest / WWW / DownloadHandler / HttpClient / WebClient")
NETPAT = ("UnityWebRequest", "DownloadHandler", "UploadHandler", "WWW", "HttpClient",
          "WebClient", "HttpWebRequest", "WebRequest", "DiscordWebhook", "Webhook",
          "UnityWebRequestAsyncOperation")
for m in methods:
    hits = sorted({c for c in m["calls"] if any(p in c for p in NETPAT)}
                  | {t for t in m["types"] if any(p in t for p in NETPAT)})
    if hits:
        print(f"  {m['type']}::{m['name']}")
        print(f"     net={hits[:8]}")
        if m["strings"]:
            print(f"     strings={[s[:90] for s in m['strings'][:4]]}")

print("\n" + "=" * 70)
print("QUERY 4: ldstr literals containing http / .csv / spreadsheets")
for m in methods:
    hits = [s for s in m["strings"] if "http" in s.lower() or ".csv" in s.lower() or "sheet" in s.lower()]
    if hits:
        print(f"  {m['type']}::{m['name']}")
        for s in hits:
            print(f"     {s[:200]!r}")

print("\n" + "=" * 70)
print("QUERY 5: all distinct net-related call targets across the assembly")
cnt = collections.Counter()
for m in methods:
    for c in m["calls"]:
        if any(p in c for p in NETPAT):
            cnt[c] += 1
for c, n in cnt.most_common(60):
    print(f"  {n:4d}  {c}")

pe.close()
print("\nwrote q1_dll_methods.json")
