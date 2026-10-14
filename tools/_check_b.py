import sys, io, os, re, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
SRC = os.path.join(ROOT, "translations", "punk.tsv")
OUT = os.path.join(ROOT, "translations", "overlay", "b-0125-0248.tsv")
LO, HI = 125, 248

# ---------- load source ----------
src = {}
order = []
with io.open(SRC, "r", encoding="utf-8", newline="") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) < 2 or not p[0].isdigit():
            continue
        src[p[0]] = p[1]

# ---------- load overlay ----------
raw = open(OUT, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
crlf = b"\r" in raw
rows = []
bad_cols = []
with io.open(OUT, "r", encoding="utf-8", newline="") as f:
    for i, line in enumerate(f, 1):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) != 2:
            bad_cols.append((i, len(p), line[:60]))
            continue
        rows.append((p[0], p[1], i))

res = {}
res["BOM 不存在"] = (not bom)
res["换行全为 LF"] = (not crlf)
res["每行两列"] = (len(bad_cols) == 0)

nums = [r[0] for r in rows]
inrange = all(n.isdigit() and LO <= int(n) <= HI for n in nums)
dup = sorted({n for n in nums if nums.count(n) > 1})
res["编号在区间内"] = inrange
res["编号无重复"] = (len(dup) == 0)
res["覆盖全部编号 0125-0248"] = (sorted(nums) == ["%04d" % n for n in range(LO, HI + 1)])

nl_bad, tag_bad, punct_bad, len_bad, eng_bad, missing = [], [], [], [], [], []
FULLWIDTH = "，。！？：；、"
ALLOWED_ENG = {
    "CAPS", "ELECTRON", "FUEL", "GEL", "TECH", "STAMINA", "HEALTH", "POWER",
    "TAB", "ALT", "SPACE", "WASD", "FIRE", "L", "SHIFT", "DPAD", "DOWN",
    "FPS", "PUNK", "discord", "DISCORD", "Steam", "Steam",
}
TAG_RE = re.compile(r"<[^>]*>")

for num, zh, ln in rows:
    if num not in src:
        missing.append(num)
        continue
    en = src[num]
    if zh.count("\\n") != en.count("\\n"):
        nl_bad.append((num, en.count("\\n"), zh.count("\\n")))
    if zh.count("<color") != en.count("<color") or zh.count("</color>") != en.count("</color>"):
        tag_bad.append((num, en.count("<color"), zh.count("<color"),
                        en.count("</color>"), zh.count("</color>")))
    # balanced tag stack
    opens = re.findall(r"<(?!/)([a-zA-Z]+)[^>]*>", zh)
    closes = re.findall(r"</([a-zA-Z]+)>", zh)
    if sorted(opens) != sorted(closes):
        tag_bad.append((num, "UNBALANCED", opens, closes))
    for ch in FULLWIDTH:
        if ch in zh:
            punct_bad.append((num, ch))
    if len(zh) > len(en) * 1.2 + 1e-9:
        len_bad.append((num, len(en), len(zh), round(len(zh) / len(en), 3)))
    stripped = TAG_RE.sub(" ", zh)
    words = re.findall(r"[A-Za-z]{2,}", stripped)
    leftover = sorted({w for w in words if w not in ALLOWED_ENG})
    if leftover:
        eng_bad.append((num, leftover))

res["\\n 条数与原文一致"] = (len(nl_bad) == 0)
res["<color> 标签配对且数量一致"] = (len(tag_bad) == 0)
res["无全角标点"] = (len(punct_bad) == 0)
res["长度 <= 原文 x1.2"] = (len(len_bad) == 0)
res["无残留英文单词"] = (len(eng_bad) == 0)
res["编号都能在原文表找到"] = (len(missing) == 0)

print("=" * 60)
print("自检报告  b-0125-0248.tsv   (%d 条)" % len(rows))
print("=" * 60)
for k, v in res.items():
    print(("  [通过] " if v else "  [不通过] ") + k)
print("-" * 60)
print("多列行:", bad_cols)
print("重复编号:", dup)
print("\\n 不符:", nl_bad)
print("标签不符:", tag_bad)
print("全角标点:", punct_bad)
print("超长:", len_bad)
print("残留英文:", eng_bad)
print("缺失:", missing)
print("-" * 60)

# length headroom report (top 6 tightest)
tight = sorted(((len(src[n]) * 1.2 - len(z), n, len(src[n]), len(z)) for n, z, _ in rows))[:6]
print("最紧的 6 条 (余量, 编号, 原长, 译长):")
for h, n, a, b in tight:
    print("   %s  余量 %.1f  (%d -> %d)  %s" % (n, h, a, b, src[n][:40]))

print("-" * 60)
print("示例前 3 行原始字节:", raw[:80])
print("总判定:", "全部通过" if all(res.values()) else "有项目不通过")
