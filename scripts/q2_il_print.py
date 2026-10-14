import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, struct
import dnfile, pefile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

NONE, I1, I4, I8, R4, R8, METH, FIELD, TYPE, STR, SIG, TOK, SWITCH, VAR1, VAR2, BR1, BR4 = range(17)
SIZE = {NONE: 0, I1: 1, I4: 4, I8: 8, R4: 4, R8: 8, METH: 4, FIELD: 4, TYPE: 4,
        STR: 4, SIG: 4, TOK: 4, VAR1: 1, VAR2: 2, BR1: 1, BR4: 4}
OP1 = {c: NONE for c in range(0x00, 0xFF)}
for c, k in [(0x0E, VAR1), (0x0F, VAR1), (0x10, VAR1), (0x11, VAR1), (0x12, VAR1), (0x13, VAR1),
             (0x1F, I1), (0x20, I4), (0x21, I8), (0x22, R4), (0x23, R8),
             (0x27, METH), (0x28, METH), (0x29, SIG),
             (0x2B, BR1), (0x2C, BR1), (0x2D, BR1), (0x2E, BR1), (0x2F, BR1), (0x30, BR1), (0x31, BR1),
             (0x32, BR1), (0x33, BR1), (0x34, BR1), (0x35, BR1), (0x36, BR1), (0x37, BR1),
             (0x38, BR4), (0x39, BR4), (0x3A, BR4), (0x3B, BR4), (0x3C, BR4), (0x3D, BR4), (0x3E, BR4),
             (0x3F, BR4), (0x40, BR4), (0x41, BR4), (0x42, BR4), (0x43, BR4), (0x44, BR4), (0x45, SWITCH),
             (0x6F, METH), (0x70, TYPE), (0x71, TYPE), (0x72, STR), (0x73, METH), (0x74, TYPE), (0x75, TYPE),
             (0x79, TYPE), (0x7B, FIELD), (0x7C, FIELD), (0x7D, FIELD), (0x7E, FIELD), (0x7F, FIELD),
             (0x80, FIELD), (0x81, TYPE), (0x8C, TYPE), (0x8D, TYPE), (0x8F, TYPE),
             (0xA3, TYPE), (0xA4, TYPE), (0xA5, TYPE), (0xC2, TYPE), (0xC6, TYPE), (0xD0, TOK),
             (0xDD, BR4), (0xDE, BR1)]:
    OP1[c] = k
OP2 = {c: NONE for c in range(0x00, 0x20)}
for c, k in [(0x06, METH), (0x07, METH), (0x09, VAR2), (0x0A, VAR2), (0x0B, VAR2), (0x0C, VAR2),
             (0x0D, VAR2), (0x0E, VAR2), (0x12, I1), (0x15, TYPE), (0x16, TYPE), (0x19, I1), (0x1C, TYPE)]:
    OP2[c] = k

NAME1 = {0x00: "nop", 0x02: "ldarg.0", 0x03: "ldarg.1", 0x04: "ldarg.2", 0x05: "ldarg.3",
         0x06: "ldloc.0", 0x07: "ldloc.1", 0x08: "ldloc.2", 0x09: "ldloc.3",
         0x0A: "stloc.0", 0x0B: "stloc.1", 0x0C: "stloc.2", 0x0D: "stloc.3",
         0x14: "ldnull", 0x15: "ldc.i4.m1", 0x16: "ldc.i4.0", 0x17: "ldc.i4.1", 0x18: "ldc.i4.2",
         0x19: "ldc.i4.3", 0x1A: "ldc.i4.4", 0x1B: "ldc.i4.5", 0x1C: "ldc.i4.6", 0x1D: "ldc.i4.7",
         0x1E: "ldc.i4.8", 0x25: "dup", 0x26: "pop", 0x28: "call", 0x2A: "ret", 0x6F: "callvirt",
         0x72: "ldstr", 0x73: "newobj", 0x74: "castclass", 0x75: "isinst", 0x7B: "ldfld", 0x7E: "ldsfld",
         0x80: "stsfld", 0x7D: "stfld", 0x2B: "br.s", 0x2C: "brfalse.s", 0x2D: "brtrue.s", 0x38: "br",
         0x39: "brfalse", 0x3A: "brtrue", 0x6F: "callvirt", 0x0E: "ldarg.s", 0x11: "ldloc.s", 0x13: "stloc.s",
         0x1F: "ldc.i4.s", 0x20: "ldc.i4", 0x2E: "beq.s", 0x33: "bne.un.s", 0x3B: "beq", 0x40: "bne.un"}

pe = pefile.PE(DLL, fast_load=True)
RAW = bytes(pe.__data__)
dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
md = dn.net.mdtables

method_owner = {}
for ti, t in enumerate(md.TypeDef.rows, start=1):
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
            method_owner[ri] = full


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
        heaps[RAW[p:end].decode("ascii")] = (m + off, size)
        p = (end + 4) & ~3
    us_off, us_size = heaps["#US"]
    data = RAW[us_off:us_off + us_size]

    def cint(bb, i):
        x = bb[i]
        if x & 0x80 == 0:
            return x, i + 1
        if x & 0xC0 == 0x80:
            return ((x & 0x3F) << 8) | bb[i + 1], i + 2
        return ((x & 0x1F) << 24) | (bb[i + 1] << 16) | (bb[i + 2] << 8) | bb[i + 3], i + 4
    strings, i = {}, 1
    while i < len(data):
        start = i
        ln, i = cint(data, i)
        if ln == 0:
            continue
        blob = data[i:i + ln]
        i += ln
        b = blob[:-1] if blob.endswith(b"\x00") else blob
        if len(b) % 2:
            b = b[:-1]
        strings[start] = b.decode("utf-16-le", errors="replace")
    return strings


us = read_us_heap()


def resolve(tok, kind):
    t, idx = tok >> 24, tok & 0xFFFFFF
    try:
        if kind == "str":
            return repr(us.get(idx, "<bad>"))
        if t == 0x06:
            return f"{method_owner.get(idx,'?')}::{md.MethodDef.rows[idx-1].Name}"
        if t == 0x0A:
            r = md.MemberRef.rows[idx - 1]
            o = None
            ci = r.Class
            if ci.table is not None:
                if ci.table.name in ("TypeRef", "TypeDef"):
                    tb = md.TypeRef if ci.table.name == "TypeRef" else md.TypeDef
                    rr = tb.rows[ci.row_index - 1]
                    ns, nm = str(rr.TypeNamespace or ""), str(rr.TypeName or "")
                    o = (ns + "." + nm) if ns else nm
                else:
                    o = "<TypeSpec:%d>" % ci.row_index
            return f"{o}::{r.Name}"
        if t == 0x04:
            return "field " + str(md.Field.rows[idx - 1].Name)
        if t == 0x01:
            rr = md.TypeRef.rows[idx - 1]
            ns, nm = str(rr.TypeNamespace or ""), str(rr.TypeName or "")
            return (ns + "." + nm) if ns else nm
        if t == 0x02:
            rr = md.TypeDef.rows[idx - 1]
            ns, nm = str(rr.TypeNamespace or ""), str(rr.TypeName or "")
            return (ns + "." + nm) if ns else nm
        if t == 0x1B:
            return "<TypeSpec:%d>" % idx
        if t == 0x2B:
            return "MethodSpec:%d" % idx
    except Exception as e:
        return f"<err {e!r}>"
    return "tok:0x%08X" % tok


def il_of(mi):
    m = md.MethodDef.rows[mi - 1]
    off = pe.get_offset_from_rva(m.Rva)
    hdr = RAW[off]
    if hdr & 3 == 2:
        code = RAW[off + 1:off + 1 + (hdr >> 2)]
    else:
        code = RAW[off + 12:off + 12 + struct.unpack_from("<I", RAW, off + 4)[0]]
    out, i, n = [], 0, len(code)
    while i < n:
        op = code[i]
        start = i
        i += 1
        if op == 0xFE:
            op2 = code[i]; i += 1
            kind = OP2.get(op2); key = 0xFE00 | op2
            nm = "fe%02x" % op2
        else:
            kind = OP1.get(op); key = op
            nm = NAME1.get(op, "op_%02x" % op)
        operand = None
        if kind == SWITCH:
            cnt = struct.unpack_from("<I", code, i)[0]; i += 4 + 4 * cnt
        elif kind != NONE:
            sz = SIZE[kind]
            operand = int.from_bytes(code[i:i + sz], "little", signed=(sz == 4))
            i += sz
        out.append((start, nm, kind, operand))
    return out


def dump(type_name, method_name, maxlines=90):
    hits = []
    for mi, m in enumerate(md.MethodDef.rows, start=1):
        if str(m.Name) == method_name and method_owner.get(mi) == type_name:
            hits.append(mi)
    print(f"\n{'='*72}\n{type_name}::{method_name}   ({len(hits)} overload(s))")
    for mi in hits:
        print(f"--- method row {mi} ---")
        for (o, nm, kind, operand) in il_of(mi)[:maxlines]:
            extra = ""
            if kind == STR:
                extra = " " + resolve(operand, "str")
            elif kind == METH:
                extra = " " + resolve(operand, "meth")
            elif kind == FIELD:
                extra = " " + resolve(operand, "field")
            elif kind == TYPE:
                extra = " " + resolve(operand, "type")
            elif operand is not None:
                extra = f" {operand}"
            print(f"  IL_{o:04X}: {nm}{extra}")


TARGETS = [
    ("ModuleData", "get_Equippable"),
    ("Module", "get_DisplayName"),
    ("Module", "get_Data"),
    ("LoadoutModuleItem", "Display"),
    ("ShopItemWidget", "Setup"),
    ("ModuleIconWidget", "DisplayModuleData"),
    ("SpawnModulePickupButton", "set_Module"),
    ("DebugMenu", "SpawnModulePickup"),
]
for tn, mn in TARGETS:
    dump(tn, mn)

print(f"\n{'='*72}\nShopItemsConfig::Parse  (does it take a URL? what does it do?)")
dump("ShopItemsConfig", "Parse", 60)
dump("ShopItemsConfig", "ParseCurrencyOrder", 30)

pe.close()
