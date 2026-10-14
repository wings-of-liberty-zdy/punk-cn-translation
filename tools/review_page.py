#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成对照评审页 translations/review.html —— 单文件，双击即开，无需服务器。

页面做什么：
  * 按"风险高低"排序：超长 / 偏宽 / 缺字 排最前，其次按分类。你只看前面几十条就够。
  * 每条显示 编号 / 原文 / 译文，译文可以直接在页面上改。
  * 筛选项：待复核 / 超长 / 偏宽 / 缺字 / 各分类 / 只看已改。
  * 「导出改动」把改过的条目输出成 overlay TSV 片段，贴进 translations/overlay/ 即可。

用法：
    python tools/review_page.py
    python tools/review_page.py --out translations/review.html
"""

import argparse
import collections
import html
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
REPORT = os.path.join(ROOT, "data", "validate.json")
CLASSIFIED = os.path.join(ROOT, "data", "dump", "strings_all_classified.jsonl")
OUT = os.path.join(ROOT, "translations", "review.html")

_QUOTES = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}

CATEGORY_CN = {
    "ui_menu": "界面与菜单",
    "item_module_desc": "物品与模块",
    "tutorial_hint": "教程提示",
    "dialogue_story": "剧情",
    "other": "其他",
}


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


def load_contexts():
    """归一化原文 -> 上下文路径（让评审的人知道这句出现在哪）。"""
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
            ctx[k] = o.get("key_or_context", "")[:96]
    return ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=TABLE)
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    rows = []
    for line in open(args.table, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) < 3:
            continue
        rows.append({"id": f[0], "en": from_cell(f[1]), "cn": from_cell(f[2])})

    issues = {}
    cats = {}
    if os.path.exists(args.report):
        rep = json.load(open(args.report, encoding="utf-8"))
        issues = rep.get("issues", {})

    # 分类从提取结果里取
    cls = {}
    if os.path.exists(CLASSIFIED):
        for line in open(CLASSIFIED, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("decision") == "keep":
                cls.setdefault(norm(o["text"]), o.get("category", "other"))
    ctxs = load_contexts()

    RISK = ["缺字", "标签错位", "换行错位", "全角标点", "残留英文", "原文已变更", "宽度提示"]

    for r in rows:
        k = norm(r["en"])
        r["cat"] = cls.get(k, "other")
        r["ctx"] = ctxs.get(k, "")
        fl = issues.get(r["id"], [])
        r["flags"] = [d["kind"] for d in fl]
        r["detail"] = "；".join("%s：%s" % (d["kind"], d["detail"]) for d in fl if d["detail"])
        r["risk"] = min([RISK.index(x) for x in r["flags"] if x in RISK] or [99])

    rows.sort(key=lambda r: (r["risk"], r["cat"], r["id"]))

    n_risk = sum(1 for r in rows if r["risk"] < 99)
    counts = collections.Counter()
    for r in rows:
        for x in r["flags"]:
            counts[x] += 1

    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")

    chips = [("all", "全部 %d" % len(rows)),
             ("risk", "待复核 %d" % n_risk),
             ("changed", "已改 0")]
    for k in RISK:
        if counts.get(k):
            chips.append((k, "%s %d" % (k, counts[k])))
    for k, v in collections.Counter(r["cat"] for r in rows).most_common():
        chips.append(("cat:" + k, "%s %d" % (CATEGORY_CN.get(k, k), v)))

    chip_html = "".join(
        '<button class="chip%s" data-f="%s">%s</button>'
        % (" on" if key == "risk" else "", html.escape(key), html.escape(label))
        for key, label in chips)

    page = TEMPLATE.replace("__ROWS__", payload) \
                   .replace("__CHIPS__", chip_html) \
                   .replace("__TOTAL__", str(len(rows))) \
                   .replace("__RISK__", str(n_risk))

    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print("评审页已写入 %s" % os.path.relpath(args.out, ROOT))
    print("  条目 %d，待复核 %d" % (len(rows), n_risk))
    print("  问题分布：%s" % dict(counts))


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>PUNK 汉化 · 对照评审</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #14140f; color: #ddd8cc;
         font: 14px/1.55 "Segoe UI", "Microsoft YaHei", sans-serif; }
  header { position: sticky; top: 0; z-index: 5; background: #1c1b16;
           border-bottom: 1px solid #35322a; padding: 10px 16px; }
  h1 { margin: 0 0 8px; font-size: 15px; font-weight: 650; color: #f0ece0; }
  h1 small { color: #8a8578; font-weight: 400; margin-left: 8px; }
  .bar { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .chip { font: inherit; font-size: 12.5px; padding: 4px 10px; border-radius: 999px;
          border: 1px solid #3d3a30; background: #201f19; color: #b9b3a4; cursor: pointer; }
  .chip:hover { border-color: #5a5546; color: #e6e1d4; }
  .chip.on { background: #3a2f22; border-color: #8a6a3c; color: #f0c98a; font-weight: 600; }
  input[type=search] { font: inherit; font-size: 13px; padding: 5px 10px; min-width: 200px;
          border-radius: 7px; border: 1px solid #3d3a30; background: #201f19; color: #ddd8cc; }
  button.act { font: inherit; font-size: 12.5px; padding: 5px 11px; border-radius: 7px;
          border: 1px solid #3d3a30; background: #201f19; color: #b9b3a4; cursor: pointer; }
  button.act:hover { border-color: #5a5546; color: #e6e1d4; }
  button.act.pri { background: #2f4a35; border-color: #4d7a57; color: #cfe8d5; font-weight: 600; }
  main { padding: 12px 16px 60px; }
  .row { border: 1px solid #2b2921; border-radius: 9px; margin-bottom: 7px; overflow: hidden; }
  .row.risk { border-color: #6b4a22; }
  .row.risk.hi { border-color: #8a3a2a; }
  .head { display: flex; gap: 10px; align-items: baseline; padding: 7px 11px;
          background: #1a1913; font-size: 12px; color: #8a8578; }
  .head b { color: #cfc9b8; font-weight: 650; font-size: 12.5px; }
  .head .cat { color: #7d8a6a; }
  .head .flags { margin-left: auto; color: #d29a4a; }
  .body { padding: 8px 11px 10px; }
  .en { color: #8a8578; white-space: pre-wrap; word-break: break-word;
        font-size: 12.5px; margin-bottom: 6px; }
  .cn { width: 100%; font: inherit; font-size: 13.5px; color: #f0ece0; background: #201f19;
        border: 1px solid #3d3a30; border-radius: 6px; padding: 6px 8px; resize: vertical;
        min-height: 34px; }
  .cn:focus { outline: none; border-color: #8a6a3c; }
  .cn.dirty { border-color: #4d7a57; background: #1e2620; }
  .meta { margin-top: 5px; font-size: 11.5px; color: #6f6a5d; }
  .meta .ctx { color: #5f5a4f; }
  .empty { color: #6f6a5d; padding: 30px 0; text-align: center; }
  dialog { border: 1px solid #3d3a30; border-radius: 10px; background: #1c1b16; color: #ddd8cc;
           max-width: 720px; width: 90%; padding: 0; }
  dialog::backdrop { background: rgba(0,0,0,.6); }
  dialog .dh { padding: 10px 14px; border-bottom: 1px solid #35322a; font-weight: 650; }
  dialog .db { padding: 12px 14px; }
  dialog textarea { width: 100%; height: 260px; font: 12.5px/1.5 ui-monospace, Consolas, monospace;
           background: #14140f; color: #ddd8cc; border: 1px solid #3d3a30; border-radius: 7px; padding: 9px; }
  dialog .df { padding: 10px 14px; border-top: 1px solid #35322a; display: flex; gap: 8px; }
</style>
<body>
<header>
  <h1>PUNK 汉化 · 对照评审 <small>共 __TOTAL__ 条，待复核 __RISK__ 条。译文可直接在下面改。</small></h1>
  <div class="bar">
    __CHIPS__
    <input type="search" id="q" placeholder="搜编号 / 原文 / 译文">
    <button class="act pri" id="exp">导出改动</button>
  </div>
</header>
<main id="list"></main>

<dialog id="dlg">
  <div class="dh">改动片段（两列 TSV：编号 / 译文）</div>
  <div class="db">
    <p style="margin:0 0 8px;font-size:12.5px;color:#8a8578">
      存成 <code>translations/overlay/&lt;随便起名&gt;.tsv</code>，然后重跑
      <code>tools/build_table.py --sync-plugin</code> 就生效。文件名排序靠后的覆盖靠前的。
    </p>
    <textarea id="out" readonly></textarea>
  </div>
  <div class="df">
    <button class="act pri" id="copy">复制</button>
    <button class="act" id="close">关闭</button>
  </div>
</dialog>

<script>
const ROWS = __ROWS__;
const CAT = {ui_menu:"界面与菜单", item_module_desc:"物品与模块",
             tutorial_hint:"教程提示", dialogue_story:"剧情", other:"其他"};
let filter = "risk", q = "";
const orig = {};
ROWS.forEach(r => orig[r.id] = r.cn);

const list = document.getElementById("list");
const qEl = document.getElementById("q");

function esc(s){ return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function show(s){ return esc(s).replace(/\\n/g, "<span style='color:#6f6a5d'>\\n</span>"); }

function match(r){
  if (filter === "risk" && r.risk >= 99) return false;
  if (filter === "changed" && r.cn === orig[r.id]) return false;
  if (filter !== "all" && filter !== "risk" && filter !== "changed") {
    if (filter.startsWith("cat:")) { if (r.cat !== filter.slice(4)) return false; }
    else if (!r.flags.includes(filter)) return false;
  }
  if (q) {
    const hay = (r.id + " " + r.en + " " + r.cn + " " + r.ctx).toLowerCase();
    if (!hay.includes(q.toLowerCase())) return false;
  }
  return true;
}

function render(){
  const hits = ROWS.filter(match);
  if (!hits.length) { list.innerHTML = '<div class="empty">没有匹配的条目</div>'; return; }
  list.innerHTML = hits.map(r => `
    <div class="row${r.risk < 99 ? " risk" : ""}${r.risk === 0 ? " hi" : ""}">
      <div class="head">
        <b>${r.id}</b>
        <span class="cat">${CAT[r.cat] || r.cat}</span>
        <span class="flags">${r.flags.length ? r.flags.join(" · ") : ""}</span>
      </div>
      <div class="body">
        <div class="en">${show(r.en)}</div>
        <textarea class="cn${r.cn !== orig[r.id] ? " dirty" : ""}" data-id="${r.id}"
                  rows="${Math.max(1, Math.ceil(r.cn.length / 46))}">${esc(r.cn)}</textarea>
        ${r.detail ? `<div class="meta">${esc(r.detail)}</div>` : ""}
        ${r.ctx ? `<div class="meta ctx">${esc(r.ctx)}</div>` : ""}
      </div>
    </div>`).join("");
}

list.addEventListener("input", e => {
  if (!e.target.classList.contains("cn")) return;
  const id = e.target.dataset.id, r = ROWS.find(x => x.id === id);
  r.cn = e.target.value;
  e.target.classList.toggle("dirty", r.cn !== orig[id]);
  document.querySelector('[data-f="changed"]').textContent =
    "已改 " + ROWS.filter(x => x.cn !== orig[x.id]).length;
});

document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => {
  document.querySelectorAll(".chip").forEach(x => x.classList.remove("on"));
  c.classList.add("on"); filter = c.dataset.f; render();
}));
qEl.addEventListener("input", () => { q = qEl.value; render(); });

document.getElementById("exp").addEventListener("click", () => {
  const ch = ROWS.filter(r => r.cn !== orig[r.id]);
  const lines = ["# 评审页导出 · 两列 TSV：编号 / 译文",
                 "# 导出时间见文件系统，共 " + ch.length + " 条改动"];
  ch.forEach(r => lines.push(r.id + "\t" + r.cn.replace(/\n/g, "\\n").replace(/\t/g, "\\t")));
  document.getElementById("out").value = lines.join("\n");
  document.getElementById("dlg").showModal();
});
document.getElementById("copy").addEventListener("click", () => {
  const t = document.getElementById("out"); t.select(); document.execCommand("copy");
  document.getElementById("copy").textContent = "已复制";
});
document.getElementById("close").addEventListener("click", () =>
  document.getElementById("dlg").close());

render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
