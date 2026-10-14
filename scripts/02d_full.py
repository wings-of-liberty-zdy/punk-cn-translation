import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import os, json, collections, traceback, time
import UnityPy
import UnityPy.helpers.TypeTreeGenerator as tg

DATA = r"D:\SteamLibrary\steamapps\common\PUNK Playtest\Punk_Data"
MANAGED = os.path.join(DATA, "Managed")
t0 = time.time()
gen = tg.TypeTreeGenerator("6000.3.4f1")
print("ctor ok", time.time() - t0, flush=True)
gen.load_local_dll_folder(MANAGED)
print("load_local_dll_folder ok", time.time() - t0, flush=True)

env = UnityPy.load(os.path.join(DATA, "resources.assets"))
env.typetree_generator = gen
sf = list(env.files.values())[0]

# resolve script names
print("script_types:", len(sf.script_types))
names = []
for st in sf.script_types[:20]:
    print("  ", st)
    names.append(st)

ok = fail = 0
errs = collections.Counter()
scripts = collections.Counter()
samples = []
t1 = time.time()
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    try:
        d = obj.read()
        ok += 1
        try:
            sn = d.m_Script.read().m_Name
        except Exception as e:
            sn = "?" + type(e).__name__
        scripts[sn] += 1
        if len(samples) < 5:
            samples.append((sn, {k: str(v)[:120] for k, v in d.__dict__.items()}))
    except Exception as e:
        fail += 1
        errs[type(e).__name__ + ": " + str(e)[:150]] += 1
    if ok + fail >= 2000:
        break
print(f"read ok={ok} fail={fail}  in {time.time()-t1:.1f}s", flush=True)
for k, v in errs.most_common(8):
    print("   ERR", v, k)
print("scripts:", len(scripts))
for k, v in scripts.most_common(50):
    print(f"   {k}: {v}")
for sn, s in samples:
    print("SAMPLE", sn, json.dumps(s, ensure_ascii=False)[:400])
