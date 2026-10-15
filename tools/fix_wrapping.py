#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修正换行排版：把中文本来放得下一行、却因为照搬原文换行而占两行的地方合并掉。

背景（用户报告）：
    加载页教学里 `DASH\\n/ HOLD TO BOOST` 译成 `冲刺\\n/ 长按加速`，照搬了原文换行。
    但中文短，本来一行放得下 —— 结果这一行比上下相邻的行高一倍，视觉节奏被打断。

规则（区分两类，因为它们的约束完全不同）：
  · **描述类**（物品/模块的 description、正文）：会自动换行，容器的宽度是固定的。
    原文的 \\n 只是英文在某个宽度下的手动断行，中文不该继承。
    ⇒ **一律合并**，让引擎按自己的宽度重新折行。
  · **标签类**（按钮、标题、HUD 标签）：容器宽度是照英文排的，宽度是硬约束。
    ⇒ **只在合并后宽度 ≤ 原文最宽行时才合并**；否则保持多行。

安全阈值：合并后 ≤ 原文最宽行 × TOLERANCE（默认 1.05，留一点余量）。

产出 translations/overlay/zz-wrap.tsv（两列 TSV：编号 / 译文）。
文件名以 zz 开头，排在 z-fixes.tsv 之后，优先级最高。

用法：
    python tools/fix_wrapping.py --dry-run      # 只看会改什么
    python tools/fix_wrapping.py
"""

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
CLASSIFIED = os.path.join(ROOT, "data", "dump", "strings_all_classified.jsonl")
OUT = os.path.join(ROOT, "translations", "overlay", "zz-wrap.tsv")

TOLERANCE = 1.05


def structural(en, cn):
    """
    这条的换行是不是**结构性**的？结构性的绝对不许合并。

    判据：原文或译文里出现 `\\n\\n`（空行）。空行是**段落分隔**，不是英文为了宽度做的断行。
    典型：启动时那封欢迎信 `HELLO AND WELCOME!\\n\\n\\nThank you for playing...`
    —— 我第一版漏了这个判断，把整封信合并成一行、段落全没了（用户报的 bug）。
    """
    return "\\n\\n" in en or "\\n\\n" in cn


def is_body(en):
    """
    这条是「成句的正文」还是「短语标签」？

    正文（描述、说明）会自动换行，原文的 \\n 只是英文在某个宽度下的手动断行，
    中文合并后让引擎自己折行就行 —— 安全。

    短语标签（`choose / control type / to start`、`PICK UP / SOME STUFF`）
    的换行是排版设计，容器宽度照英文排的 —— 合并必须算准，否则会撑破或变成一条长线。
    """
    for s in en.split("\\n"):
        s = s.strip()
        if not s:
            continue
        if vw(s) > 20 or re.search(r"[.!?,;:]", s):
            return True
    return False


def join_cn(segs):
    """
    把中文的多个段落接成一行。

    接续处**只在两侧都是 ASCII 字母数字时才补一个空格** —— 中文之间不空格，
    `弹丸命中时爆炸,` + `只要 GEL 足够` 应接成 `弹丸命中时爆炸,只要 GEL 足够`。
    """
    out = ""
    for seg in segs:
        seg = seg.strip()
        if not seg:
            continue
        if not out:
            out = seg
            continue
        a = out[-1]
        b = seg[0]
        if a.isascii() and a.isalnum() and b.isascii() and b.isalnum():
            out += " " + seg
        else:
            out += seg
    return out


def strip_markup(s):
    s = re.sub(r"<[^>]*>", " ", s)
    return re.sub(r"\{[^}]*\}", " ", s)


def vw(s):
    """渲染宽度：汉字与全角 = 2，空格 = 0.5，其余 = 1。"""
    t = 0.0
    for c in strip_markup(s):
        if c == "\n":
            continue
        t += 2.0 if ord(c) > 0x2E80 else (0.5 if c == " " else 1.0)
    return t


def norm(s):
    for a, b in {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def load_contexts():
    ctx = {}
    if not os.path.exists(CLASSIFIED):
        return ctx
    for line in open(CLASSIFIED, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if o.get("decision") != "keep":
            continue
        k = norm(o["text"])
        if k not in ctx:
            ctx[k] = o.get("key_or_context", "")
    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=TABLE)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = []
    for line in open(args.table, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) >= 3:
            rows.append((f[0], f[1], f[2]))

    ctxs = load_contexts()
    merged, rejected, kept = [], [], []

    for rid, en, cn in rows:
        if "\\n" not in cn:
            continue
        segs_en = en.split("\\n")
        segs_cn = cn.split("\\n")
        if sum(1 for s in segs_cn if s.strip()) <= 1:
            continue                      # 中文本来就只有一行有字，不动

        if structural(en, cn):
            kept.append((rid, en, cn, "含空行 = 段落分隔，结构性换行"))
            continue

        body = is_body(en)
        max_en = max(vw(s) for s in segs_en)
        one_line = join_cn(segs_cn)
        w = vw(one_line)

        if body:
            merged.append((rid, en, cn, one_line, max_en, w, "成句正文，会自动换行"))
        elif w <= max_en * args.tolerance:
            merged.append((rid, en, cn, one_line, max_en, w,
                           "短语标签，合并 %.1f ≤ %.1f×%.2f" % (w, max_en, args.tolerance)))
        else:
            rejected.append((rid, en, cn, one_line, max_en, w))

    print("扫描完毕：中文含多个非空行的条目 %d 条" % (len(merged) + len(rejected) + len(kept)))
    print("  合并 %d 条，保持多行 %d 条，结构性换行不动 %d 条\n"
          % (len(merged), len(rejected), len(kept)))

    if kept:
        print("── 结构性换行，绝对不动 ──")
        for rid, en, cn, why in kept:
            print("  %s  %-40s  %s" % (rid, en.replace("\\n", "⏎")[:40], why))
        print()

    if merged:
        print("── 合并（前 20 条）──")
        for rid, en, cn, one, me, w, why in merged[:20]:
            print("  %s  %-34s  原最宽 %.1f -> 合并 %.1f   %s" % (rid, en.replace("\\n", "⏎")[:34], me, w, why))
            print("      %s  ->  %s" % (cn.replace("\\n", "⏎")[:52], one[:52]))
        if len(merged) > 20:
            print("  … 还有 %d 条" % (len(merged) - 20))

    if rejected:
        print("\n── 保持多行（合并会超宽）──")
        for rid, en, cn, one, me, w in rejected:
            print("  %s  %-30s  原最宽 %.1f，合并要 %.1f（超 %.0f%%）"
                  % (rid, en.replace("\\n", "⏎")[:30], me, w, 100 * (w / me - 1)))

    if not merged:
        print("\n没有需要改的。")
        return 0
    if args.dry_run:
        print("\n（--dry-run，没有写文件）")
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 由 tools/fix_wrapping.py 生成 —— 换行排版修正\n")
        f.write("# 规则：描述类一律合并（会自动换行）；标签类只在合并后不超原文最宽行时合并。\n")
        f.write("# 本文件排在 z-fixes.tsv 之后，优先级最高。重跑脚本会覆盖。\n")
        for rid, en, cn, one, me, w, why in merged:
            f.write("%s\t%s\n" % (rid, one))

    print("\n已写出 %s（%d 条）" % (os.path.relpath(args.out, ROOT), len(merged)))
    print("接着运行：python tools\\build_table.py --sync-plugin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
