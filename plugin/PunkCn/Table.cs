using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;

namespace PunkCn
{
    /// <summary>
    /// 翻译表：内嵌 TSV，三列 = 编号 / 原文 / 中文。
    /// 原文里的换行在 TSV 里写成字面量 \n，读进来还原。
    /// </summary>
    internal static class Table
    {
        private static readonly Dictionary<string, string> Map =
            new Dictionary<string, string>(StringComparer.Ordinal);

        private static readonly Regex Whitespace = new Regex(@"\s+", RegexOptions.Compiled);

        internal static int Count { get { return Map.Count; } }

        /// <summary>去首尾空白、压缩连续空白、弯引号换直引号。</summary>
        internal static string Normalize(string s)
        {
            if (string.IsNullOrEmpty(s)) return s;
            s = s.Replace('\u2018', '\'').Replace('\u2019', '\'')
                 .Replace('\u201C', '"').Replace('\u201D', '"');
            s = Whitespace.Replace(s, " ");
            return s.Trim();
        }

        internal static int Load()
        {
            Map.Clear();
            var asm = Assembly.GetExecutingAssembly();
            using (var st = asm.GetManifestResourceStream("PunkCn.Resources.punk-cn.tsv"))
            {
                if (st == null) throw new FileNotFoundException("内嵌翻译表缺失（PunkCn.Resources.punk-cn.tsv）");
                using (var rd = new StreamReader(st, new UTF8Encoding(false)))
                {
                    string line;
                    while ((line = rd.ReadLine()) != null)
                    {
                        if (line.Length == 0 || line[0] == '#') continue;
                        var f = line.Split('\t');
                        if (f.Length < 3) continue;
                        var en = Normalize(f[1].Replace("\\n", "\n"));
                        var cn = f[2].Replace("\\n", "\n");
                        if (en.Length == 0 || cn.Length == 0) continue;
                        Map[en] = cn;
                    }
                }
            }
            return Map.Count;
        }

        internal static bool TryGet(string src, out string cn)
        {
            cn = null;
            if (string.IsNullOrEmpty(src)) return false;
            return Map.TryGetValue(Normalize(src), out cn);
        }
    }
}
