#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打出可直接分发的汉化补丁包。

产物（dist/ 下）：
  PUNK-Chinese-Patch-v<版本>.zip        补丁包本体
  PUNK-Chinese-Patch-v<版本>.zip.sha256 校验值
  release-notes.md                      发布说明

包内结构（**只新增文件，不修改游戏本体任何文件**）：
  BepInEx/core/...                 BepInEx 5 运行时
  BepInEx/plugins/PunkCn.dll       汉化插件（翻译表与字体已内嵌）
  BepInEx/config/...               配置模板
  winhttp.dll                      doorstop 注入器
  doorstop_config.ini
  .doorstop_version
  changelog.txt
  安装说明.txt
  卸载说明.txt

卸载 = 删掉上面这几项，游戏回到原样。

用法：
    python tools/pack_release.py --version 0.1.0
    python tools/pack_release.py --version 0.1.0 --bepinex vendor/BepInEx_win_x64_5.4.23.5.zip
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
PLUGIN_DLL = os.path.join(ROOT, "plugin", "PunkCn", "bin", "Release", "PunkCn.dll")
TABLE = os.path.join(ROOT, "translations", "punk.tsv")
BEPINEX_ZIP = os.path.join(ROOT, "vendor", "BepInEx_win_x64_5.4.23.5.zip")
GAME = r"D:\SteamLibrary\steamapps\common\PUNK Playtest"

# 这 5 项就是补丁在游戏目录里的全部痕迹，卸载时删掉它们。
PATCH_ENTRIES = ["BepInEx", "winhttp.dll", "doorstop_config.ini", ".doorstop_version", "changelog.txt"]

README_INSTALL = """\
PUNK 汉化补丁 v{ver}
========================================

安装
----
1. 关闭游戏（一定要关干净，任务管理器里不能有 Punk.exe）
2. 把本压缩包里的所有文件解压到游戏根目录，覆盖同名文件。
   游戏根目录 = 里面有 Punk.exe 的那个文件夹。Steam 上右键游戏 ->
   管理 -> 浏览本地文件，打开的就是它。
3. 启动游戏。界面就是中文了。

卸载
----
删掉游戏根目录下这 5 项即可，游戏完全回到原样（本体文件一个都没改）：
    BepInEx\\           （整个文件夹）
    winhttp.dll
    doorstop_config.ini
    .doorstop_version
    changelog.txt

说明
----
* 本补丁不修改游戏任何原始文件，只新增上面这些。卸载就是删除。
* 翻译表与中文像素字体都已内嵌在 BepInEx\\plugins\\PunkCn.dll 里，没有外部依赖。
* 内置开关：BepInEx\\config\\punk.cn.translation.cfg 里
  [General] Enabled = false 可临时关掉汉化（改完重启游戏）。
* 本补丁仅供学习交流，请勿用于商业用途。游戏版权归原作者所有。
"""

CHANGELOG = """\
v{ver}
  * 全部 {total} 条界面与物品文案汉化完成
  * 内嵌 12px 中文像素字体（Fusion Pixel，SIL OFL 1.1），与游戏原像素风一致
  * 按游戏原字体的 pointSize 分别建字体资产，字号与行距对齐原版
  * 覆盖两条文本通道：TMP 属性写入 + 资源里序列化的文本
"""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def count_table():
    n = 0
    for line in open(TABLE, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        f = line.split("\t")
        if len(f) >= 3 and f[2].strip():
            n += 1
    return n


def build_plugin():
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
    r = subprocess.run(["dotnet", "build", os.path.join(ROOT, "plugin", "PunkCn", "PunkCn.csproj"),
                        "-c", "Release", "-v", "minimal"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    ok = r.returncode == 0
    for ln in (r.stdout or "").splitlines():
        if ": error" in ln:
            print("   " + ln.strip())
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--bepinex", default=BEPINEX_ZIP)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--game", default=GAME, help="用来核对补丁痕迹的清单（可选）")
    args = ap.parse_args()

    ver = args.version.lstrip("v")
    print("打包 PUNK 汉化补丁 v%s" % ver)

    # 1) 前置检查
    if not os.path.exists(args.bepinex):
        print("× 找不到 BepInEx 包：%s" % args.bepinex)
        return 1
    if not args.skip_build:
        print("· 编译插件…")
        if not build_plugin():
            print("× 编译失败")
            return 1
    if not os.path.exists(PLUGIN_DLL):
        print("× 找不到插件 DLL：%s" % PLUGIN_DLL)
        return 1

    total = count_table()
    dll_mb = os.path.getsize(PLUGIN_DLL) / 1024 / 1024
    print("· 插件 %.2f MB，翻译表 %d 条" % (dll_mb, total))

    # 2) 组装
    stage = os.path.join(DIST, "stage")
    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    with zipfile.ZipFile(args.bepinex) as z:
        z.extractall(stage)
    print("· 展开 BepInEx")

    plugins = os.path.join(stage, "BepInEx", "plugins")
    os.makedirs(plugins, exist_ok=True)
    # 补丁自带插件；BepInEx 包里可能附带示例插件，清掉免得干扰
    for junk in os.listdir(plugins):
        p = os.path.join(plugins, junk)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    shutil.copy2(PLUGIN_DLL, os.path.join(plugins, "PunkCn.dll"))
    print("· 放入 PunkCn.dll")

    with open(os.path.join(stage, "changelog.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(CHANGELOG.format(ver=ver, total=total))
    with open(os.path.join(stage, "安装说明.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(README_INSTALL.format(ver=ver))

    # 3) 安全检查：确认只新增、没覆盖游戏本体
    #
    #    注意要排除补丁自己那 5 项 —— 如果这台机器上已经装过补丁，游戏目录里
    #    本来就有它们，直接比对会全部误报（实测会报 23 个）。
    #    真正要拦住的是 Punk_Data\ 这类游戏原始文件被覆盖。
    if os.path.isdir(args.game):
        own = tuple(e.lower() for e in PATCH_ENTRIES)
        game_files = set()
        for dirpath, _, names in os.walk(args.game):
            for n in names:
                rel = os.path.relpath(os.path.join(dirpath, n), args.game).lower()
                if rel.startswith(own):
                    continue          # 补丁自身的文件，不算游戏本体
                game_files.add(rel)
        clash = []
        for dirpath, _, names in os.walk(stage):
            for n in names:
                rel = os.path.relpath(os.path.join(dirpath, n), stage).lower()
                if rel in game_files:
                    clash.append(rel)
        if clash:
            print("× 有 %d 个文件会覆盖游戏本体，必须处理：%s" % (len(clash), clash[:8]))
            return 1
        print("· 安全检查通过：包内 %d 个文件与游戏本体 %d 个原始文件零重名"
              % (sum(len(f) for _, _, f in os.walk(stage)), len(game_files)))

    # 4) 出包
    os.makedirs(DIST, exist_ok=True)
    name = "PUNK-Chinese-Patch-v%s" % ver
    out = os.path.join(DIST, name + ".zip")
    if os.path.exists(out):
        os.remove(out)
    n_files = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dirpath, _, names in os.walk(stage):
            for n in sorted(names):
                full = os.path.join(dirpath, n)
                z.write(full, os.path.relpath(full, stage))
                n_files += 1
    digest = sha256(out)
    with open(out + ".sha256", "w", encoding="ascii") as f:
        f.write("%s  %s\n" % (digest, os.path.basename(out)))

    mb = os.path.getsize(out) / 1024 / 1024
    print()
    print("完成：%s" % os.path.relpath(out, ROOT))
    print("  %d 个文件，%.2f MB" % (n_files, mb))
    print("  SHA256 %s" % digest)
    print("  卸载只需删：%s" % "、".join(PATCH_ENTRIES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
