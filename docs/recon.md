# PUNK Playtest — 汉化现场勘查

勘查日期：本机实测，只读打开游戏目录，未修改任何文件。

## 1 · 靶子

| 项 | 值 |
|---|---|
| 游戏 | PUNK Playtest |
| Steam appid | 2850470（试玩版；正式版 PUNK 为 2707980，当前未发售，用户库里没有） |
| 安装路径 | `D:\SteamLibrary\steamapps\common\PUNK Playtest` |
| 用户数据 | `C:\Users\houdezaiwu\AppData\LocalLow\DefaultCompany\Punk\` |

## 2 · 引擎与运行时（决定插件宿主选型）

| 项 | 值 | 影响 |
|---|---|---|
| Unity 版本 | **6000.3.4f1**（Unity 6.3） | 很新。BepInEx 5 未必能挂上，需实测；兜底顺序见 §6 |
| 脚本后端 | **Mono**（存在 `MonoBleedingEdge\`，非 IL2CPP） | 好消息：程序集可直接反编译（dnSpy/ILSpy），可 Harmony 打补丁 |
| mscorlib | 4.6.57.0（.NET Framework 4.x profile） | 插件需按 net472/netstandard2.0 编译 |
| 主程序集 | `Punk_Data\Managed\Punk.Main.dll`（898 KB） | 游戏逻辑与文案字段都在这里 |
| 文本渲染 | `Unity.TextMeshPro.dll` + FontAsset `8-bit-hud SDF` | 文本走 TMP，不是烤进贴图的位图字体 |
| 其他 | Steamworks.NET、UniTask、Odin（Sirenix）、AstarPathfinding | — |
| 启动配置 | `Punk_Data\boot.config`、`options.json`（画质/音频/玩法） | `options.json` 里**没有语言字段** |

## 3 · 本地化现状（结论：完全没有）

- `Punk_Data\StreamingAssets\` 只有一个 `UnityServicesProjectConfiguration.json`，**无任何语言文件**。
- 全部 `.assets` / `.resource` 里**没有 JSON/CSV 配置块**（扫描 `"name":` 这类键，命中 0）。
- `Punk.Main.dll` 里搜索 `Localiz` / `Language` / `Translation` / `Locale` / `StringTable` 类型名，**命中 0**。
- 文案是**硬编码**的。已确认的相关符号：
  - `description`、`descriptionText`、`GetDescription()`、`get_Description`
  - `IHasDescriptionForUnit`、`IHasDescriptionForWeapon`
  - `selectedConsumableDescription`、`selectionDescription`
  - `CreateRoomDescriptions`、`GetRoomDescription`、`roomDescriptions`
- DLL 里的字符串绝大多数是开发日志（`Failed to…` / `Could not…` / `not set for`），不是玩家可见文案。
- `Player.log` 里唯一相关行：`Loaded local config from <game>\options.json: {}`

## 4 · 资源清单

| 文件 | 大小 | 备注 |
|---|---|---|
| `resources.resource` | 211.6 MB | 大块二进制（音频/贴图），ASCII 无可用文本 |
| `resources.assets` | 26.4 MB | 主要资源库，含 FontAsset、Sprite 图集、MonoBehaviour |
| `sharedassets0..3.assets` | 3.5 / 0.08 / 0.15 / 4.6 MB | UI 动画、材质、Shader |
| `level0..3` | 0.05–1.28 MB | 场景 |
| `globalgamemanagers*` | 2.06 MB | 含 Unity 版本号、输入轴定义 |

已见 Sprite 图集名：`sactx-0-1024x512-Uncompressed-Atlas UI-*`、`sactx-0-1024x2048-Uncompressed-Atlas Gameplay-*`、`prstartk Atlas`（疑似字体图集）。

## 5 · 用户已确认的决策（grill 阶段）

1. **靶子**：只做 PUNK Playtest，无正式版可迁移。
2. **交付对象**：发布给其他玩家，一键安装补丁包 → 不改游戏本体。
3. **译文来源**：术语表 + AI 初翻 + 人工校对。
4. **字体**：像素中文字体 + 缺字回退黑体；先出 A/B 对比图再定。
5. **范围**：游戏内全部文本；图片贴图里的文字另开阶段。
6. **交付形态**：GitHub 仓库 + Release 补丁包。
7. **语言开关**：v1 装即中文，插件内部留 BepInEx 配置开关，游戏菜单不插行。
8. **风格**：忠于原作的冷硬科幻腔，先出 20 条样张定调。
9. **排期**：碎片时间，先跑通最小闭环再全量。
10. **验收**：脚本全量自检（每条有译文 / 缺字 / 溢出 / 英文残留）+ 游戏内抽查四类界面截图。

## 6 · 未定与风险

- **插件宿主**：Unity 6.3 太新，BepInEx 5 兼容性未知。兜底顺序：BepInEx 5 → BepInEx 6 (bleeding edge, Mono) → MelonLoader → 直接改 `Punk.Main.dll`（放弃"不改本体"）。
- **资源解析**：UnityPy 对 Unity 6.3 的资源格式支持未知；退路 AssetRipper。文本清单勘查正在验证。
- **字体渲染**：TMP 静态图集不含 CJK。方案是运行时用内嵌中文像素字体建**动态 FontAsset 并注册为 fallback**；像素字体走 SDF 会发虚，需调 `samplingPointSize` 与锐度，或改用硬阈值 shader。
- **图片文字**：尚未确认有无烤在贴图里的文字（非本次范围）。
- **SteamDB 拒绝自动化访问**（HTTP 403 + 明示无 API），后续查 Steam 数据只用官方接口。
- **时效性**：试玩版会被正式版替换，整套管线需可重跑。

---

## 7 · 插件宿主验证（2026-10-14 实测，已通过）

**结论：BepInEx 5.4.23.5 在 Unity 6000.3.4f1 (Mono) 上干净挂上，无报错。** 全项目最大风险退场。

- 包：`BepInEx_win_x64_5.4.23.5.zip`（2026-02-08 发布）
  SHA256 `82F9878551030F54657792C0740D9D51A09500EEAE1FBA21106B0C441E6732C4`
- 已备份到 `vendor/BepInEx_win_x64_5.4.23.5.zip`
- 安装方式：解压到游戏根目录。**只新增文件，未改动任何原有文件。**

**新增清单（卸载就是删这 5 项）**

```
BepInEx/                  # core/ config/ cache/ patchers/ plugins/
winhttp.dll               # doorstop 代理
doorstop_config.ini       # enabled = true
.doorstop_version
changelog.txt
```

**`BepInEx/LogOutput.log` 全文**

```
[Message:   BepInEx] BepInEx 5.4.23.5 - Punk (2026/6/4 12:31:39)
[Info   :   BepInEx] Running under Unity v6000.3.4.16634808
[Info   :   BepInEx] CLR runtime version: 4.0.30319.42000
[Info   :   BepInEx] Supports SRE: True
[Info   :   BepInEx] System platform: Bits64, Windows
[Message:   BepInEx] Preloader started
[Info   :   BepInEx] Loaded 1 patcher method from [BepInEx.Preloader 5.4.23.5]
[Info   :   BepInEx] 1 patcher plugin loaded
[Info   :   BepInEx] Patching [UnityEngine.CoreModule] with [BepInEx.Chainloader]
[Message:   BepInEx] Preloader finished
[Message:   BepInEx] Chainloader ready
[Message:   BepInEx] Chainloader started
[Info   :   BepInEx] 0 plugins to load
[Message:   BepInEx] Chainloader startup complete
```

**关键点**

- `Supports SRE: True` ⇒ 可运行时反射发射，Harmony 补丁没问题
- `0Harmony.dll` 已在 `BepInEx/core/`，**不需要另外装 HarmonyX**
- `0 plugins to load` ⇒ 下一步就是写我们自己的插件
- 运行时自动生成：`BepInEx/config/BepInEx.cfg`、`BepInEx/cache/chainloader_typeloader.dat`、
  `BepInEx/cache/harmony_interop_cache.dat`

**排除干扰项（重要）**

`Player.log` 里有一条 `NullReferenceException at MusicTrackActivator.Awake()`。
对照 `Player-prev.log`（2026-07-02，**装 BepInEx 之前**的那次运行）⇒ **同一个异常也在**，
是游戏自带的老 bug，不是插件引入的。对照组那次有 85+ 个空引用（玩过一段），
本次仅 1 个（只到主菜单），量级也合理。

**构建工具链**

- `dotnet` SDK **9.0.203** 在 PATH（`C:\Program Files\dotnet`），Visual Studio 2022 已装
- 插件目标框架用 `net472`（游戏 CLR 是 4.0.30319.42000）
- 引用 `BepInEx/core/BepInEx.dll`、`0Harmony.dll`，以及游戏自己的
  `Punk_Data/Managed/UnityEngine.CoreModule.dll`、`Unity.TextMeshPro.dll`

**启动游戏的方式**

驱动后台最小化启动会被拒（拿不到前台锁）。可行做法：
`Start-Process -FilePath <游戏>\Punk.exe -WorkingDirectory <游戏> -WindowStyle Minimized -PassThru`
最小化也能完成 Unity 与 BepInEx 的初始化。
⚠️ **关闭要注意**：PostMessage 发 Alt+F4 对 Unity **无效**（进程不退出），需要 `taskkill /F`。

---

## 8 · 最小闭环第 2 步：中文上屏（2026-10-14 实测，已通过）

**结论：游戏主菜单已经显示中文。** 证据 `docs/shots/02-after-font-fix.png`。

### 8.1 文本替换（通过）

- 只拦 `TMP_Text.set_text`（Harmony Prefix），不拦 getter。
- 资源里序列化的文本不走 setter ⇒ 场景加载后再扫一遍（`SceneSweep`），1.5 秒后补扫一次。
- 实测：`MainMenu 扫描 159 处 TMP 文本，改写 15 处`（表里只有 32 条，其余是表外的串，正常）。

### 8.2 字体（通过，但路走对了才知道有多窄）

**决定性的对照实验**（一次跑清）：

```
探针 字节流 size 12/24/48/90            -> Success      ← 唯一可用的通道
探针 OS字体 'Microsoft YaHei'           -> Invalid_File_Structure
探针 OS字体 'Arial'                     -> Invalid_File_Structure
```

⇒ **Unity 6000.3.4 的 OS 字体通道是坏的**：`FontEngine.LoadFontFace(Font, int)` 对
`Font.CreateDynamicFontFromOSFont()` 造出来的 Font 一律返回 `Invalid_File_Structure`，
连系统自带的微软雅黑和 Arial 都不行。
所以「内嵌 TTF → `AddFontResourceEx` 私有注册 → 按族名取 Font」这条路**在这版 Unity 上不通**。

**可用路径：字节流**

```csharp
FontEngine.LoadFontFace(ttfBytes, 36);                 // 36 = 字体原生 12px 的 3 倍
var fa = ScriptableObject.CreateInstance<TMP_FontAsset>();
SetField(fa, "m_FaceInfo", FontEngine.GetFaceInfo());   // 私有字段，反射写
SetField(fa, "m_SourceFontFilePath", tempTtfPath);      // TMP 补字形时要按路径重载源文件
InitAtlasState(fa, 1024, 1024);                         // ★ 关键，见下
fa.ReadFontAssetDefinition();
fa.TryAddCharacters("按任意键开始", out missing);        // 必须返回 True 且 missing 为空
TMP_Settings.fallbackFontAssets.Add(fa);
foreach (var f in Resources.FindObjectsOfTypeAll<TMP_FontAsset>())
    f.fallbackFontAssetTable.Add(fa);                   // 逐字体也挂一遍
```

**★ 唯一的坑，也是最难找的一个**：
`ScriptableObject.CreateInstance<TMP_FontAsset>()` **不会触发 `OnEnable`**，
而 TMP 正是在 `OnEnable` 里初始化图集空闲矩形（`m_UsedGlyphRects` / `m_FreeGlyphRects`）
和字形查找表。缺了它们，`TryAddCharacters` 会在 TMP 内部抛
`NullReferenceException ... at TMPro.TMP_FontAsset.TryAddCharacters [0x00239]`，
**且没有任何提示指向缺哪个字段**。手工把这几个集合建出来即解决：

```csharp
SetField(fa, "m_AtlasTextureIndex", 0);
SetField(fa, "m_UsedGlyphRects", new List<GlyphRect>());
SetField(fa, "m_FreeGlyphRects", new List<GlyphRect> { new GlyphRect(0, 0, W - 1, H - 1) });
SetField(fa, "m_GlyphTable", new List<Glyph>());
SetField(fa, "m_CharacterTable", new List<TMP_Character>());
SetField(fa, "m_FallbackFontAssetTable", new List<TMP_FontAsset>());
```
（`TMP_FontAsset` 上没有可反射调用的 `OnEnable` / `Awake` 方法，别指望调它。）

另外这些属性在这版 TMP 里是**只读**的，只能反射写私有字段：
`atlasWidth` / `atlasHeight` / `atlasPadding` / `atlasRenderMode` / `faceInfo`。
`atlasTextures` 与 `material` 是可写的。

### 8.3 字体选型（GB2312 全集实测）

| 字体 | 汉字数 | GB2312 缺字 | 文件 | 结论 |
|---|---|---|---|---|
| Ark Pixel 12px zh-Hans | 18,299 | **484（7.16%）** | 1.11 MB | 缺 `班搬餐概既紧警` 这类常用字，不可用 |
| Fusion Pixel 12px zh-Hans | 19,219 | 143（2.11%） | 1.60 MB | 缺的都是 `鼗赝衮脔` 这类生僻字，可用 |
| **Zpix 12px** | **20,902** | **0（0.00%）** | 4.46 MB | 覆盖整个 U+4E00–9FFF，**已选用** |

- Zpix 是普通轮廓 TTF（无 `EBDT/EBLC` 位图表），族名 `Zpix`，unitsPerEm 1200，22,241 字形。
- 授权：Ark / Fusion 是 OFL-1.1（包内带 `OFL.txt`）；Zpix 需单独确认授权条款后再发布。
- 采样 36px（原生 12px 的 3 倍）实测字形锐利，与游戏 8-bit HUD 风格一致。

### 8.4 干扰项排除（两次都靠对照组）

1. `MusicTrackActivator.Awake()` 空引用 ⇒ `Player-prev.log` 里也有，游戏自带。
2. `UiManager.Pop()` / `DefaultSelector.OnDisable()` 空引用 ⇒ `Player-prev.log` 里命中 2 处，游戏自带。
3. 第一次截图里中文显示成一排 □ ⇒ **不是崩溃，是缺字形**：资产建出来了但补不进图集（见 8.2）。

### 8.5 工具链踩坑

- `dotnet` 构建 Unity 插件必须引用 `UnityEngine.dll`（门面）**和** `UnityEngine.UI.dll`，
  否则 `MonoBehaviour` / `MaskableGraphic` 报 CS0012。
- **`EmbeddedResource` 的 `Condition="Exists('相对路径')"` 不解析到项目目录** ⇒
  字体静默没嵌进去、插件只有 17 KB。**去掉条件，让缺字体时构建失败**。
- **改 DLL 前必须先关游戏**，否则 `Copy-Item` 报
  `cannot be performed on a file with a user-mapped section open`，
  而且你会以为新代码生效了、实际读的是旧日志。
- 本机 PIL/Pillow 的 FreeType 对**任何**字体都崩（`0xC0000005`，连微软雅黑都崩）⇒
  **不要用 PIL 验证字体文件**，用 fontTools。

---

## 9 · 行距 bug：多行文本叠在一起（2026-10-14 已修）

**用户报告**：游戏最开始那一屏，有两个两行的句子叠在一起，行间距不对。

### 9.1 根因：行盒度量没对齐游戏主字体

游戏主字体 `8-bit-hud SDF` 的行盒**特别高**：

| 字段 | 值 | 折合 em（pointSize 38） |
|---|---|---|
| `m_PointSize` | 38.0 | — |
| `m_LineHeight` | **60.78515625** | **1.600** |
| `m_AscentLine` | 53.1962890625 | 1.400 |
| `m_DescentLine` | -7.5888671875 | -0.200 |
| `m_CapLine` | 46.0 | 1.211 |
| `m_MeanLine` | 38.0 | 1.000 |
| `m_TabWidth` | 23.0 | 0.605 |

（`lineHeight` 正好 = `ascentLine - descentLine` = 60.785。）

**Zpix 自带的行高只有约 1.0 em**（unitsPerEm 1200 的 hhea 度量）。
直接用它的度量，多行文本的行距会少约 **37%** ⇒ **行与行叠在一起**。
对照其他字体也能看出游戏主字体有多特殊：
`LiberationSans SDF` 1.150、`prstartk SDF` 1.000、`Font_Minimum` 0.943。

### 9.2 修法：把行盒度量按比例搬过来

`FontInstaller.MatchGameLineMetrics()` —— 上面每个常数按 `pointSize / 38` 缩放后写进
`FaceInfo`（`FaceInfo` 是 `UnityEngine.TextCore` 里的结构体，字段可直接赋值）。

实测日志：
```
行盒对齐游戏字体: pointSize=36 lineHeight=57.58594 ascent=50.39648 descent=-7.189453（原字体比例 1.6）
```
比例核对：游戏 60.785/38 = **1.5996**，我们 57.586/36 = **1.5996** ✓ 完全一致。

### 9.3 验证

- 数值：日志里的比例与游戏字体逐位一致（见上）
- 画面：配装选择界面的两行标题 `选择 / 配装`（原文 `Select\nloadout`）行距正常、不重叠
  （`data/dump/input_selector.png`）
- ⚠️ 用户报的那一屏（启动时的欢迎信）**抓不到截图** —— 它在窗口可见之前就过去了
  （日志显示 `Splash Info` 场景确实加载过并改写了 18 处文本）。
  需要用户重启游戏时肉眼确认一次。

### 9.4 教训

**换字体不只是换字形，还要搬行盒度量。** 中文汉化最容易漏这一步，
症状就是「行距不对 / 行叠在一起」，而且只在多行文本上出现、单行文本完全正常。
做法：从游戏主字体的 `m_FaceInfo` 逐字段量出比例，按自己的 pointSize 缩放后写进去。

---

## 10 · 字面大小：不同字体资产差 3 倍（2026-10-14 已修）

### 10.1 症状（用户报告）

配装界面的 `返回` 比原版 `BACK` **大一倍多、下沿溢出按钮框**（"有点靠下"）；
而配装卡片的武器名 `霰弹枪` 又**偏小**。同一屏上两个方向相反的问题。

### 10.2 根因：游戏有 4 个字体资产，字面高占字号的比例差 3 倍

| 字体资产 | pointSize | 用在哪 |
|---|---|---|
| `8-bit-hud SDF` | 38 | 设置项、模块名、武器名 |
| `Font_Minimum` | 50 | **主菜单按钮、配装界面的 BACK/Restart** |
| `LiberationSans SDF` | 86 | 调试菜单 |
| `prstartk SDF` | 90 | 少量 |

TMP 的字形缩放是 `fontSize / faceInfo.pointSize × faceInfo.scale`。
我们一开始只建了**一个 pointSize=36 的资产**，于是：
原来用 50 的元素被按 36 算 → 撑大；走回退链的元素被按原字体的 pointSize 缩放 → 偏小。

**⚠️ 但 `capLine / pointSize` 不能用来推算字面高** —— 这些资产的 `m_UnitsPerEM` 是 0，
那套比例是虚的（`8-bit-hud SDF` 的 capLine/pointSize = 1.21，真实字体不可能有 1.21 em 的
字母高度）。**只能用同元素实测。**

### 10.3 实测数据（同一个元素、同一个 fontSize，原版 vs 我们）

| 元素 | 原版 | 修复前 | 修复后 | 目标系数 |
|---|---|---|---|---|
| 配装界面 `BACK` / `返回` | 9px | **24px** | 12px | 0.47 |
| 配装卡片标题 `GUNNER` / `枪手` | 11px | **29px** | 15px | 0.47 |
| 配装卡片武器名 `POPPER` / `霰弹枪` | 9px | 8px | 8px | 1.13 |
| 两行标题块高度（行距） | 42px | — | 45px | — |

### 10.4 修法

1. **按原字体的 pointSize 分别建资产**（`FontInstaller.GetFor(pointSize)` 带缓存），
   `TextPatcher` 里读 `t.font.faceInfo.pointSize` 决定用哪个。
2. **每个源字体带一个实测的 `scale` 修正**（`SrcByPoint` 表）：
   `faceInfo.scale` 是 TMP 的乘数（实测有效），用它把字面高对齐原字体。
   行盒按 `lineHeight = 源行高em × pointSize / scale` 换算，保证
   `行距 = lineHeight × fontSize/pointSize × scale = 源行高em × fontSize` 与原文一致。
3. 补挂 `TMP_Text.SetText(string)` / `SetText(string, bool)` —— 这族方法
   **直接写 m_text 字段、不走 text 属性 setter**，原来的补丁拦不到。

### 10.5 ★ 教训

- **「按字体资产一刀切」是错的。** 主菜单按钮和配装界面的 BACK 用同一个资产，
  却需要相反的缩放方向 —— 必须按元素实测。
- **推算不如实测。** 我先按 `capLine/pointSize` 推算，得出 Font_Minimum 要 ×0.349，
  结果主菜单被压得过小；改成同元素实测的 ×0.47 才对。资产里的比例字段在
  `m_UnitsPerEM=0` 时不可信。
- **`faceInfo.scale` 是有效的调节杠杆**，但会同时影响行距，必须按
  `lineHeight = 源行高em × pointSize / scale` 反向补偿。
- 剩余偏差：BACK 12px vs 原版 9px（约 1.33 倍），可再把 scale 调到 0.40 逼近，
  但继续调有过冲风险，先停在这里。




