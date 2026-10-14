import sys, io, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\translations\punk.tsv"
LO, HI = 1, 124

rows = []
with io.open(SRC, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n").rstrip("\r")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        while len(parts) < 3:
            parts.append("")
        num, en, zh = parts[0], parts[1], parts[2]
        rows.append((num, en, zh))

sel = [r for r in rows if r[0].isdigit() and LO <= int(r[0]) <= HI]
print("total rows in file:", len(rows))
print("selected:", len(sel))
done = [r for r in sel if r[2].strip()]
todo = [r for r in sel if not r[2].strip()]
print("already translated (skip):", len(done), [r[0] for r in done])
print("to translate:", len(todo))
print("---")
for num, en, zh in todo:
    print("%s\t%d\t%s" % (num, len(en), en))
