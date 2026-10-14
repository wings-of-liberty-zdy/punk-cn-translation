using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace PunkCn
{
    /// <summary>
    /// 从 TTF/OTF 的 name 表读字体族名，避免把族名写死在代码里。
    /// 取 nameID 1（族名）、4（全名）、16（排版族名）、6（PostScript 名），
    /// 顺序即尝试优先级：GDI 一般按族名注册，像素字体常把完整名放进 4。
    /// </summary>
    internal static class TtfName
    {
        private static readonly int[] WantedIds = { 1, 4, 16, 6 };

        internal static List<string> ReadFamilyNames(string path)
        {
            var result = new List<string>();
            try
            {
                var data = File.ReadAllBytes(path);
                if (data.Length < 12) return result;

                int numTables = Be16(data, 4);
                int nameOffset = -1;
                for (int i = 0; i < numTables; i++)
                {
                    int rec = 12 + i * 16;
                    if (rec + 16 > data.Length) break;
                    if (data[rec] == 'n' && data[rec + 1] == 'a' && data[rec + 2] == 'm' && data[rec + 3] == 'e')
                    {
                        nameOffset = Be32(data, rec + 8);
                        break;
                    }
                }
                if (nameOffset < 0 || nameOffset + 6 > data.Length) return result;

                int count = Be16(data, nameOffset + 2);
                int stringOffset = nameOffset + Be16(data, nameOffset + 4);

                var byId = new Dictionary<int, string>();
                for (int i = 0; i < count; i++)
                {
                    int rec = nameOffset + 6 + i * 12;
                    if (rec + 12 > data.Length) break;

                    int platformId = Be16(data, rec);
                    int nameId = Be16(data, rec + 6);
                    int length = Be16(data, rec + 8);
                    int offset = Be16(data, rec + 10);

                    if (Array.IndexOf(WantedIds, nameId) < 0) continue;
                    if (byId.ContainsKey(nameId)) continue;

                    int start = stringOffset + offset;
                    if (start + length > data.Length) continue;

                    // platformID 3 = Windows，字符串是 UTF-16BE；其余按 Latin-1 处理。
                    string value = platformId == 3
                        ? Encoding.BigEndianUnicode.GetString(data, start, length)
                        : Encoding.GetEncoding(28591).GetString(data, start, length);

                    value = value.Replace("\0", "").Trim();
                    if (value.Length > 0) byId[nameId] = value;
                }

                foreach (var id in WantedIds)
                {
                    string v;
                    if (byId.TryGetValue(id, out v) && !result.Contains(v)) result.Add(v);
                }
            }
            catch (Exception e)
            {
                Plugin.Log.LogWarning("[PunkCn] 读 TTF name 表失败: " + e.Message);
            }
            return result;
        }

        private static int Be16(byte[] d, int i) { return (d[i] << 8) | d[i + 1]; }

        private static int Be32(byte[] d, int i)
        {
            return (d[i] << 24) | (d[i + 1] << 16) | (d[i + 2] << 8) | d[i + 3];
        }
    }
}
