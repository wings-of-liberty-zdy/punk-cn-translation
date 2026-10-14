#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从提取结果生成 / 更新翻译表 translations/punk.tsv。

设计要点（与 plan.html 的决策一致）：
  * 三列：稳定编号 / 原文 / 中文。编号在条目第一次出现时分配，之后永不改变。
  * 原文列里的换行写成字面量 \\n，制表符写成 \\t。读的时候还原。
  * 已有条目的编号与译文原样保留；新条目拿新编号（只增不减，不回收）。
  * 排除规则显式列在下面，并且把每一条排除都打印出来 —— 不静默丢东西。
    想看全部条目（含调试菜单）就加 --include-all。

用法：
    python tools/build_table.py                    # 生成/更新 translations/punk.tsv
    python tools/build_table.py --include-all      # 不做排除
    python tools/build_table.py --sync-plugin      # 顺便同步进插件资源
    python tools/build_table.py --report-only      # 只看统计，不写文件
"""

import argparse
import collections
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSIFIED = os.path.join(ROOT, "data", "dump", "strings_all_classified.jsonl")
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
PLUGIN_COPY = os.path.join(ROOT, "plugin", "PunkCn", "Resources", "punk-cn.tsv")
INTERNAL_NAMES = os.path.join(ROOT, "glossary", "internal-names.txt")
OVERLAY_DIR = os.path.join(ROOT, "translations", "overlay")

# 由 main() 从 glossary/internal-names.txt 装载。
_INTERNAL = set()


def load_internal_names(path):
    names = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                names.add(line)
    return names

# ── 排除规则 ────────────────────────────────────────────────────────────────
# 教训：不要按"文本长什么样"排除。这个游戏的 UI 全是全大写
# （SETTINGS / NEW RUN / MASTER VOLUME / FLAME / LASER），
# 用 ^[A-Z]{2,7}...$ 这类规则会把整个菜单一起吃掉。
# 真正可靠的是**上下文路径**，加上一张很小的显式名单。

# 上下文路径里出现这些片段的，玩家看不到。
EXCLUDE_CONTEXT = (
    "UI/DebugMenu",        # 开发者作弊菜单
    "UI/PerTestCanvas",    # 开发者测试画布
    "UI/[Graphy]",         # 第三方性能覆盖层
    "DebugUI",
    "Canvas/Credits",      # 制作人员名单：人名不翻，整体略过
)

# 按键名与手柄键名。这张名单要手工维护 —— 它们和 UI 标签长得一模一样。
EXCLUDE_KEY_NAMES = {
    "TAB", "ALT", "SPACE", "ENTER", "ESC", "ESCAPE", "BACKSPACE", "SHIFT",
    "L SHIFT", "R SHIFT", "L CTRL", "R CTRL", "CTRL", "WASD", "MB", "GDT",
    "WPN", "FPS", "DPAD DOWN", "DPAD UP", "DPAD LEFT", "DPAD RIGHT",
    "FIRE 1", "FIRE 2", "FIRE 1/2", "LMB", "RMB", "MMB",
}

# 整条文本命中这些正则的，不是给玩家读的文案。
EXCLUDE_TEXT = (
    r"^[\d\s/+\-.,:%]+$",     # 纯数字与标点：100、2/3、13:45:59、+2、-
    r"^v?\d+(\.\d+)+$",       # 版本号：v0.02
    r"^\{0\}$",               # 只有一个占位符
    r"^\d+x\d+.*$",           # 1920x1080 60fps
    r"^[A-Za-z]$",            # 单字母按键：F、A、E、w、d、s、B
)

# 注意：**不按文本排除预制体占位符**（MODULENAME / New Text / Description）。
# 它们运行时会被数据覆盖，翻了也无害；而 MODULE NAME 这类文本同时是
# 占位符和一个真标签（Canvas/HoveredModuleInfo/Row/Name），
# 按文本排除会把真标签一起误杀。

# ── 文本归一化：必须与插件 Table.Normalize 完全一致 ──────────────────────────
_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}


def norm(s):
    for a, b in _QUOTES.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def to_cell(s):
    """写进 TSV 单元格：换行与制表符转义。"""
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def from_cell(s):
    """从 TSV 单元格读回：只还原 \\n 与 \\t，其余反斜杠原样。"""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in "nt\\":
            out.append({"n": "\n", "t": "\t", "\\": "\\"}[s[i + 1]])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def excluded_reason(text, context):
    for frag in EXCLUDE_CONTEXT:
        if frag in context:
            return "调试界面或名单 " + frag
    if text.strip() in _INTERNAL:
        return "内部资产名（glossary/internal-names.txt）"
    if text.strip() in EXCLUDE_KEY_NAMES:
        return "按键名（显式名单）"
    for pat in EXCLUDE_TEXT:
        if re.match(pat, text):
            return "非文案（匹配 " + pat + "）"
    return None


def load_existing(path):
    """读已有翻译表 -> {归一化原文: (编号, 译文)}，并记下已用过的最大编号。"""
    rows, max_id = {}, 0
    if not os.path.exists(path):
        return rows, max_id
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 3:
            continue
        num, en, cn = f[0], from_cell(f[1]), from_cell(f[2])
        rows[norm(en)] = (num, cn)
        try:
            max_id = max(max_id, int(num))
        except ValueError:
            pass
    return rows, max_id


def load_overlays(dirpath):
    """
    读 translations/overlay/*.tsv —— 两列：编号 / 译文。按编号覆盖译文。
    这是校对与批量翻译回填的入口：评审页导出什么格式，这里就吃什么格式。
    """
    ov = {}
    if not os.path.isdir(dirpath):
        return ov
    for fn in sorted(os.listdir(dirpath)):
        if not fn.endswith(".tsv"):
            continue
        for line in open(os.path.join(dirpath, fn), encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            f = line.split("\t")
            if len(f) >= 2:
                ov[f[0]] = from_cell(f[1])
    return ov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strings", default=CLASSIFIED, help="分类后的提取结果 jsonl")
    ap.add_argument("--out", default=TABLE)
    ap.add_argument("--include-all", action="store_true", help="不做排除")
    ap.add_argument("--sync-plugin", action="store_true", help="同时写入插件资源")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--show-excluded", type=int, default=0, metavar="N",
                    help="每种排除原因打印 N 条样本，用来核对规则没写错")
    ap.add_argument("--renumber", action="store_true",
                    help="按当前顺序重排编号（译文按原文保留）。"
                         "只在发布前用过一次，用来消掉排除规则留下的编号空洞；"
                         "发布之后不要再用，否则玩家手里的编号会对不上。")
    args = ap.parse_args()

    _INTERNAL.update(load_internal_names(INTERNAL_NAMES))
    print("内部资产名排除名单：%d 条（%s）" % (len(_INTERNAL), os.path.relpath(INTERNAL_NAMES, ROOT)))

    # 1 · 读提取结果，按归一化原文去重，记下所有出处
    entries = collections.OrderedDict()
    dropped = collections.Counter()
    samples = collections.defaultdict(list)
    kept_raw = 0
    for line in open(args.strings, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if o.get("decision") != "keep":
            continue
        text, ctx = o["text"], o.get("key_or_context", "")
        if not text:
            continue
        key = norm(text)
        if not key:
            continue
        kept_raw += 1
        if not args.include_all:
            why = excluded_reason(text, ctx)
            if why:
                dropped[why] += 1
                if len(samples[why]) < args.show_excluded:
                    samples[why].append((text, ctx))
                continue
        e = entries.setdefault(key, {"text": text, "contexts": [], "category": o.get("category")})
        if len(e["contexts"]) < 6:
            e["contexts"].append(ctx)

    # 2 · 合并已有译文
    existing, max_id = load_existing(args.out)
    if not existing and os.path.exists(PLUGIN_COPY):
        existing, max_id = load_existing(PLUGIN_COPY)

    rows, fresh, kept = [], 0, 0
    overlay = load_overlays(OVERLAY_DIR)
    ov_hit = 0
    for key, e in entries.items():
        if key in existing:
            num, cn = existing[key]
            kept += 1
        else:
            max_id += 1
            num, cn = "%04d" % max_id, ""
            fresh += 1
        if num in overlay:
            if overlay[num] != cn:
                ov_hit += 1
            cn = overlay[num]
        rows.append((num, e["text"], cn, e["category"], e["contexts"]))
    if overlay:
        print("overlay 覆盖 %d 条（共读到 %d 条 overlay 记录）" % (ov_hit, len(overlay)))

    rows.sort(key=lambda r: r[0])

    if args.renumber:
        before = len(rows)
        rows = [("%04d" % (i + 1), t, c, cat, ctx) for i, (_n, t, c, cat, ctx) in enumerate(rows)]
        print("已重排编号：%d 条 -> 0001 .. %04d" % (before, len(rows)))

    print("提取结果里 decision=keep 的条目：%d 条（含重复出现）" % kept_raw)
    if dropped:
        print("按规则排除 %d 条（去重前）：" % sum(dropped.values()))
        for why, n in dropped.most_common():
            print("    %-46s %d" % (why, n))
            for t, c in samples.get(why, []):
                print("        %-38s %s" % (repr(t)[:38], c[:56]))
    print("进入翻译表：%d 条（去重后）" % len(rows))
    print("    沿用已有条目（含译文）：%d" % kept)
    print("    新分配编号：%d" % fresh)
    if rows:
        print("    编号区间：%s .. %s" % (rows[0][0], rows[-1][0]))
    print("分类：%s" % dict(collections.Counter(r[3] for r in rows)))
    print("总字符：%d   已翻译：%d   待翻译：%d"
          % (sum(len(r[1]) for r in rows),
             sum(1 for r in rows if r[2]),
             sum(1 for r in rows if not r[2])))

    # 旧表里有、但本次提取没出现的编号 —— 游戏删了这句，或者改了英文。
    gone = [k for k in existing if k not in entries]
    if gone:
        print("旧表里未出现的条目：%d 条（编号保留，译文不丢）" % len(gone))
        for k in gone[:10]:
            print("    %s  %s" % (existing[k][0], repr(k)[:60]))

    if args.report_only:
        return

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    header = [
        "# PUNK 试玩版汉化表",
        "# 三列：编号 / 原文 / 中文。制表符分隔。",
        "# 编号在条目第一次出现时分配，之后永不改变。",
        "# 原文里的换行写成字面量 \\n，制表符写成 \\t；中文列同理。",
        "# 富文本标签（<color=...>、<sprite=...>）原样保留，不翻译。",
        "# 标点沿用原文的半角。原文里的拼写错误照抄，不要修正。",
        "# 本文件由 tools/build_table.py 生成，手工改动会在下次运行时保留（按原文匹配）。",
    ]
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(header) + "\n")
        for num, text, cn, _cat, _ctx in rows:
            fh.write("%s\t%s\t%s\n" % (num, to_cell(text), to_cell(cn)))
    print("已写入 %s" % args.out)

    if args.sync_plugin:
        with open(args.out, encoding="utf-8") as src, open(PLUGIN_COPY, "w", encoding="utf-8", newline="\n") as dst:
            dst.write(src.read())
        print("已同步到 %s" % PLUGIN_COPY)


if __name__ == "__main__":
    main()
