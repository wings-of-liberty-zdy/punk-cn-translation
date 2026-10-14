#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把完整的 Fusion Pixel 字体裁成只含必要字形的子集，产出插件内嵌用的 pixel-cn.ttf。

为什么要裁：完整字体 6.7 MB，内嵌会让补丁包大到 5 MB 级。
只保留用得到的字形后约几十 KB，下载快一个数量级。

授权：Fusion Pixel 是 SIL OFL 1.1，且其版权声明里**没有 Reserved Font Name 条款**，
所以 OFL 允许修改与再分发；只要保留版权声明与许可证全文即可（本脚本会保留 name 表）。

保留的字形集合：
  1. translations/punk.tsv 全部译文里用到的字符
  2. ASCII 可打印区（含空格）—— 游戏会拼数字、种子、版本号
  3. 常用中英标点与全角标点
  4. **GB2312 一级汉字（3755 个）** —— 兜底：运行时动态拼出来的中文不会变方块

用法：
    python tools/prepare_font.py
    python tools/prepare_font.py --src vendor/fonts/fusion12-vector/fusion-pixel-12px-proportional-zh_hans.ttf
"""

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(ROOT, "vendor", "fonts", "fusion12-vector",
                           "fusion-pixel-12px-proportional-zh_hans.ttf")
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
OUT = os.path.join(ROOT, "plugin", "PunkCn", "Resources", "pixel-cn.ttf")

PUNCT = (
    " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    "\u3000\u3001\u3002\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011"
    "\uff01\uff02\uff05\uff08\uff09\uff0c\uff0e\uff1a\uff1b\uff1f\uff0d"
    "\u2018\u2019\u201c\u201d\u2014\u2026\u00b7\u2190\u2191\u2192\u2193"
    "\u00d7\u00f7\u00b0\u00b1\u2264\u2265\u00a5\u20ac"
)


def from_cell(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in "nt\\":
            out.append({"n": "\n", "t": "\t", "\\": "\\"}[s[i + 1]])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def table_chars():
    cs = set()
    for line in open(TABLE, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 3:
            continue
        cs |= set(from_cell(f[2]))
        cs |= set(from_cell(f[1]))      # 原文里的英文也要留着（未翻译项、HUD 缩写）
    # 去掉控制字符：译文里的 \n \t 是排版控制，不是要渲染的字形
    return {c for c in cs if ord(c) >= 0x20}


def gb2312_level1():
    """GB2312 一级汉字：区位 16-55，每区 94 个字，共 3755 个。"""
    cs = set()
    for q in range(16, 56):
        for w in range(1, 95):
            try:
                cs.add(bytes([q + 0xA0, w + 0xA0]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return cs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--no-gb2312", action="store_true", help="不带 GB2312 兜底字（包更小）")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print("× 找不到源字体：%s" % args.src)
        print("  见 README「从源码构建」第 3 步")
        return 1

    from fontTools import subset
    from fontTools.ttLib import TTFont

    need = table_chars() | set(PUNCT) | set(chr(c) for c in range(0x20, 0x7F))
    gb = set() if args.no_gb2312 else gb2312_level1()
    want = need | gb
    print("保留字形：译文与原文 %d 个 + 标点 %d 个 + ASCII 95 个 + GB2312 一级 %d 个 = %d 个（去重后）"
          % (len(table_chars()), len(PUNCT), len(gb), len(want)))

    src_mb = os.path.getsize(args.src) / 1024 / 1024
    text = "".join(sorted(want))

    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]          # 保留 name 表 —— OFL 要求留版权声明与许可证
    opts.name_legacy = True
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.drop_tables = ["EBDT", "EBLC", "CBDT", "CBLC"]   # 丢掉点阵strikes，只留矢量轮廓

    font = subset.load_font(args.src, opts)
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(text=text)
    subsetter.subset(font)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    subset.save_font(font, args.out, opts)
    font.close()

    out_kb = os.path.getsize(args.out) / 1024
    print("已写出 %s" % os.path.relpath(args.out, ROOT))
    print("  %.2f MB -> %.0f KB（缩小 %.0f 倍）" % (src_mb, out_kb, src_mb * 1024 / out_kb))

    # 自检：译文里的字一个都不能少，且必须有矢量轮廓
    f = TTFont(args.out, lazy=True)
    cm = set()
    for t in f["cmap"].tables:
        cm |= set(t.cmap.keys())
    miss = sorted(c for c in table_chars() if ord(c) not in cm)
    print("  自检：译文用字缺 %d 个 %s" % (len(miss), "".join(miss[:40]) if miss else "✓"))

    from fontTools.pens.boundsPen import BoundsPen
    gs = f.getGlyphSet()
    gcm = f.getBestCmap()
    got = 0
    for ch in "返回设置武器追踪导弹":
        gn = gcm.get(ord(ch))
        if not gn:
            continue
        bp = BoundsPen(gs)
        gs[gn].draw(bp)
        if bp.bounds:
            got += 1
    print("  自检：抽样 %d 个字有矢量轮廓（不是点阵）" % got)

    names = {}
    for rec in f["name"].names:
        if rec.nameID in (0, 13, 14):
            try:
                names.setdefault(rec.nameID, rec.toUnicode())
            except Exception:
                pass
    print("  版权 %s" % names.get(0, "?")[:70])
    print("  授权 %s" % names.get(13, "?")[:70])
    f.close()
    return 0 if not miss and got else 1


if __name__ == "__main__":
    sys.exit(main())
