import sys, re, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\translations\punk.tsv"
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\translations\overlay\c-0249-0371.tsv"
LO, HI = 249, 371

# ---------- load source ----------
src = {}
with open(SRC, encoding="utf-8") as f:
    for ln in f.read().split("\n"):
        if not ln.strip():
            continue
        p = ln.split("\t")
        if len(p) < 2 or not p[0].strip().isdigit():
            continue
        src[p[0].strip()] = p[1]

# ---------- load overlay ----------
raw = open(OUT, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8")
crlf = "\r\n" in text
lines = text.split("\n")
if lines and lines[-1] == "":
    lines = lines[:-1]

rows = []
errs = collections.defaultdict(list)
for i, ln in enumerate(lines, 1):
    if ln.startswith("#"):
        continue
    if ln.strip() == "":
        errs["blank_line"].append(f"line {i}")
        continue
    cols = ln.split("\t")
    if len(cols) != 2:
        errs["col_count"].append(f"line {i}: {len(cols)} cols -> {ln!r}")
        continue
    rows.append((cols[0], cols[1]))

# ---------- check 1: two columns / number range / duplicates ----------
seen = collections.Counter(n for n, _ in rows)
for n, c in seen.items():
    if c > 1:
        errs["duplicate"].append(f"{n} x{c}")
    if not re.fullmatch(r"\d{4}", n):
        errs["bad_number_format"].append(n)
    elif not (LO <= int(n) <= HI):
        errs["out_of_range"].append(n)

expected = {f"{i:04d}" for i in range(LO, HI + 1)}
missing = sorted(expected - set(seen))
extra = sorted(set(seen) - expected)
if missing:
    errs["missing"].append(",".join(missing))
if extra:
    errs["extra"].append(",".join(extra))

# ---------- allowlist for residual latin ----------
RESOURCES = {"CAPS", "ELECTRON", "FUEL", "GEL", "TECH", "STAMINA", "HEALTH", "POWER"}
KEYS = {"TAB", "ALT", "SPACE", "WASD", "FIRE", "L", "SHIFT", "DPAD", "DOWN", "UP", "LEFT", "RIGHT",
        "ESC", "ENTER", "CTRL", "MOUSE", "I", "M", "E", "Q", "R", "T", "G", "B", "C", "F", "P1", "P2"}
BRANDS = {"Discord", "Steam"}
UNITS = {"GPU", "FPS", "ms", "GB", "MB"}
ALLOW = RESOURCES | KEYS | BRANDS | UNITS

TAG_RE = re.compile(r"<[^>]*>")
PH_RE = re.compile(r"\{[^}]*\}")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
FULLWIDTH = "，。！？：；、（）【】《》“”‘’…"

PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")
TAGNAME_RE = re.compile(r"<[^>]*>")

for n, t in rows:
    s = src.get(n, "")
    # 2: newline count
    if t.count("\\n") != s.count("\\n"):
        errs["newline_count"].append(f"{n}: src={s.count(chr(92)+'n')} out={t.count(chr(92)+'n')}")
    # 3: color tag counts
    if t.count("<color") != s.count("<color"):
        errs["color_open"].append(f"{n}: src={s.count('<color')} out={t.count('<color')}")
    if t.count("</color>") != s.count("</color>"):
        errs["color_close"].append(f"{n}: src={s.count('</color>')} out={t.count('</color>')}")
    # 3b: all tags preserved verbatim (multiset)
    if collections.Counter(TAGNAME_RE.findall(t)) != collections.Counter(TAGNAME_RE.findall(s)):
        errs["tag_mismatch"].append(f"{n}: src={TAGNAME_RE.findall(s)} out={TAGNAME_RE.findall(t)}")
    # 3c: placeholders preserved verbatim (multiset)
    if collections.Counter(PLACEHOLDER_RE.findall(t)) != collections.Counter(PLACEHOLDER_RE.findall(s)):
        errs["placeholder_mismatch"].append(f"{n}: src={PLACEHOLDER_RE.findall(s)} out={PLACEHOLDER_RE.findall(t)}")
    # 4: fullwidth punctuation
    fw = [c for c in t if c in FULLWIDTH]
    if fw:
        errs["fullwidth_punct"].append(f"{n}: {fw}")
    # 5: length
    if len(t) > len(s) * 1.2:
        errs["too_long"].append(f"{n}: src={len(s)} out={len(t)} ratio={len(t)/max(len(s),1):.2f} -> {t!r}")
    # 6: residual latin
    stripped = PH_RE.sub(" ", TAG_RE.sub(" ", t.replace("\\n", " ").replace("\\t", " ")))
    bad = [w for w in WORD_RE.findall(stripped) if w not in ALLOW]
    if bad:
        errs["residual_english"].append(f"{n}: {bad} -> {t!r}")

# ---------- report ----------
checks = [
    ("每行两列 (tab 分隔)", "col_count"),
    ("编号四位、区间 0249-0371 内、无重复", None),
    ("编号无缺失/无越界", None),
    ("\\n 条数与原文一致", "newline_count"),
    ("<color 开标签数一致", "color_open"),
    ("</color> 闭标签数一致", "color_close"),
    ("全部 <标签> 原样保留", "tag_mismatch"),
    ("全部 {占位符} 原样保留", "placeholder_mismatch"),
    ("无全角标点 (，。！？：；、)", "fullwidth_punct"),
    ("译文长度 <= 原文 x1.2", "too_long"),
    ("无残留英文单词 (白名单除外)", "residual_english"),
]

print(f"源文件: {SRC}")
print(f"产出:   {OUT}")
print(f"行数(非注释): {len(rows)}   BOM: {bom}   CRLF: {crlf}")
print()
print("=== 自检结果 ===")
ok_all = True
for label, key in checks:
    if key is None:
        bad = (errs["duplicate"] + errs["bad_number_format"] + errs["out_of_range"]
               + errs["missing"] + errs["extra"] + errs["blank_line"])
    else:
        bad = errs[key]
    status = "PASS" if not bad else "FAIL"
    if bad:
        ok_all = False
    print(f"[{status}] {label}" + (f"  ({len(bad)} 条)" if bad else ""))
    for b in bad[:20]:
        print("        -", b)

print()
print("总体:", "全部通过" if ok_all else "存在不通过项")

# length stats
worst = max(rows, key=lambda r: len(r[1]) / max(len(src.get(r[0], "")), 1))
print(f"最长比率条目: {worst[0]}  {len(worst[1])}/{len(src.get(worst[0],''))} = {len(worst[1])/max(len(src.get(worst[0],'')),1):.2f}")
