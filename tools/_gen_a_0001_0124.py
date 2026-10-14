# -*- coding: utf-8 -*-
"""Generate translations/overlay/a-0001-0124.tsv (rows 0031-0124).

Rows 0001-0030 already carry Chinese in punk.tsv and are skipped.
"""
import sys, io, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation"
SRC = os.path.join(ROOT, "translations", "punk.tsv")
OUT = os.path.join(ROOT, "translations", "overlay", "a-0001-0124.tsv")

# number -> translation.  \n and \t are literal backslash sequences.
T = {
    "0031": "信标",
    "0032": "用小型炸药切进天花板的装置",
    "0033": "炸弹",
    "0034": "5 秒后引爆",
    "0035": "FUEL 生成器",
    "0036": "部署一个小型装置,\\n只要它没被摧毁\\n就会生成 <color=#4D79FF>FUEL</color>",
    "0037": "火柴盒",
    "0038": "3 秒后引爆,点燃周围的东西",
    "0039": "黏合剂",
    "0040": "芯片",
    "0041": "纤维",
    "0042": "前任",
    "0043": "脸",
    "0044": "腺体",
    "0045": "能量星",
    "0046": "生成器",
    "0047": "奇怪的球",
    "0048": "点火器",
    "0049": "向下发射短程弹丸.\\n弹丸爆炸,点燃爆炸范围内的大部分东西",
    "0050": "小瓶",
    "0051": "投下装满高温物质的玻璃瓶.\\n爆炸时释放大量燃烧的次级弹丸.\\n非常适合用来点火",
    "0052": "战斗无人机",
    "0053": "打印无人机,\\n装备弹丸武器",
    "0054": "电击无人机",
    "0055": "打印无人机,\\n电击附近敌人",
    "0056": "幻影无人机",
    "0057": "打印高级无人机,\\n装备激光武器",
    "0058": "导弹无人机",
    "0059": "打印无人机,\\n装备导弹发射器",
    "0060": "自爆无人机",
    "0061": "打印无人机,\\n在敌人身上爆炸",
    "0062": "电路",
    "0063": "部署一圈电击弹丸",
    "0064": "现场生成器",
    "0065": "在任何地方丢下它都会生成燃料",
    "0066": "空中地雷",
    "0067": "部署漂浮的爆炸地雷",
    "0068": "导弹齐射",
    "0069": "向各个方向发射大量爆炸导弹",
    "0070": "泪滴",
    "0071": "投下高爆炸弹",
    "0072": "红眼",
    "0073": "添加燃烧",
    "0074": "为每枚弹丸添加燃烧,\\n只要 CAPS 足够",
    "0075": "+1 连发",
    "0076": "添加火焰爆炸",
    "0077": "弹丸命中时爆炸并燃烧,\\n只要 CAPS 足够",
    "0078": "添加电火花",
    "0079": "弹丸命中时电击附近敌人,\\n只要 ELECTRON 足够",
    "0080": "额外弹丸",
    "0081": "+ 射速",
    "0082": "提高武器射速",
    "0083": "- 散布",
    "0084": "降低弹丸散布",
    "0085": "+ 弹丸速度",
    "0086": "弹丸移动更快",
    "0087": "添加 GEL 爆炸",
    "0088": "弹丸命中时爆炸,\\n只要 GEL 足够",
    "0089": "+ 射程",
    "0090": "弹丸射得更远",
    "0091": "添加 TECH 爆炸",
    "0092": "弹丸命中时爆炸,\\n只要 TECH 足够",
    "0093": "添加爆炸",
    "0094": "弹丸命中时爆炸,\\n只要 STAMINA 足够",
    "0095": "爬行者",
    "0096": "装置",
    "0097": "增幅器",
    "0098": "内嵌",
    "0099": "升级",
    "0100": "POWER",
    "0101": "武器",
    "0102": "增幅核心",
    "0103": "升级附近的模块,\\n提高它们的属性",
    "0104": "能量核心",
    "0105": "CAPS 提升",
    "0106": "提高 <color=#B16623>CAPS</color> 上限",
    "0107": "ELECTRON 提升",
    "0108": "提高 <color=#009AB4>ELECTRON</color> 上限",
    "0109": "FUEL 提升",
    "0110": "提高 <color=#4D79FF>FUEL</color> 上限",
    "0111": "HEALTH 提升",
    "0112": "提高 <color=#B03B3B>HEALTH</color> 上限",
    "0113": "GEL 提升",
    "0114": "提高 <color=#B32AAC>GEL</color> 上限",
    "0115": "STAMINA 提升",
    "0116": "提高 <color=#A8A8A8>STAMINA</color> 上限",
    "0117": "TECH 提升",
    "0118": "提高 <color=#5F46A7>TECH</color> 上限",
    "0119": "CAPS 回复",
    "0120": "缓慢回复 <color=#B16623>CAPS</color>",
    "0121": "HEALTH 回复",
    "0122": "缓慢回复 <color=#B03B3B>HEALTH</color>",
    "0123": "GEL 回复",
    "0124": "缓慢回复 <color=#B32AAC>GEL</color>",
}

# --- read source, find the numbers in range that still need a translation ---
rows = []
with io.open(SRC, "r", encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n").rstrip("\r")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        while len(parts) < 3:
            parts.append("")
        rows.append((parts[0], parts[1], parts[2]))

todo = [n for (n, en, zh) in rows if n.isdigit() and 1 <= int(n) <= 124 and not zh.strip()]
print("rows needing translation in 0001-0124:", len(todo))
missing = [n for n in todo if n not in T]
extra = [n for n in T if n not in todo]
print("missing from dict:", missing)
print("extra in dict   :", extra)
assert not missing and not extra

os.makedirs(os.path.dirname(OUT), exist_ok=True)
lines = [
    "# PUNK 汉化 overlay · 编号 0001-0124",
    "# 两列 TSV:编号 / 译文。换行写 \\n,制表符写 \\t。",
    "# 0001-0030 在 punk.tsv 中已有中文,本文件不收录。",
]
for n in todo:
    lines.append(n + "\t" + T[n])

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines) + "\n")

print("wrote:", OUT, "entries:", len(todo))
