using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using TMPro;
using UnityEngine;
using UnityEngine.TextCore;
using UnityEngine.TextCore.LowLevel;

namespace PunkCn
{
    /// <summary>
    /// 用内嵌的中文像素字体建 TMP 动态字体资产，并挂进回退链。见 plan.html claim 3。
    ///
    /// 四条实测结论决定了这个实现（详见 docs/recon.md §8、§9）：
    ///
    /// 1. **Unity 6000.3.4 的 OS 字体通道是坏的** —— FontEngine.LoadFontFace(Font, int)
    ///    对 Microsoft YaHei / Arial 一律返回 Invalid_File_Structure。
    ///    所以只能走字节流：FontEngine.LoadFontFace(byte[], int)。
    ///
    /// 2. **动态字体资产必须给出源文件位置**（m_SourceFontFilePath）。
    ///    TMP 每次补字形前都会重新 LoadFontFace，找不到源文件就补不进字形，
    ///    表现是游戏里显示成一排 □ 缺字框。
    ///
    /// 3. **CreateInstance 不触发 OnEnable**，而 TMP 在那里建图集空闲矩形与查找表。
    ///    缺了它们 TryAddCharacters 只在 TMP 内部抛空引用，不提示缺哪个字段。
    ///
    /// 4. **必须按 pointSize 分开建资产。** 游戏有 4 个字体资产，pointSize 是
    ///    38 / 50 / 86 / 90。TMP 的字形缩放是 fontSize / faceInfo.pointSize，
    ///    只用一个尺寸会让原来用 50 的元素大 39%、走回退链的元素偏小。
    /// </summary>
    internal static class FontInstaller
    {
        private const string TtfResource = "PunkCn.Resources.pixel-cn.ttf";

        /// <summary>主字体 8-bit-hud SDF 的 pointSize。没有别的信息时按它来。</summary>
        internal const float DefaultPointSize = 38f;

        private static byte[] _bytes;
        private static string _sourcePath;

        private static readonly Dictionary<int, TMP_FontAsset> Cache = new Dictionary<int, TMP_FontAsset>();

        internal static TMP_FontAsset Install(string mode)
        {
            try
            {
                _bytes = ReadEmbedded(TtfResource);
                _sourcePath = WriteTempCopy(_bytes);
                Plugin.Log.LogInfo("[PunkCn] 内嵌字体 " + _bytes.Length + " 字节 -> " + _sourcePath);
                return GetFor(DefaultPointSize);
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("[PunkCn] 字体安装失败: " + e);
                return null;
            }
        }

        /// <summary>按原字体的 pointSize 取（或建）一个中文字体资产。</summary>
        internal static TMP_FontAsset GetFor(float originalPointSize)
        {
            int key = (int)Math.Round(originalPointSize);
            if (key < 8) key = 8;
            if (key > 128) key = 128;

            TMP_FontAsset a;
            if (Cache.TryGetValue(key, out a) && a != null) return a;

            try
            {
                a = Build(key);
                if (a != null)
                {
                    a.name = "PunkCn CJK " + key;
                    int hooked = RegisterAsFallback(a);
                    Cache[key] = a;
                    Plugin.Log.LogInfo("[PunkCn] 建中文字体资产 pointSize=" + key
                                       + " 图集=" + a.atlasWidth + "x" + a.atlasHeight
                                       + " 行高=" + a.faceInfo.lineHeight.ToString("0.##")
                                       + " 回退挂载=" + hooked + " 处");
                }
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("[PunkCn] 建 " + key + "px 中文字体失败: " + e);
            }
            return a;
        }

        private static TMP_FontAsset Build(int pointSize)
        {
            var err = FontEngine.LoadFontFace(_bytes, pointSize);
            if (err != FontEngineError.Success)
            {
                Plugin.Log.LogWarning("[PunkCn] 采样 " + pointSize + "px 加载失败: " + err);
                return null;
            }

            var asset = MakeAsset(pointSize);

            string missing;
            bool ok = asset.TryAddCharacters(ProbeText, out missing);
            Plugin.Log.LogInfo("[PunkCn] " + pointSize + "px TryAddCharacters=" + ok
                               + " 缺=" + (string.IsNullOrEmpty(missing) ? "无" : missing));
            return ok ? asset : null;
        }

        /// <summary>用来验证字形能不能真的补进去，顺便当作探针串。</summary>
        private const string ProbeText = "按任意键开始设置武器轮盘护盾";

        // ── 行盒与字面：逐字体镜像原字体 ────────────────────────────────────
        //
        // 游戏 4 个字体资产的「字面高度占字号的比例」差得极远，这是中文换字体后
        // 有的地方撑破按钮、有的地方偏小的真正原因：
        //
        //   字体                     pointSize  字面高/em   行高/em   上伸/em
        //   8-bit-hud SDF              38       1.21       1.60      1.40
        //   Font_Minimum               50       0.32       0.94      0.67
        //   LiberationSans SDF         86       0.69       1.15      0.91
        //   prstartk SDF               90       0.88       1.00      0.88
        //   Zpix（我们的）              —        0.917      1.00      0.833
        //
        // Font_Minimum 的字面只占字号 0.32，Zpix 占 0.917 —— 差 2.9 倍，
        // 所以配装界面的「返回」比原版 BACK 大一倍多、下沿溢出按钮框。
        // 8-bit-hud 反过来（1.21 > 0.917），所以模块名与武器名偏小。
        //
        // 做法：每个字体镜像它自己的行盒比例，并用 faceInfo.scale 把字面高对齐 ——
        //   scale = 原字体字面高 / Zpix 字面高
        //   lineHeight 等按 P/scale 换算，保证最终行距 = 原字体行高 × fontSize。
        private struct SrcMetrics
        {
            public float ascent, descent, line, mean, tab;
            /// <summary>
            /// 字面高的修正系数。**必须用同元素实测，不能用 capLine/pointSize 推算** ——
            /// 这些资产的 m_UnitsPerEM 是 0，capLine 那套比例是虚的（8-bit-hud 的
            /// capLine/pointSize = 1.21，真实字体不可能有 1.21 em 的字母高度）。
            ///
            /// 实测（原版 vs 我们，同一个元素、同一个 fontSize）：
            ///   Font_Minimum（配装界面 BACK）  原版 9px  / 我们 19px  -> 0.47
            ///   8-bit-hud（配装卡片武器名）    原版 9px  / 我们 8px   -> 1.13
            /// </summary>
            public float scale;
        }

        private static readonly Dictionary<int, SrcMetrics> SrcByPoint = new Dictionary<int, SrcMetrics>
        {
            { 38, new SrcMetrics { ascent = 1.40f, descent = -0.20f, line = 1.60f, mean = 1.00f, tab = 0.605f, scale = 1.13f } },
            { 50, new SrcMetrics { ascent = 0.67f, descent = -0.27f, line = 0.94f, mean = 0.32f, tab = 0.46f, scale = 0.47f } },
            { 86, new SrcMetrics { ascent = 0.91f, descent = -0.24f, line = 1.15f, mean = 0.52f, tab = 0.53f, scale = 1.00f } },
            { 90, new SrcMetrics { ascent = 0.88f, descent = -0.12f, line = 1.00f, mean = 0.63f, tab = 0.51f, scale = 1.00f } },
        };

        private static void MatchGameLineMetrics(ref FaceInfo fi, int pointSize)
        {
            SrcMetrics m;
            if (!SrcByPoint.TryGetValue(pointSize, out m)) m = SrcByPoint[38];

            float scale = m.scale;
            float k = pointSize / scale;   // em 值 -> 我们资产里的单位
                                           // （行距 = lineHeight × fontSize/pointSize × scale，要等于 line × fontSize）

            fi.pointSize = pointSize;
            fi.scale = scale;
            fi.lineHeight = m.line * k;
            fi.ascentLine = m.ascent * k;
            fi.descentLine = m.descent * k;
            fi.capLine = m.mean * k;
            fi.meanLine = m.mean * k;
            fi.baseline = 0f;
            fi.tabWidth = m.tab * k;
            fi.underlineOffset = 0.075f * k;
            fi.underlineThickness = 0.05f * k;
            fi.strikethroughOffset = m.mean * k;
            fi.strikethroughThickness = 0.05f * k;
            fi.superscriptOffset = m.ascent * k;
            fi.subscriptOffset = m.descent * k;
        }

        private static TMP_FontAsset MakeAsset(int pointSize)
        {
            const int W = 1024, H = 1024, PAD = 4;

            var asset = ScriptableObject.CreateInstance<TMP_FontAsset>();
            asset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            asset.isMultiAtlasTexturesEnabled = true;

            var fi = FontEngine.GetFaceInfo();
            MatchGameLineMetrics(ref fi, pointSize);

            // 这几个在这个 TMP 版本里是只读属性，只能反射写私有字段。
            SetField(asset, "m_FaceInfo", fi);
            SetField(asset, "m_AtlasWidth", W);
            SetField(asset, "m_AtlasHeight", H);
            SetField(asset, "m_AtlasPadding", PAD);
            SetField(asset, "m_AtlasRenderMode", GlyphRenderMode.SDFAA);
            SetField(asset, "m_Version", "1.1.0");

            // 没有这个，TMP 补字形时找不到源文件，游戏里就是一排 □。
            SetField(asset, "m_SourceFontFilePath", _sourcePath);
            SetField(asset, "m_SourceFontFileGUID", string.Empty);
            SetField(asset, "m_SourceFontFile", null);

            var tex = new Texture2D(W, H, TextureFormat.Alpha8, false);
            tex.name = "PunkCn CJK Atlas " + pointSize;
            asset.atlasTextures = new Texture2D[] { tex };

            var shader = Shader.Find("TextMeshPro/Distance Field");
            if (shader == null) throw new Exception("找不到 TextMeshPro/Distance Field shader");
            var mat = new Material(shader);
            mat.SetTexture(ShaderUtilities.ID_MainTex, tex);
            mat.SetFloat(ShaderUtilities.ID_TextureWidth, W);
            mat.SetFloat(ShaderUtilities.ID_TextureHeight, H);
            // _GradientScale 必须等于 SDF 的 padding + 1，否则 SDF 坡度对不上，
            // 小字号下字形会又细又暗。TMP 自己在 CreateFontAsset 里就是这么设的。
            mat.SetFloat(ShaderUtilities.ID_GradientScale, PAD + 1);
            mat.SetFloat(ShaderUtilities.ID_ScaleX, 1f);
            mat.SetFloat(ShaderUtilities.ID_ScaleY, 1f);
            mat.SetFloat(ShaderUtilities.ID_Sharpness, 0f);
            mat.SetFloat(ShaderUtilities.ID_PerspectiveFilter, 0f);
            mat.SetFloat(ShaderUtilities.ID_FaceDilate, 0f);
            mat.SetFloat(ShaderUtilities.ID_OutlineWidth, 0f);
            mat.SetFloat(ShaderUtilities.ID_OutlineSoftness, 0f);
            mat.SetColor(ShaderUtilities.ID_FaceColor, Color.white);
            asset.material = mat;

            // CreateInstance 不会触发 OnEnable，TMP 在那里建图集空闲矩形与查找表。
            // 缺了它们 TryAddCharacters 会在内部空引用，且不提示缺哪个字段。
            InitAtlasState(asset, W, H);
            asset.ReadFontAssetDefinition();
            InitAtlasState(asset, W, H);

            return asset;
        }

        /// <summary>把 TMP 在 OnEnable 里会建的那几个集合显式建出来。</summary>
        private static void InitAtlasState(TMP_FontAsset asset, int w, int h)
        {
            SetField(asset, "m_AtlasTextureIndex", 0);
            SetField(asset, "m_UsedGlyphRects", new List<GlyphRect>());

            var free = new List<GlyphRect>();
            free.Add(new GlyphRect(0, 0, w - 1, h - 1));
            SetField(asset, "m_FreeGlyphRects", free);

            SetField(asset, "m_GlyphTable", new List<Glyph>());
            SetField(asset, "m_CharacterTable", new List<TMP_Character>());
            SetField(asset, "m_FallbackFontAssetTable", new List<TMP_FontAsset>());
        }

        /// <summary>写 TMP_FontAsset 的私有字段（部分属性在这个 TMP 版本里只读）。</summary>
        private static void SetField(object target, string fieldName, object value)
        {
            var f = target.GetType().GetField(fieldName,
                BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
            if (f == null) { Plugin.Log.LogWarning("[PunkCn] 找不到字段 " + fieldName); return; }
            f.SetValue(target, value);
        }

        private static string WriteTempCopy(byte[] bytes)
        {
            var dir = Path.Combine(Path.GetTempPath(), "PunkCn");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "pixel-cn.ttf");
            File.WriteAllBytes(path, bytes);
            return path;
        }

        private static byte[] ReadEmbedded(string name)
        {
            using (var st = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
            {
                if (st == null) throw new FileNotFoundException("内嵌资源缺失：" + name);
                var buf = new byte[st.Length];
                int off = 0;
                while (off < buf.Length)
                {
                    int n = st.Read(buf, off, buf.Length - off);
                    if (n <= 0) break;
                    off += n;
                }
                return buf;
            }
        }

        private static int RegisterAsFallback(TMP_FontAsset asset)
        {
            int hooked = 0;
            try
            {
                var global = TMP_Settings.fallbackFontAssets;
                if (global != null && !global.Contains(asset)) { global.Add(asset); hooked++; }
            }
            catch (Exception e) { Plugin.Log.LogWarning("[PunkCn] 全局回退挂载失败: " + e.Message); }

            try
            {
                foreach (var fa in Resources.FindObjectsOfTypeAll<TMP_FontAsset>())
                {
                    if (fa == null || fa == asset) continue;
                    if (fa.fallbackFontAssetTable == null) fa.fallbackFontAssetTable = new List<TMP_FontAsset>();
                    if (!fa.fallbackFontAssetTable.Contains(asset)) { fa.fallbackFontAssetTable.Add(asset); hooked++; }
                }
            }
            catch (Exception e) { Plugin.Log.LogWarning("[PunkCn] 逐字体回退挂载失败: " + e.Message); }
            return hooked;
        }

        internal static bool ContainsCjk(string s)
        {
            if (string.IsNullOrEmpty(s)) return false;
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                if ((c >= 0x4E00 && c <= 0x9FFF) || (c >= 0x3400 && c <= 0x4DBF)
                    || (c >= 0x3000 && c <= 0x303F) || (c >= 0xFF00 && c <= 0xFFEF)) return true;
            }
            return false;
        }
    }
}
