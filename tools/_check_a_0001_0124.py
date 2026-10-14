# -*- coding: utf-8 -*-
"""Self-check for translations/overlay/a-0001-0124.tsv against translations/punk.tsv."""
import sys, io, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
SRC = os.path.join(ROOT, "translations", "punk.tsv")
OUT = os.path.join(ROOT, "translations", "overlay", "a-0001-0124.tsv")
LO, HI = 1, 124

RESOURCE_OK = {"CAPS", "ELECTRON", "FUEL", "GEL", "TECH", "STAMINA", "HEALTH", "POWER"}
KEY_OK = {"TAB", "ALT", "SPACE", "WASD", "FIRE", "L", "R", "SHIFT", "DPAD", "DOWN", "UP",
          "LEFT", "RIGHT", "CTRL", "ENTER", "ESC", "MOUSE", "E", "Q", "W", "A", "S", "D",
          "DISCORD", "STEAM"}
FULLWIDTH = "，。！？：；、（）“”‘’《》【】…—"

def load_src():
    d = {}
    with io.open(SRC, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if not line or line.startswith("#"):
                continue
            p = line.split("\t")
            while len(p) < 3:
                p.append("")
            d[p[0]] = (p[1], p[2])
    return d

raw = io.open(OUT, "rb").read()
fails = []
def check(name, ok, detail=""):
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else "  -> " + detail))
    if not ok:
        fails.append(name + " :: " + detail)

print("=== 自检 a-0001-0124.tsv ===")

# 0. encoding / newline hygiene
check("UTF-8 无 BOM", not raw.startswith(b"\xef\xbb\xbf"))
check("换行为 LF(无 CR)", b"\r" not in raw)
try:
    text = raw.decode("utf-8")
    check("可解码为 UTF-8", True)
except Exception as e:
    check("可解码为 UTF-8", False, str(e))
    raise SystemExit(1)

src = load_src()
lines = text.split("\n")
if lines and lines[-1] == "":
    lines = lines[:-1]

# 1. two columns, no stray tabs
bad_cols, entries = [], []
for i, ln in enumerate(lines, 1):
    if ln.startswith("#"):
        continue
    p = ln.split("\t")
    if len(p) != 2:
        bad_cols.append("line %d: %d cols" % (i, len(p)))
        continue
    entries.append((p[0], p[1]))
check("每行两列(制表符分隔)", not bad_cols, "; ".join(bad_cols[:5]))

# 2. numbering
nums = [n for n, _ in entries]
in_range = [n for n in nums if n.isdigit() and LO <= int(n) <= HI]
check("编号均为四位数且在 0001-0124 内",
      len(in_range) == len(nums) and all(re.fullmatch(r"\d{4}", n) for n in nums),
      "bad=" + str([n for n in nums if not re.fullmatch(r"\d{4}", n)])[:120])
dups = sorted({n for n in nums if nums.count(n) > 1})
check("编号无重复", not dups, "dups=" + str(dups))

# expected set = numbers in range that had no Chinese in punk.tsv
expected = [n for n, (en, zh) in sorted(src.items()) if n.isdigit() and LO <= int(n) <= HI and not zh.strip()]
check("覆盖了全部待译编号(%d 条)" % len(expected), sorted(nums) == sorted(expected),
      "missing=" + str(sorted(set(expected) - set(nums))) + " extra=" + str(sorted(set(nums) - set(expected))))

# 3-7 per entry
n_nl, n_tag, n_fw, n_len, n_en, missing_src = [], [], [], [], [], []
for num, zh in entries:
    if num not in src:
        missing_src.append(num)
        continue
    en = src[num][0]

    if zh.count("\\n") != en.count("\\n"):
        n_nl.append("%s en=%d zh=%d" % (num, en.count("\\n"), zh.count("\\n")))

    if zh.count("<color") != en.count("<color") or zh.count("</color>") != en.count("</color>"):
        n_tag.append("%s en=<%d/%d> zh=<%d/%d>" % (num, en.count("<color"), en.count("</color>"),
                                                   zh.count("<color"), zh.count("</color>")))

    fw = [c for c in zh if c in FULLWIDTH]
    if fw:
        n_fw.append("%s %s" % (num, "".join(sorted(set(fw)))))

    if len(zh) > len(en) * 1.2:
        n_len.append("%s %d > %.1f (%d*1.2)" % (num, len(zh), len(en) * 1.2, len(en)))

    stripped = re.sub(r"<[^>]*>", "", zh)
    stripped = stripped.replace("\\n", " ").replace("\\t", " ")
    for w in re.findall(r"[A-Za-z]{2,}", stripped):
        if w.upper() not in RESOURCE_OK and w.upper() not in KEY_OK:
            n_en.append("%s:%s" % (num, w))

check("译文 \\n 条数与原文一致", not n_nl, "; ".join(n_nl))
check("译文 <color/</color> 标签数与原文一致", not n_tag, "; ".join(n_tag))
check("译文无全角标点", not n_fw, "; ".join(n_fw))
check("译文长度 <= 原文 x1.2", not n_len, "; ".join(n_len))
check("译文无未授权英文单词", not n_en, "; ".join(sorted(set(n_en))))
check("编号均能在原文表查到", not missing_src, str(missing_src))

print("---")
print("条目数: %d" % len(entries))
if fails:
    print("结果: 不通过 (%d 项)" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("结果: 全部通过")
