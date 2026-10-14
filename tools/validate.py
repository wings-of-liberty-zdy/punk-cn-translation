#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
翻译表校验：七类问题，逐条列出。

  1 未翻译      第三列为空
  2 缺字        译文里有像素字体没有的字形（会显示成方块）
  3 超长        译文长度超过原文的 1.2 倍（固定宽度的按钮与标题栏会溢出）
  4 残留英文    译文里有没翻译掉的连续英文单词（保留的资源名与按键名除外）
  5 标签错位    <color>/</color>/<sprite> 配对或数量与原文不一致
  6 换行错位    译文里的 \\n 条数与原文不一致
  7 全角标点    译文里出现全角标点（本项目定的是沿用原文半角）

另外检查：
  8 原文已变更  表里的原文在本次提取结果里找不到（游戏改过这句）

用法：
    python tools/validate.py                     # 终端报告
    python tools/validate.py --json out.json     # 同时写 JSON，供评审页用
    python tools/validate.py --quiet             # 只输出结论
退出码：有任一项不通过则 1，否则 0。
"""

import argparse
import collections
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
FONT = os.path.join(ROOT, "plugin", "PunkCn", "Resources", "pixel-cn.ttf")
CLASSIFIED = os.path.join(ROOT, "data", "dump", "strings_all_classified.jsonl")

LEN_RATIO = 1.2

# 固定宽度的容器：只有出现在这些节点下的文本才会被"撑破"。
# 其余（正文、日志、列表项、模块名）要么自动换行，要么列宽由同组最宽的兄弟决定，
# 单看一条的宽度比没有意义 —— 把它们一起报警只会淹没真问题。
FIXED_WIDTH_HINT = (
    "Button", "OptionsMenu", "TabButton", "InputPrompt", "ButtonBody",
    "GUITitle", "GameModeSelector", "Footer",
)

# 允许在译文里保留的英文（见 style-guide.md 第 6、7 节）
ALLOWED_LATIN = {
    "CAPS", "ELECTRON", "FUEL", "GEL", "TECH", "STAMINA", "HEALTH", "POWER",
    "HUD", "P1", "P2", "Discord", "discord", "Steam", "Ex", "PUNK",
    "FPS", "GPU", "CPU", "RAM", "VRAM", "OS", "ms", "MB", "px", "Hz", "dpi",
    "TAB", "ALT", "SPACE", "ENTER", "ESC", "ESCAPE", "SHIFT", "CTRL",
    "WASD", "L", "R", "DPAD", "DOWN", "UP", "LEFT", "RIGHT", "FIRE", "MB",
}
FULLWIDTH = "，。！？：；、（）【】《》“”‘’"

_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}


def norm(s):
    for a, b in _QUOTES.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


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


def load_rows(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 3:
            continue
        rows.append({"id": f[0], "en": from_cell(f[1]), "cn": from_cell(f[2])})
    return rows


def load_font_cmap(path):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    if not os.path.exists(path):
        return None
    f = TTFont(path, lazy=True)
    cm = set()
    for t in f["cmap"].tables:
        cm |= set(t.cmap.keys())
    return cm


def load_contexts(path):
    """归一化原文 -> 上下文路径。用来判断这条文本出现在哪种容器里。"""
    ctx = {}
    if not os.path.exists(path):
        return ctx
    for line in open(path, encoding="utf-8"):
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


def load_extracted(path):
    """本次提取结果里 decision=keep 的归一化原文集合。"""
    seen = set()
    if not os.path.exists(path):
        return seen
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if o.get("decision") == "keep":
            seen.add(norm(o["text"]))
    return seen


def strip_markup(s):
    """去掉富文本标签与占位符，只留玩家真正读到的文字。"""
    s = re.sub(r"<[^>]*>", " ", s)      # <color=#de8700> … </color> <sprite=5>
    s = re.sub(r"\{[^}]*\}", " ", s)    # {0} {0:hh':'mm':'ss'}
    return s


def visual_width(s):
    """
    估算渲染宽度，单位是"一个拉丁字符宽"。
    汉字与全角字符约占 2 个拉丁字宽，空格算半个。
    比按字符数算准得多 —— 按字符数算会漏掉
    「7 个汉字 vs 13 个拉丁字」这种实际更宽的情况。
    """
    w = 0.0
    for c in strip_markup(s):
        if c == "\n":
            continue
        if ord(c) > 0x2E80:
            w += 2.0
        elif c == " ":
            w += 0.5
        else:
            w += 1.0
    return w


def count_tags(s, tag):
    return len(re.findall(r"<%s\b" % re.escape(tag), s))


def count_close(s, tag):
    return len(re.findall(r"</%s\s*>" % re.escape(tag), s))


def check(rows, cmap, extracted, contexts):
    """返回 {编号: [问题...]} 与汇总计数。"""
    issues = collections.OrderedDict()
    counts = collections.Counter()

    def add(rid, kind, detail):
        issues.setdefault(rid, []).append({"kind": kind, "detail": detail})
        counts[kind] += 1

    for r in rows:
        rid, en, cn = r["id"], r["en"], r["cn"]

        if not cn.strip():
            add(rid, "未翻译", "")
            continue

        # 3 宽度：**只作提示，不算错误**。
        #   宽度模型：汉字与全角 = 2，空格 = 0.5，其余 = 1。
        #   ⚠️ 实测教训：这个模型没法知道容器的真实宽度。
        #      `VSYNC`→`垂直同步`（8.0 vs 5.0，超 60%）在设置菜单里**放得下**；
        #      `CO-OP`→`双人合作` 在主菜单按钮里也放得下。
        #      而真正溢出的 `WISHLIST NOW!`/`JOIN OUR DISCORD` 只超 7~8%。
        #      所以：这里只列出来供人扫一眼，**判定靠游戏内截图**（见 plan.html 的验收标准）。
        we, wc = visual_width(en), visual_width(cn)
        ctx = contexts.get(norm(en), "")
        fixed = any(h in ctx for h in FIXED_WIDTH_HINT)
        if we > 0:
            ratio = wc / we
            if ratio > 1.0:
                add(rid, "宽度提示", "宽度 %.1f / %.1f = %.2f 倍%s"
                    % (wc, we, ratio, "，固定宽度容器" if fixed else "，非固定宽度容器"))

        # 2 缺字
        if cmap is not None:
            miss = sorted({c for c in cn if ord(c) > 0x2E80 and ord(c) not in cmap})
            if miss:
                add(rid, "缺字", "".join(miss))

        # 4 残留英文（先剥掉标签与占位符，否则 <color=#de8700> 里的 color 与色码会被误报）
        #    单词长度 >=2 才算：单字母是按键名（E / I / M / F）
        plain = strip_markup(cn)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", plain) if w not in ALLOWED_LATIN]
        if words:
            add(rid, "残留英文", " ".join(sorted(set(words))))

        # 5 标签错位
        for tag in ("color", "size"):
            if count_tags(en, tag) != count_tags(cn, tag) or count_close(en, tag) != count_close(cn, tag):
                add(rid, "标签错位", "<%s> 原文 %d/%d 译文 %d/%d"
                    % (tag, count_tags(en, tag), count_close(en, tag), count_tags(cn, tag), count_close(cn, tag)))
        if count_tags(en, "sprite") != count_tags(cn, "sprite"):
            add(rid, "标签错位", "<sprite> 原文 %d 译文 %d" % (count_tags(en, "sprite"), count_tags(cn, "sprite")))

        # 6 换行错位：只把「译文比原文多」当错误。
        #   中文通常比英文短，本来该合成一行；少一个换行只会让文本更矮，不会溢出。
        #   多出来的换行才可能把固定高度的框撑破。
        if cn.count("\n") > en.count("\n"):
            add(rid, "换行错位", "原文 %d 个 \\n，译文 %d 个（多了）" % (en.count("\n"), cn.count("\n")))

        # 7 全角标点
        fw = sorted({c for c in cn if c in FULLWIDTH})
        if fw:
            add(rid, "全角标点", "".join(fw))

        # 8 原文已变更
        if extracted and norm(en) not in extracted:
            add(rid, "原文已变更", "本次提取结果里找不到这句")

    return issues, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=TABLE)
    ap.add_argument("--json", default=None, help="把报告写成 JSON，供评审页使用")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    rows = load_rows(args.table)
    cmap = load_font_cmap(FONT)
    extracted = load_extracted(CLASSIFIED)
    contexts = load_contexts(CLASSIFIED)
    issues, counts = check(rows, cmap, extracted, contexts)

    translated = sum(1 for r in rows if r["cn"].strip())
    print("翻译表 %s" % os.path.relpath(args.table, ROOT))
    print("  条目 %d   已译 %d   待译 %d" % (len(rows), translated, len(rows) - translated))
    print("  像素字体字形表 %s" % ("已读取" if cmap else "读不到（跳过缺字检查）"))
    print("  提取结果对照 %s" % ("已读取" if extracted else "读不到（跳过原文已变更检查）"))
    print("  " + "─" * 58)

    order = ["未翻译", "缺字", "残留英文", "标签错位", "换行错位", "全角标点", "原文已变更", "宽度提示"]
    for kind in order:
        n = counts.get(kind, 0)
        print("  %-12s %4d  %s" % (kind, n, "通过" if n == 0 else "不通过"))

    if not args.quiet and issues:
        print()
        for kind in order:
            hits = [(rid, d) for rid, lst in issues.items() for d in lst if d["kind"] == kind]
            if not hits:
                continue
            print("── %s（%d 条，最多列 12）" % (kind, len(hits)))
            for rid, d in hits[:12]:
                row = next(r for r in rows if r["id"] == rid)
                print("   %s  %s" % (rid, d["detail"]))
                print("        原: %s" % repr(row["en"])[:74])
                print("        译: %s" % repr(row["cn"])[:74])
            if len(hits) > 12:
                print("   … 还有 %d 条" % (len(hits) - 12))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "issues": issues, "counts": dict(counts)}, fh,
                      ensure_ascii=False, indent=1)
        print("\n报告已写入 %s" % os.path.relpath(args.json, ROOT))

    hard = [k for k in order if k not in ("未翻译", "宽度提示") and counts.get(k, 0) > 0]
    soft = counts.get("宽度提示", 0)
    print("\n结论：%s%s" % ("全部通过" if not hard else "有 %d 类问题未通过" % len(hard),
                          "；另有 %d 条宽度提示，需游戏内截图确认（不是错误）" % soft if soft else ""))
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
