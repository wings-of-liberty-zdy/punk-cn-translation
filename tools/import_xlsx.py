#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把改好的 Excel 导回流水线。

它做三件事：
  1. 逐行比对「译文」列与当前翻译表，列出改动
  2. 做安全校验（\n 变多、富文本标签丢失、占位符丢失、全角标点、缺字），有致命问题就拒绝写入
  3. 把改动写成 translations/overlay/manual-edits.tsv（两列：编号 / 译文）

写完之后运行 python tools/build_table.py --sync-plugin 才真正生效。

用法：
    python tools/import_xlsx.py --dry-run     # 只看会改什么，不写文件
    python tools/import_xlsx.py
    python tools/import_xlsx.py --xlsx translations/punk-zh-CN.xlsx --out translations/overlay/manual-edits.tsv
"""

import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(ROOT, "translations", "punk-zh-CN.xlsx")
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
OUT = os.path.join(ROOT, "translations", "overlay", "manual-edits.tsv")
FONT = os.path.join(ROOT, "plugin", "PunkCn", "Resources", "pixel-cn.ttf")

FULLWIDTH = "，。！？：；、（）【】《》“”‘’"


def load_table():
    rows = {}
    order = []
    for line in open(TABLE, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) >= 3:
            rows[f[0]] = {"en": f[1], "cn": f[2]}
            order.append(f[0])
    return rows, order


def load_cmap():
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    if not os.path.exists(FONT):
        return None
    f = TTFont(FONT, lazy=True)
    cm = set()
    for t in f["cmap"].tables:
        cm |= set(t.cmap.keys())
    return cm


def count(s, pat):
    return len(re.findall(pat, s))


def check(rid, en, cn, cmap):
    """返回 (致命问题列表, 提醒列表)"""
    fatal, warn = [], []

    if not cn.strip():
        fatal.append("译文为空")

    if cn.count("\\n") > en.count("\\n"):
        fatal.append("换行变多了：原文 %d 个 \\n，译文 %d 个（多出的换行可能撑破固定高度的框）"
                     % (en.count("\\n"), cn.count("\\n")))
    elif cn.count("\\n") < en.count("\\n"):
        warn.append("换行比原文少 %d 个（通常没问题，中文更短）" % (en.count("\\n") - cn.count("\\n")))

    for tag in ("color", "size"):
        if count(en, r"<%s\b" % tag) != count(cn, r"<%s\b" % tag) or \
           count(en, r"</%s\s*>" % tag) != count(cn, r"</%s\s*>" % tag):
            fatal.append("<%s> 标签数量对不上：原文 %d 开 %d 闭，译文 %d 开 %d 闭"
                         % (tag, count(en, r"<%s\b" % tag), count(en, r"</%s\s*>" % tag),
                            count(cn, r"<%s\b" % tag), count(cn, r"</%s\s*>" % tag)))
    if count(en, r"<sprite\b") != count(cn, r"<sprite\b"):
        fatal.append("<sprite> 数量对不上")

    ph_en = sorted(re.findall(r"\{[^}]*\}", en))
    ph_cn = sorted(re.findall(r"\{[^}]*\}", cn))
    if ph_en != ph_cn:
        fatal.append("占位符对不上：原文 %s，译文 %s" % (ph_en, ph_cn))

    fw = sorted({c for c in cn if c in FULLWIDTH})
    if fw:
        warn.append("出现全角标点：%s（本项目定的是沿用原文半角）" % "".join(fw))

    if cmap is not None:
        miss = sorted({c for c in cn if ord(c) > 0x2E7F and ord(c) not in cmap})
        if miss:
            fatal.append("字体里没有这些字，会显示成方块：%s" % "".join(miss))

    return fatal, warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=XLSX)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.xlsx):
        print("× 找不到 %s" % args.xlsx)
        print("  先运行 python tools\\export_xlsx.py")
        return 1

    from openpyxl import load_workbook

    wb = load_workbook(args.xlsx, data_only=True)
    if "翻译表" not in wb.sheetnames:
        print("× Excel 里没有「翻译表」这个工作表，是不是改错文件了？")
        return 1
    ws = wb["翻译表"]

    head = [c.value for c in ws[1]]
    try:
        i_id = head.index("编号")
        i_cn = head.index("译文（中文）")
    except ValueError:
        print("× 表头找不到「编号」或「译文（中文）」，不要改动第一行")
        print("  当前表头：%s" % head)
        return 1

    old, order = load_table()
    cmap = load_cmap()

    changes, fatals, warns, unknown = [], [], [], []
    seen = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None or i_id >= len(row) or row[i_id] is None:
            continue
        rid = str(row[i_id]).strip()
        cn = row[i_cn] if i_cn < len(row) and row[i_cn] is not None else ""
        cn = str(cn)
        seen.add(rid)

        if rid not in old:
            unknown.append(rid)
            continue
        if cn == old[rid]["cn"]:
            continue

        f, w = check(rid, old[rid]["en"], cn, cmap)
        entry = {"id": rid, "old": old[rid]["cn"], "new": cn, "en": old[rid]["en"]}
        if f:
            entry["fatal"] = f
            fatals.append(entry)
        else:
            changes.append(entry)
        if w:
            entry["warn"] = w
            warns.append(entry)

    missing = [i for i in order if i not in seen]

    print("对比 %s" % os.path.relpath(args.xlsx, ROOT))
    print("  表内 %d 行，当前翻译表 %d 行" % (len(seen), len(order)))
    print("  改动 %d 条，其中 %d 条有致命问题、%d 条只是提醒"
          % (len(changes) + len(fatals), len(fatals), len(warns)))
    if missing:
        print("  ⚠ Excel 里缺 %d 行（%s）—— 是删行了吗？这些行会保留原译文" % (len(missing), ", ".join(missing[:8])))
    if unknown:
        print("  ⚠ Excel 里有 %d 个编号不在翻译表里：%s" % (len(unknown), ", ".join(unknown[:8])))

    if fatals:
        print()
        print("── 有致命问题、不会写入的改动（%d 条）──" % len(fatals))
        for e in fatals[:20]:
            print("  %s  %s" % (e["id"], e["en"][:44].replace("\n", "\\n")))
            print("      改成: %s" % e["new"][:60].replace("\n", "\\n"))
            for m in e["fatal"]:
                print("      × %s" % m)
        if len(fatals) > 20:
            print("  … 还有 %d 条" % (len(fatals) - 20))

    if warns:
        print()
        print("── 提醒（会写入，但建议看一眼）──")
        for e in warns[:10]:
            print("  %s  %s" % (e["id"], "；".join(e["warn"])))

    if changes:
        print()
        print("── 将写入的改动（前 10 条）──")
        for e in changes[:10]:
            print("  %s" % e["id"])
            print("      原: %s" % e["old"][:56].replace("\n", "\\n"))
            print("      新: %s" % e["new"][:56].replace("\n", "\\n"))
        if len(changes) > 10:
            print("  … 还有 %d 条" % (len(changes) - 10))

    if not changes:
        print()
        print("没有需要写入的改动。")
        return 0

    if args.dry_run:
        print()
        print("（--dry-run，没有写文件）")
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 由 tools/import_xlsx.py 从 %s 导出\n" % os.path.basename(args.xlsx))
        f.write("# 两列 TSV：编号 / 译文。这一层排在其他 overlay 之后，优先级最高。\n")
        f.write("# 重新跑 build_table.py 会覆盖本文件，直接改 Excel 再导一次即可。\n")
        for e in changes:
            f.write("%s\t%s\n" % (e["id"], e["new"]))

    print()
    print("已写出 %s（%d 条）" % (os.path.relpath(args.out, ROOT), len(changes)))
    print("接着运行：python tools\\build_table.py --sync-plugin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
