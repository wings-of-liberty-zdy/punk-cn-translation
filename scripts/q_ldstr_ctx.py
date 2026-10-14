import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, struct
sys.path.insert(0, r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\scripts")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "qil", r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\scripts\q_il.py")

# reuse by re-implementing the tiny bits we need instead of executing q_il (which prints)
import dnfile, pefile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
NONE, I1, I4, I8, R4, R8, METH, FIELD, TYPE, STR, SIG, TOK, SWITCH, VAR1, VAR2, BR1, BR4 = range(17)
SIZE = {NONE: 0, I1: 1, I4: 4, I8: 8, R4: 4, R8: 8, METH: 4, FIELD: 4, TYPE: 4,
        STR: 4, SIG: 4, TOK: 4, VAR1: 1, VAR2: 2, BR1: 1, BR4: 4}
OP1 = {c: NONE for c in range(0x00, 0xFF)}
for c, k in [(0x0E, VAR1), (0x0F, VAR1), (0x10, VAR1), (0x11, VAR1), (0x12, VAR1), (0x13, VAR1),
             (0x1F, I1), (0x20, I4), (0x21, I8), (0x22, R4), (0x23, R8), (0x27, METH), (0x28, METH),
             (0x29, SIG), (0x2B, BR1), (0x2C, BR1), (0x2D, BR1), (0x2E, BR1), (0x2F, BR1), (0x30, BR1),
             (0x31, BR1), (0x32, BR1), (0x33, BR1), (0x34, BR1), (0x35, BR1), (0x36, BR1), (0x37, BR1),
             (0x38, BR4), (0x39, BR4), (0x3A, BR4), (0x3B, BR4), (0x3C, BR4), (0x3D, BR4), (0x3E, BR4),
             (0x3F, BR4), (0x40, BR4), (0x41, BR4), (0x42, BR4), (0x43, BR4), (0x44, BR4), (0x45, SWITCH),
             (0x6F, METH), (0x70, TYPE), (0x71, TYPE), (0x72, STR), (0x73, METH), (0x74, TYPE), (0x75, TYPE),
             (0x79, TYPE), (0x7B, FIELD), (0x7C, FIELD), (0x7D, FIELD), (0x7E, FIELD), (0x7F, FIELD),
             (0x80, FIELD), (0x81, TYPE), (0x8C, TYPE), (0x8D, TYPE), (0x8F, TYPE), (0xA3, TYPE),
             (0xA4, TYPE), (0xA5, TYPE), (0xC2, TYPE), (0xC6, TYPE), (0xD0, TOK), (0xDD, BR4), (0xDE, BR1)]:
    OP1[c] = k
OP2 = {c: NONE for c in range(0x00, 0x20)}
for c, k in [(0x06, METH), (0x07, METH), (0x09, VAR2), (0x0A, VAR2), (0x0B, VAR2), (0x0C, VAR2),
             (0x0D, VAR2), (0x0E, VAR2), (0x12, I1), (0x15, TYPE), (0x16, TYPE), (0x19, I1), (0x1C, TYPE)]:
    OP2[c] = k
NAME = {0x00: "nop", 0x02: "ldarg.0", 0x03: "ldarg.1", 0x04: "ldarg.2", 0x05: "ldarg.3",
        0x06: "ldloc.0", 0x07: "ldloc.1", 0x08: "ldloc.2", 0x09: "ldloc.3",
        0x0A: "stloc.0", 0x0B: "stloc.1", 0x0C: "stloc.2", 0x0D: "stloc.3", 0x14: "ldnull",
        0x15: "ldc.i4.m1", 0x16: "ldc.i4.0", 0x17: "ldc.i4.1", 0x18: "ldc.i4.2", 0x19: "ldc.i4.3",
        0x1A: "ldc.i4.4", 0x1B: "ldc.i4.5", 0x1C: "ldc.i4.6", 0x1D: "ldc.i4.7", 0x1E: "ldc.i4.8",
        0x25: "dup", 0x26: "pop", 0x28: "call", 0x2A: "ret", 0x6F: "callvirt", 0x72: "ldstr",
        0x73: "newobj", 0x7B: "ldfld", 0x7D: "stfld", 0x7E: "ldsfld", 0x80: "stsfld",
        0x2B: "br.s", 0x2C: "brfalse.s", 0x2D: "brtrue.s", 0x38: "br", 0x39: "brfalse", 0x3A: "brtrue",
        0x0E: "ldarg.s", 0x11: "ldloc.s", 0x13: "stloc.s", 0x1F: "ldc.i4.s", 0x20: "ldc.i4"}

pe = pefile.PE(DLL, fast_load=True)
RAW = bytes(pe.__data__)
dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
md = dn.net.mdtables
owner = {}
for t in md.TypeDef.rows:
    ns, nm = str(t.TypeNamespace or ""), str(t.TypeName or "")
    full = (ns + "." + nm) if ns else nm
    ml = t.MethodList
    if ml is None:
        continue
    if not isinstance(ml, list):
        ml = [ml]
    for x in ml:
        ri = getattr(x, "row_index", None)
        if ri:
            owner[ri] = full


def us_heap():
    cli = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]
    cli_off = pe.get_offset_from_rva(cli.VirtualAddress)
    meta_rva, _ = struct.unpack_from("<II", RAW, cli_off + 8)
    m = pe.get_offset_from_rva(meta_rva)
    _, _, _, _, vlen = struct.unpack_from("<IHHII", RAW, m)
    p = (m + 16 + vlen + 3) & ~3
    _, n = struct.unpack_from("<HH", RAW, p)
    p += 4
    h = {}
    for _ in range(n):
        off, size = struct.unpack_from("<II", RAW, p)
        p += 8
        e = RAW.index(b"\x00", p)
        h[RAW[p:e].decode()] = (m + off, size)
        p = (e + 4) & ~3
    o, s = h["#US"]
    d = RAW[o:o + s]

    def ci(b, i):
        x = b[i]
        if x & 0x80 == 0:
            return x, i + 1
        if x & 0xC0 == 0x80:
            return ((x & 0x3F) << 8) | b[i + 1], i + 2
        return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4
    S, i = {}, 1
    while i < len(d):
        st = i
        ln, i = ci(d, i)
        if ln == 0:
            continue
        bl = d[i:i + ln]
        i += ln
        b = bl[:-1] if bl.endswith(b"\x00") else bl
        if len(b) % 2:
            b = b[:-1]
        S[st] = b.decode("utf-16-le", errors="replace")
    return S


US = us_heap()
ARGS = [a for a in sys.argv[1:] if "::" in a]
CTX = int(os.environ.get("QCTX", "6"))

for a in ARGS:
    tn, mn = a.split("::")
    for mi, m in enumerate(md.MethodDef.rows, start=1):
        if str(m.Name) != mn or owner.get(mi) != tn:
            continue
        off = pe.get_offset_from_rva(m.Rva)
        hdr = RAW[off]
        code = (RAW[off + 1:off + 1 + (hdr >> 2)] if hdr & 3 == 2
                else RAW[off + 12:off + 12 + struct.unpack_from("<I", RAW, off + 4)[0]])
        ins, i, n = [], 0, len(code)
        while i < n:
            op = code[i]
            st = i
            i += 1
            if op == 0xFE:
                o2 = code[i]; i += 1
                kind = OP2.get(o2); nm = "fe%02x" % o2
            else:
                kind = OP1.get(op); nm = NAME.get(op, "op_%02x" % op)
            operand = None
            if kind == SWITCH:
                cnt = struct.unpack_from("<I", code, i)[0]; i += 4 + 4 * cnt
            elif kind != NONE:
                sz = SIZE[kind]
                operand = int.from_bytes(code[i:i + sz], "little", signed=(sz == 4))
                i += sz
            ins.append((st, nm, kind, operand))
        print(f"\n===== {tn}::{mn}  ({len(ins)} instructions) =====")
        for idx, (o, nm, kind, operand) in enumerate(ins):
            if kind == STR and operand is not None:
                s = US.get(operand & 0xFFFFFF, "<bad>")
                print(f"  >>> ldstr {s!r}  @IL_{o:04X}")
                lo = max(0, idx - CTX)
                for j in range(lo, min(len(ins), idx + CTX + 1)):
                    oo, nn, kk, opp = ins[j]
                    extra = ""
                    if kk == STR:
                        extra = " " + repr(US.get(opp & 0xFFFFFF, "<bad>"))
                    elif opp is not None and kk in (METH, FIELD, TYPE):
                        extra = f" tok=0x{opp:08X}"
                    elif opp is not None:
                        extra = f" {opp}"
                    mark = "  <<<" if j == idx else ""
                    print(f"        IL_{oo:04X}: {nn}{extra}{mark}")
pe.close()
