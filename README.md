# PUNK 汉化补丁

给 Steam 游戏 **PUNK**（试玩版 / Playtest，AppID `2850470`）做的简体中文汉化补丁。

**不修改游戏任何原始文件**，只往游戏目录里新增几个文件；卸载就是把它们删掉。

> 正式版（AppID `2707980`）尚未发售。发售后的版本大概率需要重新对齐文本，见「版本更新后怎么办」。

---

## 安装

1. **关闭游戏**（任务管理器里确认没有 `Punk.exe`）
2. 到 [Releases](../../releases/latest) 下载 `PUNK-Chinese-Patch-v*.zip`
3. 把压缩包里的**所有文件**解压到游戏根目录，覆盖同名文件
   - 游戏根目录 = 里面有 `Punk.exe` 的那个文件夹
   - Steam 上右键游戏 → 管理 → 浏览本地文件，打开的就是它
4. 启动游戏，界面就是中文了

## 卸载

删掉游戏根目录下这 5 项，游戏完全回到原样：

```
BepInEx\              （整个文件夹）
winhttp.dll
doorstop_config.ini
.doorstop_version
changelog.txt
```

## 临时关掉汉化

`BepInEx\config\punk.cn.translation.cfg`：

```ini
[General]
Enabled = false
```

改完重启游戏。字体、翻译表都还在，只是不生效。

---

## 做到什么程度

| 项 | 状态 |
|---|---|
| 界面与物品文案 | **371 / 371 条全部翻译** |
| 文本通道覆盖 | TMP 属性写入 + 资源里序列化的文本，两条都覆盖 |
| 中文像素字体 | 内嵌，12px 像素风，与游戏画面一致 |
| 已实机验证 | 主菜单、设置（玩法/视频/音频）、配装选择 |
| 未实机验证 | 暂停菜单、物品与模块描述 |

### 已知的取舍

- **HUD 资源名保留英文大写**（`CAPS` `ELECTRON` `FUEL` `GEL` `TECH` `STAMINA` `HEALTH` `POWER`）——
  中文会撑宽 HUD，且这几个词在界面上反复出现，保留英文更好认。
- **游戏 LOGO 保持英文 `PUNK`** —— 那是图片，不在文本替换范围内，也不该改。
- **标点沿用原文的半角**（`,` `.` `?`），不换成全角。
- 部分译文宽度比原文略大（配装卡片上的武器名等），已在游戏内逐个核对，不影响阅读。

---

## 从源码构建

需要 .NET SDK（`net472` 目标）与已安装的游戏本体（要引用游戏自带的 DLL）。

```powershell
# 1. 拉代码
git clone https://github.com/wings-of-liberty-zdy/punk-cn-translation.git
cd punk-cn-translation

# 2. 下载 BepInEx（打包用）
#    https://github.com/BepInEx/BepInEx/releases  →  BepInEx_win_x64_5.4.23.5.zip
#    放到 vendor\ 下

# 3. 下载中文像素字体（构建用）
#    https://github.com/TakWolf/fusion-pixel-font/releases
#    取 fusion-pixel-font-12px-proportional-ttf-*.zip 里的 zh_hans 那一份
#    重命名为 plugin\PunkCn\Resources\pixel-cn.ttf

# 4. 编译（游戏装在别处就加 -p:GameDir=...）
dotnet build plugin\PunkCn\PunkCn.csproj -c Release

# 5. 打包
python tools\pack_release.py --version 0.1.0
```

### 仓库结构

```
plugin/PunkCn/           BepInEx 插件源码（C#，net472）
  FontInstaller.cs       运行时建 TMP 中文动态字体资产
  TextPatcher.cs         Harmony 补丁：set_text / SetText 两条通道
  SceneSweep.cs          场景加载后扫描序列化文本
  Table.cs               翻译表加载与归一化
  Resources/             内嵌的翻译表与字体
translations/            翻译表、风格指南、评审页
  punk.tsv               主表（编号 / 原文 / 译文）
  overlay/               人工修正层，按文件名排序覆盖主表
tools/                   构建与校验脚本
  build_table.py         应用 overlay、去重、稳定编号
  validate.py            七类硬检查 + 宽度提示
  review_page.py         生成对照评审页
  pack_release.py        打补丁包
glossary/                术语表与排除名单
docs/                    勘查记录与实机截图
```

---

## 版本更新后怎么办

游戏更新后英文原文可能改动，译文需要重新对齐。本项目的稳定编号机制就是为这个设计的：
**编号不变，原文变了只影响那一条**。

```powershell
python tools\build_table.py --report-only   # 看哪些原文对不上了
python tools\validate.py                    # 七类硬检查
```

---

## 致谢与授权

- **Fusion Pixel 12px** —— 中文像素字体，TakWolf 出品，
  [SIL Open Font License 1.1](https://github.com/TakWolf/fusion-pixel-font/blob/master/LICENSE-OFL)。
  本补丁内嵌其 `zh_hans` 字重，按 OFL 要求保留原始版权声明。
- **BepInEx 5** —— Unity 游戏插件框架，LGPL-2.1。
- 游戏 **PUNK** 的一切版权归其开发者所有。本补丁为爱好者制作，
  **仅供学习交流，请勿用于商业用途**；请先购买正版游戏。
- 本补丁的翻译文本与插件代码以 MIT 授权发布（不含内嵌字体与 BepInEx）。

## 反馈

发现漏译、错译或界面排版问题，请开 [Issue](../../issues)，
附上截图和那句话出现的界面位置。
