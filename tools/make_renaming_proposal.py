#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成命名提案表 translations/renaming-proposal.xlsx。

范围：6 个配装角色 + 38 件武器与主动装备（用户选定的范围）。
每条给出：原文 / 现译 / 功能描述（来自游戏资源）/ 提议 / 提议理由 / 你的决定（留空）。

命名体系见文件内的「命名体系」工作表。
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "translations", "renaming-proposal.xlsx")

# (编号, 原文, 现译, 功能描述, 提议, 理由)
# 提议为 "" 表示建议保留现译。
CHARS = [
    ("0187", "GUNNER", "枪手", "初始武器：霰弹枪", "", "「枪手」就是最朴素的职业名，gunner 本身不带修辞，改花哨反而失真。建议保留。"),
    ("0185", "ROCKETEER", "火箭手", "初始武器：追踪导弹", "火箭客", "-eer / -eteer 是「搞这行的人」。中文用「客」收尾（独行客、刀客）比「手」多一分江湖气，也更像绰号。"),
    ("0183", "SLAYER", "杀戮者", "初始武器：刀刃", "屠戮者", "slayer 的杀意比「杀戮」更重，「屠」字把主动性拉满。三个字，与其余角色等长。"),
    ("0188", "RUSHER", "突袭者", "初始武器：霰弹枪", "疾袭者", "rush 的核心是「快」不是「突然」。「疾」把速度感写进名字，也更贴霰弹枪贴脸打的打法。"),
    ("0186", "THROWER", "投掷者", "初始武器：弩箭（BOLT）", "掷矛手", "thrower 直译「投掷者」太像动词。它的武器是弩矢，用古代兵种「掷矛手」既有画面又像职业名（对标现实里的标枪手）。"),
    ("0189", "WORMSTER", "蠕虫王", "初始武器：蠕虫（WORM）", "虫王", "wormster 是 worm 加戏谑后缀 -ster，本身就有点滑稽。「蠕虫王」太书面，「虫王」更像外号，也压得住这个角色的怪。"),
]

WEAPONS = [
    ("0173", "SHOTGUN", "霰弹枪", "短程、高散布弹丸", "霰铳",
     "「霰」直取 shot 的意象（霰本就是小冰粒，成群散射），「铳」是火器旧称，给复古未来感。比「霰弹枪」像一件装备的代号。"),
    ("0139", "LASER", "激光", "（无描述）", "灼线",
     "laser 的本质是「一条烧穿东西的线」。叫「激光」是物理名词，叫「灼线」才有威胁感，也与游戏里激光是精准高伤武器一致。"),
    ("0137", "FLAME", "喷火器", "it's a flamethrower, yes", "焚风",
     "焚风是真实存在的干热风（阿尔卑斯山南麓），既是火又是风。借用真实现象当代号，正是现实武器命名（响尾蛇、战斧）的路子。"),
    ("0163", "BOLT", "弩箭", "远程、高伤害弹丸武器", "惊弩",
     "bolt 本义是弩矢，保留「弩」是对的；加「惊」字点出它单发高伤、中一发的意外感。两字比「弩箭」更有代号相。"),
    ("0149", "CAN", "罐子", "发射受重力影响的小水晶", "晶罐",
     "can 就是罐，直译「罐子」太素。点出里面装的是水晶，既忠于原文又给了画面。"),
    ("0152", "FLACK", "高射炮", "短程爆炸霰弹", "破片幕",
     "flak 本义是防空破片弹，不是「高射炮」（那是发射它的炮）。「破片幕」说的是它打出去的效果，贴合它短程一大片的打法。"),
    ("0153", "MARBLES", "弹珠", "缓慢移动的爆炸弹丸", "琉璃雷",
     "marbles 直译是弹珠/琉璃球，但「弹珠」读起来没有威胁。加「雷」点出会炸。琉璃的质感也符合像素美术。"),
    ("0165", "DART", "追踪导弹", "锁定敌人的小型追踪导弹", "追镖",
     "dart 是镖。之前从「飞镖」改成「追踪导弹」是为了说明功能，但功能该由描述承担。回到「镖」，用「追」字保留追踪感。"),
    ("0167", "DEBRIS", "残骸", "受重力影响的小型旋转弹丸", "碎屑",
     "debris 是碎屑残骸。「残骸」像一整块大东西，「碎屑」才是它实际打出来的样子——很多小片在重力下翻滚。"),
    ("0161", "BLADES", "刀刃", "穿透弹丸", "锋刃",
     "blades 保留「刃」，加「锋」强调穿透。也是给这个角色（SLAYER）一点呼应感。"),
    ("0175", "WORM", "蠕虫", "短程发射成串的微小弹丸", "虫链",
     "worm 保留「虫」，「链」点出它是一串串打出去的。名字本身就描述了弹道形状，但不直白说武器类型。"),
    ("0169", "DISC GUN", "圆盘枪", "短程、高伤害旋转圆盘", "飞锯",
     "spinning discs 打出去就是飞旋的锯齿。真实世界里没有叫「圆盘枪」的武器，但有「飞锯」这种东西。短、狠、有画面。"),
    ("0171", "POPPER", "爆响枪", "高射速、基础弹丸武器", "爆豆",
     "popper 是拟声词（啪、爆）。「爆豆」是中文里形容连续爆响的现成说法，正好对上它高射速的定位。"),
    ("0140", "LOON", "火球", "缓慢移动的光球，爆炸时燃烧潜力极高", "鬼火",
     "loon 本义是潜鸟，也指疯子。它实际是个慢慢飘过来、炸开一片火的球——「鬼火」同时抓住「飘」和「烧」，也带一点 loon 的怪。"),
    ("0157", "SHARD", "大水晶", "命中时产生大爆炸的大块水晶", "晶爆",
     "shard 是碎片。叫「大水晶」是在描述材质，叫「晶爆」是在说它干什么，也更有代号感。"),
    ("0159", "DANDELION", "蒲公英", "命中时爆炸，释放一组次级爆炸物", "蒲公英",
     "**建议保留。** 原词本身就是绝佳的比喻（种子随风散开＝次级爆炸物四散），中文「蒲公英」完美对应，改任何字都会变差。这条是全表里唯一我建议不动的武器名。"),
    ("0145", "TOROID", "电环", "电击附近敌人直到耗尽电量", "电弧环",
     "toroid 是环形。「电环」少了它持续放电的特性，加「弧」把电弧写进去，读起来也更像科幻装备。"),
    ("0147", "ZAPPER", "电击器", "由电子弧连接的光球", "电链",
     "描述说的是「光球被电弧串起来」——那就是一条链。「电击器」是电器分类词，不是代号。"),
    ("0151", "CLUSTER CUBE", "集束立方", "一大爆，然后很多小爆", "集束方",
     "cluster cube 是「成簇的方块」。中文四字「集束立方」偏术语，缩成三字「集束方」更利落，也仍是同一个东西。"),
    ("0142", "FIRE MISSILE", "火焰导弹", "缓慢飞行、锁定敌人、命中点燃", "燃矢",
     "fire + missile。「导弹」是类别词，「矢」是古语里的箭，冷兵器感与科幻混搭，正好是这个游戏的调性。"),
    ("0155", "GEL MISSILE", "GEL 导弹", "追踪导弹，锁定敌人并命中爆炸", "GEL 导弹",
     "**建议保留。** GEL 是 8 个 HUD 资源名之一（按既定决策保留英文大写），武器名照抄资源名最好认。这系列一共三把「X 导弹」，统一比各自起绰号清楚。"),
    ("0143", "Electron Missile", "ELECTRON 导弹", "爆炸时电击附近的敌方单位", "ELECTRON 导弹",
     "**建议保留。** 同 GEL 导弹：资源名照抄，三把导弹系列统一。"),
]

ACTIVE = [
    ("0048", "IGNITER", "点火器", "向下发射短程弹丸，弹丸爆炸并点燃大部分东西", "引火锥",
     "igniter 是点火装置。它向下打一发、炸开一片火，「锥」既说形状也说火势扩散的方向感。比「点火器」这个功能词更像装备。"),
    ("0050", "VIAL", "小瓶", "投下装满高温物质的玻璃瓶，爆炸释放大量燃烧弹丸", "焚瓶",
     "vial 是小瓶。直译「小瓶」完全看不出是武器。加「焚」字，一眼知道扔出去会烧。"),
    ("0062", "CIRCUIT", "电路", "部署一圈电击弹丸", "回路",
     "circuit 本义是回路、环行，正好对上它「部署成一圈」的行为。比「电路」这个词更像装置名，也保住了原文的「环」义。"),
    ("0064", "FIELD GENERATOR", "现场生成器", "在任何地方丢下它都会生成燃料", "野站",
     "field 这里是「野外/现场」（实地作业），不是「力场」。直译「现场生成器」拗口且歧义。现实里野战装备常用「野」字打头，「野站」两字干净。"),
    ("0066", "AIR MINE", "空中地雷", "部署漂浮的爆炸地雷", "浮雷",
     "air mine 是浮在空中的雷。「空中地雷」四个字太长且像注释，真实的「水雷／浮雷」命名法就是一字定性，「浮雷」正好。"),
    ("0068", "MISSILE SURGE", "导弹齐射", "向各个方向发射大量爆炸导弹", "弹幕涌",
     "surge 是涌、暴涨，不是「齐射」（齐射只说了同时）。「弹幕涌」保留「四面八方涌出来」的意思。"),
    ("0070", "TEARDROP", "泪滴", "投下高爆炸弹", "泪坠",
     "teardrop 的形状就是炸弹下落的样子。「泪滴」像形容，「泪坠」像装备名，一字之差但落点感更强。"),
]

CONSUMABLE = [
    ("0033", "BOMB", "炸弹", "5 秒后引爆", "炸雷",
     "bomb 直译「炸弹」是通名，不像具体装备。它有个 5 秒引信，「雷」在中文里正好带着「埋着等你踩」的感觉。"),
    ("0037", "MATCHBOX", "火柴盒", "3 秒后引爆，点燃周围的东西", "燃盒",
     "matchbox 是火柴盒，而火柴的作用就是引火。「燃盒」保留原文的盒子意象，也直说了它点火。"),
    ("0031", "BEACON", "信标", "用小型炸药切进天花板的装置", "天锚",
     "beacon 是信标，但它实际是钉进天花板当锚点用的。直译「信标」会让人以为只是标记。「天锚」说清了它挂在天上、要固定住。"),
    ("0035", "FUEL GENERATOR", "FUEL 生成器", "部署后只要没被摧毁就会生成 FUEL", "FUEL 井",
     "FUEL 是资源名，按既定决策保留英文。后半段 generator 直译「生成器」偏工程词；「井」在中文里天生就是「持续产出某物的地方」，比「生成器」更像游戏里的一件东西。"),
]

DRONES = [
    ("0052", "COMBAT DRONE", "战斗无人机", "打印装备弹丸武器的无人机", "铳蜂",
     "五台无人机如果都叫「XX无人机」，在 HUD 上既长又分不清。改用「蜂」统一（无人机群＝蜂群），前面一个字区分用途。第一台打弹丸，「铳」。"),
    ("0054", "ELECTRIC DRONE", "电击无人机", "打印会电击附近敌人的无人机", "电蜂",
     "同系列。电击型，「电蜂」。"),
    ("0058", "MISILLE DRONE", "导弹无人机", "打印装备导弹发射器的无人机", "弹蜂",
     "同系列。导弹型，「弹蜂」。（原文 MISILLE 是原作者的拼写错误，翻译时按 MISSILE 理解即可，不必在译文里复现错字。）"),
    ("0056", "PHANTOM DRONE", "幻影无人机", "打印装备激光武器的高级无人机", "影蜂",
     "同系列。phantom 是幻影，取「影」。也呼应它使用激光（看不见的光）。"),
    ("0060", "SUICIDE DRONE", "自爆无人机", "打印在敌人身上爆炸的无人机", "爆蜂",
     "同系列。自爆型，「爆蜂」。"),
]

SHEETS = [
    ("配装角色（6 个）", CHARS),
    ("武器（22 把）", WEAPONS),
    ("主动装备（7 个）", ACTIVE),
    ("消耗品（4 个）", CONSUMABLE),
    ("无人机（5 台）", DRONES),
]

PRINCIPLES = [
    ("命名体系", True),
    ("", False),
    ("三条约束（来自你的要求）", True),
    ("  1. 名字不承担说明功能的职责 —— 功能交给武器描述。所以避免「XX枪 / XX器 / XX机」这类类别词。", False),
    ("  2. 贴合英文原文 —— 保留原词的意象或本义，不做无关的发挥。", False),
    ("  3. 有特色 —— 稍微体现武器特性，符合太空探索冒险调性。", False),
    ("", False),
    ("借鉴的风格", True),
    ("  现实武器代号：响尾蛇（Sidewinder）、战斧（Tomahawk）、毒刺（Stinger）、", False),
    ("                鱼叉（Harpoon）、幽灵（Spirit）、猛禽（Raptor）、不死鸟（Phoenix）", False),
    ("    → 共同点：2~3 个汉字，取一个具体的东西（动物 / 器物 / 自然现象），", False),
    ("      读起来像一件东西的名字，而不像一段说明。", False),
    ("  中文旧式火器名：铳、矢、弩、雷、刃", False),
    ("    → 给科幻装备一点冷兵器的质感，与游戏像素复古风一致。", False),
    ("", False),
    ("具体手法", True),
    ("  · 类别词换意象词：霰弹枪 -> 霰铳、电击器 -> 电链、高射炮 -> 破片幕", False),
    ("  · 加一个字点出行为：罐子 -> 晶罐、小瓶 -> 焚瓶、泪滴 -> 泪坠", False),
    ("  · 统一系列后缀：五台无人机 -> 铳蜂 / 电蜂 / 弹蜂 / 影蜂 / 爆蜂", False),
    ("  · 借用真实现象：焚风（真实的干热风）", False),
    ("", False),
    ("我建议保留的 4 条（改名会变差）", True),
    ("  0159 DANDELION  蒲公英   —— 原词本身就是完美比喻，中文一一对应", False),
    ("  0155 GEL MISSILE / 0143 Electron Missile  —— 资源名照抄，三把导弹系列统一", False),
    ("  0187 GUNNER     枪手     —— gunner 本身不带修辞，改花哨反而失真", False),
    ("", False),
    ("怎么用这张表", True),
    ("  在「你的决定」列写你想要的译名；留空表示同意「提议」；写「保留」表示用回「现译」。", False),
    ("  定完发我，我一次性写进 overlay 并重新打包发版。", False),
    ("  长度提醒：名字出现在配装卡片和模块列表里，宽度有限。", False),
    ("  宽度按渲染算：汉字 = 2，空格 = 0.5，其余 = 1。建议控制在 2~4 个汉字。", False),
]


def main():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head = ["编号", "原文", "现译", "功能描述", "提议", "提议理由", "你的决定"]
    widths = [8, 20, 14, 40, 14, 66, 16]

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hfill = PatternFill("solid", fgColor="1F3864")
    hfont = Font(color="FFFFFF", bold=True, size=11)
    keep_fill = PatternFill("solid", fgColor="E2EFDA")   # 建议保留
    my_fill = PatternFill("solid", fgColor="FFF2CC")     # 你的决定

    total = 0
    first = True
    for title, rows in SHEETS:
        ws = wb.active if first else wb.create_sheet()
        ws.title = title[:31]
        first = False
        ws.append(head)
        for i, w in enumerate(widths, start=1):
            c = ws.cell(row=1, column=i)
            c.fill, c.font = hfill, hfont
            c.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.row_dimensions[1].height = 22
        ws.freeze_panes = "A2"
        for r in rows:
            ws.append(list(r) + [""])
            i = ws.max_row
            for j in range(1, 8):
                cell = ws.cell(row=i, column=j)
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=(j in (4, 6)))
            ws.cell(row=i, column=3).fill = keep_fill
            ws.cell(row=i, column=7).fill = my_fill
            if not r[4]:
                ws.cell(row=i, column=5).fill = keep_fill
            total += 1
        ws.auto_filter.ref = "A1:G%d" % ws.max_row

    ws2 = wb.create_sheet("命名体系")
    ws2.column_dimensions["A"].width = 104
    for text, bold in PRINCIPLES:
        ws2.append([text])
        ws2.cell(row=ws2.max_row, column=1).font = Font(bold=bold, size=12 if bold else 11)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print("已写出 %s" % os.path.relpath(OUT, ROOT))
    for title, rows in SHEETS:
        print("  %-16s %d 条" % (title, len(rows)))
    print("  合计 %d 条" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
