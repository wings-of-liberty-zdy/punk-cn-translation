import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import dnfile, pefile

DLL = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data\Managed\Punk.Main.dll"
dn = dnfile.dnPE(DLL, fast_load=True)
dn.parse_data_directories()
md = dn.net.mdtables
print("tables:", [t for t in dir(md) if not t.startswith("_")][:60])
print()
td = md.TypeDef
print("TypeDef rows:", td.num_rows if hasattr(td, "num_rows") else len(td.rows))
r = td.rows[0]
print("TypeDefRow attrs:", [a for a in dir(r) if not a.startswith("_")])
print("  row0:", r.TypeNamespace, r.TypeName, "MethodList=", r.MethodList, "FieldList=", r.FieldList)
print()
mdef = md.MethodDef
print("MethodDef rows:", mdef.num_rows)
mr = mdef.rows[0]
print("MethodDefRow attrs:", [a for a in dir(mr) if not a.startswith("_")])
print("  row0:", mr.Name, "Rva=", hex(mr.Rva), "Flags=", mr.Flags)
print()
mref = md.MemberRef
print("MemberRef rows:", mref.num_rows)
mrr = mref.rows[0]
print("MemberRefRow attrs:", [a for a in dir(mrr) if not a.startswith("_")])
print("  row0:", mrr.Name, "Class=", mrr.Class)
try:
    print("  Class.table:", mrr.Class.table.name, "row_index", mrr.Class.row_index)
except Exception as e:
    print("  class resolve err", e)
print()
print("AssemblyRef rows:", md.AssemblyRef.num_rows)
for a in md.AssemblyRef.rows[:400]:
    n = str(a.Name)
    if any(k in n for k in ("Http", "Web", "Net", "Json", "Unity")):
        print("   ", n, a.MajorVersion, a.MinorVersion)
