using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace PunkCn
{
    /// <summary>
    /// 资源里序列化的 m_text 不走 set_text，所以场景加载后要主动扫一遍。
    /// 见 plan.html claim 1.2：两条通道缺一条就漏一半。
    /// </summary>
    internal static class SceneSweep
    {
        internal static void Install()
        {
            SceneManager.sceneLoaded += OnSceneLoaded;
        }

        private static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            try
            {
                TranslateLoaded(scene.name);
                if (Plugin.Instance != null) Plugin.Instance.StartCoroutine(SecondPass());
            }
            catch (System.Exception e)
            {
                Plugin.Log.LogError("[PunkCn] 场景扫描出错: " + e);
            }
        }

        /// <summary>界面常常在 sceneLoaded 之后才构建完，1.5 秒后再补一次。</summary>
        private static IEnumerator SecondPass()
        {
            yield return new WaitForSeconds(1.5f);
            try { TranslateLoaded("补扫"); }
            catch (System.Exception e) { Plugin.Log.LogError("[PunkCn] 补扫出错: " + e); }
        }

        internal static void TranslateLoaded(string tag)
        {
            var all = Resources.FindObjectsOfTypeAll<TMP_Text>();
            if (Plugin.Enabled != null && !Plugin.Enabled.Value)
            {
                Plugin.Log.LogInfo("[PunkCn] " + tag + " 扫描 " + all.Length + " 处 TMP 文本，开关已关，跳过");
                return;
            }

            int hit = 0;
            foreach (var t in all)
            {
                if (t == null) continue;
                var cur = t.text;
                if (string.IsNullOrEmpty(cur)) continue;

                string cn;
                if (!Table.TryGet(cur, out cn)) continue;

                t.text = cn;      // 走的是打过补丁的 setter，Postfix 会顺带换字体
                hit++;
            }
            Plugin.Log.LogInfo("[PunkCn] " + tag + " 扫描 " + all.Length + " 处 TMP 文本，改写 " + hit + " 处");
        }
    }
}
