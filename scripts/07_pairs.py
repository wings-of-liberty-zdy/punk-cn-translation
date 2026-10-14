import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, collections, os
D = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"
rows = [json.loads(l) for l in open(os.path.join(D, "mb_strings.jsonl"), encoding="utf-8")]

# every distinct (cls, leaf-field) pair that is NOT m_Name / sfx / id / guid / path
LEAFBLACK = ("sfx", "guid", "id", "path", "action", "bytesstring", "prefabmodifications",
             "entityid", "filename", "rifftypeid", "processors", "interactions", "groups",
             "expectedcontroltype", "m_id", "tags", "layers", "sortinglayer", "script", "material",
             "shader", "sprite", "clip", "controller", "asset", "font", "texture", "resource")
pairs = collections.Counter()
for r in rows:
    leaf = r["field"].split(".")[-1].split("[")[0]
    ll = leaf.lower()
    if ll == "m_name":
        continue
    if any(b == ll or ll.endswith(b) for b in LEAFBLACK):
        continue
    pairs[(r["cls"], leaf)] += 1

print("=== all non-blacklisted (cls, leaffield) pairs ===")
for (c, f), n in pairs.most_common(200):
    print(f"  {n:6d}  {c}.{f}")
