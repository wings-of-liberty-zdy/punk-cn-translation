# 汉化范围 · 三个未决问题核查

任务性质：**只读核查**。`D:\SteamLibrary` 全程未写入（所有脚本只 `open(..., "rb")` / UnityPy 读取）。
产出脚本：`scripts/q1_*.py`、`scripts/q2_*.py`、`scripts/q3_*.py`、`scripts/q_il.py`、`scripts/q_ldstr_ctx.py`
中间产物：`data/dump/q1_*`、`data/dump/q2_*`、`data/dump/q3_*`

环境（本次实测）：
- `C:\Users\houdezaiwu\anaconda3\python.exe` 3.12.4；UnityPy 1.25.4；TypeTreeGeneratorAPI 0.0.10；**dnfile 已装**（无需再 pip）
- `dotnet 9.0.203` 存在，但 `dotnet tool install -g ilspycmd` **失败**（NuGet 包内缺 `DotnetToolSettings.xml`）。因此全部静态分析改用自写的 dnfile + IL 解码器。

---

## 方法可靠性声明（先读这一段）

本次自写的 IL 解码器（ECMA-335 操作码表 + 完整 TypeDef→MethodDef 归属映射）在本程序集上：

```
#US entries: 508
methods decoded: 5623   decode_failed: 0
```

**5623 个方法体全部解码成功，0 失败**。这是"IL 层结论可信"的核心依据——如果操作码表有错，字节流会在某处失步，必然出现大量 decode 失败或方法尾不是 `ret`。因此下文所有"某方法调用了某成员""某方法里有某 ldstr"的陈述都是精确的，不是盲扫 `0x72` 字节得到的近似。

已知并已规避的坑（任务里点名的那条）：本程序集 `#US` blob **没有前导 flag 字节**，压缩长度已含结尾 `0x00`。`scripts/q1_dll_scan.py::read_us_heap()` 按"去掉结尾 0x00 → 补齐偶数字节 → UTF-16LE 解码"处理，与前期 `10_dll_strings.py` 的结论一致，508 条与前期 507 条（去 1 条空串）吻合。

---

# 问题 1：商店文案是不是来自远程 Google 表格？

## 结论：**B —— 运行时完全不读这个 URL。商店数据 100% 来自本地已烘焙的资产数据。**

不是 C（无法确定）。证据链是闭合的，四层独立证据互相印证。

## 证据 1：那个 URL 在 `Punk.Main.dll` 里**根本不存在**

对整个游戏安装目录做原始字节扫描（ASCII + UTF-16LE 双编码，243 个文件、425 MB）：

| 文件 | 命中的 needle | 偏移 |
|---|---|---|
| `Punk_Data\resources.assets` | `docs.google.com` | 26,270,236 |
| `Punk_Data\resources.assets` | `2PACX-1vTF4s2BdJrSSrwYgrHgye7QD...` | 26,270,269 |
| `Punk_Data\resources.assets` | `output=csv` | 26,270,378 |
| `Punk_Data\Managed\Punk.Main.dll` | `get_daily_seed`（UTF-16LE） | 840,613 |

**Google 表格 URL 全盘只出现一次，且只在 `resources.assets` 里**，就是 `ShopItemsConfig`(pid 23103) 的 `url` 字段。它**不在** `Punk.Main.dll` 的 `#US` 或 `#Strings` 堆中——所以汇编里不可能有 `ldstr` 出这个 URL 的代码。这是决定性的：**不是"没找到调用点"，而是"这个字符串压根不在可执行代码里"**。

（脚本：`scripts/q1_rawgrep.py` → `data/dump/q1_rawgrep.txt`）

## 证据 2：全汇编的联网调用点只有 2 处，都不碰这个 URL

对 5623 个方法体做完整调用点枚举（脚本 `scripts/q1_dll_scan.py` → `data/dump/q1_dll_scan.txt`）：

**`get_url` / `set_url` / 任何 `url` 成员的调用：0 次。** 全汇编唯一被触碰的 `url` 成员是 `BugReporter::forumWebhookUrl`（Discord 上报）。

`UnityWebRequest` / `DownloadHandler` / `WWW` / `HttpClient` / `WebClient` 相关调用点，**全汇编只有 2 个方法**：

| 方法 | 用途 | 目标 |
|---|---|---|
| `<GetLatestData>d__5::MoveNext` | 每日种子 | `https://www.powernapgames.com/api/get_daily_seed.php` |
| `<Report>d__2::MoveNext` | Bug 上报 | `DiscordWebhook` 库 → `discord.com/api/webhooks/...` |

全汇编含 `http` / `.csv` / `sheet` 的字面量**只有 4 条**：Discord 邀请链接、Steam 商店页、每日种子 API、Discord webhook URL。**没有任何 `.csv`、没有任何 `spreadsheets`。**

## 证据 3：`ShopItemsConfig::Parse` 存在，但它是死代码，且它不读 `url`

`ShopItemsConfig` 在运行时汇编里确实有一个 CSV 解析器。IL 反汇编（`scripts/q_il.py` → `data/dump/q2_il_dump.txt`）：

```
ShopItemsConfig::Parse   (1 overload)   ← 实例方法，1 个参数 System.String
  IL_0000: ldarg.0;  ldfld resourceRegistry;   callvirt Initialize
  IL_000B: ldarg.0;  ldfld ingredientRegistry; callvirt Initialize
  IL_0016: ldarg.0;  ldfld moduleRegistry;     callvirt Initialize
  IL_0021: ldarg.0;  ldfld consumableRegistry; callvirt Initialize
  IL_002C: ldarg.0;  ldfld itemList;           callvirt Clear
  IL_0037: ldarg.1                                   ← 参数就是 CSV 正文
  IL_0038: ldc.i4.1; newarr System.String; dup; ldc.i4.0
  IL_0040: call System.Environment::get_NewLine; stelem.ref
  IL_0047: callvirt System.String::Split             ← 按换行切行
  IL_0051: call ShopItemsConfig::ParseCurrencyOrder  ← 第 1 行 = 货币列顺序
  IL_005F: call ShopItemsConfig::ParseLine           ← 第 2 行起 = 逐行解析
```

**关键点：`Parse` 全程没有 `ldfld url`。** 它拿的是**外部传进来的 CSV 文本**，不是 URL。字段名 `url` 只出现在资产里，代码里从未被读。

**并且：全汇编没有任何方法调用 `ShopItemsConfig::Parse`。** 调用点枚举显示 `Parse` 只被自己内部调用（`Parse` → `ParseCurrencyOrder` / `ParseLine`）。它是编辑器期导入器被编译进运行时汇编后留下的**死代码**（`UnityEditor` 引用数为 0，说明编辑器脚本本身已被剥离，只剩这个方法体）。

同一模式还出现在 `DamageMatrixConfig::Parse` / `ParseCurrencyOrder` / `ParseLine`——说明这是项目里"设计期用 Google 表格 → 编辑器导入器 → 烘焙进资产"的统一工作流。

## 证据 4：本地资产数据是**满的**，且带 `lineNumber`（表格行号的指纹）

`ShopItemsConfig`(pid 23103) 的 `itemList`：**62 条**，每条结构完整：

```json
{ "id": "e070f3d8-c876-440d-a66e-7e9d8fd8b6ca",
  "lineNumber": 3,
  "price":         [ {currencyType, ingredient→PPtr, resource→PPtr, amount}, ... ],
  "priceIncrement":[ ... ],
  "unlockRequirements": [ PPtr→23123 ] }
```

- **没有物品名、没有描述** —— 只有 GUID、价格、解锁条件、指向 ingredient/resource 的 PPtr。
- `lineNumber` 字段（3、4、6、7 …）就是**源表格里的行号**。这是"表格是设计期录入面、`itemList` 是烘焙产物"的直接指纹。
- 四个 registry 也都是满的：`moduleRegistry`(pid 23478) 145 条、`ingredientRegistry`(23125) 9 条、`resourceRegistry`(23540) 8 条、`consumableRegistry`(23108) 4 条。
- 运行时消费路径走本地数据：`RunData::AddShopItemsWhereRequirementsMet` 读 `ShopItemsConfig.AllItems`，`RunData::Initialize` → `RunData::CreateShopItem` → `ShopItem::CreateNew`。

## 那个 CSV 我没抓到 —— 这是本次唯一的外部限制

`web_fetch` 被策略拒绝：`URL hostname "docs.google.com" resolves to a non-public IP address`。
Python `requests` / `urllib` 直连也失败。**DNS 被劫持**：

```
docs.google.com -> ['2001::1', '31.13.112.9']     ← 31.13.112.9 属于 Facebook 的 IP 段
requests: ConnectTimeout (30s)
urllib:   URLError(TimeoutError(10060, '连接尝试失败'))
```

**所以我无法报告"CSV 有哪些列、多少行、有没有物品名与描述"。** 需要用户自己开代理/换网络抓一次（只读一次即可）：

```
https://docs.google.com/spreadsheets/d/e/2PACX-1vTF4s2BdJrSSrwYgrHgye7QDmyF4y73XqnxG1nCCuxnGiHK_Zxo4Q1EFsrvoDoWaEMNsqgRmzK0gaqm/pub?gid=0&single=true&output=csv
```

**但这不影响问题 1 的结论。** 结论 B 只依赖"运行时读不读它"，而这一点已由证据 1–4 闭合。CSV 的内容只影响**问题 1 的附带价值**：如果表里有物品名/描述，那它可作为**汉化对照参考**（设计期文案的英文原文），而不是运行时数据源。

## 对汉化范围的含义

- 商店/物品的**名称与描述**不在 `ShopItemsConfig` 里，也不在这个 CSV 的运行时路径上。它们来自各 `*Data` 资产的 `displayName` / `description` 字段（见问题 2 的代码链）。
- **不需要**为这个 URL 做任何本地化/镜像/拦截处理。
- 如果之后要改商店文案，改的是 `resources.assets` 里各 `ModuleData`/`Consumable`/`Resource` 实例的字段，**不是** Google 表格。

---

# 问题 2：`WeaponModuleData.displayName` 里哪些是内部资产名？

## 结论：**38 条内部名（不该翻） / 22 条玩家可见（该翻） / 0 条无法判断**

判据不是猜的，是**代码链 + 引用图**双重锁定。

## 数据规模（实测）

| 项 | 数量 |
|---|---|
| `resources.assets` 里 `WeaponModuleData` 实例 | **60** |
| `displayName` 去重后 | **53**（6 个名字有重复实例） |
| `icon` 为空（`m_PathID: 0`）→ 内部名 | **38** |
| `icon` 非空 → 玩家可见 | **22** |

重复的 6 个名字：`Weapon CrossPin`、`Weapon Rocket Soldier`、`Weapon_Turret_Laser`、`Weapon FloaterMiniCaps`、`Weapon_Fly_Alfa`、`Weapon_CrossRed`
（每个名字对应多个不同 pid 的实例，是敌人不同变体共用同一武器资产。）

## 证据 1：代码链证明 `displayName` 确实被赋给 TMP `m_text`

IL 反汇编（`data/dump/q2_il_dump.txt`）：

```
Module::get_DisplayName          ← 直接返回 Data 的 displayName 字段
  IL_0000: ldarg.0; call Module::get_Data; ldfld field displayName; ret

LoadoutModuleItem::Display(Module m)          ← 路径 A
  IL_0007: callvirt Module::get_DisplayName
  IL_000C: callvirt TMPro.TMP_Text::set_text   ← ★ 赋给 TMP m_text

ShopItemWidget::Setup(ShopItem item, ...)     ← 路径 B
  IL_0055: callvirt ShopItem::get_Name
  IL_005A: callvirt TMPro.TMP_Text::set_text   ← ★ 赋给 TMP m_text
ShopItem::get_Name
  IL_0000: call ShopItem::get_Module; call Module::get_DisplayName; ret
```

所以 `WeaponModuleData.displayName → Module.get_DisplayName → TMP_Text.set_text` 是**已证实的赋值链**，不是推测。

## 证据 2：60 个实例按 `icon` 分成两组，引用方完全不同

对 `resources.assets` 全部 MonoBehaviour 做 PPtr 反向引用扫描（`scripts/q2_weaponmodule.py` → `data/dump/q2_weaponmodule_instances.json`）：

| 引用方类 | icon=null 组（38 条） | icon≠null 组（22 条） |
|---|---|---|
| `ModuleRegistry` | 38 | 22 |
| **`Enemy`**（`.primaryWeapon` / `.embeddedModule`） | **34** | 0 |
| `DropTableWeightedGroup`（掉落表） | 0 | 17 |
| **`ShopItemGroup`**（商店模块池 `.moduleDistribution`） | **0** | **14** |
| **`LoadoutTemplate`**（玩家飞船配装预设 `.primary`/`.secondary`） | **0** | **9** |

**分离是完美的**：38 条只被敌人 AI 武器槽和注册表引用，**从不**出现在商店池或玩家配装模板里；22 条只出现在掉落表/商店池/配装模板。

## 证据 3：`icon` 的语义 —— 但不完全是代码闸门（这点要说清）

```
ModuleData::get_Equippable
  IL_0001: ldfld field icon
  IL_0007: call UnityEngine.Object::op_Inequality   ← icon != null
  IL_000C: brfalse.s → return false
  IL_000F: ldfld field displayName
  IL_0014: call System.String::IsNullOrEmpty
  IL_001A: ldc.i4.0; ceq; ret                        ← && !IsNullOrEmpty(displayName)
```

即 `Equippable == (icon != null && !string.IsNullOrEmpty(displayName))`，与"icon 为空 = 不可装备"一致。

**但必须诚实标注**：全汇编里 `get_Equippable` **只被 `DebugMenu::AddAllModuleToVault` 调用**（1 处）。所以 `Equippable` 并不是商店的代码闸门，它只是与分组完美相关的标志位。**真正的玩家可见性闸门是证据 2 的引用图**（`ShopItemGroup` / `LoadoutTemplate` 成员资格）。两条独立证据指向同一划分，这才是结论可靠的原因。

## 证据 4：敌人武器的 displayName 只流向 Dev 菜单

38 条内部名的 `displayName` 唯一能到达 TMP 的路径是调试菜单：

```
SpawnModulePickupButton::set_Module
  IL_000E: ldfld field module
  IL_0013: ldfld field displayName
  IL_0018: callvirt TMPro.TMP_Text::set_text    ← 但这是 DebugMenu 的生成按钮
DebugMenu::SpawnModulePickup                     ← 开发者生成物品用
```

`Enemy` 持有的是 `WeaponModuleData` 的 PPtr 作为**武器槽引用**，不经过 `Module::get_DisplayName`，所以敌人武器的名字不进玩家 UI。

## 证据 5：这 60 个名字没有一个被烘焙进资产文本

拿 60 个 `displayName` 去比对 `data/dump/ui_text_paths.json`（788 条层级路径）和全量资产 TMP `m_text`（205 个去重值）：

```
in ui_text_paths: []
in asset m_text : []
```

全部为空 —— 与"运行时由 `set_text` 动态写入"一致，也说明**不能**用"资产里有没有这段文字"来判断可见性（任务里建议的这条判据在这批数据上无效，我改用引用图 + 代码链）。

## 清单

### 玩家可见 —— 22 条，**应该翻译**

`FLAME`、`LASER`、`LOON`、`FIRE MISSILE`、`Electron Missile`、`TOROID`、`ZAPPER`、`CAN`、`CLUSTER CUBE`、`FLACK`、`MARBLES`、`GEL MISSILE`、`SHARD`、`DANDELION`、`BLADES`、`BOLT`、`DART`、`DEBRIS`、`DISC GUN`、`POPPER`、`SHOTGUN`、`WORM`

pid 23496–23517。全部 `icon` 非空，出现在 `ShopItemGroup` / `LoadoutTemplate`。
注意 `Electron Missile` 是**混合大小写**（其余多为全大写），风格上是个例外，翻译时可统一。

### 内部名 —— 38 条，**不该翻**

pid 23423–23460：`Weapon_Fly`、`Weapon CrossPin`(×2)、`Weapon Drone`、`Weapon Enemy DroneMissile`、`Weapon Enemy Queen Bomb`、`Weapon Enemy Drone Sniper`、`Weapon Fish`、`Weapon Laser CrossTablet`、`Weapon Minion CrossRed`、`Weapon Rocket Rookie`、`Weapon Rocket Soldier`(×3)、`Weapon Rocket TurretSeeker`、`Weapon_Turret_Laser`(×2)、`Weapon_Bouncer`、`Crawler Laser`、`Weapon FloaterMiniCaps`(×2)、`Weapon_Fly_Alfa`(×2)、`Weapon_Cross`、`Weapon_CrossAlpha`、`Weapon_CrossLaser`、`Weapon_CrossQueen`、`Weapon_CrossRed`(×2)、`Weapon_Fly_Dad`、`Weapon_Fly_Laser`、`Weapon_Grunt`、`Weapon_Laser_CrossQueen`、`Weapon_Minion_CrossQueen`、`Weapon_PhantomDrone`、`Weapon_Raven`、`Weapon_Turret_Worm`、`Weapon_Zipper`

`icon` 全为空，只被 `Enemy` 与 `ModuleRegistry` 引用。

### 无法判断 —— 0 条

两组之间没有灰色地带。若将来敌人武器要显示给玩家（例如"敌方情报/图鉴"功能），这 38 条才需要重新评估。

### 两个需要注意的边界情况

1. **`Weapon Rocket Soldier` / `Weapon CrossPin` 等重复名**：同一 `displayName` 对应多个 pid。翻译时按**文本**建表即可，不必按 pid。
2. **`Crawler Laser` 与 `Weapon FloaterMiniCaps`**：命名风格与其余 `Weapon_*` 不同（无下划线、有空格），但引用图证明它们与其它 36 条同类（icon=null、只被 Enemy 引用）。**风格不是判据，引用图才是。**

---

# 问题 3：被丢弃的 DLL 字面量里有没有真 UI 文案？

## 结论：**有。约 28 条应该捞回来**，其中 **7 条是一个系统性漏检**（整个加载界面步骤文案组）。

前期分类：507 条 DLL 字面量 → keep 78 / reject 429。丢弃理由分布：

| 理由 | 条数 |
|---|---|
| `identifier / file name / shader property` | 195 |
| **`unattributed DLL literal - no UI shape (default reject)`** | **104** |
| `dev log / exception / diagnostic` | 102 |
| `format specifier / punctuation only` | 26 |
| `empty` | 2 |

**根因已定位**：前期的 `attribution` 里 class 名是空的（`10_dll_strings.py` 用 `m.class_` 取归属，但 dnfile 的 `MethodDefRow` **没有** `class_` 列——归属必须由 `TypeDef.MethodList` 范围推导）。所以 `ctx` 全是 `unattributed`，104 条因此被"默认拒绝"，另有大量字符串的 DEVLOG 正则判定也缺少方法上下文。本次已修正归属（5623/5623 解码成功）。

## 判定规则（写在脚本里，可复核）

一条被丢弃的字面量算"应捞回"，需**同时**满足：
- **内容可译**：至少一个 ≥3 字母的英文单词，且不是 URL / 文件名 / `PREF_KEY` 常量 / camelCase 标识符 / 纯标记或纯格式串；
- **且**至少满足一条：
  - **R1**：`ldstr` 它的方法**直接调用** `TMP_Text::set_text` / `UI.Text::set_text` / `ShipLogOutput::Log`
  - **R2**：**同一个方法里**另有字面量在人工白名单里（同一方法、同一返回路径 ⇒ 同一 UI 出口）
  - **R3**（仅作参考，不计入捞回数）：它的方法被一个含文本出口的方法调用

R3 单独列出是因为它**噪音极大**：`Ship::Update`、`DebugMenu::Update`、`GameController::ShowLogForKilledBosses` 是调用图的超级枢纽，深度 3–4 的 BFS 会把几乎所有 dev 字符串都"连"到 UI 上。**R3 单独命中 224 条，我没把它们算作捞回。**

## 捞回清单

### A. R1 直接命中（12 条命中，其中 9 条是真 UI 文案）

| 字面量 | 调用点 | 出口 | 判定 |
|---|---|---|---|
| `'Generated in {0}'` | `LoadingScreen::OnLevelGenerated` | `TMP_Text::set_text` | ✅ 捞回 |
| `'DONE in {0:n2} sec\n'` | `LoadingScreen::UpdateText` | `TMP_Text::set_text` | ✅ 捞回 |
| `'Consumable item'` | `ConsumableInfoPopup::Show` | `TMP_Text::set_text` | ✅ 捞回 |
| `'EMPTY'` | `ConsumableWheel::Update` | `TMP_Text::set_text` | ✅ 捞回 |
| `'LOAD '` | `LoadLoadoutButton::set_Loadout` | `TMP_Text::set_text` | ✅ 捞回 |
| `'Hold '` | `Ship::Update` | `ShipLogOutput::Log` | ✅ 捞回 |
| `'Space'` | `Ship::Update` | `ShipLogOutput::Log` | ✅ 捞回 |
| `' to self-destruct'` | `Ship::Update` | `ShipLogOutput::Log` | ✅ 捞回 |
| `' added'` | `ConsumablePickup::OnPickedUp`、`IngredientPickup::OnPickedUp` | `ShipLogOutput::Log` | ✅ 捞回 |
| `'MapControl'` | `ShipMenuToggler::Open` | `TMP_Text::set_text` | ⚠️ 待定（同方法共现，但更像 InputActionMap 名） |
| `'<color=#'` | `ModulePickup::OnPickedUp` | `ShipLogOutput::Log` | ❌ 富文本片段，非文案 |
| `'yyyy - MM - dd'` | `LeaderboardComponent::Reload` | `TMP_Text::set_text` | ❌ 日期格式串，非文案 |

**注意 `'Hold '` / `'Space'` / `' to self-destruct'` 是一句 UI 提示的碎片**（"Hold [Space] to self-destruct"）。中文语序不同，**碎片必须整句重组，不能逐片段替换**——这是这次捞回里最需要注意的工程点。同类还有下面的 `'Adds '` / `' shield'`。

### B. R2 同方法兄弟证据（24 条命中，其中 5 条可信）

**最有力的一条**——同一个 `switch` 的返回值：

```
ModuleGridWidget::GetErrorMessage
  IL_0023: ldstr 'Incompatible slot'            ← keep（人工白名单）
  IL_002B: ldstr 'Incompatible connections'     ← keep
  IL_0033: ldstr 'Clusters cannot be connected' ← reject（被 DEVLOG 正则的 "cannot" 误杀）
  IL_003B: ldstr 'Clusters cannot overlap'      ← reject（同上）
  IL_0043: ldstr 'Incompatible augmentation'    ← keep
  IL_004B: ldstr 'Unknown error'                ← keep
  IL_0051: ldloc.0; ret                         ← 同一个返回值，同一个 UI 出口
```

调用方：`ModuleGridWidget::CanMoveTo` → `ShipLogOutput::Log`。**4 个兄弟已人工确认是玩家可见，这 2 个走同一返回路径 ⇒ 必然也是。**

| 字面量 | 调用点 | 兄弟证据 | 判定 |
|---|---|---|---|
| `'Clusters cannot be connected'` | `ModuleGridWidget::GetErrorMessage` | 4 个 keep 兄弟同 switch | ✅ 捞回 |
| `'Clusters cannot overlap'` | `ModuleGridWidget::GetErrorMessage` | 同上 | ✅ 捞回 |
| `'Adds '` | `AddShieldEffect::GetPropertyList` | `'Effectiveness: {0}%'`（keep） | ✅ 捞回 |
| `' shield'` | `AddShieldEffect::GetPropertyList` | 同上 | ✅ 捞回 |
| `'BURN'` | `AddExplosionEffect::GetDescription` | `'Explosion damage'`/`'Explosion radius'`（keep） | ✅ 捞回 |
| `'string missing for {0}'` | `ModifyWeaponProperty::GetEffectName` | 12 个 keep 兄弟（属性名） | ⚠️ 调试兜底，价值低 |
| `' - ID: {0} - Name: {1} ...'`、`'Avg bytes per sec: '`、`'Bitrate: '`、`'Block align: '`、`'Channel count: '`、`'Compression code: '`、`'Cues:\n'`、`'No cues'`、`'Riff type ID: '`、`'Sample count: '`、`'Sample rate: '`、`'Size: '`（共 12 条） | `MordiAudio.Wave.Metadata::GetAllMetadataAsString` | `'Duration: '`（keep） | ❌ **误报**：MordiAudio 是第三方音频库，`'Duration: '` 被白名单收录是巧合 |
| `'ConsumableWheel'`、`'MoveGrid'`、`'MoveSelection'`、`'PickUpModule'`、`'SelectShop'`、`'SelectVault'`（6 条） | `ItemWheelActionMap::.ctor`、`ModuleGridInput::RegisterPlayerInput`、`ConsumablesShopWidget::RegisterInput` 等 | `'Shop'`/`'Unequip'`/`'Selection'`（keep） | ❌ **误报**：这些是 InputActionMap / InputAction 名，不是 UI 文案 |

**R2 有明确的误报模式，不要无脑采纳**：只要一个方法里同时有"UI 标签"和"标识符"，R2 就会把标识符一起捞上来。必须逐方法人工过一遍。

### C. 手工 IL 验证补入（自动规则漏掉的，14 条）

**⭐ 最重要的一条：`LoadingScreen::GetStepMessage` 整组 7 条全被丢弃 —— 系统性漏检。**

```
LoadingScreen::GetStepMessage(LevelGenerationStep)   ← 一个 switch，返回加载界面步骤文案
  IL_0024: ldstr 'Generating graph'
  IL_002C: ldstr 'Generating biome map'
  IL_0034: ldstr 'Placing points of interests'
  IL_003C: ldstr 'Generating height map'
  IL_0044: ldstr 'Rasterization'
  IL_004C: ldstr 'Growing flora'
  IL_0054: ldstr 'Placing entities'
  IL_0073: ret

调用方：LoadingScreen::UpdateText  →  TMPro.TMP_Text::set_text   ★
```

**这 7 条全部是 reject**（'Generating graph' 等 5 条 `unattributed`，'Rasterization' 被 `identifier` 规则误杀）。它们**没有**被自动规则捞回，因为：整组都是 reject（无 keep 兄弟可校准），且 `GetStepMessage` 自身不调用文本出口（它是返回值给调用方去 set_text）。这正是"helper 返回 UI 字符串"这一类漏检——**建议把这条模式当作独立检查项，同类可能还有其它 `Get*Message` / `Get*Text` helper。**

| 字面量 | 调用点 | 证据链 | 判定 |
|---|---|---|---|
| `'Generating graph'`、`'Generating biome map'`、`'Generating height map'`、`'Rasterization'`、`'Growing flora'`、`'Placing entities'`、`'Placing points of interests'`（7 条） | `LoadingScreen::GetStepMessage` | ← `LoadingScreen::UpdateText` → `TMP_Text::set_text` | ✅ 捞回 |
| `' - recharge {0:0.0#}/s'` | `Unit::GetPropertyList` | ← `HoveredModuleInfo::UpdateEffectInfos`（模块悬浮提示框） | ✅ 捞回 |
| `'<color={0}>{1:0.#}</color>{2}'`、`'<color={0}>{1}</color>{2}'` | `TextFormatter::ResourceAmount` | ← `HoveredModuleInfo::AddModuleOrWeaponProperties`、`WeaponBase::GetPropertyList` | ✅ 捞回 |
| `'<color="orange">{0:0.#}'`、`'<color=#666666>{0:0.#}'` | `CellInfoManager::GetBurnText` | ← `CellInfoManager::GetValue`（地图格信息） | ✅ 捞回 |
| `'<space=1em>><space=1em>'` | `DisplayableProperty::.ctor` | ← 各 `*Effect::GetPropertyList` → `HoveredModuleInfo` | ✅ 捞回 |
| `'display not implemented yet'` | `ModifyWeaponProperty::GetDeltaString` | 模块提示框 delta 兜底 | ✅ 捞回 |

### 总计

| 来源 | 条数 |
|---|---|
| A（R1 直接命中，去掉 2 条非文案） | **9** |
| B（R2 可信子集，已剔除 18 条误报） | **5** |
| C（手工 IL 验证补入） | **14** |
| **合计应捞回** | **≈ 28** |
| 待定（`'MapControl'`、`'string missing for {0}'`） | 2 |
| R3 单独命中（噪音大，未计入） | 224 |

## 判断依据有多可靠

| 层级 | 可靠性 | 说明 |
|---|---|---|
| R1（同方法直接调用文本出口） | **高** | 5623/5623 IL 精确解码；出口调用点是硬事实。**残余风险**：同方法内共现 ≠ 该字符串真的流向该出口（`'MapControl'`、`'<color=#'`、`'yyyy - MM - dd'` 就是共现但非文案的例子）。约 25% 的 R1 命中是非文案，需人工过一眼。 |
| R2（同方法 keep 兄弟） | **中** | 逻辑强（同返回路径），但**误报率高**：24 条命中里 18 条是误报（第三方库、InputAction 名）。**必须逐方法人工确认，不能批量采纳。** |
| C（手工 IL 验证） | **高** | 每条都看过了调用链的 IL。`LoadingScreen` 那 7 条尤其硬：`UpdateText` 的 `set_text` 调用点是直接读出来的。 |
| R3（传递可达） | **低** | 超级枢纽方法（`Ship::Update` 等）导致 224 条噪音。**不建议单独使用。** |

## 附带发现：游戏**没有**本地化层

我专门查了（`scripts/q3_locprobe.py`）：全汇编没有 `Localization` / `Language` / `Translation` / `StringTable` / `I18n` 类。名字像的 `LocalConfig` / `LocalConfigEditor` / `LocalConfigData` 是**本地画质/雾效配置**，与语言无关。

含义：
- `'META_UNLOCKED_LOADOUTS'` / `'PLAYER_PREF_TUTORIAL_*'` 是 **PlayerPrefs 键**，不是本地化键，不该翻。
- `'string missing for {0}'`（`ModifyWeaponProperty::GetEffectName`）是属性名的**调试兜底**，说明属性名是硬编码英文，没有查表机制。
- 所以汉化必须**逐条替换字面量 + 资产字段**，不存在"翻一个语言表就全搞定"的捷径。这也解释了为什么 DLL 字面量这 507 条对汉化覆盖率这么关键。

---

# 不确定项 / 还差什么才能确定

| # | 不确定的事 | 还差什么 |
|---|---|---|
| 1 | 那个 Google 表格 CSV 的**内容**（列名、行数、有没有物品名与描述） | **网络**。本机 DNS 把 `docs.google.com` 劫持到 `31.13.112.9`（Facebook IP 段），`web_fetch` 也被 IP 策略拒绝。需要用户挂代理后自己抓一次，或换网络环境。**这不影响问题 1 的结论（B 已闭合）**，只影响"表格能否当汉化对照参考"。 |
| 2 | `'MapControl'` 是否真是玩家可见文本 | 看 `ShipMenuToggler::Open` 的完整数据流（`'MapControl'` 是否真的进了 `set_text`，还是同方法里 `FindActionMap("MapControl")` 的副产品）。需要做一次带栈追踪的 IL 数据流分析。 |
| 3 | R2 里是否还有除 `MordiAudio` / InputAction 之外的误报模式 | 24 条逐方法人工过一遍（约 20 分钟）。 |
| 4 | R3 那 224 条里是否还埋着真 UI 文案 | 需要**真正的数据流分析**（跟踪字符串从 `ldstr` 到 `set_text` 的栈位置），而不是调用图可达性。当前方法无法区分"字符串真的进了出口"和"只是同一个方法里有出口"。 |
| 5 | 是否还有别的 `Get*Message` / `Get*Text` helper 整组漏检 | 建议加一条规则：所有返回 `System.String` 且被含文本出口的方法调用的方法，其字面量全部送人工复核。`LoadingScreen::GetStepMessage` 证明这类漏检是成组发生的。 |
| 6 | 问题 2 的 38 条内部名将来是否需要翻 | 取决于是否新增"敌方情报/图鉴"类 UI。当前构建里不需要。 |

---

# 复现命令

```powershell
$PY = "C:\Users\houdezaiwu\anaconda3\python.exe"
cd C:\Users\houdezaiwu\Documents\github\punk-cn-translation

# 问题 1
& $PY scripts\q1_shopconfig.py     # 定位 pid 23103 + 全资产 http 字符串扫描
& $PY scripts\q1_items.py          # itemList 62 条 + 4 个 registry
& $PY scripts\q1_rawgrep.py        # 全盘 425MB 字节扫描（决定性证据）
& $PY scripts\q1_dll_scan.py       # 5623 方法 IL 全解码 + 5 组查询
& $PY scripts\q1_query2.py         # 调用点追溯（谁调用 Parse）
& $PY scripts\q1_fetch_csv.py      # 尝试抓 CSV（本机网络下会失败）

# 问题 2
& $PY scripts\q2_weaponmodule.py   # 60 实例 + 引用图 + registry
& $PY scripts\q2_il_print.py       # displayName→TMP 链的 IL
& $PY scripts\q_il.py "ModuleData::get_Equippable" "Module::get_DisplayName"

# 问题 3
& $PY scripts\q3_reclaim.py        # 带真实归属的重打分
& $PY scripts\q3_detail.py         # 429 条逐条判定
& $PY scripts\q3_siblings.py       # 同方法兄弟分析
& $PY scripts\q3_tiers.py          # 最终分层清单
& $PY scripts\q3_final.py          # 调用链证据
& $PY scripts\q3_locprobe.py       # 本地化层探测（结论：不存在）
& $PY scripts\q_ldstr_ctx.py "Ship::UpdateFuelLevel"   # 单方法 ldstr 上下文
```

关键中间产物：
- `data/dump/q1_rawgrep.txt` — URL 全盘命中（问题 1 决定性证据）
- `data/dump/q1_dll_scan.txt` — 联网调用点全枚举
- `data/dump/q2_il_dump.txt` — `displayName → TMP_Text::set_text` 的 IL
- `data/dump/q2_weaponmodule_instances.json` — 60 实例 + 引用方
- `data/dump/q3_reclaim_tiers.txt` / `.json` — 分层捞回清单
- `data/dump/q3_reclaim_final.txt` — 带完整证据的捞回清单
