using HarmonyLib;
using TMPro;

namespace PunkCn
{
    /// <summary>
    /// 只拦 set_text（属性写入），不拦 get_text。
    /// 游戏代码读 text 做判断时拿到的仍是英文，译文不会改变游戏行为。
    /// 见 plan.html claim 1.1。
    /// </summary>
    [HarmonyPatch(typeof(TMP_Text), "set_text")]
    internal static class TextPatcher
    {
        private static void Prefix(ref string value)
        {
            if (Plugin.Enabled != null && !Plugin.Enabled.Value) return;
            if (string.IsNullOrEmpty(value)) return;

            string cn;
            if (Table.TryGet(value, out cn)) value = cn;
        }

        private static void Postfix(TMP_Text __instance)
        {
            FontFixer.Apply(__instance);
        }
    }

    /// <summary>
    /// TMP_Text.SetText(...) 这一族方法**直接写 m_text 字段，不走 text 属性 setter**，
    /// 所以上面那个 set_text 补丁拦不到它们。实测配装卡片的武器名就是走这条路，
    /// 结果既没换字体（字形按原字体的 pointSize 缩放，偏小）也没走我们的换字体逻辑。
    ///
    /// 这里补上字符串重载：先翻译参数，再在返回后统一修字体。
    /// 数值重载（SetText(string, float) 等）由字符串重载间接覆盖，不重复挂。
    /// </summary>
    [HarmonyPatch(typeof(TMP_Text), "SetText", new[] { typeof(string) })]
    internal static class SetTextPatcher
    {
        private static void Prefix(ref string text)
        {
            if (Plugin.Enabled != null && !Plugin.Enabled.Value) return;
            if (string.IsNullOrEmpty(text)) return;

            string cn;
            if (Table.TryGet(text, out cn)) text = cn;
        }

        private static void Postfix(TMP_Text __instance)
        {
            FontFixer.Apply(__instance);
        }
    }

    [HarmonyPatch(typeof(TMP_Text), "SetText", new[] { typeof(string), typeof(bool) })]
    internal static class SetTextSyncPatcher
    {
        private static void Prefix(ref string text)
        {
            if (Plugin.Enabled != null && !Plugin.Enabled.Value) return;
            if (string.IsNullOrEmpty(text)) return;

            string cn;
            if (Table.TryGet(text, out cn)) text = cn;
        }

        private static void Postfix(TMP_Text __instance)
        {
            FontFixer.Apply(__instance);
        }
    }

    /// <summary>
    /// 含汉字的文本换成中文字体资产。
    ///
    /// **关键：按该文本原本用的字体的 pointSize 来选资产。**
    /// 游戏有 4 个字体资产（8-bit-hud SDF 38 / Font_Minimum 50 / LiberationSans SDF 86 /
    /// prstartk SDF 90），TMP 的字形缩放是 fontSize / faceInfo.pointSize。
    /// 只用一个 36 的资产，原来用 50 的地方会大 39%（返回按钮被撑大、位置下移），
    /// 走回退链的地方又会被按原字体的 pointSize 缩放而偏小。
    ///
    /// 纯英文界面保持游戏原字体不动。
    /// </summary>
    internal static class FontFixer
    {
        /// <summary>诊断用：记录每个「原字体 + 字号」组合，看清谁需要多大。</summary>
        private static readonly System.Collections.Generic.HashSet<string> Logged =
            new System.Collections.Generic.HashSet<string>();

        /// <summary>
        /// 记住每条文本**原本**用的字体的 pointSize。
        ///
        /// 为什么必须记：我们一旦把 t.font 换成自己的资产，原字体信息就丢了。
        /// 之后游戏再给同一个元素赋一次值，就会读到自己资产的 pointSize（38），
        /// 于是原本是 Font_Minimum(50) 的元素被错当成 38 —— 实测日志里出现过
        /// 「原=PunkCn CJK 38 ... 文本=前往」，而「前往」本来是 Font_Minimum。
        ///
        /// 用 ConditionalWeakTable 而不是 Dictionary：Unity 销毁对象时不会通知我们，
        /// 用普通字典会一直持有已销毁的 TMP_Text，造成泄漏。
        /// </summary>
        private sealed class PointHolder { public float Value; }

        private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<TMP_Text, PointHolder> Originals =
            new System.Runtime.CompilerServices.ConditionalWeakTable<TMP_Text, PointHolder>();

        internal static void Apply(TMP_Text t)
        {
            if (t == null) return;
            if (!FontInstaller.ContainsCjk(t.text)) return;

            PointHolder holder;
            if (!Originals.TryGetValue(t, out holder))
            {
                holder = new PointHolder { Value = FontInstaller.DefaultPointSize };
                var cur0 = t.font;
                if (cur0 != null && !cur0.name.StartsWith("PunkCn CJK"))
                {
                    float ps0 = cur0.faceInfo.pointSize;
                    if (ps0 > 0f) holder.Value = ps0;
                }
                Originals.Add(t, holder);
            }

            float want = holder.Value;
            var cur = t.font;
            string srcName = cur != null ? cur.name : "?";

            var asset = FontInstaller.GetFor(want);
            if (asset == null) return;

            // 诊断：同一个「原字体 + 原字号」只记一次，把原字体名、pointSize、
            // 这条文本的 fontSize 和内容片段写进日志 —— 用来定位到底哪个元素需要哪种缩放。
            if (Logged.Count < 120)
            {
                string key = srcName + "|" + want + "|" + t.fontSize;
                if (Logged.Add(key))
                {
                    string snip = t.text.Length > 14 ? t.text.Substring(0, 14) : t.text;
                    snip = snip.Replace("\n", "\\n");
                    Plugin.Log.LogInfo("[PunkCn] 字体诊断 原=" + srcName
                                       + " pointSize=" + want
                                       + " fontSize=" + t.fontSize
                                       + " 文本=" + snip);
                }
            }

            if (t.font == asset) return;
            t.font = asset;
        }
    }
}
