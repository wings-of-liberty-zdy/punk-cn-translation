using System;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;

namespace PunkCn
{
    [BepInPlugin(Guid, "PUNK 汉化", "0.1.0")]
    public class Plugin : BaseUnityPlugin
    {
        public const string Guid = "punk.cn.translation";

        internal static ManualLogSource Log;
        internal static ConfigEntry<bool> Enabled;
        internal static ConfigEntry<string> FontMode;
        internal static Plugin Instance;

        private Harmony _harmony;

        private void Awake()
        {
            Instance = this;
            Log = Logger;
            // 任何一步失败都只记日志，游戏照常启动。见 plan.html claim 1.3。
            try
            {
                Enabled = Config.Bind("General", "Enabled", true, "开启中文替换");
                FontMode = Config.Bind("Font", "Mode", "pixel",
                    "pixel = 用内嵌的中文像素字体；system = 用系统字体兜底");

                var n = Table.Load();
                Log.LogInfo("[PunkCn] 翻译表加载 " + n + " 条");

                var font = FontInstaller.Install(FontMode.Value);
                Log.LogInfo("[PunkCn] 字体: " + font);

                _harmony = new Harmony(Guid);
                _harmony.PatchAll(typeof(TextPatcher));
                Log.LogInfo("[PunkCn] TMP_Text.set_text 补丁已挂");

                SceneSweep.Install();
                Log.LogInfo("[PunkCn] 汉化已加载");
            }
            catch (Exception e)
            {
                Log.LogError("[PunkCn] 初始化失败，游戏继续运行: " + e);
            }
        }
    }
}
